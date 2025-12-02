# -*- coding: utf-8 -*-
"""
Created on Mon Dec  1 19:58:49 2025

@author: rocio
"""

def vo2max_uth(hr_max, rhr):
    ## VO2max estimate in (mL/kg/min)
    vo2_max = 15.3 * (hr_max / rhr)
    return vo2_max
