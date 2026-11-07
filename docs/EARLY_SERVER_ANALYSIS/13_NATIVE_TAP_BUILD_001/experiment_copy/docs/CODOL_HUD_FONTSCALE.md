# Native HUD font-scale transitions

`changefontscaleovertime(seconds)` now records the displayed starting scale,
level time and duration for a native HUD element. Script assignment to
`fontscale` continues to set the destination. Interrupting a transition samples
its current interpolated size; times before its start clamp to the starting
size. Duration must be finite, positive and no greater than 60 seconds.

Evidence: local IW4 executable `D:/CoD/shx/iw4x.exe` registers the method at
0x5e1bf0. Its helper at 0x474560 interpolates from +0x18 to +0x14, using +0x1c
and +0x20 as start/duration. It rounds float milliseconds to the nearest integer
after adding 2^-30. Alpha0022 `docs/hudelem.md` identifies the same CoDOL fields
from C1's consumer at 0x449710 (timing at 0x4497ab/0x4497ae and starting scale
at 0x4497d9). CoDOL encodes both font sizes in tenths in a six-bit field.

The native IW3 HUD layout is unchanged. Separate owned transition records are
keyed by HUD slot. `HudElem_UpdateClient` copies each transition alongside its
native HUD element, so later changes or reuse of the original slot cannot
change already captured client state. C defaults, script reset, team-HUD
allocation and global HUD teardown reset the appropriate metadata.

The complete CoDOL HUD builder now accepts captured transition fields in its
semantic bindings. The server resolver retrieves them from live HUD objects or
client copies registered by the native update path. Unidentified detached copies
are rejected. The [native frame capture](CODOL_FRAME_HUD.md) now resolves the
HUD before detaching the native player state; the writer must consume that
sequence-matched capture before placing it in history. It must not reconstruct historical transition
state from a subsequently modified native object. The live snapshot writer is
still not integrated with the complete CoDOL player-state builder.

The dedicated test executes the real C HUD update path, checks interruption
from size 1 toward 3 halfway through, verifies CoDOL starting-size/time/duration
fields, invalid parameters, copy identity, reset and ownership after source
reuse. It passes with ASan/UBSan. The native VM fixture additionally calls the
method, assigns a destination, resets, invokes again and destroys the element.
Client-visible rendering in a connected match remains unverified.

The native VM initially exposed the retained IW3 font setter's 1.4 minimum.
C1's setter at 0x524970 permits positive smaller values. The CoDOL build now
uses a finite-positive setter, leaving representability checks to the wire
serializer. It does not retain IW3's 1.4..4.6 restriction. C1's diagnostic for
unusually large values is not reproduced by this setter.

Validation on 2026-09-08: the Linux suite passes; the final setter passes the
dedicated ASan/UBSan fixture; final Linux and Windows builds pass. The isolated native Bog VM
probe in `%TEMP%/sh1x-hud-fontscale-vm-final-probe` logs all four VM markers,
including `SH1X_HUD_FONTSCALE_VM_PASS`, completes initialization and quits.
The full-reference probe in `%TEMP%/sh1x-hud-fontscale-reference-probe` advances
to missing `weaponInheritsPerks` in `maps/mp/perks/_perks.gsc:155`. The existing
C1 client and Python lobby are untouched.
