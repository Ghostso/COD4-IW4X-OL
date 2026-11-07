# MP animation precache gap

Current source does not register `precachempanim`. Offline IW4 table record
`0x79abdc` names it and points to `0x5f8380`. The handler requires the
initialization flag at `0x1a831c4`; its error at `0x6f02b0` explicitly says
to call before waits in gametype/level scripts. It reads string argument 0,
then calls the indexed configstring registrar `0x4af0c0` with base `0xfca`
(4042), capacity `0x3f` (63), create=1 and label `mp anim` (`0x73600c`).
It pushes no script return. It is not an empty precache marker.

Actual source callers in alpha0022's vendored IW4 tree include
`maps/mp/_animatedmodels.gsc:17` and `_ac130.gsc:1756` through 1758,
preloading the three `ac130_angel_flares` animations. Destructible scripts
also pass a function pointer to it. These files are ignored by ordinary
`rg` searches; use `rg --no-ignore` on the reference tree. Earlier empty
search results must not be interpreted as missing script calls or files.

C1's equivalent animation publication/consumer has not been identified.
Do not copy IW4 base4042: it lies inside C1's tagged-effect range3971..4226.
The nearby C1 block3363..3394 is also not an animation mapping: dispatcher
`0x4674bb..0x4674cb` loads those entries as asset type`0x29` and stores
the resulting pointers. Python's older configstring_map.py calls that block
effects, while its later bot_snapshot.py identifies vehicles; neither label
is a reason to place animation names there. The measured asset type is the
starting evidence for verifying that block separately.

Next implementation work: trace C1 animated scriptmodel state and XAnim
consumers, connect a real native precache registry to that transport and
asset loading, then register the global function. A no-op or an animation
name sent to an unrelated configstring bank would not provide support.
No builds, tests, assembly, runtime launches or match entry were performed.
