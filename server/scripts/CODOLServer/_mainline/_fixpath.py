p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()

# 1) resolve the live-key paths to absolute, creating the directory once
old = "            liveP608KeyFile = handshakeP608KeyFile;"
new = '''            // Resolve to absolute paths: a relative path made File.WriteAllText
            // throw DirectoryNotFoundException on every sample (~100/s), which
            // flooded the log and likely slowed the sampling loop.
            Func<string, string> abs = (f) =>
            {
                if (string.IsNullOrEmpty(f)) return f;
                try { return Path.GetFullPath(f); } catch (Exception) { return f; }
            };
            liveP608KeyFile = abs(handshakeP608KeyFile);
            acReadyFlag = abs(acReadyFlag);
            foreach (var f in new[] { liveP608KeyFile, liveRxKeyFile, liveTxKeyFile,
                                      acReadyFlag })
            {
                if (string.IsNullOrEmpty(f)) continue;
                try
                {
                    var dir = Path.GetDirectoryName(f);
                    if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                        Directory.CreateDirectory(dir);
                }
                catch (Exception) { }
            }'''
assert old in s
s = s.replace(old, new, 1)

open(p, "w", encoding="utf-8").write(s)
print("paths resolved to absolute")
