# HISTORICAL ARCHAEOLOGY — Reference research, Assets (IFS/FF/IWD/PAK), non-lobby experiments, tooling

**Anchor:** 2026-10-05 16:36 (HANDOFF_20261005_LOBBY_REACHED.md).
**Window:** 2026-10-05 16:36 → 2026-10-08 (now).
**Area:** reference research (IW4X / third-party), resources & assets (IFS/FF/IWD/PAK), post-anchor
experiments not covered by lobby/market/booking/battle, tooling/infrastructure.

---

## 0. METHOD + SCOPE FINDING (read first)

Full recursive census of every file with LastWriteTime >= 2026-10-05 16:36, grouped by top-level component:

| component | post-anchor files |
|---|---:|
| REF_LOBBY_KIT | 33455 |
| DEV-PUBLISHER-RESTORE | 13691 |
| COD OL | 976 |
| GOLDEN-LOBBY-001 | 138 |
| DEV-BOOKING | 112 |
| _lb015 | 45 |
| run_codol_001 | 19 |
| _cleanout | 4 |
| CODOLServer | 1 (logs\elevated_agent.json, 10-08 18:00) |
| root | 6 |

**Hard finding:** these task-named directories contain ZERO files modified after the anchor:
IW4X\, OfflineServer\, restore003\, restore005\, restore006\, RESTORE_ENGINE_BRIDGE_002\,
RESTORE_LOCALRM_001\, restore_iips_contract_001\, restore_iips_contract_002\, ace_facade\,
_PLAINTEXT_PROJECT\, _dyn_stage1\, toolchain\, analysis_logs\.

They are documented below **only as REFERENCE / ARCHITECTURE RESEARCH / prerequisite dependencies**
(newest mtimes quoted), never as post-anchor CODOL feature work. Each is marked with the post-anchor
evidence (if any) that actually cites it. All mtimes are in the project's 2026 clock.

---

## 1. TIMELINE

| ID | time | work | purpose | action | result | follow-up |
|---|---|---|---|---|---|---|
| REF-01 | 2026-09-24 PRE | IW4X × CODOL reuse assessment | can IW4X seed the server? | static source review + PE hashes + one isolated -dedicated probe | same IW4 lineage, NOT ABI/protocol compatible; probe exit 0xC0000135 (missing iw4x.dll) | architecture baseline only |
| REF-02 | 2026-10-01…10-05 11:09 PRE | F: drive third-party kit | real reference implementation | C# lobby/battle server + 大厅 python kit on F:; snapshot copied locally | F: kit exists; local copy 10-01 23:06 | still declared "实际参考实现" post-anchor |
| REF-03 | 2026-10-07 19:0x POST | ol-mod unlock check | obtain booking source | search E:\handoff2, E:\ root, whole-machine depth-6 | NOT FOUND everywhere; BOOKING_SOURCE = BLOCKED | booking work stopped by instruction |
| REF-04 | 2026-10-07 19:13 POST | ACE / IW4X honesty status | prevent over-claiming | explicit counters in battle stage report | IW4X 直接引用 = 0; ACE_REMOVAL = NOT_COMPLETE; ACE facade 未使用 | — |
| ASSET-01 | 2026-09-30 PRE | .ff layer-1 decryption | open fastfiles | offline RSA-2048 + AES-192-CTR | 10/10 main\*.ff solved; RSA key == IW4X ZoneKey; layer 2 open | prerequisite for all asset work |
| ASSET-02 | 2026-10-05 18:33–18:36 POST | layer-2 static attack | crack common_marketplace_lite.ff layer 2 | _mkt_layer2_probe.py, _mkt_period_probe.py over _cleanout layer1.bin | ALL hypotheses REFUTED; period was small-sample noise | switch to runtime memory route |
| ASSET-03 | 2026-10-05 22:36–22:58 POST | extract full common_marketplace | authoritative item inventory | _extract_marketplace_assets.py over plaintext nifs packs | 34911 unique paths / 124929 entries / 18 packs | feeds callsign/SKU mapping |
| ASSET-04 | 2026-10-06 14:16–18:40 POST | IFS/FF scan tooling | find client-owned tables in packs | ~12 scripts | .ifs = partial plaintext (paths) + encrypted data; string search unreliable | corrected by MD5 scan |
| ASSET-05 | 2026-10-06 16:24–18:40 POST | MD5 full-scan of 974 .ifs | are the 6 tables inside any pack? | scan every zlib stream, compare MD5 | 1,469,394 candidates, 0/6 hits → tables in asset registry 0x239B120 | runtime route only |
| ASSET-06 | 2026-10-07 17:12 POST | codol_crypto.py (41.8 KB) | crypto for running kit | file added to REF_LOBBY_KIT | expanded derivative of F: kit crypto (10.4 KB, 10-02) | used by server/codec |
| ASSET-07 | 2026-10-08 20:32:23 POST | 974 .ifs rewritten | asset repair/download? | bulk in-place rewrite, one second | LWT=AT=20:32:23, CT preserved from 2026-09-10 00:15 | mechanism UNKNOWN |
| ASSET-08 | 2026-10-05 18:33–22:36 POST | _cleanout layer-1 dumps | inputs for layer-2 attack | 4 layer1.bin products | 3 marketplace zones dumped | KEPT |
| RE-01 | 2026-10-08 15:36–16:10 POST | _lb015 memory-dump RE | locate listener/net/booking paths | 45 throwaway scripts over mem_linear dump | no report/output retained | UNKNOWN |
| RE-02 | 2026-10-08 14:46 POST | _s1.py A/B writer scan | find writers of [reg+0x168/0x16c] | capstone scan of image_best.bin | script only | booking-adjacent |
| RUN-01 | 2026-10-07 20:00 → 10-08 20:32 POST | run_codol_001 sandbox runs | observe client/IIPS dynamically | ETW probe_dump.xml, BugTrace.log, TenioLog ×6, download.db | sandbox active; IIPS TPFUI images fail | sandbox-only evidence |
| FAIL-01 | 2026-10-05 22:10 POST | self-authored SKU page | fill empty market page | patched public tail with invented SKUs | broke the whole marketplace | ROLLED_BACK / REFUTED |
| TOOL-01 | ≤ 2026-10-05 15:36 PRE | CODOLServer\_mainline (802 files) | privileged experiment driver | agent_client.py + nt10.py etc. | newest 10-05 15:36 _cmp_auth_resp.py.done | USED post-anchor (anchor §3) |

