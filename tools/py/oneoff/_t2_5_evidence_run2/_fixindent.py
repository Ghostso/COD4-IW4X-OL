import io
p = "build_deliverables.py"
lines = io.open(p, encoding="utf-8").read().split("\n")
start = next(i for i, l in enumerate(lines) if l.startswith('A("> 该偏差'))
end = next(i for i, l in enumerate(lines) if l.startswith('A("## 6.'))
fixed = 0
for i in range(start + 1, end):
    if lines[i].startswith("    A("):
        lines[i] = lines[i][4:]
        fixed += 1
io.open(p, "w", encoding="utf-8", newline="").write("\n".join(lines))
print("de-indented", fixed, "lines between", start + 1, "and", end)
