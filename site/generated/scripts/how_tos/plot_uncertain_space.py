"""# Create an uncertain space

## Problem

Uncertainty quantification requires defining a space of random variables
with specified probability distributions.

## Solution

Create a `ParameterSpace` and add random variables with `add_random_variable`.

## Step-by-step guide

The following steps create an uncertain space with three random variables.
"""

from gemseo.algos.parameter_space import ParameterSpace

# %%
# ### 1. Create an empty parameter space
uncertain_space = ParameterSpace()

# %%
# ### 2. Add random variables
#
# A standard Gaussian variable $u$:
uncertain_space.add_random_variable("u", "OTNormalDistribution")

# %%
# !!! note
#     OT stands for OpenTURNS, the UQ library used for sampling.

# %%
# A Gaussian variable $v$ with mean 2 and standard deviation 0.5:
uncertain_space.add_random_variable("v", "OTNormalDistribution", mu=2, sigma=0.5)

# %%
# A triangular variable $z$:
uncertain_space.add_random_variable(
    "z", "OTTriangularDistribution", minimum=-1.0, mode=0.5, maximum=1.0
)

# %%
# ### 3. Inspect the uncertain space
uncertain_space

# %%
# ## Summary
#
# Create a `ParameterSpace` and call `add_random_variable` for each random input.
# The default current value is set to the mean of each distribution.
#
# ## One step further
#
# For repeated use, subclass `ParameterSpace`:
class MyUncertainSpace(ParameterSpace):
    def __init__(self):
        super().__init__()
        self.add_random_variable("u", "OTNormalDistribution")
        self.add_random_variable("v", "OTNormalDistribution", mu=2, sigma=0.5)
        self.add_random_variable(
            "z", "OTTriangularDistribution", minimum=-1.0, mode=0.5, maximum=1.0
        )


uncertain_space = MyUncertainSpace()
uncertain_space
