"""Problème 2 — Cas d'usage 1 : propagation des incertitudes et analyse de sensibilité.

Le problème 2 fige la conception ``x`` et étudie l'effet des incertitudes
technologiques ``u`` sur les sorties. Pour le cas kérosène (conventionnel), il n'y
a pas de réservoir cryogénique : l'espace incertain se limite aux facteurs
d'échelle ``aef`` (traînée), ``sef`` (masse structurale) et ``cef`` (consommation
moteur). On ajuste un surrogate RBF de ``f(u)``, on calcule les indices de Sobol
sur ce surrogate, et on rapporte les statistiques empiriques + la distribution de
la MTOM sous incertitudes.

Ce script utilise la formulation complète à 11 disciplines (avec
``operating_cost``) et l'espace incertain à 3 variables, distincts du pipeline
canonique ``_oad`` (dont seul le helper de figures est réutilisé). La conception
est figée au point optimal X_opt ; décommenter le bloc correspondant ci-dessous
pour l'analyse au point initial X_init.

Script lourd (échantillonnage du vrai modèle, Sobol sur surrogate).
"""

from __future__ import annotations

import os
import sys

if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "p2_uc1.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pprint

import numpy as np
from matplotlib import pyplot as plt

from gemseo import sample_disciplines
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


# %%
# ### 1. Espace incertain (3 facteurs d'échelle : aef, sef, cef)
class MyUncertainSpace(ParameterSpace):
    def __init__(self):
        super().__init__()
        self.add_random_variable(
            "aef", "OTTriangularDistribution", minimum=0.99, mode=1.0, maximum=1.03
        )
        self.add_random_variable(
            "sef", "OTTriangularDistribution", minimum=0.99, mode=1.0, maximum=1.03
        )
        self.add_random_variable(
            "cef", "OTTriangularDistribution", minimum=0.99, mode=1.0, maximum=1.03
        )


uncertain_space = MyUncertainSpace()

# %%
# ### 2. Disciplines et conception figée (formulation complète à 11 disciplines)
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

# Point initial X_init (décommenter pour l'analyse au point initial)
# update_default_input_values(disciplines, {"slst": convert_from('kN', 150)})
# update_default_input_values(disciplines, {"area": convert_from('m2', 180)})
# update_default_input_values(disciplines, {"n_pax": 150})
# update_default_input_values(disciplines, {"ar": 9})

# Point optimal X_opt
update_default_input_values(disciplines, {"slst": convert_from('kN', 100)})
update_default_input_values(disciplines, {"area": convert_from('m2', 120)})
update_default_input_values(disciplines, {"n_pax": 120})
update_default_input_values(disciplines, {"ar": 15.199})

# %%
# ### 3. Plans d'entraînement et de test
training_dataset = sample_disciplines(
    disciplines, uncertain_space, ["mtom", "tofl", "vapp", "vz", "fm"], algo_name="OT_OPT_LHS", n_samples=100
)
test_dataset = sample_disciplines(
    disciplines, uncertain_space, ["mtom", "tofl", "vapp", "vz", "fm"], algo_name="OT_FULLFACT", n_samples=30**2
)

# Matrice de dispersion de l'espace incertain
scatter = ScatterMatrix(training_dataset, variable_names=["aef", "sef", "cef"])
scatter.execute(save=True, show=False, file_path=os.path.join(_oad.FIG_DIR, "uc1_p2_scatter"))

# %%
# ### 4. Surrogate RBF de f(u)
surrogate_discipline = SurrogateDiscipline("RBFRegressor", data=training_dataset)

# %%
# ### 5. Analyse de sensibilité (indices de Sobol) via le surrogate
sobol = SobolAnalysis()
sobol.compute_samples([surrogate_discipline], uncertain_space, n_samples=1000)  # 500 et 10000
sobol.compute_indices(output_names=["mtom", "tofl", "vapp", "vz", "fm"])
pprint.pprint(sobol.indices.first)
pprint.pprint(sobol.indices.total)
print(list(sobol.indices.first.keys()))
# Au point optimal -> x_opt ; renommer en _x_init si le bloc X_init est décommenté.
sobol.plot("mtom", save=True, show=False,
           file_path=os.path.join(_oad.FIG_DIR, "uc1_p2_sobol_opt"))

# %%
# ### 6. Statistiques empiriques (tableau français)
outputs = ["mtom", "tofl", "vapp", "vz", "fm"]
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

# %%
# ### 7. Distribution de la MTOM (propagation des incertitudes)
data_mtom = test_dataset["outputs"]["mtom"]
fig = plt.figure(figsize=(8, 5))
plt.hist(data_mtom, bins=20, density=True, alpha=0.6, color='b')
plt.title("Distribution de la MTOM (Propagation des incertitudes)")
plt.xlabel("MTOM (kg)")
plt.ylabel("Densité de probabilité")
plt.grid(True)
_oad.savefig(fig, "uc1_p2_distribmtom_opt.png")
plt.close(fig)

# %%
# ### 8. Précision du surrogate
r2 = surrogate_discipline.get_error_measure("R2Measure")
print(f"R2 : {r2.compute_learning_measure(as_dict=True)}")
print(f" Cross Validation Measure : {r2.compute_cross_validation_measure(as_dict=True)}")
print(f" Test Measure : {r2.compute_test_measure(sobol.dataset, as_dict=True)}")
rmse = surrogate_discipline.get_error_measure("RMSEMeasure")
print(f"RMSE : {rmse.compute_learning_measure(as_dict=True)}")
print(f"Cross Validation Measure : {rmse.compute_cross_validation_measure(as_dict=True)}")
print(f"Test Measure : {rmse.compute_test_measure(sobol.dataset, as_dict=True)}")
