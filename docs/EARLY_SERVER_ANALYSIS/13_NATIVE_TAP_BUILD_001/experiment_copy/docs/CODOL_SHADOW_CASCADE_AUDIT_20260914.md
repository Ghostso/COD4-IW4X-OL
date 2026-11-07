# Shadow/camera dvar publication audit

Status: no incorrect server override established. Offline C1/native review and existing-log inspection only; no client settings, processes, builds or tests changed.

## Server command mapping

Retained `PlayerCmd_SetClientDvar` in `_g_client_script_cmd_mp.asm` has a C1 conditional emitting `s name "value"`, replacing IW3 letter `v`. C1's `s` handler calls `0x468a00`, which recognizes specific names before taking its generic dvar-set path:

- `cg_objectiveText`, `cg_objectiveIcon`, `hud_drawHud`, `g_scriptMainMenu`;
- numeric name2611, `cg_unlockFlagSet`, `cg_vo_prefix`;
- other names flow through `0x468b41..0x468b46` to the generic setter0x625330.

This is name/value publication, not an integer dvar-index remapping. No translation from a UI dvar into an unrelated shadow-split setting was found in this receiver. The generic setter's complete permission/flag behavior was not audited here, so this does not claim every renderer dvar is writable by the server.

Current qconsole's observed `s` names are UI/objective/chat/summary fields plus `cg_thirdPerson` and `cg_fov`. The latter commands set thirdPerson0 and FOV65. No observed command names sm_enable, a shadowmap split, a depth-bias setting, or a near/far plane. The local script overlay search likewise found no explicit shadow/near-plane override. Logged commands are not proof that every earlier or future command is absent.

## C1 shadow-enable input

C1 registers literal `sm_enable` at0xa7c59a and stores its dvar pointer at0xcf41d4 (0xa7c5b7). View preparation at0xa82f8d..0xa82fb0 checks that dvar's current byte and a separate renderer capability/state byte0xcf3e37, then stores the combined result at `[0xcf4380]+0x4190c`. This establishes a local shadow-enable input; it does not identify a camera-near cascade split or a bad snapshot value.

Literal searches did not identify `r_znear`, `r_zfar`, `sm_sunShadowScale`, `sm_sunShadowCenter`, `sm_sunShadowSplitScale` or `sm_polygonOffsetBias` in this C1 image. Many C1 dvars use numeric names, so absence of those readable strings is not evidence that equivalent controls or cascades are absent.

## Outcome

The server's C1 `s` mapping is correct for the inspected path, and no captured server command supplies an incorrect shadow/camera-depth override. Camera-near cascade parameters and their exact C1 producers remain undecoded. No guessed numeric setting or bias change is justified. This bounded audit adds no causal explanation for the camera-dependent dark patch.
