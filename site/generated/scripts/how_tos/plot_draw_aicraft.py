"""# Draw an aircraft

## Problem

Visualizing aircraft geometry helps to understand
how design parameters affect the shape.

## Solution

Call `draw_aircraft` with an `AircraftConfiguration` object.

## Step-by-step guide

The following steps draw the default aircraft
and two variants with different wing areas.
"""
from gemseo_oad_training.utils import AircraftConfiguration
from gemseo_oad_training.utils import draw_aircraft

# %%
# ### 1. Draw the default aircraft
draw_aircraft()

# %%
# ### 2. Draw variants with a custom wing area
configuration_1 = AircraftConfiguration(area=200, name="Conf 1", color="b")
draw_aircraft(configuration_1, title="Area = 200")

# %%
configuration_2 = AircraftConfiguration(area=80, name="Conf 2", color="r")
draw_aircraft(configuration_2, title="Area = 80")

# %%
draw_aircraft(configuration_1, configuration_2, title="Comparison")

# %%
# ## Summary
#
# Call `draw_aircraft()` for the default geometry.
# Pass an `AircraftConfiguration` to override design parameters.
