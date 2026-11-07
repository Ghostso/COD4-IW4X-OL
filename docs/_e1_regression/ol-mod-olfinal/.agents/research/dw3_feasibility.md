# CODOL 3.3.3.3 DW3 feasibility

> Status: historical feasibility study and early runtime evidence. Its initial implementation order has been superseded by the current source tree; use `../AGENTS.md` for live priorities and `../modules/backend.md` for current boundaries.

## Recorded decision and present status

Restoring the QA client's online bootstrap, menus, publisher data, player state,
and matchmaking request flow is feasible with the local references. Reaching an
actual playable match is not yet proven because no CODOL dedicated server binary
is available.

The Auth + LSG feasibility milestone has since been completed in the injected
`ol_backend`, and the first game-server skeleton exists. Moving the control
plane into a standalone process remains an optional reliability improvement,
not the next required protocol step. Current work and go/no-go boundaries are
maintained in `../AGENTS.md`.

## Evidence used

- `codoMP_client_shipRetail.exe.i64`, image base `0x400000`.
- BO2 `CoDMPServer_PC.exe.i64` with PDB symbols.
- IW8 PDB-exported `bdtencent` sources under the local OpenIW8 tree.
- Local `s1x-client` DW3 implementation.
- `CODOL revival notes.txt`.
- The published Ayria title `1004` assets.

IDA 9.3 batch analysis was run against copies under `Bin/diagnostics`; the source
databases were not modified.

## End-to-end chain

| Stage | Protocol / responsibility | Local evidence | Feasibility |
|---|---|---|---|
| Redirect | `dwauth.ini`, CA, STUN and Auth/LSG endpoints | Client references `dwauth.ini`; notes document the format | High |
| Auth3 | HTTPS JSON request and code `700` response | CODOL functions at `0xA58F00`, `0xA598B0`; s1x `auth3_server` | High |
| Tickets | 3DES client ticket, 128-byte server ticket, 24-byte session key | CODOL ticket parsing/decryption at `0x6C7C90`, `0x6C7E60`, `0x6C8BC0`, `0x6C9BA0`, `0x79C0F0` | High after key validation |
| LSG handshake | TCP framing, header ACK, client auth, AES/HMAC key derivation | s1x `lobby_server.cpp`, `keys.cpp`, `reply.cpp`; BO2 PDB lobby classes | High |
| Initial services | 43 observed calls across Storage2, Profiles2, Tencent, Marketplace, Teams and others | Runtime request matrix; revival notes; CODOL service/error strings | High for the startup ledger |
| Publisher storage | List and fetch required configuration files | BO2 PDB service `0x0A`, tasks `6` and `7`; CODOL function `0x591FD0` | High |
| Player state | Public/private profile and onboarding state | Ayria title `1004` profile files; CODOL profile/onboarding RTTI | Medium-high |
| Matchmaking | Return sessions and dedicated-server connection data | BO2 matchmaking structures; CODOL query RTTI for playlist/map/channel/server | Medium |
| Gameplay server | Run map simulation, GSC and authoritative networking | No CODOL server binary; only client orchestration evidence | Low / unproven |

## Runtime validation

The original client, original injector, and the 2019 Ayria runtime complete
Auth3, the DW3 LSG handshake, and encrypted `0xAB85` service traffic. The first
repeatable disconnect was caused by an Alwaysoffline hostname predicate, not by
an Auth3 ticket, LSG crypto, or client executable patch.

Alwaysoffline uses `strstr(hostname, "stun.")`, while CODOL resolves eight names
beginning with `stun1-` or `stun2-`. In the failed `20260727_094709` run, the
client sent 288 STUN datagrams to obsolete public addresses, received none, and
reported `Address Fail|result = -3` after about 94.7 seconds. In the successful
`20260727_095307` run, temporarily shortening the needle to `stun` redirected
all eight names through the local `240/8` proxy, produced 132 successful UDP
receives, and allowed 43 DW service requests to proceed. The user independently
confirmed that the client reached the working game UI.

