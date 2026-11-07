# Shadow artifact: vision/fog publication audit

Status: no causal mismatch established. Offline C1 disassembly, native source review and a passive client read only. No gameplay edits, tests, input, settings changes or restarts.

## Vision publication and receiving contract

Native `codol_script_vision.c` publishes global sets into C1 configstrings1305..1309, as `"name" durationMilliseconds`. C1 dispatcher `0x4675e6..0x46766c` explicitly routes1305..1310 to `0x466b80` with type0..5. The receiving helper selects the corresponding configstring pointer, tokenizes the first token and copies at most63 characters to a64-byte global vision-name slot (`0x466c41..0x466c64`). The native format and slot selection agree with that consumer.

The current qconsole log contains the following naked-vision sequence for Nucleur, at lines11440,11441 and11447: `"mp_killhouse_sh" 3000`, `"mpIntro" 0`, `"mp_killhouse_sh" 3000`. The native script overlay `_gamelogic.gsc` explicitly makes these transitions around intro/match startup (lines976,985,1018..1032). This identifies actual script producers rather than an inferred rendering override. It does not establish the contents or blended result of the referenced vision assets at the exact artifact frame.

## Fog and sun-fog contract

`CODOL_RefreshServerMapConfigstrings` publishes retained map slot9 as C1 slot13. `CODOL_Scr_SetExponentialFog` stores the extended payload in native slot9: start, density, RGB, opacity, duration, sun-enabled, followed by sun RGB/direction/fade angles/scale when enabled. The refresh path preserves the full8/17-token payload, and expands old six-token payloads with opacity1 and sun-disabled0.

C1 dispatcher `0x467480..0x467489` sends slot13 to `0x4667e0`. That consumer reads its offset from `0x6d0d164`, relative to the configstring text base `0x6d1370c`; it parses ordinary and optional sun-fog fields and calls `0xa88080` to configure them (`0x466aca..0x466b15`), then `0xa88130` with transition timing. This is a fog/sun-fog input path, not evidence of a server-set sun-shadow projection matrix. No incorrectly routed fog slot was found.

## Passive read and remaining uncertainty

Process discovery found C1 PID90944. An exact fog-consumer code guard passed, but predicted commandTime was0. Fog13, ambience1300 and visions1305..1310 were empty in that inactive client. `obj/killhouse-shadow-configstrings-90944.json` records the read. These empty strings are not evidence that the connected gameplay scene lacked vision/fog; the prior active scene-brush capture is a separate earlier sample.

One independent pre-existing protocol gap remains in source: `SV_SetClientStat` (`src/sv_client.c:3233`) still sends reliable letter `N` with numeric stat arguments. C1 uses `N` for the naked per-player vision transition, already documented in `codol_script_vision.c`. The searched current log contains no corresponding `N` command establishing that this path ran during the reported artifact. Do not attribute the spectator wall patch to that collision without an actual call/command trace; do not invent a replacement stat letter.

The evidence supports correct global vision routing and fog configstring selection. The missing observation is an active exact-artifact capture of received configstrings plus the blended C1 vision/fog state. No server-driven vision/sun/fog defect has been demonstrated.
