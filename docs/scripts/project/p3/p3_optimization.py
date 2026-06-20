"""Problème 3 — Optimisation robuste sur le surrogate conjoint ``f_hat(x, u)``.

Minimise ``E[mtom]`` sous des contraintes en marge ``mean +/- k*std`` (``k = 2``),
l'espérance et les marges étant estimées par un Monte-Carlo interne sur ``u`` à
chaque itération (``gemseo-umdo``). L'optimum robuste est ensuite comparé à
l'optimum déterministe (problème 1) en propageant les mêmes incertitudes aux deux
conceptions.

``k = 2`` est un proxy de robustesse fondé sur les moments, pas une garantie
probabiliste ; les fiabilités réelles sont mesurées par Monte-Carlo ci-dessous.

Script lourd : le Monte-Carlo interne rend chaque cas d'usage long de plusieurs
minutes. Lancer ``p3_doe`` puis ``p3_surrogate`` d'abord.
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
# mkdocs-gallery exécute ce fichier sans ``__file__`` ; on le définit pour
# résoudre les imports et chemins ci-dessous.
if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "p3_optimization.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from matplotlib import pyplot as plt

from gemseo import configure_logger, create_mda, from_pickle, sample_disciplines
from gemseo.scenarios.mdo_scenario import MDOScenario
from gemseo.algos.doe.openturns.settings.ot_monte_carlo import OT_MONTE_CARLO_Settings
from gemseo_oad_training.utils import AircraftConfiguration, draw_aircraft
from lh2pac.utils import update_default_inputs
from gemseo_umdo.formulations.sampling_settings import Sampling_Settings
from gemseo_umdo.scenarios.umdo_scenario import UMDOScenario

import _oad

configure_logger(level="WARNING")

HERE = os.path.dirname(os.path.abspath(__file__))

MARGIN_FACTOR = 2.0  # k dans la marge "mean +/- k*std" (proxy fondé sur les
# moments, pas une garantie probabiliste ; fiabilités réelles mesurées par MC).
N_MC = 150           # taille du Monte-Carlo interne pour l'estimation des statistiques.
MAX_ITER = 60        # itérations de l'optimiseur (chacune lance un échantillonnage interne complet).
N_TRUE = 2000        # taille du Monte-Carlo pour la vérification sur le VRAI modèle ci-dessous.

DES = ("slst", "n_pax", "area", "ar")


def _true_nominal(uc, design):
    """Évalue le VRAI modèle couplé en un point de conception, u figé au nominal.

    Les chiffres clés sont lus ici, pas sur le surrogate (qui sur-estime le MTOM
    dans les coins). (Les grammaires AutoPyDiscipline veulent des entrées scalaires.)
    """
    disc = _oad.make_disciplines(uc)
    _oad.set_design_point(
        disc, {k: _oad.NOMINAL_UNCERTAIN[k] for k in _oad.get_uncertain_space(uc).variable_names})
    out = create_mda("MDAChain", disc).execute({k: float(design[k]) for k in DES})
    return {n: float(np.ravel(out[n])[0]) for n in _oad.OUTPUT_NAMES}


def _true_propagate(uc, design):
    """Propagation Monte-Carlo de u à travers le VRAI modèle, conception figée.

    Renvoie le MTOM espéré réel et la probabilité réelle de satisfaire chaque
    contrainte (fiabilité réelle, pas celle du surrogate).
    """
    disc = _oad.make_disciplines(uc)
    _oad.set_design_point(disc, {k: float(design[k]) for k in DES})
    dataset = sample_disciplines(
        disc, _oad.get_uncertain_space(uc), _oad.SENSITIVITY_OUTPUTS,
        algo_name="OT_MONTE_CARLO", n_samples=N_TRUE, seed=3,
    )
    mean_mtom = float(dataset.get_view(variable_names="mtom").to_numpy().mean())
    proba = {}
    for name, positive, bound in _oad.CONSTRAINTS:
        if name not in _oad.SENSITIVITY_OUTPUTS:
            continue
        values = dataset.get_view(variable_names=name).to_numpy().ravel()
        proba[name] = float(np.mean(values >= bound) if positive else np.mean(values <= bound))
    return mean_mtom, proba


def _deterministic_optimum(model, uc, start=None):
    """Optimum déterministe min-MTOM sur le surrogate, u figé au nominal.

    Repli : ``run`` préfère le pickle d'optimum déterministe du problème 1 et
    n'appelle cette fonction qu'en son absence.
    """
    nominal = {k: np.array([v]) for k, v in _oad.NOMINAL_UNCERTAIN.items()
               if k in _oad.get_uncertain_space(uc).variable_names}
    update_default_inputs([model], nominal)
    design_space = _oad.get_design_space()
    # Démarrage à chaud depuis l'optimum robuste (point faisable) : COBYLA est
    # local et stagnerait sinon depuis le point central par défaut.
    if start is not None:
        design_space.set_current_value({k: np.array([float(start[k])]) for k in DES})
    det_scenario = MDOScenario([model], _oad.OBJECTIVE, design_space,
                               formulation_name="DisciplinaryOpt")
    _oad.add_constraints(det_scenario)
    det_scenario.execute(algo_name="NLOPT_COBYLA", max_iter=200)
    return {k: float(v[0]) for k, v in det_scenario.optimization_result.x_opt_as_dict.items()}


def run(uc):
    """Optimisation robuste + comparaison déterministe pour un cas d'usage."""
    surrogate = from_pickle(os.path.join(HERE, "data", f"{uc.lower()}_p3_surrogate.pkl"))

    # Scénario robuste sur le surrogate (supprimer le pickle pour le refaire).
    def run_robust_scenario():
        settings = Sampling_Settings(doe_algo_settings=OT_MONTE_CARLO_Settings(n_samples=N_MC, seed=0))
        scenario = UMDOScenario(
            [surrogate], _oad.OBJECTIVE, _oad.get_design_space(), _oad.get_uncertain_space(uc),
            "Mean", statistic_estimation_settings=settings, formulation_name="DisciplinaryOpt",
        )
        for name, positive, bound in _oad.CONSTRAINTS:
            # "<= bound" -> mean + k*std <= bound ; ">= bound" -> mean - k*std >= bound.
            factor = -MARGIN_FACTOR if positive else MARGIN_FACTOR
            scenario.add_constraint(name, "Margin", value=bound, positive=positive, factor=factor)
        scenario.execute(algo_name="NLOPT_COBYLA", max_iter=MAX_ITER)

        # Historique de convergence (base de données du scénario, tracé au recalcul).
        problem = scenario.formulation.optimization_problem
        database = problem.database
        obj_history = np.array(database.get_function_history(problem.objective.name)).ravel()
        violations = np.zeros(len(obj_history))
        for constraint in problem.constraints:
            g = np.array(database.get_function_history(constraint.name)).reshape(len(obj_history), -1)
            violations = np.maximum(violations, np.clip(g, 0.0, None).max(axis=1))
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        ax1.plot(np.arange(1, len(obj_history) + 1), obj_history, "-o", ms=3, color="tab:green")
        ax1.set_ylabel("E[MTOM] (kg)")
        ax1.set_title(f"{uc} - Problem 3 robust optimization convergence")
        ax2.plot(np.arange(1, len(violations) + 1), violations, "-o", ms=3, color="tab:red")
        ax2.axhline(0.0, color="grey", lw=0.8, ls="--")
        ax2.set_ylabel("max margin violation")
        ax2.set_xlabel("iteration")
        fig.tight_layout()
        _oad.savefig(fig, f"{uc.lower()}_p3_robust_history.png")
        plt.close(fig)
        return scenario.optimization_result

    result = _oad.cached(
        os.path.join(HERE, "data", f"{uc.lower()}_p3_optimization.pkl"), run_robust_scenario
    )

    x_robust = {k: float(v[0]) for k, v in result.x_opt_as_dict.items()}
    print(f"\n[{uc}] Problem 3 robust optimum (E[MTOM] = {float(result.f_opt):.0f} kg):")
    for name in ("slst", "n_pax", "area", "ar"):
        print(f"  {name:6s} = {x_robust[name]:.2f}")

    # Optimum déterministe (problème 1) pour comparaison : pickle P1 si présent,
    # sinon recalcul sur le même surrogate.
    det_path = os.path.join(HERE, "..", "p1", "data", f"{uc.lower()}_p1_optimization.pkl")
    if os.path.exists(det_path):
        x_det = {k: float(v[0]) for k, v in from_pickle(det_path).x_opt_as_dict.items()}
    else:
        x_det = _deterministic_optimum(surrogate, uc, start=x_robust)
    print(f"  deterministic optimum: " + " ".join(f"{k}={x_det[k]:.2f}" for k in DES))

    # ---- VÉRIFICATION SUR LE VRAI MODÈLE ---------------------------------- #
    # Le surrogate ne sert qu'à chercher ; les chiffres rapportés sont lus sur le
    # vrai modèle. D'abord le point nominal (1 MDA chacun).
    det_true, rob_true = _true_nominal(uc, x_det), _true_nominal(uc, x_robust)
    nominal_u = {k: np.array([v]) for k, v in _oad.NOMINAL_UNCERTAIN.items()
                 if k in _oad.get_uncertain_space(uc).variable_names}

    def surr_nominal_mtom(design):
        out = surrogate.execute({**{k: np.array([design[k]]) for k in DES}, **nominal_u})
        return float(np.ravel(out["mtom"])[0])

    print("  nominal MTOM  surrogate / TRUE  (the surrogate over-predicts at the optimum):")
    print(f"    deterministic {surr_nominal_mtom(x_det):.0f} / {det_true['mtom']:.0f} kg")
    print(f"    robust        {surr_nominal_mtom(x_robust):.0f} / {rob_true['mtom']:.0f} kg")

    # ---- Avion robuste vs déterministe (géométrie du vrai modèle) ---------- #
    det_config = AircraftConfiguration(
        name="Deterministic (P1)", area=x_det["area"], n_pax=int(round(x_det["n_pax"])),
        slst=x_det["slst"], span=det_true["span"], length=det_true["length"], color="tab:blue",
    )
    rob_config = AircraftConfiguration(
        name="Robust (P3)", area=x_robust["area"], n_pax=int(round(x_robust["n_pax"])),
        slst=x_robust["slst"], span=rob_true["span"], length=rob_true["length"], color="tab:green",
    )
    draw_aircraft(
        det_config, rob_config, title=f"{uc} - deterministic vs robust optimum",
        file_path=os.path.join(_oad.FIG_DIR, f"{uc.lower()}_p3_robust_vs_det.png"),
        save=True, show=False,
    )

    # ---- Contrôle de robustesse sur le VRAI modèle ------------------------ #
    # Propage u à travers le vrai modèle à chaque conception figée : MTOM espéré réel
    # et P(contrainte satisfaite) réelle.
    constrained = [(n, p, b) for n, p, b in _oad.CONSTRAINTS if n in _oad.SENSITIVITY_OUTPUTS]
    det_mtom, det_p = _true_propagate(uc, x_det)
    rob_mtom, rob_p = _true_propagate(uc, x_robust)
    print(f"  TRUE E[MTOM] deterministic design = {det_mtom:.0f} kg")
    print(f"  TRUE E[MTOM] robust design        = {rob_mtom:.0f} kg")
    print(f"  price of robustness               = {rob_mtom - det_mtom:+.0f} kg")
    print("  TRUE P(constraint satisfied)  deterministic / robust:")
    for name, _, _ in constrained:
        print(f"    {name:5s} {det_p[name]:6.1%} / {rob_p[name]:6.1%}")

    names = [n for n, _, _ in constrained]
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(x - 0.2, [det_p[n] for n in names], 0.4, label="deterministic (P1)", color="tab:blue")
    ax.bar(x + 0.2, [rob_p[n] for n in names], 0.4, label="robust (P3)", color="tab:green")
    ax.axhline(1.0, color="grey", lw=0.8, ls="--")
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel("P(constraint satisfied)")
    ax.set_ylim(0, 1.08)
    ax.set_title(f"{uc} - true-model constraint reliability: deterministic vs robust")
    ax.legend()
    _oad.savefig(fig, f"{uc.lower()}_p3_feasibility.png")
    plt.close(fig)
    print(f"[{uc}] P3 robust optimization figures saved.")


# %%
# ## Cas d'usage 2 — Hydrogène liquide / Turbofan
run("UC2")