The persistent compatibility patch changes only file offset `0x181594` in
`Alwaysoffline.Localnet32` from `'.'` to NUL. `tools/runtime/SetCodolStunProxy.py`
applies or restores that known change. This binary edit is a reproducibility
bridge, not the final architecture: the source-owned backend/local-networking
replacement must match `stun1-` and `stun2-` directly.

The stable executable and archived original differ at only seven instruction
sites (ten bytes total). IDA identifies RVA `0x2422C1` as the localization-load
guard, RVA `0x24283D` as the mandatory `-q/-qa` guard, and RVAs `0x2D2AD1`,
`0x2D2B07`, `0x2D2B42`, `0x2D2B8D`, and `0x2D2C18` as error-only branches in
the DW logon state machine. `AlwaysofflineRe` now applies those changes in
memory from `DllMain`, before Injector32 resumes the game main thread. All
sites, the x86 machine, PE timestamp `0x57611E31`, and image size `0xC72A000`
must match; validation completes before page protections or bytes are changed.

DW3 request payloads begin with `service_id`, protocol version, then `task_id`.
CODOL uses protocol version `3`; treating the second byte as the task incorrectly
labels every request as task 3. `references/client_probe/AnalyzeCodolTrace.py` reparses the raw
payload and generates [the request matrix](codol_dw_request_matrix.md).

## Static findings

### Player identity and marketplace inventory

The lobby display name does not come from Platformwrapper's `Username.txt`.
A rendered-window capture from the live client displays `Alwaysoffline`, and
the plugin copies that 13-byte
literal from file offset `0x181568` into the DW authentication account structure
at `0x1002D7F7`. A short literal replacement can validate another name, but the
source implementation should expose it as account configuration and serialize
it through Auth3/LSG instead of retaining a fixed-size binary field.
A historical `CODOL/Config/Identity.json` recorded the test identity `dest1yo`.
That config was not migrated into the current distribution. The remaining
`tools/profile/SetCodolIdentity.py` is an archived-plugin binary-patch experiment,
not the source backend's identity configuration path; do not present it as a
current supported workflow.

Marketplace is service `0x50`. The successful startup invokes tasks `0x46`,
`0x6B`, `0xE6`, `0xAD`, and `0xAE`; their CODOL-specific names are not yet
assigned. The 2019 plugin contains a title asset loader for `Marketplace` with
the keys `Wallets`, `Loot`, `Entitlements`, and `lootConfig`, plus item fields
including `ID`, `Type`, `Amount`, `Key`, and `Value`. The title `1004` assets do
not currently provide that Marketplace definition or a CODOL loot-config CSV.

The live client's `StringTable` assets were exported through
`DB_FindXAssetHeader`: `mp/coMarketplaceItems.csv` has 6,772 rows,
`mp/badgeTable.csv` has 21, and `mp/callsignBackground.csv` has 397. Marketplace
category `pci` denotes an emblem, `pcb` a player-card background, and `bdg` a
badge. The source-controlled test inventory uses two confirmed emblems (`30000`,
`30564`), two confirmed backgrounds (`30022`, `30372`), and one badge (`40001`).
The historical `SetCodolMarketplace.py` experiment deployed that asset to the
title `1004` server directory. It has been superseded by the recovered
`assets/backend/1004/MarketplaceSkus.json` catalog and is not the current
distribution contract.

The clean-start trial proved that `Loot` entries alone do not produce owned
CODOL items. IDA decompilation explains why: Alwaysoffline function `0x10042990`
loads each `Loot[].ID`, but its dispatcher at `0x1004284C` only implements tasks
`32`, `49`, `107`, `130`, `151`, `155`, `165`, and `169`. CODOL's
`marketplace.getinventory` path uses task `203` and a larger inventory object
with an additional `customSourceType` byte.

