# -*- coding: utf-8 -*-
"""Frozen native chain: same server stack, then launch the C client."""
from pathlib import Path
import os
import json
import subprocess
import sys
import time
CHAIN = Path(__file__).resolve().parents[1]
KIT = CHAIN / "kit"
GAME = CHAIN / "game"
LOGS = CHAIN / "logs"
def main():
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 600
    stack = subprocess.Popen([sys.executable, "-X", "utf8", str(CHAIN / "scripts" / "service_stack.py"), "--seconds", str(seconds)], cwd=str(CHAIN), creationflags=subprocess.CREATE_NO_WINDOW)
    ready = CHAIN / "stack_ready.json"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not ready.exists():
        if stack.poll() is not None:
            return stack.returncode or 1
        time.sleep(0.25)
    if not ready.exists():
        stack.terminate()
        raise SystemExit("native server stack did not become ready")
    try:
        state = json.loads(ready.read_text(encoding="utf-8"))
        state["client_started"] = True
        ready.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as exc:
        print("[native-chain] unable to update stack state: " + repr(exc), flush=True)
    out = LOGS / "frozen_nt10.txt"
    cmd = [sys.executable, "-X", "utf8", str(KIT / "nt10.py"), "--root", str(GAME), "--secs", str(seconds), "--delay", "0", "--out", str(out), "--apis", "OpenFileMappingW,CreateFileMappingW,MapViewOfFile,connect,sendto,WinHttpConnect,WinHttpOpenRequest,WinHttpSendRequest,z1,z2"]
    env = os.environ.copy()
    env["CODOL_NATIVE_CHAIN"] = "1"
    env["CODOL_NATIVE_CHAIN_CLIENT"] = "1"
    print("NATIVE_CHAIN_READY client_started=true", flush=True)
    try:
        return subprocess.call(cmd, cwd=str(KIT), env=env)
    finally:
        if stack.poll() is None:
            stack.terminate()
            try:
                stack.wait(timeout=5)
            except Exception:
                stack.kill()
if __name__ == "__main__":
    raise SystemExit(main())
