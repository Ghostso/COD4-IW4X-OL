# What the CoDOL tests establish

The tests isolate compatibility boundaries while the native server is being
ported. A passing fixture establishes its tested boundary, not a playable match.

| Test family | Goal |
| --- | --- |
| Wire, delta, tables, player arrays, usercmd, send | Check field order, bit widths, quantization, command decoding and packet/history behavior against the available reference. Catch corruption before connecting a client. |
| Configstrings, inherited strings, asset names | Check index spaces, baseline/override behavior and publication of names the client must resolve. |
| Weapon ammo registry | Reproduce 108 live-harvested stock keys, distinguish custom reserve inheritance from magazine allocation, and map owned native weapons to snapshot ammo slots with explicit removal clears. |
| Server snapshot ammo | Resolve the exact snapshot inventory against registered native definitions and client pool keys, retain the actual counts, reject unloaded ownership, and invalidate a recipient frame after failed resolution. This is not a connected-client firing test. |
| Server weapon configstrings | Build the client registration order from the mounted attachment table and partner weapons, suppress stale inherited slots, preserve unrelated values and invalidate failed registry refreshes. The native Bog probe checks actual mounted initialization. |
| Archives, IWD crypto, assets, maps, brushes, stream models | Check decoding, bounds and ownership of original CoDOL data. Python here is an offline reference/tool, not the gameplay server. |
| Native collision, model trace, model lookup, model flags, physics brushes, weapons | Check converted structures against the retained engine's layout and consumers. These fixtures do not cover every asset in every map. |
| Animation ABI, native conversion, evaluation and tables | Check that CoDOL animation data fits the native evaluator, including empty delta data and expanded animation indices. |
| Script source/lowering, math, entity/server/menu helpers, path/vehicle nodes | Check native VM-facing behavior, source adaptation and actual map records, including rejection of invalid inputs. |
| Offhand/weapon-switch controls | Check independent restrictions, repeated calls, player validation and preservation of unrelated player-state fields. Full movement/client prediction remains separate validation. |
| Player usability | Execute retained activation assembly to verify pending-use cancellation, release edges and restoration of enabled use processing. |
| HUD font-scale transitions | Check smooth interruption, native client-copy ownership, reset/reuse and CoDOL timing fields; also invoke the methods in the native VM. |
| Frame HUD capture | Preserve resolved HUD state when native player state is copied; reject stale sequences or failed replacements and retain old indices after later name remapping. |
| Owned native frame assembly | Compose player, HUD, entity and client data with owned actor/animation-command copies; preserve supplied client metadata and roll back both event-clock stores after a late failure. Check semantic structure alignment after packed engine headers. |
| Live CoDOL snapshot writer | Run owned frames through the real writer and send finalizer; verify full/ACK delta headers, accepted history and reliable-message recovery for stale frames. The fixture supplies frame inputs that gameplay still needs to produce. |
| Client-info vehicle attachment | Translate the unattached entity sentinel, preserve real vehicle IDs, and reject invalid late records without partially replacing a client span. |
| Event parameters and frame entities | Check supported event mappings, ring/history bounds, ordering, entity reuse, and atomic failure when any entity cannot be converted. |
| Physics-launch trajectories | Translate native mode 8 to CoDOL mode 9, preserve linear/angular launch deltas and duration, and encode the script-mover entity. Actual client rigid-body simulation remains an integration check. |

The isolated Bog script fixture also runs assertions in the actual native VM,
including path nodes, vehicle nodes and PhysicsLaunchClient. The full-reference
startup probe finds the next real script/asset integration failure. Both are
stronger than binding-count checks, but neither establishes live match entry.

The remaining end-to-end test is an authenticated CoDOL client entering a map,
receiving valid gamestate/snapshots, moving, switching/firing weapons and running
the full gametype. The live snapshot writer and unresolved gameplay/asset/script
semantics still prevent claiming that outcome.
