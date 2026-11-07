# CODOL Frozen Launch Chain

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
