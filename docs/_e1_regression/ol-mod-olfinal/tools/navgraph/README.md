# CODOL Navgraph Editor — portable preview

Copy this directory into any folder. Open **Open-Editor.cmd**, or open **Editor.html** directly in a current browser. No installation, account, Python, game or server is required for offline editing. Everything needed by the page is embedded; there are no remote libraries or uploads.

The supplied example is the Factory teleporter-room draft with the latest preserved edits (85 nodes). It is an authoring draft, not a claim that this custom graph is currently active in the game. Keep your original export as a backup.

## Five-minute acceptance test

1. Click a connection away from its endpoints. Press **Delete**, then **Ctrl+Z** to restore it.
2. Select a point, press **C**, then click another point that is not already connected. Press **Esc** to finish the chain.
3. Set XYZ values, press **A**, and click to place a point. The hidden axis uses its XYZ field. In top view this is height Z.
4. Select that point, change Z, and click **Apply XYZ**. Use **2** and **3** to inspect it in side views; **1** returns to top view.
5. Press **Ctrl+S** to export. Reload the page and use **Reopen edited JSON** to load your export. Confirm the added point, height and connection survived.
6. Move the whole extracted folder elsewhere and reopen it. Nothing should depend on its previous path.

Report editor PASS/FAIL and the step involved. Do not replace your accepted graph with the temporary edits from this test.

## Shortcuts

Each shortcut also appears on its own line in the editor.

| Key | Action |
| --- | --- |
| V | Select point or connection |
| C | Connect a chain from the selected point |
| A | Place a point |
| Delete | Delete selection |
| Ctrl+Z / Ctrl+Y | Undo / redo |
| Ctrl+S | Export JSON |
| 1 / 2 / 3 | XY / XZ / YZ view |
| P | Add fresh live player position |
| F | Center on live player |
| Esc | End chain / cancel |

Wheel zooms. Right-drag pans. Shortcuts affect this editor only while it has focus. Export before closing; there is no automatic save.

## Optional live player marker

Requires Python 3.10+ (standard library only) and a compatible server emitting `ACTORROUTE` player diagnostics. Run **Start-Live.cmd** and select **your** `CodolGameServer.log`; the browser opens automatically. Alternatively:

```
python live.py --log "path/to/CodolGameServer.log" --open
```

Walk normally in the teleporter room. **P** adds a fresh position; it never automatically connects it. Stale, inactive, outside-room, duplicate and excluded ledge samples are rejected. The adapter only reads new log lines; it does not launch, inject into, control or modify the game. It listens on loopback only and stops when its console closes. Its random local URL belongs to that session. No administrator rights are needed.

`live-config.json` selects player slot, room XY bounds, freshness and the probe offset. Coordinates are game units: stored probe Z is player-foot Z **plus 32**. This feed cannot prove the player is grounded or detect noclip. Different server log formats require a separate adapter.

## Validate an export for integration

The browser rejects exports with a different base identity. A matching export can also be checked with Python:

```
python validate-export.py "my-edited.nav.json" --output "review-output"
```

Choose a new output directory. The validator saves the original, normalized review graph and change receipt. It checks structure and provenance, not live collision. The included `room-v2-base.json` anchors this specific room revision. It is not a universal importer for arbitrary map formats.

Connections here are undirected authoring corridors. This version does **not** create directed jump/vault/door links or modify existing native traversal ownership. Keep those integration instructions separate. Cyan paths preserve captured bends; amber paths are manual proposals. No map walls are rendered, and no connection is certified walkable. Runtime integration must check floor, body clearance, gates and native traversal boundaries before enabling edges. Exporting or validating never installs a graph.

## Build the first custom Factory room

This tool and the first room patch form one candidate. The patch is opt-in; it is not enabled by opening the editor. Save an export and run from the repository root:

```
python tools/navgraph/compile-room.py tools/navgraph/Example-Factory-Room.nav.json --output src/game_server/server_mp/sv_zm_factory_room_data.hpp
```

Rebuild using the repository build instructions. Before starting the dedicated server, set `OLMOD_ZM_NAV_SOURCE=bo1_hybrid` and `OLMOD_FACTORY_ROOM_DRAFT=1`. Use Factory only. Remove the second variable to restore the unmodified hybrid graph. Ordinary multiplayer is unaffected by the room hook.

Verify **FACTORYROOM applied** in the server log before accepting a room test. Fully isolated non-port points whose links all fail clearance are omitted and identified in `omittedLocalIds`; no replacement links are created. Disconnected multi-point sections and required ports still reject atomically. A rejection retains the entire previous graph; it is not a custom-room success. Rejected link endpoints are local offsets into the generated Points array; its comments give editor IDs. Do not disable collision checks to make an export apply. Correct the reported point or corridor in the editor and regenerate.

The binding manifest explicitly connects local:440 to the existing door approaches, local:441/442 to the two existing window landings, and local:409 to an ordinary existing route. These bindings never replace barrier breaking or vault ownership. Local:372/396 is not a new directed jump; the existing path around it remains. The replacement footprint and ports are specific to this first room and require review before adapting to another room. Standalone unconnected local:330 is omitted and reported by the compiler.

## Package contents

`Editor.html` is the standalone application. `Example-Factory-Room.nav.json` is the starting editable example. `model-v2.js` is the readable model source. `live.py` and `live-config.json` provide optional position support. `validate-export.py` validates exports. No binaries, accounts, certificates, game assets or machine-specific paths are included.
