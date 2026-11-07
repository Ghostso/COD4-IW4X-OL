# Repeated first-death camera position

User reports subsequent deaths show the location of their first death.
The existing native clone allocates a new corpse-info slot but never writes
that slot to playerstate. C1's ps+e4 corpseIndex therefore remains zero in
every snapshot even as additional corpses are created.

Direct aligned C1 clone disassembly from51c780 confirms call531a80 at51c9db
returns the corpse-info index in EAX. It selects info storage with index*b88
at51c9e2..51c9ea and writes the same EAX to the source player's ps+e4 at
51ca2f. This is distinct from the rotating corpse entity19..26.

The retained clone's G_GetFreePlayerCorpseIndex return is now captured into
the source player's native extension before EAX is reused. The added call
preserves all registers and the original stack with the same aligned call
pattern used by the existing appearance capture. No client memory is changed.

The extension carries a bounded0..7 corpse index, writes/reads an independent
changed bit plus3-bit value in internal archives, and publishes C1 ps+e4
with player animation state. Full state copies and ordinary lifecycle reset
include the field; archived publication uses its own captured state.

Compile/link and linked clone-call verification completed. A later death at
a different location still needs live confirmation; no automated tests run.
