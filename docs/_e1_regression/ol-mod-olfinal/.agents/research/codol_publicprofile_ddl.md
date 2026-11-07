# CODOL Publicprofile DDL and XAsset Chain

> Status: evidence reference accumulated before and during the ol-mod migration. Stable ownership conclusions belong in `modules/backend.md`; commands below use current repository paths.

This note records the structure and call-chain facts that are confirmed by
CODOL runtime data, the CODOL IDA database, IW4x source, and the Ghosts server
PDB. It deliberately does not apply the BO1/BO2 `ddlRoot_t` layout to CODOL.

## XAsset lookup

CODOL's XAsset type-name table starts at `0xCE0EA0`. Entry `39` is
`structureddatadef`; entries `0..42` follow the IW4 ordering exactly.

The profile path is:

```text
Profiles2 Publicprofile serialize/deserialize
  -> DB_FindXAssetHeader(ASSET_TYPE_STRUCTURED_DATA_DEF, name, 1)
  -> XAssetHeader.structuredDataDefSet
  -> StructuredDataDefSet.defs[0]
  -> root StructuredDataType and offsetMap
```

Confirmed CODOL addresses:

| Address | Name | Role |
|---|---|---|
| `0x49E7D0` | `DB_FindXAssetHeader` | Looks up an XAsset pool entry and returns its 4-byte header union. |
| `0x6D7500` | `CODOL_ProfileBlob_Serialize` | Serializes public or secure profile data. |
| `0x6D7740` | `CODOL_ProfileBlob_Deserialize` | Restores the Blob, verifies CRC, then applies trailing fields. |
| `0x630750` | `StructuredData_CollectProfileFields_r` | Walks the DDL and collects properties flagged with `0x20`. |
| `0x6D7B20` | `CODOL_ProfileBlob_GetSerializedSize` | Computes the complete Profiles2 payload size. |
| `0x6D7D80` | `CODOL_ProfileBlob_UpdateCRC32` | Computes CRC32 over bytes `4..0x7FFF` and stores it at byte `0`. |

The IDA type and names above are saved in the editable CODOL i64.

## Cross-version evidence

IW4x defines `ASSET_TYPE_STRUCTURED_DATA_DEF = 0x27`, a four-byte
`XAssetHeader` union member named `structuredDataDefSet`, and the base
`StructuredDataDefSet`/`StructuredDataDef` layouts.

The Ghosts PDB independently confirms the same architecture:

```cpp
StructuredDataDefSet *StructuredDataDef_LoadDef(const char *name)
{
    return DB_FindXAssetHeader(
        ASSET_TYPE_STRUCTURED_DATA_DEF, name, 1).structuredDataDefSet;
}
```

Ghosts also links the asset through `Load_StructuredDataDefAsset` and runs
`StructuredData_PostLoad` after it enters the DB pool.

BO1 and BO2 use the newer `XAssetHeader.ddlRoot -> ddlRoot_t -> ddlDef_t`
family. That confirms DDL remains an XAsset, but those structures are not
layout-compatible with CODOL.

## CODOL structure extensions

All sizes below are for the 32-bit CODOL client.

| Type | CODOL size | Relevant difference |
|---|---:|---|
| `XAssetHeader` | `4` | Union containing `StructuredDataDefSet *`. |
| `StructuredDataDefSet` | `12` | `name`, `defCount`, `defs`. |
| `StructuredDataDef` | `60` | IW4's 52-byte definition plus `offsetMapCount` at `+0x34` and `offsetMap` at `+0x38`. |
| `StructuredDataStruct` | `20` | Base fields plus `logicalStride` at `+0x10`. |
| `StructuredDataStructProperty` | `24` | `validationFlags` at `+0x10` and an unresolved word at `+0x14`. |
| `StructuredDataIndexedArray` | `16` | Same base layout as IW4. |
| `StructuredDataEnumedArray` | `16` | Same base layout as IW4. |

The runtime `mp/playerdata.def` asset has:

- version `233`
- checksum `0xE32D50D6`
- logical data size `14426`
- one definition

