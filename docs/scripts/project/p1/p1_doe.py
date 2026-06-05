"""Problem 1 — Design of Experiments (full draft pipeline, to be split).

NOTE for the Problem-1 contributor: this file currently holds the **complete
Problem-1 draft** for Use Case 1 (kerosene). It builds the coupled disciplines and
the 4-parameter design space, runs the deterministic MDF optimization on the true
model, fits and validates an RBF surrogate of ``f̂(x)``, re-optimizes on the
surrogate, verifies the optimum and sketches the aircraft.

It is kept here as a single block on purpose: the surrogate-building/validation
part is meant to move into ``p1_surrogate.py`` and the optimization part into
``p1_optimization.py`` (three parts, like Problem 3), and both use cases (UC1 and
UC2) still need to be wired in. Until then this draft lives in the DoE slot.
"""


from gemseo import generate_coupling_graph
from gemseo.disciplines.auto_py import AutoPyDiscipline
from gemseo_oad_training.models import aerodynamic
from gemseo_oad_training.models import approach
# from gemseo_oad_training.models import battery
from gemseo_oad_training.models import climb
from gemseo_oad_training.models import engine
from gemseo_oad_training.models import fuel_tank
from gemseo_oad_training.models import geometry
from gemseo_oad_training.models import mass
from gemseo_oad_training.models import mission
from gemseo_oad_training.models import operating_cost
from gemseo_oad_training.models import take_off
from gemseo_oad_training.models import total_mass

from gemseo.algos.design_space import DesignSpace
from numpy import array


from gemseo.scenarios.mdo_scenario import MDOScenario

from gemseo_oad_training.unit import convert_from


from gemseo import sample_disciplines
from gemseo.disciplines.surrogate import SurrogateDiscipline

from gemseo_oad_training.utils import AircraftConfiguration
from gemseo_oad_training.utils import draw_aircraft

disciplines = [AutoPyDiscipline(aerodynamic),
    AutoPyDiscipline(approach),
    AutoPyDiscipline(climb),
    AutoPyDiscipline(engine),
    AutoPyDiscipline(fuel_tank),
    AutoPyDiscipline(geometry),
    AutoPyDiscipline(mass),
    AutoPyDiscipline(mission),
    AutoPyDiscipline(operating_cost),
    AutoPyDiscipline(take_off),
    AutoPyDiscipline(total_mass)]
generate_coupling_graph(disciplines, file_path='couplage.png',full=False)

design_space = DesignSpace()

design_space.add_variable("slst", size=1, lower_bound=convert_from('kN',100), upper_bound=convert_from('kN',200) ,value=convert_from('kN',150))

design_space.add_variable("n_pax", size=1, lower_bound=120, upper_bound=180 ,value=150)

design_space.add_variable("area", size=1, lower_bound=convert_from('m2',100), upper_bound=convert_from('m2',200) ,value=convert_from('m2',180))

design_space.add_variable("ar", size=1, lower_bound=5, upper_bound=20 ,value=9)


scenario = MDOScenario(disciplines, "mtom", design_space, formulation_name="MDF")
scenario.add_constraint("tofl", constraint_type="ineq", positive=False, value=convert_from('m',1900))
scenario.add_constraint("vapp", constraint_type="ineq", positive=False, value=convert_from('kt',135))
scenario.add_constraint("vz", constraint_type="ineq", positive=True, value=convert_from('ft/min',300))
scenario.add_constraint("span", constraint_type="ineq", positive=False, value=convert_from('m',40))
scenario.add_constraint("length", constraint_type="ineq", positive=False, value=convert_from('m',45))
scenario.add_constraint("fm", constraint_type="ineq", positive=True, value=0)


print(design_space)
#scenario.execute(algo_name="SLSQP", max_iter=100)
scenario.execute(algo_name="NLOPT_COBYLA", max_iter=100)

scenario.optimization_result

scenario.optimization_result.constraint_values
# %%
scenario.optimization_result.x_opt_as_dict
# %%
scenario.optimization_result.x_0_as_dict
# %%
# Plot the optimization history:
scenario.post_process(post_name="OptHistoryView", save=False, show=True)



#Surrogate

# ### 2. Generate training and test datasets
training_dataset = sample_disciplines(
    disciplines, design_space, ["mtom","tofl","vapp","vz","span","length","fm"], algo_name="OT_OPT_LHS", n_samples=30
)
test_dataset = sample_disciplines(
    disciplines, design_space, ["mtom","tofl","vapp","vz","span","length","fm"], algo_name="OT_FULLFACT", n_samples=30**2
)

