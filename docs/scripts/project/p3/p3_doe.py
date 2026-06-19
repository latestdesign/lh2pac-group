"""Problème 3 — Plan d'expériences conjoint (conception + incertain).

Cette étape construit les données d'entraînement du surrogate **robuste**
``f̂(x, u) = f(x, u)``. Contrairement aux problèmes 1 et 2 (qui figent soit les
incertitudes, soit la conception), l'optimisation robuste du problème 3 exige un
surrogate valide sur **les deux** blocs à la fois : un unique plan en hypercube
latin échantillonne donc le vrai modèle OAD couplé sur l'espace *conjoint* —
4 paramètres de conception plus 3 (kérosène) ou 5 (hydrogène liquide) paramètres
incertains. L'analyse multidisciplinaire, dont la boucle de rétroaction sur la
masse est rendue explicite par le graphe de couplage exporté, est résolue à
chaque échantillon.

Script lourd (échantillonnage du vrai modèle) : à lancer avant ``p3_surrogate``
et ``p3_optimization``. Le helper ``run`` est agnostique au cas d'usage ; seul
UC2 (hydrogène liquide) est produit ici. Les jeux de données sont mis en cache
dans ``data/`` sous des noms par cas d'usage (supprimer un pickle pour
ré-échantillonner). Le plan d'expériences est tiré avec une graine fixe pour que
les R² et les figures d'optimisation robuste en aval soient reproductibles.
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
    # L'espace conjoint est de grande dimension (7-9 D) et l'optimum se situe dans
    # un *coin* (slst, n_pax sur leurs bornes inférieures). Un plan space-filling à
    # 5x-dim laisse ces coins trop clairsemés, si bien que le surrogate y
    # sur-estime le MTOM ; une étude vrai-vs-surrogate a montré que 10x-dim divise
    # à peu près par deux ce biais. On utilise donc 10x la dimension ici (encore
    # modeste pour un problème 9-D), et on vérifie l'optimum final sur le vrai
    # modèle dans p3_optimization.
    n_train = 10 * dim
    n_test = 12 * dim

    disciplines = _oad.make_disciplines(uc)

    # Graphe de couplage (condensé) : documente la MDA résolue à chaque échantillon
    # du plan d'expériences, c.-à-d. la boucle de rétroaction sur la masse au
    # décollage mtom (mass <-> total_mass <-> mission).
    generate_coupling_graph(
        disciplines,
        file_path=os.path.join(_oad.FIG_DIR, f"{uc.lower()}_p3_coupling.png"),
        full=False,
    )

    # Charger-ou-calculer : réutiliser les jeux de données picklés s'ils existent,
    # sinon échantillonner (LHS, graines distinctes pour train/test) et sauvegarder.
    # Supprimer un pickle pour ré-échantillonner.
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

    # Graphe de criblage : chaque entrée conjointe en fonction de la masse au décollage.
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
