import numpy as np
import pandas as pd
def get_weights(usage_profile: str, user_emphasis=None):
    base = {
        "gaming": {
            "cpu_tier": 0.25,
            "gpu_tier": 0.45,
            "ram": 0.15,
            "ssd_present": 0.05,
            "price_euro": 0.10,
        },
        "student": {
            "cpu_tier": 0.40,
            "gpu_tier": 0.15,
            "ram": 0.20,
            "ssd_present": 0.10,
            "price_euro": 0.15,
        },
        "basic": {
            "cpu_tier": 0.35,
            "gpu_tier": 0.05,
            "ram": 0.25,
            "ssd_present": 0.15,
            "price_euro": 0.20,
        },
        "workstation": {
            "cpu_tier": 0.30,
            "gpu_tier": 0.30,
            "ram": 0.20,
            "ssd_present": 0.10,
            "price_euro": 0.10,
        },
    }[usage_profile]

    if user_emphasis:
        for feature in user_emphasis:
            if feature in base:
                base[feature] += 0.1
        total = sum(base.values())
        base = {k: v / total for k, v in base.items()}

    return base

