"""Problème 3 — Propagation des incertitudes (statistiques empiriques).

Étape de propagation : on échantillonne directement les paramètres incertains par
Monte-Carlo à travers le vrai modèle multidisciplinaire, puis on estime les
**statistiques empiriques** (moyenne et variance) des sorties et on visualise leurs
distributions. La conception est laissée à ses valeurs par défaut ; seul u varie.

Ce script utilise la formulation complète à 11 disciplines (avec ``operating_cost``)
et l'espace incertain à 7 variables ; il ne passe donc pas par ``_oad`` (hormis le
helper de figures).

Script lourd (Monte-Carlo de 1000 tirages sur le vrai modèle). Les deux cas
d'usage sont produits ci-dessous.
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "p3_propagation.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matplotlib import pyplot as plt

from gemseo import configure_logger, sample_disciplines
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.disciplines.auto_py import AutoPyDiscipline
from gemseo.utils.discipline import update_default_input_values
from gemseo.uncertainty.statistics.empirical_statistics import EmpiricalStatistics
from gemseo_oad_training.models import (
    aerodynamic, approach, climb, engine, fuel_tank, geometry,
    mass, mission, operating_cost, take_off, total_mass,
)

import _oad

configure_logger(level="WARNING")

OUTPUTS = ["mtom", "tofl", "vapp", "vz", "span", "length", "fm"]


def _build_disciplines(uc):
    """Formulation complète à 11 disciplines (avec operating_cost) ; fuel_type fixé pour UC2."""
    disciplines = [AutoPyDiscipline(func) for func in (
        aerodynamic, approach, climb, engine, fuel_tank, geometry,
        mass, mission, operating_cost, take_off, total_mass)]
    if uc == "UC2":
        update_default_input_values(disciplines, {"fuel_type": "liquid_h2"})
    return disciplines


def _uncertain_space():
    """Espace incertain complet à 7 variables (incluant fc_pwd et bed)."""
    space = ParameterSpace()
    space.add_random_variable("gi", "OTTriangularDistribution", minimum=0.35, mode=0.4, maximum=0.405)
    space.add_random_variable("vi", "OTTriangularDistribution", minimum=0.755, mode=0.8, maximum=0.805)
    space.add_random_variable("aef", "OTTriangularDistribution", minimum=0.99, mode=1.0, maximum=1.03)
    space.add_random_variable("cef", "OTTriangularDistribution", minimum=0.99, mode=1.0, maximum=1.03)
    space.add_random_variable("sef", "OTTriangularDistribution", minimum=0.8, mode=1.0, maximum=1.02)
    space.add_random_variable("fc_pwd", "OTTriangularDistribution", minimum=0.755, mode=0.8, maximum=0.805)
    space.add_random_variable("bed", "OTUniformDistribution", minimum=400, maximum=700)
    return space


def run(uc):
    """Propagation Monte-Carlo de u à travers le vrai modèle + statistiques empiriques."""
    disciplines = _build_disciplines(uc)
    uncertain_space = _uncertain_space()

    # Échantillonnage Monte-Carlo des incertitudes (conception aux valeurs par défaut).
    dataset = sample_disciplines(
        disciplines, uncertain_space, OUTPUTS, algo_name="OT_MONTE_CARLO", n_samples=1000
    )

    # Statistiques empiriques : moyenne et variance des sorties.
    statistics = EmpiricalStatistics(dataset)
    mean = statistics.compute_mean()
    variance = statistics.compute_variance()
    print(f"\n[{uc}] P3 propagation — moyenne empirique des sorties :")
    print(mean)
    print(f"[{uc}] P3 propagation — variance empirique des sorties :")
    print(variance)

    # Histogrammes des distributions des sorties (grille complète).
    ncols = 3
    nrows = (len(OUTPUTS) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(4 * ncols, 3 * nrows))
    for ax, name in zip(axes.ravel(), OUTPUTS):
        ax.hist(dataset.get_view(variable_names=name).to_numpy().ravel(), bins=30, color="tab:green")
        ax.set_title(name)
    for ax in axes.ravel()[len(OUTPUTS):]:
        ax.axis("off")
    fig.suptitle(f"{uc} - Problem 3 uncertainty propagation: output distributions")
    fig.tight_layout()
    _oad.savefig(fig, f"{uc.lower()}_p3_propagation.png")
    plt.close(fig)
    print(f"[{uc}] P3 propagation : figure sauvegardée.")


# %%
# ## Cas d'usage 1 — Kérosène / Turbofan
run("UC1")

# %%
# ## Cas d'usage 2 — Hydrogène liquide / Turbofan
run("UC2")
