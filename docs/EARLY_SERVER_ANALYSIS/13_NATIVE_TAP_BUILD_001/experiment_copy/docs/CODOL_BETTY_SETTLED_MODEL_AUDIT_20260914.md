# Settled Betty model capture

Status: concrete script-mover model-selector defect found and source corrected; parent owns build/runtime verification. No tests, input or process changes performed.

The deployed script replaces the settled missile with a `script_model`, sets `projectile_bouncing_betty_grenade`, assigns ground-normal-derived angles, creates a separate pickup origin25 units above it, then deletes the original missile. The separate pickup explains why a prompt alone does not establish a rendered model.

Passive C1 PID102052 capture at commandTime72809, active Killhouse, found centity106 containing type6, flags0, model slot753 resolving to that projectile name, origin(3862,-869,4), angles(0,0,0), scale1, and DObj map entry0. This alone would not prove a model-construction failure: centity backing storage can outlive active snapshot membership after a map restart.

Native correlation used the actual running `codol_dedrun_next.exe` PID103388, module base0xf50000, PE preferred base0x400000, symbol `_g_entities`0x11b21a04 and source-verified entity stride0x274. Entity106 was entirely zero, including inuse0, model0 and origin0. Therefore the captured client Betty was historical storage, not a current deployed entity. Artifacts: `obj/betty-client-model-102052.json` and `obj/betty-native-103388-106.json`.

C1 mover consumer0x43fc80 excludes eFlags0x10 and looks up the entity's DObj at0x43fccd..0x43fcf3. A null DObj enters the brush path, which only handles actual inline brush models. This explains why a genuinely active non-brush mover without a DObj would be invisible, but does not establish why a future/current Betty would lack one. The stale candidate must not be used to justify a renderer or snapshot patch. Correlation needs a currently in-use native mine before interpreting its received/model state.

The suspected missing relink after `setModel` is excluded by the actually registered implementation: `src/scr_vm_main.c` binds `setmodel` to retained `ScrCmd_SetModel`; `_g_scr_main_mp.asm` invokes `G_SetModel`, then `G_DObjUpdate`, then tail-jumps `SV_LinkEntity` with the same entity argument. `G_SetModel` alone writes the model handle at+0x168, but the GSC wrapper performs both update and relink. Betty does not need `makeUsable` on its visible model merely to obtain this relink. No speculative extra link operation was added.

## Proven constructor selector mismatch and fix

C1's DObj-update dispatch at0x443ba0 uses data table0x443c4c; its type6 entry0 routes through0x443bbe to0x43e7d0. For type6,0x43e80f loads centity+0x140, which is entityState+0x5c. The ordinary mover branch (no special previous subtype at centity+0xcc and no weapon-like selector at centity+0x14c) reaches0x43e974 while retaining that model selector in ECX. At0x43e97a it resolves `[decoded cgs +0x1b4 +selector*4]`. The cgs pointer uses index0x6c3d2b0 and XOR0x3958bead. It then calls constructor0x443610. That constructor explicitly exits for a null model at0x443663..0x443665; a missing animation tree is allowed and creates an unanimated DObj.

The general-entity branch instead loads centity+0x17c (entityState+0x98) at0x43e96e before joining the same cache lookup. The no-DObj brush renderer separately uses+0x98 as its inline-model selector. Thus the earlier assumption that all model entities share+0x98 was incorrect: a valid Betty model name in configstrings and+0x98 does not feed the ordinary type6 DObj constructor.

`CODOL_OverlayEngineModelEntity` previously published every non-brush model to+0x98 and never wrote+0x5c. It now writes+0x5c for ET_SCRIPTMOVER and+0x98 for ET_GENERAL. The dedicated brush producer remains unchanged at+0x98. Animation entry+0x60, tree+0x94 and animation timestamp+0x6c are untouched. This is a native state-producer correction, not a model substitution, visibility override or client hook.

## Later live attempts

The next session revalidated native PID99340/modulebase0xc0000 and client PID102092/base0x400000. A capture at commandTime96574..96585 found no simultaneously in-use native type6 with a resolved Betty client name. Native player0 was initially valid, confirming the entity base; a later bounded60-sample pass observed commandTime0/player0.inuse0 throughout despite advancing native level.time. Captures are `obj/betty-live-99340-102092.json` and `obj/betty-passive-99340-102092-samples.json`. These do not validate the fix's rendered behavior. The fix rests on the direct C1 constructor's selector and the mismatched native producer, not the earlier stale DObj observation.