The offset map is used by shipping code, not just by the diagnostic dumper.
For a primitive field the collector resolves its byte address as:

```text
buffer.data + definition.offsetMap[logicalOffset]
```

Boolean fields are the important exception. Their offset-map entry is a bit
offset, matching the shipping setter at `0x630060`:

```text
bitOffset = definition.offsetMap[logicalOffset]
byteAddress = buffer.data + (bitOffset >> 3)
bitMask = 1 << (bitOffset & 7)
```

`tools/profile/DumpCodolStructuredData.py` handles this distinction when resolving a
decoded Publicprofile offset.

## Publicprofile envelope

The Profiles2 object contains a DW Typed Buffer envelope followed by a Blob:

```text
U32 compressed
U32 profileFormatVersion
U32 CRC32
Blob compressed-or-raw-0x8000-bytes
flagged primitive fields...
```

After decompression, the fixed `0x8000` bytes contain:

```text
+0x0000  embedded CRC32
+0x0004  DDL player data (version begins here)
```

When `profileFormatVersion == 1` and the CRC matches, deserialization reads the
trailing primitive values and overwrites their mapped locations in the Blob.
This behavior matters when generating or editing a profile: changing only the
compressed Blob is insufficient for fields carrying `validationFlags & 0x20`.

In `mp/playerdata.def`, the flagged set contains 125 concrete values:

- `badge`, `cardBackground`, `cardIcon`, `cardNameplate`, and `cardTitle`
- `primaryBase` and `secondaryBase` for all 60 `weaponClasses`

Attachments, perks, `uiNotificationFlags`, and `uiStencilFlags` are not in this
trailing overwrite set.

## Public and secure profile transport

`CODOL_ProfileManager_ResetForUser` (`0x6D9DA0`) initializes exactly two
`dwProfile` objects for one user. Their mode field is set to `1` (`public`) and
`2` (`private`) respectively; each owns a separate `0x8000`-byte DDL buffer.
The mode selects `mp/playerdata.def` or `mp/playersecuredata.def` in the shared
serializer and deserializer.

The request pump at `0x6D8560` reaches the standard Profiles2 service through a
different remote-task constructor from the one used by most CODOL services.
This explains why an earlier scan of only `sub_A63F20` callers did not find
service `0x08`:

| Service/task | CODOL constructor | Meaning |
|---|---|---|
| `8/1` | `0xA5A890` | Get public profiles for a list of user IDs. |
| `8/2` | `0xA5A9D0` | Get the current user's private profile. |
| `8/3` | `0xA5A420` | Set the current user's public profile. |
| `8/6` | `0xA5A530` | Set private profile for an explicit user ID. |
| `8/7` | `0xA5A770` | Get private profile for an explicit user ID. |
| `8/8` | `0xA5A650` | Set public profile for an explicit user ID. |

The earlier runtime log contains six requests each for tasks `1` and `2`, and
seven requests for task `3`. It contains no task `4`, `6`, `7`, or `8`. Those
task-2 requests returned error `800` because no `Privateprofile` existed, yet
the completion path explicitly accepted that result as an empty/default
profile. Public changes, in contrast, triggered task `3` and were written back
repeatedly.

A later live validation created a native secure profile with this codec and
started the unmodified client twice. Profiles2 `8/2` returned error `0` with
the stored object on sequences `9`, `21`, and `22`; CODOL accepted the DDL
checksum/CRC/trailing validation fields and reached the lobby as level 1. This
confirms the read path and generated file format, but not a game-originated
private upload.

The private object's ready byte is also exposed to session/script metadata as
`secureProfileReady`. `CODOL_SecureProfile_MarkReady` (`0x6D27B0`), a
`dwLobbyEventHandler` callback, sets this byte independently of loading a
`Privateprofile` file. A successful lobby startup therefore does not prove
that secure DDL state was downloaded or persisted.

### Secure profile editor

`tools/profile/CodolProfile.py` reads and writes the native `Privateprofile` envelope
for `mp/playersecuredata.def` version `19`, checksum `0x8A317D69`. It does not
introduce a sidecar player-state format. The codec updates all three layers the
client validates:

1. the decoded `0x8000`-byte DDL buffer;
2. the embedded and outer CRC32 plus the optional zlib-compressed Blob;
3. the 36 scalar fields flagged `0x20`, serialized again after the Blob in DDL
   property order.

The tool exposes the recovered level, experience, prestige, rating, combat,
match, objective, and survival fields. Level `1..70` uses the native
`mp/rankTable.csv` thresholds, prestige `0..3` uses
`mp/prestigeTable.csv`, and `rankVersion` is kept at `4`. Changing level or
prestige therefore also selects a consistent experience range instead of
writing the displayed level in isolation.

Run the external editor with:

```text
python tools\profile\CodolProfile.py editor --port 8766
```

The local page edits Privateprofile progression/statistics, the verified
Publicprofile identity and character fields, and the reconstructed Marketplace
inventory. Profile replacements are atomic and retain `.bak` copies.

When CODOL is running, the editor does not call game functions on its HTTP or
Frida thread. It writes each backing file first, then queues work through exports
on `Alwaysoffline.Localnet32`. A hook on `CODOL_ProfileManager_Frame` consumes
the requests on the game thread in this order:

```text
Marketplace task 203 refresh
  -> Publicprofile operation 1 download
  -> Privateprofile operation 1 download
```

Each step is polled to its native completion callback before the next begins.
The first live validation completed all three against one running client with
DW error `0`; task 203 returned 32 inventory objects.

The secure profile is not the Marketplace ownership cache and does not hold the
equipped loadout. Entitlements remain in task `80/203` and the reconstructed
`Inventory.json` backing store; equipped weapons, attachments, character, card,
badge, and title remain in `Publicprofile`.

One archived-implementation mismatch remains useful historical context. The
preserved Ayria dispatcher aliases tasks `5` and `6` to deletion, while the
CODOL client constructs task `6` as `setPrivateInfoByUserID`. The
reconstruction now follows the client: task `5` deletes the current profile,
and tasks `6/7/8` read or write the explicit user's private/public file. The
server path is covered by two-user isolation tests, but task `6` still needs a
completed-match runtime capture to verify when and with which payload CODOL
actually invokes it.

## Loadouts are not the ownership inventory

The complete runtime root schema distinguishes equipped/profile state from
Marketplace ownership. `mp/playerdata.def` contains:

- 60 `weaponClasses`, each storing `primaryBase`, `secondaryBase`, attachments,
  perks, equipment, killstreaks, and a character index;
- 12 `characterClasses`, each storing an emote and nine integer slots;
- the currently equipped `badge`, `cardBackground`, `cardIcon`,
  `cardNameplate`, and `cardTitle`;
- 32 `shoppingCartSkus`, which are transaction/UI state rather than a durable
  entitlement collection.

It does not contain an inventory or entitlement array capable of representing
the Marketplace ownership set. CODOL keeps that set in a separate 20,000-entry
client cache populated by Marketplace service `0x50`, task `203`.

The secure schema is separate as well. `mp/playersecuredata.def` contains
`unlockFlags[4096]`, `unlockFlagsNew[2048]`, challenges, progression, and match
statistics. `CODOL_UnlockFlag_GetIndex` (`0x4A4B10`) maps names through
`mp/unlockFlags.csv`; `CODOL_UnlockFlag_MeetsValue` (`0x4A4CA0`) then compares
`unlockFlagsNew[index]` with a required rank/value. These are progression and
UI gates, not the `bdMarketplaceInventory` objects returned by task `203`.

The three interrupted character-creation captures provide a direct loadout
cross-check. They differ from one another at only two decoded bytes:

| Decoded offset | DDL path | Marcus | Wei | Cowboy |
|---|---|---:|---:|---:|
| `0x0F16` | `characterClasses[0].slots[0]` | `0x64` | `0x50` | `0xAE` |
| `0x257A` | `onboardCharacterID` | `0x64` | `0x50` | `0xAE` |