---

## 2. WORK ITEMS

### REF-01 — IW4X reuse assessment (REFERENCE / ARCHITECTURE RESEARCH)

- **PROBLEM:** can the open-source IW4X client/server seed a CODOL server?
- **HYPOTHESIS:** CODOL and IW4X share enough IW4 lineage to reuse code/addresses.
- **ACTION (STATIC + one DYNAMIC probe):** compared IW4X source (IW4X\Client核心代码\iw4x-client) with CODOL
  binaries; hashed; ran isolated: iw4x.exe -dedicated -stdout -nointro +set sv_lanOnly 1 +set net_port 28960 +map mp_rust.
- **MODIFICATION:** none ("没有修改 E 盘文件").
- **OBSERVATION:** both x86/PE32, IW4 lineage. CODOL exe SHA-256 36997674…B537, Base.dll EF75220D…6A20,
  E:\IW4X\iw4x.exe 49EA90E3…7009. Probe exit 0xC0000135 (STATUS_DLL_NOT_FOUND) — E:\IW4X lacks iw4x.dll.
  G:\SteamLibrary MW2 iw4mp.exe is x64/PE32+ (FD3AFF1F…ABE2), incompatible generation.
- **RESULT:** IW4X reusable only as "服务器工程结构参考" (lifecycle/state model/OOB dispatch shape); addresses,
  commands and auth must NOT be copied.
- **EVIDENCE:** CODOLServer\IW4X_CODOL_REUSE_REPORT.md (lines 9–26, 61–91, 104–124, 177–207).
- **DISPOSITION:** KEPT (reference baseline).
- **IMPACT:** prevented inventing CODOL fields from IW4X names; IW4X later contributes exactly one artifact
  (the .ff RSA ZoneKey, ASSET-01), not code.

### REF-02 — F: drive third-party reference kit / reference-implementation dependence

- **PROBLEM:** official CODOL servers are dead; a working reference is required.
- **ACTION (STATIC inventory, external, read-only):**
  - F:\桌面\ol\大厅\ — HANDOFF.md, CODOL_LOBBY_WORKING_20261002.md, scripts\{nt10.py, nt8o.py, run_all.py,
    lobby_server.py, fake_auth_tls.py, codol_crypto.py, write_dwauth.py, patch_crossshell.py},
    certs\, data\, logs\{auth3074.log, lobby_srv.log, secrets.txt}, _frozen_manifest.txt.
  - F:\桌面\ol\新建文件夹\reference\ — the C# reference server: CodolLocalLobbyServer.cs (58.8 KB, 10-01 23:06),
    CodolLocalBattleServer.cs (28.9 KB, 10-02 01:19), CodolBattleKeyExchange.cs, CodolClientCommandReader.cs,
    CodolMotionSnapshot.cs, CodolStateReader.cs, CodolRangeEquipment.cs, plus JSON traces (playerstate-*,
    client-input-candidates-v19.json, config-assets.json).
  - F:\桌面\ol\CODOL_KDF_BREAKTHROUGH_20261003.md, CODOL_ROOM_MARKET_20261004(1).md,
    CODOL_MOVEMENT_PHYSICS_20261004.md (+zips), 新建文件夹\docs\.
  - F:\下载\ChatGPT-IW4X架构研习-20260916-2018.md (400 KB) — independent IW4X architecture study.
  - Newest F: kit content is 2026-10-04 (ol dir mtime 2026-10-05 11:09) = PRE-anchor external dependency.
- **OBSERVATION (post-anchor dependence):**
  - REF_LOBBY_KIT\_ref\CodolLocalLobbyServer.cs (10-01 23:06) and _ref\lsg.log (10-02 22:58) are local copies.
  - REF_LOBBY_KIT\STAGE_REPORT_BATTLE.md:180-184 (10-07 POST): "IW4X 直接引用 = 0 ... 实际参考实现 = 三方 C#
    (_ref\CodolLocalLobbyServer.cs) + ol-mod (不在本机)"; "不声称'当前 Server 基于 IW4X'".
  - REF_LOBBY_KIT\GOLDEN-LOBBY-001.md:180 (10-07 POST): ACE ABI/stub/mock backups exist at ace_facade\,
    _ace_backup_20261002\ but are "**未使用**".
  - CODOLServer\HANDOFF_20261005_SESSION_1347.md:418-434 (PRE, 10-05 13:47) lists the F: paths as "F: 盘
    （外部，只读参考）" — the citation tying the work to the F: kit.
