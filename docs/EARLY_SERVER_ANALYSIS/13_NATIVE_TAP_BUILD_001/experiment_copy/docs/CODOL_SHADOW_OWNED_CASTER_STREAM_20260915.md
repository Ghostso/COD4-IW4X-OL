# Owned sun caster stream — 2026-09-15

Status: actual owned draw-key capture; no offending caster identified. No gameplay
source changes, renderer settings, hooks or process writes.

The passive probe now bounds descriptor+40/+44 key spans to the current
frontend+D3B00 arena of16384 eight-byte entries, retains all keys and checks
pointer/count/data stability. An initial frame had null destination streams;
that is not interpreted as an absent shadow pass. A subsequent capture at
command190756 has valid stable streams, saved as
obj/killhouse-shadow-owned-caster-keys-90404.json.

## Exact C1 key interpretation

AADB60 loads both words of each key. AADC08 shifts the high word by22 and
masks15; AADC0E dispatches through BF4620. Surface type is therefore bits54..57,
verified in C1 rather than copied from T5.

| Partition | Count | Type6 | Type7 | Type9 |
| --- | ---: | ---: | ---: | ---: |
| Near | 31 | 4 | 27 | 0 |
| Far | 190 | 4 | 140 | 46 |

Handlers are6=ACE200,7=ACD520,9=ACD0D0. A817F0's DObj emitter identifies7 as
the rigid-record branch and9 as the skinned-record branch; -3 is skipped and
other negative header values determine rigid record length. Scene record+44
owns the starting prepared surface pointer. The emitter walks actual selected
model LOD surfaces before generating these keys. ACD575/ACD14F resolve model
keys' low16 index to frontend+42700+index*4. This permits future same-scene
correlation; it does not by itself reveal vertex bounds.

## Scope correction

AA71A0 maps descriptor+40/+44 into the generic key iterator, and AAF4E0 selects
its AADB60 callback independently of other streams. Descriptor data before and
after these fields feed separate BSP/static/other iterators. Consequently the
captured31/190 keys are not every world caster: absence of other type values in
this stream cannot exclude static map geometry. Global construction counters
may already reset while prepared destination streams remain valid.

A follow-up full pose capture found C1 commandTime0 and skipped scene reads;
obj/killhouse-shadow-owned-caster-pose-90404.json records that limitation. No
same-scene model bounds were available, so no caster is accused or excluded on
stale storage. The next active capture can pair these owned keys with actual
selected DObj surface/LOD ranges; separate world streams still require their
own ownership and geometry capture. No speculative native patch is justified.
