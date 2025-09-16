import json
import urllib.request
import urllib.error
from typing import Dict, Any
from .base import BaseAgent

class OllamaAgent(BaseAgent):
    def infer(self, prompt: str, timeout: float) -> Dict[str, Any]:
        base_url = self.config.get("base_url", "http://localhost:11434")
        model = self.config.get("model", "llama3:8b")
        params = self.config.get("parameters", {})
        url = f"{base_url}/api/generate"
        body = {"model": model, "prompt": prompt, **params}
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                # Ollama suele enviar JSON ND-JSON por líneas; consolidamos los campos 'response'
                pieces = []
                raw_chunks = []
                for line_bytes in resp:
                    try:
                        line = line_bytes.decode("utf-8")
                    except Exception:
                        continue
                    raw_chunks.append(line)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        j = json.loads(line)
                        if isinstance(j, dict):
                            if "response" in j:
                                pieces.append(j.get("response", ""))
                            if j.get("done") is True:
                                break
                    except Exception:
                        # si no es JSON por línea, ignoramos
                        pass
                raw_text = "".join(raw_chunks)
                response_text = "".join(pieces) if pieces else raw_text
                return {"ok": True, "response": response_text, "raw": raw_text}
        except urllib.error.HTTPError as e:
            return {"ok": False, "error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
