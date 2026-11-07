"""Check whether [obj+0x608] points at obj+0x5FC (the TLS buffer)."""
from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    stdout = Path(sys.argv[1])
    text = stdout.read_text(encoding="utf-8", errors="replace")
    prov = re.search(r"POST83_PROVIDERS,p604=(\d+) p608=(\d+)", text)
    sample = re.search(r"POST83_SAMPLE,req=0x([0-9A-Fa-f]+)", text)
    if not prov or not sample:
        print("missing fields")
        return 1
    p604, p608 = int(prov.group(1)), int(prov.group(2))
    req = int(sample.group(1), 16)
    print("req      ", hex(req))
    print("req+0x5FC", hex(req + 0x5FC))
    print("p604     ", hex(p604))
    print("p608     ", hex(p608))
    print("p608 == req+0x5FC ?", p608 == req + 0x5FC)
    print("p608 == req        ?", p608 == req)
    print("p604 == req        ?", p604 == req)
    print("p608 - req        =", hex(p608 - req))
    print("p604 - p608       =", p604 - p608)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
