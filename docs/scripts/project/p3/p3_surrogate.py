"""Problem 3 — Robust surrogate ``f̂(x, u)`` and its validation.

Trains and validates the surrogate that the robust optimization will run on.
**Linear**, **RBF** and **Kriging** (Gaussian-Process) models are compared on a
held-out test set. Here we deliberately keep the **Kriging** model: although the
three have similar global R², the Gaussian Process is better calibrated in the
data-sparse *corners* of the joint space where the optimum lives, which reduces
the systematic over-prediction of MTOM at the optimum (quantified, and corrected,
by the true-model verification in ``p3_optimization``). Because the joint DoE is
still small, a single train/test split can be optimistic, so the surrogate is
cross-checked by **K-fold cross-validation**: a CV R² close to the test R² is the
evidence it is not over-fitting. The two are overlaid on the validation chart.

Heavy script: run ``p3_doe`` first. The selected surrogate is cached in ``data/``
per use case and consumed by ``p3_optimization``.
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
# mkdocs-gallery execs this file without defining ``__file__`` (cwd is the
# script directory during execution); define it so the helpers below work.
if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "p3_surrogate.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gemseo import configure_logger, from_pickle

import _oad

configure_logger(level="WARNING")

HERE = os.path.dirname(os.path.abspath(__file__))


def run(uc):
    """Fit Linear vs RBF on the joint DoE, validate, and cache the best surrogate."""
    surrogate_path = os.path.join(HERE, "data", f"{uc.lower()}_p3_surrogate.pkl")

    def fit_and_validate():
        train = from_pickle(os.path.join(HERE, "data", f"{uc.lower()}_p3_train.pkl"))
        test = from_pickle(os.path.join(HERE, "data", f"{uc.lower()}_p3_test.pkl"))

        # Compare Linear / RBF / Kriging, but deliberately keep the Kriging
        # (Gaussian-Process) model: it is better calibrated in the data-sparse
        # corners of the joint space where the optimum lives, which reduces the
        # over-prediction of MTOM at the optimum (see the true-model verification
        # in p3_optimization). The full comparison is still plotted to justify it.
        best_name, surrogate, results = _oad.train_and_select(
            train, test, _oad.OUTPUT_NAMES, prefer="GaussianProcessRegressor")
        print(f"\n[{uc}] Problem 3 surrogate validation (test set R2):")
        for name, res in results.items():
            r2s = " ".join(f"{o}={res['R2'][o]:.3f}" for o in _oad.OUTPUT_NAMES)
            print(f"  {name:16s} {r2s}")
        print(f"  -> selected: {best_name}")

        # K-fold cross-validation of the selected surrogate (close to the test R2
        # => no over-fitting despite the small DoE).
        cv_r2 = surrogate.get_error_measure("R2Measure").compute_cross_validation_measure(as_dict=True)
        print(f"[{uc}] cross-validation R2 ({best_name}):")
        for o in _oad.OUTPUT_NAMES:
            print(f"  {o:7s} {float(cv_r2[o][0]):.3f}")

        # Overlay the CV R2 on the validation chart so it can be seen tracking the
        # single-split test R2 output by output.
        cv = {o: float(cv_r2[o][0]) for o in _oad.OUTPUT_NAMES}
        _oad.plot_validation_bars(
            results, _oad.OUTPUT_NAMES, f"{uc.lower()}_p3_validation.png",
            f"{uc} - Problem 3 surrogate validation (test $R^2$ vs cross-val.)",
            cv=cv, cv_label=f"{best_name} (cross-val.)",
        )
        print(f"[{uc}] P3 surrogate fitted and validated ({best_name}).")
        return surrogate

    # Load-or-compute: reuse the pickled surrogate if present, else fit + validate.
    _oad.cached(surrogate_path, fit_and_validate)


# %%
# ## Use Case 1 — Kerosene / Turbofan
# Skeleton for the UC1 contributor: the ``run`` helper above is use-case agnostic,
# so completing UC1 is as simple as calling ``run("UC1")`` here (or implementing a
# dedicated version).
pass

# %%
# ## Use Case 2 — Liquid H₂ / Turbofan
run("UC2")
