# filtering.py
# Modular processor with additional metrics: SDNN, perfusion, respiration

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfiltfilt, find_peaks
from scipy.interpolate import interp1d
import pandas as pd

# ================================================================
# TUNABLE CONSTANTS
# ================================================================
SAMPLE_RATE = 200
BATCH_SIZE = 40                      

TRIM_START_SECONDS = 1.0             # Remove startup artifact
TRIM_END_SECONDS = 2.0               # Remove noisy end

BANDPASS_LOW = 0.7
BANDPASS_HIGH = 10.0
BANDPASS_ORDER = 4

INTEGRATION_WINDOW_SEC = 0.15
MIN_PEAK_DIST_SEC = 0.65             # Stricter to avoid dicrotic notch doubles
PEAK_HEIGHT_FACTOR = 0.25
PEAK_PROMINENCE_FACTOR = 0.08

RR_LOWER_FACTOR = 0.7
RR_UPPER_FACTOR = 1.5

SPO2_DELAY_SEC = 0.02

# Set to True when running standalone, False when called from GUI
PRODUCE_GRAPHS = False

# ================================================================
# MAIN PROCESSING FUNCTION
# ================================================================
def process_ppg_file(filename: str):
    """
    Full Pan-Tompkins processing on a PPG CSV file with seq, IR, Red columns.
    Returns dictionary of metrics and (optionally) shows detailed graphs.
    """
    # --- Load data ---
    df = pd.read_csv(filename)
    seq = df['seq'].values.astype(int)
    ir_raw = df['IR'].values.astype(float)
    red_raw = df['Red'].values.astype(float)

    # --- Gap reconstruction using sequence number ---
    max_seq = seq.max()
    true_total_packets = max_seq + 1
    total_samples = true_total_packets * BATCH_SIZE

    print(f"Max seq: {max_seq} → {true_total_packets} packets attempted")
    print(f"True timeline: {total_samples} samples = {total_samples / SAMPLE_RATE:.1f} seconds")

    ir_full = np.full(total_samples, np.nan)
    red_full = np.full(total_samples, np.nan)

    for i in range(len(df)):
        s = seq[i]
        sample_in_packet = i % BATCH_SIZE
        idx = s * BATCH_SIZE + sample_in_packet
        if idx < total_samples:
            ir_full[idx] = ir_raw[i]
            red_full[idx] = red_raw[i]

    t_full = np.arange(total_samples) / SAMPLE_RATE

    # Interpolate missing packets
    valid = ~np.isnan(ir_full)
    interp_ir = interp1d(np.arange(total_samples)[valid], ir_full[valid],
                         kind='cubic', bounds_error=False, fill_value='extrapolate')
    ir_fixed = interp_ir(np.arange(total_samples))

    interp_red = interp1d(np.arange(total_samples)[valid], red_full[valid],
                          kind='cubic', bounds_error=False, fill_value='extrapolate')
    red_fixed = interp_red(np.arange(total_samples))

    if PRODUCE_GRAPHS:
        plt.figure(figsize=(15, 5))
        plt.plot(t_full, ir_full, label='Raw IR (with gaps)', alpha=0.7, color='lightgray')
        plt.plot(t_full, ir_fixed, label='Interpolated IR (full timeline)', linewidth=1.5, color='blue')
        plt.title('1. Raw Data + Gap-Filled Interpolation')
        plt.xlabel('Time (seconds)')
        plt.ylabel('ADC Value')
        plt.legend()
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.show()

    # --- Trim startup and end noise ---
    trim_start = int(TRIM_START_SECONDS * SAMPLE_RATE)
    trim_end = int(TRIM_END_SECONDS * SAMPLE_RATE)

    ir_trim = ir_fixed[trim_start:-trim_end] if trim_end > 0 else ir_fixed[trim_start:]
    red_trim = red_fixed[trim_start:-trim_end] if trim_end > 0 else red_fixed[trim_start:]
    t_trim = np.arange(len(ir_trim)) / SAMPLE_RATE

    print(f"After trimming: {len(ir_trim)} samples = {len(ir_trim)/SAMPLE_RATE:.2f} seconds")

    if PRODUCE_GRAPHS:
        plt.figure(figsize=(15, 5))
        plt.plot(t_trim, ir_trim, color='navy', linewidth=1.2)
        plt.title('2. Truncated Raw IR (clean section only)')
        plt.xlabel('Time (seconds)')
        plt.ylabel('ADC Value')
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.show()

    # --- AC component (zero-mean) ---
    ir_ac = ir_trim - np.mean(ir_trim)

    if PRODUCE_GRAPHS:
        plt.figure(figsize=(15, 5))
        plt.plot(t_trim, ir_ac, color='darkgreen', linewidth=1.2)
        plt.title('3. Truncated AC Component (DC removed)')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Amplitude')
        plt.axhline(0, color='black', linewidth=0.8, linestyle='--')
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.show()

    # --- Bandpass filter ---
    def bandpass_filter(sig):
        sos = butter(BANDPASS_ORDER, [BANDPASS_LOW, BANDPASS_HIGH], 'band', fs=SAMPLE_RATE, output='sos')
        return sosfiltfilt(sos, sig)

    ir_bp = bandpass_filter(ir_ac)

    if PRODUCE_GRAPHS:
        plt.figure(figsize=(15, 5))
        plt.plot(t_trim, ir_bp, color='purple', linewidth=1.2)
        plt.title('4. Bandpass Filtered (0.7–10 Hz)')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Amplitude')
        plt.axhline(0, color='black', linewidth=0.8, linestyle='--')
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.show()

    # --- Derivative (gradient) ---
    deriv = np.gradient(ir_bp)

    if PRODUCE_GRAPHS:
        plt.figure(figsize=(15, 5))
        plt.plot(t_trim, deriv, color='orange', linewidth=1.2)
        plt.title('5. Derivative (emphasizes slopes)')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Slope')
        plt.axhline(0, color='black', linewidth=0.8, linestyle='--')
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.show()

    # --- Squared ---
    squared = deriv ** 2

    if PRODUCE_GRAPHS:
        plt.figure(figsize=(15, 5))
        plt.plot(t_trim, squared, color='red', linewidth=1.2)
        plt.title('6. Squared (non-linear amplification)')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Amplitude')
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.show()

    # --- Moving integration ---
    win = int(INTEGRATION_WINDOW_SEC * SAMPLE_RATE)
    kernel = np.ones(win) / win
    integrated = np.convolve(squared, kernel, mode='same')

    if PRODUCE_GRAPHS:
        plt.figure(figsize=(15, 5))
        plt.plot(t_trim, integrated, color='darkblue', linewidth=1.5)
        plt.title('7. Moving Window Integration (one bump per beat)')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Amplitude')
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.show()

    # --- Peak detection ---
    min_dist = int(MIN_PEAK_DIST_SEC * SAMPLE_RATE)
    peaks, _ = find_peaks(integrated,
                          distance=min_dist,
                          height=PEAK_HEIGHT_FACTOR * integrated.max(),
                          prominence=PEAK_PROMINENCE_FACTOR * integrated.std())

    if PRODUCE_GRAPHS:
        plt.figure(figsize=(15, 5))
        plt.plot(t_trim, integrated, color='darkblue', linewidth=1.5, label='Integrated signal')
        plt.plot(t_trim[peaks], integrated[peaks], 'ro', ms=8, label=f'{len(peaks)} Detected Peaks')
        plt.title('8. Peak Detection on Integrated Signal')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Amplitude')
        plt.legend()
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.show()

    # --- Heart rate calculation ---
    if len(peaks) > 1:
        rr_ms = np.diff(peaks) / SAMPLE_RATE * 1000
        median_rr = np.median(rr_ms)
        valid = (rr_ms > RR_LOWER_FACTOR * median_rr) & (rr_ms < RR_UPPER_FACTOR * median_rr)
        rr_clean = rr_ms[valid]

        if len(rr_clean) > 0:
            hr_bpm = 60000 / rr_clean
            t_hr = t_trim[peaks[1:]][valid]
            mean_hr = np.mean(hr_bpm)
            rmssd = np.sqrt(np.mean(np.diff(rr_clean)**2))
            sdnn = np.std(rr_clean)  # Additional HRV metric
            perfusion_x10 = int((np.std(ir_bp) / np.mean(ir_trim)) * 1000)

            # Respiration rate estimate (FFT on low-freq PPG)
            fft = np.fft.rfft(ir_bp)
            freq = np.fft.rfftfreq(len(ir_bp), 1/SAMPLE_RATE)
            low_freq_mask = (freq > 0.1) & (freq < 0.5)
            resp_freq = freq[low_freq_mask][np.argmax(np.abs(fft[low_freq_mask]))]
            respiration = resp_freq * 60  # breaths/min

            print(f"\n=== FINAL METRICS ===")
            print(f"Mean HR: {mean_hr:.1f} bpm")
            print(f"RMSSD: {rmssd:.1f} ms")
            print(f"Detected peaks: {len(peaks)}")

            if PRODUCE_GRAPHS:
                plt.figure(figsize=(15, 5))
                plt.plot(t_hr, hr_bpm, color='green', linewidth=2)
                plt.title('9. Instantaneous Heart Rate')
                plt.xlabel('Time (seconds)')
                plt.ylabel('BPM')
                plt.ylim(40, 140)
                plt.grid(alpha=0.3)
                plt.tight_layout()
                plt.show()
        else:
            print("No valid RR intervals after cleaning")
    else:
        print("No peaks detected")

    # --- SpO2 estimate ---
    red_bp = bandpass_filter(red_trim - np.mean(red_trim))
    delay = int(SPO2_DELAY_SEC * SAMPLE_RATE)
    red_shifted = np.roll(red_bp, delay)
    red_shifted[:delay] = red_shifted[delay]

    def ac_dc(sig):
        sos = butter(4, 0.5, 'low', fs=SAMPLE_RATE, output='sos')
        low = sosfiltfilt(sos, sig)
        ac = sig - low
        return np.std(ac), np.mean(low)

    ac_ir, dc_ir = ac_dc(ir_bp)
    ac_red, dc_red = ac_dc(red_shifted)
    R = (ac_red / dc_red) / (ac_ir / dc_ir + 1e-8)
    spo2 = np.clip(110 - 25 * R, 85, 100)
    print(f"Estimated SpO2: {spo2:.1f}%")

    return {
        'mean_hr': mean_hr if 'mean_hr' in locals() else None,
        'rmssd': rmssd if 'rmssd' in locals() else None,
        'sdnn' : sdnn if 'sdnn' in locals() else None,
        'spo2': spo2,
        'perfusion_index_x10': perfusion_x10 if 'perfusion_x10' in locals() else None,
        'respiration_rate': respiration if 'respiration' in locals() else None,
        'peaks': peaks.tolist() if 'peaks' in locals() else []
    }

# ================================================================
# RUN WHEN EXECUTED DIRECTLY
# ================================================================
if __name__ == "__main__":
    PRODUCE_GRAPHS = True
    process_ppg_file('')