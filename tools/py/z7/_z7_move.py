"""Move RecheckJmpTarget out from inside TraceEips so both are proper class
members."""
import io

P = r"restore_iips_contract_001\observer2\AboProbe.cs"
src = io.open(P, encoding="utf-8-sig").read()

# 1. cut the RecheckJmpTarget definition block
k_start = "        // §5.27.125  Cheap periodic re-read of the packed entry target."
k_end = "        }"
start = src.find(k_start)
if start < 0:
    print("start marker missing")
    raise SystemExit(1)

tail = src[start:]
lines = tail.splitlines(True)
depth = 0
end = None
for i, l in enumerate(lines):
    depth += l.count("{") - l.count("}")
    if i > 0 and depth == 0:
        end = i + 1
        break
if end is None:
    print("end not found")
    raise SystemExit(1)

block = "".join(lines[:end])
src = src[:start] + "".join(lines[end:])

# 2. close TraceEips where its body resumes, then append the moved block
anchor = "            // §5.27.107 diagnostics: prove the sampler actually runs, and"
if anchor not in src:
    print("anchor missing")
    raise SystemExit(1)
src = src.replace(
    anchor,
    "        }\n\n" + block + "\n" + anchor,
    1)

# 3. remove the now-duplicated empty stub left at the old site
src = src.replace(
    "            // -----------------------------------------------------------------\n"
    "            // (RecheckJmpTarget is defined just below this method.)\n"
    "            // -----------------------------------------------------------------\n"
    "        }\n\n",
    "", 1)

io.open(P, "w", encoding="utf-8-sig", newline="").write(src)
print("moved %d chars" % len(block))
