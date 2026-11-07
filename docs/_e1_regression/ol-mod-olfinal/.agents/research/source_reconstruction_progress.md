# Alwaysoffline source reconstruction progress

> Status: compatibility snapshot captured during the migration into ol-mod. Counts and phrases such as "current" describe that capture point; recompute them from source and traces before quoting them as present status. Current priorities live only in `../AGENTS.md`.

This ledger separates measurable compatibility from complete source recovery.
The archived lobby task denominator is now known, but handler registration is
not the same as semantic reconstruction and must not be presented as a single
whole-plugin percentage.

## Verified coverage at capture time

| Scope | Coverage | Meaning |
|---|---:|---|
| Broad captured CODOL request ledger | `47 / 47` (100%) | Every unique service/task pair in the current full-startup capture has a registered handler. |
| Structured/stateful handlers in that ledger | `28 / 47` (59.6%) | Request fields and response/state behavior are implemented rather than represented only by a captured empty-success reply. |
| Captured empty-success handlers | `19 / 47` (40.4%) | The archived response shape is exact, but no unobserved behavior is claimed. |
| Matchmaking `0x15`/`0x8A` unique tasks | `8 / 8` (100%) | Tasks `1,2,3,5,9,10,12,16` are all implemented. |
| Profiles2 CODOL tasks | `8 / 8` (100%) | Tasks `1-8` implement current/by-user public and private reads/writes, atomic persistence, missing-private error `800`, and current-user deletion. |
| ContentUnlock2 archived tasks | `4 / 4` (100%) | Tasks `1-4` reproduce per-content counters, user-scoped request forms, and the minimum returned count of 32. |
| Archived Project Nova lobby service-ID breadth | `14 / 21` (66.7%) | At least one handler exists for 14 of the 21 service IDs registered by the archived multi-game lobby plugin. This is not CODOL reachability or full task coverage. |
| Archived Project Nova lobby task-case breadth | `64 / 141` (45.4%) | A handler is registered for 64 original service/task cases. The denominator spans the generic multi-game plugin; this includes captured-empty handlers and does not claim complete CODOL semantics. |

Profiles2 intentionally follows CODOL's client contract instead of preserving
one archived-plugin defect. The original service-8 constructor identifies task
`6` as set-private-by-user-ID, whereas the archived plugin aliases tasks `5/6`
to profile deletion. The reconstructed tasks `6/7/8` now parse the explicit
user ID and isolate each user's private/public files; task `5` alone deletes
the current user's pair. No task `6` has appeared in the current lobby-only
runtime traces, so the post-match trigger and payload remain to be verified in
a completed match even though the server-side persistence path is implemented.
The generated version-19 secure profile has also completed two live task-2
downloads and lobby starts, validating the read envelope, CRC and 36 trailing
fields independently of the unobserved match upload.

The reconstructed registry currently contains 78 unique service/task pairs,
including CODOL calls which the archived dispatcher did not implement, such as
Marketplace inventory tasks `203/230` and purchase task `154`.

Startup ownership loading is now connected to that service implementation.
Runtime traces proved that unmodified CODOL startup never requests task `203`;
its native callers only cover console/UI refresh and purchase/coupon completion.
The source plugin wraps the validated `bdProfiles_GetPublicInfos` callsite,
starts the game's original inventory request immediately before Profiles2
`8/1`, and defers that profile request until the remote task has deserialized
and the native inventory finalizer has run. A live run completed Marketplace
`80/203` sequence `7` with 28 entitlement objects before issuing Profiles2
`8/1` sequence `19`. This keeps the client cache, Marketplace serialization
and loadout consumers native while ensuring ownership is present for the first
loadout validation pass.

CODOL then performs a distinct late Marketplace initialization through service
`80`, task `230`. Its completion callback clears the same 20,000-entry cache
and replaces it with the returned objects. The reconstructed service now maps
task `230`'s empty-context request to the same persistent inventory backing
store as task `203`. Runtime sequence `26` returned the same 28 objects, the
post-initialization native count remained 28, and the warehouse displayed owned
supplies without a purchase or `CodolInventory.py refresh`.

The completion hook remains as a fallback when Marketplace is not ready at the
earlier callsite. It also covers the native first-user case where Profiles2
`8/1` returns error `800`: CODOL treats that result as an accepted empty public
profile, without treating unrelated profile errors as success.

The CODOL client-side ownership boundary is also recovered. Public Profiles2
stores equipped loadout and identity selections, secure Profiles2 stores
progression `unlockFlagsNew` values, and Marketplace task `203` supplies the
entitlement cache. A separate client-built starter/default whitelist explains
why the initial M4/Vector/L86, M9, attachments and class items remain usable
without entitlement rows. This removes the need to treat `Publicprofile` as an
unknown inventory container. The secure-profile upload handlers now follow the
client task contract, while the real post-match trigger remains unobserved.

