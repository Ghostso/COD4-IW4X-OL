# Heartbeat sensor enable-state omission — 2026-09-14

C1 sensor capability is not merely its model. Shipped common_gametype_mp
weaponattach heartbeat_shareda has six overrides: source758 (kind13), bed
(kind6 boolean), and materials52c/530/534/538 (kind12), including
motiontracker3d_bg, enemy/friendly pings and sweep. The selected descriptor
already carries the attachment; no event-to-ordinary alias relaxation is needed.

Missing native player input/producer found:

- C1 generic client field tableC3C258: motiontrackerenabled, integer client35a8.
- C1 spawn50f31b sets client35a8=1, next to corpse-index and viewlock defaults.
- Renderer451f10 calls4535c0 to resolve selected weapon (ps33c, alternate340),
  requires weapon bytebed nonzero at451f1d AND playerState22c nonzero at451f39,
  then rejects jamming through4715e0. Update45241c..452435 repeats these gates.
- Native radar handled21c/220/224/228 but had no22c producer and no registered
  motiontrackerenabled field. Player netfield22c is one bit, initialized zero.

Implemented missing integer script input using existing radar client slot2,
with C1 spawn default1. Existing connection/map/spawn reset paths own its reset;
explicit script0 remains0 until reset. Weapon capability is still required by
C1; this does not force sensor rendering on unrelated weapons. Frame publisher
captures input!=0 in playerState extension radar_types.motion_tracker. Snapshot
22c reads that copied extension, never current live input. Extension archive
writes/reads/validates the new one-bit value in its radar block. Existing
spectator/playerState copy semantics therefore carry the followed frame value.

Changed files: codol_radar_types.c/.h, codol_playerstate_ext.c,
g_client_fields.cpp. No source offsets equated across engines, no hooks, no
client assets or weapon model substitutions. The exact C1 frame-copy instruction
was not recovered; spawn/field registration/render consumers establish the
required native representation and producer contract.

Status: source written and locally reviewed; parent build/live verification
pending. This fixes a proven sensor-screen enable gate. Target blip visibility,
range and immunity remain separately unverified. No automated tests, build,
UI action or process modification performed by worker.
