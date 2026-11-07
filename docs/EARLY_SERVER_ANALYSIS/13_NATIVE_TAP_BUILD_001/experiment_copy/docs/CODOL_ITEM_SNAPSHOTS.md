# Weapon pickup entity selectors

The gameplay frame producer now accepts base-variant `ET_ITEM` weapon entities.
Their selector is translated through the registered weapon map, then the existing
entity collector composes trajectories, scale and events.

Retained `G_SpawnItem` writes its item number into `entityState.index` at +0x88.
The low seven bits select the weapon; the quotient by 128 selects a world-model
variant. This is a packed weapon selector, not a model configstring slot.

Static C1 evidence:

- The type-3 model dispatch at `0x443ba5` reaches `0x443bbe`, then `0x43e7d0`.
- Its item branch at `0x43e947` reads centity+0x17c (next entity state+0x98).
- `0x43e953..0x43e958` divides by 700. The remainder selects the weapon passed
  to `0x43e600`; `0x43e619` resolves the weapon table and `0x43e66b` reads its
  world model at +0x1c.

`CODOL_OverlayEngineItem` accepts native selectors 1..127, resolves their CoDOL
weapon IDs, and writes +0x98 only for IDs 1..699. It rejects `none`, unmapped
IDs, out-of-bank IDs and nonzero native world-model variants. Variant semantics
are not assumed equivalent merely because both layouts use a quotient.

The gameplay fixture uses native weapon 1 mapped to client weapon 25, builds a
frame containing the item, and serializes it through the real snapshot writer.
It also checks invalid selectors, failed translation without partial output,
and recipient-frame invalidation for unsupported variants. This verifies item
representation in snapshots, not live C1 pickup interaction or every item flag.

Validation on 2026-09-08: the completed Linux build/full suite passed in
`/tmp/sh1x-item-frame-final-linux.log`, followed by the forced Windows build in
`/tmp/sh1x-item-frame-win32.log` (sequential exit zero). The final item-frame
serialization and boundary fixture also passed ASan/UBSan; compiler output is
in `/tmp/sh1x-item-frame-sanitizer.log`. The first full run exposed an older
generic fixture's zero item selector; that fixture now supplies a mapped item
and asserts its translated selector.
