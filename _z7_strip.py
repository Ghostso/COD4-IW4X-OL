"""Remove the now-redundant VSD_VTABLE_DUMP block (its string reparsing was
unreliable; VSD_VT records the same data at the point of proof)."""
import io

P = r"restore_iips_contract_001\observer2\AboProbe.cs"
src = io.open(P, encoding="utf-8-sig").read()

start = src.find("                // §5.27.123: dump the vtable behind each")
if start < 0:
    print("marker not found; nothing to do")
    raise SystemExit(0)

# find the enclosing block: from the comment to the closing brace of the
# "{" that follows it
brace = src.find("{", start)
depth = 0
i = brace
while i < len(src):
    if src[i] == "{":
        depth += 1
    elif src[i] == "}":
        depth -= 1
        if depth == 0:
            break
    i += 1

end = i + 1
removed = src[start:end]
src = src[:start] + src[end:]
io.open(P, "w", encoding="utf-8-sig", newline="").write(src)
print("removed %d chars" % len(removed))
