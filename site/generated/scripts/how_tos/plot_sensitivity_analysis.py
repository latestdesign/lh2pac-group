r"""# Perform a sensitivity analysis

## Problem

Quantifying the influence of uncertain inputs on a model output
guides uncertainty reduction and robust design efforts.

## Solution

Use `SobolAnalysis` to compute first-order and total Sobol' indices.

## Step-by-step guide

The following steps apply Sobol' analysis to the Ishigami function:

$$f(x_1,x_2,x_3)=\sin(x_1)+7\sin(x_2)^2+0.1x_3^4\sin(x_1)$$

where $x_1,x_2,x_3\in[-\pi,\pi]$.
"""

import pprint

from gemseo.algos.parameter_space import ParameterSpace
from gemseo.disciplines.analytic import AnalyticDiscipline
from gemseo.uncertainty.sensitivity.sobol_analysis import SobolAnalysis
from numpy import pi

# %%
# ### 1. Create the discipline
discipline = AnalyticDiscipline(
    {"y": "sin(x2)+7*sin(x1)**2+0.1*x3**4*sin(x2)"},
    name="Ishigami",
)

# %%
# ### 2. Define the uncertain space
uncertain_space = ParameterSpace()
for name in ["x1", "x2", "x3"]:
    uncertain_space.add_random_variable(
        name, "OTUniformDistribution", minimum=-pi, maximum=pi
    )

# %%
# ### 3. Compute Sobol' indices
#
# !!! warning
#
#     Sobol' analysis uses the pick-and-freeze (PF) algorithm,
#     which generates $(1+p)N$ evaluations where $p$ is the input dimension.
#     GEMSEO takes a maximum number of simulator calls $n$
#     and deduces $N=\lceil n/(1+p)\rceil$.
#
sobol = SobolAnalysis()
sobol.compute_samples([discipline], uncertain_space, 10000)
sobol.compute_indices()

# %%
# Print first-order and total indices:
pprint.pprint(sobol.indices.first)
pprint.pprint(sobol.indices.total)

# %%
# ### 4. Visualize the indices
#
# Indices are automatically sorted by magnitude:
sobol.plot("y", save=False, show=True)

# %%
# ## Summary
#
# Create a `SobolAnalysis`, call `compute_samples` then `compute_indices`.
# Use `plot` to display the sorted indices.
