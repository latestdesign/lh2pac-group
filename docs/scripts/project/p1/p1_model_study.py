"""Problème 1 — Étude croisée métamodèle x taille du plan d'expériences.

Étude de faisabilité justifiant le choix du couple (métamodèle, nombre
d'échantillons) du problème 1. Pour chaque combinaison de régresseur
(``LinearRegressor``, ``RBFRegressor``, ``RandomForestRegressor``) et de taille de
plan ``N`` (30, 100, 1000), on entraîne un surrogate déterministe sur le vrai
modèle, on optimise le MTOM dessus, puis on **vérifie l'optimum sur le vrai
modèle** : on rapporte le MTOM surrogate, le MTOM réel, et si la solution est
réellement faisable. Le tableau final montre que la plupart des couples donnent un
optimum infaisable au sens du vrai modèle.

Ce script utilise la formulation complète à 11 disciplines (avec
``operating_cost``) ; il ne passe donc pas par le helper ``_oad``.

Script lourd (échantillonnage du vrai modèle jusqu'à N=1000, plusieurs modèles).
Les deux cas d'usage sont produits ci-dessous.
"""

from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
if "__file__" not in globals():
    __file__ = os.path.join(os.getcwd(), "p1_model_study.py")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

import numpy as np
from gemseo.disciplines.auto_py import AutoPyDiscipline
from gemseo_oad_training.models import (
    aerodynamic, approach, climb, engine, fuel_tank, geometry,
    mass, mission, operating_cost, take_off, total_mass,
)
from gemseo.algos.design_space import DesignSpace
from gemseo_oad_training.unit import convert_from, convert_to
from gemseo import sample_disciplines
from gemseo.disciplines.surrogate import SurrogateDiscipline
from gemseo.scenarios.mdo_scenario import MDOScenario
from gemseo.utils.discipline import update_default_input_values

# Suppress warnings to keep logs clean
logging.getLogger("gemseo").setLevel(logging.ERROR)

surrogates = ["LinearRegressor", "RBFRegressor", "RandomForestRegressor"]
n_samples_list = [30, 100, 1000]


def get_fresh_design_space():
    ds = DesignSpace()
    ds.add_variable("slst", size=1, lower_bound=convert_from('kN',100), upper_bound=convert_from('kN',200) ,value=convert_from('kN',150))
    ds.add_variable("n_pax", size=1, lower_bound=120, upper_bound=180 ,value=150)
    ds.add_variable("area", size=1, lower_bound=convert_from('m2',100), upper_bound=convert_from('m2',200) ,value=convert_from('m2',180))
    ds.add_variable("ar", size=1, lower_bound=5, upper_bound=20 ,value=9)
    return ds


