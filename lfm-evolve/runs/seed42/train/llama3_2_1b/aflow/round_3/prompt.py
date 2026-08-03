SOLVE_MATH_PROMPT = """You are an expert math solver. Solve the following grade-school math problem with careful step-by-step reasoning.

Instructions:
1. Read the problem carefully and identify what is being asked.
2. Break down the problem into clear, logical steps.
3. Perform each arithmetic operation carefully, writing out the calculation explicitly.
4. After completing your solution, quickly verify your final answer by checking it makes sense in context.
5. State the final numerical answer on its own line prefixed with "#### ".

Important: The final line of your response must be in the format: #### <number>
Only output a single number after ####, with no units or extra text.

Problem: """