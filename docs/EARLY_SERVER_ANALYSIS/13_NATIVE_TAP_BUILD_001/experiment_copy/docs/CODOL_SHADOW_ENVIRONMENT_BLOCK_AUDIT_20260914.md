# Shadow audit: remaining replicated environment channel

Status: initial channel audit, superseded by `CODOL_REPLICATED_DVAR_COLLISION_20260914.md`. The subsequent passive capture proved a separate legacy128-slot publisher corrupts C1's200-slot pairing. No direct dark-region cause established. No process/UI changes, builds or tests.

## Replicated dvar block differs from reliable s commands

C1 dispatcher0x46740a..0x467419 routes configstrings24..423 to0x466020. This is independent of the already-reviewed `s name value` command handler. The consumer walks names24..223 paired with values224..423 and stops at the first empty name. At0x46605e..0x466087 it resolves both strings and invokes generic setter0x625330; an optional client-mode transformation0x72f9d0 occurs first. Therefore checking only logged `s` commands did not exhaust server-fed dvar input.

The native producer `CODOL_RefreshServerDvars` preserves inherited name ordering, finds each corresponding native dvar and publishes a changed value only when that dvar has CVAR_SYSTEMINFO. The names originate in the mounted `mp/constConfigStrings_mp.csv` for MP (`src/sv_main.c:5216`), not a newly invented server list. The pairing offset200 and empty-name termination agree with C1. `CODOL_SetReplicatedDvars` also clears unused names explicitly, preventing stale inherited tail entries from remaining active.

## Actual traffic requiring name resolution

The current qconsole contains value-block updates `d 253 250`, `d 254 1`, `d 255 1`, `d 256 1`. Their paired name slots are53,54,55,56 respectively. This audit did not resolve those four inherited names, so they must not be called shadow, near-plane or lighting overrides on the basis of the numeric slots.

The next distinct passive comparison is the complete active name/value block24..423 against mounted constant rows and the native dvars that changed it. Resolve every observed changed value through its paired name before assigning renderer relevance. Any difference then has a concrete producer (`Cvar_FindVar` plus CVAR_SYSTEMINFO selection), unlike speculative cascade-bias changes.

No further direct map/environment configstring consumer linked to the reported patch was established from the dispatcher. That is a bounded finding, not proof that no additional rendering inputs exist. This channel remains a more concrete next check than repeating brush transforms or already-disabled sun overrides.
