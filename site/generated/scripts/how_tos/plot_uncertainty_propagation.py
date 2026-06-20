r"""# Propagate uncertainties

## Problem

Estimating the statistics of a model output
when some of its inputs are uncertain.

## Solution

Sample the discipline with a Monte Carlo algorithm,
then compute statistics from the resulting dataset
using `EmpiricalStatistics`.

## Step-by-step guide

The following steps propagate uncertainties through $f:u,v\mapsto u+v$
where $u\sim\mathcal{N}(-1,1)$ and $v\sim\mathcal{N}(1,1)$ are independent.
"""
from matplotlib import pyplot as plt

from gemseo import sample_disciplines
from gemseo.algos.parameter_space import ParameterSpace
from gemseo.disciplines.analytic import AnalyticDiscipline
from gemseo.uncertainty.statistics.empirical_statistics import EmpiricalStatistics

# %%
# ### 1. Define the uncertain space
uncertain_space = ParameterSpace()
uncertain_space.add_random_variable("u", "OTNormalDistribution", mu=-1.0)
uncertain_space.add_random_variable("v", "OTNormalDistribution", mu=1.0)

# %%
# ### 2. Create the discipline
discipline = AnalyticDiscipline({"w": "u+v"})

# %%
# ### 3. Sample with Monte Carlo
dataset = sample_disciplines(
    [discipline], uncertain_space, ["w"], algo_name="OT_MONTE_CARLO", n_samples=1000
)

# %%
# ### 4. Compute statistics
statistics = EmpiricalStatistics(dataset)
mean = statistics.compute_mean()
mean

# %%
# Variance:
variance = statistics.compute_variance()
variance

# %%
# !!! note
#
#     The mean and standard deviation of $w$ are approximately 0 and $\sqrt{2}$,
#     as expected for the sum of two independent Gaussian variables.

# %%
# ### 5. Plot the histograms
fig, axes = plt.subplots(1, 3)
for ax, name in zip(axes, ["u", "v", "w"]):
    ax.hist(dataset.get_view(variable_names=name))
    ax.set_title(name)

# %%
# ## Summary
#
# Define an uncertain space, sample the discipline with Monte Carlo,
# then use `EmpiricalStatistics` to compute mean, variance, and other statistics.
