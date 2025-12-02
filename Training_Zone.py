# -*- coding: utf-8 -*-
"""
Created on Thu Nov 27 18:56:27 2025

@author: rocio
"""
def zones_karvonen(hr, hr_max, rhr):
    hrr = hr_max - rhr
    intensity = (hr - rhr) / hrr * 100

    ## Warm-up zone: 50-60%
    if intensity < 60:
        return 1

    ## Aerobic/Endurance zone: 60-70%
    elif intensity < 70:
        return 2

    ## Moderate/Cardio zone: 70-80%
    elif intensity < 80:
        return 3

    ## Redline zone: 80-90%
    elif intensity < 90:
        return 4

    ## Anaerobic/Peak zone: 90-100%
    else:
        return 5

# Labeling the Training Zone
def zone_label(zone):
    labels = {
        1: "Warm-Up",
        2: "Endurance/Aerobic",
        3: "Moderate/Cardio",
        4: "Redline",
        5: "Peak/Anaerobic"
    }
    return labels.get(zone, "Unknown")

