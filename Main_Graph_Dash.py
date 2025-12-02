# -*- coding: utf-8 -*-
"""
Created on Tue Dec  2 11:20:06 2025

@author: rocio
"""
# -*- coding: utf-8 -*-
"""
Created on Tue Dec  2 11:20:06 2025
@author: rocio
"""

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import time

# ==== IMPORT YOUR MODULES ====
from HR_Processing import HRProcessor
from HRV_Processing import HRVProcessor
from User_Profile import UserProfile
from Training_Zone import zones_karvonen, zone_label
from VO2_Max_Estimator import vo2max_uth
from Heart_Rate_Sim import Simulated_HR


# ==== INITIALIZE EVERYTHING ====
user = UserProfile(23, 5, 4, "F", 200)
hr_resting = 62
hr_max = 192

hr_processor = HRProcessor()
hrv_processor = HRVProcessor()

sim_hr = Simulated_HR(start_hr=75)

# Buffers for graphs (5 min = 300s)
MAX_POINTS = 300
hr_history = []
rmssd_history = []
time_history = []

step = 0


# ==== DASH APP ====
app = dash.Dash(__name__)
app.title = "Heart Rate Live Dashboard"

app.layout = html.Div([
    html.H1("Heart Rate / HRV Dashboard", style={"textAlign": "center"}),

    html.Div(id="live-text", style={
        "fontSize": "22px",
        "margin": "15px",
        "textAlign": "center"
    }),

    dcc.Graph(id="hr-graph"),
    dcc.Graph(id="rmssd-graph"),

    dcc.Interval(id="interval", interval=1000, n_intervals=0)
])


@app.callback(
    [Output("live-text", "children"),
     Output("hr-graph", "figure"),
     Output("rmssd-graph", "figure")],
    [Input("interval", "n_intervals")]
)
def update_dashboard(n):
    global step

    # 1 — GET HEART RATE (simulated)
    hr_raw = sim_hr.workout(step)
    # hr_raw = sim_hr.resting()
    # hr_raw = ppg_reader.get_bpm()  # NEEDS TO BE CODED/REPLACED
    step += 1

    # 2 — PROCESS HR
    clean_hr = hr_processor.process(hr_raw)
    if clean_hr is None:
        return "Waiting for stable HR...", dash.no_update, dash.no_update

    # 3 — TRAINING ZONE
    zone = zones_karvonen(clean_hr, hr_max, hr_resting)
    zone_lbl = zone_label(zone)

    # 4 — HRV
    rr = hrv_processor.add_beat(timestamp=time.time())
    ## rr = hrv_processor.add_beat(timestamp=ppg_reader.timestamp) # use only if ppg gives peak timestamps
    rmssd_val = hrv_processor.get_rmssd()

    rmssd_display = "N/A" if rmssd_val is None else f"{rmssd_val:.2f}"

    # 5 — VO2 MAX
    vo2 = vo2max_uth(hr_max, hr_resting)

    # ===== HISTORY =====
    if len(time_history) >= MAX_POINTS:
        time_history.pop(0)
        hr_history.pop(0)
        rmssd_history.pop(0)

    time_history.append(n)
    hr_history.append(clean_hr)
    rmssd_history.append(rmssd_val if rmssd_val else 0)

    # ===== FIGURES =====
    hr_fig = go.Figure()
    hr_fig.add_trace(go.Scatter(x=time_history, y=hr_history, mode="lines"))
    hr_fig.update_layout(title="Heart Rate (BPM)", xaxis_title="Time (s)")

    rmssd_fig = go.Figure()
    rmssd_fig.add_trace(go.Scatter(x=time_history, y=rmssd_history, mode="lines"))
    rmssd_fig.update_layout(title="RMSSD (ms)", xaxis_title="Time (s)")

    # ===== TEXT =====
    text = (
        f"❤️ {clean_hr} BPM | "
        f"Zone: {zone_lbl} | "
        f"RMSSD: {rmssd_display} ms | "
        f"VO2max: {vo2:.2f} mL/kg/min"
    )

    return text, hr_fig, rmssd_fig


if __name__ == "__main__":
    app.run(debug=False)