`AlwaysofflineRe` now supplies task `203` directly. The captured request is the
contextual form `string context`, `uint16 maximumResults` (normally `20000`),
not the earlier assumed page-only request. Persistent ownership is reloaded on
each request from
`Ayria/Assets/Alwaysoffline/<titleId>/<userIdHex>/Inventory.json`, and the
response serializes the archived inventory object field order. The normal game
completion callback then populates the 20,000-entry inventory cache at
`0x7BEC448`. `tools/profile/CodolInventory.py refresh` invokes the original client
refresh path.

Repeated clean launches showed that the client does not issue task `203` during
its normal startup sequence. Six captured runs reached Profiles2 `8/1`, but no
`0x50/203` request appeared. Xrefs to the native refresh entry at `0x4A6B10`
are limited to the console command, storefront/ActionScript callbacks, and
post-purchase or post-coupon cache refreshes. In particular, the apparent
`PlayerDataEventHandler` caller at `0x5E3570` is virtual slot 16, dispatched by
`RedeemCouponsComplete`; it is not a profile-load callback.

The reconstructed plugin therefore wraps the sole public-profile request call
at `0x6D866A` in `CODOL_Profile_RequestPump` (`0x6D8560`). The wrapper starts
the native inventory request at `0x4A6B10`, captures the remote task created at
`0x4A6B97`, and defers `bdProfiles_GetPublicInfos` until status `2`, error `0`,
deserialization and the native finalizer at `0x4A6CC0` have completed. The
original call bytes and native targets are tied to the validated CODOL image
before patching. This avoids calling Marketplace from `DllMain`, removes the
old fixed post-lobby delay, and places owned items in the client cache before
the first public-profile loadout and identity validation pass.

Live validation recorded Marketplace `80/203` as request sequence `7`, with its
28-object response finalized before Profiles2 `8/1` was issued as sequence
`19`. The client remained running through the normal lobby startup. A detour
at `CODOL_Profile_OnTaskComplete` (`0x6D83E0`) remains as a retry only if the
Marketplace interface was not ready at the earlier request callsite.

The later `CODOL_Marketplace_RequestStartupInventory` (`0x4A5120`)
independently constructs service `80`, task `230` through
`bdMarketplace_StartGetInventoryPaged` (`0xA472B0`). Its completion callback,
`CODOL_Marketplace_OnPagedInventoryComplete` (`0x4A5680`), clears the
20,000-entry native inventory, copies the returned 168-byte inventory objects,
and finalizes the replacement. The captured request body is an empty context
(`100000` including the trailing frame byte), not the task `203`
context-plus-maximum form. Mapping task `230` to the same persistent inventory
store prevents this legitimate late replacement from erasing the pre-profile
cache. Runtime sequence `26` returned 28 objects, live memory kept
`CODOL_Marketplace_InventoryCount == 28`, and a restored equipped M4A1 remained
selected after the next startup.

The same hook also follows CODOL's native treatment of Profiles2 error `800`:
the client accepts it as an empty public profile for first-user onboarding.
The fallback predicate is restricted to public-profile download operations and
accepts either normal success or error `800`; private-profile reads, uploads and
other failures do not request inventory. A no-`Publicprofile` runtime trial
recorded the accepted-empty-profile message followed by `service=80 task=203`,
which returned the current 24 entitlement objects without terminating CODOL.

CODOL has two observed purchase routes: Marketplace `0x50/154` and the
storefront's service `0x5D/131`. Both use an array contract containing SKU IDs,
quantities, account identifiers, and zero-valued optional fields, with one
different trailing count. The Marketplace success callback does not consume a
response object: it clears the client inventory cache and immediately starts
task `203`. `AlwaysofflineRe` validates and acknowledges both captured request
shapes, resolves their SKU grants through the recovered four-table catalog,
commits the resulting entitlements, and lets the normal completion callback
repopulate the client cache. The refresh entry is executable RVA `0xA6B10`;
the source plugin now reaches it before the validated public-profile request,
so no separate post-lobby compatibility DLL or Frida refresh is required.

