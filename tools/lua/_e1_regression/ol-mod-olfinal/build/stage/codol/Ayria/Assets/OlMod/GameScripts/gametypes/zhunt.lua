-- Free-for-all. The client books this as the playlist token "ffa"; the engine
-- gametype - and so this file's name - is "dm", which is the stock IW name.
--
-- There are no map game objects: playlist 23 carries no objective of any kind,
-- and the shipped description is "Eliminate the enemies to score. First player
-- to reach the score limit wins."

print("gametype has no map gameobjects", "dm")

-- Free-for-all has no sides. Every player is left at team None, which makes
-- issameteam false for every pair, so the only self-kill check needed is the
-- attacker not being the victim. There is deliberately no addteamscore here -
-- that is the one line that separates this from cha.
assert(codol.on("player_killed", function(player, event)
    if event.attacker_entity_num ~= nil and
        event.attacker_entity_num ~= event.target_client_num then
        local attacker = codol.player(event.attacker_entity_num)
        -- Two counters, in two different units, exactly as cha keeps them.
        -- addscore is the DISPLAY score at 50 a kill; addkill is the one the
        -- score limit reads, at 1 a kill, and is free-for-all's stand-in for
        -- cha's addteamscore. The shipped limit is 30, so awarding only the
        -- display score would end the match on the first kill.
        -- 50 is MEASURED, not cha's 100: the retail dm server sets
        -- ui_DMKillScore "50" at serverTime 0 and its score popup carries 50.
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
