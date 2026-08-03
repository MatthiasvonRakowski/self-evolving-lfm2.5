SOLVE_MATH_PROMPT = """You are a helpful math tutor. Solve the following grade-school math problem step by step.

Show your reasoning clearly, then provide the final numerical answer on its own line prefixed with "#### ".

Problem: """

VERIFY_MATH_PROMPT = """You are a careful math checker. You will solve the problem independently first, then compare with the previous solution.

Step 1: Re-solve the problem completely from scratch, showing all steps.
Step 2: Compare your answer with the previous solution. Identify any discrepancies.
Step 3: If both solutions agree, confirm the answer. If they disagree, carefully re-examine each step to find the error and determine the correct answer.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

Problem and previous solution to review: """

ARBITRATE_MATH_PROMPT = """You are an expert math arbitrator. Two solution attempts have been made for the problem below, but they appear to disagree or contain errors. Your job is to carefully analyze both attempts and determine the definitive correct answer.

Instructions:
1. Read the problem carefully.
2. Review both solution attempts critically.
3. Identify which steps are correct and which contain errors.
4. Solve the problem independently from scratch to confirm the correct answer.
5. Provide your final definitive answer.

Always end your response with the final numerical answer on its own line prefixed with "#### ".

Problem and both attempts: """