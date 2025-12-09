# Overview:

By: Rocio Bautista, Jesus Morales, Jason Sharer

This project, BioWatch PPG Health Monitor, is a real-time photoplethysmography (PPG) system designed to connect to a hardware sensor (specifically the MAX30102) via Bluetooth Low Energy (BLE), collect IR and Red light data, process it to extract vital signs (e.g., heart rate, SpO2, HRV metrics), and display results through an interactive Streamlit GUI. The system is built in Python and integrates asynchronous BLE communication, signal processing with SciPy and NumPy, and a web-based interface for user interaction.
The core files include:

        ble_connection.py: Handles BLE scanning, connection, data streaming, and command sending to the sensor.
        filtering.py: Processes the collected PPG data using a modified Pan-Tompkins algorithm, including gap interpolation, bandpass filtering, peak detection, and metric calculation (e.g., mean HR, RMSSD, SDNN, SpO2, perfusion index, respiration rate).
        gui.py: Streamlit-based GUI for starting/stopping tests, displaying real-time metrics, and showing final results with trends.
        main_engine.py: Orchestrates the system by launching BLE listener and processing threads alongside the GUI.
        test_replay.py and test_main_engine.py: For offline testing by replaying pre-recorded data from test_data.csv.

This system was developed to demonstrate real-time biomedical signal processing and has been refined from an initial faulty demo to a robust, integrated application.

# Key Features:

- Real-Time BLE Streaming: Connects to a PPG sensor (named "PPG_Sensor") using Bleak library, sending commands ('S' for start, 'P' for pause) and receiving notifications with sequenced packets (16 samples/packet at roughly 200 Hz).

- Advanced Signal Processing: Implements a PPG-adapted Pan-Tompkins algorithm with bandpass filtering (0.7-10 Hz), moving window integration, and peak detection tuned to avoid false beats. Includes gap reconstruction via cubic interpolation based on sequence numbers, removal of signal error through trimming (1s start, 2s end), and additional metrics like SDNN (HRV variability), perfusion index, and respiration rate estimation via FFT.

- Interactive GUI: Streamlit interface with user inputs (age, gender, weight, height for VO2 Max), real-time metric displays (HR, SpO2, RMSSD, SDNN, stress level, perfusion, respiration), trend graphs, and reliable start/stop controls using forms to prevent UI glitches.

- Modular Design: Uses file-based flags (e.g., start.txt, stop.txt, ble_connected.txt) for inter-process coordination between BLE, processing, and GUI threads. Data is saved incrementally to CSV for efficiency.

- Test Mode: Offline simulation replays data from test_data.csv (~20 seconds of data at 200 Hz, approximately 4000 samples) in chunks, mimicking real-time streaming without hardware.


# How to Use
## Normal Mode (With Hardware)

Ensure the PPG sensor is powered on and discoverable.

Run python main_engine.py.
This starts the BLE listener thread (scans and connects), processing thread (runs filtering every 5s on accumulated data), and launches the Streamlit GUI.

In the browser (Streamlit opens automatically), enter user info in the sidebar.

Once "BLE Status: Connected – Ready to Test" appears, click "Start 1-Minute Test".
The system creates start.txt, triggering BLE to send 'S' and begin streaming.
Data accumulates in latest_ppg_data.csv, processed to latest_metrics.json, and displayed in real-time.

The test auto-stops at 60s or manually via "Stop Test" (creates stop.txt, sends 'P' after min duration).

View final results, including averages, VO2 Max, and HR trend graph.

## Test Mode (Offline Simulation)

Place test_data.csv in the project directory (pre-recorded PPG data for ~20s simulation).

Run python test_main_engine.py.
This launches test_replay.py in a background thread, which signals "connected" via flag, waits for start, and appends data chunks (200 samples/~1s) to latest_ppg_data.csv with async sleeps to simulate 200 Hz real-time.
Processing and GUI run as in normal mode, updating metrics every 5s.

Follow GUI steps as above; the system uses replayed data instead of live BLE.
Unique: Async chunking ensures realistic timing, allowing GUI to show progressive metrics without hardware.


This dual-mode setup allows development/testing without the sensor, while normal mode uses actual hardware.

# Complex Challenges Solved

- BLE Reliability: Initial issues with premature 'P' commands (stop) after 'S' (start) were fixed by enforcing a 30-second minimum duration, ignoring early stop flags. Async sleeps and timeouts handle flaky connections.

- Data Integrity: PPG packets can have gaps due to BLE drops; solved via sequence-based reconstruction, NaN-filling missing slots, and cubic interpolation for continuous timelines.

- Signal Artifacts: Startup/end noise trimmed programmatically; peak detection tuned with min distance (0.65s) and prominence/height factors to ignore dicrotic notches while capturing true beats.

- Real-Time Coordination: Disconnected components (BLE, processing, GUI) integrated via threading and file flags for IPC, avoiding shared memory issues in async/sync mix.

- Processing Efficiency: Chunked CSV saves (every 200 samples) and periodic filtering (every 5s) balance real-time updates with performance, handling ~12,000 samples/minute.

- SpO2 Accuracy: Phase delay compensation (0.02s shift) and AC/DC ratio calculation for reliable estimates.

# Improvements from Faulty First Demo
The initial demo suffered from disconnected software components and a failed GUI presentation during class:

- Disconnected Elements: BLE, filtering, and GUI ran independently, leading to sync issues (e.g., starting test without connection). Now unified in main_engine.py with threads and flags for seamless orchestration.

- GUI Failures: Start button disappeared or didn't trigger reliably; fixed using Streamlit forms (st.form) for persistent, action-on-submit behavior. Added explicit BLE status checks to disable buttons when not connected.
- Presentation Reliability: Faulty demo used simulated data only, causing skepticism; evolved to real hardware integration for authentic results, with test mode as a fallback for demos.
- Overall Robustness: From crashes on bad packets or gaps to resilient handling (e.g., size checks, interpolation), the system now runs end-to-end without intervention.

- Hardware Implementation and Learning about Real-Time Systems
Unlike early simulations (e.g., synthetic sine waves), we implemented actual hardware integration:

- PPG Sensor Connection: Uses a physical "PPG_Sensor" device with custom UUIDs for commands and data. Streams binary packets via BLE notifications, parsed into IR/Red values—demonstrating real-world wireless data acquisition.

- Real-Time Aspects: Learned async programming (asyncio for non-blocking I/O), threading for concurrent BLE/processing/GUI, and handling variable latencies (e.g., ~80ms/packet). File-based IPC taught simple, reliable coordination in distributed systems.

- Insights Gained: Real-time challenges, built understanding of embedded systems, signal integrity, and biomedical applications. Transition from simulation to hardware highlighted noise/artifacts not present in synthetic data, improving algorithm robustness.


 This hands-on approach produced genuine results (e.g., HR ~73.7 bpm, SpO2 ~97.8% from partial test data), far more credible than simulations.

# Future Extensions

Add more sensors or multi-device support.
Enhance ML-based artifact rejection.
Deploy as a web app with user authentication.