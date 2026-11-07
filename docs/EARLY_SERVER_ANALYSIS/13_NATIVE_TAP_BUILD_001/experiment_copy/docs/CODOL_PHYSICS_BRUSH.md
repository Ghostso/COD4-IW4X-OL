# Native model physics brushes

`CODOL_BuildNativePhysicsMap` now converts source type-0 brushes in addition
to the existing box and cylinder primitives. The 68-byte source brush stores
midpoint/half-size bounds, 8-byte sides, and byte adjacency offsets. The native
80-byte wrapper stores minimum/maximum bounds, 12-byte sides, and 16-bit offsets.
Conversion owns an aligned wrapper, sides, both plane collections, and adjacency
bytes. Per-side resolved planes are preserved independently from the wrapper's
plane array. Plane normals, finite bounds, side counts and adjacency ranges are
validated; failure preserves the previously published map.

The retained `Phys_ObjSetCollisionFromXModel` dispatches a non-null brush to
`Phys_ObjAddGeomBrush` before primitive type dispatch. No primitive substitution
or hook is used. The source has no brush contents mask; the native wrapper keeps
that field zero and the ODE path receives the shape directly. This conversion
does not claim complete parity for extended CoDOL physics simulation parameters.

The focused fixture covers axial-only and nonaxial brushes, differing per-side
planes, bounds conversion, alignment, adjacency-range rejection, invalid normals,
failure atomicity, source-independent ownership and repeated cleanup. It passes
with 32-bit AddressSanitizer/UndefinedBehaviorSanitizer and is in `test-codol`.
The full Linux `make -B -j6 all test-codol` also passes
(`/tmp/sh1x-physics-brush-linux.log`).

The Windows build passes (`/tmp/sh1x-physics-brush-win32.log`). An isolated
`mp_bog_sh` probe reports `com_cellphone_on` complete 1, including its three
materials, preset and brush map. Startup advances to `G_Spawn: no free entities`;
its entity dump includes `node_pathnode`, cover and concealment node classes
through slot 1021. Dedicated path-node handling remains to be implemented and
verified. The planned vehicle-node GSC assertion marker is still absent.

Probe PID 64508 exited after shutdown and `quit`; log:
`%TEMP%/sh1x-physics-brush-native-probe/main/qconsole.log`. It used an isolated
minimal script fixture and loopback port 17739. No existing client or lobby was
restarted or modified. This proves loader advancement, not active-body collision
parity, full reference script startup, or client match entry.