The client-side equipment persistence loop is now recovered as well. Native
weapon and attachment setters stage a base item plus six attachments per
weapon slot, flush exact `primaryBase`/`secondaryBase` and attachment DDL
paths, mark the public profile dirty, and reach Profiles2 `8/3` through the
normal upload poll. A separate class staging path covers perks, equipment,
killstreaks, wildcards and double-ammo flags; current character selection uses
the same dirty/upload mechanism. This confirms that reconstruction code can
use the game's original loadout setters and `Publicprofile` serialization
instead of maintaining a parallel equipped-loadout JSON format.

The same result now covers identity presentation. Native category dispatch
persists badge, card icon, title and background to `Publicprofile`, including
default fallback and entitlement-removal behavior. `cardNameplate` remains a
validated profile field but is not dispatched as a normal purchasable identity
item, so its service-side meaning remains a narrower follow-up item.

The Advanced Warfare launcher distribution contains an archived
`Alwaysoffline.Localnet32` with the same SHA-256 as the CODOL-era copies and
uses that plugin family across several 32-bit and 64-bit games. Consequently,
the 141-case denominator describes Project Nova as a whole, not the CODOL
completion target. See `project_nova_codol_scope.md` for the distribution
comparison and the CODOL reachability rules.

## Functional migration classes

Archived behavior is audited by impact, not by requiring instruction-for-
instruction equivalence. Every dispatcher and task must end in one of these
classes before whole-plugin coverage can be claimed:

| Class | Required evidence | Current examples | Priority |
|---|---|---|---|
| `stateful-required` | IDA task enumeration plus request, response and persistence semantics | Profiles2 `1-8`; ContentUnlock2 `1-4`; Marketplace inventory/purchase; Matchmaking `1/2/3/9/10/12`; local `0x0B/5` channel push; Messaging `0x06/14,18` | Highest |
| `protocol-required` | Wire-compatible handshake, framing, crypto or file-transfer behavior | STUN, Auth3, LSG, Storage2 `12/20/21` | Highest |
| `captured-empty` | Exact archived capture shows empty success; underlying handler still awaits cold-path audit | 19 active generic entries from `CodolStartupTasks.cpp` | Medium |
| `unused/cold` | Complete dispatcher enumeration and call-site review show no CODOL gameplay dependency | Messaging `0x06/5` archived ring has readers and cleanup but no insertion xref | Low |
| `unknown-review` | Task set or side effects are not yet fully recovered | Remaining archived service dispatchers outside the enumerated set | Audit queue |

An observed empty response is not sufficient to classify a task as
`unused/cold`: file I/O, container mutation, response-object construction and
network broadcast in the archived handler all promote it to
`stateful-required`. This is the guard against omitting features that were not
exercised by the current single-client capture.

## Archived lobby dispatcher ledger

IDA xrefs to the archived callback registrar at `0x10035B81` establish one
LSG protocol callback (service `0x07`) and the following 21 task dispatchers.
The protocol callback is deliberately excluded from the task-case denominator.

| Service | Archived task cases | Current registered archived cases | Gap |
|---:|---|---|---:|
| `0x47` Tencent | `1,2,3,4,5,6,7,8,10,11,15` | all except `6`, plus task `9` outside the archived switch | `1` |
| `0x21` unknown | `1-6` | none | `6` |
| `0x32` unknown | `1,2,3,5,6,8,9,10,13-20` | none | `16` |
| `0x43` unknown | `1-6` | none | `6` |
| `0x50` Marketplace | `32,49,107,130,151,155,165,169` | `32,107,130` | `5` |
| `0x0A` Storage2 | `1-13,16,18,20,21,23,24` | `12,20,21` | `16` |
| `0x12` unknown | `1` | none | `1` |
| `0x1B` unknown | `1-3` | none | `3` |
| `0x15` Matchmaking | `1,2,3,5,9,10,12,16` | all | `0` |
| `0x8A` Matchmaking2 | `1,2,3,5,9,10,12,16` | all | `0` |
| `0x09` Friends2 | `1,9,12,14,16,17,26` | `9,12,14,16,26` | `2` |
| `0x06` Messaging | `5,14,18` | all | `0` |
| `0x0B` room/identity | `1,2,4,5,9,10,11,13` | all | `0` |
| `0x66` unknown | `1,2,3,4,8` | `1` | `4` |
| `0x08` Profiles2 | `1-8` | all | `0` |
| `0x44` unknown | `1,2` | `1` | `1` |
| `0x0C` TitleUtilities2 | `1-10` | `6,9` | `8` |
| `0x26` unknown | `2,4,6` | none | `3` |
| `0x17` unknown | `1,2` | none | `2` |
| `0x1C` ContentUnlock2 | `1-4` | all | `0` |
| `0x0F` unknown | `1-3` | none | `3` |

The five `dwAuth` callback registrations use service IDs `0x00`, `0x0A`,
`0x0C`, `0x1A`, and `0x1C`. They are raw authentication protocol handlers,
not lobby task dispatchers, and therefore require a separate wire-behavior
ledger rather than being added to the 141 task cases.

