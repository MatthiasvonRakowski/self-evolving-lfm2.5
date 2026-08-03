SCRATCHPAD_PROMPT = """You are working out a math problem on scratch paper. Write out all arithmetic operations explicitly with their numerical values. List every multiplication, addition, subtraction, and division needed. Do not skip any numeric step. Just compute raw numbers without worrying about presentation.

Math problem: """

FINAL_SOLVE_PROMPT = """You are a math tutor. A rough scratchpad has already been computed for the problem below. Use the scratchpad calculations as a reference to write a clean, step-by-step solution. Verify each number matches the scratchpad.

Provide the final numerical answer on its own line prefixed with "#### ".

"""