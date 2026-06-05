"""Problem 3 - Surrogate model of f(x, u) and its validation.

HEAVY script: loads the joint DoE datasets, trains Linear vs RBF over the joint
design+uncertain space, validates on the test set, keeps the best and pickles it
for the robust optimization step. Run ``uc*_p3_doe.py`` first.
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
# mkdocs-gallery execs this file without defining ``__file__`` (cwd is the
# script directory during execution); define it so the helpers below work.
if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "uc2_p3_surrogate.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gemseo import configure_logger, from_pickle, to_pickle

import _oad

configure_logger(level="WARNING")

UC = _oad.uc_from_filename(__file__)
HERE = os.path.dirname(os.path.abspath(__file__))

train = from_pickle(os.path.join(HERE, "data", f"{UC.lower()}_p3_train.pkl"))
test = from_pickle(os.path.join(HERE, "data", f"{UC.lower()}_p3_test.pkl"))

best_name, surrogate, results = _oad.train_and_select(train, test, _oad.OUTPUT_NAMES)
to_pickle(surrogate, os.path.join(HERE, "data", f"{UC.lower()}_p3_surrogate.pkl"))

print(f"\n[{UC}] Problem 3 surrogate validation (test set R2):")
for name, res in results.items():
    r2s = " ".join(f"{o}={res['R2'][o]:.3f}" for o in _oad.OUTPUT_NAMES)
    print(f"  {name:16s} {r2s}")
print(f"  -> selected: {best_name}")

_oad.plot_validation_bars(
    results, _oad.OUTPUT_NAMES, f"{UC.lower()}_p3_validation.png",
    f"{UC} - Problem 3 surrogate validation (test $R^2$)",
)
print(f"[{UC}] P3 surrogate saved ({best_name}).")
