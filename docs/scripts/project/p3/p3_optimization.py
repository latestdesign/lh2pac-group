"""Problem 3 — Robust optimization on the joint surrogate ``f̂(x, u)``.

Minimizes the **expected** maximum take-off mass ``E[mtom]`` while enforcing every
operational constraint with a safety margin ``mean ± k·std`` (here ``k = 2``), so
the design stays feasible despite the technological uncertainties. The expected
value and the margins are estimated by an **inner Monte-Carlo** over ``u`` at every
optimizer iteration (``gemseo-umdo``). The robust optimum is then compared to the
**deterministic** optimum (Problem 1) by propagating the same uncertainties
through the surrogate at both designs — this quantifies the *price of robustness*
and the gain in constraint reliability.

The ``k = 2`` margin is a **moment-based robustness proxy**, not a probabilistic
guarantee: with non-Gaussian (triangular, nonlinear) outputs it does not certify a
97.7 % reliability — the actual reliabilities are *measured* by Monte-Carlo below.

Heavy script: although it only evaluates the cheap surrogate, the inner
Monte-Carlo makes each use case minutes-long. Run ``p3_doe`` then ``p3_surrogate``
first. Results/figures are cached/committed per use case.
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
# mkdocs-gallery execs this file without defining ``__file__`` (cwd is the
# script directory during execution); define it so the helpers below work.
if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "p3_optimization.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from matplotlib import pyplot as plt

from gemseo import configure_logger, create_mda, from_pickle, sample_disciplines
from gemseo.scenarios.mdo_scenario import MDOScenario
from gemseo.algos.doe.openturns.settings.ot_monte_carlo import OT_MONTE_CARLO_Settings
from gemseo_oad_training.utils import AircraftConfiguration, draw_aircraft
from lh2pac.utils import update_default_inputs
from gemseo_umdo.formulations.sampling_settings import Sampling_Settings
from gemseo_umdo.scenarios.umdo_scenario import UMDOScenario

import _oad

configure_logger(level="WARNING")

HERE = os.path.dirname(os.path.abspath(__file__))

MARGIN_FACTOR = 2.0  # k in "mean +/- k*std" margin constraint. NB: the ~97.7%
# one-sided reliability only holds if the output is Gaussian; here outputs are
# triangular-fed and nonlinear, so this is a moment-based proxy (Chebyshev only
# guarantees >=80% for k=2). Actual reliabilities are measured by MC below.
N_MC = 150           # inner Monte-Carlo size for statistic estimation.
MAX_ITER = 60        # optimizer iterations (each runs a full inner sampling).
N_TRUE = 2000        # Monte-Carlo size for the TRUE-model verification below.

DES = ("slst", "n_pax", "area", "ar")


def _true_nominal(uc, design):
    """Evaluate the TRUE coupled model at a design point, u frozen at nominal.

    The surrogate over-predicts MTOM by ~2% in the design-space corners where the
    optimum sits, so the headline numbers must be read off the true model, not the
    surrogate. (AutoPyDiscipline grammars want scalar inputs.)
    """
    disc = _oad.make_disciplines(uc)
    _oad.set_design_point(
        disc, {k: _oad.NOMINAL_UNCERTAIN[k] for k in _oad.get_uncertain_space(uc).variable_names})
    out = create_mda("MDAChain", disc).execute({k: float(design[k]) for k in DES})
    return {n: float(np.ravel(out[n])[0]) for n in _oad.OUTPUT_NAMES}


def _true_propagate(uc, design):
    """Monte-Carlo propagation of u through the TRUE model at a fixed design.

    Returns the true expected MTOM and the true probability of satisfying each
    (uncertainty-dependent) constraint -- the honest reliability, not the
    surrogate's. The design is frozen and the uncertain parameters are sampled.
    """
    disc = _oad.make_disciplines(uc)
    _oad.set_design_point(disc, {k: float(design[k]) for k in DES})
    dataset = sample_disciplines(
        disc, _oad.get_uncertain_space(uc), _oad.SENSITIVITY_OUTPUTS,
        algo_name="OT_MONTE_CARLO", n_samples=N_TRUE, seed=3,
    )
    mean_mtom = float(dataset.get_view(variable_names="mtom").to_numpy().mean())
    proba = {}
    for name, positive, bound in _oad.CONSTRAINTS:
        if name not in _oad.SENSITIVITY_OUTPUTS:
            continue
        values = dataset.get_view(variable_names=name).to_numpy().ravel()
        proba[name] = float(np.mean(values >= bound) if positive else np.mean(values <= bound))
    return mean_mtom, proba


def _deterministic_optimum(model, uc, start=None):
    """Min-MTOM optimum on the surrogate with u frozen at nominal.

    The deterministic baseline is, by definition, argmin MTOM(x, u=nominal) under
    the six constraints; computing that on the same surrogate gives exactly that
    optimum -- the correct baseline, just computed in-place.

    TODO(once contributions are merged): prefer the real Problem-1 deterministic
    optimum. CAVEAT to revisit then: a dedicated P1 fits its surrogate on a
    *design-only* DoE (no u axis), which can be marginally sharper in the design
    subspace and shift the optimum slightly. Same baseline, same method -- only the
    surrogate it is read off differs. The load below already prefers the P1 pickle
    when it exists, so this self-corrects once P1 lands.
    """
    nominal = {k: np.array([v]) for k, v in _oad.NOMINAL_UNCERTAIN.items()
               if k in _oad.get_uncertain_space(uc).variable_names}
    update_default_inputs([model], nominal)
    design_space = _oad.get_design_space()
    # Warm-start from a known-good feasible point (the robust optimum): COBYLA is
    # local and otherwise stalls in a poor basin from the default centre start.
    if start is not None:
        design_space.set_current_value({k: np.array([float(start[k])]) for k in DES})
    det_scenario = MDOScenario([model], _oad.OBJECTIVE, design_space,
                               formulation_name="DisciplinaryOpt")
    _oad.add_constraints(det_scenario)
    det_scenario.execute(algo_name="NLOPT_COBYLA", max_iter=200)
    return {k: float(v[0]) for k, v in det_scenario.optimization_result.x_opt_as_dict.items()}


def run(uc):
    """Robust optimization + deterministic comparison for one use case."""
    surrogate = from_pickle(os.path.join(HERE, "data", f"{uc.lower()}_p3_surrogate.pkl"))

    # Robust scenario: minimise E[mtom] under margin constraints, using the
    # surrogate. The inner Monte-Carlo makes this the ~minutes-long step, so it is
    # cached; delete the optimization pickle to redo it (and its history figure).
    def run_robust_scenario():
        settings = Sampling_Settings(doe_algo_settings=OT_MONTE_CARLO_Settings(n_samples=N_MC, seed=0))
        scenario = UMDOScenario(
            [surrogate], _oad.OBJECTIVE, _oad.get_design_space(), _oad.get_uncertain_space(uc),
            "Mean", statistic_estimation_settings=settings, formulation_name="DisciplinaryOpt",
        )
        for name, positive, bound in _oad.CONSTRAINTS:
            # "<= bound" -> mean + k*std <= bound ; ">= bound" -> mean - k*std >= bound.
            factor = -MARGIN_FACTOR if positive else MARGIN_FACTOR
            scenario.add_constraint(name, "Margin", value=bound, positive=positive, factor=factor)
        scenario.execute(algo_name="NLOPT_COBYLA", max_iter=MAX_ITER)

        # Convergence history (needs the live scenario database -> drawn here, on a
        # recompute only).
        problem = scenario.formulation.optimization_problem
        database = problem.database
        obj_history = np.array(database.get_function_history(problem.objective.name)).ravel()
        violations = np.zeros(len(obj_history))
        for constraint in problem.constraints:
            g = np.array(database.get_function_history(constraint.name)).reshape(len(obj_history), -1)
            violations = np.maximum(violations, np.clip(g, 0.0, None).max(axis=1))
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        ax1.plot(np.arange(1, len(obj_history) + 1), obj_history, "-o", ms=3, color="tab:green")
        ax1.set_ylabel("E[MTOM] (kg)")
        ax1.set_title(f"{uc} - Problem 3 robust optimization convergence")
        ax2.plot(np.arange(1, len(violations) + 1), violations, "-o", ms=3, color="tab:red")
        ax2.axhline(0.0, color="grey", lw=0.8, ls="--")
        ax2.set_ylabel("max margin violation")
        ax2.set_xlabel("iteration")
        fig.tight_layout()
        _oad.savefig(fig, f"{uc.lower()}_p3_robust_history.png")
        plt.close(fig)
        return scenario.optimization_result

    result = _oad.cached(
        os.path.join(HERE, "data", f"{uc.lower()}_p3_optimization.pkl"), run_robust_scenario
    )

    x_robust = {k: float(v[0]) for k, v in result.x_opt_as_dict.items()}
    print(f"\n[{uc}] Problem 3 robust optimum (E[MTOM] = {float(result.f_opt):.0f} kg):")
    for name in ("slst", "n_pax", "area", "ar"):
        print(f"  {name:6s} = {x_robust[name]:.2f}")

    # Deterministic optimum (Problem 1) for comparison: the real P1 pickle when it
    # exists, else recompute the baseline in-place on the same surrogate.
    det_path = os.path.join(HERE, "..", "p1", "data", f"{uc.lower()}_p1_optimization.pkl")
    if os.path.exists(det_path):
        x_det = {k: float(v[0]) for k, v in from_pickle(det_path).x_opt_as_dict.items()}
    else:
        x_det = _deterministic_optimum(surrogate, uc, start=x_robust)
    print(f"  deterministic optimum: " + " ".join(f"{k}={x_det[k]:.2f}" for k in DES))

    # ---- TRUE-MODEL VERIFICATION ------------------------------------------ #
    # The surrogate is only used to *search*; the reported numbers are read off
    # the true coupled model. First the nominal point (1 MDA each): this is the
    # headline MTOM, and it exposes the surrogate's optimism at the optimum.
    det_true, rob_true = _true_nominal(uc, x_det), _true_nominal(uc, x_robust)
    nominal_u = {k: np.array([v]) for k, v in _oad.NOMINAL_UNCERTAIN.items()
                 if k in _oad.get_uncertain_space(uc).variable_names}

    def surr_nominal_mtom(design):
        out = surrogate.execute({**{k: np.array([design[k]]) for k in DES}, **nominal_u})
        return float(np.ravel(out["mtom"])[0])

    print("  nominal MTOM  surrogate / TRUE  (the surrogate over-predicts at the optimum):")
    print(f"    deterministic {surr_nominal_mtom(x_det):.0f} / {det_true['mtom']:.0f} kg")
    print(f"    robust        {surr_nominal_mtom(x_robust):.0f} / {rob_true['mtom']:.0f} kg")

    # ---- Robust vs deterministic aircraft (true-model geometry) ----------- #
    det_config = AircraftConfiguration(
        name="Deterministic (P1)", area=x_det["area"], n_pax=int(round(x_det["n_pax"])),
        slst=x_det["slst"], span=det_true["span"], length=det_true["length"], color="tab:blue",
    )
    rob_config = AircraftConfiguration(
        name="Robust (P3)", area=x_robust["area"], n_pax=int(round(x_robust["n_pax"])),
        slst=x_robust["slst"], span=rob_true["span"], length=rob_true["length"], color="tab:green",
    )
    draw_aircraft(
        det_config, rob_config, title=f"{uc} - deterministic vs robust optimum",
        file_path=os.path.join(_oad.FIG_DIR, f"{uc.lower()}_p3_robust_vs_det.png"),
        save=True, show=False,
    )

    # ---- Robustness check on the TRUE model ------------------------------- #
    # Propagate u through the true model at each fixed design: the honest expected
    # MTOM (fair "price of robustness") and the true P(constraint satisfied).
    constrained = [(n, p, b) for n, p, b in _oad.CONSTRAINTS if n in _oad.SENSITIVITY_OUTPUTS]
    det_mtom, det_p = _true_propagate(uc, x_det)
    rob_mtom, rob_p = _true_propagate(uc, x_robust)
    print(f"  TRUE E[MTOM] deterministic design = {det_mtom:.0f} kg")
    print(f"  TRUE E[MTOM] robust design        = {rob_mtom:.0f} kg")
    print(f"  price of robustness               = {rob_mtom - det_mtom:+.0f} kg")
    print("  TRUE P(constraint satisfied)  deterministic / robust:")
    for name, _, _ in constrained:
        print(f"    {name:5s} {det_p[name]:6.1%} / {rob_p[name]:6.1%}")

    names = [n for n, _, _ in constrained]
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(x - 0.2, [det_p[n] for n in names], 0.4, label="deterministic (P1)", color="tab:blue")
    ax.bar(x + 0.2, [rob_p[n] for n in names], 0.4, label="robust (P3)", color="tab:green")
    ax.axhline(1.0, color="grey", lw=0.8, ls="--")
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel("P(constraint satisfied)")
    ax.set_ylim(0, 1.08)
    ax.set_title(f"{uc} - true-model constraint reliability: deterministic vs robust")
    ax.legend()
    _oad.savefig(fig, f"{uc.lower()}_p3_feasibility.png")
    plt.close(fig)
    print(f"[{uc}] P3 robust optimization figures saved.")


# %%
# ## Use Case 1 — Kerosene / Turbofan
# Skeleton for the UC1 contributor: the ``run`` helper above is use-case agnostic,
# so completing UC1 is as simple as calling ``run("UC1")`` here (or implementing a
# dedicated version).
pass

# %%
# ## Use Case 2 — Liquid H₂ / Turbofan
run("UC2")
