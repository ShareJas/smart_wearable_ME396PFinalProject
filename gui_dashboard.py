# -*- coding: utf-8 -*-

"""
Live Heart Metrics Monitor - Dash App
Created on Tue Dec 2 2025
@author: jgmor
"""

from HR_Processing import HRProcessor
from HRV_Processing import HRVProcessor
from User_Profile import UserProfile
from Training_Zone import zones_karvonen, zone_label
from VO2_Max_Estimator import vo2max_uth
from Heart_Rate_Sim import Simulated_HR

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
global_step = {"value": 0}

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

    # AUTO UPDATE  
    dcc.Interval(id="interval-component", interval=1000, n_intervals=0)  
]  
)

# ---------------------------

# Live metrics callback

# ---------------------------
@app.callback(
[Output("live-output", "children"),
Output("hr_output", "children")],
[Input("interval-component", "n_intervals"),
Input("show_hr_btn", "n_clicks")],
[State("age", "value"),
State("weight", "value"),
State("feet", "value"),
State("inches", "value"),
State("sex", "value"),
State("fitness_level", "value")]
)
def update_metrics(n_intervals, n_clicks, age, weight, feet, inches, sex, fitness_level):
    try:
    # Rebuild user profile
        user = UserProfile(age, feet, inches, sex, weight)
        hr_max = user.hr_max
        hr_resting = user.resting_hr
    
    
        # Simulate HR
        step = global_step["value"]
        hr_raw = sim_hr.workout(step)
        global_step["value"] += 1
    
        clean_hr = hr_processor.process(hr_raw)
        if clean_hr is None:
            return ("Waiting for valid HR...", "")
    
        # Training Zone
        zone = zones_karvonen(clean_hr, hr_max, hr_resting)
        label = zone_label(zone)
    
        # HRV - pass R-R interval in seconds instead of timestamp
        # rr = hrv_processor.add_beat(60 / clean_hr if clean_hr else 0)
        # rmssd_val = hrv_processor.get_rmssd()
        # rmssd_display = f"{rmssd_val:.2f}" if rmssd_val else "N/A"
        rr = hrv_processor.add_beat(timestamp=time.time())
        rmssd_val = hrv_processor.get_rmssd() # in ms
        
        rmssd_display = f"{rmssd_val:.2f}" if rmssd_val is not None else "N/A"
    
        # VO2 Max
        vo2_max = vo2max_uth(hr_max, hr_resting)
    
        # Outputs
        live_output = f"❤️ {clean_hr} BPM | Zone: {label}"
        hr_output = f"RMSSD: {rmssd_display} ms | VO2max: {vo2_max:.1f} mL/kg/min"
    
        return (live_output, hr_output)
    
    except Exception as e:
        # Catch and display any callback errors
        return (f"Error: {e}", "")

# @app.callback(
# [Output("live-output", "children"),
# Output("hr_output", "children")],
# [Input("interval-component", "n_intervals"),
# Input("show_hr_btn", "n_clicks")],
# [State("age", "value"),
# State("weight", "value"),
# State("feet", "value"),
# State("inches", "value"),
# State("sex", "value"),
# State("fitness_level", "value")]
# )
# def update_metrics(n_intervals, n_clicks, age, weight, feet, inches, sex, fitness_level):
#     # User profile
#     user = UserProfile(age, feet, inches, sex, weight)
#     hr_max = user.hr_max()
#     hr_resting = user.hr_resting()
    
#     # Simulate HR  
#     step = global_step["value"]  
#     hr_raw = sim_hr.workout(step)  
#     global_step["value"] += 1  
    
#     clean_hr = hr_processor.process(hr_raw)  
#     if clean_hr is None:  
#         return ("Waiting for valid HR...", "")  
    
#     # Training Zone  
#     zone = zones_karvonen(clean_hr, hr_max, hr_resting)  
#     label = zone_label(zone)  
    
#     # HRV  
#     rr = hrv_processor.add_beat(timestamp=time.time())  
#     rmssd_val = hrv_processor.get_rmssd()  
#     rmssd_display = f"{rmssd_val:.2f}" if rmssd_val else "N/A"  
    
#     # VO2 Max  
#     vo2_max = vo2max_uth(hr_max, hr_resting)  
    
#     # Outputs  
#     live_output = f"❤️ {clean_hr} BPM | Zone: {label}"  
#     hr_output = f"RMSSD: {rmssd_display} ms | VO2max: {vo2_max:.1f} mL/kg/min"  
    
#     return (live_output, hr_output)  


# ---------------------------

# Run server

# ---------------------------

if __name__ == "__main__":
    app.run(debug=True, port=8054)
