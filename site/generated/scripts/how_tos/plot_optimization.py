r"""# Solve an optimization problem

## Problem

Minimize a function subject to inequality constraints over a bounded domain.

## Solution

Build an `MDOScenario` from a discipline and a design space,
add constraints with `add_constraint`, then call `execute` with an optimizer.

## Step-by-step guide

The following steps minimize the Rosenbrock function
$f(x,y)=(1-x)^2+100(y-x^2)^2$
over $[-2,2]^2$
under the constraint $c(x,y)=\sqrt{(x-1)^2+(y-1)^2}\geq 1$.
"""
from gemseo import configure_logger
from gemseo import from_pickle
from gemseo import to_pickle
from gemseo.algos.design_space import DesignSpace
from gemseo.disciplines.analytic import AnalyticDiscipline
from gemseo.scenarios.mdo_scenario import MDOScenario

# %%
# ### 1. Set up the logger
configure_logger()

# %%
# ### 2. Create the discipline
discipline = AnalyticDiscipline(
    {"z": "(1-x)**2+100*(y-x**2)**2", "c": "((x-1)**2+(y-1)**2)**0.5"},
    name="Rosenbrock"
)

# %%
# ### 3. Create the design space
design_space = DesignSpace()
design_space.add_variable("x", lower_bound=-2., upper_bound=2., value=0.)
design_space.add_variable("y", lower_bound=-2., upper_bound=2., value=0.)

# %%
# ### 4. Build the scenario and add the constraint
#
# `"DisciplinaryOpt"` is the standard formulation for a single discipline.
# For several coupled disciplines, use `"MDF"`:
#
# ```python
# scenario = MDOScenario(disciplines, objective_name, design_space, formulation_name="MDF")
# ```
scenario = MDOScenario([discipline], "z", design_space, formulation_name="DisciplinaryOpt")
scenario.add_constraint("c", constraint_type="ineq", positive=True, value=1.)

# %%
# ### 5. Execute with a gradient-free optimizer
scenario.execute(algo_name="NLOPT_COBYLA", max_iter=100)

# %%
# ### 6. Inspect the results
scenario.optimization_result
# %%
scenario.optimization_result.constraint_values
# %%
scenario.optimization_result.x_opt_as_dict
# %%
scenario.optimization_result.x_0_as_dict
# %%
# Plot the optimization history:
scenario.post_process(post_name="OptHistoryView", save=False, show=True)

# %%
# ## Summary
#
# Create an `MDOScenario`, add constraints, call `execute`,
# then read `optimization_result`.
#
# ## One step further
#
# Results can be persisted and reloaded:
to_pickle(scenario.optimization_result, "optimization_result.pkl")
optimization_result = from_pickle("optimization_result.pkl")
optimization_result
