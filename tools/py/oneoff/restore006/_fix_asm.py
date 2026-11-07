import io
p = r"restore006/build_localrm_v3.py"
s = io.open(p, encoding="utf-8").read()
reps = [
 ("a = Asm(new_va + OFF_GET)",   "a = Asm(IMAGE_BASE + new_va + OFF_GET)"),
 ("r = Asm(new_va + OFF_REL)",   "r = Asm(IMAGE_BASE + new_va + OFF_REL)"),
 ("dt = Asm(new_va + OFF_DTOR)", "dt = Asm(IMAGE_BASE + new_va + OFF_DTOR)"),
 ("st = Asm(new_va + OFF_STUB)", "st = Asm(IMAGE_BASE + new_va + OFF_STUB)"),
 ("i = Asm(init_va)",            "i = Asm(IMAGE_BASE + new_va + OFF_INIT)"),
 ("e = Asm(new_va + OFF_ENTRY)", "e = Asm(IMAGE_BASE + new_va + OFF_ENTRY)"),
 ("    init_va = new_va + OFF_INIT\n", ""),
]
for a,b in reps:
    if a not in s: print("NOT FOUND:", a)
    s = s.replace(a,b)
io.open(p,"w",encoding="utf-8").write(s)
print("done")
