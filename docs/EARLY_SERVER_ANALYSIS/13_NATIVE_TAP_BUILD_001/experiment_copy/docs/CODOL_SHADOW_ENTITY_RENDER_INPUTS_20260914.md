# Entity rendering inputs after replicated-dvar repair

Status: bounded offline source/binary audit. No new mismatched shadow input established; no gameplay edits, process changes, UI input, builds or tests.

## Scale consumer and publication

C1's interpolation at0x44152c reads cg+0xb0348. Instructions0x441532..0x441546 interpolate centity+0x138 against centity+0xbc and store the result at centity+0x30. With nextState at+0xe4, the next scale input is entityState+0x54, agreeing with the snapshot producer. The previous scale is a separate interpolated-state input; it is not a model-index field.

`CODOL_OverlayEngineEntityVisible` explicitly writes float1.0 to C1 entityState+0x54 for serialized entities. The missile overlay independently writes1.0 there too. Therefore these producers do not send an enlarged scale or a camera-distance-dependent scale. This is a narrow source exclusion: it does not prove client interpolation is correct at every frame or that runtime model composition/bounds cannot be wrong. It also exposes a functional limitation: source does not represent arbitrary C1 model scale here, but no captured map requirement or script caller establishes a missing non-unit scale as this artifact's cause.

## DObj submission flags are separately constructed

The general-entity consumer0x43ea30 first excludes nextState.eFlags0x10 at0x43ea44. After obtaining its DObj and model-lighting-origin helper result, it passes a literal0 render-flags argument at0x43ea8e to0xa83480. The scene submission's flags are therefore not an unexamined direct copy of the complete entity eFlags word.

Inside0xa83480, flags participate in distinct branches: low bit2 at0xa834c9, mask0x14 at0xa8354d, and the eventual packed scene key at0xa835da..0xa835f3. That packing combines a12-bit entity selector, shifted render flags and a7-bit per-object effect slot. Thus guessing an entity eFlag from these renderer masks would target the wrong representation. The inspected optimized submission branch additionally writes literal unit scale to scene record+0x28 at0xa83642..0xa8364b. Other submission branches remain outside this bounded audit.

The already-reviewed mover/brush paths supply model selector+0x98 and solid+0xa8 through their dedicated overlays. Earlier active submitted-brush captures matched centity identity, model index, origin and identity quaternion. Those captures are historical evidence, not proof of the current exact artifact frame.

## Consequence

After the verified replicated-dvar repair, no server-published oversized scale or general-entity render-flag alias was found in these paths. No speculative flag suppression or scale clamp is justified. The remaining useful discriminator is a capture tied to the exact dark region that includes the affected submitted DObj/model bounds or world renderer path, rather than another comparison of already-matching brush indices. This audit makes no visual-causation claim and does not exclude client-side depth or camera-relative world rendering.

## Downstream bound ownership and latest capture guard

The later passive modifier probe revalidated C1 PID102092 and the exact0xa82140 code guard, but commandTime was0. `obj/killhouse-render-modifiers-102092.json` records the skipped inactive sample. No actual local modifier values were inferred from defaults or old memory.

Offline follow-through of dynamic DObj submission0xa83681 shows it obtains a scalar through0x634dd0, which reads DObj+0x9c directly. Constructor helper0x6343e0 writes that member at0x63462c after accumulating model/bone-related data, called by DObj creation0x634660. This input is owned by the client's constructed DObj, not a direct copy of native server collision bounds. The model lighting-position path0x43e370 likewise reads the first client XModel's data at+0x140..0x154, combines its first vector with centity angles/origin, and returns a world position. A server collision-box-size hypothesis must therefore identify a separate consumer; it cannot be justified by equating those native bounds to these renderer inputs.

No out-of-range active DObj bound was captured, and no server producer mismatch was established from these downstream reads. The native model selection fix is separate: it changes which correct client asset can be constructed, not the asset's own bound data or the static world's depth/shadow rendering.
