import json
import urllib.request
import urllib.error
from typing import Dict, Any
from .base import BaseAgent

class HttpAgent(BaseAgent):
    def infer(self, prompt: str, timeout: float) -> Dict[str, Any]:
        base_url = self.config.get("base_url")
        headers = self.config.get("headers", {})
        params = self.config.get("parameters", {})
        schema = self.config.get("schema", "simple")
        if not base_url:
            return {"ok": False, "error": "base_url no configurado"}
        if schema == "openai":
            model = params.get("model", "local-model")
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
            for k in ("temperature", "top_p", "max_tokens"):
                if k in params:
                    payload[k] = params[k]
        else:
            payload = {"prompt": prompt, **params}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(base_url, data=data, headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_text = resp.read().decode("utf-8")
                try:
                    raw_json = json.loads(raw_text)
                    response_text = (
                        raw_json.get("response")
                        or raw_json.get("choices", [{}])[0].get("message", {}).get("content")
                        or raw_json.get("text")
                        or raw_text
                    )
                except Exception:
                    response_text = raw_text
                return {"ok": True, "response": response_text, "raw": raw_text}
        except urllib.error.HTTPError as e:
            return {"ok": False, "error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
