-- BattleCity. The client books this as "dmz"; the mode is Brave Games / battle
-- royale, and Activision stripped its logic when the game shut down. This file
-- was a byte-for-byte copy of dm.lua until now, which is why the mode played as
-- deathmatch.
--
-- WHAT IS ACTUALLY MISSING IS SMALLER THAN IT LOOKS. The ASSETS survived the
-- strip -- mp_battlecity's model band publishes the whole pickup set, the
-- parachute, the care-package pod and the play-area cylinder (dumped with
-- OLMOD_DUMP_MODEL_BAND=1, 283 entries). Only the script that places them is
-- gone. This is step one of putting it back: loot you can walk up to and see.
--
-- PICKUP IS PRESS-USE, NOT WALK-OVER, and that is what retail does. The dmz
-- demo shows `cursorHint` going 0 -> 1 with `cursorHintEntIndex` naming the crate
-- while the player stands at it, and the weapon arriving only afterwards -- so
-- the player asks and the server answers. Walking over loot in a battle royale
-- and having it grabbed for you would be wrong anyway.
--
-- The bridge still refuses entity_touch, so none of this is done here: setloot
-- registers what is in a crate, and the server does the range test, the prompt
-- and the grant. See ServerCore::driveCursorHints / processLootCommittedCommand.
--
-- WHAT THIS DOES NOT DO YET, so nobody reads more into it than is here:
--   * the circle is not drawn. fx_dmz_cylinder and fx_dmz_intersect_ring are in
--     the band, so the geometry is a model rather than custom rendering, but
--     nothing shrinks or damages yet.
--   * a picked-up gun replaces the last one rather than filling a second slot,
--     because the server holds exactly one grant per player.

print("gametype has no map gameobjects", "dmz")

-- The pickup set mp_battlecity ships. Every name here was read out of the live
-- model configstring band; spawnmodel refuses anything the map does not
-- publish, so this list is not a guess and must not be extended by guessing.
local LOOT_MODELS = {
    "bc_pickups_mountains_ammo_pistol_sh",
    "bc_pickups_mountains_ammo_shotgun_sh",
    "bc_pickups_mountains_ammo_sniperrifle_sh",
    "bc_pickups_mountains_ammo_weapon_sh",
    "bc_pickups_mountains_attachment_sh",
    "bc_pickups_mountains_perk_sh",
    "bc_pickups_mountains_recover_sh",
    "dmz_pickups_armor",
    "orbital_carepackage_pod_01_sh",
}

-- Far enough not to stand inside a crate, close enough to be on screen the
-- instant the map loads. This is a bring-up value, not a design one.
local LOOT_RADIUS = 150

-- WHAT IS IN EACH CRATE, one per model above and in the same order.
--
-- COUNTING UP FROM firstDynamicWeapon, WHICH IS 1147 ON THIS MAP. The server
-- registers its modular weapons contiguously from there -- see
-- SV_RegisterModularWeaponConfigString -- so the real ones are 1147, 1148, 1149
-- and so on for as many as the classes produced, and there is no way to know
-- from here how many that is.
--
-- THE LOOT BAND IS NOT THAT LIST, which is the trap this walked into. cs
-- 12506..12692 advertises 1148..1211 because it is a verbatim replay of a RETAIL
-- capture, and retail had 1211 weapons registered where this server has eight.
-- Six of the nine crates below were handing out real guns and three were naming
-- nothing at all.
--
-- setloot NOW REFUSES A WEAPON THAT DOES NOT RESOLVE, so an index past the end
-- prints "loot contents failed" against the crate that asked for it. That is the
-- measurement: whatever the last successful line says is how many this server has.
local LOOT_WEAPONS = {
    1147, 1148, 1149, 1150, 1151, 1152, 1153, 1154, 1155,
}

-- HOW CLOSE COUNTS. The ring puts crates about 105 units apart, so this is
-- comfortably inside "the one I am standing at" without two of them ever being
-- the nearest at once. The server picks the closest anyway if they do overlap.
local LOOT_PICKUP_RADIUS = 72

