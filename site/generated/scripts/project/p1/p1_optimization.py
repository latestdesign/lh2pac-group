"""Problème 1 — Optimisation déterministe sur le surrogate f_hat(x).

Minimise mtom sous les six contraintes (incertitudes gelées au nominal) avec
COBYLA sur le surrogate, puis vérifie l'optimum sur le vrai modèle couplé.
L'optimum est picklé dans data/ et sert de référence au problème 3.

Script lourd : lancer p1_doe puis p1_surrogate d'abord. Produit les figures
d'historique de convergence et de dessin de l'avion.
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
# mkdocs-gallery exécute ce fichier sans __file__; on le définit pour
# résoudre les imports et chemins ci-dessous.
if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "p1_optimization.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from matplotlib import pyplot as plt

from gemseo import configure_logger, create_mda, from_pickle
from gemseo.scenarios.mdo_scenario import MDOScenario
from gemseo_oad_training.utils import AircraftConfiguration, draw_aircraft

import _oad

configure_logger(level="WARNING")

HERE = os.path.dirname(os.path.abspath(__file__))

DES = ("slst", "n_pax", "area", "ar")


def _true_at(uc, design):
    """Évalue le VRAI modèle couplé en un point de conception, u gelé au nominal.

    Les chiffres clés (MTOM, contraintes) sont lus ici, pas sur le surrogate.
    (Les grammaires AutoPyDiscipline veulent des entrées scalaires.)
    """
    disc = _oad.make_disciplines(uc)
    _oad.set_design_point(
        disc, {k: _oad.NOMINAL_UNCERTAIN[k] for k in _oad.get_uncertain_space(uc).variable_names})
    out = create_mda("MDAChain", disc).execute({k: float(design[k]) for k in DES})
    return {n: float(np.ravel(out[n])[0]) for n in _oad.OUTPUT_NAMES}


def run(uc):
    """Optimisation déterministe + vérification sur le vrai modèle pour un cas d'usage."""
    surrogate = from_pickle(os.path.join(HERE, "data", f"{uc.lower()}_p1_surrogate.pkl"))

    # Optimisation déterministe sur le surrogate (supprimer le pickle pour la refaire).
    def run_scenario():
        scenario = MDOScenario([surrogate], _oad.OBJECTIVE, _oad.get_design_space(),
                               formulation_name="DisciplinaryOpt")
        _oad.add_constraints(scenario)
        scenario.execute(algo_name="NLOPT_COBYLA", max_iter=200)

        # Historique de convergence (base de données du scénario, tracé au recalcul).
        problem = scenario.formulation.optimization_problem
        database = problem.database
        obj_history = np.array(database.get_function_history(problem.objective.name)).ravel()
        violations = np.zeros(len(obj_history))
        for constraint in problem.constraints:
            g = np.array(database.get_function_history(constraint.name)).reshape(len(obj_history), -1)
            violations = np.maximum(violations, np.clip(g, 0.0, None).max(axis=1))
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        ax1.plot(np.arange(1, len(obj_history) + 1), obj_history, "-o", ms=3, color="tab:blue")
        ax1.set_ylabel("MTOM (kg)")
        ax1.set_title(f"{uc} - Problem 1 deterministic optimization convergence")
        ax2.plot(np.arange(1, len(violations) + 1), violations, "-o", ms=3, color="tab:red")
        ax2.axhline(0.0, color="grey", lw=0.8, ls="--")
        ax2.set_ylabel("max constraint violation")
        ax2.set_xlabel("iteration")
        fig.tight_layout()
        _oad.savefig(fig, f"{uc.lower()}_p1_opt_history.png")
        plt.close(fig)
        return scenario.optimization_result

    # Référence déterministe rechargée par le problème 3.
    result = _oad.cached(
        os.path.join(HERE, "data", f"{uc.lower()}_p1_optimization.pkl"), run_scenario
    )

    x_opt = {k: float(v[0]) for k, v in result.x_opt_as_dict.items()}
    print(f"\n[{uc}] Problem 1 deterministic optimum (surrogate MTOM = {float(result.f_opt):.0f} kg):")
    for name in DES:
        print(f"  {name:6s} = {x_opt[name]:.2f}")

    # Vérification sur le vrai modèle : le MTOM et les contraintes de référence.
    true = _true_at(uc, x_opt)
    print(f"  TRUE MTOM at optimum = {true['mtom']:.0f} kg")
    print("  TRUE constraints:  " + " ".join(f"{n}={true[n]:.3g}" for n in _oad.OUTPUT_NAMES if n != "mtom"))

    # Dessin de l'avion optimal (géométrie issue du vrai modèle).
    config = AircraftConfiguration(
        name=f"{uc} optimum", area=x_opt["area"], n_pax=int(round(x_opt["n_pax"])),
        slst=x_opt["slst"], span=true["span"], length=true["length"], color="tab:blue",
    )
    draw_aircraft(
        config, title=f"{uc} - Problem 1 deterministic optimum",
        file_path=os.path.join(_oad.FIG_DIR, f"{uc.lower()}_p1_aircraft.png"),
        save=True, show=False,
    )
    print(f"[{uc}] P1 optimization figures saved.")


# %%
# ## Cas d'usage 1 — Kérosène / Turbofan
run("UC1")

# %%
# ## Cas d'usage 2 — Hydrogène liquide / Turbofan
run("UC2")
