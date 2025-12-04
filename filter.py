import logging

import pandas as pd

logger = logging.getLogger(__name__)


def filter_laptops(
    model_name: str | None = None,
    brand: str | None = None,
    cpu: str | None = None,
    cpu_cores: int | None = None,
    cpu_threads: int | None = None,
    ram: int | None = None,
    ssd_gb: int | None = None,
    hdd_gb: int | None = None,
    os: str | None = None,
    gpu: str | None = None,
    gpu_vram_gb: int | None = None,
    screen_size_in: float | None = None,
    resolution_w: int | None = None,
    resolution_h: int | None = None,
    resolution_type: str | None = None,
    spec_score: int | None = None,
    price_euro: float | None = None,
    sort_by: str | None = None,
    top_k: int | None = None,
    dataset_path: str = "./data/laptops_cleaned.csv",
):
    try:
        df = pd.read_csv(dataset_path)
    except FileNotFoundError:
        logger.error(f"Laptop dataset file not found at {dataset_path}")
        return pd.DataFrame()

    mask = pd.Series(True, index=df.index)
    # String Matching : model_name, cpu, gpu ,os
    if model_name:
        mask = mask & df["model_name"].str.contains(model_name, case=False)
    if cpu:
        mask = mask & (df["cpu"].str.contains(cpu, case=False))
    if gpu:
        mask = mask & (df["gpu"].str.contains(gpu, case=False))
    if os:
        mask = mask & (df["os"].str.contains(os, case=False))
    # Exact matching : brand ,resolution_type
    if brand:
        mask = mask & (df["brand"].str.lower() == brand.lower())
    if resolution_type:
        VALID_RES = {"HD", "FHD", "QHD", "4K"}
        if resolution_type.upper() not in VALID_RES:
            raise ValueError(f"Invalid resolution: {resolution_type}")
        mask &= df["resolution_type"] == resolution_type.upper()

    # Numeric matching MIN
    if cpu_cores:
        mask = mask & (df["cpu_cores"] >= cpu_cores)
    if cpu_threads:
        mask = mask & (df["cpu_threads"] >= cpu_threads)
    if gpu_vram_gb:
        mask = mask & (df["gpu_vram_gb"] >= gpu_vram_gb)
    if ram:
        mask = mask & (df["ram"] >= ram)
    if ssd_gb:
        mask = mask & (df["ssd_gb"] >= ssd_gb)
    if hdd_gb:
        mask = mask & (df["hdd_gb"] >= hdd_gb)
    if screen_size_in:
        mask = mask & (df["screen_size_in"] >= screen_size_in)
    if resolution_w:
        mask = mask & (df["resolution_w"] >= resolution_w)
    if resolution_h:
        mask = mask & (df["resolution_h"] >= resolution_h)

    #  Numeric matching MAX
    if price_euro:
        mask = mask & (df["price_euro"] <= price_euro)

    result = df[mask].copy()

    if sort_by and sort_by in result.columns:
        result = result.sort_values(by=sort_by, ascending=False)
    elif sort_by:
        logger.warning(f"sort_by column '{sort_by}' not found in dataset")

    if top_k and len(result) > top_k:
        result = result.head(top_k)

    return result.reset_index(drop=True)


if __name__ == "__main__":
    df = filter_laptops(price_euro=500, os="linux", sort_by="spec_score", top_k=1)
    print(df.to_string())
    df = filter_laptops(brand="ASUS", gpu="RTX 3080", ram=16, resolution_h=1440)
    df = filter_laptops(
        resolution_type="4K", price_euro=1500.0, sort_by="spec_score", top_k=3
    )
    df = filter_laptops(
        model_name="Microsoft ",
        cpu_cores=8,
        resolution_type="fhd",
        os="windows",
        top_k=2,
        sort_by="price_euro",
    )
