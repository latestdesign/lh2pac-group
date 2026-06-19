"""Shared OAD problem definition for the LH2PAC project.

This module is the single source of truth for the Overall Aircraft Design (OAD)
problem. It is imported by every ``uc*`` / ``plot_uc*`` script in this directory.

It does NOT carry the ``plot_`` prefix on purpose: the documentation gallery only
executes ``plot_*.py`` files, so this helper is shown/installed but never run as a
standalone example.

The "true" model ``f(x, u)`` is built by wrapping the analytic functions of
``gemseo_oad_training.models`` as :class:`.AutoPyDiscipline` objects and coupling
them. There is a feedback loop on the maximum take-off mass ``mtom``
(``mass`` <-> ``total_mass`` <-> ``mission``), so a multidisciplinary analysis
(MDA) is required: we always use the ``MDF`` formulation, which builds the MDA
automatically.

* ``x`` (design parameters): ``slst``, ``n_pax``, ``area``, ``ar``.
* ``u`` (uncertain parameters): ``aef``, ``cef``, ``sef`` (all use cases) plus
  ``gi``, ``vi`` for liquid-hydrogen aircraft.
* Objective: minimise ``mtom``. Constraints: ``tofl``, ``vapp``, ``vz``,
  ``span``, ``length``, ``fm``.
"""

from __future__ import annotations

import os

from gemseo.algos.design_space import DesignSpace
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.disciplines.auto_py import AutoPyDiscipline

from gemseo_oad_training import models
from gemseo_oad_training.unit import convert_from

from lh2pac.utils import update_default_inputs

# Directory where every script saves its figures (scripts run from this folder).
# All project figures are consolidated under docs/images/use_case/.
FIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "images", "use_case")


def savefig(fig, filename: str) -> None:
    """Save a matplotlib figure into the consolidated images directory."""
    os.makedirs(FIG_DIR, exist_ok=True)
    fig.savefig(os.path.join(FIG_DIR, filename), bbox_inches="tight", dpi=130)


def cached(file_path: str, compute):
    """Load a pickled artifact if it exists, else compute it and pickle it.

    Load-or-compute caching shared by the heavy scripts: re-running a script
    reuses the artifacts it has already produced, so a re-run (or a docs rebuild)
    is cheap and the reported numbers stay fixed. To force a fresh computation,
    simply delete the corresponding pickle and run again.

    Args:
        file_path: Where the artifact is (or will be) pickled.
        compute: Zero-argument callable that produces the artifact when it is
            missing. Only called on a cache miss.

    Returns:
        The loaded or freshly computed artifact.
    """
    from gemseo import from_pickle, to_pickle

    if os.path.exists(file_path):
        return from_pickle(file_path)
    artifact = compute()
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    to_pickle(artifact, file_path)
    return artifact

# --------------------------------------------------------------------------- #
# Use cases (only UC1 and UC2 are required by the project, see docs/index.md)
# --------------------------------------------------------------------------- #
USE_CASES = {
    "UC1": {"fuel_type": "kerosene", "engine_type": "turbofan", "design_range_km": 5500},
    "UC2": {"fuel_type": "liquid_h2", "engine_type": "turbofan", "design_range_km": 5500},
}

# The 11 disciplines involved in the multidisciplinary process.
# ``battery`` stays silent (returns zeros) for kerosene/liquid_h2 but is kept so
# that the chain is identical for every use case.
_MODEL_FUNCTIONS = (
    models.geometry,
    models.aerodynamic,
    models.engine,
    models.fuel_tank,
    models.battery,
    models.mass,
    models.total_mass,
    models.mission,
    models.take_off,
    models.approach,
    models.climb,
)

# Outputs of interest f(x, u): objective + constraints.
OBJECTIVE = "mtom"
OUTPUT_NAMES = ["mtom", "tofl", "vapp", "vz", "span", "length", "fm"]

# Outputs that actually depend on the uncertain parameters u.
# ``span`` and ``length`` are purely geometric (deterministic given x), so they
# have zero variance under u and must be excluded from variance-based sensitivity.
SENSITIVITY_OUTPUTS = ["mtom", "tofl", "vapp", "vz", "fm"]

# Constraints as (output_name, positive, bound) in STANDARD (SI) units.
# ``positive=False`` means ``output <= bound``; ``positive=True`` means ``output >= bound``.
CONSTRAINTS = [
    ("tofl", False, 1900.0),                       # take-off field length <= 1900 m
    ("vapp", False, convert_from("kt", 135.0)),    # approach speed <= 135 kt
    ("vz", True, convert_from("ft/min", 300.0)),   # vertical speed >= 300 ft/min
    ("span", False, 40.0),                         # wing span <= 40 m
    ("length", False, 45.0),                       # aircraft length <= 45 m
    ("fm", True, 0.0),                             # fuel margin >= 0
]

# Nominal (most likely) values of the uncertain parameters, used to freeze u.
NOMINAL_UNCERTAIN = {"aef": 1.0, "cef": 1.0, "sef": 1.0, "gi": 0.4, "vi": 0.8}

