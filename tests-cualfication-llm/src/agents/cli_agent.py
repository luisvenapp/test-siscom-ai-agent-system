import subprocess
from typing import Dict, Any
from .base import BaseAgent

class CliAgent(BaseAgent):
    def infer(self, prompt: str, timeout: float) -> Dict[str, Any]:
        cmd = self.config.get("cmd")
        args = self.config.get("args", [])
        use_stdin = self.config.get("prompt_stdin", True)
        if not cmd:
            return {"ok": False, "error": "cmd no configurado"}
        try:
            if use_stdin:
                proc = subprocess.run([cmd, *args], input=prompt.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            else:
                proc = subprocess.run([cmd, *args, prompt], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            if proc.returncode != 0:
                return {"ok": False, "error": proc.stderr.decode("utf-8", errors="ignore")}
            text = proc.stdout.decode("utf-8", errors="ignore")
            return {"ok": True, "response": text, "raw": text}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"timeout {timeout}s"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
