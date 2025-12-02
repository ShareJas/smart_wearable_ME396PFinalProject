# gui.py
# Clean Apple-Watch-style BioWatch GUI – works 100%

import tkinter as tk
from datetime import datetime
from constants import BLACK, GREEN, RED, CYAN, GRAY, ORANGE, DARK_GRAY


class WatchGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BioWatch v1")
        self.root.geometry("400x800")
        self.root.configure(bg=BLACK)
        self.root.resizable(False, False)

        # Top heart ring
        self.canvas = tk.Canvas(self.root, width=360, height=360, bg=BLACK, highlightthickness=0)
        self.canvas.pack(pady=(60, 20))

        # Big HR
        self.hr_big = tk.Label(self.root, text="--", font=("Helvetica", 96, "bold"), fg=GREEN, bg=BLACK)
        self.hr_big.pack()

        self.bpm_label = tk.Label(self.root, text="bpm", font=("Helvetica", 24), fg=GRAY, bg=BLACK)
        self.bpm_label.pack(pady=(0, 20))

        # SpO2
        self.spo2_label = tk.Label(self.root, text="SpO₂ --%", font=("Helvetica", 40, "bold"), fg=CYAN, bg=BLACK)
        self.spo2_label.pack(pady=(10, 20))

        # Info section
        self.info_frame = tk.Frame(self.root, bg=BLACK)
        self.info_frame.pack(pady=20)

        self.rmssd_label = tk.Label(self.info_frame, text="rMSSD --ms", font=("Helvetica", 18), fg=GRAY, bg=BLACK)
        self.rmssd_label.pack()

        self.resp_label = tk.Label(self.info_frame, text="Resp --", font=("Helvetica", 18), fg=GRAY, bg=BLACK)
        self.resp_label.pack(pady=(8, 0))

        self.conf_label = tk.Label(self.info_frame, text="Confidence --%", font=("Helvetica", 18), fg=ORANGE, bg=BLACK)
        self.conf_label.pack(pady=(8, 0))

        # Bottom status
        self.status = tk.Label(self.root, text="Place finger • Starting...", font=("Helvetica", 14), fg=GRAY, bg=BLACK)
        self.status.pack(side="bottom", pady=30)

        self.draw_heart_ring(0)

    def draw_heart_ring(self, hr: int):
        self.canvas.delete("all")
        cx, cy, r = 180, 180, 165

        # Background ring
        self.canvas.create_arc(cx-r, cy-r, cx+r, cy+r, start=0, extent=359.9,
                               outline=DARK_GRAY, width=28, style="arc")

        if hr > 0:
            angle = min(180, (hr / 200.0) * 180)
            color = GREEN if hr < 100 else ORANGE if hr < 130 else RED
            self.canvas.create_arc(cx-r, cy-r, cx+r, cy+r, start=90, extent=angle,
                                   outline=color, width=32, style="arc")

        # Heart icon + HR text
        self.canvas.create_text(cx, cy-20, text="♡", fill=GRAY, font=("Apple Color Emoji", 64))
        self.canvas.create_text(cx, cy+30, text="HR", fill=GRAY, font=("Helvetica", 20))

    def update(self, metrics: dict):
        if not metrics or not metrics.get("valid"):
            self.hr_big.config(text="--", fg=GRAY)
            self.spo2_label.config(text="SpO₂ --%", fg=GRAY)
            self.rmssd_label.config(text="rMSSD --ms", fg=GRAY)
            self.resp_label.config(text="Resp --", fg=GRAY)
            self.conf_label.config(text="Confidence --%", fg=ORANGE)
            self.status.config(text="No signal • Check placement", fg=RED)
            self.draw_heart_ring(0)
            return

        hr = metrics["hr_bpm"]
        spo2 = metrics["spo2"]
        rmssd = metrics["rmssd"]
        conf = metrics["confidence"]
        resp = metrics.get("resp_rate")

        # HR
        self.hr_big.config(text=str(hr), fg=GREEN if hr < 100 else RED)
        self.draw_heart_ring(hr)

        # SpO2
        self.spo2_label.config(
            text=f"SpO₂ {spo2}%",
            fg=CYAN if spo2 >= 95 else ORANGE if spo2 >= 90 else RED
        )

        # Bottom info
        self.rmssd_label.config(text=f"rMSSD {rmssd}ms", fg=GRAY)
        resp_text = f"{resp:.1f}/min" if resp else "--"
        self.resp_label.config(text=f"Resp {resp_text}", fg=GRAY)

        conf_color = GREEN if conf >= 70 else ORANGE if conf >= 40 else RED
        self.conf_label.config(text=f"Confidence {conf}%", fg=conf_color)

        now = datetime.now().strftime("%H:%M:%S")
        self.status.config(text=f"{now} • Live • 8s window", fg=GREEN)

    # This was missing → fixed!
    def run(self):
        self.root.mainloop()