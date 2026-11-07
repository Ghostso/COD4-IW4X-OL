-- CODOL story missions use the engine gametype token "coop". Mission progress,
-- actors, objectives, checkpoints, and presentation belong to the map layer;
-- the gametype layer only establishes rules shared by every story mission.

print("campaign gametype initialized", "coop")

-- Story allies must not damage one another. The Wetwork map carries allied
-- Price, Nikolai, and hazmat actor spawners and places the player on their side.
-- Enemy damage remains authoritative because issameteam is false across sides.
codol_friendly_fire_mode = 0

-- There is deliberately no PvP score, kill, or timed-respawn handler here.
-- The former file was a stale copy of dm.lua and awarded FFA points before
-- respawning the player after every death. Wetwork death and checkpoint restart
-- are mission state transitions and will be owned by the cargoship map layer.
