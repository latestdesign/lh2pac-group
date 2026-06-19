"""
Problem 2 - Use Case 1: Uncertainty Propagation and Sensitivity Analysis
========================================================================

This script propagates uncertainties and computes Sobol' indices for Use Case 1.
"""
from gemseo import generate_coupling_graph
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

from gemseo.post.dataset.scatter_plot_matrix import ScatterMatrix
from gemseo.algos.design_space import DesignSpace
from numpy import array
import numpy as np

from gemseo.scenarios.mdo_scenario import MDOScenario

from gemseo_oad_training.unit import convert_from


from gemseo import sample_disciplines
from gemseo.disciplines.surrogate import SurrogateDiscipline

from gemseo.algos.parameter_space import ParameterSpace

from gemseo.utils.discipline import update_default_input_values

from gemseo.uncertainty.sensitivity.sobol_analysis import SobolAnalysis
import pprint

from matplotlib import pyplot as plt

from gemseo import sample_disciplines
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.disciplines.analytic import AnalyticDiscipline
from gemseo.uncertainty.statistics.empirical_statistics import EmpiricalStatistics


# %%
# ### 1. Create an empty parameter space
class MyUncertainSpace(ParameterSpace):
    def __init__(self):
        super().__init__()
        self.add_random_variable

        self.add_random_variable(
        "aef", "OTTriangularDistribution", minimum=0.99, mode=1.0, maximum=1.03
        )

        self.add_random_variable(
        "sef", "OTTriangularDistribution", minimum=0.99, mode=1.0, maximum=1.03
        )

        self.add_random_variable(
        "cef", "OTTriangularDistribution", minimum=0.99, mode=1.0, maximum=1.03
        )


# %%
# ### 3. Inspect the uncertain space

uncertain_space = MyUncertainSpace()
uncertain_space

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

#update_default_input_values(disciplines, {"slst": convert_from('kN',150)})
#update_default_input_values(disciplines, {"area": convert_from('m2',180)})
#update_default_input_values(disciplines, {"n_pax": 150})
#update_default_input_values(disciplines, {"ar": 9})
#x Optimal
update_default_input_values(disciplines, {"slst": convert_from('kN',100)})
update_default_input_values(disciplines, {"area": convert_from('m2',120)})
update_default_input_values(disciplines, {"n_pax": 120})
update_default_input_values(disciplines, {"ar": 15.199})


print("All default values")
for discip in disciplines :
 print(discip.io.input_grammar.defaults)


# ### 2. Generate training and test datasets
training_dataset = sample_disciplines(
    disciplines, uncertain_space, ["mtom", "tofl", "vapp", "vz", "fm"], algo_name="OT_OPT_LHS", n_samples=100
)
test_dataset = sample_disciplines(
    disciplines, uncertain_space, ["mtom", "tofl", "vapp", "vz", "fm"], algo_name="OT_FULLFACT", n_samples=30**2
)

# Création et exécution du graphique de matrice de dispersion avec GEMSEO
scatter = ScatterMatrix(training_dataset, variable_names=["aef", "sef", "cef"])
#scatter.execute(
    #save=True, 
   # show=True 
    #file_path="/Users/drisschraibi/Desktop/lh2pac/fig_prob_2/scatter_opt"
#)


surrogate_discipline = SurrogateDiscipline(
 "RBFRegressor",
 data=training_dataset
)

#Stats 

# Sobol Analysis

sobol = SobolAnalysis()
sobol.compute_samples([surrogate_discipline], uncertain_space, n_samples=1000) #500 et 10000
sobol.compute_indices(output_names= ["mtom", "tofl", "vapp", "vz", "fm"])

# %%
# Print first-order and total indices:
pprint.pprint(sobol.indices.first)
pprint.pprint(sobol.indices.total)

# %%
# ### 4. Visualize the indices
#
# Indices are automatically sorted by magnitude:
print(list(sobol.indices.first.keys()))

#sobol.plot("mtom", save=True, show=True, file_path="/Users/drisschraibi/Desktop/lh2pac/fig_prob_2/sobol_opt")

print("Surrogate Discipline :")
# ### 3. Build the surrogate discipline
print(sobol.dataset.inputs)


import numpy as np

# Liste des sorties à analyser
outputs = ["mtom", "tofl", "vapp", "vz", "fm"]

# Calcul des statistiques sur l'ensemble du dataset
stats = EmpiricalStatistics(test_dataset)
means = stats.compute_mean()
variances = stats.compute_variance()
coeffs = stats.compute_variation_coefficient()

print(f"{'Variable':<10} | {'Moyenne':<12} | {'Écart-type':<12} | {'Coeff. Var'}")
print("-" * 55)

for var in outputs:
    mu = means[var].item()
    var_val = variances[var].item()
    std = np.sqrt(var_val)
    cv = coeffs[var].item()
    
    print(f"{var:<10} | {mu:<12.2f} | {std:<12.2f} | {cv:.4f}")

#Distrib 
# Visualisation de la distribution de la MTOM
data_mtom = test_dataset["outputs"]["mtom"]

plt.figure(figsize=(8, 5))
plt.hist(data_mtom, bins=20, density=True, alpha=0.6, color='b')
plt.title("Distribution de la MTOM (Propagation des incertitudes)")
plt.xlabel("MTOM (kg)")
plt.ylabel("Densité de probabilité")
plt.grid(True)
#plt.savefig("/Users/drisschraibi/Desktop/lh2pac/fig_prob_2/distribmtom_opt")
plt.show()
#print(surrogate_discipline.execute({"gi":array([0.4]),"vi":array([0.8]),"aef":array([1]),"sef":array([1]),"fc_pwd":array([1]),"bed":array([400])}))
# ### 5. Evaluate accuracy

# R² measure — on training data, by cross-validation, and on test data:
r2 = surrogate_discipline.get_error_measure("R2Measure")
print(f"R2 : {r2.compute_learning_measure(as_dict=True)}")
# %%
print(f" Cross Validation Measure : {r2.compute_cross_validation_measure(as_dict=True)}")
# %%
print(f" Test Measure : {r2.compute_test_measure(sobol.dataset, as_dict=True)}")

# %%
# RMSE measure:
rmse = surrogate_discipline.get_error_measure("RMSEMeasure")
print(f"RMSE : {rmse.compute_learning_measure(as_dict=True)}")
# %%
print(f"Cross Validation Measure : {rmse.compute_cross_validation_measure(as_dict=True)}")
# %%
print(f"Test Measure : {rmse.compute_test_measure(sobol.dataset, as_dict=True)}")


