"""Définition partagée du problème OAD, importée par tous les scripts du projet.

Source de vérité unique du problème de conception avion globale (Overall Aircraft
Design). Le vrai modèle ``f(x, u)`` couple les fonctions analytiques de
``gemseo_oad_training.models`` via des :class:`.AutoPyDiscipline`. La boucle de
rétroaction sur la masse au décollage (``mass`` <-> ``total_mass`` <-> ``mission``)
impose une analyse multidisciplinaire (MDA), construite par la formulation ``MDF``.

* ``x`` (conception) : ``slst``, ``n_pax``, ``area``, ``ar``.
* ``u`` (incertain) : ``aef``, ``cef``, ``sef`` ; plus ``gi``, ``vi`` pour
  l'hydrogène liquide.
* Objectif : minimiser ``mtom``. Contraintes : ``tofl``, ``vapp``, ``vz``,
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

# Répertoire où chaque script enregistre ses figures (les scripts s'exécutent
# depuis ce dossier). Toutes les figures du projet sont regroupées sous
# docs/images/use_case/.
FIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "images", "use_case")


def savefig(fig, filename: str) -> None:
    """Enregistre une figure matplotlib dans le répertoire d'images regroupé."""
    os.makedirs(FIG_DIR, exist_ok=True)
    fig.savefig(os.path.join(FIG_DIR, filename), bbox_inches="tight", dpi=130)


def cached(file_path: str, compute):
    """Charge un artefact picklé s'il existe, sinon le calcule et le pickle.

    Partagée par les scripts lourds : une ré-exécution réutilise les artefacts
    déjà produits et les valeurs rapportées restent figées. Supprimer le pickle
    pour forcer un recalcul.

    Args:
        file_path: Emplacement du pickle.
        compute: Fonction sans argument, appelée seulement si le pickle est absent.

    Returns:
        L'artefact chargé ou calculé.
    """
    from gemseo import from_pickle, to_pickle

    if os.path.exists(file_path):
        return from_pickle(file_path)
    artifact = compute()
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    to_pickle(artifact, file_path)
    return artifact

# --------------------------------------------------------------------------- #
# Cas d'usage (seuls UC1 et UC2 sont requis par le projet, cf. docs/index.md)
# --------------------------------------------------------------------------- #
USE_CASES = {
    "UC1": {"fuel_type": "kerosene", "engine_type": "turbofan", "design_range_km": 5500},
    "UC2": {"fuel_type": "liquid_h2", "engine_type": "turbofan", "design_range_km": 5500},
}

# Les 11 disciplines impliquées dans le processus multidisciplinaire.
# ``battery`` reste silencieuse (renvoie des zéros) pour kerosene/liquid_h2 mais
# est conservée afin que la chaîne soit identique pour chaque cas d'usage.
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

# Sorties d'intérêt f(x, u) : objectif + contraintes.
OBJECTIVE = "mtom"
OUTPUT_NAMES = ["mtom", "tofl", "vapp", "vz", "span", "length", "fm"]

# Sorties qui dépendent réellement des paramètres incertains u.
# ``span`` et ``length`` sont purement géométriques (déterministes une fois x
# fixé), donc leur variance sous u est nulle et elles doivent être exclues de
# l'analyse de sensibilité basée sur la variance.
SENSITIVITY_OUTPUTS = ["mtom", "tofl", "vapp", "vz", "fm"]

# Contraintes sous la forme (nom_sortie, positif, borne) en unités STANDARD (SI).
# ``positive=False`` signifie ``sortie <= borne`` ; ``positive=True`` signifie ``sortie >= borne``.
CONSTRAINTS = [
    ("tofl", False, 1900.0),                       # longueur de piste au décollage <= 1900 m
    ("vapp", False, convert_from("kt", 135.0)),    # vitesse d'approche <= 135 kt
    ("vz", True, convert_from("ft/min", 300.0)),   # vitesse verticale >= 300 ft/min
    ("span", False, 40.0),                         # envergure <= 40 m
    ("length", False, 45.0),                       # longueur de l'avion <= 45 m
    ("fm", True, 0.0),                             # marge de carburant >= 0
]

# Valeurs nominales (les plus probables) des paramètres incertains, pour figer u.
NOMINAL_UNCERTAIN = {"aef": 1.0, "cef": 1.0, "sef": 1.0, "gi": 0.4, "vi": 0.8}

# Point de conception initial / nominal (valeurs par défaut, cf. use_cases.md), en unités SI.
INITIAL_DESIGN = {
    "slst": convert_from("kN", 150.0),  # 150 kN
    "n_pax": 150.0,
    "area": 180.0,
    "ar": 9.0,
}