The current `Inventory.json` file is a reconstruction-owned service backing
store. It is not present in any preserved Project Nova distribution and is not
a CODOL profile format. The client-visible behavior remains native: task `203`
returns `bdMarketplaceInventory` objects into the 20,000-entry cache, while
`Publicprofile` stores equipped loadouts and personalization references. The
secure profile separately contains progression-oriented `unlockFlags` and
`unlockFlagsNew`. Replacing JSON with a database is therefore a backend storage
change, not a client hook or profile-format change.

The standalone reconstruction now handles the captured Marketplace task `130`
balance request. The original dispatcher maps it to the same handler as legacy
task `32`: it reads one `uint32` maximum-result count and serializes each wallet
as `uint8 Type` followed by `uint32 Amount`. Wallet values come from the
optional title asset `Marketplace` and its `Wallets` array. Title `1004` has no
such asset, so the archived plugin's effective response is an empty successful
list; the reconstruction preserves that behavior instead of inventing a
currency balance.

### Tencent service cross-check

The exported IW8 `bdTencent` source is useful to CODOL despite the five-year
gap. CODOL independently constructs service `0x47` requests at `0xA48540` to
`0xA49280`, and the following task contracts match the later named source:

| Task | CODOL function | Request contract | IW8 name / confidence |
|---:|---|---|---|
| `1` | `0xA48540` | String; one result | `verifyString`, exact |
| `2` | `0xA48640` | String; one result | `sanitizeString`, exact |
| `3` | `0xA48B80` / `0xA49280` | TLog string, batched | `tLogBatchSend`, exact |
| `4` | `0xA48800` | CodoID, signature, version, extra data, login signature, MAC | `registerCodoID`, exact field order |
| `5` | `0xA48740` | No input; one AAS result | `getAASRecord`, exact |
| `7` | `0xA48B80` / `0xA49250` | TLog string | `tLog`, exact |
| `8` | `0xA48CA0` | Antibot string | `antibotSendData`, same task and purpose |
| `9` | `0xA48DF0` | No payload | Unresolved; not IW8 `doLogoff` |
| `10` | `0xA48EA0` | No payload | `claimRewards`, exact |
| `11` | `0xA48F50` | Count plus event-code strings | `claimClientDecidedRewards`, exact; string cap changed |
| `12` | `0xA490E0` | Item ID plus desired name | `redeemNameChange`, exact |
| `15` | `0xA48A60` | Compressed blob | `tlogBatchSendCompressed`, exact |

Task `9` is the important counterexample to blanket compatibility. CODOL sends
no fields and invokes it during startup, even though the archived Tencent
dispatcher has no explicit case and falls through to empty success. IW8 calls
task `9` `doLogoff` and writes an `offlineReason` `uint32`. The service number
and most task contracts stayed stable, but individual tasks did drift.

The reconstruction now also implements archived task `1` as one input string
and a typed zero `uint32` verification result. Tasks `3/7/8` share an explicit
single-string telemetry consumer, while task `11` validates its typed count and
event-code string list before returning empty success. Task `6` remains the
only explicit archived Tencent case without a source handler because its
multi-object result contract is not yet fully identified.

The IW8 source should therefore be used as a semantic and serialization-field
dictionary. Its 64-bit object layout, newer struct-buffer result types, antibot
batching implementation, and post-CODOL tasks must not be copied into the 2015
client ABI. The inspected IW8 `.i64` was not opened or modified while IDA was
upgrading it.

The captured `configs_s.info` has `tencent=0`. That disables the service for that
specific configuration; it does not contradict the complete client-side
implementation or the initial request ledger.

### Auth3

