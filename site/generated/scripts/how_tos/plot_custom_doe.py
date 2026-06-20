"""# Execute a scenario at a given point"""

from gemseo.algos.design_space import DesignSpace
from gemseo.disciplines.analytic import AnalyticDiscipline
from gemseo.scenarios.mdo_scenario import MDOScenario
from numpy import array

# %%
# ### 1. Create the discipline
#
# `AnalyticDiscipline` defines a function from a string expression
# and derives gradients symbolically via [sympy](https://www.sympy.org/fr/):
discipline = AnalyticDiscipline(
    {"z": "(1-x)**2+100*(y-x**2)**2"},
    name="Rosenbrock",
)

# %%
# ### 2. Create the design space
design_space = DesignSpace()
design_space.add_variable("x", lower_bound=-2, upper_bound=2)
design_space.add_variable("y", lower_bound=-2, upper_bound=2)

# %%
# ### 3. Create the scenario and execute the DOE
#
scenario = MDOScenario([discipline], "z", design_space, formulation_name="DisciplinaryOpt")
xstar = {"x": array([1.5]), "y": array([-0.5])}
# xstar = surrogate_scenario.optimization_result.x_opt_as_dict
scenario.execute(algo_name="CustomDOE", samples=[xstar])
scenario.optimization_result

# %%
# ### 4. Export the results as a dataset
#
dataset = scenario.to_dataset(opt_naming=False)
dataset
