# Killhouse authored shadow correction

Integrated and built from the actual IW4x map script recovered from the user's
`D:/CoD/iw4x_development/iw4x/iw4x_00.iwd`. Archive and source hashes are in
`obj/iw4x-map-audit/manifest.json`. The authored script sets
sm_sunSampleSizeNear to 0.35 with the explicit shadow-error correction comment.

C1 uses numeric dvar 1617: registration 0xa7c759..0xa7c79a, pointer 0xcf41f8,
default 0.25, bounds 0.015625..32. Renderer consumer 0xa853f1/0xa85404 performs
the matching shadow sample-footprint calculation. A friendly server-only
setdvar would not update that client field.

The new native script function publishes 1617 through the existing C1
replicated dvar bank. Killhouse's native map script requests 0.35. After an
owned override, server configstring reset schedules baseline 0.25 into the
next initialized map bank, before map GSC; another Killhouse load overwrites
that same slot. This preserves the new map's value for late joins and avoids
relying on an old-map reliable command surviving teardown. The baseline is
C1's registration/viewer-hide value, not an arbitrary saved user preference.

Build exit 0, deployed both native executable names, server PID56040 started
with four bots. SHA256 D2BA3F66B83ACAFDBDE67237F16798BB20DB56FD529AEB7432E0087EAF64411E.
C1 reception verified: replicated slot178 and actual renderer dvar at
0x2acfcac both read approximately0.35. User subsequently confirmed that the
shadow looks great and explicitly requested no further shadow investigation.
Killhouse shadow issue closed. No automated tests performed.
