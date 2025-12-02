# main.py
"""
BioWatch v1 — Real-time PPG Emulator (Reads from PPG file)
Live Watch-style GUI + UDP JSON broadcast.
Works in parallel with a databasebase processor to publish metrics.
"""

import json
import queue
import socket
import threading
import time
from datetime import datetime

#from local
from constants import DEVICE_NAME, PLAYBACK_SPEED, WINDOW_SECONDS
from gui import WatchGUI
from sensor_simulator import SensorSimulator
from signal_processor import compute_metrics

class BioWatchEmulator:

    def __init__(self):
        # UDP broadcast
        self.udp_host = "127.0.0.1"     #Local Host
        self.udp_port = 4444
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.queue = queue.Queue(maxsize=2)

        print(f"\n{DEVICE_NAME} Emulator")
        print(f"   • Speed: {PLAYBACK_SPEED:.1f}x")
        print(f"   • Sending Live Metrics to : {self.udp_host}:{self.udp_port} :Localhost")
        print("   Close window to stop.\n")

    def start_processing(self):
        """Background thread: read sensor → compute metrics forever."""
        sensor = SensorSimulator()

        while True:
            chunk = sensor.get_next_chunk()
            metrics = compute_metrics(chunk)

            # Keep only the newest data
            try:
                self.queue.put_nowait(metrics)
            except queue.Full:
                try:
                    self.queue.get_nowait()  # drop old
                except:
                    pass
                self.queue.put_nowait(metrics)

            #mess with playback speed to go faster than 8 sec per datum
            time.sleep(WINDOW_SECONDS / PLAYBACK_SPEED)

    def gui_update_loop(self, gui: WatchGUI):
        """Pull latest metrics and update GUI + broadcast over UDP."""
        try:
            metrics = self.metrics_queue.get_nowait()
        except queue.Empty:
            metrics = None

        if metrics:
            gui.update(metrics)

            # This is the live JSON being sent over the network
            payload = {
                "device": DEVICE_NAME,
                "timestamp": datetime.now().isoformat(timespec="milliseconds"),
                "unix_timestamp": int(time.time()),
                **metrics #unpacks metrics
            }
            self.sock.sendto(
                json.dumps(payload).encode("utf-8"),
                (self.broadcast_ip, self.port)
            )

        # Refresh GUI at ~100 Hz
        gui.root.after(100, lambda: self.gui_updater(gui))

    def run(self):
        """Launch GUI and start everything."""
        gui = WatchGUI()
        # Start processing incoming PPG data
        threading.Thread(target=self.start_processing, daemon=True).start()
        # Start GUI updates after window appears
        gui.root.after(300, lambda: self.gui_update_loop(gui))
        gui.run()



if __name__ == "__main__":
    BioWatchEmulator().run()
