p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()
before = s.count("t >= 30.0")
s = s.replace("if (!post83Watch && t >= nextPtrTrack && t >= 30.0)",
              "if (!post83Watch && t >= nextPtrTrack)   // no t>=30 gate: the probe\n                                                          // answers ~0.17 s after accept,\n                                                          // long before 30 s")
s = s.replace("if (!post83Watch && t >= nextP608CtxSample && t >= 30.0)",
              "if (!post83Watch && t >= nextP608CtxSample)   // no t>=30 gate (see above)")
after = s.count("t >= 30.0")
open(p, "w", encoding="utf-8").write(s)
print("occurrences before:", before, "after:", after)
