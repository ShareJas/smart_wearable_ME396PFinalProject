# -*- coding: utf-8 -*-
"""
Live Heart Metrics Monitor - Dash App
Created on Tue Dec 2 2025
@author: jgmor (fixed)
"""

from HR_Processing import HRProcessor
from HRV_Processing import HRVProcessor
from User_Profile import UserProfile
from Training_Zone import zones_karvonen, zone_label
from VO2_Max_Estimator import vo2max_uth
from Heart_Rate_Sim import Simulated_HR

import plotly.graph_objs as go
import time
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State

# ---------------------------
# Initialize processors & simulation
# ---------------------------

hr_processor = HRProcessor()
hrv_processor = HRVProcessor()
sim_hr = Simulated_HR(start_hr=75)

# Buffers for graphs (5 min = 300s)
MAX_POINTS = 300
hr_history = []
rmssd_history = []
time_history = []

# ---------------------------
# Dash App Layout
# ---------------------------

app = dash.Dash(__name__)

app.layout = html.Div(
    style={"fontFamily": "Arial", "padding": "40px", "textAlign": "center"},
    children=[
        html.H2("Live Heart Metrics Monitor"),

        # -------- USER INPUT SECTION --------
        html.Div([
            html.H3("User Settings"),

            html.Label("Age"),
            dcc.Input(id="age", type="number", value=23, style={"marginBottom": "10px"}),
            html.Br(),

            html.Label("Weight (kg)"),
            dcc.Input(id="weight", type="number", value=68, style={"marginBottom": "10px"}),
            html.Br(),

            html.Label("Height (ft):"),
            dcc.Input(id="feet", type="text", value="5", style={"marginBottom": "10px"}),
            html.Br(),

            html.Label("Height (in):"),
            dcc.Input(id="inches", type="text", value="9", style={"marginBottom": "10px"}),
            html.Br(),

            html.Label("Sex (M/F)"),
            dcc.Input(id="sex", type="text", value="F", style={"marginBottom": "10px"}),
            html.Br(),

            html.Label("Fitness Level (1–5)"),
            dcc.Input(id="fitness_level", type="number", value=3, style={"marginBottom": "20px"}),
            html.Br(),

            html.Button("Show HR Info", id="show_hr_btn", n_clicks=0),

        ], style={
            "width": "400px",
            "margin": "0 auto",
            "padding": "20px",
            "border": "1px solid #ccc",
            "borderRadius": "10px"
        }),

        html.Hr(),

        # LIVE OUTPUT
        html.Div(id="live-output", style={"marginTop": "40px"}),
        html.Div(id="hr_output"),
        dcc.Graph(id="hr-graph"),
        dcc.Graph(id="rmssd-graph"),

        # AUTO UPDATE
        dcc.Interval(id="interval-component", interval=1000, n_intervals=0)
    ]
)

# ---------------------------
# Single unified callback (returns 4 outputs)
# ---------------------------
@app.callback(
    [
        Output("live-output", "children"),
        Output("hr_output", "children"),
        Output("hr-graph", "figure"),
        Output("rmssd-graph", "figure")
    ],
    [
        Input("interval-component", "n_intervals"),
        Input("show_hr_btn", "n_clicks")
    ],
    [
        State("age", "value"),
        State("weight", "value"),
        State("feet", "value"),
        State("inches", "value"),
        State("sex", "value"),
        State("fitness_level", "value")
    ]
)
def update_metrics(n_intervals, n_clicks, age, weight, feet, inches, sex, fitness_level):
    """
    Single callback to update text outputs and both graphs.
    Uses n_intervals as the time axis (seconds since app start).
    """
    try:
        # Validate / coerce inputs
        try:
            feet_i = int(feet)
        except Exception:
            feet_i = 0
        try:
            inches_i = int(inches)
        except Exception:
            inches_i = 0

        user = UserProfile(age=age, feet=feet_i, inches=inches_i, sex=sex, weight=weight)
        hr_max = getattr(user, "hr_max", None)
        hr_resting = getattr(user, "resting_hr", None)

        # Simulate HR using n_intervals as step (keeps simulation deterministic)
        step = int(n_intervals) if n_intervals is not None else 0
        hr_raw = sim_hr.workout(step)

        # Process HR
        clean_hr = hr_processor.process(hr_raw)
        if clean_hr is None:
            # Return placeholders for all outputs (must return 4 outputs)
            return ("Waiting for valid HR...", "", dash.no_update, dash.no_update)

        # Training Zone (safely handle missing hr_max/hr_resting)
        try:
            zone = zones_karvonen(clean_hr, hr_max, hr_resting)
            label = zone_label(zone)
        except Exception:
            label = "N/A"

        # HRV - add beat (pass timestamp). 
        try:
            _ = hrv_processor.add_beat(timestamp=time.time())
            rmssd_val = hrv_processor.get_rmssd()  # expected in ms or None
        except TypeError as te:
            raise RuntimeError("HRVProcessor methods appear overwritten (float object not callable). Check HRV_Processing.py") from te

        rmssd_display = f"{rmssd_val:.2f}" if rmssd_val is not None else "N/A"

        # VO2 Max (safe fallback)
        try:
            vo2_max = vo2max_uth(hr_max, hr_resting)
            vo2_display = f"{vo2_max:.2f}"
        except Exception:
            vo2_display = "N/A"

        # Update histories (use n_intervals as x axis)
        if len(time_history) >= MAX_POINTS:
            time_history.pop(0)
            hr_history.pop(0)
            rmssd_history.pop(0)

        time_history.append(step)
        hr_history.append(clean_hr)
        rmssd_history.append(rmssd_val if (rmssd_val is not None) else 0)

        # Build figures
        hr_fig = go.Figure()
        hr_fig.add_trace(go.Scatter(x=list(time_history), y=list(hr_history), mode="lines", name="BPM"))
        hr_fig.update_layout(title="Heart Rate (BPM)", xaxis_title="Time (s)", yaxis_title="BPM", margin={"l": 40, "r": 10, "t": 40, "b": 30})

        rmssd_fig = go.Figure()
        rmssd_fig.add_trace(go.Scatter(x=list(time_history), y=list(rmssd_history), mode="lines", name="RMSSD"))
        rmssd_fig.update_layout(title="RMSSD (ms)", xaxis_title="Time (s)", yaxis_title="ms", margin={"l": 40, "r": 10, "t": 40, "b": 30})

        # Text outputs
        live_output = f"❤️ {clean_hr} BPM | Zone: {label}"
        hr_output = f"RMSSD: {rmssd_display} ms | VO2max: {vo2_display} mL/kg/min"

        return (live_output, hr_output, hr_fig, rmssd_fig)

    except Exception as e:
        # Always return four items (use dash.no_update for figures when error occurs)
        err_text = f"Error: {e}"
        return (err_text, "", dash.no_update, dash.no_update)

# ---------------------------
# Run server
# ---------------------------

if __name__ == "__main__":
    app.run(debug=True, port=8054)
