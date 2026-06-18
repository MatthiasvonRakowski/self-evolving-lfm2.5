DECOMPOSE_PROMPT = """Extract and list all the key quantities, variables, and relationships from this math problem. For each quantity, write it as: [name] = [value or expression]. List what is being asked for at the end. Be concise and precise. Do not solve the problem yet.

Problem: """

SOLVE_WITH_DECOMP_PROMPT = """Solve the math problem below using the provided key quantities and relationships as a guide. Work through the arithmetic step by step, showing each calculation explicitly on its own line with its numeric result. Double-check your arithmetic before writing the final answer. End your response with the final answer on its own line in this exact format: #### <number>

"""