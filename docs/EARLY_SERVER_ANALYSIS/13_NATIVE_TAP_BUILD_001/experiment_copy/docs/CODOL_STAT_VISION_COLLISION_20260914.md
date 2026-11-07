# Legacy stat / C1 vision command collision

Status: confirmed protocol collision, not an established cause of the reported shadow artifact. Read-only source/binary audit; no gameplay changes, builds or tests.

## Reachable native producers

- `src/scr_vm_main.c:819` registers `setstat` to `PlayerCmd_SetStat`.
- `src/scr_vm_functions.c:390` validates a player receiver, two arguments and legacy numeric indices, then calls `SV_SetClientStat`.
- `src/sv_client.c:3233` modifies the old byte/long stats array and, when changed, emits `N index value` without a C1 conditional.
- `src/asmsource/pluginexports.asm:71` exposes the same function as `Plugin_SetStat`. Retained `GScr_SetStat` also calls it, although current native registration uses the C implementation.

The C1 receiver at `0x469bed..0x469c21` copies command argument1 into the naked vision name, converts argument2 to an integer transition duration and calls `0x47a1e0`. Thus `N 2000 5` would be interpreted as vision name `2000`, duration5ms. No alternate stat letter was identified.

## Selected class / perk call paths

A whole-word search of the local `scripts/codol` overlay found no `setstat` call. Challenge functions such as `_missions.gsc`'s `ch_setState` call `setPlayerData`, not `setstat`. Native `setplayerdata` is registered separately to `CODOL_Scr_SetPlayerData`; its structured-schema public write path calls `CODOL_BeginProfileUpdate`, marks the changed field bytes and seals the session profile. It does not call `SV_SetClientStat` or emit `N`.

This excludes a direct call in the searched overlays, not all possible shipped script assets or external plugins. The observed Killhouse logs supplied no actual `N` stat command correlated with the wall patch. A plugin or other script can still reach the legacy export.

## C1 profile synchronization evidence

The prior profile investigation is preserved in `obj/claude-workers/profile-updates-report.md` and the native `codol_profile_updates.h` contract. The following decisive check was independently re-read from C1:

`0x592fa6` compares connection state at0x16fc2e8 with3. At or above3, it logs `Refusing to accept online stats because we are connected to a server` and returns at0x592fc3. This is inside the account-service public-profile completion callback at0x592f30. That is positive evidence against using this receiver to replace live in-match playerdata.

Public script writes have a different verified producer: C1 record at client+0x6200d, per-byte dirty map+0x6a009 and flag+0x6b009. Native code reproduces that tracking. The bridge from this dirty record to account-service persistence has not been established or implemented. Existing client upload chunks and `statResponse` acknowledge client-to-server upload; they are not a server-to-client update format. Service writeback candidates and their unresolved buffer relationship are documented in the prior report.

## Concrete correction boundary

Prevent `SV_SetClientStat` from emitting the IW3 `N` command to C1 clients. This is a proven incompatible producer and needs correction even though it has not been tied to the shadow artifact. It must not be replaced with a guessed command letter or a reversed upload packet.

Meaningful C1 stat support must use the structured profile schema and verified account-service persistence. Arbitrary IW3 numeric stat indices do not establish CoDOL field identities. Until explicit mappings and lifecycle are implemented, neither a silent local-array update nor an unsupported-error branch counts as completed C1 stat support. Keep this missing compatibility work visible rather than reporting that suppression alone implements synchronization.
