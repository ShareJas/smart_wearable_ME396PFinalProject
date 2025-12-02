# -*- coding: utf-8 -*-
"""
Created on Fri Nov 28 13:53:10 2025

@author: rocio
"""

class HRProcessor:
    def __init__(self, window_size=5, max_jump=25):
        """
        window_size: moving average window
        max_jump: maximum allowed sudden change in BPM
        """
        self.window_size = window_size
        self.max_jump = max_jump
        self.buffer = []
        self.last_valid_hr = None

    def reject_unrealistic(self, hr):
        ## Remove impossible HR readings.
        if hr is None:
            return None
        if hr < 30 or hr > 220:
            return None
        return hr

    def reject_spikes(self, hr):
        ## Remove sudden big jumps common in MAX30102.
        if self.last_valid_hr is None:
            return hr

        if abs(hr - self.last_valid_hr) > self.max_jump:
            # Too large to be real, discard
            return None

        return hr

    def smooth(self, hr):
        ## Moving average smoothing.
        self.buffer.append(hr)
        if len(self.buffer) > self.window_size:
            self.buffer.pop(0)
        return sum(self.buffer) / len(self.buffer)

    def process(self, hr):
        """
        Full HR processing pipeline:
        1. reject unrealistic
        2. reject spikes
        3. smooth
        Returns: cleaned HR or None
        """
        hr = self.reject_unrealistic(hr)
        if hr is None:
            return None

        hr = self.reject_spikes(hr)
        if hr is None:
            return None

        hr = self.smooth(hr)
        self.last_valid_hr = hr

        return int(hr)
