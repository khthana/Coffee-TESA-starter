"""Ask an OpenAI-compatible LLM (vLLM gateway, Ollama, OpenAI) for a JSON answer.

ask_json() never raises: on timeout, a bad answer or any error it returns None and the
caller falls back to rules. Local LLMs fail often — the agent must survive that.
"""
import json
import re
import time

from openai import OpenAI

# Ways to switch Qwen's "thinking" on/off; servers disagree, so try each and remember what works.
THINKING_STYLES = [
    lambda on: {"reasoning_effort": "medium" if on else "none"},                    # Ollama, OpenAI
    lambda on: {"extra_body": {"chat_template_kwargs": {"enable_thinking": on}}},    # vLLM
]


class LLM:
    def __init__(self, base_url: str, model: str, api_key: str, timeout: float = 60, thinking: bool = False,
                 max_tokens: int = 1500, temperature: float = 0.7):
        self.client = OpenAI(base_url=base_url, api_key=api_key or "none", timeout=timeout, max_retries=0)
        self.model, self.thinking, self.timeout = model, thinking, timeout
        self.max_tokens, self.temperature = max_tokens, temperature
        self.style = 0
        self.last_error = None

    def ask_json(self, system: str, user: str, schema: dict, timeout: float | None = None) -> dict | None:
        self.last_error = None
        client = self.client.with_options(timeout=min(timeout, self.timeout)) if timeout else self.client
        t0 = time.time()
        for style in range(self.style, len(THINKING_STYLES)):
            try:
                r = client.chat.completions.create(
                    model=self.model, temperature=self.temperature, max_tokens=self.max_tokens,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    response_format={"type": "json_schema", "json_schema": {"name": "answer", "schema": schema}},
                    **THINKING_STYLES[style](self.thinking))
            except Exception as e:                       # noqa: BLE001 — any failure means "use the fallback"
                self.last_error = f"{type(e).__name__}: {e}"[:300]
                if getattr(e, "status_code", None) == 400:   # server did not like this thinking switch
                    continue
                return None
            self.style = style
            text = r.choices[0].message.content or ""
            answer = parse_json(text)
            if answer is None:
                self.last_error = f"not JSON (finish={r.choices[0].finish_reason}): {text[:200]!r}"
            self.seconds = round(time.time() - t0, 1)
            return answer
        return None


def parse_json(text: str) -> dict | None:
    """Accept plain JSON, JSON in ``` fences, or JSON after a <think> block."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    for candidate in (text, *re.findall(r"\{.*\}", text, flags=re.S)):
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            pass
    return None
