# main.py
"""
BioWatch v1 — Real-time PPG Emulator (Reads from PPG file)
Live Watch-style GUI + UDP JSON broadcast.
Works in parallel with a database processor to publish metrics.
"""

import json
import queue
import socket
import threading
import time
import numpy as np  # <-- needed for the quick fix
from datetime import datetime

# from local
from constants import DEVICE_NAME, PLAYBACK_SPEED, WINDOW_SECONDS
from gui import WatchGUI
from sensor_simulator import SensorSimulator
from signal_processor import compute_metrics


class BioWatchEmulator:
    def __init__(self):
        # UDP Configuration
        self.udp_host = "127.0.0.1"          # Use "255.255.255.255" for real network broadcast
        self.udp_port = 4444

        # UDP socket with broadcast enabled
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self.queue = queue.Queue(maxsize=2)

        print(f"\n{DEVICE_NAME} Emulator Started")
        print(f"   • Playback Speed: {PLAYBACK_SPEED:.1f}x")
        print(f"   • Broadcasting Live Metrics → {self.udp_host}:{self.udp_port}")
        print("   • Close window to stop.\n")

    def start_processing(self):
        """Background thread: read sensor → compute metrics forever."""
        sensor = SensorSimulator()

        while True:
            chunk = sensor.get_next_chunk()
            metrics = compute_metrics(chunk)

            # Keep only the latest metrics
            try:
                self.queue.put_nowait(metrics)
            except queue.Full:
                try:
                    self.queue.get_nowait()
                except queue.Empty:
                    pass
                self.queue.put_nowait(metrics)

            time.sleep(WINDOW_SECONDS / PLAYBACK_SPEED)

    def gui_update_loop(self, gui: WatchGUI):
        """Pull latest metrics → update GUI + broadcast over UDP."""
        try:
            metrics = self.queue.get_nowait()
        except queue.Empty:
            metrics = None

        if metrics:
            gui.update(metrics)

            payload = {
                "device": DEVICE_NAME,
                "timestamp": datetime.now().isoformat(timespec="milliseconds"),
                "unix_timestamp": int(time.time() * 1000),
                **metrics
            }

            try:
                # ONE-LINE FIX: handles np.int64, np.float64, etc.
                self.sock.sendto(
                    json.dumps(
                        payload,
                        default=lambda x: float(x) if isinstance(x, (np.integer, np.floating)) else str(x)
                    ).encode("utf-8"),
                    (self.udp_host, self.udp_port)
                )
            except Exception as e:
                print(f"UDP send failed: {e}")

        # ~100 Hz GUI refresh
        gui.root.after(10, lambda: self.gui_update_loop(gui))

    def run(self):
        """Start everything and run the GUI."""
        gui = WatchGUI()

        threading.Thread(target=self.start_processing, daemon=True).start()

        gui.root.after(300, lambda: self.gui_update_loop(gui))
        gui.run()

        # Cleanup
        print("\nBioWatch Emulator stopped.")
        self.sock.close()


if __name__ == "__main__":
    BioWatchEmulator().run()