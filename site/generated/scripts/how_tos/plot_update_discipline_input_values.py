"""# Update the default input values of disciplines

## Problem

Several disciplines share input variables,
and their default values must be updated consistently across all of them.

## Solution

Use `update_default_inputs` from `lh2pac.utils`,
which updates only the disciplines that own the given input name.

## Step-by-step guide

The following steps update the default value of the shared variable `a`
across two disciplines.
"""
from numpy import array

from gemseo.disciplines.analytic import AnalyticDiscipline
from gemseo.utils.discipline import update_default_input_values

# %%
# ### 1. Create two disciplines sharing an input
discipline_1 = AnalyticDiscipline({"y": "a+b"})
discipline_2 = AnalyticDiscipline({"z": "a+d"})

# %%
# ### 2. Inspect default values before the update
discipline_1.io.input_grammar.defaults, discipline_2.io.input_grammar.defaults

# %%
# ### 3. Update the shared default value
update_default_input_values([discipline_1, discipline_2], {"a": array([1.])})

# %%
# ### 4. Inspect default values after the update
discipline_1.io.input_grammar.defaults, discipline_2.io.input_grammar.defaults

# %%
# ## Summary
#
# Pass a list of disciplines and a name-to-value mapping to `update_default_inputs`.
# Only disciplines that own a given input name are updated.
