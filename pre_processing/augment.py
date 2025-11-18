#!/usr/bin/env python
import re

import numpy as np
import pandas as pd

# coding: utf-8
# In[1]:
# TODO: change rupees to euro, standarize os(windows/linux/macos), add resolution_category (FHD, HD, 4K), seprate VRAM from gpu (if they start by a number then split it take first two then leave rest in gpu)
# model_name, brand, cpu, cpu_cores, cpu_threads, ram_gb, ssd_gb, hdd_gb, os, gpu, screen_size_in, resolution_w, resolution_h, resolution_type, spec_score, price_euro

df_raw = pd.read_csv("../data/modern_laptops.csv", index_col=0)
df_raw.head()


# In[2]:


df = df_raw.rename(
    columns={
        "processor_name": "cpu",
        "ram(GB)": "ram",
        "ssd(GB)": "ssd_gb",
        "Hard Disk(GB)": "hdd_gb",
        "Operating System": "os",
        "graphics": "gpu",
        "screen_size(inches)": "screen_size_in",
        "no_of_cores": "cpu_cores",
        "no_of_threads": "cpu_threads",
    }
)


# In[3]:


df = df.dropna(subset=["resolution (pixels)"])
df = df[df["gpu"].str.lower() != "missing"].reset_index(drop=True)


# In[4]:


df["resolution_w"] = (
    df["resolution (pixels)"].str.split("x").str[0].str.strip().astype(int)
)
df["resolution_h"] = (
    df["resolution (pixels)"].str.split("x").str[1].str.strip().astype(int)
)


# In[5]:


mask = df["resolution_w"] < df["resolution_h"]
df.loc[mask, ["resolution_w", "resolution_h"]] = df.loc[
    mask, ["resolution_h", "resolution_w"]
].values


# In[6]:


def get_resolution_type(w, h):
    if w >= 3840 and h >= 2160:
        return "4K"
    elif w >= 2560 and h >= 1440:
        return "QHD"
    elif w >= 1920 and h >= 1080:
        return "FHD"
    else:
        return "HD"


df["resolution_type"] = df.apply(
    lambda row: get_resolution_type(row["resolution_w"], row["resolution_h"]), axis=1
)


# In[7]:


df["os"] = df["os"].replace({"Ubuntu": "Linux"})


# In[8]:


df["price_euro"] = df["price_inIndianRupees"] * 0.0097


# In[9]:


def extract_vram(gpu_str):
    if pd.isna(gpu_str):
        return pd.Series([np.nan, np.nan])

    match = re.match(r"^(\d+\s*GB)\s+(.*)", gpu_str)
    if match:
        return pd.Series([match.group(1), match.group(2)])
    else:
        return pd.Series([np.nan, gpu_str])


df[["gpu_vram", "gpu"]] = df["gpu"].apply(extract_vram)


# In[10]:


df.drop(columns=["price_inIndianRupees", "resolution (pixels)"])


# In[11]:


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
        "gpu_vram",
        "screen_size_in",
        "resolution_w",
        "resolution_h",
        "resolution_type",
        "spec_score",
        "price_euro",
    ]
]


# In[12]:


df.to_csv("../data/laptops_cleaned.csv", index=False)