- **RESULT:** post-anchor implementation depends on the F: C# reference and on ol-mod (absent); explicitly NOT on IW4X code.
- **DISPOSITION:** KEPT (external dependency). **IMPACT:** "server is based on IW4X" is REFUTED by the project itself.

### REF-03 — ol-mod / booking-source unlock check → BLOCKED

- **ACTION:** REF_LOBBY_KIT\STAGE_REPORT_BATTLE.md:188-206: E:\handoff2\ol-mod-olfinal.zip NOT FOUND;
  E:\handoff2\ NOT FOUND; whole-machine depth-6 search for Servers.cpp, DedicatedControl.*, sharedRoomClient.*,
  bookingDispatcher.*, playable_architecture.md, "Understand Project Repository.md", ol-mod*.zip over
  D:/E:/F:/G:/C:\Users → 0 hits.
- **RESULT:** BOOKING_SOURCE = BLOCKED; BOOKING_PROTOCOL = UNKNOWN; BATTLE_ENTRY = NOT_OBSERVED; experiments stopped.
- **EVIDENCE:** REF_LOBBY_KIT\STAGE_REPORT_BATTLE.md:188-219.
- **DISPOSITION:** ABANDONED by instruction.
- **NOTE (SOURCE_CONFLICT):** DEV-BOOKING\* docs (10-08) do continue booking experiments; the stop applied only
  to the battle stage-report branch.

### REF-04 — pre-anchor reference / restore / plaintext dirs with NO post-anchor activity

Read for content, dates and absence of post-anchor use. **REFERENCE / ARCHITECTURE RESEARCH**, pre-anchor.

| Dir | newest mtime | content | post-anchor use |
|---|---|---|---|
| OfflineServer\ | 2026-10-02 22:01 | one-click offline lobby (portproxy 443→8443/8444, CA append, probe+socket servers) | none |
| restore003\ | 2026-09-22 15:20 | RESTORE_ENGINE_BRIDGE_003_DECISION.md (553 lines): LOCALRM_LOAD=PASS, GETRM=FAIL, RM_VTABLE_CALLS=0, ROOT_BLOCKING_POINT = post-gate IIPS init contract | none |
| restore005\ | 2026-09-22 13:34 | PE dump, LocalRM v2 builder, load tests, out_*.txt | none |
| restore006\ | 2026-09-22 14:13 | LocalRM v3 builder + ABI audit + ledger | none |
| RESTORE_ENGINE_BRIDGE_002\ | 2026-09-21 19:25 | FINAL = all UNKNOWN / NOT_OBSERVED | none |
| RESTORE_LOCALRM_001\ | 2026-09-21 19:53 | LocalRM.cpp + ABI test; could not compile (no cl/gcc/clang) | none |
| restore_iips_contract_001\ | 2026-09-22 15:59 | 22 probes → 29 KB decision; incl. t18_ifs_dll_missing.py, t20_sandbox_ifs_probe.py | none |
| restore_iips_contract_002\ | 2026-09-22 21:54 | sandbox matrix, ACE-DRV32.dll, run_matrix.ps1; NO report | none |
| ace_facade\ | 2026-10-02 17:05 | build_facade.py + make_stub*.py — hand-built PE32 facade DLLs | cited POST as 未使用 (GOLDEN-LOBBY-001.md:180) |
| _PLAINTEXT_PROJECT\ | 2026-10-02 19:27 | README: L0/L1 .ff spec, L2 open, byte statistics; tools\codol_ff_decrypt.py | none direct; knowledge used by ASSET-02 |
| _dyn_stage1\ | 2026-09-18 17:11 | 277 files, ex027–ex059 dynamic observers/debuggers | none |
| toolchain\ | 2026-09-11 07:04 | only BIT2B1B.tmp (4.27 MB) | none; purpose UNKNOWN |
| analysis_logs\ | 2026-09-25 01:59 | TCLS/TenBase/TAS crypto dumps, launch baselines, handoff_recovery.md | none |

- **EVIDENCE:** the directories; OfflineServer\README.md; restore003\RESTORE_ENGINE_BRIDGE_003_DECISION.md:1-46;
  RESTORE_LOCALRM_001\RESTORE_LOCALRM_001_FINAL.md:13-61; RESTORE_LOCALRM_004_FINAL.md:1-23;
  RESTORE_ENGINE_BRIDGE_002\RESTORE_ENGINE_BRIDGE_002_FINAL.md; _PLAINTEXT_PROJECT\README.md;
  ace_facade\build_facade.py:1-15; analysis_logs\handoff_recovery.md:1-70.
- **DISPOSITION:** KEPT as reference; no post-anchor disposition.

### ASSET-01 — .ff layer-1 decryption (prerequisite, PRE)

