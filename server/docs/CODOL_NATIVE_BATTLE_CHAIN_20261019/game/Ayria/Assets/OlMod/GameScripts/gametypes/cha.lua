local _, error_message, error_code = codol.call(
    "function:setmapgameobjects",
    "cha",
    "airdrop_pallet")
assert(
    error_message == nil,
    tostring(error_message) .. ":" .. tostring(error_code))

print("gametype map gameobjects activated", "cha")

-- Charge is a team deathmatch variant with recurring fixed-team spawns.
-- The script owns respawn policy; C++ only validates and schedules the
-- authoritative player spawn transition.
assert(codol.on("player_killed", function(player, event)
    if event.attacker_entity_num ~= nil and
        event.attacker_entity_num ~= event.target_client_num then
        local attacker = codol.player(event.attacker_entity_num)
        local same_team, team_error = codol.call(
            "method:issameteam", player, attacker)
        if team_error == nil and not same_team then
            -- TODO(CODOL): source these defaults from the authoritative
            -- playlist/game-rule teamScorePerKill and rank score owners.
            local _, score_error, score_error_code = codol.call(
                "method:addscore", attacker, 100)
            local _, team_score_error, team_score_error_code = codol.call(
                "method:addteamscore", attacker, 1)
            if score_error ~= nil then
                print("player score deferred", score_error, score_error_code)
            end
            if team_score_error ~= nil then
                print(
                    "team score deferred",
                    team_score_error,
                    team_score_error_code)
            end
        end
    end

    local _, respawn_error, respawn_error_code = codol.call(
        "method:respawn", player, 3000)
    if respawn_error ~= nil then
        print("player respawn deferred", respawn_error, respawn_error_code)
    end
end))

codol_friendly_fire_mode = 0
