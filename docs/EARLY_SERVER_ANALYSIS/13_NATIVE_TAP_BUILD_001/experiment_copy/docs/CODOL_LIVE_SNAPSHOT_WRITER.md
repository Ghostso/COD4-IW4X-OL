# Native CoDOL snapshot entry point

For `CODOL_SERVER`, `SV_WriteSnapshotToClient` now uses the CoDOL serializer
and recipient ACK history. The retained IW3 body remains compiled only for the
upstream build. The writer preserves rate-delay, inactive-client and server
snapshot flags, requests origin/velocity fields, and derives position bases
through the existing configstring-aware preparation path.

`CODOL_BuildClientNativeFrame` assembles and owns one frame per recipient using
the existing player/HUD/entity/client conversion and explicit actor/animation
command inputs. Retrieval requires the exact outgoing sequence. Failed rebuilds
invalidate the prior frame even when retrying the same sequence. New native
snapshot construction clears the previous owned frame, and client history reset
frees it together with HUD captures and ACK history.

The writer appends a complete CoDOL body and EOF after the reliable prefix.
`SV_EndClientSnapshot` retains its exact-byte and sequence checks, and commits
history only when transport accepts that message. Missing/stale native data
marks the message for existing reliable-message recovery; it does not emit an
IW3 body under the CoDOL envelope.

The send fixture invokes the actual frame builder, live writer and finalizer.
Its world services intentionally contain no entities/clients/HUD, while the
separate asset-name fixture exercises production ring collectors. It checks
CoDOL opcode, full-frame flag, exact ACK delta, accepted history, stale-frame
recovery, failed same-sequence rebuild invalidation and reset cleanup.

## Remaining integration

The native send path now calls `CODOL_BuildGameplayFrame`, which supplies the
initial gameplay bindings and calls `CODOL_BuildClientNativeFrame`. See
[gameplay frame producer](CODOL_GAMEPLAY_FRAME.md) for supported states and
explicit remaining gaps. Unsupported frames still use reliable-message recovery.
The route is connected, but a live authenticated match has not been verified.
The full-reference script compile also still stops at `weaponInheritsPerks`.

Validation passed the complete Linux `test-codol` suite
(`/tmp/sh1x-live-writer-linux.log`), final Linux relinking after capture
invalidation was added (`/tmp/sh1x-live-writer-linux-final.log`), and a forced
Windows build of `bin/codol_dedrun.exe` (`/tmp/sh1x-live-writer-win32.log`). The
send fixture compiled after that invalidation edit. All commands exited zero.
Shared static libraries were last built for Windows.
