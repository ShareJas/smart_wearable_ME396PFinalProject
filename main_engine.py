# main_engine.py
# Orchestrator: Starts BLE listener thread, processing thread, and GUI
# Fixed: Forces working directory so flag files are in the correct place

import threading
import subprocess
import time
import os
import pandas as pd

from ble_connection import start_ble_listener_thread
from filtering import process_ppg_file

CSV_FILE = "latest_ppg_data.csv"
METRICS_FILE = "latest_metrics.json"
MIN_SAMPLES_FOR_PROCESS = 1000  # ~5s at 200 Hz

def processing_thread():
    while True:
        try:
            if os.path.exists(CSV_FILE):
                df = pd.read_csv(CSV_FILE)
                if len(df) >= MIN_SAMPLES_FOR_PROCESS:
                    metrics = process_ppg_file(CSV_FILE)
                    with open(METRICS_FILE, "w") as f:
                        import json
                        json.dump(metrics or {}, f)
        except Exception as e:
            print(f"Processing error: {e}")
        time.sleep(5)

if __name__ == "__main__":
    # Force correct working directory so all files (CSV, flags) are in the same folder
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    threading.Thread(target=start_ble_listener_thread, daemon=True).start()
    threading.Thread(target=processing_thread, daemon=True).start()
    subprocess.run(["streamlit", "run", "gui.py"])