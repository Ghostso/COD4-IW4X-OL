# Client-info attached-vehicle entity

`CODOL_OverlayEngineClient` now maps native `clientState.attachedVehEntNum` to
CoDOL client-info field +0xbc. Native entity numbers 0..1021 remain unchanged;
native ENTITYNUM_NONE (1023) becomes CoDOL ENTITYNUM_NONE (2047). Negative values,
the reserved native world entity (1022) and out-of-range values are rejected
without changing the output.

The previous client-ring collector initialized this unproduced field to zero,
which is a real entity number rather than CoDOL's unattached sentinel.

Source evidence:

- Retained `_g_active_mp.asm`, `ClientEndFrame_40`, writes `ownerNum - 1` to
  gclient +0x3068. `ClientEndFrame_80` writes 0x3ff there when unattached.
  This is `sess.cs.attachedVehEntNum`; the distinct ride slot is +0x306c.
- C1 `G_UpdateClientInfo` at 0x50d4f4..0x50d55f defaults to 0x7ff and otherwise
  writes the validated owner-handle entity number to gclient +0x3524, which is
  clientState +0xbc. Its field table gives this field 32 bits.
- Alpha0022 `docs/bots_notes.md` section 4.3 locates the same producer. Its older
  labels for other fields include errors (notably perk masks labelled as names);
  this mapping follows the inspected instructions, not those unrelated labels.

Tests cover attached entities 0, 17 and 1021, detachment, invalid input, CoDOL
wire reachability, and a two-client span across the native ring wrap. A bad
vehicle ID in the second client preserves the entire previously collected span.

Validation on 2026-09-08: Linux `make -j6 all test-codol` and the forced Windows
MinGW server build pass. The existing C1 client and Python lobby were untouched.

Vehicle seat indices, other unmapped client-info properties, the full live
CoDOL snapshot writer and connected-client vehicle behavior remain unfinished.