def run(uc):
    """Balayage (métamodèle x N) avec vérification de faisabilité sur le vrai modèle."""
    # Disciplines : formulation complète à 11 disciplines (avec operating_cost).
    disciplines = [
        AutoPyDiscipline(aerodynamic),
        AutoPyDiscipline(approach),
        AutoPyDiscipline(climb),
        AutoPyDiscipline(engine),
        AutoPyDiscipline(fuel_tank),
        AutoPyDiscipline(geometry),
        AutoPyDiscipline(mass),
        AutoPyDiscipline(mission),
        AutoPyDiscipline(operating_cost),
        AutoPyDiscipline(take_off),
        AutoPyDiscipline(total_mass)
    ]
    if uc == "UC2":
        update_default_input_values(disciplines, {"fuel_type": "liquid_h2"})

    print(f"Starting feasibility evaluation for all surrogate configurations... ({uc})")

    results = []

    for model_name in surrogates:
        for n in n_samples_list:
            print(f"\n--- Model: {model_name} | N = {n} ---")

            # 1. Generate training data
            ds_train = get_fresh_design_space()
            training_dataset = sample_disciplines(
                disciplines, ds_train, ["mtom","tofl","vapp","vz","span","length","fm"], algo_name="OT_OPT_LHS", n_samples=n
            )

            # 2. Build surrogate
            surrogate = SurrogateDiscipline(model_name, training_dataset)

            # 3. Optimize on surrogate
            ds_opt = get_fresh_design_space()
            scenario_surr = MDOScenario([surrogate], "mtom", ds_opt, formulation_name="DisciplinaryOpt")
            scenario_surr.add_constraint("tofl", constraint_type="ineq", positive=False, value=convert_from('m',1900))
            scenario_surr.add_constraint("vapp", constraint_type="ineq", positive=False, value=convert_from('kt',135))
            scenario_surr.add_constraint("vz", constraint_type="ineq", positive=True, value=convert_from('ft/min',300))
            scenario_surr.add_constraint("span", constraint_type="ineq", positive=False, value=convert_from('m',40))
            scenario_surr.add_constraint("length", constraint_type="ineq", positive=False, value=convert_from('m',45))
            scenario_surr.add_constraint("fm", constraint_type="ineq", positive=True, value=0)

            try:
                scenario_surr.execute(algo_name="NLOPT_COBYLA", max_iter=100)
                x_opt = scenario_surr.optimization_result.x_opt_as_dict

                f_opt_val = scenario_surr.optimization_result.f_opt
                surr_mtom = float(np.atleast_1d(f_opt_val)[0])

                # Print intermediate optimization result
                print(f"Surrogate f_opt (mtom): {surr_mtom:.2f} kg")

                slst_val = float(np.atleast_1d(x_opt['slst'])[0])
                n_pax_val = float(np.atleast_1d(x_opt['n_pax'])[0])
                area_val = float(np.atleast_1d(x_opt['area'])[0])
                ar_val = float(np.atleast_1d(x_opt['ar'])[0])
                print(f"Surrogate x_opt: slst={convert_to('kN', slst_val):.1f} kN, n_pax={n_pax_val:.1f}, area={convert_to('m2', area_val):.1f} m2, ar={ar_val:.2f}")

                # 4. Evaluate optimal point on true disciplines
                ds_test = get_fresh_design_space()
                scenario_test = MDOScenario(disciplines, "mtom", ds_test, formulation_name="MDF")
                scenario_test.add_constraint("tofl", constraint_type="ineq", positive=False, value=convert_from('m',1900))
                scenario_test.add_constraint("vapp", constraint_type="ineq", positive=False, value=convert_from('kt',135))
                scenario_test.add_constraint("vz", constraint_type="ineq", positive=True, value=convert_from('ft/min',300))
                scenario_test.add_constraint("span", constraint_type="ineq", positive=False, value=convert_from('m',40))
                scenario_test.add_constraint("length", constraint_type="ineq", positive=False, value=convert_from('m',45))
                scenario_test.add_constraint("fm", constraint_type="ineq", positive=True, value=0)

                scenario_test.execute(algo_name="CustomDOE", samples=[x_opt])

                # 5. Retrieve true model feasibility
                true_result = scenario_test.optimization_result
                true_mtom = float(np.atleast_1d(true_result.f_opt)[0])

                # Find violated constraints manually
                violations = []
                is_feasible = True
                for constr_name, constr_val in true_result.constraint_values.items():
                    val = float(np.atleast_1d(constr_val)[0])
                    if val > 1e-6: # Violated if positive
                        violations.append(f"{constr_name} ({val:.3f})")
                        is_feasible = False

                violation_str = ", ".join(violations) if violations else "Aucune"

                results.append({
                    "model": model_name,
                    "n": n,
                    "surr_mtom": surr_mtom,
                    "true_mtom": true_mtom,
                    "feasible": "Oui" if is_feasible else "Non",
                    "violations": violation_str
                })

                print(f"True mtom: {true_mtom:.2f} kg | Feasible: {is_feasible} | Violations: {violation_str}")
            except Exception as e:
                print(f"Error during optimization/verification: {e}")
                import traceback
                traceback.print_exc()
                results.append({
                    "model": model_name,
                    "n": n,
                    "surr_mtom": np.nan,
                    "true_mtom": np.nan,
                    "feasible": "Erreur",
                    "violations": str(e)
                })

    # Print the final Markdown table
    print(f"\n=== FINAL RESULTS TABLE ({uc}) ===")
    print("| Métamodèle | Échantillons (N) | MTOM Surrogate (kg) | MTOM Réelle (kg) | Faisable (Réel) | Contraintes violées (valeur standardisée) |")
    print("|---|---|---|---|---|---|")
    for res in results:
        print(f"| {res['model']} | {res['n']} | {res['surr_mtom']:.1f} | {res['true_mtom']:.1f} | {res['feasible']} | {res['violations']} |")


# %%
# ## Cas d'usage 1 — Kérosène / Turbofan
run("UC1")

# %%
# ## Cas d'usage 2 — Hydrogène liquide / Turbofan
run("UC2")
