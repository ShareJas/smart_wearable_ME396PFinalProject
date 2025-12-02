# -*- coding: utf-8 -*-
"""
Created on Wed Nov 26 18:33:26 2025

@author: rocio
"""

# Imports
from HR_Processing import HRProcessor
from HRV_Processing import HRVProcessor
# from activity_classifier import ActivityClassifier
from User_Profile import UserProfile
from Training_Zone import zones_karvonen
from Training_Zone import zone_label
from VO2_Max_Estimator import vo2max_uth

# import time
# import math
from collections import deque
import random
import time


# Initialize modules
user = UserProfile(23, 5, 4, "F", 200)
hr_resting  = 62
hr_max = 192

# age = input("Age? ")
# feet = input("Feet: ")
# inches = input("Inches: ")
# sex = input("Sex? M or F: ")
# weight = input("Weight? ")

# user = UserProfile(age, feet, inches, sex, weight)

# hr_resting = user.resting_hr
# hr_max = user.hr_max

hr_processor = HRProcessor()
hrv_processor = HRVProcessor()
# classifier = ActivityClassifier()




# Allocate Buffers
# imu_buffer = deque(maxlen=window_size)
hr_buffer = deque(maxlen=300)   # 5 minutes at 1 Hz
rr_buffer = deque(maxlen=300)


from Heart_Rate_Sim import Simulated_HR
sim_hr = Simulated_HR(start_hr=75)


# Main Loop
step = 0

while True:
    # 1. Read heart rate
    # hr_raw = sim_hr.resting()    
    hr_raw = sim_hr.workout(step)

    # 2. Process HR
    clean_hr = hr_processor.process(hr_raw)
    if clean_hr is None:
        continue

    # 3. Determine training zone
    zone = zones_karvonen(clean_hr, hr_max, hr_resting)
    label = zone_label(zone)


    # 4. Compute additional metrics (optional)
    # e.g., add RR intervals for HRV
    rr = hrv_processor.add_beat(timestamp=time.time())
    rmssd_val = hrv_processor.get_rmssd() # in ms
    
    rmssd_display = f"{rmssd_val:.2f}" if rmssd_val is not None else "N/A"


    # VO2 max example
    vo2_max = vo2max_uth(hr_max, hr_resting)
    
    # 5. Update output
    print(f"❤️ {clean_hr} BPM | Zone: {label} | RMSSD: {rmssd_display} ms | VO2max: {vo2_max:.2f} mL/kg/min")

    # 6. Wait for the next reading
    step += 1
    time.sleep(1)  # simulate 1 Hz update rate

