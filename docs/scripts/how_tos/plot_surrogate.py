r"""# Build and evaluate a surrogate model

## Problem

The original simulator is too expensive to be used directly
in optimization or uncertainty quantification loops.

## Solution

Sample the discipline to create a training dataset,
then build a `SurrogateDiscipline` from it.

## Step-by-step guide

The following steps build a radial-basis-function (RBF) surrogate
of the Rosenbrock function and evaluate its accuracy.
"""
from numpy import array

from gemseo import from_pickle
from gemseo import sample_disciplines
from gemseo import to_pickle
from gemseo.algos.design_space import DesignSpace
from gemseo.disciplines.analytic import AnalyticDiscipline
from gemseo.disciplines.surrogate import SurrogateDiscipline

# %%
# ### 1. Create the discipline and design space
discipline = AnalyticDiscipline(
    {"z": "(1-x)**2+100*(y-x**2)**2", "c": "((x-1)**2+(y-1)**2)**0.5"},
    name="Rosenbrock",
)

design_space = DesignSpace()
design_space.add_variable("x", lower_bound=-2.0, upper_bound=2.0, value=0.0)
design_space.add_variable("y", lower_bound=-2.0, upper_bound=2.0, value=0.0)

# %%
# ### 2. Generate training and test datasets
training_dataset = sample_disciplines(
    [discipline], design_space, ["z", "c"], algo_name="OT_OPT_LHS", n_samples=30
)
test_dataset = sample_disciplines(
    [discipline], design_space, ["z", "c"], algo_name="OT_FULLFACT", n_samples=30**2
)

# %%
# ### 3. Build the surrogate discipline
surrogate_discipline = SurrogateDiscipline("RBFRegressor", training_dataset)

# %%
# ### 4. Make a prediction
surrogate_discipline.execute({"x": array([1.0])})

# %%
# ### 5. Evaluate accuracy
#
# R² measure — on training data, by cross-validation, and on test data:
r2 = surrogate_discipline.get_error_measure("R2Measure")
r2.compute_learning_measure(as_dict=True)
# %%
r2.compute_cross_validation_measure(as_dict=True)
# %%
r2.compute_test_measure(test_dataset, as_dict=True)

# %%
# RMSE measure:
rmse = surrogate_discipline.get_error_measure("RMSEMeasure")
rmse.compute_learning_measure(as_dict=True)
# %%
rmse.compute_cross_validation_measure(as_dict=True)
# %%
rmse.compute_test_measure(test_dataset, as_dict=True)

# %%
# ## Summary
#
# Sample the discipline to get a training dataset,
# pass it to `SurrogateDiscipline` with a regressor name,
# then assess quality with `get_error_measure`.
#
# ## One step further
#
# Persist and reload the surrogate:
to_pickle(surrogate_discipline, "my_surrogate.pkl")
surrogate_discipline = from_pickle("my_surrogate.pkl")
surrogate_discipline.execute({"x": array([1.0])})
