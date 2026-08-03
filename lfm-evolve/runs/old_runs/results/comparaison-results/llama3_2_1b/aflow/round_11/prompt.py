SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Instructions:
1. Read the problem carefully and identify all given information.
2. Solve the problem step by step, showing all calculations clearly.
3. After reaching an answer, verify it by checking: Does the answer make sense? Re-examine each arithmetic operation.
4. Correct any mistakes found during verification.
5. Provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

SOLVE_MATH_PROMPT_ALT = """You are an expert mathematician specializing in algebraic problem solving. Solve the following math problem by explicitly setting up variables and equations.

Instructions:
1. Carefully read the problem and identify all unknown quantities.
2. Define a variable (e.g., let x = ...) for the unknown quantity you need to find.
3. Translate the problem conditions into mathematical equations or expressions using those variables.
4. Solve the equations step by step, showing all arithmetic clearly.
5. Verify your answer by substituting back into the original equations to confirm correctness.
6. Provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

REVIEW_MATH_PROMPT = """You are a careful math checker. You will be given a math problem and multiple solution attempts.

Review all solutions:
1. Check each solution for arithmetic errors and logical correctness.
2. Identify which solution(s) are correct.
3. If solutions disagree, determine the correct answer by re-solving carefully from scratch.
4. Pick the single best final answer.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

"""