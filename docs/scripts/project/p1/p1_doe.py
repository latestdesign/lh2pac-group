"""Problème 1 — Plan d'expériences déterministe (espace de conception seul).

Le problème 1 fige les incertitudes technologiques à leurs valeurs nominales et
n'étudie que les 4 paramètres de conception x = (slst, n_pax, area, ar). Cette
étape échantillonne le vrai modèle OAD couplé sur le seul espace de conception
(u gelé au nominal) afin d'entraîner le surrogate déterministe f̂(x) ≈ f(x, u_nom)
des étapes suivantes. La boucle de rétroaction sur la masse au décollage est
résolue par une analyse multidisciplinaire (MDA) à chaque échantillon ; le graphe
de couplage condensé est exporté pour documentation.

Script lourd (échantillonnage du vrai modèle) : à lancer avant ``p1_surrogate``
et ``p1_optimization``. Les deux cas d'usage (UC1 kérosène, UC2 hydrogène
liquide) sont produits ci-dessous ; les jeux de données sont mis en cache dans
``data/`` (supprimer un pickle pour ré-échantillonner). Le plan est tiré avec une
graine fixe pour des résultats reproductibles.
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
# mkdocs-gallery exécute ce fichier sans définir ``__file__`` (le répertoire
# courant est celui du script pendant l'exécution) ; on le définit pour que les
# helpers ci-dessous fonctionnent.
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
    # Petit plan space-filling : on reste sobre (≈ 10x la dimension), conforme à la
    # règle "3 à 5 fois la dimension d'entrée" élargie pour des sorties non
    # linéaires (tofl notamment). La qualité est vérifiée dans p1_surrogate.
    n_train = 10 * dim
    n_test = 12 * dim

    disciplines = _oad.make_disciplines(uc)
    # Problème déterministe : on gèle les paramètres incertains à leur valeur
    # nominale, seul x varie ensuite dans le plan d'expériences.
    _oad.set_design_point(
        disciplines,
        {k: _oad.NOMINAL_UNCERTAIN[k] for k in _oad.get_uncertain_space(uc).variable_names},
    )

    # Graphe de couplage (condensé) : documente la MDA résolue à chaque échantillon
    # (boucle de rétroaction mass <-> total_mass <-> mission sur la masse mtom).
    generate_coupling_graph(
        disciplines,
        file_path=os.path.join(_oad.FIG_DIR, f"{uc.lower()}_p1_coupling.png"),
        full=False,
    )

    # Charger-ou-calculer : réutiliser les jeux picklés s'ils existent, sinon
    # échantillonner (LHS, graines distinctes train/test). Supprimer un pickle pour
    # ré-échantillonner.
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

    # Graphe de criblage : chaque paramètre de conception en fonction du MTOM.
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
