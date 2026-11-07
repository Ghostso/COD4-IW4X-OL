# Killhouse live sun-override capture

Read-only process discovery found C1 PID90944. Exact code guards for the fog consumer and direction-override setter passed. Predicted commandTime was627467 before and after the read. The render world's name was `maps/mp/mp_killhouse_sh.d3dbsp`; camera origin was (3767.8098,-42.49794,104.63486).

`obj/killhouse-sun-overrides-90944-live.json` records:

- C1 configstrings8 and9: empty;
- fog13: `0`;
- naked vision1305: `"mp_killhouse_sh" 3000`;
- color, direction and interpolation override-enable bytes0xcf3e36..38: all0;
- override RGB, both direction vectors and transition times: all0;
- local `sm_enable`:1.

The received empty override configstrings and cleared override storage agree with C1's reset consumers. No active server sun-color/direction override mismatch was found. The default map-light path remains selected by these override controls; the map's final light direction was not independently captured, so this is not a numerical comparison against that direction.

An attempted read through `[0xcf4380]+0x419xx` did not validate as live renderer output: the supposed override flag was64 and the putative direction contained implausible tiny floats. These fields are retained only under `unvalidatedFrameMemory`, not interpreted as a malformed light or server defect. Renderer lifetime/frame ownership or effective layout requires further tracing before those addresses support conclusions.

No exact artifact-frame screenshot was correlated. No client input, settings writes, debugger attachment, process changes, tests or builds occurred.