# Initial / nominal design point (default values, see use_cases.md), SI units.
INITIAL_DESIGN = {
    "slst": convert_from("kN", 150.0),  # 150 kN
    "n_pax": 150.0,
    "area": 180.0,
    "ar": 9.0,
}


def uc_from_filename(path: str) -> str:
    """Infer the use-case id (``"UC1"``/``"UC2"``) from a script file name.

    ``uc1_p1_doe.py`` -> ``"UC1"``; ``plot_uc2_p2_uq.py`` -> ``"UC2"``.
    This lets the UC1 and UC2 scripts share identical content.
    """
    return "UC" + os.path.basename(path).split("uc")[1][0]


def make_disciplines(uc: str):
    """Build the list of coupled disciplines for a given use case.

    Args:
        uc: The use case identifier (``"UC1"`` or ``"UC2"``).

    Returns:
        The list of :class:`.AutoPyDiscipline` objects with the categorical and
        fixed inputs set to the use-case values.
    """
    settings = USE_CASES[uc]
    disciplines = [AutoPyDiscipline(func) for func in _MODEL_FUNCTIONS]
    update_default_inputs(
        disciplines,
        {
            "fuel_type": settings["fuel_type"],
            "engine_type": settings["engine_type"],
            "design_range": convert_from("km", settings["design_range_km"]),
        },
    )
    return disciplines


def set_design_point(disciplines, design_point) -> None:
    """Freeze the design parameters of the disciplines at a given point.

    Used by Problem 2, where the design ``x`` is fixed and only ``u`` varies.

    Args:
        disciplines: The disciplines returned by :func:`make_disciplines`.
        design_point: Mapping ``name -> value`` in SI units (scalars or arrays).
    """
    import numpy as np

    # The discipline grammars validate *default* values strictly as scalar
    # numbers (execution values may be arrays and are coerced), so freeze the
    # design parameters as plain floats.
    scalar_point = {k: float(np.asarray(v).ravel()[0]) for k, v in design_point.items()}
    update_default_inputs(disciplines, scalar_point)


def get_design_space() -> DesignSpace:
    """Return the design space of the 4 design parameters (SI units)."""
    design_space = DesignSpace()
    design_space.add_variable(
        "slst", lower_bound=convert_from("kN", 100.0),
        upper_bound=convert_from("kN", 200.0), value=INITIAL_DESIGN["slst"],
    )
    design_space.add_variable("n_pax", lower_bound=120.0, upper_bound=180.0, value=150.0)
    design_space.add_variable("area", lower_bound=100.0, upper_bound=200.0, value=180.0)
    design_space.add_variable("ar", lower_bound=5.0, upper_bound=20.0, value=9.0)
    return design_space


def get_uncertain_space(uc: str) -> ParameterSpace:
    """Return the uncertain space of the relevant random variables for a use case.

    ``aef``/``cef``/``sef`` are always relevant; ``gi``/``vi`` only for liquid_h2.
    """
    settings = USE_CASES[uc]
    uncertain_space = ParameterSpace()
    for name in ("aef", "cef", "sef"):
        uncertain_space.add_random_variable(
            name, "OTTriangularDistribution", minimum=0.99, mode=1.0, maximum=1.03
        )
    if settings["fuel_type"] == "liquid_h2":
        uncertain_space.add_random_variable(
            "gi", "OTTriangularDistribution", minimum=0.35, mode=0.4, maximum=0.405
        )
        uncertain_space.add_random_variable(
            "vi", "OTTriangularDistribution", minimum=0.755, mode=0.8, maximum=0.805
        )
    return uncertain_space


def get_joint_space(uc: str) -> ParameterSpace:
    """Return the joint design+uncertain space used in Problem 3.

    Design variables are added as uniform random variables on their bounds so
    that a single DoE explores ``f(x, u)``; the optimization later treats the
    design part as deterministic.
    """
    space = ParameterSpace()
    space.add_random_variable("slst", "OTUniformDistribution",
                              minimum=convert_from("kN", 100.0),
                              maximum=convert_from("kN", 200.0))
    space.add_random_variable("n_pax", "OTUniformDistribution", minimum=120.0, maximum=180.0)
    space.add_random_variable("area", "OTUniformDistribution", minimum=100.0, maximum=200.0)
    space.add_random_variable("ar", "OTUniformDistribution", minimum=5.0, maximum=20.0)
    for name in ("aef", "cef", "sef"):
        space.add_random_variable(name, "OTTriangularDistribution",
                                  minimum=0.99, mode=1.0, maximum=1.03)
    if USE_CASES[uc]["fuel_type"] == "liquid_h2":
        space.add_random_variable("gi", "OTTriangularDistribution",
                                  minimum=0.35, mode=0.4, maximum=0.405)
        space.add_random_variable("vi", "OTTriangularDistribution",
                                  minimum=0.755, mode=0.8, maximum=0.805)
    return space


def add_constraints(scenario) -> None:
    """Add the 6 operational constraints to an MDO/UMDO scenario."""
    for name, positive, bound in CONSTRAINTS:
        scenario.add_constraint(name, constraint_type="ineq", positive=positive, value=bound)


