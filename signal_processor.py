# signal_processor.py
# Clean, readable, Pan-Tompkins-style PPG processing for HR, HRV, SpO2

# Pan-Tompkins algorithm adapted for PPG (Pan & Tompkins, 1985)
# Reference: IEEE Trans. Biomed. Eng., 32(3), 230–236

# --- Using np to manage data and scipy for signal processing ------------------------------------
import numpy as np
from scipy.signal import butter, sosfiltfilt, find_peaks
from constants import SAMPLE_RATE_HZ as FS
from constants import SAMPLES_PER_WINDOW

def bandpass_filter(raw_ppg: np.ndarray) -> np.ndarray:
    """
    Apply a zero-phase bandpass filter (0.7 to 10 Hz) to isolate the pulsatile component.
    
    This is the first and most critical step of the Pan-Tompkins algorithm
    
    Why these exact frequencies?
        • 0.7 Hz  → Removes very slow trends (breathing, baseline wander)
        • 10 Hz   → Removes high-frequency noise (muscle artifact, 50/60Hz mains, sensor jitter)
        • Result  → Only the clean cardiac pulse remains (~0.7 - 5 Hz, suitable for HR 42- 300BPM) 
    
    What is sosfiltfilt and butterworth:
    
    """
    # Step 1: Remove DC offset (resp for ~90 % of signal value)
    ppg_AC = raw_ppg - raw_ppg.mean()
    
    # Step 2: 4th-order Butterworth bandpass, zero-phase implementation
    sos = butter( N=4, Wn=[0.7, 10.0], btype='band',fs=FS, output='sos')
    
    #Step 3: Apply forward and backward filtering on the AC data 
    return sosfiltfilt(sos, ppg_AC)

def pan_tompkins_transform(ppg_filtered: np.ndarray) -> np.ndarray:
    """
    Apply the classic Pan-Tompkins nonlinear transformation:
        derivative → squaring → moving window integration
    
    This is Steps 2-4 of the original Pan-Tompkins algorithm (1985)

    -Derivative (np.gradient)
       → Turns each cardiac pulse into a sharp positive/negative spike

    -Squaring (deriv ** 2)
       → Makes the entire signal positive and dramatically amplifies slopes

    -Moving Window Integration (120 ms)
       → Smooths the spiky squared-derivative into clean, rounded peaks
       → One clear peak per heartbeat → perfect for find_peaks()
       → Window duration 120 ms is ideal for adults 
       (covers HR from ~40 to 150 bpm without double-counting or missing beats)
    """
    # Step 1: Derivative
    derivative = np.gradient(ppg_filtered)
    
    # Step 2: Squaring
    squared = derivative ** 2
    
    # Step 3: Moving window integration (120 ms = typical pulse width) (61 samples at 512 Hz)
    integration_window_samples = int(0.120 * FS)
    window_kernel = np.ones(integration_window_samples) / integration_window_samples
    
    # mode='same' preserves original length and alignment
    return np.convolve(squared, window_kernel, mode='same')

def extract_peaks(transformed):
    """
    This is **Step 5** of the Pan-Tompkins algorithm: peak detection
    on the integrated squared-derivative waveform.

    Parameters used:
        - distance = 0.35 s 
          → Prevents double-detection on wide or noisy peaks
        
        - height = 15% of global max  → Ignores tiny noise peaks even if prominent
        
        - prominence = 8% of standard deviation  
          → Ensures peaks stand out clearly from background fluctuations
    """
    min_dist = int(0.35 * FS)  # ~300ms min RR
    peaks, _ = find_peaks( transformed, distance=min_dist,
        height=0.15 * transformed.max(), prominence=0.08 * transformed.std()
    )
    return peaks

def clean_rr_intervals(peaks: np.ndarray) -> np.ndarray:
    """
    Convert detected peak locations → RR intervals

    What is an RR interval?
        → Time between two consecutive heartbeats (R-peak to R-peak in ECG,
          pulse peak to pulse peak in PPG).
            • Normal range: ~600-1200 ms

    Cleaning rule (standard in research & medical devices):
        Keep only RR intervals that are within ±40% of the current median
        → i.e. 0.6 x median < RR < 1.67 x median
        → Diretcly taken from Pan Tompkins
    """
    rr_ms = np.diff(peaks) / FS * 1000.0
    if len(rr_ms) < 3: return np.array([])
    valid = (rr_ms > 0.6 * np.median(rr_ms)) & (rr_ms < 1.67 * np.median(rr_ms))
    return rr_ms[valid]

def estimate_spo2(ppg_clean: np.ndarray) -> int:
    """
    Estimate blood oxygen saturation (SpO₂) using the classic 'ratio-of-ratios' method.

    Important:
    The data only has a green PPG channel — real pulse oximeters use green + red/infrared.
    We simulate the missing red channel by slightly time-shifting the green signal by 20 ms
    (20 ms delay ≈ typical pulse transit time difference between wavelengths).

    Steps:
        1. Simulate red signal by delaying green PPG by ~20 ms
        2. Extract AC (pulsatile) and DC (baseline) components of both
        3. Compute ratio-of-ratios (R)
        4. Apply standard empirical formula
        5. Add realistic noise and clamp to medical range (85 - 100%)
    """
    #simulated red dataset
    delay = int(0.02 * FS)
    red_sim = np.roll(ppg_clean, delay)
    red_sim[:delay] = red_sim[delay]

    #produces ac, dc, values from a dataset
    def ac_dc(sig):
        low = sosfiltfilt(butter(4, 0.5, 'low', fs=FS, output='sos'), sig)
        ac = sig - low
        dc = low.mean()
        return np.std(ac), max(dc, 1e-8)

    ac_g, dc_g = ac_dc(ppg_clean)
    ac_r, dc_r = ac_dc(red_sim)
    R = (ac_r / dc_r) / (ac_g / dc_g)
    spo2 = int(110 - 25 * R)
    return np.clip(spo2 + np.random.randint(-2, 3), 85, 100)

def compute_metrics(ppg_chunk: np.ndarray) -> dict:
    clean           = bandpass_filter(ppg_chunk)
    transformed     = pan_tompkins_transform(clean)
    peaks           = extract_peaks(transformed)
    rr_clean        = clean_rr_intervals(peaks)
    hr_bpm          = int(round((60_000) / np.median(rr_clean)))    #60 s , * 1000 ms 
    rmssd           = round(float(np.sqrt(np.mean(np.diff(rr_clean)**2))), 1)
    spo2            = estimate_spo2(clean)
    confidence      = min(100, max(0, len(rr_clean) * 9 - 15))      #appox of good data
    perfusion_x10   = int((ppg_chunk.std() / max(ppg_chunk.mean(), 1e-8)) * 1000)

    return {
        "valid": True,
        "hr_bpm": hr_bpm,
        "rmssd": rmssd,
        "spo2": spo2,
        "confidence": confidence,
        "perfusion_index_x10": perfusion_x10,
        "mean_rr_ms": int(np.median(rr_clean)),
        "rr_intervals": (rr_clean[-16:].astype(int).tolist() + [0]*16)[:16]
    }