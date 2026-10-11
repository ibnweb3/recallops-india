"""Thin OpenAI-compatible client for the hackathon LiteLLM gateway, with a hard call cap.

Config comes from the environment (.env is loaded, never printed):
  LITELLM_API_KEY   gateway key
  LLM_BASE_URL      default https://litellm.vision.aivar.app/v1
  LLM_MODEL         default model for judgement calls (default nova-lite, the cheap one)
  LLM_DRAFT_MODEL   model for drafted notices (default claude-haiku)
  RECALLOPS_MAX_LLM_CALLS   refuse further calls after this many (default 150); the budget is $20 in total
The code does the matching and arithmetic; the model is only asked about ambiguous names/aliases and
to draft notices.
"""
from __future__ import annotations

import os
import time

from . import tracing

DEFAULT_BASE_URL = "https://litellm.vision.aivar.app/v1"


class BudgetExceeded(Exception):
    pass


class LLM:
    def __init__(self, model: str | None = None, draft_model: str | None = None, max_calls: int | None = None):
        from dotenv import load_dotenv

        load_dotenv()
        self.model = model or os.environ.get("LLM_MODEL", "nova-lite")
        self.draft_model = draft_model or os.environ.get("LLM_DRAFT_MODEL", "claude-haiku")
        self.max_calls = max_calls if max_calls is not None else int(os.environ.get("RECALLOPS_MAX_LLM_CALLS", "150"))
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import openai  # imported late: neatlogs.init() has to run first

            key = os.environ.get("LITELLM_API_KEY")
            if not key:
                raise RuntimeError("LITELLM_API_KEY is not set (put it in .env)")
            self._client = tracing.wrap_client(openai.OpenAI(api_key=key, base_url=os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL), timeout=60))
        return self._client

    def complete(self, system: str, user: str, *, draft: bool = False, max_tokens: int = 300) -> str:
        if self.calls >= self.max_calls:
            raise BudgetExceeded(f"LLM call cap of {self.max_calls} reached")
        self.calls += 1
        last = None
        for attempt in range(2):
            try:
                r = self.client.chat.completions.create(
                    model=self.draft_model if draft else self.model, temperature=0, max_tokens=max_tokens,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
                if r.usage:
                    self.prompt_tokens += r.usage.prompt_tokens or 0
                    self.completion_tokens += r.usage.completion_tokens or 0
                return (r.choices[0].message.content or "").strip()
            except Exception as e:  # network blips, gateway 5xx: one retry, then surface
                last = e
                time.sleep(1.5)
        raise last

    def usage(self) -> dict:
        return {"calls": self.calls, "prompt_tokens": self.prompt_tokens, "completion_tokens": self.completion_tokens}
