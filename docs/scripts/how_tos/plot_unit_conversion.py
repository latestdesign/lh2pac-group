"""# Convert units

## Problem

Use-case data are often expressed in common units,
but the simulator requires standard (SI) units.

## Solution

Use `convert_from` and `convert_to` from `gemseo_oad_training.unit`.

## Step-by-step guide

The following steps convert a time value from hours to seconds, then to minutes.
"""
from gemseo_oad_training.unit import convert_from
from gemseo_oad_training.unit import convert_to

# %%
# ### 1. Define a value in a common unit
time_in_hours = 1

# %%
# ### 2. Convert to standard units (seconds)
time_in_seconds = convert_from("h", time_in_hours)
time_in_seconds

# %%
# ### 3. Convert to another unit
time_in_minutes = convert_to("min", time_in_seconds)
time_in_minutes

# %%
# ## Summary
#
# Use `convert_from(unit, value)` to convert from a given unit to SI,
# and `convert_to(unit, si_value)` to convert from SI to a given unit.
#
# ## One step further
#
# !!! seealso
#     [The available units](https://gemseo.gitlab.io/dev/gemseo-oad-training/develop/reference/gemseo_oad_training/unit/)
