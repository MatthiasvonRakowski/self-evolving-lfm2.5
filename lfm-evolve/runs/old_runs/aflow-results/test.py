import os, dotenv, litellm
from evoagentx.models import LiteLLMConfig, LiteLLM
dotenv.load_dotenv()

llm = LiteLLM(config=LiteLLMConfig(
    model="ollama_chat/lfm2.5-16k",
    is_local=True,
    api_base="http://localhost:11434",
))
litellm.api_base = None  # your usual leak guard

big = "Solve this math problem. " + ("context filler. " * 1200)  # ~5k+ tokens
print(llm.generate(prompt=big))
