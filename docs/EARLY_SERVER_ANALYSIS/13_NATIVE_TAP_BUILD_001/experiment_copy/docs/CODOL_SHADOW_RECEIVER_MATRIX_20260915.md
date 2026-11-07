# C1 shadow receiver matrix consumer

Status: exact native C1 consumer chain recovered. No observed mismatch, native
patch, process mutation, hooks, build or automated test. Corrected frontend guards
from CODOL_SHADOW_DRAWLIST_TRANSFER_20260915.md remain mandatory.

## Matrix publication and camera-relative adjustment

ACECA4 selects frontend+41C50 for a sun-shadowed light. ACECAC calls ACE960 with
the command source, light index, and that pointer. ACE968 compares the cached
light index at command-source+16E0; on change ACE970 updates it and calls AB0370.
AB0374 increments the matrix version word at source+16C8. AB0381..AB038C copies
exactly16 floats from the supplied pointer to source+1570. This proves the first
64 bytes of frontend sun output are the receiver lookup matrix, beyond the
earlier raw output capture's unspecified meaning.

AB3290 supplies the shader-facing matrix. It copies source+1570 into source+300,
then AB32AC..AB32B8 calls61ABC0 with vector source+1560, the copied matrix, and
output source+330 (its last row). 61ABC0 explicitly evaluates the four row-vector
dot products, including the input vector's fourth component. This replaces the
translation row with that vector transformed by the lookup matrix. AB32BD/AB32C9
then publishes the version word. Therefore receiver sampling has a real
camera-relative adjustment in addition to caster projection. Incorrect origin or
matrix version lifecycle could affect it, but no such fault is established here.

The source+1560 vector is mode-dependent: AAFFB0 sets mode2 and writes (0,0,0,1)
there when entering that mode. It would be incorrect to assume this vector is
always the raw camera origin, or compare it with scene bone translations without
following the active mode producer. OpenBLOPS's named R_SetShadowLookupMatrix and
shadow receiver path provide semantic guidance only; offsets above are direct
C1 instructions.

## Probe and remaining boundary

The passive draw-only probe now records frontend+41C50 as16 floats, finiteness
and before/after byte stability, with exact static allocation/endpoint and
frontend/view-pointer coherence checks. It does not follow an invented command
source pointer or claim the shader-facing translated matrix was captured.

`obj/killhouse-shadow-receiver-matrix-100756.json`: revalidated client, command0,
scene skipped. No matrix values inferred from stale frontend state. Next concrete
work is resolve the active backend command-source ownership/mode and correlate
its source+1560, +1570, +300 and version words in a valid frame. A correct source
matrix alone would not prove depth texture contents or receiver sampling correct.

No evidence-backed server field correction follows from this offline chain.

## Active coordinate-mode producer and real source ownership

AB00D0 enters mode1 at source+171C. Source+16F0 points to the selected view
parameters; AB00F3 copies54h words into source+1410. AB0100..AB011E copies the
view origin (view-parameter offsets100/104/108) into source+1560/1564/1568 and
AB0126 writes w=1 at+156C. This completes the previously unresolved origin
producer: in mode1 the vector is the selected view origin. Mode2 explicitly
uses(0,0,0,1), as documented above. Multiple matrix version words change during
mode transitions; those are engine lifecycle, not network snapshot fields.

AAA3EA passes literal12A6B30 to either AAFFB0 (mode2) or AB00D0 (mode1); AAC4AD
also passes it to AB00D0. Numerous UI and world call sites reuse this same global
command source. Consequently a late-frame mode2 capture is legitimate and must
not be interpreted as a missing mode1 update. ACEC44 obtains the backend owner
from source+1404 before resolving light records and sun-shadow lookup data.

The draw-only passive probe now captures this *verified* global source: backend
owner, mode, selected view pointer, current/cached light IDs, raw and shader
matrices, origin vector, source/applied version words, byte stability, and the
expected transformed last row. Interpretation requires a valid frame, coherent
backend ownership and actual relevant draw mode. A numeric difference alone can
mean a deferred matrix update or a different UI pass; it is not labeled a defect.

`obj/killhouse-shadow-command-source-100756.json` remains inactive (command0), so
no command-source memory was sampled. The tool does not guess transient stack
command sources used by other backend jobs. Those additional ownership paths and
actual material draw context remain unresolved. No runtime or gameplay changes.

## Guarded active receiver capture

`obj/killhouse-shadow-command-source-active-100756.json` records12 passive samples
at command405193..405241 in exact Killhouse. All frontend pointers passed the
two-allocation and readable-endpoint guard; nine retained frontend identity
across the complete read. The frontend lookup matrix was finite in all samples.
Allocation counts varied0/66/158/188 as frame preparation progressed. Those are
sampling phases, not maximum frame usage or evidence of missing geometry.

Every sampled global command source was mode2, origin vector(0,0,0,1), null view
parameters and zero raw/applied lookup matrices/version words. Its backend owner
was the other valid frame allocation, rather than the concurrent frontend. This
is compatible with buffered backend/UI work; it is not proof of a wrong owner or
a missing 3D shadow matrix. No sample captured the actual world receiver command
source, so the zeros must not motivate an always-on or forced-origin fix.

