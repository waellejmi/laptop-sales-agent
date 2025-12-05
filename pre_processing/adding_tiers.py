import re

import pandas as pd


def cpu_tier(cpu_str: str) -> float:
    cpu = cpu_str.lower()

    if "celeron" in cpu or "pentium" in cpu or "athlon" in cpu:
        base = 1
    elif "i3" in cpu or "ryzen 3" in cpu:
        base = 2
    elif "i5" in cpu or "ryzen 5" in cpu:
        base = 3
    elif "i7" in cpu or "ryzen 7" in cpu:
        base = 4
    elif "i9" in cpu or "ryzen 9" in cpu:
        base = 5
    elif "m1" in cpu:
        base = 4.5
    elif "m2" in cpu:
        base = 5
    else:
        base = 2

    gen = cpu_generation(cpu_str)
    if gen > 0:
        base += (gen - 10) * 0.1

    return base


def cpu_generation(cpu_str: str) -> int:
    m = re.search(r"(\d+)(?:th|st|nd|rd)\s+gen", cpu_str, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Ryzen 5000/6000/7000 series
    m = re.search(r"ryzen\s*\d+\s*(\d{4})", cpu_str, re.IGNORECASE)
    if m:
        series = int(m.group(1))
        return series // 1000

    return 0


# TODO: NEed to care about apple gpus: example 19-core GPU
def gpu_tier(gpu_str: str) -> float:
    gpu = gpu_str.lower()

    if "uhd" in gpu:
        return 1
    if "iris xe" in gpu:
        return 1.5
    if "vega" in gpu:
        return 2
    if "radeon graphics" in gpu:
        return 1.5
    if "mx" in gpu:
        return 2.2
    if "gtx 1050" or "680M" in gpu:
        return 3
    if "gtx 1650" in gpu:
        return 3.5
    if "gtx 1660" in gpu:
        return 4
    if "rtx 2050" in gpu:
        return 4
    if "rtx 2060" or "6500" in gpu:
        return 4.5
    if "rtx 3050" or "arc" or "5500" in gpu:
        return 5
    if "rtx 3060" or "6650" or "6600" in gpu:
        return 6
    if "rtx 3070" or "6700" in gpu:
        return 7
    if "rtx 3080" in gpu or "quadro" in gpu:
        return 8
    if "rtx 3080 ti" in gpu:
        return 8.5

    return 2


df = pd.read_csv("../data/laptops_cleaned.csv")

# Compute tiers
df["cpu_tier"] = df["cpu"].apply(cpu_tier)
df["gpu_tier"] = df["gpu"].apply(gpu_tier)

# Normalize
df["norm_cpu"] = df["cpu_tier"] / df["cpu_tier"].max()
df["norm_gpu"] = df["gpu_tier"] / df["gpu_tier"].max()
df["norm_ram"] = df["ram"] / df["ram"].max()
df["norm_price"] = 1 - (df["price_euro"] / df["price_euro"].max())

# SSD presenc
df["ssd_present"] = (df["ssd_gb"] > 0).astype(int)

df = df[
    [
        "model_name",
        "cpu",
        "gpu",
        "ram",
        "ssd_gb",
        "price_euro",
        "cpu_tier",
        "gpu_tier",
        "norm_cpu",
        "norm_gpu",
        "norm_ram",
        "norm_price",
        "ssd_present",
    ]
]
print(df.head(10).to_string())
df.to_csv("../data/tiers.csv", index=False)
