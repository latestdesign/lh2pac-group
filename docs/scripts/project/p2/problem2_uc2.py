"""
Problem 2 - Use Case 2: Uncertainty Propagation and Sensitivity Analysis
========================================================================

This script propagates uncertainties and computes Sobol' indices for Use Case 2.
"""

from gemseo import generate_coupling_graph
from gemseo.post.dataset.scatter_plot_matrix import ScatterMatrix
from gemseo.disciplines.auto_py import AutoPyDiscipline
from gemseo_oad_training.models import aerodynamic
from gemseo_oad_training.models import approach
# from gemseo_oad_training.models import battery
from gemseo_oad_training.models import climb
from gemseo_oad_training.models import engine
from gemseo_oad_training.models import fuel_tank
from gemseo_oad_training.models import geometry
from gemseo_oad_training.models import mass
from gemseo_oad_training.models import mission
from gemseo_oad_training.models import operating_cost
from gemseo_oad_training.models import take_off
from gemseo_oad_training.models import total_mass

from numpy import array
import numpy as np
import matplotlib.pyplot as plt
import logging
logging.getLogger("gemseo").setLevel(logging.ERROR)

from gemseo_oad_training.unit import convert_from


from gemseo import sample_disciplines
from gemseo.disciplines.surrogate import SurrogateDiscipline

from gemseo.algos.parameter_space import ParameterSpace

from gemseo.utils.discipline import update_default_input_values

from gemseo.uncertainty.sensitivity.sobol_analysis import SobolAnalysis
import pprint

from gemseo.uncertainty.statistics.empirical_statistics import EmpiricalStatistics

# %%
# ### 1. Create an empty parameter space
uncertain_space = ParameterSpace()

# %%
# ### 2. Add random variables
#vi T(0.755, 0.800, 0.805) liquid_h2 All
#aef T(0.99, 1., 1.03) All All
#cef T(0.99, 1., 1.03) All All
#sef T(0.99, 1., 1.03) All All
#fc_pwd T(0.8, 1, 1.02) liquid_h2 electrofan
#bed U(400,700) battery All

# A triangular variable $z$:
class MyUncertainSpace(ParameterSpace):
    def __init__(self):
        super().__init__()
        self.add_random_variable(
        "gi", "OTTriangularDistribution", minimum=0.35, mode=0.4, maximum=0.405
        ) # mass hydrogen/ mass hydrogen + mass reservoir
        self.add_random_variable(
        "vi", "OTTriangularDistribution", minimum=0.755, mode=0.800, maximum=0.805
        ) #vol hydrogen/ vol reservoir

        self.add_random_variable(
        "aef", "OTTriangularDistribution", minimum=0.99, mode=1.0, maximum=1.03
        )

        self.add_random_variable(
        "sef", "OTTriangularDistribution", minimum=0.99, mode=1.0, maximum=1.03
        )


# %%
# ### 3. Inspect the uncertain space

uncertain_space = MyUncertainSpace()
uncertain_space
import matplotlib.pyplot as plt

samples = uncertain_space.compute_samples(1000)
fig, axes = plt.subplots(1, 4, figsize=(12, 4))
for ax, name, values in zip(axes, uncertain_space.variable_names, samples.T):
    ax.hist(values, bins=30, density=True, alpha=0.6, color="g")
    ax.set_title(f"Distribution of {name}")
    ax.set_xlabel(name)
    ax.set_ylabel("Density")

plt.tight_layout()
plt.show()



#uncertainty propagation :



disciplines = [AutoPyDiscipline(aerodynamic),
    AutoPyDiscipline(approach),
    AutoPyDiscipline(climb),
    AutoPyDiscipline(engine),
    AutoPyDiscipline(fuel_tank),
    AutoPyDiscipline(geometry),
    AutoPyDiscipline(mass),
    AutoPyDiscipline(mission),
    AutoPyDiscipline(operating_cost),
    AutoPyDiscipline(take_off),
    AutoPyDiscipline(total_mass)]
generate_coupling_graph(disciplines, file_path='couplage.png',full=False)

# %%
# Definition of x_init and x_opt (by hand)
#X_init
update_default_input_values(disciplines, {"fuel_type": "liquid_h2"})
update_default_input_values(disciplines, {"slst": convert_from('kN',150)})
update_default_input_values(disciplines, {"area": convert_from('m2',180)})
update_default_input_values(disciplines, {"n_pax": 150})
update_default_input_values(disciplines, {"ar": 9})

#X_Opt
# update_default_input_values(disciplines, {"fuel_type": "liquid_h2"})
# update_default_input_values(disciplines, {"slst": convert_from('kN',100)})
# update_default_input_values(disciplines, {"area": convert_from('m2',111.58)})
# update_default_input_values(disciplines, {"n_pax": 120})
# update_default_input_values(disciplines, {"ar": 8.89})



# print("All default values")
# for discip in disciplines :
#     print(discip.io.input_grammar.defaults)


