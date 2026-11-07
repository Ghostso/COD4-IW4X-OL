# mp_nuked collision startup failure

Read-only offline asset audit; no automated tests/builds/process changes.

Parent reproduction stage diagnostics identify dynamic category0,index49: native effect `destructibles/fx_dest_elec_box` loading fails. Source collision parsing succeeded. This isolates the failure from the previous worldweapon teardown investigation.

Shipped source archive: `D:/CoD/CODOL Builds/Call of Duty Online 1.1.1.13/client_shipRetail/chinese/mp_nuked.ff`. Inflated cached zone: `C:/Users/Michael/AppData/Local/Temp/codol_zones/mp_nuked.zone` (57,527,404 bytes). Offline inspection finds gfxworld asset238/type21 and collision asset240/type15 sharing name reference0x3039788d. Collision has9734 planes,5716 brushes,1577 static models,393 dynamic category0 entities. Native static-model finite/bounds guards and leaf/internal brush-tree constraints match inspected source values; these checks do not establish all native dependencies load.

Actual failing effect is zone asset53/type30,14,275 bytes. Extracted bytes and SHA256/header record report are `obj/bot-worldgun-audit/fx_dest_elec_box.bin` and `fx_dest_elec_box-header.json`.

The root effect contains13 elements, source types in order:0,14,10,0,4,0,0,0,0,6,0,0,12. Native transaction codol_asset_registry.c rejects source type4; native pack codol_effects_native.c rejects it independently. Element4 is therefore concretely unsupported. Separately elements0,4,10 have nonzero +256 (inline extra_name), which source decoding preserves but native pack rejects. No root element has a +244 extension or +252 pointer. All root effectRefs+216/+220/+224 are zero, but element1 contains five type14 runner visuals whose child identities require complete pooled-reference traversal.

Consequently dropping dynamic effects or weakening validation would hide missing representation. Required next work is C1 type4 equivalent decoding/consumer semantics and preservation of the +256 field/its consumer; actual child effects must then also be resolved. Exact extra_name identities were not inferred from unaligned printable strings. Parent owns native correction and reproduction diagnostics.

## Native C1 FX representation correction

C1 draw dispatch table C3CB54[4] selects4E4D80. It evaluates velocity through
5043C0, normalizes it, performs line culling4E4BF0 and invokes4E4C80 to construct
line geometry. This matches OpenBLOPS FX_DrawElem_Line's sequence, not the
retained cloud or tail type. The correct source identity is type4, with its
material visual and velocity/visual samples preserved.

C1 +256 is now proven **spawn sound**, not a fourth effect link. Loader
4BD505..4BD55B resolves it as XString;4BD56B and4BD5BB advance elements by104hex.
Runtime4FF3B7 and502602 read element+100hex and pass the string to4FF850.
That function resolves asset type11, reports `Failed to find sound alias '%s'`
on failure, and calls44F940/44F7F0 with the supplied origin and resolved alias.
The fourth word at+252 is not pointer-relocated by the C1 element loader; its
four original scalar bytes are retained without inventing a field meaning.

Changed source:

- `src/xassets/fx.h`: CoDOL native FxElemDef is260bytes, original first252bytes
  followed by four source scalar bytes and spawnSound pointer at256. Non-CoDOL
  targets retain252bytes. FxEffectDef header remains32bytes.
- `codol_effects_native.c`: retains original C1 element IDs instead of reducing
  them to IW3 renderer IDs; admits type4 with real visual dependencies, copies
  trailing scalar bytes, validates string-reference presence and owns each
  spawn-sound string inside its allocated definition. No asset is skipped.
- `codol_asset_registry.c`: type4 receives normal material resolution. Runner
  cycle fixups now identify source type14, preserving placeholder replacement
  after the native type-remapping removal. Effect links and graph transaction
  publication/free behavior remain unchanged.
- Corresponding source/native headers document the preserved representation.

Consumer/stride audit: native C element-array consumers are the packer and
registry graph fixups, both using sizeof/typed indexing. Main retained
`_db_load.asm::Load_FxEffectDef` still reads legacy **IW3 serialized**252-byte
records; this is not the mounted C1 decoder or graph construction path and its
serialized format must not be silently reinterpreted as260. The additional
`src/bspc` loader is outside the server makefile's assembly source glob. Retained
DB pool operations use the unchanged32-byte effect header. Dedicated-server
collision and weapon owners retain the effect handle; FX registration and
publication use its original asset name. There is no active server FX rendering
loop to remap to IW3 element IDs. C1 itself owns line drawing and spawn-sound
playback from the named original assets; no duplicate server audio was added.

Source written and manually reviewed only. Parent owns build and isolated
mp_nuked startup verification. Nested runner/material/model resolution remains
strict and transactional; if an additional unsupported child is encountered,
that is further implementation work, not permission to substitute an empty FX.
No automated tests, launches, client writes or process changes by this worker.