-- SPAWN THE LOOT EXACTLY ONCE. client_spawned fires on every respawn, and the
-- entity pool is finite -- dynamic numbers start at 37 -- so a ring per death
-- would exhaust it and then fail silently, which is the hard kind of bug to
-- read in a log.
local loot_placed = false
local loot = {}

local function place_loot_around(player)
    local origin, origin_error, origin_error_code = codol.call(
        "method:getorigin", player)
    if origin == nil then
        print("loot origin unavailable", origin_error, origin_error_code)
        return
    end

    for index, model in ipairs(LOOT_MODELS) do
        -- ipairs is 1-based, so subtract one before dividing the circle or the
        -- first and last crate land on top of each other.
        local angle = (index - 1) * (2 * math.pi / #LOOT_MODELS)
        local x = origin[1] + LOOT_RADIUS * math.cos(angle)
        local y = origin[2] + LOOT_RADIUS * math.sin(angle)
        -- Same z as the player: these are ground pickups and the player is
        -- standing on the ground. There is no ground trace exposed to script,
        -- so a crate on a slope will float or sink until one is.
        local entity, spawn_error, spawn_error_code = codol.call(
            "function:spawnmodel", model, x, y, origin[3])
        if entity == nil then
            -- nil with no error is the pool refusing, which is expected once
            -- the dynamic region fills. nil WITH an error is a real fault.
            if spawn_error ~= nil then
                print("loot spawn failed", model, spawn_error, spawn_error_code)
            else
                print("loot spawn refused, entity pool is full", model)
            end
        else
            loot[#loot + 1] = entity
            print("loot placed", model, x, y, origin[3])
            -- AND WHAT IS IN IT. Without this the crate is scenery: the server
            -- has no reason to offer it and no answer if the player presses use.
            local weapon = LOOT_WEAPONS[index]
            local set, set_error, set_error_code = codol.call(
                "method:setloot", entity, weapon, LOOT_PICKUP_RADIUS)
            if set == nil then
                print("loot contents failed", model, weapon,
                    set_error, set_error_code)
            else
                print("loot contents", model, weapon, LOOT_PICKUP_RADIUS)
            end
        end
    end
    print("loot ring complete", #loot, #LOOT_MODELS)
end

-- THE TIMED TEST GRANT IS GONE. It existed because nothing could be picked up,
-- so a gun had to appear on its own to prove the grant survived the pmove. It
-- does, and now a crate can hand one over, so a rifle materialising five seconds
-- into every life would only get in the way of testing the real path.
--
-- `method:giveweapon` is still there and still takes either a name or a raw
-- modular index; the pickup path calls the same world function underneath.

assert(codol.on("client_spawned", function(player, event)
    if not loot_placed then
        loot_placed = true
        place_loot_around(player)
    end
end))

-- Scoring and respawn are still deathmatch's, deliberately. Replacing them is a
-- separate job from proving loot reaches the world, and a battle royale with no
-- respawn and no loot to fight over is not testable.
assert(codol.on("player_killed", function(player, event)
    if event.attacker_entity_num ~= nil and
        event.attacker_entity_num ~= event.target_client_num then
        local attacker = codol.player(event.attacker_entity_num)
        local _, score_error, score_error_code = codol.call(
            "method:addscore", attacker, 50)
        if score_error ~= nil then
            print("player score deferred", score_error, score_error_code)
        end
        local _, kill_error, kill_error_code = codol.call(
            "method:addkill", attacker, 1)
        if kill_error ~= nil then
            print("player kill deferred", kill_error, kill_error_code)
        end
    end

    local _, respawn_error, respawn_error_code = codol.call(
        "method:respawn", player, 3000)
    if respawn_error ~= nil then
        print("player respawn deferred", respawn_error, respawn_error_code)
    end
end))

codol_friendly_fire_mode = 0
