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

#imports for uncertain space
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.disciplines.analytic import AnalyticDiscipline
from gemseo.uncertainty.statistics.empirical_statistics import EmpiricalStatistics
from matplotlib import pyplot as plt

#Sellar's MDO problem
from gemseo_umdo.formulations.sampling_settings import Sampling_Settings
from gemseo_umdo.formulations.surrogate_settings import Surrogate_Settings
from gemseo_umdo.formulations.taylor_polynomial_settings import TaylorPolynomial_Settings

from gemseo_umdo.scenarios.umdo_scenario import UMDOScenario

from gemseo.utils.discipline import update_default_input_values

# %%
# ### 1. Create an empty parameter space
uncertain_space = ParameterSpace()
# %%
# ### 2. Add random variables
#
# A standard Gaussian variable $u$:
uncertain_space.add_random_variable("gi", "OTTriangularDistribution", minimum=0.35, mode=0.4, maximum=0.405)
uncertain_space.add_random_variable("vi", "OTTriangularDistribution", minimum=0.755, mode=0.800, maximum=0.805)
uncertain_space.add_random_variable("aef", "OTTriangularDistribution", minimum=0.99, mode=1., maximum=1.03)
uncertain_space.add_random_variable("cef", "OTTriangularDistribution", minimum=0.99, mode=1., maximum=1.03)
uncertain_space.add_random_variable("sef", "OTTriangularDistribution", minimum=0.8, mode=1., maximum=1.02)
uncertain_space.add_random_variable("fc_pwd", "OTTriangularDistribution", minimum=0.755, mode=0.800, maximum=0.805)
uncertain_space.add_random_variable("bed", "OTUniformDistribution", minimum=400, maximum=700)

print(uncertain_space)

#create discipline 
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

update_default_input_values(disciplines, {"fuel_type": "liquid_h2"})

#Desigh space 

design_space = DesignSpace()

design_space.add_variable("slst", size=1, lower_bound=convert_from('kN',100), upper_bound=convert_from('kN',200) ,value=convert_from('kN',150))

design_space.add_variable("n_pax", size=1, lower_bound=120, upper_bound=180 ,value=150)

design_space.add_variable("area", size=1, lower_bound=convert_from('m2',100), upper_bound=convert_from('m2',200) ,value=convert_from('m2',180))

design_space.add_variable("ar", size=1, lower_bound=5, upper_bound=20 ,value=9)

#Surrogate 

# ### 2. Generate training and test datasets
training_dataset = sample_disciplines(
 disciplines, design_space, ["mtom", "tofl", "vapp", "vz", "span", "length", "fm"], algo_name="OT_OPT_LHS", n_samples=30
)
test_dataset = sample_disciplines(
 disciplines, design_space, ["mtom", "tofl", "vapp", "vz", "span", "length", "fm"], algo_name="OT_FULLFACT", n_samples=30**2
)

# %%
print("Surrogate Discipline :")
# ### 3. Build the surrogate discipline
surrogate_discipline = SurrogateDiscipline("RBFRegressor", training_dataset)

# %%
print("Surrogate Discipline :")
# ### 3. Build the surrogate discipline
#Scenario avec les 3 approches de calcul de statistiques : Monte Carlo, Taylor et Surrogate
scenario = UMDOScenario(
    disciplines, #surrogate
    "mtom",
    design_space,
    uncertain_space,
    "Mean",
    formulation_name="MDF",
    statistic_estimation_settings=Surrogate_Settings(n_samples=200), #changer n_samples https://gemseo.gitlab.io/dev/gemseo-umdo/latest/user_guide/umdo/surrogate/
)   

"""scenario = UMDOScenario(
    disciplines, #surrogate
    "mtom",
    design_space,
    uncertain_space,
    "Mean",
    formulation_name="MDF",
    statistic_estimation_settings=Sampling_Settings(n_samples=200), #changer n_samples https://gemseo.gitlab.io/dev/gemseo-umdo/latest/user_guide/umdo/surrogate/
)"""

"""scenario = UMDOScenario(
    disciplines, #surrogate
    "mtom",
    design_space,
    uncertain_space,
    "Mean",
    formulation_name="MDF",
    statistic_estimation_settings=TaylorPolynomial_Settings(), #changer n_samples https://gemseo.gitlab.io/dev/gemseo-umdo/latest/user_guide/umdo/surrogate/
)"""
#statistic_estimation_settings=sampling_Settings(doe_n_samples=20), #MC
#statistic_estimation_settings=Taylor_Settings(doe_n_samples=20), #DL taylor

scenario.add_constraint("tofl",  "Margin", factor=2.0, value=convert_from('m',1900))
scenario.add_constraint("vapp",  "Margin", factor=2.0, value=convert_from('kt',135))
scenario.add_constraint("vz",  "Margin", positive = True, factor=2.0, value=convert_from('ft/min',300))
scenario.add_constraint("span",  "Margin", factor=2.0, value=convert_from('m',40))
scenario.add_constraint("length",  "Margin", factor=2.0, value=convert_from('m',45))
scenario.add_constraint("fm",  "Margin", positive = True, factor=2.0, value=0)

scenario.execute(algo_name="NLOPT_COBYLA", max_iter=200)
scenario.post_process(post_name="OptHistoryView", save=True, show=False)
result = scenario.optimization_result
print(result.x_opt, result.constraint_values, result.f_opt)
scenario.optimization_result

scenario.optimization_result.constraint_values
# %%
scenario.optimization_result.x_opt_as_dict
# %%
scenario.optimization_result.x_0_as_dict
# %%
# Plot the optimization history:
scenario.post_process(post_name="OptHistoryView", save=False, show=True)

print("execute", scenario.execute(algo_name="CustomDOE", samples=[scenario.optimization_result.x_opt_as_dict]))
print("result du CUSTOM", scenario.optimization_result)

# %%
# ### 3. Sample with Monte Carlo
dataset = sample_disciplines(
    disciplines, uncertain_space, ["mtom", "tofl", "vapp", "vz", "span", "length", "fm"], algo_name="OT_MONTE_CARLO", n_samples=1000
)

# %%dd!vb
# ### 4. Compute statistics
statistics = EmpiricalStatistics(dataset)
mean = statistics.compute_mean()
print(mean)

# %%
# Variance:
variance = statistics.compute_variance()
print(variance)

# %%
# !!! note
#
#     The mean and standard deviation of $w$ are approximately 0 and $\sqrt{2}$,
#     as expected for the sum of two independent Gaussian variables.

# %%
# ### 5. Plot the histograms
fig, axes = plt.subplots(1, 3)
for ax, name in zip(axes, ["mtom", "tofl", "vapp", "vz", "span", "length", "fm", "gi", "vi", "aef", "cef", "sef", "fc_pwd", "bed"]):
    ax.hist(dataset.get_view(variable_names=name))
    ax.set_title(name)


