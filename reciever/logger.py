# logger.py — Pure silent logger (perfect for web backend)
import json
import socket
import sqlite3

DB_FILE = "biowatch_recordings.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS readings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at         TEXT    DEFAULT CURRENT_TIMESTAMP,
    device              TEXT,
    timestamp           TEXT,
    unix_ts             REAL,
    valid               INTEGER,
    hr_bpm              INTEGER,
    spo2                INTEGER,
    rmssd               REAL,
    confidence          INTEGER,
    perfusion_index_x10 INTEGER,
    mean_rr_ms          INTEGER,
    rr_intervals        TEXT,
    raw_json            TEXT
)
""")
conn.commit()

print(f"Logger running → saving to {DB_FILE}")
print("Waiting for BioWatch data on UDP 4444...")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 4444))

while True:
    data, _ = sock.recvfrom(4096)
    try:
        msg = json.loads(data.decode("utf-8"))
        cur.execute("""
            INSERT INTO readings (
                device, timestamp, unix_ts, valid,
                hr_bpm, spo2, rmssd, confidence,
                perfusion_index_x10, mean_rr_ms, rr_intervals, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            msg.get("device"),
            msg.get("timestamp"),
            msg.get("unix_ts"),
            1 if msg.get("valid") else 0,
            msg.get("hr_bpm"),
            msg.get("spo2"),
            msg.get("rmssd"),
            msg.get("confidence"),
            msg.get("perfusion_index_x10"),
            msg.get("mean_rr_ms"),
            json.dumps(msg.get("rr_intervals", [])),
            json.dumps(msg)
        ))
        conn.commit()

    except Exception as e:
        pass