- **PROBLEM:** COD OL\main\*.ff are encrypted; contents needed.
- **HYPOTHESIS:** IW4 DBIF format, key recoverable offline.
- **ACTION (STATIC + crypto):** extract the RSA private key; replicate PKCS#1 v1.5 + AES-CTR in Python.
- **OBSERVATION:** layout = XFileHeader (21 B; magic IWff0100; version 461) + 256 B RSA block + AES-CTR body.
  RSA private key (1191 B DER) byte-identical to IW4X FastFiles::ZoneKey; AES-192 key
  da135e91c7981459a13ddc2aed3050ae6dd9a7ce619bb6c5 unique repo-wide; CTR = whole-block little-endian increment.
- **RESULT:** 10/10 main\*.ff → IWffs100 container + zone name. Layer 2 REFUTED for zlib/deflate/gzip/lzma/bz2/LZ4/
  ECB/CBC/CFB/OFB/CTR-variants.
- **EVIDENCE:** CODOLServer\FF_LAYER1_DECRYPT_20260930.md:1-90+; CODOLServer\REVERSE_STATUS_20260930.md:8-49;
  _PLAINTEXT_PROJECT\README.md:9-107; tool CODOLServer\_mainline\ff_iw4_decrypt.py; products _cleanout\ff_layer1\.
- **DISPOSITION:** KEPT (most reused prerequisite).

### ASSET-02 — .ff layer-2 static attack (POST, REFUTED)

- **PROBLEM:** layer-2 body of common_marketplace_lite.ff opaque; SKU catalogue behind it.
- **HYPOTHESIS:** repeating XOR keystream (period ~0x1000) or zone-name-derived AES key.
- **ACTION (STATIC):** root\_mkt_layer2_probe.py (10-05 18:35) and root\_mkt_period_probe.py (10-05 18:36) over
  _cleanout\mkt\common_marketplace_lite.ff.layer1.bin (28.9 MB, 10-05 18:33).
- **MODIFICATION:** two root probe scripts only; no product touched.
- **OBSERVATION:** layer 1 confirmed (file 29,594,085 B; IV d499de7d14802404db93a5b886340000; zone
  common_marketplace_lite @0x12C). Layer 2: zlib/deflate/gzip all-offset = 0 hits; entropy 8.000; period scan
  P=256..8192 min Δ −0.009; 1 MB XOR@0x1000 = 7.9998; zone-name KDF = 0 hits; 0x40000-window XOR = 7.957;
  block entropy min 7.204 / avg 7.910.
- **RESULT:** all hypotheses REFUTED. The first probe's dist=0x1000 = 7.41 is recorded as **small-sample noise**
  (4 KB random expectation ≈ 7.7) — documented methodological pitfall.
- **EVIDENCE:** HANDOFF_20261005_LOBBY_BUGS.md:142-197 (§4.0.1/§4.0.2, caveat box 167–170);
  _mkt_layer2_probe.py; _mkt_period_probe.py (both root, POST).
- **DISPOSITION:** REFUTED (static route closed). **IMPACT:** mandated runtime memory route.

### ASSET-03 — full common_marketplace plaintext nifs extraction (POST)

- **HYPOTHESIS:** the repo always had the full common_marketplace packs, not just the 29 MB _lite.
- **ACTION (STATIC, read-only):** _extract_marketplace_assets.py (10-05 22:36) scans every *common_marketplace*.ifs
  under COD OL\IIPS\IIPSDownload and extracts main/… and mp/… path strings.
- **OBSERVATION (script docstring, POST 2026-10-05):** "主目录里一直有完整版 common_marketplace … 共 37 个包 /
  9.4 GB … 这些包是 nifs 明文容器(不是加密 ff)，头 0x200 之后就是 main/images/xxx_item_icon.iwi、main/models/...
  这类资源路径".
- **RESULT:** mkt_assets_summary.md — 34911 unique resource paths / 124929 raw entries / 18 source packs; category
  breakdown (名片背景 1205, 头像图标 441, 称号 1, …); per-pack table (largest lf_init_common_marketplace_1_V49.1.ifs = 7150).
- **EVIDENCE:** REF_LOBBY_KIT\_extract_marketplace_assets.py:1-13; REF_LOBBY_KIT\mkt_assets\mkt_assets_summary.md:1-201
  (duplicated under DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\mkt_assets\).
- **DISPOSITION:** KEPT. **IMPACT:** byte-grounded inventory of displayable assets; feeds callsign/SKU mapping.

### ASSET-04 — IFS/FF scan tooling (POST; TOOLING)

- **ACTION (STATIC, ~12 POST scripts):** _find_ff_and_tables.py (14:16), _find_common_mp.py (14:17),
  _check_ifs_magic.py (14:17), _scan_common_mp.py, _find_callsign_tables_all.py, _scan_all_ifs_csv.py (16:24),
  _search_ifs_for_content.py (17:11), _check_ff_files.py (18:22), _find_asset_table.py, _dig_asset_table.py,
  _validate_string_method.py (18:06).
- **OBSERVATION (method self-check):** on lf_init_common_marketplace_1_V49.ifs (594 MB): main/images 4215×, iwi
  4248×, but pcb_amorphous01 0×, callsignNameplate 0×, codo.objects 0×. ⇒ .ifs = partially plaintext (resource-path
  table) + encrypted asset data; "string not found" does NOT prove absence.
