import re

import pandas as pd


def detect_apple(cpu_str: str):
    s = (cpu_str or "").lower()
    m = re.search(r"(m\d)\s*(pro|max)?", s)
    if not m:
        m = re.search(r"apple\s*(m\d)\s*(pro|max)?", s)
    if not m:
        return None, None
    family = m.group(1)
    variant = m.group(2)
    c = re.search(r"(\d+)-core", s)
    cores = int(c.group(1)) if c else None
    return (family, variant), cores


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
    apple, cores = detect_apple(cpu_str)

    if apple[0] if apple else False:
        family, variant = apple
        if family == "m1":
            if variant == "max":
                base = 5.2
            elif variant == "pro":
                base = 4.9
            else:
                base = 4.0
        elif family == "m2":
            if variant == "max":
                base = 5.45
            elif variant == "pro":
                base = 5.1
            else:
                base = 4.25
        else:
            base = 4.0
        if cores:
            base += (cores - 8) * 0.05
        return round(base, 3)

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
    s = gpu_str.lower()

    if any(k in s for k in ("uhd", "intel uhd", "intel uhd graphics")):
        return 1.0
    if "iris xe" in s:
        return 1.5
    if "vega" in s and "radeon" in s:
        return 1.8
    if "radeon graphics" in s and "rx" not in s:
        return 1.6

    nvidia = {
        "1050": 2.5,
        "1650": 3.2,
        "1660": 3.9,
        "2050": 4.2,
        "3050 ti": 5.1,
        "3050": 4.9,
        "3060": 6.0,
        "3070": 7.2,
        "3070 ti": 7.6,
        "3080 ti": 9.2,
        "3080ti": 9.2,
        "3080": 8.6,
        "A5500": 8.65,
    }
    for key, val in nvidia.items():
        if key in s:
            return val

    amd = {
        "rx 550": 2.5,
        "rx 5500m": 3.5,
        "rx 5600m": 4.0,
        "rx 6500m": 4.4,
        "rx 6600m": 4.8,
        "rx 6650m": 5.5,
        "rx 6700s": 6.4,
        "rx 6700m": 7,
        "rx 6800s": 7.4,
        "rx 6800m": 7.6,
    }
    for key, val in amd.items():
        if key in s:
            return val

    intel_arc = {
        "a350m": 3.5,
        "a370m": 4.0,
    }
    for key, val in intel_arc.items():
        if key in s:
            return val

    mx = {
        "mx330": 2,
        "mx350": 2.2,
        "mx450": 2.3,
        "mx550": 2.4,
        "mx570": 2.5,
    }
    for key, val in mx.items():
        if key in s:
            return val

    quadro = {
        "t500": 2.2,
        "t600": 2.8,
        "t1200": 3.5,
    }
    for key, val in quadro.items():
        if key in s:
            return val

    m = re.search(r"(\d+)\s*-\s*core|\b(\d+)\s*core\b", s)
    if m:
        core = int(m.group(1) or m.group(2))
        if core >= 30:
            return 5.5
        if core >= 20:
            return 4.5
        if core >= 8:
            return 3.0

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
            "brand",
            "cpu",
            "cpu_cores",
            "cpu_threads",
            "ram",
            "ssd_gb",
            "hdd_gb",
            "os",
            "gpu",
            "gpu_vram_gb",
            "screen_size_in",
            "resolution_w",
            "resolution_h",
            "resolution_type",
            "spec_score",
            "price_euro",
            "cpu_tier",
            "gpu_tier",
            "ssd_present",
            # normalized scores
            "norm_cpu",
            "norm_gpu",
            "norm_ram",
            "norm_price",
        ]
    ]
    df.to_csv("../data/laptops_enhanced.csv", index=False)
    print(df.head(10).to_string())
