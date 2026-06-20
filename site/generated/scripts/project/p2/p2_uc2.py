"""Problème 2 — Cas d'usage 2 : propagation des incertitudes et sensibilité.

Conception x figée, on étudie l'effet des incertitudes u sur les sorties.
Pour l'hydrogène liquide, l'espace incertain retient gi, vi (stockage
cryogénique) et aef, sef (facteurs d'échelle). On ajuste un surrogate RBF
de f(u), on le valide, puis on s'en sert pour une propagation Monte-Carlo
(10 000 tirages) et une analyse de Sobol.

Formulation complète à 11 disciplines (avec operating_cost) et espace incertain
à 4 variables, hors pipeline _oad (seul le helper de figures est réutilisé).
Conception figée au point initial X_init; décommenter le bloc dédié pour X_opt.

Script lourd (échantillonnage du vrai modèle, Monte-Carlo et Sobol sur surrogate).
"""

from __future__ import annotations

import os
import sys
import logging

if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "p2_uc2.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pprint

import matplotlib.pyplot as plt
from numpy import array

from gemseo import generate_coupling_graph, sample_disciplines
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.disciplines.auto_py import AutoPyDiscipline
from gemseo.disciplines.surrogate import SurrogateDiscipline
from gemseo.post.dataset.scatter_plot_matrix import ScatterMatrix
from gemseo.uncertainty.sensitivity.sobol_analysis import SobolAnalysis
from gemseo.uncertainty.statistics.empirical_statistics import EmpiricalStatistics
from gemseo.utils.discipline import update_default_input_values
from gemseo_oad_training.models import (
    aerodynamic, approach, climb, engine, fuel_tank, geometry,
    mass, mission, operating_cost, take_off, total_mass,
)
from gemseo_oad_training.unit import convert_from

import _oad

logging.getLogger("gemseo").setLevel(logging.ERROR)


# %%
# ### 1. Espace incertain (4 variables : gi, vi, aef, sef)
class MyUncertainSpace(ParameterSpace):
    def __init__(self):
        super().__init__()
        self.add_random_variable(
            "gi", "OTTriangularDistribution", minimum=0.35, mode=0.4, maximum=0.405
        )  # masse hydrogène / (masse hydrogène + masse réservoir)
        self.add_random_variable(
            "vi", "OTTriangularDistribution", minimum=0.755, mode=0.800, maximum=0.805
        )  # volume hydrogène / volume réservoir
        self.add_random_variable(
            "aef", "OTTriangularDistribution", minimum=0.99, mode=1.0, maximum=1.03
        )
        self.add_random_variable(
            "sef", "OTTriangularDistribution", minimum=0.99, mode=1.0, maximum=1.03
        )


uncertain_space = MyUncertainSpace()

# %%
# ### 2. Visualisation des distributions de l'espace incertain
samples = uncertain_space.compute_samples(1000)
fig, axes = plt.subplots(1, 4, figsize=(12, 4))
for ax, name, values in zip(axes, uncertain_space.variable_names, samples.T):
    ax.hist(values, bins=30, density=True, alpha=0.6, color="g")
    ax.set_title(f"Distribution of {name}")
    ax.set_xlabel(name)
    ax.set_ylabel("Density")
plt.tight_layout()
_oad.savefig(fig, "uc2_p2_uncertain_space_distribution.png")
plt.close(fig)

# %%
# ### 3. Disciplines et conception figée (formulation complète à 11 disciplines)
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
generate_coupling_graph(disciplines, file_path=os.path.join(_oad.FIG_DIR, "uc2_p2_coupling.png"), full=False)

# Point initial X_init
update_default_input_values(disciplines, {"fuel_type": "liquid_h2"})
update_default_input_values(disciplines, {"slst": convert_from('kN', 150)})
update_default_input_values(disciplines, {"area": convert_from('m2', 180)})
update_default_input_values(disciplines, {"n_pax": 150})
update_default_input_values(disciplines, {"ar": 9})

# Point optimal X_opt (décommenter pour l'analyse au point optimal)
# update_default_input_values(disciplines, {"fuel_type": "liquid_h2"})
# update_default_input_values(disciplines, {"slst": convert_from('kN', 100)})
# update_default_input_values(disciplines, {"area": convert_from('m2', 111.58)})
# update_default_input_values(disciplines, {"n_pax": 120})
# update_default_input_values(disciplines, {"ar": 8.89})

# %%
# ### 4. Plans d'entraînement et de test
outputs = ["mtom", "tofl", "vapp", "vz", "span", "length", "fm"]
training_dataset = sample_disciplines(
    disciplines, uncertain_space, outputs, algo_name="OT_OPT_LHS", n_samples=100
)
test_dataset = sample_disciplines(
    disciplines, uncertain_space, outputs, algo_name="OT_FULLFACT", n_samples=30**2
)

# Matrice de dispersion de l'espace incertain
scatter = ScatterMatrix(training_dataset, variable_names=["gi", "vi", "aef", "sef"])
scatter.execute(save=True, show=False, file_path=os.path.join(_oad.FIG_DIR, "uc2_p2_scatter"))

# %%
# ### Statistiques sur le plan de test
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

# %%
# ### 5. Surrogate RBF de f(u)
surrogate_discipline = SurrogateDiscipline("RBFRegressor", training_dataset)

prediction = surrogate_discipline.execute({
    "gi": array([0.4]),
    "vi": array([0.8]),
    "aef": array([1.0]),
    "sef": array([1.0])
})
print("Surrogate prediction at test point:")
print(prediction)

# ### 6. Précision du surrogate
r2 = surrogate_discipline.get_error_measure("R2Measure")
print(f"R2 on training data: {r2.compute_learning_measure(as_dict=True)}")
print(f"R2 by cross validation: {r2.compute_cross_validation_measure(as_dict=True)}")
print(f"R2 on test data: {r2.compute_test_measure(test_dataset, as_dict=True)}")
rmse = surrogate_discipline.get_error_measure("RMSEMeasure")
print(f"RMSE on training data: {rmse.compute_learning_measure(as_dict=True)}")
print(f"RMSE by cross validation: {rmse.compute_cross_validation_measure(as_dict=True)}")
print(f"RMSE on test data: {rmse.compute_test_measure(test_dataset, as_dict=True)}")

# %%
# ### 7. Propagation Monte-Carlo via le surrogate (10 000 tirages)
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

# Histogrammes mtom et tofl
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
_oad.savefig(fig, "uc2_p2_histograms_surrogate.png")
plt.close(fig)

# %%
# ### 8. Analyse de sensibilité (indices de Sobol) via le surrogate
print("Computing Sobol' indices using the surrogate model...")
sobol = SobolAnalysis()
sobol.compute_samples([surrogate_discipline], uncertain_space, 10000)
sobol.compute_indices(output_names=["mtom"])
print("First-order indices:")
pprint.pprint(sobol.indices.first)
print("Total-order indices:")
pprint.pprint(sobol.indices.total)
# Au point initial -> x_init; renommer en _x_opt si le bloc X_opt est décommenté.
sobol.plot("mtom", save=True, show=False,
           file_path=os.path.join(_oad.FIG_DIR, "uc2_p2_sobol_indices_x_init"))
print("Sobol indices plot saved.")
