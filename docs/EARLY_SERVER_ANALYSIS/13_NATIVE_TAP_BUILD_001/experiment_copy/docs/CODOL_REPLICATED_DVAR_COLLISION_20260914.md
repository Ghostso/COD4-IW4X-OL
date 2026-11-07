# C1 replicated-dvar collision

Status: native producer corrected and source reviewed. Parent owns build and runtime validation. No process changes, tests or builds performed for this audit. This establishes malformed client input; it does not establish the cause of the reported dark wall region.

## Captured corruption

`obj/killhouse-replicated-dvars-90944.json` is a passive C1 capture from PID90944, map `maps/mp/mp_killhouse_sh.d3dbsp`, commandTime220837 unchanged across the read. The block contains178 pairs. C1 dispatcher0x46740a..0x467419 and consumer0x466020 pair names24..223 with values224..423 and stop at the first empty name.

Compared with the mounted `code_post_gfx_mp.zone` table `mp/constConfigStrings_mp.csv`:

| Name slot | Name | Value slot | Shipped value | Captured value |
|---|---|---|---|---|
|53|bg_viewKickScale|253|0.25|250|
|54|bg_weaponBobAmplitudeDucked|254|0.045 0.025|1|
|55|bg_weaponBobAmplitudeProne|255|0.02 0.005|1|
|56|bg_weaponBobAmplitudeRoll|256|1.5|1|

Names125..128 were also replaced: `player_breath_gasp_time`, `player_breath_hold_lerp`, `player_breath_hold_time`, `player_breath_snd_delay` became `cg_hudGrenadeIconMaxRangeFrag`, `cg_drawCrosshairNames`, `cg_drawCrosshair`, `cg_drawTalk`. Their correctly paired C1 values325..328 remained the old breathing values1,1,4.5,1.

The log establishes which producer corrupted both regions:

```
d 125 cg_hudGrenadeIconMaxRangeFrag
d 253 250
d 126 cg_drawCrosshairNames
d 254 1
d 127 cg_drawCrosshair
d 255 1
d 128 cg_drawTalk
d 256 1
```

Those pairs have separation128, not200. The native `bg_viewKickScale` registration is not the source of250; its default0.2 and maximum10 already contradict that interpretation.

## Producer and correction

`SV_PreFrame` and `SV_SaveSystemInfo` call `SV_SetConfig(20,128,256)`. Its callback selects CVAR_CONFIG256 and calls `SV_SetConfigValueForKey`. The retained allocator searches the IW3 name range and writes values at `start + max + slot`; `SV_SetConfigstring` then broadcasts those indices unchanged. In contrast, `CODOL_RefreshServerDvars` is a separate correctly paired CVAR_SYSTEMINFO8 path. Changing its defaults would not fix this defect.

The native route in `SV_SetConfigValueForKey` now sends this semantic dvar operation to `CODOL_PublishReplicatedDvar` in `src/codol/snapshot/codol_replicated_dvars.c`. It finds an existing name in the effective C1 bank (explicit overrides, otherwise inherited constants), preserves its slot and spelling, or appends at the first empty name. It publishes the corresponding value at224+slot. Names are never allocated by a value-string lookup.

Both allocations and the merged client pool are validated before mutation. New values are sent before exposing new names so C1's complete-bank reapplication cannot apply an old slot value to the new dvar. That intermediate pool cannot exceed the validated final pool: the remaining operation adds only the new name. Existing-name updates have only one changed string. The normal C1 bank owns both values, so later gamestates and late joiners receive the same state as live clients. Full200-slot banks fail explicitly rather than writing into another range.

Before map constants exist, publication is deferred. `SV_SpawnServer` installs inherited constants before its unconditional `SV_SaveSystemInfo`, which republishes all CVAR_CONFIG variables before SS_GAME regardless of modified flags. Thus allocation never masks the inherited prefix by running early. This does not disable replication or special-case the four observed names.

## Limits and other differences

The captured renderer dvars `r_diffuseColorScale`, `r_lightGridContrast`, `r_lightGridEnableTweaks`, `r_lightGridIntensity`, `r_specularColorScale`, `r_ssaoBlurRadius`, `r_ssaoDebug`, `r_ssaoDownsample`, `r_ssaoPower`, `r_ssaoStrength`, and `sm_sunShadowScale` match their shipped table values. The corruption affects weapon view kick, bob and breathing/client HUD configuration; a direct causal link to the camera-following dark region remains unproven.

Existing malformed client configstrings require a fresh gamestate from the corrected server. No attempt was made to overwrite running client state or guess original values outside the normal inherited table. Runtime verification should observe correct name/value pairing, preserved slots53..56 and125..128, and whether the user-visible symptom changes.

## Post-deploy capture attempt

After the parent deployed the corrected native executable, the passive probe rediscovered C1 PID90944 at the expected executable path and matched the exact consumer0x466020 instruction guard. Its predicted commandTime was0, so the probe did not interpret the map or potentially stale configstrings. `obj/killhouse-replicated-dvars-90944-postfix.json` records this inactive result. Corrected live pairing and any visual effect remain unverified until an active match provides a fresh gamestate.

A subsequent process revalidation found no C1.exe process. No historical PID memory or stale captured bank was interpreted as post-fix state. A bounded retained-assembly configstring call-site review found no additional proven shadow input: retained fog slot9 is explicitly republished to C1 slot13, and the active GSC vision bindings select the native C1 producer. One separate, unmodified scoreboard lead was reported to the parent: `ClientEndFrame_140` still publishes team scores through retained slots4/5, while the documented C1 score bank is5/6. Its intermission execution and C1 consumers require review; it is not evidence explaining a spectator dark region.

## Successful live verification

The later capture `obj/killhouse-replicated-dvars-102052-postfix.json` rediscovered C1 PID102052, validated the exact consumer instruction guard, and confirmed active Killhouse state. commandTime107445 and all424 captured string offsets were unchanged across the read. It contains190 contiguous pairs.

- Slots53..56 retain `bg_viewKickScale`, `bg_weaponBobAmplitudeDucked`, `bg_weaponBobAmplitudeProne`, `bg_weaponBobAmplitudeRoll`, with restored values0.25, `0.045 0.025`, `0.02 0.005`,1.5.
- Slots125..128 retain their original breathing names, paired with values325..328=1,1,4.5,1.
- HUD names `cg_hudGrenadeIconMaxRangeFrag`, `cg_drawCrosshairNames`, `cg_drawCrosshair`, `cg_drawTalk` now occupy210..213, correctly paired with410..413=250,1,1,1.
- Other appended native dvars occupy202..209: `bg_bobMax`, four `bg_bobAmplitude*` names, and three inertia names. This demonstrates the generic allocator rather than a special-case fix for the four HUD names.

The native CVAR_CONFIG path also now publishes matching existing names, including team/score colors, grenade indicator speed, footstep/move thresholds and UI fields. These are actual value updates, not evidence of a shifted channel. No default values were changed by this repair.

All names beginning `r_` or `sm_` have the same paired values as the earlier captured bank. The capture is spectator state pm_type5: origin(3492,-238,224), camera(3492,-238,232). This records camera state only; it is not a standing-player height measurement or visual isolation of the dark region. Corrected configstring pairing is now verified in C1, while any effect on the reported shadow artifact remains unproven.
