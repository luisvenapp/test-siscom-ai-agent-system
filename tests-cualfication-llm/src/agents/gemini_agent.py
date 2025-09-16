import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any, List
from .base import BaseAgent

class GeminiAgent(BaseAgent):
    """
    Agent for Google AI Studio (Gemini) REST API (no Vertex). Uses models.generateContent endpoint schema.
    Config keys:
      - base_url (optional; default: https://generativelanguage.googleapis.com/v1beta/models)
      - model (required), e.g., gemini-2.5-flash or gemini-2.5-pro
      - api_key (optional; fallback to env GOOGLE_API_KEY)
      - parameters (optional):
          * generationConfig: temperature, topP (top_p), topK (top_k), maxOutputTokens (max_tokens)
          * stopSequences (stop_sequences: list[str])
          * candidateCount (candidate_count: int)
          * systemInstruction (system_instruction: str)
          * safetySettings (safety_settings: list[dict]) pass-through
    """
    def infer(self, prompt: str, timeout: float) -> Dict[str, Any]:
        root = self.config.get("base_url") or "https://generativelanguage.googleapis.com/v1beta/models"
        model = self.config.get("model")
        api_key = self.config.get("api_key") or os.environ.get("GOOGLE_API_KEY")
        params = self.config.get("parameters", {})

        if not model:
            return {"ok": False, "error": "model no configurado"}
        if not api_key:
            return {"ok": False, "error": "GOOGLE_API_KEY no configurada"}

        # Endpoint: POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=API_KEY
        url = f"{root}/{model}:generateContent?key={api_key}"
        payload: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ]
        }
        # Optional system instruction
        sys_instr = params.get("system_instruction")
        if isinstance(sys_instr, str) and sys_instr.strip():
            payload["systemInstruction"] = {"parts": [{"text": sys_instr.strip()}]}

        # generationConfig
        gen_cfg_keys = {
            "temperature": "temperature",
            "top_p": "topP",
            "top_k": "topK",
            "max_tokens": "maxOutputTokens",
        }
        if any(k in params for k in gen_cfg_keys):
            generation_config: Dict[str, Any] = {}
            for src, dst in gen_cfg_keys.items():
                if src in params:
                    generation_config[dst] = params[src]
            payload["generationConfig"] = generation_config

        # stop sequences
        if isinstance(params.get("stop_sequences"), list):
            payload["stopSequences"] = params.get("stop_sequences")
        # candidate count
        if isinstance(params.get("candidate_count"), int):
            payload["candidateCount"] = params.get("candidate_count")
        # safety settings pass-through
        if isinstance(params.get("safety_settings"), list):
            payload["safetySettings"] = params.get("safety_settings")

        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw_text = resp.read().decode("utf-8")
                try:
                    raw_json = json.loads(raw_text)
                    # Extract text; if blocked or no candidates, return appropriate error.
                    candidates = raw_json.get("candidates", [])
                    if not candidates:
                        fb = raw_json.get("promptFeedback") or {}
                        block_reason = fb.get("blockReason")
                        if block_reason:
                            return {"ok": False, "error": f"Gemini blocked content: {block_reason}", "raw": raw_text}
                        return {"ok": False, "error": "Gemini did not return candidates", "raw": raw_text}
                    # concatenate all text parts of first candidate
                    parts: List[Dict[str, Any]] = candidates[0].get("content", {}).get("parts", [])
                    texts = [p.get("text") for p in parts if isinstance(p, dict) and p.get("text")]
                    response_text = "\n".join([t for t in texts if t]) if texts else raw_text
                    return {"ok": True, "response": response_text, "raw": raw_text}
                except Exception:
                    return {"ok": True, "response": raw_text, "raw": raw_text}
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8")
            except Exception:
                detail = e.reason
            return {"ok": False, "error": f"HTTP {e.code}: {detail}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
