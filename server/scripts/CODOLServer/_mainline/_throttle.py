p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()
if "using System;\n" not in s:
    print("need System using")
else:
    print("System using present")

# 2) throttle the noisy debug samplers: emit at most every 0.5 s
old = '''                Ev("CODEC_KEYS", p604Str, p608Str,'''
new = '''                // Throttle: these used to fire on every change and produced
                // 8k+ lines per run, which slowed the loop.
                bool emitKeys = (t - lastCodecKeysEmit) >= 0.5;
                if (emitKeys) lastCodecKeysEmit = t;
                if (emitKeys) Ev("CODEC_KEYS", p604Str, p608Str,'''
assert old in s
s = s.replace(old, new, 1)

old2 = "        static string lastKeyObjPtrs = null;"
new2 = old2 + "\n        static double lastCodecKeysEmit = -1.0;"
assert old2 in s
s = s.replace(old2, new2, 1)

# throttle CONN_D9 the same way
old3 = '                Ev("CONN_D9",'
new3 = '''                bool emitD9 = (t - lastConnD9Emit) >= 0.5;
                if (emitD9) lastConnD9Emit = t;
                if (emitD9) Ev("CONN_D9",'''
assert old3 in s
s = s.replace(old3, new3, 1)

old4 = "        static double lastCodecKeysEmit = -1.0;"
new4 = old4 + "\n        static double lastConnD9Emit = -1.0;"
assert old4 in s
s = s.replace(old4, new4, 1)

# throttle P608_VTABLE / P604_VTABLE too
old5 = '                    Ev("P608_VTABLE",'
new5 = '''                    bool emitVt = (t - lastVtableEmit) >= 0.5;
                    if (emitVt) lastVtableEmit = t;
                    if (emitVt) Ev("P608_VTABLE",'''
assert old5 in s
s = s.replace(old5, new5, 1)

old6 = "        static double lastConnD9Emit = -1.0;"
new6 = old6 + "\n        static double lastVtableEmit = -1.0;"
assert old6 in s
s = s.replace(old6, new6, 1)

open(p, "w", encoding="utf-8").write(s)
print("throttling added")
