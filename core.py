import logging

import pandas as pd

logger = logging.getLogger(__name__)


def filter_laptops(
    model_name: str | None,
    brand: str | None,
    cpu: str | None,
    cpu_cores: int | None,
    cpu_threads: int | None,
    ram: int | None,
    ssd_gb: int | None,
    hdd_gb: int | None,
    os: str | None,
    gpu: str | None,
    gpu_vram_gb: int | None,
    screen_size_in: float | None,
    resolution_w: int | None,
    resolution_h: int | None,
    resolution_type: str | None,
    spec_score: int | None,
    price_euro: float | None,
):
    try:
        df = pd.read_csv("./data/laptops_cleaned.csv")

        mask = pd.Series(True, index=df.index)

        if model_name:
            mask = mask & (df["model_name"].str.contains(model_name, case=False))
        if brand:
            mask = mask & (df["brand"].str.lower() == brand.lower())
        # CPU
        if cpu:
            mask = mask & (df["cpu"].str.contains(cpu, case=False))
        if cpu_cores:
            mask = mask & (df["cpu_cores"] >= cpu_cores)
        if cpu_threads:
            mask = mask & (df["cpu_threads"] >= cpu_threads)
        # Memory
        if ram:
            mask = mask & (df["ram"] == ram)
        if ssd_gb:
            mask = mask & (df["ssd_gb"] >= ssd_gb)
        if hdd_gb:
            mask = mask & (df["hdd_gb"] >= hdd_gb)
        # GPU
        if gpu:
            mask = mask & (df["gpu"].str.contains(gpu, case=False))
        if gpu_vram_gb:
            mask = mask & (df["gpu_vram_gb"] >= gpu_vram_gb)
        # rest of the specs
        if screen_size_in:
            mask = mask & (df["screen_size_in"] >= screen_size_in)
        if resolution_w:
            mask = mask & (df["resolution_w"] >= resolution_w)
        if resolution_h:
            mask = mask & (df["resolution_h"] == resolution_h)

        VALID_RES = {"HD", "FHD", "QHD", "4K"}
        if resolution_type:
            if resolution_type.upper() not in VALID_RES:
                raise ValueError(f"Invalid resolution: {resolution_type}")
            mask &= df["resolution_type"] == resolution_type.upper()
        if price_euro:
            mask = mask & (df["price_euro"] <= price_euro)
        return df[mask]
    except FileNotFoundError:
        logger.error("Laptop dataset file not found.")


if __name__ == "__main__":
    df = filter_laptops(
        model_name=None,
        brand="Acer",
        cpu=None,
        cpu_cores=None,
        cpu_threads=None,
        ram=None,
        ssd_gb=None,
        hdd_gb=None,
        os=None,
        gpu=None,
        gpu_vram_gb=None,
        screen_size_in=None,
        resolution_w=None,
        resolution_h=None,
        resolution_type="fhd",
        spec_score=None,
        price_euro=1000.0,
    )
    print(df.head())