Their `weaponClasses[0]` data is identical and already contains the initial
weapon/attachment configuration. This proves that the chosen character and
default M4/M9 loadout configuration are written to `Publicprofile`; it does
not prove ownership of those item IDs.

### Native loadout write and upload path

The client has two staging and flush paths rather than writing every loadout
field through one function. Both paths end in the public profile dirty flag:

```text
weapon selection
  -> CODOL_Loadout_EquipWeapon (0x6C1E70)
  -> CODOL_WeaponSlot_Stage (0x5946C0)
  -> CODOL_WeaponSlots_FlushToPublicProfile (0x5948F0)
  -> CODOL_WeaponSlot_FlushToPublicProfile (0x592B10)

attachment selection
  -> CODOL_Loadout_EquipAttachment (0x6C2090)
  -> CODOL_WeaponSlot_Stage
  -> CODOL_WeaponSlots_FlushToPublicProfile

perk/equipment/streak/class changes
  -> 112-byte per-class staging records
  -> CODOL_Loadout_FlushToPublicProfile (0x594E90)

current character selection
  -> cached currentCharacterIndex
  -> CODOL_CurrentCharacter_FlushToPublicProfile (0x68A040)
```

`CODOL_WeaponSlot_FlushToPublicProfile` constructs these exact DDL paths for
each of the 60 classes:

```text
weaponClasses[i].primaryBase
weaponClasses[i].primaryAttach[0..5]
weaponClasses[i].secondaryBase
weaponClasses[i].secondaryAttach[0..5]
```

`CODOL_Loadout_FlushToPublicProfile` writes `name`, `perks[0..5]`,
`killstreaks[0..2]`, `lethal`, `special`, `tactical`, `wildcards[0..2]`,
`lethalDoubleAmmo`, and `tacticalDoubleAmmo`. The recovered three-entry field
table at `0xCDD504` is exactly `lethal`, `special`, `tactical`.

Identity display items use the same native DDL and dirty mechanism. The equip
dispatcher at `0x5C7460` maps item-definition categories as follows:

| Item category | Publicprofile field | Native setter |
|---:|---|---|
| `7` | `badge` | `CODOL_Identity_EquipBadge` (`0x5C75D0`) |
| `9` | `cardIcon` | `CODOL_Identity_SetCardIcon` (`0x590A00`) |
| `10` | `cardTitle` | `CODOL_Identity_SetCardTitle` (`0x590B40`) |
| `11` | `cardBackground` | `CODOL_Identity_SetCardBackground` (`0x590C80`) |

The three card setters validate ownership and fall back to `pci_default`,
`pct_default`, and `pcb_default` as appropriate. The outer equip dispatcher
marks the public profile dirty. `CODOL_Identity_RemoveUnavailableItem`
(`0x5C74E0`) applies the inverse path when an entitlement disappears, choosing
a valid fallback and marking the profile dirty again.

`cardNameplate` is also a validated Publicprofile field and has a native DDL
write path during profile repair, but it is absent from the normal purchasable
identity-item switch above. It should not be modeled as an ordinary SKU-driven
badge/card slot without additional evidence.

After either flush changes data, the client marks the public `dwProfile`
dirty at offsets `+0x9084/+0x9085` (manager offsets `+37012/+37013`). The
per-frame path is then:

```text
CODOL_PublicProfile_UploadPoll (0x592350)
  -> CODOL_Profile_TryUpload (0x6D8810)
  -> CODOL_Profile_StartOperation(profile, 2)
  -> CODOL_Profile_RequestPump
  -> bdProfiles_SetPublicInfo
  -> Profiles2 service 8 task 3
```

Operation completion clears `dwProfile + 0x9085`. This closes the native
persistence loop: equipped weapons, attachments, class items, character and
identity fields belong in `Publicprofile`, while Marketplace task `203`
remains the separate ownership/entitlement source.

