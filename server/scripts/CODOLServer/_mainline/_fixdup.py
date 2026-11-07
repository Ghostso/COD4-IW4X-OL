p = r"CODOLServer\_mainline\_e57a5c_experiment.py"
lines = open(p, encoding="utf-8").read().split("\n")
# line 201 (index 200) is the stray "if p608_key_file:" ; remove it
assert lines[200].strip() == "if p608_key_file:", repr(lines[200])
assert lines[201].strip() == "if p608_key_file:", repr(lines[201])
del lines[200]
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("removed duplicate line")