CODOL builds the Auth3 JSON and HTTPS request in `0xA58F00`. The request includes
`auth_task`, `iv_seed`, and `title_id`, and is sent to `https://<host>:<port>/auth/`.
The HTTP path also sends `title_id` and `tencent_ticket` headers.

The response parser at `0xA598B0` validates `auth_task` and `code`, decodes
`client_ticket`, and requires an exactly 128-byte decoded `server_ticket`.
`0xA58730` treats code `700` as success. `0xA57980` consumes the persisted
`lsg_server_ticket`, its size, and the IV seed.

s1x provides the correct server shape, ticket structure, session key plumbing,
and crypto primitives. It cannot be copied unchanged because its token layout,
account type, title assumptions, and key derivation are S1-specific.

There is a title-ID discrepancy to resolve from a captured request:

- The notes' example and `0x03EA` redirect value imply title `1002`.
- Current Ayria logs and `configs_s.info` map the `stnd` zone to title `1004`.

The backend must log and honor the client's actual request instead of hardcoding
either value.

### LSG framing

s1x already implements the reusable DW3 wire state machine:

1. Client header ACK (`0xC8`).
2. Server header ACK.
3. Client auth (`0xAB 0x82`).
4. Session-key derivation using SHA-1 and HMAC-SHA1 labels.
5. Server auth done (`0xAB 0x83`).
6. Encrypted service traffic (`0xAB 0x85`) using AES and an 8-byte HMAC suffix.

The original CODOL plugin and the captured QA client refine that generic shape:

- The generation-3 client header begins with two `0xC8` dwords but is only 28
  bytes long. The first dword is not a normal frame length.
- The key transcript is exactly `clientHeader[8:] + serverHeader +
  clientAuth[:-8]`.
- The intermediate secret is `HMAC-SHA1(key=SHA1(transcript),
  data=sessionKey)`. The argument direction is significant.
- `CLIENTCHAL` and `BDDATA` use repeated
  `HMAC-SHA1(secret, previous + label + oneByteCounter)` blocks.
- `BDDATA[0:20]` authenticates client requests, `BDDATA[20:40]`
  authenticates server responses, and the AES keys are at `[40:56]` and
  `[56:72]`. A single shared HMAC key does not validate real CODOL traffic.

The successful `20260727_095307` trace reproduces the captured `AB83`
challenge exactly with the 24-byte session key `Tencentticket` followed by 11
NUL bytes. It also confirms that service `0x5D`, task `1` receives a type-1
empty-success envelope: error `0`, task `1`, and object count `0`. Its logical
21-byte response is padded into a 66-byte encrypted frame by the original
serializer.

Unknown services can initially return a task-success envelope. This matches the
revival notes: most initial requests can be dummied, but publisher storage cannot.

### Publisher storage

The BO2 PDB confirms the legacy service contract used by s1x:

- Service `0x0A`, task `6`: `bdStorage::listAllPublisherFiles`.
- Service `0x0A`, task `7`: `bdStorage::getPublisherFile`.
- List parameters are `startDate`, `maxNumResults`, `offset`, and optional name.
- Get takes a filename and returns one `bdFileData` result.

CODOL `0x591FD0` requests these files directly:

- `configs_s.info`
- the playlist filename selected by dvar `1887`
- `broadcast.info`
- `activities_v1.info`
- `tlogconfig.info`
- `market-down.info`
- `whitelist_tester.info`
- `sku_tags.info`

The current Ayria assets already contain seven matching files and substantial
CODOL data. `configs_s.info` is about 25 KB and the playlist is about 128 KB.
The playlist contains onboarding, PvP, PvE, map rotations and game types.

One alias is required: the client defaults to `mp_playlists_shipRetail.info`,
while the available asset is `mp_playlists_shipRetail_release.info`.

