"""Problem 3 — Joint design + uncertain Design of Experiments.

This step builds the training data for the **robust** surrogate ``f̂(x, u) = f(x, u)``.
Unlike Problems 1 and 2 (which fix either the uncertainties or the design), the
robust optimization of Problem 3 needs a surrogate valid over **both** blocks at
once, so a single Latin-Hypercube design samples the true coupled OAD model over
the *joint* space — 4 design parameters plus 3 (kerosene) or 5 (liquid H₂)
uncertain parameters. The multidisciplinary analysis, whose mass feedback loop is
made explicit by the exported coupling graph, is solved at every sample.

Heavy script (true-model sampling): run this before ``p3_surrogate`` and
``p3_optimization``. Both use cases are produced below; the datasets are cached
in ``data/`` under per-use-case names (delete a pickle to resample). The DoE is
seeded so the downstream R² and robust-optimization figures are reproducible.
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
# mkdocs-gallery execs this file without defining ``__file__`` (cwd is the
# script directory during execution); define it so the helpers below work.
if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "p3_doe.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matplotlib import pyplot as plt

from gemseo import configure_logger, generate_coupling_graph, sample_disciplines

import _oad

configure_logger(level="WARNING")

HERE = os.path.dirname(os.path.abspath(__file__))


def run(uc):
    """Sample the true coupled model over the joint (design + uncertain) space."""
    joint_space = _oad.get_joint_space(uc)
    dim = len(joint_space.variable_names)
    # The joint space is high-dimensional (7-9 D) and the optimum sits in a
    # *corner* (slst, n_pax on their lower bounds). A 5x-dim space-filling DoE
    # leaves those corners too sparse, so the surrogate over-predicts MTOM there;
    # a true-vs-surrogate study showed 10x-dim roughly halves that bias. We
    # therefore use 10x dimension here (still small for a 9-D problem), and verify
    # the final optimum on the true model in p3_optimization.
    n_train = 10 * dim
    n_test = 12 * dim

    disciplines = _oad.make_disciplines(uc)

    # Coupling graph (condensed): documents the MDA solved at every DoE sample,
    # i.e. the feedback loop on the take-off mass mtom (mass <-> total_mass <->
    # mission).
    generate_coupling_graph(
        disciplines,
        file_path=os.path.join(_oad.FIG_DIR, f"{uc.lower()}_p3_coupling.png"),
        full=False,
    )

    # Load-or-compute: reuse the pickled datasets if present, else sample (LHS,
    # distinct seeds for train/test) and save. Delete a pickle to resample.
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

    # Screening plot: each joint input against the take-off mass.
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
# ## Use Case 1 — Kerosene / Turbofan
# Skeleton for the UC1 contributor: the ``run`` helper above is use-case agnostic,
# so completing UC1 is as simple as calling ``run("UC1")`` here (or implementing a
# dedicated version).
pass

# %%
# ## Use Case 2 — Liquid H₂ / Turbofan
run("UC2")
