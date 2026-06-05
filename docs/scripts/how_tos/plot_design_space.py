"""# Create a design space

## Problem

An optimization problem requires a design space
to define the variables, their bounds, and their default values.

## Solution

Use the `DesignSpace` class and its `add_variable` method.

## Step-by-step guide

The following steps create a design space with three variables.
"""

from numpy import array

from gemseo.algos.design_space import DesignSpace

# %%
# ### 1. Create an empty design space
design_space = DesignSpace()

# %%
# ### 2. Add variables
#
# A variable $x$ without bounds or default value:
design_space.add_variable("x")

# %%
# A variable $y$ of dimension 2 with a lower bound and a default value:
design_space.add_variable("y", size=2, lower_bound=0.0, value=array([0.5, 0.75]))

# %%
# A variable $z$ with both bounds but no default value:
design_space.add_variable("z", lower_bound=-1.0, upper_bound=1.0)

# %%
# ### 3. Inspect the design space
design_space

# %%
# ## Summary
#
# Create a `DesignSpace`, then call `add_variable` for each variable.
#
# ## One step further
#
# For repeated use, subclass `DesignSpace`:
class MyDesignSpace(DesignSpace):
    def __init__(self):
        super().__init__(name="foo")
        self.add_variable("x")
        self.add_variable("y", size=2, lower_bound=0.0, value=array([0.5, 0.75]))
        self.add_variable("z", lower_bound=-1.0, upper_bound=1.0)


design_space = MyDesignSpace()
design_space
