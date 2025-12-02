# sensor_simulator.py
import numpy as np
import pickle
from constants import SAMPLES_PER_WINDOW, DEFAULT_RECORDING, SAMPLE_RATE_HZ

class SensorSimulator:
    def __init__(self):
        with open(DEFAULT_RECORDING, "rb") as f: data = pickle.load(f)
        #list file data in a flattened numpy array, init pos to 0 
        self.signal = np.array(data["signal"], dtype=float).flatten()
        self.pos = 0

    def get_next_chunk(self):
        # Get next chunk, loop forever when we reach the end
        if self.pos + SAMPLES_PER_WINDOW >= len(self.signal):
            print("Reached end → looping from start\n"); self.pos = 0
        #Get next chunk
        chunk = self.signal[self.pos : self.pos + SAMPLES_PER_WINDOW]
        self.pos += SAMPLES_PER_WINDOW
        return chunk