# -*- coding: utf-8 -*-
"""Local native chain: services only, never a game client."""
from pathlib import Path
import subprocess
import sys
CHAIN = Path(__file__).resolve().parents[1]
def main():
    seconds = sys.argv[1] if len(sys.argv) > 1 else "600"
    return subprocess.call([sys.executable, "-X", "utf8", str(CHAIN / "scripts" / "service_stack.py"), "--seconds", seconds], cwd=str(CHAIN))
if __name__ == "__main__":
    raise SystemExit(main())
