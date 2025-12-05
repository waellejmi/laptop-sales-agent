import re

import pandas as pd


def cpu_generation(cpu_str: str) -> int:
    s = (cpu_str or "").lower()
    m = re.search(r"(\d+)(?:th|st|nd|rd)\s+gen", s)
    if m:
        return int(m.group(1))
    m = re.search(r"ryzen\s*[^\d]*(\d{3,4})", s)
    if m:
        num = m.group(1)
        return int(num[0])
    m = re.search(r"(?:i3|i5|i7|i9)[^\d]*(\d{3,4})", s)
    if m:
        num = m.group(1)
        return int(num[:2])
    return 0


def cpu_tier(cpu_str: str) -> float:
    s = (cpu_str or "").lower()
    if "celeron" in s:
        base = 1.0
    elif "pentium" in s or "athlon" in s:
        base = 1.25
    elif re.search(r"\bi3\b", s) or "ryzen 3" in s:
        base = 2.0
    elif re.search(r"\bi5\b", s) or "ryzen 5" in s:
        base = 3.0
    elif re.search(r"\bi7\b", s) or "ryzen 7" in s:
        base = 4.0
    elif re.search(r"\bi9\b", s) or "ryzen 9" in s:
        base = 4.6
    elif "m1 max" in s or "m2 max" in s:
        base = 5.2
    elif "m1 pro" in s or "m2 pro" in s:
        base = 4.9
    elif "m2" in s:
        base = 4.25
    elif "m1" in s:
        base = 4.0
    else:
        base = 2.0
    gen = cpu_generation(cpu_str or "")
    if gen > 0:
        base += max((gen - 10) * 0.08, -0.5)
    return round(base, 3)


def gpu_tier(gpu_str: str) -> float:
    s = (gpu_str or "").lower()

    if any(k in s for k in ("uhd", "intel uhd", "intel uhd graphics")):
        return 1.0
    if "iris xe" in s:
        return 1.5
    if "vega" in s and "radeon" in s:
        return 1.8
    if "radeon graphics" in s and "rx" not in s:
        return 1.6

    nvidia = {
        "gtx 1050": 2.5,
        "gtx 1650": 3.2,
        "gtx 1660": 3.9,
        "rtx 2050": 4.2,
        "rtx 3050": 4.9,
        "rtx 3050 ti": 5.1,
        "rtx 3060": 6.0,
        "rtx 3070": 7.2,
        "rtx 3070 ti": 7.6,
        "rtx 3080": 8.6,
        "rtx 3080 ti": 9.2,
        "rtx 4060": 6.5,
        "rtx 4070": 8.0,
        "rtx 4080": 9.0,
        "rtx 4090": 9.8,
    }
    for key, val in nvidia.items():
        if key in s:
            return val

    amd = {
        "rx 5500m": 3.5,
        "rx 5600m": 4.0,
        "rx 6500m": 4.4,
        "rx 6600m": 6.0,
        "rx 6700m": 7.0,
        "rx 6800m": 7.6,
        "rx 6800s": 7.5,
    }
    for key, val in amd.items():
        if key in s:
            return val

    intel_arc = {
        "a350m": 3.5,
        "a370m": 4.0,
        "a550m": 5.0,
        "a730m": 6.0,
        "a770m": 7.0,
    }
    for key, val in intel_arc.items():
        if key in s:
            return val

    if "mx" in s and ("mx" in s and re.search(r"mx\s*\d+", s)):
        return 2.2

    m = re.search(r"(\d+)\s*-\s*core|\b(\d+)\s*core\b", s)
    if m:
        core = int(m.group(1) or m.group(2))
        if core >= 60:
            return 8.5
        if core >= 40:
            return 7.0
        if core >= 30:
            return 5.5
        if core >= 20:
            return 4.5
        if core >= 8:
            return 3.0

    if "quadro" in s or "rtx a" in s:
        if "t" in s or "t1000" in s:
            return 3.5
        return 6.5

    return 1.5


if __name__ == "__main__":
    df = pd.read_csv("../data/laptops_cleaned.csv")
    df["cpu_tier"] = df["cpu"].fillna("").apply(cpu_tier)
    df["gpu_tier"] = df["gpu"].fillna("").apply(gpu_tier)
    df["norm_cpu"] = df["cpu_tier"] / df["cpu_tier"].max()
    df["norm_gpu"] = df["gpu_tier"] / df["gpu_tier"].max()
    df["norm_ram"] = df["ram"].fillna(0) / df["ram"].max()
    df["norm_price"] = 1 - (
        df["price_euro"].fillna(df["price_euro"].max()) / df["price_euro"].max()
    )
    df["ssd_present"] = (df["ssd_gb"].fillna(0) > 0).astype(int)
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
    df.to_csv("../data/tiers.csv", index=False)
    print(df.head(10).to_string())
