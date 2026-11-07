# TCLS → Client hand-off recovery (CODOL offline revival) — session findings

Status: **static recovery of the TCLS-side hand-off COMPLETE and validated**, plus live
evidence of how far the original client gets under it. All original binaries untouched.

## 1. Command line used by TCLS when it starts the game (statically recovered)

Wide template in `TCLS.dll` at `0x103C53CC`:

```
"%s" -q %u -i %d -s %d -g %d -u %u -n %s
```

* args, in order (push order reversed at `0x100449BC`..`0x100449EF`):
  `exe path`, `this+0xCC` (uId), `this+0x491B4`, `[ebp-0xE48]` (from `this+0x9D8` indexed
  by `this+0x2B8`), caller arg `[ebp+8]`, `this+0x48F94`, `this+0x46C14`.
* optional tail appended when the tcls daemon flag `channel->vtbl+0xA8()` returns 0:
  `L" -m --1"` at `0x103C53BC` (append at `0x10044A31`).
* the *repair tool* has its own, shorter template at `0x103C4E30`: `"%s" -q %u -i %d`.

`CreateProcessW` call site `0x10044AE4` (function `0x100447C0`):

```c
CreateProcessW(exe,           // [ebp-0x620]  workpath\name from [Cross]/Path (0x1002A5C0)
               cmdline,       // [ebp-0xE40]
               NULL, NULL,
               TRUE,          // bInheritHandles -- so the game inherits the mappings' handles
               0,             // dwCreationFlags: NOT suspended
               NULL,
               workdir,       // [ebp-0xA30] expanded (0x10047EB0)
               &si, &pi );    // si.cb = 0x44
```

`hProcess` is kept in `this+0x491C0`; the sibling launcher `0x10044360` (section
`LevelRepair`, `0x103C51B0`) stores it in `this+0x491C4` and immediately `CloseHandle`s it.

## 2. Shared-memory hand-off (the part the client consumes)

TAS writer `TCLS.dll 0x1003FD10` (wide name prefix `0x103C2DF0`), pid formatted with
`L"%d"` (`0x103BF7B0`), built from the **pid of the process TCLS just created**:

| step | evidence |
| --- | --- |
| name | `TCLS_TASMEMORY_<pid>` (wide) |
| security | `InitializeSecurityDescriptor` + `SetSecurityDescriptorDacl(1,NULL,1)` -> NULL DACL |
| create | `CreateFileMappingW(INVALID_HANDLE_VALUE,&sa,PAGE_READWRITE,0,0x7AC,name)` |
| map | `MapViewOfFile(FILE_MAP_ALL_ACCESS /*0xF001F*/)` |
| keep | handle returned to caller (object stays alive) |

TAS layout (0x7AC bytes):

```
+0x000  DWORD  ready flag        (0 while filling, 1 after encrypting: 0x10040207)
+0x004  DWORD  0x7AC             (0x1003FFFB)
+0x008  DWORD  len1  <= 0x400     (0x1004000B..0x10040020)
+0x00C  DWORD  len2  <= 0x80
+0x010  BYTE[0x400] block1       (daemon data, memcpy at 0x1004005C)
+0x410  BYTE[0x80]  block2
+0x490  DWORD  field (daemon struct)
+0x494  DWORD  field
+0x498  char[0x104] UTF-8 text    (wide->UTF8 at 0x100400DC)
--- then: encrypt [0x004, 0x7AC) in place, length 0x7A8 (0x100401FF) ---
```

SHELL writer `TCLS.dll 0x1003F500` (prefix `0x103C24F4`, size `0x224`, **plaintext**):

```
+0x000  DWORD 0        +0x004 DWORD 0x224
+0x008  DWORD field    +0x00C DWORD field      +0x010 DWORD 1
```
Note the two writers store the *same* daemon dword at TAS+0x490 and SHELL+0x008.

## 3. The cipher (recovered exactly — used for TAS memory and for Tenio files)

* key source `0x100D7BF0`: `CreateFileW(path, GENERIC_READ, share=3, OPEN_EXISTING)` +
  `GetFileTime(h,NULL,NULL,&ftLastWrite)` -> 8 key bytes  `pack('<II', lo, hi)`;
  when the file time is 0 it falls back to `0x46D14CF9 / 0xEF1DC888`.
  In the TAS path the key is the file time of the **game exe** (`this+0x461EC`).
* KSA `0x100D7920(key8, flag, out key2, out table)`:
  ```
  MASK = 8A E6 9B F3 C1 7D 40 25
  key2[i] = key[i] ^ MASK[i]                                  (i = 0..7)
  seed    = BE32(key2[0:4]) ^ BE32(key2[4:8])
  sbox[i] = i ; state = seed
  for i in 0..255: state = state*0x343FD + 0x269EC3           (MSVCRT rand())
                   j = (state >> 16) & 0xFF ; swap(sbox[i], sbox[j])
  if flag == 0: table = inverse(sbox)                          (0x100D7ABF..0x100D7B1E)
  ```
* transform `0x100D7720(key2, flag, buf)`, per byte i:
  ```
  enc (flag=1): x ^= i;  x ^= key2[i&7]; x = table_inv[x]; x ^= key2[i&7]
  dec (flag=0): x ^= key2[i&7]; x = table_fwd[x]; x ^= key2[i&7]; x ^= i
  ```
* wrapper used by the TAS writer: `0x100D7D60(key_lo, key_hi, buf, len)` -> `flag = 1`.

Implemented and self-tested in `COD OL\scripts\tas_crypt.py` (round-trip verified, and the
decrypted copy of our own TAS payload reads back as `size=0x7AC`, text at `+0x498`).

