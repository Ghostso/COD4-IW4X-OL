# C1 shadow projection: server-fed direction overrides

Status: a concrete server-fed renderer input is identified; no Killhouse causation established. Offline read-only audit. No code, process, settings, tests or builds changed.

## Correction to earlier interpretation

The byte0xcf3e37 used beside `sm_enable` at0xa82f8d is a direction-override enable byte, not an established hardware capability. Its neighboring byte0xcf3e38 selects interpolation. Following their writers identifies direct server configstring consumers previously omitted from the fog/vision audit.

## Exact publication path

1. C1 configstring8 dispatches to0x465a70. That reads the string offset at0x6d0d150, relative to0x6d1370c. Empty calls0xa88220 and clears the color override. Nonempty parses three floats (`%g %g %g`) and calls0xa881f0, setting enable byte0xcf3e36 and RGB0xcf3e3c..44.
2. C1 configstring9 dispatches to0x465ae0. Empty calls0xa882c0 and clears direction enable0xcf3e37. The parser uses `%g %g %g %g %g %g %d %d` at0xc44630. Exactly three parsed values call0xa88230: enable/interpolation word becomes0x0001 and direction0xcf3e48..50 is copied. Other parse counts follow0xa88260, which writes enable/interpolation0x0101, two direction vectors0xcf3e48..5c and timing integers0xcf3e60/64. A valid timed payload therefore requires all eight fields; the receiver does not reject a malformed intermediate count on the observed branch.
3. View preparation0xa82f20 first selects a light using0xa882d0 (byte+0x12 of its input) and a64-byte light-record stride. After that,0xa82f8d combines direction override enable with `sm_enable` into `[0xcf4380]+0x4190c`. At0xa82fd1 it chooses either the direct direction or interpolation0xa82da0. Color override is applied at0xa8301c. Thus these configstrings affect the renderer before any spawned local player is required.

## Matching C1 script producers

-0x55ad40 accepts exactly three float arguments and formats them to configstring8 at0x55adbc..0x55adc0.
-0x55add0 is the adjacent zero-argument operation; its complete contract remains to be traced.
-0x55ae90 accepts exactly one vector, passes it through0x4090e0, and formats three floats to configstring9 at0x55af13..0x55af17.
-0x55af30 accepts exactly three arguments and is the adjacent direction operation; its remaining argument/timing contract is not yet established.

These functions appear in C1's builtin table at0xcd2f78/84/9c/a8, but names there are blank in this image. Do not claim exact GSC method names without correlating an independent enumeration.

## Native gap and next evidence

No CoDOL configstring constants or native script producers for the color/direction slots8/9 were found. Retained native fog slot9 is explicitly republished as C1 slot13 and must not be reused as the C1 direction slot. This is a concrete missing native renderer-control facility. It is not proof that Killhouse requests those overrides: searched local script overlays had no explicit sun control calls, and no captured active configstring8/9 values are available from the artifact frame.

The next discriminating passive capture is C1 received configstrings8/9 plus bytes0xcf3e36..38, vectors0xcf3e3c..5c, timing0xcf3e60/64, and the resulting selected-light direction/output flag during the exact artifact. If a required producer is found in shipped map scripts, implement its C1 slot and argument contract; do not guess a direction or globally enable the override. Downstream cascade matrix construction remains undecoded.
