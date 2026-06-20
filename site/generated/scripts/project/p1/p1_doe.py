"""Problème 1 — Plan d'expériences déterministe (espace de conception seul).

Échantillonne le vrai modèle couplé sur les 4 paramètres de conception
x = (slst, n_pax, area, ar), incertitudes gelées au nominal, pour entraîner le
surrogate déterministe f_hat(x). Exporte aussi le graphe de couplage de la MDA.

Script lourd : à lancer avant p1_surrogate et p1_optimization. Jeux de
données mis en cache dans data/ (supprimer un pickle pour ré-échantillonner);
graine fixe pour la reproductibilité.
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
# mkdocs-gallery exécute ce fichier sans __file__; on le définit pour
# résoudre les imports et chemins ci-dessous.
if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "p1_doe.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matplotlib import pyplot as plt

from gemseo import configure_logger, generate_coupling_graph, sample_disciplines

import _oad

configure_logger(level="WARNING")

HERE = os.path.dirname(os.path.abspath(__file__))


def run(uc):
    """Échantillonne le vrai modèle couplé sur l'espace de conception (u au nominal)."""
    design_space = _oad.get_design_space()
    dim = len(design_space.variable_names)  # 4 paramètres de conception
    # Plan space-filling à ~10x la dimension (qualité vérifiée dans p1_surrogate).
    n_train = 10 * dim
    n_test = 12 * dim

    disciplines = _oad.make_disciplines(uc)
    # Incertitudes gelées au nominal : seul x varie dans le plan.
    _oad.set_design_point(
        disciplines,
        {k: _oad.NOMINAL_UNCERTAIN[k] for k in _oad.get_uncertain_space(uc).variable_names},
    )

    # Graphe de couplage (condensé) de la MDA résolue à chaque échantillon.
    generate_coupling_graph(
        disciplines,
        file_path=os.path.join(_oad.FIG_DIR, f"{uc.lower()}_p1_coupling.png"),
        full=False,
    )

    # LHS, graines distinctes train/test (réutilise les pickles s'ils existent).
    train = _oad.cached(
        os.path.join(HERE, "data", f"{uc.lower()}_p1_train.pkl"),
        lambda: sample_disciplines(disciplines, _oad.get_design_space(), _oad.OUTPUT_NAMES,
                                   algo_name="OT_OPT_LHS", n_samples=n_train, seed=0),
    )
    test = _oad.cached(
        os.path.join(HERE, "data", f"{uc.lower()}_p1_test.pkl"),
        lambda: sample_disciplines(disciplines, _oad.get_design_space(), _oad.OUTPUT_NAMES,
                                   algo_name="OT_OPT_LHS", n_samples=n_test, seed=1),
    )

    # Graphe de criblage : chaque paramètre de conception vs MTOM.
    mtom = train.get_view(variable_names="mtom").to_numpy().ravel()
    names = list(design_space.variable_names)
    ncols = 2
    nrows = (len(names) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(4 * ncols, 3 * nrows))
    for ax, name in zip(axes.ravel(), names):
        col = train.get_view(variable_names=name).to_numpy().ravel()
        ax.scatter(col, mtom, s=18, c="tab:blue")
        ax.set_xlabel(name)
        ax.set_ylabel("mtom")
    for ax in axes.ravel()[len(names):]:
        ax.axis("off")
    fig.suptitle(f"{uc} - Problem 1 DoE: design inputs vs MTOM ({n_train} LHS samples)")
    fig.tight_layout()
    _oad.savefig(fig, f"{uc.lower()}_p1_doe.png")
    plt.close(fig)
    print(f"[{uc}] P1 DoE done: {n_train} train / {n_test} test samples ({dim} inputs).")


# %%
# ## Cas d'usage 1 — Kérosène / Turbofan
run("UC1")

# %%
# ## Cas d'usage 2 — Hydrogène liquide / Turbofan
run("UC2")
