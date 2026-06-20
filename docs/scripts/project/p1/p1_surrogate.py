"""Problème 1 — Surrogate déterministe f_hat(x) et sa validation.

Compare les régresseurs linéaire, RBF et krigeage sur un jeu de test et garde le
meilleur (R2 moyen le plus élevé), puis recoupe le retenu par validation croisée
K-fold. Les deux R2 sont superposés sur le graphe de validation.

Script lourd : lancer p1_doe d'abord. Surrogate retenu mis en cache dans
data/ et consommé par p1_optimization.
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
# mkdocs-gallery exécute ce fichier sans __file__; on le définit pour
# résoudre les imports et chemins ci-dessous.
if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "p1_surrogate.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gemseo import configure_logger, from_pickle

import _oad

configure_logger(level="WARNING")

HERE = os.path.dirname(os.path.abspath(__file__))


def run(uc):
    """Ajuste linéaire/RBF/krigeage sur le plan de conception, valide, et met en cache le meilleur surrogate."""
    surrogate_path = os.path.join(HERE, "data", f"{uc.lower()}_p1_surrogate.pkl")

    def fit_and_validate():
        train = from_pickle(os.path.join(HERE, "data", f"{uc.lower()}_p1_train.pkl"))
        test = from_pickle(os.path.join(HERE, "data", f"{uc.lower()}_p1_test.pkl"))

        # Compare linéaire / RBF / krigeage, garde le meilleur sur le jeu de test.
        best_name, surrogate, results = _oad.train_and_select(train, test, _oad.OUTPUT_NAMES)
        print(f"\n[{uc}] Problem 1 surrogate validation (test set R2):")
        for name, res in results.items():
            r2s = " ".join(f"{o}={res['R2'][o]:.3f}" for o in _oad.OUTPUT_NAMES)
            print(f"  {name:16s} {r2s}")
        print(f"  -> selected: {best_name}")

        # Validation croisée K-fold du surrogate sélectionné.
        cv_r2 = surrogate.get_error_measure("R2Measure").compute_cross_validation_measure(as_dict=True)
        print(f"[{uc}] cross-validation R2 ({best_name}):")
        for o in _oad.OUTPUT_NAMES:
            print(f"  {o:7s} {float(cv_r2[o][0]):.3f}")

        # Superpose le R2 de validation croisée au R2 de test, sortie par sortie.
        cv = {o: float(cv_r2[o][0]) for o in _oad.OUTPUT_NAMES}
        _oad.plot_validation_bars(
            results, _oad.OUTPUT_NAMES, f"{uc.lower()}_p1_validation.png",
            f"{uc} - Problem 1 surrogate validation (test $R^2$ vs cross-val.)",
            cv=cv, cv_label=f"{best_name} (cross-val.)",
        )
        print(f"[{uc}] P1 surrogate fitted and validated ({best_name}).")
        return surrogate

    _oad.cached(surrogate_path, fit_and_validate)


# %%
# ## Cas d'usage 1 — Kérosène / Turbofan
run("UC1")

# %%
# ## Cas d'usage 2 — Hydrogène liquide / Turbofan
run("UC2")
