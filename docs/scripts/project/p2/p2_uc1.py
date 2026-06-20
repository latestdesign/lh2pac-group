"""Problème 2 — Cas d'usage 1 : propagation des incertitudes et sensibilité.

Conception x figée, on étudie l'effet des incertitudes u sur les sorties.
Pour le kérosène, l'espace incertain se limite aux facteurs d'échelle aef
(traînée), sef (masse) et cef (consommation). On ajuste un surrogate RBF de
f(u), on calcule les indices de Sobol dessus, et on rapporte les statistiques
empiriques et la distribution de la MTOM.

Formulation complète à 11 disciplines (avec operating_cost) et espace incertain
à 3 variables, hors pipeline _oad (seul le helper de figures est réutilisé).
L'analyse couvre les deux points de conception (X_init ; X_opt issu de la
Partie 1) ; étapes aléatoires graînées ; surrogate validé par validation croisée et
sur un plan de test indépendant tiré du vrai modèle.

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
import openturns as ot
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

# Graine globale : reproductibilité du LHS d'entraînement et du sondage de Sobol.
SEED = 0
np.random.seed(SEED)

OUTPUTS = ["mtom", "tofl", "vapp", "vz", "fm"]


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
# ### 2. Disciplines (formulation complète à 11 disciplines)
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

# Les deux points de conception analysés (l'espace incertain, lui, est commun).
DESIGN_POINTS = {
    "init": {
        "label": "X_init (point initial)",
        "values": {"slst": convert_from("kN", 150), "area": convert_from("m2", 180),
                   "n_pax": 150, "ar": 9},
        "suffix": "",       # figures : uc1_p2_distribmtom.png, uc1_p2_sobol.png
    },
    "opt": {
        "label": "X_opt (point optimal)",
        "values": {"slst": convert_from("kN", 100), "area": convert_from("m2", 120),
                   "n_pax": 120, "ar": 15.199},
        "suffix": "_opt",   # figures : uc1_p2_distribmtom_opt.png, uc1_p2_sobol_opt.png
    },
}

# %%
# ### 3. Matrice de dispersion de l'espace incertain (indépendante de x)
# On la génère une seule fois à partir d'un plan d'entraînement de référence.
ref_train = sample_disciplines(
    disciplines, uncertain_space, OUTPUTS, algo_name="OT_OPT_LHS", n_samples=100, seed=SEED
)
scatter = ScatterMatrix(ref_train, variable_names=["aef", "sef", "cef"])
scatter.execute(save=True, show=False, file_path=os.path.join(_oad.FIG_DIR, "uc1_p2_scatter"))


# %%
# ### 4. Analyse complète pour un point de conception donné
def analyse_point(point: dict) -> None:
    """Fige la conception, entraîne le surrogate, valide et propage les incertitudes."""
    label, suffix = point["label"], point["suffix"]
    update_default_input_values(disciplines, point["values"])
    print(f"\n{'=' * 70}\n[UC1] {label}\n{'=' * 70}")

    # Plans d'entraînement (LHS, graîné) et de test (plan factoriel sur le VRAI modèle).
    training_dataset = sample_disciplines(
        disciplines, uncertain_space, OUTPUTS, algo_name="OT_OPT_LHS", n_samples=100, seed=SEED
    )
    test_dataset = sample_disciplines(
        disciplines, uncertain_space, OUTPUTS, algo_name="OT_FULLFACT", n_samples=30**2
    )

    # Surrogate RBF de f(u).
    surrogate_discipline = SurrogateDiscipline("RBFRegressor", data=training_dataset)

    # Analyse de sensibilité (indices de Sobol) via le surrogate (sondage graîné).
    ot.RandomGenerator.SetSeed(SEED)
    sobol = SobolAnalysis()
    sobol.compute_samples([surrogate_discipline], uncertain_space, n_samples=10000)
    sobol.compute_indices(output_names=OUTPUTS)
    print("Indices de Sobol (premier ordre) :")
    pprint.pprint(sobol.indices.first)
    print("Indices de Sobol (totaux) :")
    pprint.pprint(sobol.indices.total)
    sobol.plot("mtom", save=True, show=False,
               file_path=os.path.join(_oad.FIG_DIR, f"uc1_p2_sobol{suffix}"))

    # Statistiques empiriques sur le plan factoriel (vrai modèle).
    stats = EmpiricalStatistics(test_dataset)
    means, variances, coeffs = (stats.compute_mean(), stats.compute_variance(),
                                stats.compute_variation_coefficient())
    print(f"\n{'Variable':<10} | {'Moyenne':<12} | {'Écart-type':<12} | {'Coeff. Var'}")
    print("-" * 55)
    for var in OUTPUTS:
        mu, std, cv = means[var].item(), np.sqrt(variances[var].item()), coeffs[var].item()
        print(f"{var:<10} | {mu:<12.2f} | {std:<12.2f} | {cv:.4f}")

    # Distribution de la MTOM (propagation des incertitudes, vrai modèle).
    fig = plt.figure(figsize=(8, 5))
    plt.hist(test_dataset["outputs"]["mtom"], bins=20, density=True, alpha=0.6, color="b")
    plt.title(f"Distribution de la MTOM — {label}")
    plt.xlabel("MTOM (kg)")
    plt.ylabel("Densité de probabilité")
    plt.grid(True)
    _oad.savefig(fig, f"uc1_p2_distribmtom{suffix}.png")
    plt.close(fig)

    # Précision du surrogate : apprentissage, validation croisée, et plan de test
    # indépendant (vrai modèle).
    r2 = surrogate_discipline.get_error_measure("R2Measure")
    rmse = surrogate_discipline.get_error_measure("RMSEMeasure")
    print("\nR2  apprentissage      :", r2.compute_learning_measure(as_dict=True))
    print("R2  validation croisée :", r2.compute_cross_validation_measure(as_dict=True))
    print("R2  test (vrai modèle) :", r2.compute_test_measure(test_dataset, as_dict=True))
    print("RMSE test (vrai modèle):", rmse.compute_test_measure(test_dataset, as_dict=True))


# %%
# ### 5. Exécution pour les deux points de conception
for _point in DESIGN_POINTS.values():
    analyse_point(_point)
