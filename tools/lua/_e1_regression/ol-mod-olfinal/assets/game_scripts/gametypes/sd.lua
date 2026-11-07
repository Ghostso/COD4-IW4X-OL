local _, error_message, error_code = codol.call(
    "function:setmapgameobjects",
    "sd",
    "bombzone",
    "blocker",
    "airdrop_pallet")
assert(
    error_message == nil,
    tostring(error_message) .. ":" .. tostring(error_code))

print("gametype map gameobjects activated", "sd")

-- CODOL/COD team modes use 0=no damage, 1=target, 2=half reflect,
-- 3=half shared. Mode selection remains gametype-owned.
-- TODO(CODOL): source this default from authoritative playlist/game rules.
codol_friendly_fire_mode = 0