The startup ordering was dynamically closed on 2026-08-07. The task `203`
response contained 115 inventory objects, but the old reconstruction polled
the completed `bdRemoteTask` after `CODOL_Marketplace_OnInventoryComplete` had
already consumed it. The count at `bdRemoteTask +0x24` was then `0`, and the
hook incorrectly called `CODOL_Marketplace_FinalizeInventory(1, 0)` a second
time. The client consequently downloaded the original 1982-byte profile,
repaired it against an empty cache, and uploaded a 1943-byte replacement via
Profiles2 `8/3`; request payload and stored file were byte-identical with
SHA-256 `37FAEAA...24A33`.

The reconstruction now observes the return boundary of the native finalizer
instead of calling it. In clean PID `16296`, `bdRemoteTask_GetNumResults`
(`0xA44CB0`) supplied `115` to the single native finalizer before Profiles2
`8/1` was released. The restored profile remained 1982 bytes with SHA-256
`DC9AAE6...D4464B`, and the bounded launch capture contained no `8/3` request.
This proves the inventory/profile ordering fix; it does not prove that a
frontend-only staged character or weapon selection was flushed before exit.

The subsequent PID `27808` run proved only the low-level upload path, not the
normal selection contract. `0x68C580` has one caller at `0x5F01A0`, which also
writes `onboardCharacterID` and onboarding telemetry. The normal Scaleform
registration `CL_SetDefaultCharacter/CL_SetCurrentCharacterID` is handled by
`0x69C850` and forwards to `CODOL_CurrentCharacter_SelectItem` at `0x689FF0`
with custom `EDI=itemId` ABI. That selector finds or creates the character
slot, updates and flushes `currentCharacterIndex`, and refreshes presentation
without changing onboarding state. `CodolMatchFlow.py --character-index` now
uses this normal selector before polling `CODOL_PublicProfile_UploadPoll`.

Clean-start timing then identified a separate lazy-cache race. At about 4.8
seconds, before Publicprofile was parsed, the native UI called
`CODOL_CurrentCharacter_GetIndex` (`0x68A0E0`) and changed the cache at
`0xCD7E3C` from `-1` to `0`. At about 13.2 seconds the profile and inventory
were complete and Alice item `10362` was available, but later character init
continued to reuse the cached zero. The backend hook now resets this cache to
`-1` only after a successful public-profile download completion
(`kind=1, operation=1, succeeded, errorCode=0`). Clean PID `31148` then read
`currentCharacterIndex=3` without a character override; the following booking
reported `current/prepared/registered=3` and class masks `31/31`. Runtime
evidence is in `20260807_character_startup_timing_v1` and
`20260807_current_character_cache_fix_v1`.

The runtime availability decision is now traced precisely:

```text
CODOL_ItemAvailability_Query (0x695BC0)
  -> reject-list lookup
  -> Marketplace task-203 inventory cache lookup
     -> CODOL_ItemAvailability_FromInventory (0x695A80)
  -> CODOL_Item_IsLocallyAvailable (0x695A10)
     -> Publicprofile onboardCharacterID
     -> CODOL_DefaultAvailableItems_Contains (0x706700)
```

`CODOL_DefaultAvailableItems_Init` (`0x7052F0`) builds the latter table after
loading `mp/coMarketplaceItems.csv`. It resolves item definitions by name and
stores up to 100 positive IDs. The directly recovered default names are:

