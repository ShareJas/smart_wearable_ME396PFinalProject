# gui.py
# Fixed: Start button works reliably using st.form
# No disappearing button, proper action on click

import streamlit as st
import json
import time
import os
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("BioWatch PPG Health Monitor")

# Initialize session state
if 'test_running' not in st.session_state:
    st.session_state.test_running = False
if 'metrics_history' not in st.session_state:
    st.session_state.metrics_history = []

# BLE connection status
ble_connected = os.path.exists("ble_connected.txt")
status_text = "Connected – Ready to Test" if ble_connected else "Waiting for Bluetooth connection..."
status_color = "green" if ble_connected else "orange"
st.markdown(f"**BLE Status:** <span style='color:{status_color}'>{status_text}</span>", unsafe_allow_html=True)

# User info
st.sidebar.header("User Information (for VO2 Max)")
age = st.sidebar.number_input("Age", 18, 100, 30)
sex = st.sidebar.selectbox("Sex", ["Male", "Female"])
weight_kg = st.sidebar.number_input("Weight (kg)", 40, 150, 70)
height_cm = st.sidebar.number_input("Height (cm)", 140, 220, 170)

# === Start Button using st.form (this fixes the disappearing issue) ===
if not st.session_state.test_running:
    with st.form("start_form"):
        st.write("### Ready to begin test")
        start_submitted = st.form_submit_button(
            "Start 1-Minute Test",
            disabled=not ble_connected,
            type="primary",
            use_container_width=True
        )
        if start_submitted:
            st.session_state.test_running = True
            st.session_state.start_time = time.time()
            st.session_state.metrics_history = []
            open("start.txt", "w").close()
            st.success("Test started – streaming from sensor")
            st.rerun()

# === Real-Time Test Display + Manual Stop Button ===
if st.session_state.test_running:
    elapsed = time.time() - st.session_state.start_time

    # Auto-stop at 60 seconds
    if elapsed >= 60:
        st.session_state.test_running = False
        open("stop.txt", "w").close()
        st.success("Test complete (auto-stop at 60s)")

    placeholder = st.empty()
    with placeholder.container():
        col_time, col_stop = st.columns([3, 1])
        col_time.header(f"Test Running – {elapsed:.1f}s / 60s")

        # Manual Stop button
        if col_stop.button("Stop Test", type="secondary", use_container_width=True):
            open("stop.txt", "w").close()
            st.session_state.test_running = False
            st.success("Test stopped manually")

        # Load metrics
        try:
            with open("latest_metrics.json", "r") as f:
                metrics = json.load(f)
            st.session_state.metrics_history.append(metrics)
        except:
            metrics = {}

        # Display all metrics (same as your full version)
        col1, col2, col3, col4 = st.columns(4)

        hr = metrics.get('mean_hr')
        col1.metric("Heart Rate", f"{hr:.1f} bpm" if isinstance(hr, (int, float)) and hr is not None else "— bpm")

        spo2 = metrics.get('spo2')
        col2.metric("SpO₂", f"{spo2:.1f}%" if isinstance(spo2, (int, float)) and spo2 is not None else "—%")

        rmssd = metrics.get('rmssd')
        col3.metric("RMSSD (HRV)", f"{rmssd:.1f} ms" if isinstance(rmssd, (int, float)) and rmssd is not None else "— ms")

        sdnn = metrics.get('sdnn')
        col4.metric("SDNN (HRV)", f"{sdnn:.1f} ms" if isinstance(sdnn, (int, float)) and sdnn is not None else "— ms")

        # Stress Level
        if isinstance(rmssd, (int, float)) and rmssd is not None:
            if rmssd > 50:
                stress_level = "Low"
            elif rmssd > 30:
                stress_level = "Medium"
            else:
                stress_level = "High"
        else:
            stress_level = "—"
        st.metric("Stress Level", stress_level)

        # Perfusion Index
        perfusion_raw = metrics.get('perfusion_index_x10')
        perfusion = perfusion_raw / 10 if isinstance(perfusion_raw, (int, float)) else None
        st.metric("Perfusion Index", f"{perfusion:.2f}" if perfusion is not None else "—")

        # Respiration Rate
        resp = metrics.get('respiration_rate')
        st.metric("Respiration Rate", f"{resp:.1f} br/min" if isinstance(resp, (int, float)) and resp is not None else "—")

    time.sleep(1)
    st.rerun()

# === Final Results ===
if not st.session_state.test_running and st.session_state.metrics_history:
    st.header("Final 1-Minute Test Results")
    final = st.session_state.metrics_history[-1]

    col1, col2, col3, col4 = st.columns(4)
    hr = final.get('mean_hr')
    col1.metric("Average HR", f"{hr:.1f} bpm" if isinstance(hr, (int, float)) else "— bpm")

    spo2 = final.get('spo2')
    col2.metric("SpO₂", f"{spo2:.1f}%" if isinstance(spo2, (int, float)) else "—%")

    rmssd = final.get('rmssd')
    col3.metric("RMSSD", f"{rmssd:.1f} ms" if isinstance(rmssd, (int, float)) else "— ms")

    sdnn = final.get('sdnn')
    col4.metric("SDNN", f"{sdnn:.1f} ms" if isinstance(sdnn, (int, float)) else "— ms")

    # VO2 Max Estimate
    if isinstance(hr, (int, float)) and hr > 0:
        factor = 15.3 if sex == "Male" else 14.7
        vo2_max = factor * (220 - age) / hr
        st.metric("Estimated VO2 Max", f"{vo2_max:.1f} mL/kg/min")
    else:
        st.metric("Estimated VO2 Max", "— (no HR)")

    # HR Trend Graph
    hr_list = [m['mean_hr'] for m in st.session_state.metrics_history if isinstance(m.get('mean_hr'), (int, float))]
    if hr_list:
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(hr_list, color='green', linewidth=2.5, marker='o')
        ax.set_title("Heart Rate Trend During Test")
        ax.set_xlabel("Update (~every 5s)")
        ax.set_ylabel("BPM")
        ax.grid(alpha=0.3)
        st.pyplot(fig)