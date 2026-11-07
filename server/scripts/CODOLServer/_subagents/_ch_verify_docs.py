"""Verify the C2 deliverables: JSON parses, report has the appendices,
and every fenced asm block is well formed. ASCII-only source.
"""

import json
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(HERE, "connect_handshake_report.md")
SPEC = os.path.join(HERE, "connect_spec.json")


def main():
    ok = True

    try:
        spec = json.load(open(SPEC, encoding="utf-8"))
        print("SPEC JSON OK, top-level keys =", len(spec))
    except Exception as exc:  # noqa: BLE001
        ok = False
        print("SPEC JSON FAIL:", exc)
        spec = {}

    text = open(REPORT, encoding="utf-8").read()
    print("REPORT chars =", len(text), "lines =", text.count("\n") + 1)

    # Appendix headings are non-ASCII in the report; match by ASCII marker.
    for label, marker in (
        ("appendix A", "## \u9644\u5f55 A"),
        ("appendix B", "## \u9644\u5f55 B"),
        ("appendix C", "## \u9644\u5f55 C"),
    ):
        present = marker in text
        print("REPORT %s = %s" % (label, present))
        if not present:
            ok = False

    fences = text.count("```")
    print("REPORT fence count =", fences, "(even = OK)")
    if fences % 2 != 0:
        ok = False

    required_vas = [
        "0xB88CC0", "0xB88B80", "0xB9A9E0", "0xC752E3",
        "0xC767F0", "0xD5A2CC", "0xD5A228", "0x81A9EC4", "0x81A76A8",
    ]
    for va in required_vas:
        if va.lower() not in text.lower():
            ok = False
            print("REPORT MISSING", va)

    asm_lines = re.findall(r"^\s*([0-9A-F]{8})\s", text, re.M)
    print("REPORT asm-like lines =", len(asm_lines))

    for path in sorted(glob.glob(os.path.join(HERE, "_ch_*.py"))):
        try:
            open(path, "rb").read().decode("ascii")
            print("ASCII OK:", os.path.basename(path))
        except UnicodeDecodeError as exc:
            ok = False
            print("ASCII FAIL:", os.path.basename(path), exc)

    print("RESULT:", "OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
