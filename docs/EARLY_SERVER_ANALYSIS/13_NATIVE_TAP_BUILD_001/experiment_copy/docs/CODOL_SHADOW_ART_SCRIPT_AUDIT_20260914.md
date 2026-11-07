# Killhouse art-script and shipped vision audit

Status: offline source/asset/binary audit; no causal defect or justified renderer change established. No tests, UI input, process changes, or extra-zone loading performed.

The current native qconsole records lowering `maps/mp/_art.gsc` (6819 bytes) and `common_scripts/_artcommon.gsc` (4874 bytes). These match the IW4 vendor files in alpha0022. `_load::main` invokes `_art::main`. The latter's main and tweak loop bodies are developer blocks (`/# ... #/`). Even if developer execution is enabled, the initializer supplies `scr_art_tweak=0` when unset, and the mutation loop waits while that dvar remains0. Fog sliders are converted and sent only after that gate. No current log evidence establishes enabling the gate or the `ART TWEAK ENABLED` path. The presence of a compiled art file alone is therefore not evidence that it overwrote scene fog or shadow settings.

The alpha0022 Killhouse level-script overlay calls the map FX, standard load chain, minimap setup and team assignments. It supplies no authored exponential fog or sun override. Its provenance explicitly says no original level GSC was available. An independent rawfile extraction from cached base/patch Killhouse and common-gametype zones found no matching `maps/mp/mp_killhouse_sh.gsc`, `maps/mp/_art.gsc` or `common_scripts/_artcommon.gsc` assets in those checked zones. This does not claim no such source exists elsewhere.

The base Killhouse zone does contain the actual `vision/mp_killhouse_sh.vision` (372 bytes), extracted unchanged to `obj/shadow-art-audit/mp_killhouse_sh-vision_mp_killhouse_sh.vision`. It uses numeric names511..531, not literal IW4 renderer names. C1 has the corresponding parser metadata at0xcd67d8, stride12: name pointer, destination offset, type. Names511..525 map to offsets0..0x38; vector names526/527/528 map to0x3c/0x48/0x54; names529/530/531 map to0x60/0x64/0x68. Types0/1/2 distinguish boolean/scalar/vector entries. Parser references are0x479559 and0x47970e. Consequently these shipped names are valid C1 fields, not an unrecognized IW4 vision file silently falling back on defaults.

For example, the authored vectors526..528 are `1.04633 1.1 0.85`, `1.02806 0.95242 0.813787`, `1.09073 0.975186 0.887041`. Fields530/531 are both1. Their C1 dvars register at0xa7ba41/0xa7ba72, store pointers0xcf4118/0xcf4140, and feed view preparation at0xa82169/0xa82178. Their semantic labels were not independently established here; calling them shadow strength, exposure or depth limits would be speculative.

The already captured native naked-vision command references the correct shipped `mp_killhouse_sh` asset. This audit verifies asset existence and parser recognition, not the final blended vision values at the exact dark patch. It supplies no basis for replacing the map's art settings with another map's settings, fabricating fog/sun values, or loading unrelated zones. The remaining distinct observation is the final active blended C1 vision/view preparation state during the exact artifact; numeric field semantics and downstream rendering remain to be traced before changing a producer.

## Follow-through: fields530/531 resolved

Offline tracing continued through the complete C1 function0xa82140, called by view preparation0xa82630 at0xa8280c. It implements three branches:

- If dvar pointer0xcf41a4 (numeric1502) is disabled, output view+0x268/+0x26c becomes1/1.
- Otherwise, when pointer0xcf4264 (numeric529) is enabled, output comes from numeric530/531 dvars at pointers0xcf4118/0xcf4140.
- When numeric529 is disabled, output comes from input scene parameters+0x7c/+0x80.

This exactly matches OpenBLOPS `R_SetupCharacterPrimaryLightScale` in `Engine/Renderer/gfx_d3d/r_scene.cpp`: hero-lighting enable, primary-light tweak enable, diffuse/specular tweak strengths, otherwise the scene's character-primary-light scales. The C1 field values and branch relationships were traced directly; T5 offsets were not copied. This identifies530/531 as character primary-light diffuse/specular scale and529 as its tweak selector. These fields are not camera near-plane or world-shadow cascade limits. The shipped Killhouse values530=531=1 request neutral character scaling.

A passive follow-through probe rediscovered C1 PID102052 and verified bytes at0xa82140, but predicted commandTime was0. `obj/killhouse-vision-viewprep-102052.json` records the inactive result, and the probe skipped stale dvar/view interpretation. Consequently no live final blend mismatch was established. This resolves the specific previously proposed numeric-field lead without guessing a change; it does not exclude other vision fields or the world renderer.
