
## Fog configstring translation — source written, unvalidated

Parent mapped retained G_setfog slot9 to C1 slot13 for initial gamestate and dynamic publication. Retained six-token exponential fog payload gains maxOpacity1 before milliseconds and a trailing0 for disabled sun extension; single0 reset remains0. Source: codol_sv_assets.c, codol_configstrings.h. G_InitGame calls G_setfog("0"); retained Scr_SetExponentialFog emits start,density,RGB,milliseconds. C1 dispatcher467480 routes13 to4667e0; C1 fog producer545fd0..54601e uses formatc57acc "%g %g %g %g %g %g %.0f 0" and publishes13. Usagec57ae8 confirms maxOpacity and sun arguments. C1 slot9 instead drives465ae0, a different renderer setting.

Remaining: retained GSC API still accepts only six arguments; native C1 setexpfog546040 accepts7/14. Implement the full API and sun representation next; this change only transports the already-existing producer correctly. Legacy votes13..16 still collide with C1 fog/timing/center; systeminfo/extensions/IWD mappings remain unreviewed. No builds/tests/runtime; no new missing-method count or match-entry claim. Both Claude implementation CLIs76420 and77704 verified live at this review.

## Extended setexpfog producer — registered source, incomplete mirrors

Added codol_script_fog.c and CODOL registry binding. Accepts actual IW4/C1 seven/fourteen-argument forms, plus retained six-argument compatibility path. Decoded C1 argument10 is vector;11begin,12end,13scale (usage string misleading). Emits measured8/17-token non-sun/sun format through native slot9 -> wire13; publication recognizes complete payload without adding legacy defaults. Clears native fog culling limits toFLT_MAX like C1 common helper546023. Updates existing RGB/start/half diagnostic dvars. Corrected density constant to C1c85470 promotedfloat0.6931471824645996. Registered source only; new opacity/sun diagnostic dvar mirrors still required, extreme FP/error-message parity unverified. No builds/tests/runtime or complete-GSC claim. IW4table79a6a4->5f41a0 confirms7/14; C1handler546040, helper545c30, actualargreads546267..54629b andformat545f34..54601e inspected.

Animation original worker terminalmax55,56reportedturns,cost3.7346455, no source/report. Verified CLI gone, then resumed SAME session3056ea48-a3ca-434b-8e20-96acc0e53189 for15turn bounded handoff, checkpoint immediately/no broad searches. Vehicle CLI77704 remains live. No worker output counted.

## Fog diagnostic dvars — source integration

Parent added registration of measured numeric C1 fog dvars1411..1420 at native G_RegisterCvars, with defaults/domains from52c737..52c8f5. Seven/fourteen-argument setexpfog now updates color/opacity/start/half then optional sun enable/color/direction/begin/end/scale before common validation. Seven-argument calls clear only sun-enabled, retaining other sun mirrors as C1 does. Native read-only flags use existing fog flags0x10c0, not blind C1 flag copies. C1 strings independently read for all ten IDs. Header codol_script_fog.h and g_sv_main.c lifecycle call added. Existing six-argument IW3 compatibility extension still delegates its old implementation and does not update the new numeric mirrors; this is a remaining compatibility-path difference. Extreme FP/libc/domain-clamping parity unverified. No builds/tests/runtime.

Animation finish CLI73256 and vehicleCLI77704 both verified live this turn, no output accepted. The absence of a checkpoint/report file is not completion or proof of a stopped worker.

## Unified six-argument fog compatibility path

Parent removed the early delegate to retained Scr_SetExponentialFog. Six-argument calls now use the same CoDOL producer as7/14, taking time fromarg5, defaulting opacity1, clearing sun-enabled and updating numeric diagnostic dvars. This resolves the stale numeric mirror difference reported in the prior entry. Registration remains one setexpfog binding; no new missing-method count. CoDOL now owns its culling and complete payload for all accepted forms. Legacy argument error wording/float rounding follows the CoDOL producer, not exact IW3 behavior. No builds/tests/runtime; match entry not verified.

Parent source inspection also reconfirmed SV_LoadLevel always publishes IW4OL extension CS2 plus IWD headers4861/4862; these still need a native CoDOL disposition/mapping, because fallback numeric passthrough is not a namespace translation. Legacy voting13..16 still collides with C1 fog/timing/center. Neither problem is fixed or suppressed in this pass. Animation finish73256/vehicle77704 remain verified live; no handoff accepted.
