"""One tiny call per model to confirm the gateway works and see token usage. Never prints the key."""
import os
import sys

sys.path.insert(0, ".")
from recallops.llm import LLM  # noqa: E402

llm = LLM(max_calls=10)
for model in sys.argv[1:] or ["nova-micro", "nova-lite", "claude-haiku"]:
    llm.model = model
    try:
        out = llm.complete("Answer with one word.", "Is 'Acetaminophen' the same drug as 'Paracetamol'? yes or no", max_tokens=5)
        print(f"{model:14} ok -> {out!r}")
    except Exception as e:
        print(f"{model:14} FAILED: {type(e).__name__}: {str(e)[:160]}")
print("usage:", llm.usage(), "| key set:", bool(os.environ.get("LITELLM_API_KEY")))
