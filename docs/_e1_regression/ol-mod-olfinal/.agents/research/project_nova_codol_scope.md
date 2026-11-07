# Project Nova distribution and CODOL scope

> Status: archived-distribution evidence and scope criteria. Binary sizes and coverage figures are observations from the recorded reconstruction snapshot, not the current build manifest or roadmap.

This note records the evidence that the archived Ayria package is a Project
Nova multi-game distribution. It also defines the boundary for reconstructing
CODOL behavior without cloning every game supported by the generic plugin.

## Distribution evidence

The Advanced Warfare launcher ships this Ayria tree:

- `Bootstrapper32.dll` and `Bootstrapper64.dll`
- `Injector32.exe` and `Injector64.exe`
- `Alwaysoffline.Localnet32` and `Alwaysoffline.Localnet64`
- `Localnetworking.Ayria32` and `Localnetworking.Ayria64`
- `Platformwrapper.Ayria32` and `Platformwrapper.Ayria64`
- per-title assets under `Assets/Alwaysoffline/<titleId>`

Its `Form1.cs` selects the same injector family for MW3, Ghosts, Advanced
Warfare, Black Ops, Black Ops 2, Modern Warfare Remastered and Blur. It maps
each detected executable to an architecture and an Ayria title directory. Its
cleanup command removes every other title directory and the unused
architecture, which directly confirms that the original package is a shared
multi-title distribution rather than a CODOL-only build.

The archived 32-bit backend in the Advanced Warfare distribution is byte-for-
byte identical to the CODOL-era copies:

| Distribution | Size | SHA-256 |
|---|---:|---|
| Advanced Warfare launcher | 1,775,104 | `A4A7230C03FDFF7A100668E137B99DD8639B7E4079970DA5DF7900A32A84DCF2` |
| `Ayria_unkown_release` | 1,775,104 | `A4A7230C03FDFF7A100668E137B99DD8639B7E4079970DA5DF7900A32A84DCF2` |
| `ayriax3/1/Ayria` | 1,775,104 | `A4A7230C03FDFF7A100668E137B99DD8639B7E4079970DA5DF7900A32A84DCF2` |

The injector, bootstrapper, Localnetworking and Platformwrapper binaries also
match by SHA-256 between the Advanced Warfare package and
`Ayria_unkown_release`. Differences between those distributions are confined
to mutable user data, title assets, playlist revisions and IDA database
artifacts. They are not different CODOL and Advanced Warfare plugin builds.

The reconstructed backend observed in that capture was 3,639,808 bytes with SHA-256
`604385BEA9AB15D89248A80518491690039BB12363AA167606403AEABF30B740`.
That is the reconstructed backend, not another archived Project Nova release.

PE COFF timestamps in these deterministic binaries decode to implausible dates
and must not be used to date the release. Content hashes and recovered behavior
are the reliable identity evidence.

## What the generic binary changes

The archived plugin's 21 lobby dispatchers and 141 task cases are a denominator
for the whole Project Nova backend. They are not a CODOL implementation
checklist. A function's presence in that binary only proves that one supported
title may use it.

The reconstruction target is instead **CODOL observable compatibility**:

- the wire protocols required by the CODOL executable;
- every CODOL-reachable service/task and its observable response;
- file, profile, inventory, matchmaking and other persistent side effects;
- unsolicited callbacks and server pushes that CODOL can receive;
- the state transitions needed from startup through sustained gameplay and
  post-match persistence.

Instruction-level equivalence and handlers reachable only by other Project
Nova titles are not required.

For this reconstruction, title ID `1004` is the CODOL title. Its published
assets are CODOL-specific and the captured CODOL Auth3 session selects the same
ID. The public launcher's Black Ops mapping is treated as a launcher mistake or
version mismatch and does not override the asset and runtime evidence. A
composite CODOL PE/build fingerprint is still required for safe executable
patching, but not for classifying the `1004` asset tree.

## CODOL reachability test

A generic-plugin path belongs in the CODOL reconstruction when at least one of
these conditions is satisfied:

1. A real CODOL trace contains its service/task pair or protocol exchange.
2. The CODOL executable has a live static call path to the corresponding DW API
   and the path is reachable in a supported UI or gameplay scenario.
3. The archived handler has a CODOL-reachable side effect even when its response
   is empty, including file I/O, shared-state mutation or network publication.
4. The path creates an unsolicited event, callback or push consumed by a CODOL
   registration point. These paths will not appear in a request-only ledger.
5. A required downstream state transition fails without the path and succeeds
   with an archived-oracle-compatible implementation.

A path may be classified `non-CODOL` only after positive evidence, such as:

- it is 64-bit-only while this CODOL client and backend are x86;
- it is gated by a different title identity or another title's asset directory;
- its callers are specific to another supported executable or protocol
  generation;
- complete registration, call-site and side-effect review proves it is cold for
  CODOL.

Absence from one startup trace is not enough to exclude a path. Store actions,
profile mutation, room lifecycle, ready-to-map, in-map play, disconnect,
reconnect and post-match completion need separate scenario traces.

## Practical closure model

There is no single binary signature that proves all CODOL functionality has
been restored. The useful closure test is a combined matrix:

| Evidence | Purpose |
|---|---|
| Runtime `(service, task)` ledger | Finds actual requests and payload variants |
| CODOL DW API call graph | Finds cold UI/gameplay paths not yet exercised |
| Archived dispatcher and side-effect audit | Preserves behavior hidden behind empty replies |
| Callback/push registration graph | Covers server-originated events absent from request logs |
| Scenario differential tests | Compares archived and rebuilt state transitions and persistence |

Each newly observed pair should be replayed against the archived DLL, assigned
an explicit semantic class, implemented in source, and added to a regression
fixture. A scenario is closed only when the rebuilt backend has no missing
handler, no unexplained response delta, and no unexplained persistent-state
delta relative to the archived oracle.

## Interpretation of the recorded snapshot

The recorded `46/46` figure closed that captured broad startup/request ledger; it
does not close every possible CODOL scenario. Conversely, `64/141` does not mean
that CODOL is only 45.4 percent reconstructed, because 141 is the generic
Project Nova task-case denominator.

The highest-value remaining work is therefore not blind completion of all 141
cases. It is the CODOL scenario frontier already visible in the project:

- ready-to-map and server-allocation behavior;
- listen or dedicated gameplay-server establishment;
- client/server challenge, gamestate and snapshot flow;
- map load, GSC execution and sustained play;
- post-match result persistence;
- real two-client LAN discovery and messaging.
