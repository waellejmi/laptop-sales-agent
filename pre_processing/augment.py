#!/usr/bin/env python
# coding: utf-8

# In[1]:


# TODO: change rupees to euro, standarize os(windows/linux/macos), add resolution_category (FHD, HD, 4K), seprate VRAM from gpu
# reorder model_name, brand, cpu, cpu_cores, cpu_threads, ram_gb, ssd_gb, hdd_gb, os, gpu, screen_size_in, resolution_w, resolution_h, resolution_type, spec_score, price_euro
import pandas as pd

df_raw = pd.read_csv("../data/modern_laptops.csv",index_col=0)
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
    df["resolution (pixels)"]
    .str.split("x")
    .str[0]
    .str.strip()
    .astype(int)
)
df["resolution_h"] = (
    df["resolution (pixels)"]
    .str.split("x")
    .str[1]
    .str.strip()
    .astype(int)
)


# In[5]:


mask = df["resolution_w"] < df["resolution_h"]
df.loc[mask, ["resolution_w", "resolution_h"]] = df.loc[mask, ["resolution_h", "resolution_w"]].values


# In[6]:


def get_resolution_type(w, h):
    if w >= 3840 and h >= 2160: return "4K"
    elif w >= 2560 and h >= 1440: return "QHD"
    elif w >= 1920 and h >= 1080: return "FHD"
    else: return "HD"

df["resolution_type"] = df.apply(lambda row: get_resolution_type(row["resolution_w"], row["resolution_h"]), axis=1)


# In[7]:


df["os"] = df["os"].replace({"Ubuntu": "Linux", "DOS": "Linux"})


# In[8]:


import re

def normalize_cpu(cpu: str) -> str:
    cpu = cpu.strip()

    # Already normalized
    if cpu.startswith(("Intel ", "AMD ", "Apple ")):
        return cpu

    # Handle Intel generational format: "11th Gen Core i5" -> "Intel Core i5 11th Gen"
    gen_match = re.match(r'(\d+)(?:th|st|nd|rd)\s+Gen\s+(Core i[3579])', cpu, re.IGNORECASE)
    if gen_match:
        gen = f"{gen_match.group(1)}th Gen"
        tier = gen_match.group(2)
        # Ensure 'i' is lowercase: "Core I5" -> "Core i5"
        tier = re.sub(r'([iI])(\d)', r'i\2', tier)
        return f"Intel {tier} {gen}"

   # Intel: Celeron or Pentium
    if re.search(r'\b[Cc]eleron\b|\b[Pp]entium\b', cpu):
        return "Intel " + re.sub(r'^(Intel\s*)?', '', cpu)

    # AMD: Ryzen or Athlon 
    if re.search(r'\b[Rr]yzen\b|\b[Aa]thlon\b', cpu):
        return "AMD " + re.sub(r'^(AMD\s*)?', '', cpu)



    # If none match, return as is
    return cpu


# In[9]:


df['cpu'] = df['cpu'].apply(normalize_cpu)


# In[10]:


df["price_euro"] = df["price_inIndianRupees"] * 0.0097
df["price_euro"] = df["price_euro"].round(2)


# In[11]:


import numpy as np
import re

def extract_vram(gpu_str):
    if pd.isna(gpu_str):
        return pd.Series([np.nan, np.nan])

    match = re.match(r"^(\d+\s*GB)\s+(.*)", gpu_str)
    if match:
        return pd.Series([match.group(1), match.group(2)])
    else:
        return pd.Series([np.nan, gpu_str])

df[["gpu_vram", "gpu"]] = df["gpu"].apply(extract_vram)


# In[12]:


df.drop(columns=["price_inIndianRupees","resolution (pixels)"])


# In[13]:


df = df[[
    "model_name", "brand", "cpu", "cpu_cores", "cpu_threads",
    "ram", "ssd_gb", "hdd_gb", "os", "gpu", "gpu_vram",
    "screen_size_in", "resolution_w", "resolution_h",
    "resolution_type", "spec_score", "price_euro"
]]


# In[14]:


df.head()


# In[15]:


df.to_csv("../data/laptops_cleaned.csv",index=False)

