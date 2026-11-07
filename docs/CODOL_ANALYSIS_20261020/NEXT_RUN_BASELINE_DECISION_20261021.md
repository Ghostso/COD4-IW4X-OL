# Next-run baseline decision (2026-10-21)

Status: **START BLOCKED / baseline source identified / migration not yet authorized**

## Facts

1. `REF_LOBBY_KIT\marketplace_store.py` is 50,022 B while `_golden_hashes.json` expects 46,226 B. The current protected set is therefore 8/9.
2. `CODOL_VERIFIED_GOLDEN_20261019\marketplace_store.py` has the same 50,022 B conflict.
3. `REF_LOBBY_KIT_CAP009\marketplace_store.py` matches the golden file, but CAP009 is only 7/9 overall (`lobby_server.py` differs and `make_local_ca.ps1` is missing).
4. `GOLDEN-LOBBY-001\REF_LOBBY_KIT` matches all 9 protected files byte-for-byte. A recursive copy into `run_codol_001\runs\BASELINE_SOURCE_AUDIT_20261021_1430\REF_LOBBY_KIT` also matches 9/9.
5. That golden source is not a clean runtime directory: it contains 208 top-level files including old logs, certificates, session files, `tas_off.flag`, `poke_off.flag`, `firingrange-battle.enabled`, `firingrange-session.enabled` and many prior probe outputs.
6. The original `run_all.py` hard-codes `GAME_ROOT = D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929`; it also defaults to `--retries 6`, so it can relaunch a client several times in one invocation.
7. Those behaviors conflict with the single-shot and isolated-run rules. They cannot be fixed by silently editing `REF_LOBBY_KIT` or `CODOL_VERIFIED_GOLDEN_20261019`.

## Blocking decisions

| ID | Decision needed | Recommended handling | Why start is currently blocked |
|---|---|---|---|
| B-01 | Which baseline is authoritative? | Treat `GOLDEN-LOBBY-001\REF_LOBBY_KIT` as the source only after an explicit baseline-migration decision. Do not replace the current `REF_LOBBY_KIT`. | The current kit is 8/9; replacing or repairing it is a baseline mutation. |
| B-02 | How to isolate mutable state? | Copy the protected files verbatim into a fresh run directory, then remove only run-time residue from that copy before launch. Record hashes before and after cleanup. | The chosen source contains old certificates, logs, flags and probe outputs that can alter behavior or contaminate evidence. |
| B-03 | How to enforce one client launch? | Do not use the original default retry behavior. Use `--retries 1` or an explicitly reviewed one-shot runner in the new run directory. If the client exits early, stop and open a new run; do not relaunch. | `run_all.py` defaults to six attempts and is not a single-shot contract. |
| B-04 | How to prevent shared sandbox state? | Do not point two runs at the same mutable sandbox. Either use a run-local sandbox/game working set or obtain explicit approval to reuse the declared shared `GAME_ROOT` after proving it is unchanged. | A shared sandbox violates run isolation and makes evidence attribution ambiguous. |

## Clean-copy checklist for the next run

1. Create a new `run_codol_001\runs\<RUN_ID>` directory.
2. Copy the 9 protected files from the accepted source verbatim; do not edit their contents.
3. Remove only known runtime residue from the copy (logs, certificates, session/key files, flags, probe outputs, caches).
4. Recompute the 9 protected hashes and require 9/9 against `_golden_hashes.json`; also require `run_all.py` SHA-256 `2AAA8847...6ECDA6`.
5. Prove `dumpcap_live` is running before starting any client.
6. Start one client only, with no automatic retry; record client creation time and PID.
7. Keep the same PID through Auth/TLS, Lobby and Battle.
8. Capture bidirectional application payloads, gamestate/configstrings, at least two snapshots, game-level ACKs and consumer trace.
9. Prove one live readable image page before any full-page sweep; `299` means `BLOCKED_AFTER_ACE`, not partial coverage.
10. Export layer-2 CLIPMAP_MP, MAP_ENTS, ComWorld and physics/XModel collision with hashes and references.
11. Keep raw capture only in run-local quarantine; publish a strictly filtered/redacted game-only package.

## Current evidence

- Baseline audit: `run_codol_001\runs\BASELINE_SOURCE_AUDIT_20261021_1430\BASELINE_SOURCE_AUDIT.json`
- Baseline copy integrity: `run_codol_001\runs\BASELINE_SOURCE_AUDIT_20261021_1430\baseline_copy_integrity.json`
- Current blocker status: `CODOL_ANALYSIS_20261020\THIRD_ROUND_BLOCKER_STATUS_20261021.json`
- Current intake audit: `CODOL_ANALYSIS_20261020\COLLECT_319_20261021_132905_INTAKE_AUDIT.md`
- Prerequisites: `CODOL_ANALYSIS_20261020\THIRD_ROUND_PREREQUISITES.md`

## Decision

No new client launch is authorized by this document. P0 remains `0/11`; wire-protocol and playability comparison remain `BLOCKED`. The next action is to approve or reject the baseline-migration and run-isolation choices above, then prepare a fresh run with the pre-launch capture proof.
