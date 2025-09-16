import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any
from .base import BaseAgent

class OpenAIAgent(BaseAgent):
    """
    Agent for OpenAI Chat Completions API.
    Config keys:
      - base_url (optional, default: https://api.openai.com/v1/chat/completions)
      - model (required)
      - api_key (optional; fallback to env OPENAI_API_KEY)
      - parameters (optional): temperature, top_p, max_tokens, etc.
    """
    def infer(self, prompt: str, timeout: float) -> Dict[str, Any]:
        base_url = self.config.get("base_url") or "https://api.openai.com/v1/chat/completions"
        params = self.config.get("parameters", {})
        model = self.config.get("model") or params.get("model")
        api_key = self.config.get("api_key") or os.environ.get("OPENAI_API_KEY")

        if not model:
            return {"ok": False, "error": "model no configurado"}
        if not api_key:
            return {"ok": False, "error": "OPENAI_API_KEY no configurada"}

        payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        for k in ("temperature", "top_p", "max_tokens", "frequency_penalty", "presence_penalty", "stop"):
            if k in params:
                payload[k] = params[k]
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        req = urllib.request.Request(base_url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_text = resp.read().decode("utf-8")
                try:
                    raw_json = json.loads(raw_text)
                    response_text = (
                        raw_json.get("choices", [{}])[0].get("message", {}).get("content")
                        or raw_json.get("text")
                        or raw_text
                    )
                except Exception:
                    response_text = raw_text
                return {"ok": True, "response": response_text, "raw": raw_text}
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8")
            except Exception:
                detail = e.reason
            return {"ok": False, "error": f"HTTP {e.code}: {detail}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
