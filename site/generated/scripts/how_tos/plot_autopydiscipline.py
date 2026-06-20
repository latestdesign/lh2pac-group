"""# Create a discipline from a Python function

## Problem

GEMSEO workflows require disciplines,
but the model is already implemented as a plain Python function.

## Solution

Wrap the function with `AutoPyDiscipline`.

## Step-by-step guide

The following steps wrap a rectangle area function as a GEMSEO discipline.
"""

from gemseo.disciplines.auto_py import AutoPyDiscipline


# %%
# ### 1. Define the Python function
def compute_area(width: float = 1., length: float = 1.) -> float:
    """Compute the area of a rectangle.

    Args:
        width: The width of the rectangle.
        length: The length of the rectangle.

    Returns:
        The area of the rectangle.
    """
    area = width * length
    return area

# %%
# ### 2. Create the discipline
discipline = AutoPyDiscipline(compute_area)

# %%
# Inspect its inputs, outputs, and default values:
list(discipline.io.input_grammar)
# %%
list(discipline.io.output_grammar)
# %%
discipline.io.input_grammar.defaults

# %%
# ### 3. Execute the discipline
#
# With default values:
discipline.execute()

# %%
# With custom input values:
discipline.execute({"width": 2.})
# %%
discipline.execute({"length": 3.})
# %%
discipline.execute({"width": 2., "length": 3.})

# %%
# ## Summary
#
# Pass the Python function to `AutoPyDiscipline`.
# Type annotations and default argument values are used
# to infer input/output names and default values automatically.
