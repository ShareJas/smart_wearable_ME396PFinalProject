# ble_connection.py
# Fixed: Prevents 'P' from being sent too soon after 'S'

import asyncio
import os
import pandas as pd
from bleak import BleakScanner, BleakClient
import time

SERVICE_UUID = "180D"
COMMAND_UUID = "2A37"
DATA_UUID = "2A38"

SAMPLES_PER_PACKET = 16
EXPECTED_PACKET_SIZE = 1 + SAMPLES_PER_PACKET * 8

CSV_FILE = "latest_ppg_data.csv"
CONNECTED_FLAG = "ble_connected.txt"
START_FLAG = "start.txt"
STOP_FLAG = "stop.txt"

seq_values = []
ir_values = []
red_values = []
last_saved = 0

def notification_handler(sender, data):
    global last_saved
    if len(data) != EXPECTED_PACKET_SIZE:
        print(f"[ERROR] Bad packet size: {len(data)}")
        return

    seq = data[0]
    offset = 1
    for _ in range(SAMPLES_PER_PACKET):
        ir = int.from_bytes(data[offset:offset+4], 'big')
        red = int.from_bytes(data[offset+4:offset+8], 'big')
        seq_values.append(seq)
        ir_values.append(ir)
        red_values.append(red)
        offset += 8

    current = len(ir_values)
    if current - last_saved >= 200:
        df_chunk = pd.DataFrame({
            'seq': seq_values[last_saved:current],
            'IR': ir_values[last_saved:current],
            'Red': red_values[last_saved:current]
        })
        mode = 'a' if os.path.exists(CSV_FILE) else 'w'
        df_chunk.to_csv(CSV_FILE, mode=mode, header=(mode=='w'), index=False)
        last_saved = current
        print(f"[CSV] Saved {current} samples")

async def start_ble_listener():
    global last_saved

    seq_values.clear()
    ir_values.clear()
    red_values.clear()
    last_saved = 0
    if os.path.exists(CSV_FILE):
        os.remove(CSV_FILE)

    print("Scanning for PPG_Sensor...")
    devices = await BleakScanner.discover(timeout=15.0)
    device = next((d for d in devices if d.name == "PPG_Sensor"), None)
    if not device:
        print("[ERROR] Device not found!")
        return

    client = BleakClient(device.address)
    try:
        await client.connect(timeout=20.0)
        print("[SUCCESS] BLE Connected")
        open(CONNECTED_FLAG, "w").close()

        await client.start_notify(DATA_UUID, notification_handler)

        print("[DEBUG] Waiting for start.txt...")
        while not os.path.exists(START_FLAG):
            await asyncio.sleep(0.5)
        os.remove(START_FLAG)
        start_time = time.time()
        await client.write_gatt_char(COMMAND_UUID, b'S')
        print("[SUCCESS] Sent 'S' – streaming started")

        # Wait for stop.txt, but ignore it for the first 30 seconds
        print("[DEBUG] Streaming – waiting for stop.txt (minimum 30s test)...")
        while True:
            if os.path.exists(STOP_FLAG):
                elapsed = time.time() - start_time
                if elapsed >= 30:  # Minimum test duration
                    os.remove(STOP_FLAG)
                    await client.write_gatt_char(COMMAND_UUID, b'P')
                    print("[SUCCESS] Sent 'P' – streaming stopped")
                    break
                else:
                    print(f"[DEBUG] Stop requested but only {elapsed:.1f}s elapsed – ignoring (min 30s)")
                    os.remove(STOP_FLAG)  # Remove premature flag
            await asyncio.sleep(0.5)

        # Final save
        if last_saved < len(ir_values):
            df_final = pd.DataFrame({
                'seq': seq_values[last_saved:],
                'IR': ir_values[last_saved:],
                'Red': red_values[last_saved:]
            })
            df_final.to_csv(CSV_FILE, mode='a', header=not os.path.exists(CSV_FILE), index=False)
            print(f"[CSV] Final save: {len(df_final)} samples")

    except Exception as e:
        print(f"[ERROR] BLE error: {e}")
    finally:
        await client.disconnect()
        if os.path.exists(CONNECTED_FLAG):
            os.remove(CONNECTED_FLAG)
        print("[DEBUG] BLE disconnected cleanly")

def start_ble_listener_thread():
    asyncio.run(start_ble_listener())