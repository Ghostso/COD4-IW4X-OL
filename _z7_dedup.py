"""Remove the duplicated jmp-target block left inside ProbeVsd; the logic now
lives in RecheckJmpTarget()."""
import io

P = r"restore_iips_contract_001\observer2\AboProbe.cs"
src = io.open(P, encoding="utf-8-sig").read()

start = src.find("            // Cheap periodic re-check of the packed entry point.")
if start < 0:
    print("marker not found")
    raise SystemExit(0)

lines = src[start:].splitlines(True)
depth = 0
end = None
for i, l in enumerate(lines):
    depth += l.count("{") - l.count("}")
    if i > 0 and depth == 0:
        end = i + 1
        break
if end is None:
    print("could not find block end")
    raise SystemExit(1)

removed = "".join(lines[:end])
src = src[:start] + "".join(lines[end:])
io.open(P, "w", encoding="utf-8-sig", newline="").write(src)
print("removed %d chars / %d lines" % (len(removed), end))
