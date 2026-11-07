# Weapon composer lookup work reduction — 2026-09-14

Source increment: src/codol/weapon/codol_weapon_compose.c only.

Existing composed definitions already cache complete attachment application and
native conversion by canonical name. Repeated work before reaching that cache
included marketplace ordinal/name/group resolution (full table scans per call)
and the scored component-model row search, repeatedly requested by validation,
default filling, tag collision checking and composition.

Changes:

- Build a dense attachment-ordinal index once per mounted marketplace table.
  Ordinal lookup becomes direct indexed access; duplicate/empty/null handling
  preserves each previous API's semantics.
- Build a sorted name index in that same pass. Reverse lookup uses upper_bound
  so the last matching row still wins, with O(log N) comparisons instead of a
  whole marketplace scan. Allocation failure uses the unchanged scan path.
- Add a bounded 256-entry direct-mapped component-row cache keyed by immutable
  table identity, copied base/item strings and camo. Hits bypass the scored
  table traversal. Both matching rows and valid no-row results are cached;
  unavailable/malformed tables are not. Collisions cause ordinary recomputation,
  never a different result. Oversized keys bypass caching.
- Preserve the original reverse-order exact/camo-zero fallback selection and
  borrowed output strings. No recipe fields, variants, timings or client output
  changed.

Lifecycle: archive mounting/replacement already calls RetireComposedWeapons
before publishing new archives (codol_asset_registry.c around314). Retire now
clears the lookup structures before its early no-composed-definitions return.
Total ResetComposedWeapons also clears them. Marketplace identity is checked on
every lookup; model row cache checks the currently loaded table pointer before
reusing its row. Retired composed cores and their borrowed art remain untouched.
There are no cache-held borrowed strings surviving retirement/reset.

Evidence level: source reviewed; no automated tests, build or live latency
measurement run by this worker. This removes repeated scans; it does not prove
all first-time weapon construction stalls are eliminated. Initial table loading,
first model assembly, attachment-table legality scans and publication remain
separate costs. Parent handles integration/build and runtime observation.

## Mounted dependency index increment

Second source increment: codol_asset_registry.c. The prior parent-owned table
logging guard remains intact.

`find_dependency_definition` previously traversed every alias in each active
archive for every name lookup. `LoadMountedNativeXAnim` performs four such
lookups per animation through its source/handle/native paths, including cache
hits. A new weapon's conversion enumerates up to144 animation slots, so this
path alone can perform up to576 complete alias traversals before other models,
weapons, effects and sound dependencies are counted. Existing native animation
conversion caching did not eliminate those searches.

Each fully replayed archive now lazily builds one open-addressed index of
(type, normalized name) to its winning asset. Normalization exactly matches
asset_name_equal: ASCII A-Z case folding and backslash-to-slash, with every
other byte preserved. Full equality follows hash comparison/probing. The table
has at least twice as many slots as aliases, so lookup always reaches an empty
slot even if every alias is a distinct definition.

Ordering remains unchanged: active archives are searched in their existing
newest-first list; within one archive, duplicate names choose the greatest
serialized asset data address, not alias-array order. Leading-comma references,
unnamed/unsupported/malformed names are excluded exactly as the old resolver.
The original linear path remains available for incomplete/source-only archives,
allocation failure or capacity overflow. A failed allocation is not retried on
every weapon lookup. No negative result is cached across archive generations.

The index borrows only its own archive's immutable block strings and alias
records. It is created after prepared=1 and publication; no replay transaction
can expose a partial index. Replacement removes old archives from the active
search list and new archives start with zeroed index fields. Retired indexes
stay archive-owned until total unmount; both active and retired archive cleanup
free the index before block/source storage. Pending rollback also frees the
nullable index. No gameplay state, source bytes, models or animation data are
removed or modified.

Other measured-by-source costs remain: each weapon publication rebuilds all
existing wire registry entries, reparses mounted weapon/ammo names, and clones
up to6519 configstring slots before swapping. Reliable publication sends only
new weapon entries followed by the count; batching/removing those commands is
not part of this change. First unique streamed model resolution can still read
models/<name> synchronously through FS_ReadFile. These are further profiling
candidates, not established live stall proportions.

Status: source-only audit and implementation. Parent review/build pending;
worker ran no automated tests, builds, launches or process modifications.
