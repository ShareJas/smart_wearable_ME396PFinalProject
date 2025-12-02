# -*- coding: utf-8 -*-
"""
Created on Wed Nov 26 22:07:58 2025

@author: rocio
"""


## Creating the user profile

class UserProfile:
    def __init__(self, age, feet, inches, sex, weight):
        self.age = int(age)
        self.sex = sex.strip().upper()
        self.weight = int(weight)

        # Height stored both in original units and meters
        self.feet = int(feet)
        self.inches = int(inches)
        total_inches = self.feet * 12 + self.inches
        self.height_m = total_inches * 0.0254

        ## Estimating Maximum Heart Rate with the Tanaka Formula
        ## Underestimates HR_Max in men by 1 bpm
        ## Overestimates HR_Max in women by 5 bpm
        self.hr_max = 208 - (0.7 * self.age)

        self.resting_hr = 70

    def __str__(self):
        return (
            f"--- User Profile ---\n"
            f"Age: {self.age}\n"
            f"Weight:  {self.weight} lbs\n"
            f"Height: {self.feet} ft {self.inches} in ({self.height_m:.2f} m)\n"
            f"Sex: {self.sex}\n"
            f"Estimated Max HR: {self.hr_max:.1f} bpm\n"
            f"Estimated Resting HR: {self.resting_hr:.1f} bpm\n"
        )


# age = input("Age? ")
# feet = input("Feet: ")
# inches = input("Inches: ")
# sex = input("Sex? M or F: ")
# weight = input("Weight? ")

# user = UserProfile(age, feet, inches, sex, weight)

# print(user)

