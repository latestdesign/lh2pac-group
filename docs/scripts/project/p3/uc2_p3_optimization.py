"""Problem 3 - Robust optimization on the joint surrogate f(x, u).

HEAVY script (no ``plot_`` prefix): although it only evaluates the cheap
surrogate, the robust optimization wraps an inner Monte-Carlo statistic estimation
inside every optimizer iteration (``gemseo-umdo``), which takes a few minutes -
too long for the documentation gallery. It is therefore run manually and its
figures are committed for the report.

The objective is the *expected* maximum take-off mass; each constraint is enforced
with a safety margin ``mean +/- k*std`` so that it remains satisfied under the
technological uncertainties. The robust optimum is compared to the deterministic
optimum from Problem 1.

Run ``uc*_p3_doe.py`` then ``uc*_p3_surrogate.py`` (and the Problem 1 scripts).
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
# mkdocs-gallery execs this file without defining ``__file__`` (cwd is the
# script directory during execution); define it so the helpers below work.
if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "uc2_p3_optimization.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from matplotlib import pyplot as plt

from gemseo import configure_logger, from_pickle, sample_disciplines, to_pickle
from gemseo.algos.doe.openturns.settings.ot_monte_carlo import OT_MONTE_CARLO_Settings
from gemseo_oad_training.utils import AircraftConfiguration, draw_aircraft
from lh2pac.utils import update_default_inputs
from gemseo_umdo.formulations.sampling_settings import Sampling_Settings
from gemseo_umdo.scenarios.umdo_scenario import UMDOScenario

import _oad

configure_logger(level="WARNING")

UC = _oad.uc_from_filename(__file__)
HERE = os.path.dirname(os.path.abspath(__file__))

MARGIN_FACTOR = 2.0  # k in "mean +/- k*std": ~97.7% one-sided for a normal output.
N_MC = 150           # inner Monte-Carlo size for statistic estimation.
MAX_ITER = 60        # optimizer iterations (each runs a full inner sampling).

surrogate = from_pickle(os.path.join(HERE, "data", f"{UC.lower()}_p3_surrogate.pkl"))

# Robust scenario: minimise E[mtom] under margin constraints, using the surrogate.
settings = Sampling_Settings(doe_algo_settings=OT_MONTE_CARLO_Settings(n_samples=N_MC))
scenario = UMDOScenario(
    [surrogate], _oad.OBJECTIVE, _oad.get_design_space(), _oad.get_uncertain_space(UC),
    "Mean", statistic_estimation_settings=settings, formulation_name="DisciplinaryOpt",
)
for name, positive, bound in _oad.CONSTRAINTS:
    # "<= bound" -> mean + k*std <= bound ; ">= bound" -> mean - k*std >= bound.
    factor = -MARGIN_FACTOR if positive else MARGIN_FACTOR
    scenario.add_constraint(name, "Margin", value=bound, positive=positive, factor=factor)

scenario.execute(algo_name="NLOPT_COBYLA", max_iter=MAX_ITER)
result = scenario.optimization_result
to_pickle(result, os.path.join(HERE, "data", f"{UC.lower()}_p3_optimization.pkl"))

x_robust = {k: float(v[0]) for k, v in result.x_opt_as_dict.items()}
print(f"\n[{UC}] Problem 3 robust optimum (E[MTOM] = {float(result.f_opt):.0f} kg):")
for name in ("slst", "n_pax", "area", "ar"):
    print(f"  {name:6s} = {x_robust[name]:.2f}")

# Deterministic optimum from Problem 1 (for comparison).
det_result = from_pickle(os.path.join(HERE, "..", "p1", "data", f"{UC.lower()}_p1_optimization.pkl"))
x_det = {k: float(v[0]) for k, v in det_result.x_opt_as_dict.items()}

# ---- Convergence history (expected MTOM + max margin violation) ----------- #
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
ax1.set_title(f"{UC} - Problem 3 robust optimization convergence")
ax2.plot(np.arange(1, len(violations) + 1), violations, "-o", ms=3, color="tab:red")
ax2.axhline(0.0, color="grey", lw=0.8, ls="--")
ax2.set_ylabel("max margin violation")
ax2.set_xlabel("iteration")
fig.tight_layout()
_oad.savefig(fig, f"{UC.lower()}_p3_robust_history.png")
plt.close(fig)

# ---- Robust vs deterministic aircraft ------------------------------------- #
nominal_u = {k: np.array([v]) for k, v in _oad.NOMINAL_UNCERTAIN.items()
             if k in _oad.get_uncertain_space(UC).variable_names}


def evaluate(design):
    inputs = {k: np.array([design[k]]) for k in ("slst", "n_pax", "area", "ar")}
    inputs.update(nominal_u)
    return surrogate.execute(inputs)


det_out, rob_out = evaluate(x_det), evaluate(x_robust)
det_config = AircraftConfiguration(
    name="Deterministic (P1)", area=x_det["area"], n_pax=int(round(x_det["n_pax"])),
    slst=x_det["slst"], span=float(det_out["span"][0]),
    length=float(det_out["length"][0]), color="tab:blue",
)
rob_config = AircraftConfiguration(
    name="Robust (P3)", area=x_robust["area"], n_pax=int(round(x_robust["n_pax"])),
    slst=x_robust["slst"], span=float(rob_out["span"][0]),
    length=float(rob_out["length"][0]), color="tab:green",
)
draw_aircraft(
    det_config, rob_config, title=f"{UC} - deterministic vs robust optimum",
    file_path=os.path.join(_oad.FIG_DIR, f"{UC.lower()}_p3_robust_vs_det.png"),
    save=True, show=False,
)
# ---- Robustness check: feasibility at the deterministic vs robust design --- #
# Propagate the uncertainties through the surrogate at each fixed design and
# compare the expected MTOM (fair "price of robustness") and the probability of
# satisfying each constraint. This is what justifies the robust design.
uncertain_space = _oad.get_uncertain_space(UC)
constrained = [(n, p, b) for n, p, b in _oad.CONSTRAINTS if n in _oad.SENSITIVITY_OUTPUTS]


def propagate(design):
    """Monte-Carlo propagation of u through the surrogate at a fixed design x."""
    update_default_inputs(
        [surrogate], {k: np.array([design[k]]) for k in ("slst", "n_pax", "area", "ar")}
    )
    dataset = sample_disciplines(
        [surrogate], uncertain_space, _oad.SENSITIVITY_OUTPUTS,
        algo_name="OT_MONTE_CARLO", n_samples=20000,
    )
    mean_mtom = float(dataset.get_view(variable_names="mtom").to_numpy().mean())
    proba = {}
    for name, positive, bound in constrained:
        values = dataset.get_view(variable_names=name).to_numpy().ravel()
        proba[name] = float(np.mean(values >= bound) if positive else np.mean(values <= bound))
    return mean_mtom, proba


det_mtom, det_p = propagate(x_det)
rob_mtom, rob_p = propagate(x_robust)
print(f"  E[MTOM] deterministic design = {det_mtom:.0f} kg")
print(f"  E[MTOM] robust design        = {rob_mtom:.0f} kg")
print(f"  price of robustness          = {rob_mtom - det_mtom:+.0f} kg")
print("  P(constraint satisfied)  deterministic / robust:")
for name, _, _ in constrained:
    print(f"    {name:5s} {det_p[name]:6.1%} / {rob_p[name]:6.1%}")

# Constraint-reliability bar chart: deterministic vs robust design.
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
ax.set_title(f"{UC} - constraint reliability: deterministic vs robust design")
ax.legend()
_oad.savefig(fig, f"{UC.lower()}_p3_feasibility.png")
plt.close(fig)
print(f"[{UC}] P3 robust optimization figures saved.")
