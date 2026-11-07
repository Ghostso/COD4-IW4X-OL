# Native particle-cloud elements

The Windows `codol_checkcollision mp_bog_sh` audit initially failed assembly
despite successful brush, terrain, leaf, static-model and physics conversion.
All 17 failed dynamic-effect instances referenced `props/watermelon`. Its first
element has source type 6, with no extension or extra name. The converter and
its archive dependency traversal rejected this type.

## C1 evidence

For C1 SHA256
`d990610732258b1d00dd6fe63d6691f294312a2e0562955a01ce16216115390d`:

- Draw dispatch table `0x00c3cb54[6]` points to `0x004e4500`.
- That entry calls `0x004e4100` to evaluate cloud scale from visual samples
  and the random table, and `0x004e4180` for sphere culling. The cull radius
  combines visual dimensions with the computed cloud scale.
- `0x004e44a0` chooses the element material from +0xbc, including its random
  visual array, and calls `0x00a806c0` to obtain scene cloud storage. It then
  passes element type 6 to `0x004e4210`.
- At `0x004e4213`, type 6 selects velocity evaluation (`0x005043c0`) and
  normalization (`0x004090e0`). Subsequent code evaluates visual state, copies
  cloud dimensions, shifts the endpoint by velocity, and preserves the
  element flag bits used by the cloud renderer.

The symbol-named IW3 `FX_DrawElem_Cloud` in
`tools/cod4_dasm/src/_fx_draw.asm` evaluates the same scale, sphere culling,
random material selection, `R_AddParticleCloudToScene`, visual state, velocity,
dimensions and endpoints. Its `s_drawElemHandler` table assigns index 4.
This supports translating source type 6 to native type 4. It is a comparison
of rendering behavior, not a guess from serialization alone. C1 was inspected
statically; no live client breakpoints or hooks were introduced.

## Implementation and verification

Both the native converter and archive effect-graph traversal now accept type
6. Native material bindings, owned velocity/visual samples, child effects and
transactional publication follow the existing implementation. Extensions and
unconverted CoDOL fields still reject; type 7 and type 8 are not covered by this
mapping.

The focused 32-bit ASan/UBSan fixture passes for type translation, material and
child bindings, copied samples, and atomic rejection of unsupported extension
data. Actual map assembly and in-VM node tests are tracked separately; accepting
this type alone is not evidence of a playable match or client rendering parity.

The Windows map probe after this change installs mp_bog_sh's native collision:
658 leaves, 432/0 dynamic entities, checksum `a228f2cd`. The follow-up audit now
reports **51 ready / 0 failed dynamic effect instances**, and assembled clipmap
status 1. The isolated VM probe proceeds into game initialization and then stops
at `BG_IndexForString: unknown token 'idlelaststand'` in
`mp/playeranim.script:37`. Its node assertions therefore have not executed.
The temporary test also needs its expected classname corrected to
`info_vehicle_node_rotate` and `developer 1` set so native assertion calls are
retained. No VM assertion success is claimed from this run.

Final validation: Windows server build passes; full Linux
`make -B -j6 all test-codol` passes. The focused sanitizer fixture and actual
Windows Bog conversion audit above cover the new type. The diagnostic process
exited normally, and the existing lobby/client processes were not modified.