The reconstructed backend now implements the CODOL runtime contract on tasks
`20/21` as well as the shared DW3 response envelope. IDA recovery of the
original result vtables confirms that task `20` serializes file size, a 64-bit
field containing the filename's 32-bit FNV-1a hash, two timestamps,
visibility, publisher owner, filename, and a 16-byte binary MD5 value. Task
`21` returns one typed blob and error `1000` when the requested file is absent.
The earlier tasks `6/7` remain a useful older-DW reference, but are not the
contract observed in the captured CODOL startup request.

The captured task `12` request is the user-file path: empty game name,
filename, 64-bit owner, then empty platform. The reconstructed service resolves
`<title>/<owner-hex>/<filename>` and returns one typed blob. This reproduces the
successful `the.json` response from the archived title-1004 assets and error
`1000` for the missing `FileBriefMessage` request.

Profiles2 task `3` is the current-user public-profile write path. It stores the
remaining request bytes directly as `Publicprofile`; the service does not need
to interpret CODOL's compressed DDL payload. Task `4` does the same for the
current user's `Privateprofile`. Tasks `6/7/8` parse their required typed user
ID and respectively set private, get private, and set public data in that
user's directory. Task `5` alone deletes both files for the current session.
A missing or empty private profile returns error `800`; a present one is
returned as a typed user ID followed by the stored bytes. All write paths use
atomic file replacement. Two-user regression tests prove that by-user writes
do not overwrite the current account and task `5` does not delete the other
account.

CODOL's own `bdProfiles` constructors are authoritative for this correction.
The client maps service `8` tasks `1/2/3/6/7/8` to get-public,
get-current-private, set-current-public, set-private-by-user-ID,
get-private-by-user-ID, and set-public-by-user-ID. In particular, task `6` is
not deletion in the client. The preserved Ayria plugin's `5/6` deletion alias
is therefore an implementation defect or title-specific shortcut; the
reconstruction now follows the client contract instead.

The initial runtime captures contained six missing task-2 reads returning error
`800`, which CODOL deliberately accepted as an empty/default private profile.
A later validation created a version-19 secure `Privateprofile` with the native
checksum, CRC and 36 trailing validation scalars. Two unmodified-client starts
then returned that object successfully through task `2` and reached the level-1
lobby. No private write task has been observed, however. The handler and read
format are now validated, but a completed real match is still required to
observe task `6` and any game-server-driven secure-profile update path.

### Matchmaking and gameplay

The archived plugin's service `0x15` and `0x8A` dispatchers expose the same
eight unique tasks: `1`, `2`, `3`, `5`, `9`, `10`, `12`, and `16`. Tasks `9`
and `10` are the legacy `submitPerformance` and `getPerformanceValues` pair.
The recovered request contract begins with a `uint32` context. Task `9` then
accepts repeated `uint64 user ID` plus `int64 performance` pairs and returns
empty success. Task `10` accepts repeated user IDs and returns one
`bdPerformanceValue` (`uint64 user ID`, `int64 performance`) per matching
entry. The archived DLL probe confirms both service IDs share this state and
omit unknown users from the result list.

Service `0x0B` participates in the room/identity flow. Its tasks `1/9/11`
consume two typed 64-bit IDs, while task `10` consumes two IDs, a `uint32` and
a boolean; these four scalar paths now have exact source handlers. Task `4`
decodes a channel ID, message blob and type, then invokes the local public
channel receiver before publishing `Demonware::Channelmessage`. Restoring that
event-8 push was required for CODOL to commit the local room member's ready
state. Task `5` is
not an empty acknowledgement: the archived handler decodes a channel ID,
recipient ID, message blob and type, adds the local sender metadata, and
publishes `Demonware::Channelmessage`. The replacement now reproduces its local
event `7` push and the legacy UDP `MEEP` transport on port `0x4321`, including
Base64 JSON framing, process-origin loopback filtering and origin/IP binding.
Remote non-whisper events are converted to the archived event `8` push. The
transport format is corroborated by both the archived binary and
`Ayria_cpp_20191208/Platformwrapper/Source/Common/Communication.cpp`; a real
two-client game run is still required before runtime compatibility is claimed.

