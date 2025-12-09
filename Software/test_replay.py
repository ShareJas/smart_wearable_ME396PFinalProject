# test_replay.py
# Ultra-simple CSV replay for testing: streams test_data.csv in real-time chunks
# No BLE simulation, no packet reconstruction needed

import asyncio
import os
import pandas as pd
import time

CSV_FILE = "test_data.csv"
CONNECTED_FLAG = "ble_connected.txt"
START_FLAG = "start.txt"
STOP_FLAG = "stop.txt"
SAMPLE_RATE = 200
CHUNK_SIZE = 200  # Save every ~1 second of data (200 samples at 200Hz)

async def replay_csv(csv_path="test_data.csv"):
    # Signal that we're "connected"
    open(CONNECTED_FLAG, "w").close()

    # Clear any old data
    if os.path.exists(CSV_FILE):os.remove(CSV_FILE)

    print(f"[REPLAY] Loading {csv_path}...")
    df = pd.read_csv(csv_path)
    total_samples = len(df)
    print(f"[REPLAY] Loaded {total_samples} samples ({total_samples/SAMPLE_RATE:.1f}s)")

    print("[REPLAY] Waiting for start.txt...")
    while not os.path.exists(START_FLAG):
        await asyncio.sleep(0.5)
    os.remove(START_FLAG)
    print("[REPLAY] Starting replay...")

    start_time = time.time()
    saved = 0

    for i in range(0, total_samples, CHUNK_SIZE):
        # Check for manual stop
        if os.path.exists(STOP_FLAG):
            elapsed = time.time() - start_time
            if elapsed >= 30:  # Respect minimum duration like real system
                os.remove(STOP_FLAG)
                print(f"[REPLAY] Stopped at {elapsed:.1f}s")
                break
            else:
                os.remove(STOP_FLAG)

        chunk = df.iloc[i:i + CHUNK_SIZE]
        mode = 'a' if saved > 0 else 'w'
        chunk.to_csv(CSV_FILE, mode=mode, header=(mode == 'w'), index=False)
        saved += len(chunk)
        print(f"[REPLAY] Streamed {saved}/{total_samples} samples")

        # Simulate real-time playback
        await asyncio.sleep(CHUNK_SIZE / SAMPLE_RATE)

    # Final chunk if any
    if saved < total_samples:
        final_chunk = df.iloc[saved:]
        final_chunk.to_csv(CSV_FILE, mode='a', header=False, index=False)
        print(f"[REPLAY] Final chunk: {len(final_chunk)} samples")

    if os.path.exists(CONNECTED_FLAG):
        os.remove(CONNECTED_FLAG)
    print("[REPLAY] Finished")

if __name__ == "__main__":
    asyncio.run(replay_csv())