def make_disciplines(uc: str):
    """Construit la liste des disciplines couplées pour un cas d'usage donné.

    Args:
        uc: L'identifiant du cas d'usage (``"UC1"`` ou ``"UC2"``).

    Returns:
        La liste des objets :class:`.AutoPyDiscipline` dont les entrées
        catégorielles et fixes sont réglées aux valeurs du cas d'usage.
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
    """Fige les paramètres de conception des disciplines en un point donné.

    Utilisé par le problème 2, où la conception ``x`` est figée et où seul ``u``
    varie.

    Args:
        disciplines: Les disciplines renvoyées par :func:`make_disciplines`.
        design_point: Dictionnaire ``nom -> valeur`` en unités SI (scalaires ou
            tableaux).
    """
    import numpy as np

    # Les grammaires des disciplines valident strictement les valeurs *par défaut*
    # comme des nombres scalaires (les valeurs d'exécution peuvent être des
    # tableaux et sont converties), on fige donc les paramètres de conception en
    # simples flottants.
    scalar_point = {k: float(np.asarray(v).ravel()[0]) for k, v in design_point.items()}
    update_default_inputs(disciplines, scalar_point)


def get_design_space() -> DesignSpace:
    """Renvoie l'espace de conception des 4 paramètres de conception (unités SI)."""
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
    """Renvoie l'espace incertain des variables aléatoires pertinentes pour un cas d'usage.

    ``aef``/``cef``/``sef`` sont toujours pertinentes ; ``gi``/``vi`` seulement
    pour liquid_h2.
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
    """Renvoie l'espace conjoint conception+incertitudes utilisé au problème 3.

    Les variables de conception sont ajoutées comme variables aléatoires
    uniformes sur leurs bornes afin qu'un unique plan d'expériences explore
    ``f(x, u)`` ; l'optimisation traite ensuite la partie conception comme
    déterministe.
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
    """Ajoute les 6 contraintes opérationnelles à un scénario MDO/UMDO."""
    for name, positive, bound in CONSTRAINTS:
        scenario.add_constraint(name, constraint_type="ineq", positive=positive, value=bound)


# --------------------------------------------------------------------------- #
# Sélection & validation du surrogate (linéaire vs RBF, garder le plus simple adéquat)
# --------------------------------------------------------------------------- #
def train_and_select(train_dataset, test_dataset, output_names,
                     regressors=("LinearRegressor", "RBFRegressor", "GaussianProcessRegressor"),
                     prefer=None):
    """Entraîne plusieurs régresseurs, les valide et garde le meilleur sur le jeu de test.

    Par défaut, on garde le régresseur de R2 de test moyen le plus élevé (règle
    « commencer simple »). Le tableau complet est renvoyé pour le rapport.

    Args:
        prefer: Si fourni, force ce régresseur (les autres restent entraînés pour
            le tableau de comparaison). Utilisé par le problème 3 pour imposer le
            krigeage.

    Returns:
        ``(selected_name, selected_surrogate, results)`` où ``results`` associe
        chaque nom de régresseur à ``{"R2": {out: value}, "RMSE": {out: value}}``.
    """
    from gemseo.disciplines.surrogate import SurrogateDiscipline

    results = {}
    surrogates = {}
    import numpy as np

    for name in regressors:
        surrogate = SurrogateDiscipline(name, train_dataset)
        # Élargit le domaine de validité du surrogate autour de chaque entrée :
        # avec de petits plans, le Monte-Carlo et l'optimisation en aval sondent
        # juste au-delà de la boîte d'entraînement (tout en restant physiques) et
        # saturent les journaux d'avertissements. Les bornes élargies sont picklées
        # avec le surrogate.
        VALIDITY_DOMAIN_MARGIN = 2.0  # 1.0 = boîte d'origine, 2.0 = doublée autour du centre
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
    """Diagramme en barres comparant le R2 de test de chaque régresseur par sortie, et l'enregistre.

    Args:
        cv: Dictionnaire optionnel ``sortie -> R2 de validation croisée``, superposé
            au graphe sous forme d'une série de barres supplémentaire.
        cv_label: Libellé de légende de cette série (par défaut « cross-val. »).
    """
    import numpy as np
    from matplotlib import pyplot as plt

    # La série optionnelle de validation croisée compte comme un groupe de barres supplémentaire.
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
    ax.set_ylabel("$R^2$ de test (1 = parfait)")
    ax.set_ylim(min(0.0, ax.get_ylim()[0]), 1.05)
    ax.set_title(title)
    ax.legend()
    savefig(fig, filename)
    return fig