Messaging service `0x06` uses the same legacy transport. Task `14` consumes a
typed recipient ID followed by a message blob; for a remote recipient it
publishes `Demonware::Instantmessage` and invokes the local receiver, which
then filters the event because it is not addressed to this user. Task `18`
consumes one message blob followed by repeated typed recipient IDs and
publishes one event per recipient. The remote receiver validates the JSON
recipient and serializes type-2 lobby event `21` as sender ID, sender name and
message blob. That remote chain is now represented in source and covered by an
exact archived-byte test plus synthetic MEEP ingestion. Task `14` routes a
zero or local recipient through a special nested-blob command parser. The
token `mmbook` produces an immediate local event-21 push whose message is the
raw-length blob `mmbook accepted`; the reconstructed bytes now match the
archived black box exactly. CODOL appends a single zero after the task-14 blob;
the parser now accepts that archived wire terminator while continuing to reject
other trailing data.

A July 30, 2026 real-client trace validated the combined path. A ready event-8
push caused `FIND_SERVERS`, the local `mmbook` request received event-21
`mmbook accepted`, and the client then sent:

```text
mmstart sv_resetServer; 2486 1; 3265 6; 2489 1; playlist 33; start_map_rotate_once 5
```

The client subsequently attempted the returned gameplay endpoint and failed
with `EXE_CLIENTFAILEDTOCHALLENGE`. Inspection of the captured task-5 payload
showed why: its first typed `uint32` was `1` (`MatchMaking_FIND_SERVERS_Query`),
but the reconstructed handler ignored that discriminator and returned the
client-created player lobby. A later lobby search began with `3`
(`MatchMaking_FIND_LOBBIES_BY_PLAYLIST_Query`). The handler now keeps the local
lobby for kind `3` and legacy empty requests, but excludes it for kind `1`.
Consequently, a positive `FIND_SERVERS` result must now represent an explicit
external server candidate. The first PVE story mission returned no server and
displayed the busy-server warning. The control-plane reconstruction has reached
allocation requests; neither historical result is evidence of a running
gameplay server.

The external-candidate experiment is implemented by
`references/client_probe/CodolGameplayProbe.py`. Remote discovery entries must carry
`Session.Role=server` to satisfy query kind `1`; kind `3` excludes those entries
and continues to return player lobbies. The tool clones the latest native
task-1 descriptor from the plugin log and constructs only its network address.
CODOL `0xA36F60` confirms that address is five local IPv4/port pairs, one public
IPv4/port pair, and a NAT byte. The prior test fixture was one empty local slot
short and has been corrected against the real-client request.

The probe deliberately stops at the first engine handshake boundary. It can
answer `getchallenge` and capture `connect`; it does not emit a fake gamestate,
snapshot, or map-start success.

Task `5` reads a `uint32` offset, a `uint32` maximum-result count, and a boolean
consume flag. Its archived ring supports non-destructive pagination or
front-consumption, but complete data xrefs show readers and shutdown cleanup
without any insertion path. Both consume modes return the same empty-success
envelope in black-box probes. The source handler therefore validates all three
fields and returns the build's observable empty queue instead of inventing a
message store.

This service is not being reconstructed from the archived DLL alone.
`FourDeltaOne/T5M/code/clientdll/dw/bdMessaging.cpp` corroborates service `6`,
task IDs `14/18`, and both request field orders. The older
`T5-DemonWare/DWServer/DW/DWMessaging.cs` also implements task `14` and writes
the same type-2 event `21` fields: sender ID, sender name, and message blob.
Those references establish the reusable Demonware contract. They do not
contain Ayria's MEEP envelope, task `18` recipient loop, recipient filtering,
or the nested `mmbook` command, so the archived CODOL plugin remains the source
of truth for those extensions.

