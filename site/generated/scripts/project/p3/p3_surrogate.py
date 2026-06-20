"""Problème 3 — Surrogate robuste ``f_hat(x, u)`` et sa validation.

Compare les régresseurs linéaire, RBF et krigeage sur un jeu de test, mais conserve
délibérément le krigeage : mieux calibré dans les coins peu denses de l'espace
conjoint où se trouve l'optimum. Le retenu est recoupé par validation croisée
K-fold ; les deux R2 sont superposés sur le graphe de validation.

Script lourd : lancer ``p3_doe`` d'abord. Surrogate retenu mis en cache dans
``data/`` et consommé par ``p3_optimization``.
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
# mkdocs-gallery exécute ce fichier sans ``__file__`` ; on le définit pour
# résoudre les imports et chemins ci-dessous.
if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "p3_surrogate.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gemseo import configure_logger, from_pickle

import _oad

configure_logger(level="WARNING")

HERE = os.path.dirname(os.path.abspath(__file__))


def run(uc):
    """Ajuste linéaire/RBF/krigeage sur le plan conjoint, valide, et met en cache le meilleur surrogate."""
    surrogate_path = os.path.join(HERE, "data", f"{uc.lower()}_p3_surrogate.pkl")

    def fit_and_validate():
        train = from_pickle(os.path.join(HERE, "data", f"{uc.lower()}_p3_train.pkl"))
        test = from_pickle(os.path.join(HERE, "data", f"{uc.lower()}_p3_test.pkl"))

        # Compare linéaire / RBF / krigeage, mais conserve délibérément le krigeage :
        # mieux calibré dans les coins peu denses où se trouve l'optimum.
        best_name, surrogate, results = _oad.train_and_select(
            train, test, _oad.OUTPUT_NAMES, prefer="GaussianProcessRegressor")
        print(f"\n[{uc}] Problem 3 surrogate validation (test set R2):")
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
            results, _oad.OUTPUT_NAMES, f"{uc.lower()}_p3_validation.png",
            f"{uc} - Problem 3 surrogate validation (test $R^2$ vs cross-val.)",
            cv=cv, cv_label=f"{best_name} (cross-val.)",
        )
        print(f"[{uc}] P3 surrogate fitted and validated ({best_name}).")
        return surrogate

    _oad.cached(surrogate_path, fit_and_validate)


# %%
# ## Cas d'usage 2 — Hydrogène liquide / Turbofan
run("UC2")