This completes the bounded capture: frontend matrix values are available, but
the global source is the wrong draw context for proving receiver behavior.
Next investigation must identify the world-pass local command source from its
actual context producer, rather than sample12A6B30 more often or reinterpret its
legitimate 2D mode. No demonstrated server-side field defect.

## World draw callbacks use a fresh stack source

The ownership path is now concrete. ACF1C0 reserves an aligned179Ch-byte stack
frame. ACF1EB passes an address within that frame to AAFC30; AAFC30 zeroes exactly
1780h bytes, then initializes the source from view+A10 input. This source is not
the global12A6B30. ACF201 sets its render target and ACF212 its viewport. ACF227
passes it into AB4750 together with the view, view+180 parameters and callback.

AB4771 obtains that local source from argument3. AB4787 calls AB02F0 with the
local source, supplied view parameters and view, establishing mode1/origin via
the earlier verified AB00D0 path. AB47A9 copies global *render state*12A82B0 to a
separate B20h-byte stack state; the source and render state are distinct objects.
AB47D5 invokes the selected draw callback with the local source and state. Only
the render state is copied back to12A82B0 at AB47EA. There is no copy of the local
source's shadow matrix back to12A6B30 on this path.

ACF95D/96C/97B/98A select callbacks ACF000/ACF070/ACF0E0/ACF150 and call ACF1C0.
For example ACF000 prepares view+170 viewport context and passes the actual
view+568 draw list to AAF630 at ACF049. The source therefore belongs to a concrete
world draw-list invocation, not merely an unused stack allocation. Each callback
gets its own initialized source lifetime.

This explains why capturing the global source after rendering returned zero
shadow matrices: those particular world callbacks never publish their matrix to
that global. That is normal C1 ownership, not a server producer omission.

No new live source capture was attempted at an invented stack address. The
current passive reader has no verified active stack-frame pointer for ACF1C0 or
its nested callbacks; scanning stale stack contents would not establish an active
receiver. Next useful evidence must identify an actual current draw context and
its material/constant selection, or inspect the GPU depth/receiver output through
an already available non-mutating capture facility. No hooks, suspensions,
breakpoints or gameplay changes were introduced to obtain this evidence.

## Narrow receiver technique gate and server-control boundary

New offline branch AB1F2D checks view+FA4, bool dvar[CF4138]+C, then the
frontend+41920 bit indexed by world+20. That branch selects technique27h(39) when
all pass, otherwise25h(37). Its receiver class and the semantic identity of
world+20 still need verification; it must not be presented as the global sun
enabled gate. Independently, A803A0 scans shadowable bits for indices1 through
world+1C, a different selection range used before sun list construction.

Registration A7C201..A7C227 proves CF4138 is numeric bool1544, default1, flags4.
It is client renderer registration, not a direct playerstate field. A80A04 also
copies its current byte into an internal view setup record. No native-server
producer that overwrites numeric1544 was established. Friendly external dvars are
not equivalent to this registration, as prior exact-name lookup work proved.

Guarded active sample `obj/killhouse-shadow-receiver-gates-100756.json` at
command739095: frontendE1FE80 and view pointer coherent; view+FA4=1; actual1544
current/reset=1; world+20=30 and its selected bit is clear. The clear bit is only
this unclassified branch's input, not evidence that sun shadows were disabled or
that any server state is wrong. In particular, equating world+20 with an earlier
document's sun index would be an unsupported layout assumption.

Narrowed hypotheses: actual relevant material technique selection/texture binding,
or mode-correct world local receiver matrix sampling. Known matrix preparation
and source lifetime are native client renderer behavior. Existing server-fed sun
direction/vision/dvar publication remains a separate audited boundary; current
evidence has not identified a mismatching server-controlled value here. Do not
change1544, light bits or shader constants to force this unclassified branch.

## Gate identity resolved: additional lights, not the sun

Disassembling the complete entry AB1EA0 resolves the earlier isolated branch.
AB1EAD loads world+20, and AB1EB0 compares it against view+1B0 before entering
the loop. Each iteration takes a64-byte light record at
frontend+F3B00+lightIndex*40h, and indexes a per-additional-light list using
lightIndex minus world+20. This is the extra-light range beginning after the
world's primary lights. The original Killhouse asset's primaryLightCount30
corroborates the captured world+20 value30. AB1F0E reads that light's type;
AB1F1A branches specifically on type2. Type2 chooses normal technique25h or
shadowed27h; the other branch chooses26h. It is not selection of sun shadow
partition matrices or a global sun toggle.

OpenBLOPS's r_draw_shadowablelight.cpp separately checks an additional emissive
spot light at Com_GetPrimaryLightCount() and requires its shadow-map bit. This
provides a semantic reference for the additional-light policy; C1's actual loop,
record offsets and technique IDs above were read directly from C1 and were not
copied from T5.

Consequently the earlier clear bit30 does not establish a missing sun shadow.
The loop may not even execute if the view has no extra lights. The probe now
captures view+1B0 and reports this applicability explicitly before interpreting
the type2 gate. Follow-up capture
`obj/killhouse-shadow-additional-light-gate-100756.json` found command0 and skipped
scene data. The earlier sample did not record this range limit, so its gate
value cannot retrospectively establish that a corresponding draw happened.

This closes one misleading hypothesis without a renderer/server tweak. Remaining
actual sun material/texture sampling must be traced through its own receiver draw
context. No source defect or missing native server field is demonstrated here.