Client-side names (`codoMP_client_shipRetailBase.dll`, module base 0x5D570000 in the live
run): `L"%s%d"` @ `0x10890130`, `L"TCLS_TASMEMORY_"` @ `0x10890138`, ASCII @ `0x10890158`
(`tersafe.dll` / `tcj.dll` / `ace-*` carry the same strings; the readers are protected and
have no plain call xrefs).

## 4. Live behaviour with the recovered hand-off (measured, not assumed)

`COD OL\scripts\codol_launch.py` re-implements steps 1-2 (suspended create -> mappings ->
resume) and `scripts\watch_game.py` samples the target process over time
(modules / named kernel objects / windows / sockets / memory markers).

| observation | result |
| --- | --- |
| window | `class=CoD Splash Screen`, title `使命召唤online Multiplayer`, rect (559,253)-(1361,765), **visible=True at t+10s** |
| named objects | only `\Sessions\1\BaseNamedObjects\TenProtect3_Share_Data_<pid>` (created by the game itself); no other TCLS/TenProtect events or mutexes |
| sockets | 4x ESTABLISHED to Tencent endpoints (`101.72.248.61:80/443`, `116.133.6.147:80`, `116.131.225.226:443`) + 3 UDP |
| modules | full stack loaded: `tersafe.dll`, `ACE-DRV32.dll`, `ace-ats32.dll`, `tcj.dll`, `TenRpcs.dll`, `GameRpcs.dll`, `GbSpy.dll`, `TenProxy.dll`, `policyprobe.dll`, `BugTrace.dll`, `GDPLoader/GDPImpl`, `bink2w32.dll`, `d3d9.dll` |
| lifetime | exits ~20-40 s after start, **exit code 0xFFFFFFFF**, and `COD OL\BugTrace.log` is rewritten at the same moment (anti-cheat abort record) |
| our TAS markers (`CODOLBLOCK1-MARKER`, `CODOL-TEXT-MARKER`) | **not found** in the game's memory at t+6 s (control string `codoMP_client` found, so the scan is valid) |
| our mapping handles | `TCLS_TASMEMORY_<pid>` / `TCLS_SHELLMEMORY_<pid>` were never seen in the game's handle list (t+10 s / t+12 s samples) |

Interpretation: the TCLS hand-off we recovered is *sufficient to reach the visible splash*,
but the client aborts later for a reason **beyond the TCLS hand-off** — TenProtect/TAS +
platform (iips) authentication, which needs live Tencent services. Memory reads of the game
process also stop working after ~10 s (ACE protects it), so later marker scans are
inconclusive by tooling limits, not by evidence of use.

Notes: launching `-q` directly from an (unelevated) shell produces the same splash + ~30 s
abort, so elevation/parent-process is not the difference; the old "clean exit" baseline was
not reproducible in this environment.

## 5. Tools added this session (all under `COD OL\scripts\`)

| tool | purpose |
| --- | --- |
| `tas_crypt.py` | Tenio cipher (KSA/enc/dec) + `selftest`; `dec/enc <keyhex\|default> <file>`; `brute <file>` |
| `codol_launch.py` | launcher prototype: recovered cmdline + TAS/SHELL mappings (`--mode baseline\|full`, `--no-shm`, `--keep`) |
| `watch_game.py` | launches and samples the game over time -> `analysis_logs\game_watch*.txt` |
| `procmem.py` | `modules`, `windows`, `scan`, `dump`, `cmd_scan_multi` (fast multi-pattern scan) |
| `prochandles.py` | named Section/Event/Mutant/Semaphore objects of a pid (extended handle info) |
| `probe_handoff.py` | one-shot: launch + marker scan, prints scan results |

Logs written: `analysis_logs\game_watch.txt`, `game_watch2.txt`, `game_watch3.txt`,
`game_modules.txt`, `launch_baseline.txt`, `probe_out.txt`, `TCLS_cipher_core.txt`,
`TCLS_ksa.txt`, plus the earlier `TenBase_*` / `TCLS_*` disasm dumps.

## 6. Verified / still unknown

Verified: everything in sections 1-4 (offsets come from the disassembly dumps; the cipher is
round-trip tested; splash/abort/sockets are measured).

Still unknown (do NOT fabricate):
* semantics of `-i`, `-s`, `-g`, `-u` and of the `-n` name; `this+0x48F94`,
  `this+0x46C14`, `this+0x491B4`, `this+0x9D8[i]` field meanings.
* actual `uId` / cltkey / gameSignature / OpenID / LoginKey values (all live-account data).
* content the Tenio daemon puts into TAS block1/block2 (offline it is unavailable).
* whether the client ever opens `TCLS_TASMEMORY_<pid>` in a *successful* TAS login path
  (the reader lives in protected TenProtect code; the string is present in the client DLL).
* `commonconfig.cfg` / `tlog\*.log` decryption: **not** this cipher with a local file-time
  key (brute over 570 local exe/dll file times + the default key failed for both directions),
  so their key/format is still open.

## 7. Suggested next steps

1. Redirect the four platform endpoints (hosts/DNS + local stub) with the existing
   `CODOLServer` work, then watch whether the splash proceeds to the login menu.
2. Recover the reader side: which TenProtect module consumes `TCLS_TASMEMORY_<pid>` — e.g.
   hook `OpenFileMappingW` inside the game process with the existing `rt_hook.py` approach.
3. If block1 must be valid, obtain a real TAS login block from an immutable live-era capture
   instead of inventing one.
4. Config decryption: try key = file time of the writer process (`TCLS\Client.exe`,
   `Assistant.exe`, `TPSvc.exe`) with different cipher parameters, or locate the real prologue
   of the `TenBase 0x10054100` loader (0x10054100 is mid-function).
