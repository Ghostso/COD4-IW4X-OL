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
        -- CODREF: IW4 _rank.gsc registers 50 XP for a teamless kill and 50
        -- more for a headshot. CODOL's retail DM trace independently confirms
        -- the 50-point base: an ordinary kill moves the AAR row XP 50 farther
        -- than aarTotalBonusXP. Keep progression awards beside scoring rather
        -- than deriving them later from presentation medals.
        local _, xp_error, xp_error_code = codol.call(
            "method:addxp", attacker, 50)
        if xp_error ~= nil then
            print("player xp deferred", xp_error, xp_error_code)
        end
        if event.hit_location == 1 or event.hit_location == 2 then
            local _, headshot_xp_error, headshot_xp_error_code = codol.call(
                "method:addxp", attacker, 50)
            if headshot_xp_error ~= nil then
                print("player headshot xp deferred", headshot_xp_error,
                    headshot_xp_error_code)
            end
        end
        local _, kill_error, kill_error_code = codol.call(
            "method:addkill", attacker, 1)
        if kill_error ~= nil then
            print("player kill deferred", kill_error, kill_error_code)
        end
    end

    -- 1500 IS MEASURED. C-2021-7-25[1-19-26]dm.demo, mp_cross_fire, 8 clients: the recording
    -- client's playerState pm_type goes 0 -> 8 on death and 8 -> 0 when it is controllable
    -- again, and across the whole match that gap is
    --     n=24   min 1500   p25 1500   median 1500   p75 1500   max 1600
    -- with 23 of the 24 at exactly 1500. The single 1600 is one serverTime step; this demo's
    -- snapshots are 100 ms apart. p25 == median == p75, so it is a constant, not a computation.
    --
    -- 3000 WAS INVENTED and it was twice too slow.
    --
    -- MEASURED ON pm_type, NOT ON THE UI VERB, and the difference matters. The first pass timed
    -- `u 10` (death screen) to `u 11` (alive) and got median 1500 with a tail to 2500 -- which
    -- reads as "1500 plus something unidentified". It is not: that window also encloses the
    -- killcam, so it measures when the SCREEN closes. pm_type is the engine's own movement state
    -- and is what decides whether the player can move. Two instruments disagreed on the first
    -- death (1500 vs 2200) and the one that actually wraps the quantity won.
    --
    -- STILL UNMEASURED: whether this varies with anything -- gametype, player count, killcam on
    -- or off. One 8-player mp_cross_fire match cannot say, and it is the ONLY dm demo in the
    -- 84-demo corpus. dmz cannot stand in for it: that is BATTLE ROYALE (playlist 199,
    -- "BattleCity - SOLO"), and a single-life mode has no respawn delay to compare against.
    local _, respawn_error, respawn_error_code = codol.call(
        "method:respawn", player, 1500)
    if respawn_error ~= nil then
        print("player respawn deferred", respawn_error, respawn_error_code)
    end
end))

codol_friendly_fire_mode = 0
