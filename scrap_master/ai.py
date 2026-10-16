# -*- coding: utf-8 -*-
"""LLM access for MANOLO Scrap — local Ollama or OpenRouter, plain HTTP, no SDKs."""

import json
import re
import urllib.request
from typing import Dict, List

OLLAMA_URL = "http://localhost:11434"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OLLAMA_MODEL = "llama3.1"
DEFAULT_OPENROUTER_MODEL = "free"  # auto-pick a currently free model (no credits needed)
_SKIP_FREE = ("safety", "guard", "code", "embed", "vl", "omni")


class AIError(RuntimeError):
    pass


def _cfg():
    from scrap_master.config import Config

    return Config()


def provider_info() -> Dict[str, str]:
    c = _cfg()
    provider = c.get("ai_provider") or ("openrouter" if c.get("openrouter_api_key") else "ollama")
    if provider == "openrouter":
        model = c.get("openrouter_model") or DEFAULT_OPENROUTER_MODEL
    else:
        model = c.get("ollama_model") or DEFAULT_OLLAMA_MODEL
    return {"provider": provider, "model": model}


def _post(url: str, payload: dict, headers: Dict[str, str], timeout: int) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise AIError(f"{url}: {type(e).__name__}: {e}") from e


def chat(messages: List[Dict[str, str]], json_mode: bool = False, timeout: int = 180) -> str:
    """Send a chat request to the configured provider and return the reply text."""
    info = provider_info()
    if info["provider"] == "openrouter":
        key = _cfg().get("openrouter_api_key")
        if not key:
            raise AIError("No OpenRouter key. Set it in Settings or: scrap-master configure openrouter-key")
        models = [info["model"]] if info["model"] != "free" else []
        models += [m for m in free_openrouter_models()[:5] if m not in models]
        last: Exception = AIError("No OpenRouter model available")
        for model in models:
            payload = {"model": model, "messages": messages}
            try:
                data = _post(
                    OPENROUTER_URL,
                    payload,
                    {"Authorization": f"Bearer {key}", "X-Title": "MANOLO Scrap"},
                    timeout,
                )
                content = data["choices"][0]["message"]["content"]
                if content:
                    return content
            except (AIError, KeyError, IndexError, TypeError) as e:
                # 402 no credits / 429 rate limit / 404 retired model -> try the next free model
            {"Authorization": f"Bearer {key}", "X-Title": "MANOLO Scrap"},
            timeout,
        )
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise AIError(f"Unexpected OpenRouter reply: {str(data)[:300]}") from e

    payload = {"model": info["model"], "messages": messages, "stream": False}
    if json_mode:
        payload["format"] = "json"
    data = _post(f"{OLLAMA_URL}/api/chat", payload, {}, timeout)
    return data.get("message", {}).get("content", "")


def ollama_models() -> List[str]:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3) as resp:
            return [m["name"] for m in json.loads(resp.read())["models"]]
    except Exception:
        return []


def parse_json(text: str) -> dict:
    """Parse the first JSON object in a model reply (tolerates code fences / chatter)."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise AIError(f"Model did not return JSON: {text[:200]}")
    return json.loads(m.group(0))


PLAN_PROMPT = """You plan web-scraping jobs. The user describes what data they want.
Reply with ONLY a JSON object:
{
  "project_name": "short folder name",
  "queries": ["3-6 precise web search queries that find pages or files with this data"],
  "urls": ["known direct URLs to start from, if any (else empty)"],
  "file_types": [".pdf"],
  "depth": 0 or 1 (1 = also follow same-site links from result pages),
  "extract_text": true or false (extract text / OCR from downloaded PDFs),
  "max_documents": 5-60
}"""


def plan_job(request: str) -> dict:
    reply = chat(
        [{"role": "system", "content": PLAN_PROMPT}, {"role": "user", "content": request}],
        json_mode=True,
    )
    plan = parse_json(reply)
    plan.setdefault("project_name", request[:40])
    plan["queries"] = [q for q in plan.get("queries") or [] if isinstance(q, str)][:8] or [request]
    plan["urls"] = [u for u in plan.get("urls") or [] if isinstance(u, str) and u.startswith("http")]
    plan["file_types"] = [
        e if e.startswith(".") else f".{e}" for e in (plan.get("file_types") or [".pdf"])
    ]
    plan["depth"] = 1 if plan.get("depth") else 0
    plan["extract_text"] = bool(plan.get("extract_text", True))
    plan["max_documents"] = max(1, min(int(plan.get("max_documents") or 20), 100))
    return plan


def summarize(request: str, material: str) -> str:
    return chat(
        [
            {
                "role": "system",
                "content": "You write concise Markdown reports about scraped data: what was "
                "collected, key findings, gaps, and suggested next scrapes. Use only the "
                "material given.",
            },
            {"role": "user", "content": f"Request: {request}\n\nMaterial:\n{material[:24000]}"},
        ]
    )
