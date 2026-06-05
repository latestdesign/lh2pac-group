"""Problem 3 - Design of Experiments over the joint (design + uncertain) space.

HEAVY script: samples the true coupled model ``f(x, u)`` over BOTH the design
parameters and the uncertain parameters, to build a single surrogate usable for
robust optimization. Design variables are sampled uniformly on their bounds.
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
# mkdocs-gallery execs this file without defining ``__file__`` (cwd is the
# script directory during execution); define it so the helpers below work.
if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "uc2_p3_doe.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matplotlib import pyplot as plt

from gemseo import configure_logger, sample_disciplines, to_pickle

import _oad

configure_logger(level="WARNING")

UC = _oad.uc_from_filename(__file__)
HERE = os.path.dirname(os.path.abspath(__file__))

joint_space = _oad.get_joint_space(UC)
dim = len(joint_space.variable_names)
n_train = 5 * dim
n_test = 12 * dim

disciplines = _oad.make_disciplines(UC)
train = sample_disciplines(disciplines, _oad.get_joint_space(UC), _oad.OUTPUT_NAMES,
                           algo_name="OT_OPT_LHS", n_samples=n_train)
test = sample_disciplines(disciplines, _oad.get_joint_space(UC), _oad.OUTPUT_NAMES,
                          algo_name="OT_OPT_LHS", n_samples=n_test)

to_pickle(train, os.path.join(HERE, "data", f"{UC.lower()}_p3_train.pkl"))
to_pickle(test, os.path.join(HERE, "data", f"{UC.lower()}_p3_test.pkl"))

# Screening plot: design and uncertain variables against MTOM.
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
fig.suptitle(f"{UC} - Problem 3 DoE: joint inputs vs MTOM ({n_train} LHS samples)")
fig.tight_layout()
_oad.savefig(fig, f"{UC.lower()}_p3_doe.png")
plt.close(fig)
print(f"[{UC}] P3 DoE done: {n_train} train / {n_test} test samples ({dim} inputs).")
