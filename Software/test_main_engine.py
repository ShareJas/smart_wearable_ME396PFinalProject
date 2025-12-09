# test_main_engine.py
# Minimal test runner — only starts processing thread + GUI

import threading
import subprocess
import time
import os
import json
from filtering import process_ppg_file
import pandas as pd

CSV_FILE = "latest_ppg_data.csv"
METRICS_FILE = "latest_metrics.json"
MIN_SAMPLES = 1000

def processing_thread():
    while True:
        if os.path.exists(CSV_FILE):
            try:
                df = pd.read_csv(CSV_FILE)
                if len(df) >= MIN_SAMPLES:
                    metrics = process_ppg_file(CSV_FILE)
                    with open(METRICS_FILE, "w") as f:
                        json.dump(metrics or {}, f)
            except Exception as e:
                print(f"Processing error: {e}")
        time.sleep(5)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Start replay in background
    threading.Thread(target=lambda: __import__('test_replay').asyncio.run(
        __import__('test_replay').replay_csv()), daemon=True).start()

    # Start processing and GUI
    threading.Thread(target=processing_thread, daemon=True).start()
    subprocess.run(["streamlit", "run", "gui.py"])