# -*- coding: utf-8 -*-
"""
Created on Fri Nov 28 18:00:04 2025

@author: rocio
"""
import time
import math
from collections import deque

class HRVProcessor:
    def __init__(self, window_size=20):
        """
        window_size: number of RR intervals to keep for rolling HRV calculation
        """
        self.last_beat_time = None
        self.rr_intervals = deque(maxlen=window_size)  # stores RR in ms


    def add_beat(self, timestamp=None):
        """
        Called every time a beat is detected by the PPG peak detector.

        timestamp: optional external timestamp
                   if None, use time.time()
        """
        if timestamp is None:
            timestamp = time.time()

        # If this is the first beat, just store timestamp
        if self.last_beat_time is None:
            self.last_beat_time = timestamp
            return None  # can't compute RR yet

        # RR interval in milliseconds
        rr = (timestamp - self.last_beat_time) * 1000.0
        self.last_beat_time = timestamp

        # Filter unrealistic values (optional)
        if 300 < rr < 2000:  # typical RR physiological range (30–200 BPM)
            self.rr_intervals.append(rr)
            return rr
        else:
            return None

    def get_rmssd(self):
            ## Computes RMSSD (Root Mean Square of Successive Differences)
            if len(self.rr_intervals) < 2:
                return None
    
            diffs = []
            for i in range(1, len(self.rr_intervals)):
                diff = self.rr_intervals[i] - self.rr_intervals[i - 1]
                diffs.append(diff ** 2)
    
            mean_square = sum(diffs) / len(diffs)
            rmssd = math.sqrt(mean_square)
    
            return rmssd
