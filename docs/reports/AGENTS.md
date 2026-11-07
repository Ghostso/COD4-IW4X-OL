# CODOL Frozen Launch Chain

## Reference authority hierarchy (MANDATORY)

Every technical judgement must follow this credibility order, highest first:

1. **Local reverse engineering** — bytes captured from the real client, data unpacked
   from the shipped game files. Irrefutable; overrides every other source on conflict.
   Examples: `RX_BODY`, `TX_SNAP_HEX`, `keymap_cal.csv`, `common_mp.ff` unpack products,
   `_map_extract\*_zone.bin`.
2. **IW4X** — authoritative implementation reference.
3. **CoD4X** — authoritative implementation reference, ranked **below IW4X**.
   Where the two disagree, follow IW4X.
4. **Any other external project** — value unverified, lowest credibility.

### ol-mod is NOT authoritative

- ol-mod does **not** meet the bar for primary study. It is usable only as a
  "similar game of the same family" cross-reference.
- Never copy its constants, field layouts, or protocol values into our implementation.
  Its own header states it targets a different build: `net_chan_mp.hpp` —
  "3.3.3.3 ends a server message with 6; **OLfinal** ends it with 5".
- The C battle server's architecture already derives from IW4X + CoD4X
  (source references: CoD4x 16, IW4 14, IW4X 7, ol-mod 3). Do not conflate
  "the server's architecture lineage" with "which reference I reach for in a detail".

Before citing any reference, first confirm it targets this build (3.19 / build 1649370).

## Reverse engineering is the primary method — do not ask permission

Reverse engineering (decompiling, unpacking, byte analysis, memory dumps, protocol
reverse engineering, asset extraction) is this project's **main working method**.
Perform it directly. Do not interrupt work to ask "shall I dig further / may I start
reversing X" — just do it and report results.

Approval is still required only for actions with side effects: deleting or overwriting
files, launching the game client, modifying protected assets, or pushing changes.

### Restoring a large game = many independent function-sized tasks

> **大型游戏复原可以拆成大量独立函数任务，再通过依赖关系和严格验证机制持续推进。**
> (GPT-6A)

Corollary, binding on this project:

- **Never say "this needs runtime observation / a sample we don't have" as a stopping point.**
  Decompose the question into function-sized sub-tasks and keep going statically.
  "Needs runtime" is only valid after the static decomposition is *itself* exhausted and
  the exhaustion is written down (what was tried, what each attempt ruled out).
- Every open item must be expressed as a concrete, independently checkable task
  (address / byte range / call edge), not as a topic ("member record semantics").
- Progress is maintained by the **dependency graph + strict verification**, not by
  hoping a sample shows up: each closed task must cite reproducible evidence.

## Protected launch assets

The following are immutable inputs unless the user explicitly requests a baseline migration:

- REF_LOBBY_KIT\run_all.py
- REF_LOBBY_KIT\nt10.py
- REF_LOBBY_KIT\lobby_server.py
- REF_LOBBY_KIT\fake_auth_tls.py
- REF_LOBBY_KIT\codol_crypto.py
- REF_LOBBY_KIT\write_dwauth.py
- REF_LOBBY_KIT\make_local_ca.ps1
- REF_LOBBY_KIT\_golden_hashes.json
- Everything named by REF_LOBBY_KIT\_golden_hashes.json
- CODOL_VERIFIED_GOLDEN_20261019 as a whole

Do not edit, overwrite, rename, delete, generate certificates into, or write runtime state into these paths.

## Required way to run experiments

Use run_codol_001\run_frozen_chain_once.py or create a new run-specific working directory. Copy the frozen files there before modifying behavior. Runtime artifacts, logs, snapshots, flags, certificates, generated configs, and user data must stay under run_codol_001\runs\<RUN_ID>\.

## Single-shot rule

One invocation may create only one game client. Do not automatically relaunch the client after an early exit. Retry only when the user explicitly requests it and only in a new isolated run directory.

## Baseline integrity

Before and after every run, hash the protected files and record the result in the run directory. A changed protected hash means the chain was modified and the run is invalid. Do not repair by rebuilding the full game tree; restore the named source from its manifest and move the experiment to a fresh run directory.

## Experiments

Each independent change needs its own run directory and manifest. Never point two projects at the same mutable kit or sandbox. Never change IIPS, hosts, certificates, registry policy, security software, or game binaries as an incidental fix.

## Verification

A run is successful only with timestamped evidence for IIPS, Auth, Lobby, the same client PID, and the declared success threshold. Keep all evidence in the run directory.