# %%
print("Surrogate Discipline :")
# ### 3. Build the surrogate discipline
surrogate_discipline = SurrogateDiscipline("RBFRegressor", training_dataset)

print(surrogate_discipline.execute({"slst":array([convert_from("kN",150)]),"n_pax":array([150]),"area":array([convert_from("m2",180)]),"ar":array([9])}))
# ### 5. Evaluate accuracy

#
# R² measure — on training data, by cross-validation, and on test data:
r2 = surrogate_discipline.get_error_measure("R2Measure")
print(f"R2 : {r2.compute_learning_measure(as_dict=True)}")
# %%
print(f" Cross Validation Measure : {r2.compute_cross_validation_measure(as_dict=True)}")
# %%
print(f" Test Measure : {r2.compute_test_measure(test_dataset, as_dict=True)}")

# %%
# RMSE measure:
rmse = surrogate_discipline.get_error_measure("RMSEMeasure")
print(f"RMSE : {rmse.compute_learning_measure(as_dict=True)}")
# %%
print(f"Cross Validation Measure : {rmse.compute_cross_validation_measure(as_dict=True)}")
# %%
print(f"Test Measure : {rmse.compute_test_measure(test_dataset, as_dict=True)}")

# Optimisation avec le surrogate

scenario_surrogate = MDOScenario([surrogate_discipline], "mtom", design_space, formulation_name="DisciplinaryOpt")
scenario_surrogate.add_constraint("tofl", constraint_type="ineq", positive=False, value=convert_from('m',1900))
scenario_surrogate.add_constraint("vapp", constraint_type="ineq", positive=False, value=convert_from('kt',135))
scenario_surrogate.add_constraint("vz", constraint_type="ineq", positive=True, value=convert_from('ft/min',300))
scenario_surrogate.add_constraint("span", constraint_type="ineq", positive=False, value=convert_from('m',40))
scenario_surrogate.add_constraint("length", constraint_type="ineq", positive=False, value=convert_from('m',45))
scenario_surrogate.add_constraint("fm", constraint_type="ineq", positive=True, value=0)
print(scenario_surrogate)

# %%
# ### 5. Execute with a gradient-free optimizer
scenario_surrogate.execute(algo_name="NLOPT_COBYLA", max_iter=100)

# %%
# ### 6. Inspect the results
print(f"Optimisation result {scenario_surrogate.optimization_result}")
# %%
print(f"Constraint values {scenario_surrogate.optimization_result.constraint_values}")
# %%
print(f"X opt : {scenario_surrogate.optimization_result.x_opt_as_dict}")
# %%
print(f"X0 : {scenario_surrogate.optimization_result.x_0_as_dict}")
# %%
# Plot the optimization history:
scenario_surrogate.post_process(post_name="OptHistoryView", save=False, show=True)


scenario_test = MDOScenario(disciplines, "mtom", design_space, formulation_name="MDF")
scenario_test.add_constraint("tofl", constraint_type="ineq", positive=False, value=convert_from('m',1900))
scenario_test.add_constraint("vapp", constraint_type="ineq", positive=False, value=convert_from('kt',135))
scenario_test.add_constraint("vz", constraint_type="ineq", positive=True, value=convert_from('ft/min',300))
scenario_test.add_constraint("span", constraint_type="ineq", positive=False, value=convert_from('m',40))
scenario_test.add_constraint("length", constraint_type="ineq", positive=False, value=convert_from('m',45))
scenario_test.add_constraint("fm", constraint_type="ineq", positive=True, value=0)


scenario_test.execute(algo_name="CustomDOE", samples=[scenario_surrogate.optimization_result.x_opt_as_dict])
print(f'Execute : ')
print(f"Optimisation result {scenario_test.optimization_result}")

draw_aircraft()
# %%
# ### 2. Draw variants with a custom wing area
configuration_1 = AircraftConfiguration(area=200, name="Conf 1", color="b")
draw_aircraft(configuration_1, title="Area = 200")

# %%
configuration_2 = AircraftConfiguration(area=80, name="Conf 2", color="r")
draw_aircraft(configuration_2, title="Area = 80")

# %%
draw_aircraft(configuration_1, configuration_2, title="Comparison")
