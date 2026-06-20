"""Problème 3 — Plan d'expériences conjoint (conception + incertain).

Construit les données d'entraînement du surrogate robuste f_hat(x, u). Un seul
plan en hypercube latin échantillonne le vrai modèle couplé sur l'espace conjoint :
4 paramètres de conception plus 3 (kérosène) ou 5 (hydrogène liquide) paramètres
incertains. Exporte aussi le graphe de couplage de la MDA.

Script lourd : à lancer avant p3_surrogate et p3_optimization. Seul UC2 est
produit ici. Jeux de données mis en cache dans data/ (supprimer un pickle pour
ré-échantillonner); graine fixe pour la reproductibilité.
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
# mkdocs-gallery exécute ce fichier sans __file__; on le définit pour
# résoudre les imports et chemins ci-dessous.
if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "p3_doe.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matplotlib import pyplot as plt

from gemseo import configure_logger, generate_coupling_graph, sample_disciplines

import _oad

configure_logger(level="WARNING")

HERE = os.path.dirname(os.path.abspath(__file__))


def run(uc):
    """Échantillonne le vrai modèle couplé sur l'espace conjoint (conception + incertain)."""
    joint_space = _oad.get_joint_space(uc)
    dim = len(joint_space.variable_names)
    # Espace conjoint de grande dimension (7-9 D), optimum dans un coin : plan
    # space-filling à 10x la dimension (meilleure couverture des coins qu'à 5x).
    # L'optimum final est vérifié sur le vrai modèle dans p3_optimization.
    n_train = 10 * dim
    n_test = 12 * dim

    disciplines = _oad.make_disciplines(uc)

    # Graphe de couplage (condensé) de la MDA résolue à chaque échantillon.
    generate_coupling_graph(
        disciplines,
        file_path=os.path.join(_oad.FIG_DIR, f"{uc.lower()}_p3_coupling.png"),
        full=False,
    )

    # LHS, graines distinctes train/test (réutilise les pickles s'ils existent).
    train = _oad.cached(
        os.path.join(HERE, "data", f"{uc.lower()}_p3_train.pkl"),
        lambda: sample_disciplines(disciplines, _oad.get_joint_space(uc), _oad.OUTPUT_NAMES,
                                   algo_name="OT_OPT_LHS", n_samples=n_train, seed=0),
    )
    test = _oad.cached(
        os.path.join(HERE, "data", f"{uc.lower()}_p3_test.pkl"),
        lambda: sample_disciplines(disciplines, _oad.get_joint_space(uc), _oad.OUTPUT_NAMES,
                                   algo_name="OT_OPT_LHS", n_samples=n_test, seed=1),
    )

    # Graphe de criblage : chaque entrée conjointe vs MTOM.
    mtom = train.get_view(variable_names="mtom").to_numpy().ravel()
    names = list(joint_space.variable_names)
    ncols = 3
    nrows = (len(names) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(4 * ncols, 3 * nrows))
    for ax, name in zip(axes.ravel(), names):
        col = train.get_view(variable_names=name).to_numpy().ravel()
        ax.scatter(col, mtom, s=18, c="tab:green")
        ax.set_xlabel(name)
        ax.set_ylabel("mtom")
    for ax in axes.ravel()[len(names):]:
        ax.axis("off")
    fig.suptitle(f"{uc} - Problem 3 DoE: joint inputs vs MTOM ({n_train} LHS samples)")
    fig.tight_layout()
    _oad.savefig(fig, f"{uc.lower()}_p3_doe.png")
    plt.close(fig)
    print(f"[{uc}] P3 DoE done: {n_train} train / {n_test} test samples ({dim} inputs).")


# %%
# ## Cas d'usage 2 — Hydrogène liquide / Turbofan
run("UC2")