### Recovered side-effect paths

| Service/task | Archived side effect | Current status |
|---|---|---|
| `0x0B/4` room message | Immediately feeds a public `Demonware::Channelmessage` to the local receiver, then broadcasts the same event over MEEP | Recovered from `Unknown0B_dispatch -> 0x1005167C`. The source now emits the exact public event `8` type-2 push. A real client run confirmed that the room member ready flag changes to `1` and the matchmaking state machine proceeds. |
| `0x0B/5` and legacy MEEP | Broadcasts `Demonware::Channelmessage` as a Base64-encoded JSON event over UDP port `0x4321` | Local event `7`, remote event `8`, encrypted type-2 LSG delivery, origin filtering and the original wire envelope are represented in source. Real two-client delivery remains an end-to-end test gap rather than a source gap. |
| `0x06/14,18` and legacy MEEP | Publishes `Demonware::Instantmessage`; the receive callback filters by recipient and queues event `21` as an encrypted type-2 LSG push | Remote task-14 and repeated-recipient task-18 publishing, strict JSON validation, recipient filtering and the exact event-21 serializer are represented in source. The recipient-zero/local `mmbook` command reproduces its nested raw blob and immediate `mmbook accepted` event-21 push byte-for-byte, including CODOL's optional request-tail zero. A real client run reached `mmstart`. |
| `0x06/5` | Paginates an archived instant-message ring and optionally consumes returned entries | Both three-field request modes return exact empty success in the archived black box. Complete xrefs show no ring insertion path in this build, so the explicit source handler validates the request and preserves the observable empty result. |

## End-to-end status

Verified in a real client run:

- startup patching and hostname compatibility;
- STUN, Auth3 TLS/HTTP, tickets, DW3 LSG handshake and encrypted traffic;
- publisher and user storage used by startup;
- identity, public profile, inventory and purchase persistence;
- main lobby, session search/create/delete, room entry and ready state;
- natural `FIND_SERVERS -> mmbook -> mmbook accepted -> mmstart` progression;
- archived LAN discovery format and native-style session IDs.

The gameplay data plane is not yet restored. The historical PVP run advanced to
`mmstart` because task `0x15/5` returned the client-created player lobby for a
query whose leading typed `uint32` was `1`
(`MatchMaking_FIND_SERVERS_Query`). That false allocation configured playlist
`33` and `start_map_rotate_once 5`, then failed with
`EXE_CLIENTFAILEDTOCHALLENGE` because no authoritative server owned the lobby
endpoint. The handler now distinguishes kind `1` from kind `3`
(`MatchMaking_FIND_LOBBIES_BY_PLAYLIST_Query`) and excludes the local lobby from
server searches. The first story mission's empty server result and busy-server
UI are now the expected behavior until an explicit external server candidate
is registered.

An explicit-candidate probe now exists in `references/client_probe/CodolGameplayProbe.py`. The
backend accepts only remote discovery sessions labelled `Session.Role=server`
for `FIND_SERVERS` and excludes those sessions from playlist-lobby queries. The
probe clones a real task-1 descriptor, advertises a controlled 37-byte
`bdCommonAddr`, listens on the advertised UDP endpoint, replies to
`getchallenge`, and records the subsequent `connect` request. This is a
diagnostic protocol boundary, not an authoritative gameplay implementation.

The QA ship client's Gate A audit is now negative. BO1 symbol comparison maps
CODOL `0x465C00` and `0x466790` to the client-side `CL_CheckForResend` and
`CL_DispatchConnectionlessPacket` roles, while the server-side challenge
producer, server frame loop, gamestate/snapshot builder and server GSC execution
cluster have no identified counterparts. The `mmbook accepted` path at
`0x6E6F60` builds an outbound `mmstart` command at `0x6E6BF0`; its
`sv_resetServer`, `map`, and `start_map_rotate_once` tokens have no local
receiver. Work should therefore target an external authoritative server rather
than another synthetic matchmaking success or a dormant listen-mode patch.

Not yet verified:

- a successful ready-to-map transition using a real dedicated-server descriptor;
- a compatible external CODOL authoritative gameplay server path;
- client/server challenge, gamestate and snapshot exchange;
- map loading, server GSC execution and sustained play;
- post-match result persistence;
- a real two-client LAN discovery and channel-message session.

## Why there is no whole-plugin percentage

The archived multi-game Project Nova binary registers 27 callbacks: five `dwAuth` protocol handlers,
one LSG protocol handler, and 21 lobby task dispatchers. The lobby dispatcher
and task-case denominators are now complete, but only selected handlers have
fully recovered request, response and state semantics. A percentage based on
registered cases would count captured empty replies as complete and ignore the
separate protocol surface. The honest whole-plugin status therefore remains
**partial, with a complete lobby registration denominator but an incomplete
semantic denominator**. The next audit milestone is to classify all 141 cases
by side effects and response-object construction.
