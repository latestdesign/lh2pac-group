"""# Sample a function with a DOE algorithm

## Problem

Evaluating a function at many points in its domain
requires a design of experiments (DOE) and execution infrastructure.

## Solution

Create a `DOEScenario` from a discipline and a design space,
then call `execute` with a DOE algorithm name and a sample count.

## Step-by-step guide

The following steps sample the Rosenbrock function
$f(x,y)=(1-x)^2+100(y-x^2)^2$ over $[-2,2]^2$
using a Latin hypercube sampling algorithm.
"""
from gemseo import configure_logger
from gemseo.algos.design_space import DesignSpace
from gemseo.disciplines.analytic import AnalyticDiscipline
from gemseo.scenarios.doe_scenario import DOEScenario

# %%
# ### 1. Set up the logger
configure_logger()

# %%
# ### 2. Create the discipline
#
# `AnalyticDiscipline` defines a function from a string expression
# and derives gradients symbolically via [sympy](https://www.sympy.org/fr/):
discipline = AnalyticDiscipline(
    {"z": "(1-x)**2+100*(y-x**2)**2"},
    name="Rosenbrock",
)

# %%
# ### 3. Create the design space
design_space = DesignSpace()
design_space.add_variable("x", lower_bound=-2, upper_bound=2)
design_space.add_variable("y", lower_bound=-2, upper_bound=2)

# %%
# ### 4. Create the scenario and execute the DOE
#
# `"DisciplinaryOpt"` evaluates disciplines sequentially.
# For multiple outputs of interest, call `add_observable` before executing:
#
# ```python
# scenario.add_observable("bar")
# ```
scenario = DOEScenario([discipline], "z", design_space, formulation_name="DisciplinaryOpt")
scenario.execute(algo_name="OT_OPT_LHS", n_samples=100)

# %%
# ### 5. Export the results as a dataset
#
# The result is an `IODataset`, a subclass of `pandas.DataFrame`:
dataset = scenario.to_dataset(opt_naming=False)
dataset

# %%
# ## Summary
#
# Create a `DOEScenario`, call `execute` with a DOE algorithm,
# then export with `to_dataset`.
#
# ## One step further
#
# See the [Dataset examples](https://gemseo.readthedocs.io/en/stable/examples/dataset/index.html)
# and [DOE examples](https://gemseo.readthedocs.io/en/stable/examples/doe/index.html)
# for more options.