- **RESULT:** earlier "0 hits" string searches were methodologically insufficient; corrected by MD5 scan (ASSET-05).
- **EVIDENCE:** the scripts; REF_LOBBY_KIT\HANDOFF_20261006_MARKET_MANIFEST.md:94-149.
- **DISPOSITION:** KEPT (tooling); partial REFUTATION of the prior method.

### ASSET-05 — MD5 full scan of all 974 .ifs (POST; decisive negative)

- **HYPOTHESIS:** the 6 client market tables live (zlib-compressed) inside the .ifs packs.
- **ACTION:** take 6 MD5s from mp/marketplace.json; scan every legal zlib stream in all 974 packs; compare digests.
- **RESULT:** 974 packs, 1,469,394 zlib candidates, **0/6 hits** → tables are NOT in any .ifs compressed stream.
- **Follow-on (STATIC):** entry point is the client asset registry at 0x239B120 (stride 0x1C, +0x00 type code, some
  paths require == 0xC), companion tables 0x1E2D338 / 0xE5C8C0; a disk probe mp/marketplace.json was ineffective.
  Method error corrected: 0x239B120 is an RVA, not a file offset; it maps into Base.dll .tvm0 (shell-virtualized).
- **EVIDENCE:** REF_LOBBY_KIT\HANDOFF_20261006_MARKET_MANIFEST.md:94-205; cross-ref per that doc:
  CODOLServer\SESSION_APPEND_20260929_STAGE3_SUCCESS.md.
- **DISPOSITION:** KEPT (negative result). **IMPACT:** file/IFS-based table recovery abandoned.

### ASSET-06 — codol_crypto.py (POST; TOOLING/port)

- Observed at REF_LOBBY_KIT\codol_crypto.py (10-07 17:12, 41.8 KB), mirrored in DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\
  and GOLDEN-LOBBY-001\REF_LOBBY_KIT\.
- The F: kit already has F:\桌面\ol\大厅\scripts\codol_crypto.py (10-02 16:35, 10.4 KB) and
  F:\桌面\ol\新建文件夹\scripts\codol_crypto.py (10-04) → the post-anchor 41.8 KB file is an expanded local
  derivative, not a new algorithm.
- **EVIDENCE:** REF_LOBBY_KIT\codol_crypto.py; F:\桌面\ol\大厅\scripts\codol_crypto.py.
- **DISPOSITION:** KEPT. Crypto core ownership is the F: kit (REFERENCE), extended locally.

### ASSET-07 — 974 .ifs bulk rewrite at 2026-10-08 20:32:23 (POST, DYNAMIC; cause UNKNOWN)

- **OBSERVATION (filesystem, DYNAMIC):** all 974 .ifs in COD OL\IIPS\IIPSDownload have LastWriteTime =
  LastAccessTime = 2026-10-08 20:32:23, while CreationTime is preserved from install (2026-09-10 00:15:0x).
  readme.txt (2026-09-10) is the only non-.ifs file: "Cleared out IFS files to be downloaded by IIPS should be put
  here by the build process." No hardlinks/reparse points (LinkType empty).
- **CORRELATED DYNAMIC EVIDENCE:** sandbox IIPS wrote
  run_codol_001\sandbox_ifs1_ctl_iips1_20260927\IIPS\vodcache\download.db at 2026-10-08 20:32:23 (SQLite, table
  old_items(key,tii,tdi), 0 rows), and emitted six TenioLog files that day (18:12:05, 20:08:29, 20:14:31, 20:21:36,
  20:24:41, 20:25:28). The 20:25:28 log is entirely "LoadImage LoadImageFromBuffer failed" for TPFUI PNGs under
  run_codol_001\sandbox_datafix_20260929\IIPS\TPFUI\IIPSRes\... (Chinese UI paths).
- **HYPOTHESES (unresolved):** (a) in-place IIPS repair/verify-all rewrite; (b) bulk restore/copy into the real
  install; (c) timestamp touch. CT preservation fits in-place rewrite but does not prove it.
