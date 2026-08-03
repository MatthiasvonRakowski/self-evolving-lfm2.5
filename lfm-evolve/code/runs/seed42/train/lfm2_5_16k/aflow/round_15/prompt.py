SOLVE_MATH_PROMPT = """You are an expert math tutor solving grade-school math problems. Follow these steps carefully:

1. READ the problem carefully and identify all given quantities and what is being asked.
2. PATTERN: Identify the core mathematical relationship(s) governing this problem. Write them symbolically (e.g., "total_apples = apples_per_basket × number_of_baskets", "money_left = starting_money - amount_spent"). This maps the story to math structure before any calculation.
3. SUBSTITUTE: Replace each symbol in your pattern with the actual numbers from the problem, writing out the expression explicitly.
4. SOLVE step by step, writing out every arithmetic operation explicitly (e.g., 3 × 4 = 12).
5. CHECK each arithmetic operation you performed by recomputing it (e.g., verify 3 × 4 = 12 ✓).
6. STATE your final answer clearly.

After completing all steps, write the final numerical answer on its own line prefixed exactly with "#### " (e.g., #### 42).

Problem: """