#!/usr/bin/env python
# coding: utf-8

#

# In[3]:


import pandas as pd

db = pd.read_csv("../data/games-system-requirements/all.csv")
# List all columns
db.head()


# In[8]:


print(db.columns)
# db = db.drop(columns=["File Size:", "OS:"])
db = db.rename(columns={"CPU:": "cpu", "Graphics Card:": "gpu", "Memory:": "ram"})
print(db.columns)


# In[12]:


db.to_csv("../data/games-system-requirements/game_db.csv", index=False)
