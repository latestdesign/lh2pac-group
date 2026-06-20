"""Problème 3 — Comparaison des méthodes d'estimation des statistiques (UQ).

Compare les trois manières d'estimer l'espérance et l'écart-type propagés à chaque
itération de l'optimiseur robuste :

* surrogate : krigeage de f_hat(x, u) ré-échantillonné (Surrogate_Settings);
* sampling : Monte-Carlo direct sur le modèle multidisciplinaire (Sampling_Settings);
* taylor : développement de Taylor au premier ordre (TaylorPolynomial_Settings).

Formulation complète à 11 disciplines (avec operating_cost) et espace incertain
à 7 variables (incluant fc_pwd et bed), hors pipeline _oad (seul le
helper de figures est réutilisé).

Script lourd (la variante sampling sur le vrai modèle surtout) : chaque couple
(cas d'usage, méthode) est dans un bloc # %% séparé.
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "p3_uq_methods.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from matplotlib import pyplot as plt

from gemseo import configure_logger
from gemseo.algos.design_space import DesignSpace
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.disciplines.auto_py import AutoPyDiscipline
from gemseo.utils.discipline import update_default_input_values
from gemseo_oad_training.models import (
    aerodynamic, approach, climb, engine, fuel_tank, geometry,
    mass, mission, operating_cost, take_off, total_mass,
)
from gemseo_oad_training.unit import convert_from
from gemseo_umdo.formulations.sampling_settings import Sampling_Settings
from gemseo_umdo.formulations.surrogate_settings import Surrogate_Settings
from gemseo_umdo.formulations.taylor_polynomial_settings import TaylorPolynomial_Settings
from gemseo_umdo.scenarios.umdo_scenario import UMDOScenario

import _oad

configure_logger(level="WARNING")

N_SAMPLES = 200  # taille d'échantillonnage des variantes surrogate / sampling


def _build_disciplines(uc):
    """Formulation complète à 11 disciplines (avec operating_cost); fuel_type fixé pour UC2."""
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


def _design_space():
    space = DesignSpace()
    space.add_variable("slst", lower_bound=convert_from("kN", 100), upper_bound=convert_from("kN", 200), value=convert_from("kN", 150))
    space.add_variable("n_pax", lower_bound=120, upper_bound=180, value=150)
    space.add_variable("area", lower_bound=convert_from("m2", 100), upper_bound=convert_from("m2", 200), value=convert_from("m2", 180))
    space.add_variable("ar", lower_bound=5, upper_bound=20, value=9)
    return space


_SETTINGS = {
    "surrogate": lambda: Surrogate_Settings(n_samples=N_SAMPLES),
    "sampling": lambda: Sampling_Settings(n_samples=N_SAMPLES),
    "taylor": lambda: TaylorPolynomial_Settings(),
}


def run(uc, method):
    """Optimisation robuste min E[mtom] sous marges, avec la méthode d'estimation choisie."""
    disciplines = _build_disciplines(uc)
    scenario = UMDOScenario(
        disciplines, "mtom", _design_space(), _uncertain_space(), "Mean",
        formulation_name="MDF", statistic_estimation_settings=_SETTINGS[method](),
    )
    # Contraintes en marge (mean +/- 2*std).
    scenario.add_constraint("tofl", "Margin", factor=2.0, value=convert_from("m", 1900))
    scenario.add_constraint("vapp", "Margin", factor=2.0, value=convert_from("kt", 135))
    scenario.add_constraint("vz", "Margin", positive=True, factor=2.0, value=convert_from("ft/min", 300))
    scenario.add_constraint("span", "Margin", factor=2.0, value=convert_from("m", 40))
    scenario.add_constraint("length", "Margin", factor=2.0, value=convert_from("m", 45))
    scenario.add_constraint("fm", "Margin", positive=True, factor=2.0, value=0)

    scenario.execute(algo_name="NLOPT_COBYLA", max_iter=200)
    result = scenario.optimization_result
    x_opt = {k: float(np.ravel(v)[0]) for k, v in result.x_opt_as_dict.items()}
    print(f"\n[{uc}] P3 méthode UQ '{method}' — E[MTOM] = {float(np.ravel(result.f_opt)[0]):.1f} kg")
    for name in ("slst", "n_pax", "area", "ar"):
        print(f"  {name:6s} = {x_opt[name]:.2f}")

    # Historique de convergence (objectif).
    problem = scenario.formulation.optimization_problem
    obj_history = np.array(problem.database.get_function_history(problem.objective.name)).ravel()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(np.arange(1, len(obj_history) + 1), obj_history, "-o", ms=3, color="tab:green")
    ax.set_xlabel("iteration")
    ax.set_ylabel("E[MTOM] (kg)")
    ax.set_title(f"{uc} - Problem 3 robust optimization ({method})")
    _oad.savefig(fig, f"{uc.lower()}_p3_uq_{method}.png")
    plt.close(fig)
    print(f"[{uc}] P3 méthode UQ '{method}' : figure sauvegardée.")


# %%
# ## Cas d'usage 1 — Kérosène / Turbofan
run("UC1", "surrogate")
# %%
run("UC1", "sampling")
# %%
run("UC1", "taylor")

# %%
# ## Cas d'usage 2 — Hydrogène liquide / Turbofan
run("UC2", "surrogate")
# %%
run("UC2", "sampling")
# %%
run("UC2", "taylor")