# --------------------------------------------------------------------------- #
# Surrogate selection & validation (Linear vs RBF, keep the simplest adequate)
# --------------------------------------------------------------------------- #
def train_and_select(train_dataset, test_dataset, output_names,
                     regressors=("LinearRegressor", "RBFRegressor", "GaussianProcessRegressor"),
                     prefer=None):
    """Train several regressors, validate them and keep the best on the test set.

    By default the selection follows the project rule "start simple": among the
    candidate regressors we keep the one with the highest mean test R2 over the
    outputs. The full table is returned so the report can justify the choice.

    Args:
        prefer: If given and among ``regressors``, force that regressor as the
            selected surrogate (the others are still trained for the comparison
            table). Used by Problem 3, which deliberately picks the Kriging
            (Gaussian-Process) model: it is better calibrated than the RBF in the
            data-sparse *corners* of the joint space where the optimum sits, which
            reduces the systematic over-prediction of MTOM at the optimum.

    Returns:
        ``(selected_name, selected_surrogate, results)`` where ``results`` maps
        each regressor name to ``{"R2": {out: value}, "RMSE": {out: value}}``.
    """
    from gemseo.disciplines.surrogate import SurrogateDiscipline

    results = {}
    surrogates = {}
    import numpy as np

    for name in regressors:
        surrogate = SurrogateDiscipline(name, train_dataset)
        # GEMSEO records a "validity domain": the hypercube spanned by the
        # min/max of each input in the *training* DoE, and logs a warning every
        # time the surrogate is later evaluated outside it. With our small DoEs
        # and triangular uncertain inputs (whose samples cluster near the mode),
        # downstream Monte-Carlo/optimization routinely probes just past that
        # empirical box -- still well within the physical ranges, only outside
        # the few training points -- which floods the logs with harmless
        # warnings. We therefore *enlarge* the box by VALIDITY_DOMAIN_MARGIN
        # about each input's centre, instead of disabling the check: a moderate
        # factor absorbs that expected near-boundary extrapolation while a point
        # that lands genuinely far outside still trips the warning, so the safety
        # net is kept. (Note: emptying the domain does NOT work -- the membership
        # check then raises internally and re-emits the very same warning.) The
        # widened bounds are pickled with the surrogate, so the P2/P3 runs that
        # load it inherit the same behaviour.
        VALIDITY_DOMAIN_MARGIN = 2.0  # 1.0 = original box, 2.0 = doubled about centre
        validity_domain = surrogate.regression_model.validity_domain
        for variable_name in tuple(validity_domain):
            lower = validity_domain.get_lower_bound(variable_name)
            upper = validity_domain.get_upper_bound(variable_name)
            centre = (lower + upper) / 2.0
            half_width = (upper - lower) / 2.0
            validity_domain.set_lower_bound(
                variable_name, centre - VALIDITY_DOMAIN_MARGIN * half_width)
            validity_domain.set_upper_bound(
                variable_name, centre + VALIDITY_DOMAIN_MARGIN * half_width)
        r2 = surrogate.get_error_measure("R2Measure").compute_test_measure(
            test_dataset, as_dict=True)
        rmse = surrogate.get_error_measure("RMSEMeasure").compute_test_measure(
            test_dataset, as_dict=True)
        results[name] = {
            "R2": {o: float(r2[o][0]) for o in output_names},
            "RMSE": {o: float(rmse[o][0]) for o in output_names},
        }
        surrogates[name] = surrogate

    def mean_r2(name):
        return sum(results[name]["R2"].values()) / len(output_names)

    best_name = max(regressors, key=mean_r2)
    selected = prefer if prefer in surrogates else best_name
    return selected, surrogates[selected], results


def plot_validation_bars(results, output_names, filename, title, cv=None, cv_label=None):
    """Bar chart comparing test R2 of each regressor for each output, and save it.

    Args:
        cv: Optional mapping ``output -> cross-validation R2`` for the selected
            surrogate. When given, an extra bar series is overlaid so the figure
            shows that the cross-validation R2 tracks the single-split test R2
            (evidence of no over-fitting on the small DoE).
        cv_label: Legend label for that extra series (defaults to "cross-val.").
    """
    import numpy as np
    from matplotlib import pyplot as plt

    # The optional cross-validation series counts as one extra group of bars.
    series = list(results) + (["__cv__"] if cv is not None else [])
    x = np.arange(len(output_names))
    width = 0.8 / len(series)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for i, name in enumerate(series):
        if name == "__cv__":
            values = [cv[o] for o in output_names]
            ax.bar(x + i * width, values, width, label=cv_label or "cross-val.",
                   color="tab:gray", hatch="//")
        else:
            values = [results[name]["R2"][o] for o in output_names]
            ax.bar(x + i * width, values, width, label=name)
    ax.set_xticks(x + width * (len(series) - 1) / 2)
    ax.set_xticklabels(output_names)
    ax.axhline(1.0, color="grey", lw=0.8, ls="--")
    ax.set_ylabel("Test $R^2$ (1 = perfect)")
    ax.set_ylim(min(0.0, ax.get_ylim()[0]), 1.05)
    ax.set_title(title)
    ax.legend()
    savefig(fig, filename)
    return fig
