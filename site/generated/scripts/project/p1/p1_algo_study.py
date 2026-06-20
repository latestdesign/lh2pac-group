"""Problème 1 — Étude du choix de l'algorithme d'optimisation (COBYLA vs SLSQP).

Compare NLOPT_COBYLA (sans gradient, région de confiance) et SLSQP (par
gradient) sur le vrai modèle couplé (u gelé au nominal), pour plusieurs budgets
d'itérations, via le MTOM optimal et les historiques de convergence.

Script lourd (optimisation sur le vrai modèle, plusieurs exécutions).
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "p1_algo_study.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from matplotlib import pyplot as plt

from gemseo import configure_logger
from gemseo.scenarios.mdo_scenario import MDOScenario

import _oad

configure_logger(level="WARNING")

ALGORITHMS = ("NLOPT_COBYLA", "SLSQP")
MAX_ITERS = (50, 100, 500)


def _optimize(disciplines, algo_name, max_iter):
    """Résolution déterministe sur le vrai modèle (MDF) ; renvoie (f_opt, historique objectif)."""
    scenario = MDOScenario(disciplines, _oad.OBJECTIVE, _oad.get_design_space(),
                           formulation_name="MDF")
    _oad.add_constraints(scenario)
    scenario.execute(algo_name=algo_name, max_iter=max_iter)
    problem = scenario.formulation.optimization_problem
    obj_history = np.array(
        problem.database.get_function_history(problem.objective.name)).ravel()
    return float(scenario.optimization_result.f_opt), obj_history


def run(uc):
    """Compare COBYLA et SLSQP sur le vrai modèle pour un cas d'usage."""
    disciplines = _oad.make_disciplines(uc)
    # Problème déterministe : incertitudes gelées au nominal.
    _oad.set_design_point(
        disciplines,
        {k: _oad.NOMINAL_UNCERTAIN[k] for k in _oad.get_uncertain_space(uc).variable_names})

    # Tableau de comparaison f_opt(algo, max_iter).
    table = {algo: {} for algo in ALGORITHMS}
    histories = {}
    for algo in ALGORITHMS:
        for max_iter in MAX_ITERS:
            f_opt, history = _optimize(disciplines, algo, max_iter)
            table[algo][max_iter] = f_opt
            histories[(algo, max_iter)] = history

    print(f"\n[{uc}] Étude des algorithmes du problème 1 — MTOM optimal (kg) :")
    header = "  max_iter " + " ".join(f"{a:>14s}" for a in ALGORITHMS)
    print(header)
    for max_iter in MAX_ITERS:
        row = " ".join(f"{table[a][max_iter]:14.1f}" for a in ALGORITHMS)
        print(f"  {max_iter:8d} {row}")

    # Figure : historiques de convergence des deux algorithmes (budget de 100).
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = {"NLOPT_COBYLA": "tab:blue", "SLSQP": "tab:orange"}
    for algo in ALGORITHMS:
        history = histories[(algo, 100)]
        ax.plot(np.arange(1, len(history) + 1), history, "-o", ms=3,
                color=colors[algo], label=algo)
    ax.set_xlabel("iteration")
    ax.set_ylabel("MTOM (kg)")
    ax.set_title(f"{uc} - Problem 1 optimizer convergence (max_iter = 100)")
    ax.legend()
    _oad.savefig(fig, f"{uc.lower()}_p1_algo_study.png")
    plt.close(fig)
    print(f"[{uc}] Étude des algorithmes du problème 1 : figure sauvegardée.")


# %%
# ## Cas d'usage 1 — Kérosène / Turbofan
run("UC1")

# %%
# ## Cas d'usage 2 — Hydrogène liquide / Turbofan
run("UC2")
