p = r"CODOLServer\_mainline\_e57a5c_experiment.py"
s = open(p, encoding="utf-8").read()
old = '''    if p608_key_file:
        argv += ["-AcReadyFlag", (p608_key_file.replace(".txt", "") +
                                  "_ac_ready.flag")]'''
new = '''    if p608_key_file:
        # Keep the flag next to the key file (same directory) so the probe and
        # the observer resolve the same path.
        argv += ["-AcReadyFlag", (p608_key_file[:-4] + "_ac_ready.flag"
                                  if p608_key_file.endswith(".txt")
                                  else p608_key_file + "_ac_ready.flag")]'''
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("path unified")