- **RESULT:** 974 content packs (≈23.8 GB per REVERSE_STATUS_20260930.md:23-24: "974 个内容包 / 23.8 GB，其中 695 个
  内嵌 IWff") all (re)written in one second while IIPS sandboxes were active.
- **EVIDENCE:** COD OL\IIPS\IIPSDownload\* (LWT/CT/AT); readme.txt; run_codol_001\...\TenioLog\20261008_*.log;
  run_codol_001\...\vodcache\download.db; CODOLServer\REVERSE_STATUS_20260930.md:23-24.
- **DISPOSITION:** UNKNOWN (observation KEPT; cause not established).
- **IMPACT:** if (a), the IIPS asset pipeline is functional post-anchor over ~23.8 GB. Do not claim verification
  without a log naming the files.

### ASSET-08 — _cleanout layer-1 dumps (POST)

| file | size | LWT |
|---|---|---|
| _cleanout\mkt\common_marketplace_lite.ff.layer1.bin | 28.9 MB | 10-05 18:33 |
| _cleanout\mkt1\common_marketplace_lite1.ff.layer1.bin | 3.36 MB | 10-05 21:31 |
| _cleanout\mktloc\localized_common_marketplace_lite.ff.layer1.bin | 64.8 KB | 10-05 21:31 |
| _cleanout\mktfull\ff_init_common_marketplace_V95.ifs.layer1.bin | 32.3 MB | 10-05 22:36 |

The three marketplace zones are exactly the three the pre-anchor mount audit flagged as absent from the startup
zone set (RESOURCE_MOUNT_AUDIT_20260929.md:60-66) — the gap still mattered post-anchor. Other _cleanout\*.py
(≈180 files) are all 2026-09-30 (PRE).
- **EVIDENCE:** the four .layer1.bin files; CODOLServer\RESOURCE_MOUNT_AUDIT_20260929.md:28-87.
- **DISPOSITION:** KEPT (scratch inputs to ASSET-02).

### RE-01 — _lb015 post-anchor reverse engineering (POST)

- **ACTION (STATIC/DYNAMIC scratch):** 45 files created 2026-10-08 15:36–16:10: memmap.py, cmp1.py, img.py,
  p_632680.py, p_vt.py, p_refs.py, p_ctor.py, p_callers.py, p_ctorcaller.py, p_glob.py, p_imp.py, p_slots.py,
  scan1-4.py, pe.py, vtfind.py, vtfind2.py, s5.py, mem.py, a1.py, fast.py, b1–b14.py, c1.py, c2.py.
- **OBSERVATION:** _lb015\mem.py:2-10 declares its source as the fresh full linear memory dump
  REF_LOBBY_KIT\mem_linear_20261007_134406 (regions r_XXXXXXXX_YYYY.bin); b10.py disassembles 0x7CAF30
  ("listener E69CB0 +0x24"); c2.py scans the PE for "call dword [0xCA7000..0xCB2000]" IAT slots and resolves them
  against the dump; scan1.py searches dword 0x82E13FC with a +4 memory operand.
- **RESULT:** no report and no captured output in _lb015; results UNKNOWN.
- **DISPOSITION:** UNKNOWN (artifacts kept). **IMPACT:** mem_linear_20261007_134406 (produced 10-07 by
  REF_LOBBY_KIT\_dump_mem_linear.py, 10-06 19:03) is a shared post-anchor RE resource.

### RE-02 — _s1.py A/B field writer scan (POST)

- **ACTION (STATIC):** root _s1.py (10-08 14:46) loads
  CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin and searches for writes to [reg+0x168] /
  [reg+0x16c] in module 0x620000–0x63A000.
- **RESULT:** script only; no output artifact.
- **RELATION:** these are the A/B fields of the PVE booking/matching work (DEV-BOOKING\PVE-MATCHING-AB-FIELD-IDENTITY-018.md,
  PVE-MATCHING-AB-ALIGN-019.md, 10-08 18:55/20:26) — booking-adjacent static support, recorded so it is not lost.
- **DISPOSITION:** UNKNOWN.

### RUN-01 — run_codol_001 post-anchor sandbox activity (DYNAMIC)

19 post-anchor files:
- probe_dump.xml (3.1 MB, 10-07 20:00) — ETW event XML, first TimeCreated 2026-10-07T19:58:21.
- sandbox_datafix_20260929\BugTrace.log (503.5 KB, 10-08 18:02) — ACE BugTrace still active.
- sandbox_datafix_20260929\cacert.pem (354 KB, 10-08 20:21).
- sandbox_datafix_20260929\ACE-DRV32.dll (6.7 MB, 20:25), tcj.dll.bh (4.2 MB, 20:25).
- sandbox_datafix_20260929\players\config_mp.cfg (7.7 KB, 20:26), _co.tlg (0.3 KB, 20:30) — client wrote config.
- sandbox_datafix_20260929\TenproxyLog\20261008_180217.log (0 B).
- sandbox_ifs1_ctl_iips1_20260927\IIPS\IIPSClient.ini (1.9 KB, 18:11), TenioLog ×6 (18:12–20:25),
  vodcache\download.db (20:32), Progress.ini (0 B, 20:32).
- **OBSERVATION:** sandbox ran repeatedly through 10-08 20:32; IIPS repeatedly fails to load its own TPFUI images;
  ACE BugTrace still writing.
- **DISPOSITION:** KEPT (raw evidence). **IMPACT:** only post-anchor IIPS-side dynamic artifacts in my area.

### TOOL-01 — CODOLServer\_mainline privileged driver (PRE, used POST)

- 802 files; newest 2026-10-05 15:36 (_cmp_auth_resp.py.done) → directory NOT modified after the anchor, but is a
  post-anchor dependency: HANDOFF_20261005_LOBBY_REACHED.md:122-130 (post-anchor reproduction) requires
  CODOLServer\_mainline\agent_client.py; HANDOFF_20261005_LOBBY_BUGS.md:199-214 requires agent_client.py + nt10.py
  for the runtime memory route.
- **EVIDENCE:** CODOLServer\_mainline\ (802 files, newest 10-05 15:36); the two handoffs above.
- **DISPOSITION:** KEPT. **IMPACT:** sole channel for post-anchor dynamic work.

### TOOL-02 — DEV-PUBLISHER-RESTORE mirror (POST; TOOLING)

- Created 10-08 09:22; 13691 post-anchor files; contains exactly popup\ and a full copy of REF_LOBBY_KIT\.
  A dev copy created after the Golden freeze (GOLDEN-LOBBY-001.md:205-208 mandates experiments in a dev copy); it
  duplicates asset tooling (e.g. DEV-PUBLISHER-RESTORE\REF_LOBBY_KIT\mkt_assets\).
- **DISPOSITION:** KEPT (infrastructure). **IMPACT:** post-10-08 asset work may live here, not in the Golden.

### TOOL-03 — observer / experiment directory inventory (mostly PRE)

_dyn_stage1 (277, 09-18), _pml_analyze (27, 09-19), _ebo1_observer (19, 09-21), _core009/_core011/_core013p
(2 each), _ich015…_ich048_observer (1–4 each, 09-21), _ord1_observer, _restore001_observer, _observer_broken_snapshot
(3, 10-02). CODOLServer\ has ≈120 _*run* / _sniff_* / _liveplat_* / _aeskey_* dirs (09-25), plus _lobbyprobe1,
_localconn*, _subagents/subagents, _static_reports*, _ui_ff, _fullimage, _gdptest, _keyderive, _runtime_aes, _stubs.
No post-anchor activity. Root holds 617 .py scripts; only _mkt_layer2_probe.py, _mkt_period_probe.py and _s1.py are POST.
- **DISPOSITION:** KEPT as historical tooling; PRE, no post-anchor use found.

### FAIL-01 — invented SKU page broke the marketplace (POST, ROLLED_BACK)

- HANDOFF_20261005_LOBBY_BUGS.md §8 "★★ 失败记录：自编 SKU 页把整个 marketplace 打挂（2026-10-05 22:10）";
  REF_LOBBY_KIT\_rollback_state.py and _revert_to_trusted_catalog.py (10-06 15:19/15:24) reverted to a trusted catalogue.
- **EVIDENCE:** HANDOFF_20261005_LOBBY_BUGS.md:303-341; the two scripts.
- **DISPOSITION:** ROLLED_BACK / REFUTED. Recorded even though the subject is market.

---

## 3. EVIDENCE FILE PATHS RELIED ON

**Post-anchor (primary):**
- HANDOFF_20261005_LOBBY_BUGS.md (root, 10-05 22:17) §4.0.1/4.0.2/4.0.3, §8
- _mkt_layer2_probe.py, _mkt_period_probe.py, _s1.py (root, POST)
- _cleanout\mkt\common_marketplace_lite.ff.layer1.bin; _cleanout\mkt1\...; _cleanout\mktloc\...;
  _cleanout\mktfull\ff_init_common_marketplace_V95.ifs.layer1.bin
- REF_LOBBY_KIT\_extract_marketplace_assets.py; _check_ifs_magic.py; _scan_all_ifs_csv.py; _search_ifs_for_content.py;
  _find_ff_and_tables.py; _check_ff_files.py; _validate_string_method.py; codol_crypto.py
- REF_LOBBY_KIT\mkt_assets\mkt_assets_summary.md
- REF_LOBBY_KIT\HANDOFF_20261006_MARKET_MANIFEST.md (94–205)
- REF_LOBBY_KIT\STAGE_REPORT_BATTLE.md (175–219)
- REF_LOBBY_KIT\GOLDEN-LOBBY-001.md (150–211)
- REF_LOBBY_KIT\_ref\CodolLocalLobbyServer.cs; _ref\lsg.log
- COD OL\IIPS\IIPSDownload\* (974 .ifs + readme.txt)
- run_codol_001\sandbox_ifs1_ctl_iips1_20260927\IIPS\TenioLog\20261008_*.log (×6)
- run_codol_001\sandbox_ifs1_ctl_iips1_20260927\IIPS\vodcache\download.db
- run_codol_001\sandbox_ifs1_ctl_iips1_20260927\IIPS\IIPSClient.ini
- run_codol_001\sandbox_datafix_20260929\{BugTrace.log, cacert.pem, ACE-DRV32.dll, tcj.dll.bh,
  players\config_mp.cfg, _co.tlg, TenproxyLog\20261008_180217.log}
- run_codol_001\probe_dump.xml
- _lb015\*.py (45 files)
- HANDOFF_20261005_LOBBY_REACHED.md (anchor; §3 reproduction, §2.5 correction)
- CODOLServer\logs\elevated_agent.json

**Pre-anchor prerequisites cited:**
- CODOLServer\IW4X_CODOL_REUSE_REPORT.md
- CODOLServer\IIPS_ROOT_CAUSE.md
- CODOLServer\FF_LAYER1_DECRYPT_20260930.md
- CODOLServer\REVERSE_STATUS_20260930.md
- CODOLServer\RESOURCE_MOUNT_AUDIT_20260929.md
- CODOLServer\HANDOFF_20261005_SESSION_1347.md (418–434)
- CODOL_PROJECT_NODE_ANALYSIS.md (10-04; node map L0–L9, 172 nodes)
- _PLAINTEXT_PROJECT\README.md
- OfflineServer\README.md; restore003\RESTORE_ENGINE_BRIDGE_003_DECISION.md;
  RESTORE_ENGINE_BRIDGE_002\RESTORE_ENGINE_BRIDGE_002_FINAL.md; RESTORE_LOCALRM_001\RESTORE_LOCALRM_001_FINAL.md;
  RESTORE_LOCALRM_004_FINAL.md; ace_facade\build_facade.py; analysis_logs\handoff_recovery.md
- External: F:\桌面\ol\大厅\{HANDOFF.md, scripts\*, certs\*, data\*, logs\*};
  F:\桌面\ol\新建文件夹\reference\Codol*.cs; F:\桌面\ol\CODOL_KDF_BREAKTHROUGH_20261003.md;
  F:\下载\ChatGPT-IW4X架构研习-20260916-2018.md; E:\IW4X\; E:\CODOL_SANDBOX\

---

## 4. SOURCE_CONFLICT

1. **IW4X dependence, contradictory framing.**
   - REF_LOBBY_KIT\STAGE_REPORT_BATTLE.md:180-184 (10-07): IW4X 直接引用 = 0; "不声称当前 Server 基于 IW4X".
   - CODOLServer\FF_LAYER1_DECRYPT_20260930.md:5,61-81 and _PLAINTEXT_PROJECT\README.md:69-74: the .ff RSA key is
     byte-identical to IW4X FastFiles::ZoneKey and WAS used to solve the fastfiles.
   - Compatible (crypto artifact vs server code) but reads as contradiction. **Keep both.**
2. **RESTORE_ENGINE_BRIDGE_002 vs 003.**
   - 002_FINAL.md: everything UNKNOWN / NOT_OBSERVED.
   - restore003\...003_DECISION.md:5-30: STATUS=COMPLETE, LOCALRM_LOAD=PASS, ENGINE_GATE=PASS, GETRM=FAIL.
   - Later supersedes earlier. **Keep both.**
3. **LocalRM buildability.**
   - RESTORE_LOCALRM_001_FINAL.md:13-17,57-61: no compiler, DLL not built, ABI mostly UNKNOWN.
   - RESTORE_LOCALRM_004_FINAL.md:2-23: PE32_BUILDER=YES, LocalRM.dll built, GETPROCADDRESS_TEST=PASS,
     LOADLIBRARY_TEST=FAIL; root also has LocalRM.dll (09-21), LocalRM_v2.dll, LocalRM_v3.dll (09-22).
   - 001 was REPLACED by 004+ artifacts. **Keep both.**
4. **IIPS [100] root cause vs later resolution.**
   - CODOLServer\IIPS_ROOT_CAUSE.md:27-59 (09-25): IIPSHostApp never initialises; empty HostPid; zero IIPS/Tenio pipes;
     [100] is local pipeline failure, not network.
   - CODOLServer\HANDOFF_20260927_IIPS_GATE_RESOLVED.md (09-27, filename claim) plus the 10-05 lobby entry imply the
     IIPS gate was passed. Whether the host was FIXED or BYPASSED is unresolved. **Keep both.**
5. **Layer-2 "weakness" signal.**
   - _mkt_period_probe.py:4-5 docstring: dist=0x1000 XOR 熵 = 7.41, 明显低于随机期望 (suggests a period).
   - HANDOFF_20261005_LOBBY_BUGS.md:161-170: that 7.41 is small-sample bias; 64 KB → 7.999, 1 MB → 7.9998; no period.
   - Resolved in-document (hypothesis→refutation). **Keep both.**
6. **974 .ifs rewrite vs IIPS download DB.**
   - COD OL\IIPS\IIPSDownload\*.ifs all LWT = 2026-10-08 20:32:23.
   - COD OL\IIPS\vodcache\download.db is still 2026-09-28 10:55 (no download record in the real install).
   - Sandbox DB written at 20:32:23 but empty. Mechanism conflict. **Keep both; cause UNKNOWN.**
7. **Within the anchor document (self-correction, recorded for completeness).**
   - HANDOFF_20261005_LOBBY_REACHED.md §1.1 first frames the reconnect HMAC=BAD as a handshake key race; §2.5
     explicitly corrects it: "早先把它写成'握手密钥竞态残留'是错的 … BAD 是结果，不是原因". **Keep both sections.**

---

## 5. UNKNOWN

- UNKNOWN-1: mechanism of the 974 .ifs rewrite at 2026-10-08 20:32:23 (in-place IIPS repair vs bulk copy vs
  timestamp touch). No log names the files.
- UNKNOWN-2: _lb015 results — no report, no captured stdout.
- UNKNOWN-3: _s1.py results — no captured output.
- UNKNOWN-4: whether the IIPS TPFUI LoadImage failures (10-08 20:25:28) affect only the sandbox or also the real
  COD OL\IIPS\TPFUI (log paths point at sandbox_datafix_20260929).
- UNKNOWN-5: outcome of restore_iips_contract_002 — only run_matrix.ps1 + a DLL, no decision report.
- UNKNOWN-6: purpose of toolchain\BIT2B1B.tmp (2026-09-11, 4.27 MB) — no referencing file found.
- UNKNOWN-7: whether post-anchor work ever executed _PLAINTEXT_PROJECT\tools\codol_ff_decrypt.py (no post-anchor file
  references it; only its knowledge is reused).
- UNKNOWN-8: post-anchor dependence on _dyn_stage1, analysis_logs, restore003/005/006, RESTORE_LOCALRM_001,
  restore_iips_contract_*, OfflineServer — none is referenced by any post-anchor file.
- UNKNOWN-9: root file $null (0 B, 10-06 18:40) — accidental shell artifact.

*End of report.*