| Group | Client item-definition names | Recovered item IDs |
|---|---|---|
| Starter primaries | `m4_mp`, `vector_mp`, `l86_mp` | `10001`, `10010`, `10015` |
| Starter secondary | `m9_mp` | `10049` |
| Starter attachments | `red_normalm4`, `for_gripvtlong2m4`, `red_reflexvector`, `sra_riflelaservector`, `red_reflexl86`, `sra_riflelaserl86`, `red_rmrm9` | `20379`, `20782`, `20416`, `21037`, `20394`, `25075`, `25684` |
| Perks | `specialty_blindeye`, `specialty_scavenger`, `specialty_tactical_mask` | `60043`, `60040`, `60137` |
| Streaks | `uav`, `predator_missile`, `helicopter` | `60076`, `60080`, `60083` |
| Equipment | `frag_grenade_mp`, `smoke_grenade_mp`, `tabun_gas_mp`, three themed smoke variants, `defaultknife_mp` | `60000`, `60005`, `60003`, `60128`, `60144`, `60162`, `12243` |
| Character items | `cha_INFbaseA`, `cha_INFbaseB`, `cha_INFbaseE`, `cha_COWprestigeA`, `cha_MOUveteranA`, `cha_GREbaseA`, `cha_ACUbaseA` | `545`, `789`, `792`, `686`, `1945`, `612`, `592` |
| Wildcards | all eight `wild_*` class-building wildcards | `60178` through `60185` |
| Identity defaults | `pci_default`, `pcb_default`, `pct_default` | `30059`, `30060`, `30061` |
| Client-only/default helpers | `ret_default`, `sco_none`, `token` | no product mapping for the first two; `token` is `50000` |

This is the concrete reason the initial weapons and attachments remain usable
without corresponding task-203 entitlement records: they are explicitly
whitelisted by the title. The secure unlock flags may gate later progression
items, but they are not consulted by this fallback. Conversely, item-definition
`flags & 2` in `0x695A80` only converts an already granted inventory record to
non-expiring availability; it does not grant the item.

`Inventory.json` is therefore a reconstruction backing store, not a recovered
CODOL or Project Nova file format. It was introduced by this repository in
commit `91f9d73`; none of the preserved Ayria distributions contains that
filename. The native part of the current implementation is the DW task `203`
request/response and `bdMarketplaceInventory` wire object. A future SQLite or
other service-side database can replace the JSON without changing the client
protocol or moving ownership into `Publicprofile`.

## Onboarding state

The onboarding decision does not use an opaque reserved byte. It follows a
normal DDL bool-array path:

```text
CODOL_IsOnboardComplete (0x5C36F0)
  -> CODOL_UINotification_GetIndex("onboard_complete") (0x5C6350)
     -> mp/uiNotifications.csv column 0 -> column 1
  -> CODOL_Profile_GetIndexedBool("uiNotificationFlags", index) (0x5953A0)
     -> StructuredData path walker
```

The runtime StringTable assigns `onboard_complete` index `87`. With the bool
bit-offset rule above, this is decoded Publicprofile byte `0x1126`, mask
`0x01`. The archived profile has `0x1126 == 0x21`, which means:

| Decoded offset | Bit | DDL path | StringTable meaning |
|---|---:|---|---|
| `0x1126` | `0x01` | `root.uiNotificationFlags[87]` | `onboard_complete` |
| `0x1126` | `0x20` | `root.uiNotificationFlags[92]` | `un_career` |

The other two previously suspected bytes are unrelated accompanying state:

| Decoded offset | Value | DDL path | Meaning |
|---|---:|---|---|
| `0x111D` | `0x01` | `root.uiNotificationFlags[15]` | `un_marketplace` |
| `0x2583` | `0x02` | `root.uiStencilFlags[41]` | legacy input-binding migration completed |

The `uiStencilFlags[41]` interpretation is independently confirmed by
`0x463270`, which reads the flag before migrating an old binding layout and
sets it after migration.

The three profiles captured immediately after character selection have zero
DDL version/checksum bytes, while the archived profiles that skip onboarding
carry version `233`, checksum `0xE32D50D6`, and the flags above. Those partial
profiles are useful evidence for the interrupted creation flow, but they are
not valid templates for a completed account. The archived profile remains the
known-good seed until the full new-account server workflow is reconstructed.

## Diagnostics

`tools/profile/DumpCodolStructuredData.py` reads the live XAsset and exports enums,
structs, arrays, flags, and the offset map. CODOL definitions use a 60-byte
stride; using IW4's 52-byte stride would only appear to work while an asset has
exactly one definition.

The `mp/uiNotifications.csv` StringTable used for the onboarding mapping was
dumped from the same running build under the untracked diagnostics directory.

The current verified dump is intentionally untracked under:

```text
diagnostics/structured_data/20260729_080915
```