ContentUnlock2 service `0x1C` has four archived tasks. Tasks `1/2` increment a
shared counter for every supplied content ID (task `2` first consumes a user
ID), task `3` consumes one user ID, and task `4` returns each requested ID with
`max(counter, 32)`. The earlier reconstruction returned a constant `32` and
therefore omitted the state transition; all four tasks and the shared counter
are now represented in source.

The BO2 PDB exposes session creation, update and deletion through matchmaking
service `0x15` (for example tasks `1`, `12`, and `3`). CODOL retains RTTI for:

- `MatchMaking_FIND_LOBBIES_BY_PLAYLIST_Query`
- `MatchMaking_FIND_LOBBIES_BY_MAP_Query`
- `MatchMaking_FIND_LOBBIES_BY_CHANNEL_Query`
- `MatchMaking_FIND_SERVERS_Query`
- `bdMatchMakingInfo`

The client also contains `xpartygo`, `map_restart`, onboarding mission handlers,
and tutorial-launch UI types. These are client-side match orchestration, not an
authoritative server. BO1 symbol comparison identifies CODOL `0x465C00` as
`CL_CheckForResend` and `0x466790` as `CL_DispatchConnectionlessPacket`: CODOL
sends `getchallenge` and consumes `challengeResponse`, but has no server-side
standalone `getchallenge` dispatcher or `challengeResponse %i` producer. The
server cluster represented in BO1 and Ghosts by `SV_Init`, `SV_Startup`,
`SV_SpawnServer`, `SV_ConnectionlessPacket`, `SV_GetChallenge`, `SV_Frame`,
`G_RunFrame`, gamestate/snapshot generation, and server GSC execution has no
equivalent call graph in this CODOL executable.

The native room path confirms the ownership boundary. `0x6E6F60` handles
`mmbook accepted`, `0x6E6BF0` constructs an outbound `mmstart` string, and a
room virtual call sends server-only commands such as `sv_resetServer`, `map`,
and `start_map_rotate_once` away from the client. Those tokens have no local
receiver. Gate A is therefore closed negatively for the QA ship client's
built-in hosting path: a real match requires an authoritative server
implementation. That implementation may initially share the injected process;
logical ownership of server state and protocol behavior does not require a
separate process.

## Reference suitability

| Reference | Use | Do not assume |
|---|---|---|
| s1x | Auth3 response shape, tickets, LSG framing, crypto, reply serialization | S1 endpoints, title IDs, tokens, service coverage or hardcoded keys |
| FourDeltaOne T5M / T5-DemonWare | Messaging service `6`, task `14/18` request order, and type-2 event `21` field order | Ayria MEEP transport, CODOL recipient-loop behavior, or the nested local `mmbook` command |
| BO2 PDB | Class layouts, byte-buffer serialization, legacy LSG service/task contracts | BO2 Auth is identical to CODOL Auth3 or all CODOL Tencent tasks exist |
| IW8 `bdTencent` source | Names and field order for service `0x47` tasks that match CODOL bytecode | 64-bit layouts, newer result classes, or every task number remained unchanged |
| CODOL i64 | Source of truth for request fields, state transitions, filenames and client result types | RTTI alone establishes server-side behavior |
| dwd3 | Hook pattern for observing completed publisher downloads | A backend implementation; it is only a dumper for later games |
| Ayria assets | Existing CODOL publisher/profile seed data | The plugin's in-process emulation is a complete DW3 server |

## Superseded planning note

The original standalone-backend milestone and ten-step implementation order
were planning guidance before the reconstructed Auth3/LSG/services and game
server skeleton existed. They are intentionally removed rather than maintained
as a second roadmap. The current deployment may keep logical control-plane and
gameplay-server boundaries in one process while those interfaces stabilize;
process separation is an architectural option, not a prerequisite for the next
protocol milestone.