# suite
# Define outputs of interest (objective and operational requirements)
outputs = ["mtom", "tofl", "vapp", "vz", "span", "length", "fm"]

# ### 1. Generate training and test datasets
training_dataset = sample_disciplines(
    disciplines, uncertain_space, outputs, algo_name="OT_OPT_LHS", n_samples=100
)
test_dataset = sample_disciplines(
    disciplines, uncertain_space, outputs, algo_name="OT_FULLFACT", n_samples=30**2
)

# Scatter plot matrix of the uncertain space
import os
scatter_fig_path = os.path.join(
    os.path.dirname(__file__), "..", "..", "report", "figs", "uc2_p2_scatter"
)
scatter = ScatterMatrix(training_dataset, variable_names=["gi", "vi", "aef", "sef"])
scatter.execute(save=True, show=True, file_path=scatter_fig_path)

# ### Statistics on Test dataset
statistics = EmpiricalStatistics(test_dataset)
mean = statistics.compute_mean()
variance = statistics.compute_variance()
variation_coeff = statistics.compute_variation_coefficient()
print("Empirical Mean of outputs:")
pprint.pprint(mean)
print("Empirical Variance of outputs:")
pprint.pprint(variance)
print("Empirical Variation Coefficient of outputs:")

pprint.pprint(variation_coeff)
print("Ratio var/mean for mtom")
print(variation_coeff['mtom'][0] / mean['mtom'][0])
# Plot the histograms

# %%
# ### 2. Build the surrogate discipline
surrogate_discipline = SurrogateDiscipline("RBFRegressor", training_dataset)

# Evaluate a prediction
prediction = surrogate_discipline.execute({
    "gi": array([0.4]),
    "vi": array([0.8]),
    "aef": array([1.0]),
    "sef": array([1.0])
})
print("Surrogate prediction at test point:")
print(prediction)

# ### 3. Evaluate accuracy
# R² measure:
r2 = surrogate_discipline.get_error_measure("R2Measure")
print(f"R2 on training data: {r2.compute_learning_measure(as_dict=True)}")
print(f"R2 by cross validation: {r2.compute_cross_validation_measure(as_dict=True)}")
print(f"R2 on test data: {r2.compute_test_measure(test_dataset, as_dict=True)}")

# RMSE measure:
rmse = surrogate_discipline.get_error_measure("RMSEMeasure")
print(f"RMSE on training data: {rmse.compute_learning_measure(as_dict=True)}")
print(f"RMSE by cross validation: {rmse.compute_cross_validation_measure(as_dict=True)}")
print(f"RMSE on test data: {rmse.compute_test_measure(test_dataset, as_dict=True)}")

# ### 4. Uncertainty propagation using the surrogate model
print("Propagation of uncertainties using the surrogate model...")
surrogate_mc_dataset = sample_disciplines(
    [surrogate_discipline], uncertain_space, outputs, algo_name="OT_MONTE_CARLO", n_samples=10000
)

statistics = EmpiricalStatistics(surrogate_mc_dataset)
mean = statistics.compute_mean()
variance = statistics.compute_variance()
variation_coeff = statistics.compute_variation_coefficient()
print("Empirical Mean of outputs:")
pprint.pprint(mean)
print("Empirical Variance of outputs:")
pprint.pprint(variance)
print("Empirical Variation Coefficient of outputs:")

pprint.pprint(variation_coeff)
print("Ratio var/mean for mtom")
print(variation_coeff['mtom'][0] / mean['mtom'][0])


# Plot the histograms
fig, axes = plt.subplots(1, 2, figsize=(10, 5))
axes[0].hist(surrogate_mc_dataset.get_view(variable_names="mtom").values, bins=50, edgecolor='black')
axes[0].set_title("Histogram of mtom")
axes[0].set_xlabel("mtom")
axes[0].set_ylabel("Frequency")

axes[1].hist(surrogate_mc_dataset.get_view(variable_names="tofl").values, bins=50, edgecolor='black')
axes[1].set_title("Histogram of tofl")
axes[1].set_xlabel("tofl")
axes[1].set_ylabel("Frequency")

plt.tight_layout()
plt.savefig("histograms_surrogate.png")
print("Histograms saved as histograms_surrogate.png")
plt.show()

#
# ### 5. Sensitivity Analysis (Sobol' Indices) using the surrogate model
print("Computing Sobol' indices using the surrogate model...")
sobol = SobolAnalysis()
sobol.compute_samples([surrogate_discipline], uncertain_space, 10000)
sobol.compute_indices(output_names=["mtom"])

# Print first-order and total indices:
print("First-order indices:")
pprint.pprint(sobol.indices.first)
print("Total-order indices:")
pprint.pprint(sobol.indices.total)

# Visualize the indices
sobol.plot("mtom", save=True, show=True, file_path="sobol_indices_surrogate.png")
print("Sobol indices plot saved as sobol_indices_surrogate.png")

