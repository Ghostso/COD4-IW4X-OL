-- Zombies. The client books this as gametype "zm"; retail serverinfo, byte-identical
-- across all three zm_factory_sh demos, is:
--
--     \g_gametype\zm\g_hardcore\0\mapname\zm_factory_sh
--     \scr_game_allowkillcam\0\scr_team_fftype\0
--
-- Until this file was written it was a BYTE-IDENTICAL COPY OF dm.lua -- free-for-all
-- rules, including awarding 50 display score and a kill for shooting another player.
-- That is exactly backwards for a co-operative mode and is the first thing corrected
-- here.

-- Zombies has no bombzone, blocker or airdrop_pallet; there is no objective to bind.
-- Retail's own zombie map objects -- the mystery box (`d 3627 zmb_box_poof` in the
-- demo), doors, power -- are not map gameobjects in this sense and have no builtin.
print("gametype has no map gameobjects", "zm")

-- Every player is a survivor on the same side, so no player should ever damage
-- another. Mode 0 is "no damage" and it matches retail's `scr_team_fftype\0`.
codol_friendly_fire_mode = 0

-- THE ZOMBIE MODEL, PRECACHED BEFORE ANYTHING SPAWNS.
--
-- The client resolves the agent element's model INDEX against its own configstring
-- band, and that band holds only what this server has transmitted. Loading the same
-- map does NOT give the client the dedicated's band: index 308 was empty on the
-- client, so the actor record's model name stayed "" and the client built no DObj at
-- all. Zombies were on the wire, validated, and invisible.
-- re/demo-re/20-zm-actor-lifecycle.md 12.21.
--
-- HERE, AT SCRIPT LOAD, because this publishes into the gamestate and so has to
-- happen before a client is served one. Publishing it at spawn time instead is a live
-- configstring change and the client could not enter the session at all.
--
-- The name is declared ONCE and reused by every spawn below. It is read off the map's
-- own actor_zombie_* entities, but note those entities also name models this script
-- does NOT spawn, so the script is the authority on which one to precache.
-- MEASURED OUT OF THE RETAIL CAPTURE, NOT CHOSEN. During playback of
-- C-2021-7-31[15-32-16]zm (zm_factory_sh) the client's own 684-byte actor records
-- read back, at record+568 (the model) and record+52 (the first attachment):
--
--     rec0 ent=723  c_zom_garbageman_body_blue    + c_zom_garbageman_head
--     rec1 ent=724  c_zom_worker_body_blue        + c_zom_worker_head
--     rec2 ent=725  c_zom_ger_body_blue           + c_zom_ger_head
--     rec3 ent=726  c_zom_secunityguard_body_blue + c_zom_secunityguard_head
--
-- So retail's German zombie is `c_zom_ger_body_blue`, NOT `c_zom_ger_body1`, which
-- this script used to send. Both assets exist in the client, but only the _blue one
-- is in the band the client resolves against -- which is why index 308 came back as
-- an empty name and no DObj was ever built. re/demo-re/20-zm-actor-lifecycle.md 12.25.
--
-- THE HEAD IS A SEPARATE ATTACHMENT and is not sent yet; body first.
zm_actor_model = "c_zom_ger_body_blue"
-- THE HEAD IS A SEPARATE ATTACHMENT. Retail pairs one with every body -- read live
-- out of the client's own actor records, record+52 beside record+568:
--     c_zom_ger_body_blue           + c_zom_ger_head
--     c_zom_worker_body_blue        + c_zom_worker_head
--     c_zom_garbageman_body_blue    + c_zom_garbageman_head
--     c_zom_secunityguard_body_blue + c_zom_secunityguard_head
-- It goes out as agentState field 13 (+0x014); attachment slot 1 is asserted as 0
-- alongside it because its default is 1317 and retail clears it. 12.25 / 12.29.
zm_actor_head = "c_zom_ger_head"
-- DISABLED, AND THE RESULT IS THE POINT: publishing this configstring KILLS THE
-- CLIENT. Measured 2026-09-02 00:40 --
--     actor model PUBLISHED index=308 cs=2876 name=c_zom_ger_body1
--     zm actor model precached c_zom_ger_body1
--     clients=1 active=1 snapshots=139   then   client timeout client=0
-- The client connected AFTER the publish, ran ~15 s and timed out.
--
-- This was the careful version: the configstring ALONE, no `|` precache, at script
-- load rather than at spawn. So neither the precache command nor the timing is the
-- cause -- writing cs 2876 is by itself fatal. Both earlier theories (12.21, 12.22)
-- are therefore wrong, and the remaining suspects are the INDEX (308 is the
-- dedicated band's, and may simply not be the client's slot for this model) and
-- SV_SetConfigString into the model band at all.
--
-- The builtin stays registered and works; only this call is off. Re-enable it when
-- there is a reason to believe the index, not before.
-- local precached, precache_error, precache_code =
--     codol.call("function:precachemodel", zm_actor_model)

-- THE ZONE MODEL. The server parses zm's zone/spawner layout straight out of the map
-- entity string and exposes it here. STEP 2 OF THE ZOMBIE WORK: NOTHING SPAWNS YET.
-- This walks the model and prints it, so that the script's view of the map is proven
-- before anything is built on top of it.
--
-- INDEX-BASED AND ONE-BASED. A builtin cannot hand Lua a structure -- the value type
-- has no table variant -- so the model is walked with counts and indices instead.
-- Zones are ordered by name, so an index is stable for a given map.
--
-- The numbers to expect, measured off the shipped maps in
-- re/demo-re/21-zm-zones-and-spawners.md:
--     zm_factory_sh   12 zones / 63 spawn points
--     zm_sumpf_sh     11 zones / 74
--     zm_prototype_sh  3 zones / 41
--     zm_asylum_sh     9 zones / 38
-- Set by the round director below, and left nil on a map with no zone model. The
-- entity_killed handler at the bottom of this file is registered unconditionally and
-- has to tolerate that.
local zm_actor_died

local zone_count, zone_count_error = codol.call("function:zmzonecount")
if zone_count == nil then
    -- Not a failure to stop on: a non-zm map has no zone model, and this file also
    -- loads before anything depends on one.
    print("zm zone model unavailable", zone_count_error)
else
    local total_points = 0
    for zone = 1, zone_count do
        local name = codol.call("function:zmzonename", zone)
        local points = codol.call("function:zmzonespawncount", zone)
        total_points = total_points + (points or 0)
        print("zm zone", zone, name, points)
    end
    -- One origin, to prove a vector survives the crossing. It arrives as a
    -- one-based table of three numbers.
    local first_origin = codol.call("function:zmspawnorigin", 1, 1)
    local first_goal = codol.call("function:zmspawngoal", 1, 1)
    if first_origin ~= nil then
        print("zm first spawn point",
            first_origin[1], first_origin[2], first_origin[3], first_goal)
    end
    -- POINT-IN-ZONE, AGAINST A POINT PREDICTED BEFORE THIS EVER RAN.
    -- zm_factory_sh's info_player_start is at (16, 122, 131). Both the exact k-DOP
    -- test and the AABB the server actually uses put it in receiver_zone and in NO
    -- other zone (re/demo-re/21-zm-zones-and-spawners.md section 21b). Anything else
    -- printed here means the bounds resolution is wrong, not that the map is odd.
    -- The point is factory-specific; on another map this line is meaningless.
    local at = codol.call("function:zmzoneat", {16, 122, 131})
    -- EXPECTED: receiver_zone. The volume shapes now come out of MapEnts.trigger
    -- exactly, hulls and slab planes included, so this is the true k-DOP answer and
    -- not a bounding box. Anything else means the trigger arrays were misread.
    print("zm zone at factory info_player_start", at)
    print("zm zone model visible to the script", zone_count, total_points)

    -- SPAWN ON THE MAP'S OWN ZOMBIE SPAWNERS, IN THE ZONE THE PLAYERS START IN.
    --
    -- MEASURED, not chosen. re/demo-re/20-zm-actor-lifecycle.md 12.31: every retail
    -- actor's first asserted position in C-2021-7-31[15-32-16]zm decodes to within a
    -- few units of a `script_struct` whose script_noteworthy is "zombie_spawner",
    -- and factory carries exactly 63 of them -- the same 63 the zone model parses.
    -- Two of the eight sampled were within SEVEN units, which is the spawn instant
    -- caught exactly. So zmspawnactor(zone, point) already spawns where retail does.
    --
    -- THE RING OF FOUR IS GONE. It placed zombies 200 units around the player's own
    -- spawn, which is not a thing retail ever does; it existed only to get one in
    -- view before anything drew. Nothing needs it now.
    --
    -- The zone is resolved BY GEOMETRY, not by name: zmzoneat answers which volume
    -- contains the map's player start, so this works on any zm map instead of only
    -- the one whose start zone happens to be called receiver_zone.
    local home_zone
    for zone = 1, zone_count do
        if codol.call("function:zmzonename", zone) == at then
            home_zone = zone
        end
    end
    if home_zone == nil then
        -- Standing outside every volume is a legitimate answer (21b), so a map whose
        -- start point is not inside a zone falls back rather than spawning nothing.
        print("zm start zone unresolved, falling back to zone 1", at)
        home_zone = 1
    end

    -- THE ROUND DIRECTOR.
    --
    -- WHAT THIS REPLACES: a single burst of four actors at map load, drawn from every
    -- zone but the players' own, where a refusal abandoned that zone's whole turn.
    -- 12.159 measured three of seven attempts refused and the four survivors walking
    -- to the players by open routes and then looping forever.
    --
    -- WHAT IS RETAIL HERE AND WHAT IS NOT:
    --   ADJACENCY IS.        Retail's director draws from the players' zone and the
    --                        zones next to it, never the far side of the map.
    --   THE SPAWN POINTS ARE. They are the map's own `zombie_spawner` structs, and
    --                        12.31 measured retail spawning on these very structs.
    --   THE COUNTS ARE NOT.  Retail's per-round wave sizes are not measured yet, so
    --                        the curve below is a placeholder and is marked as one.
    --                        Do not read it as a claim about retail.
    --   THE ROUND END IS NOT. A round should end when the wave is dead. Actors carry
    --                        no damage state -- spawnZombieActor registers none and
    --                        no builtin counts living ones -- so NOTHING CAN KILL A
    --                        ZOMBIE YET and the round advances on a timer instead.
    --                        That is the next piece of work, not a design choice.
    -- MEASURED OFF A SOLO ZM DEMO ON THIS MAP, rounds 2-4 identified by their HUD
    -- (12.165). Everything here replaces an invented value.
    --
    --                    round 2   round 3   round 4
    --   spawned             29        34        39      +5 per round
    --   peak alive          27        30        31      rises with the round
    --   round length        86 s      65 s       -
    --   pause before        11.8 s    10.8 s    11.5 s
    --
    -- THE SPAWN SHAPE IS NOT A FLAT TIMER. A round opens with a fast burst up to the
    -- concurrency cap -- 18 actors in about 5 s -- and then trickles at ~1.5 s to
    -- replace deaths until the quota is spent. This server used to spawn at a flat
    -- interval from an empty start, which is why waves took a minute to build.
    --
    -- A SECOND DEMO ON THIS MAP DISAGREES and is deliberately NOT merged in: it
    -- showed 68-72 spawned per round and 36-42 s pauses. It is a different
    -- recording of unknown player count. This one is solo and its rounds are
    -- identified, so it is the authority for a one-player game. If a per-player
    -- multiplier is ever wanted, that other capture is the second data point.
    -- Milliseconds throughout. The server now raises this director every 100 ms;
    -- flooring to whole seconds made the measured 300/400 ms timings impossible.
    local ROUND_ONE_DELAY = 5500   -- first round: first actor at +5.5 s
    local NEXT_ROUND_DELAY = 400   -- rounds 2-8: first actor at +0.4 s
    local ROUND_PAUSE = 11000      -- measured 10.8-11.2 s
    local SPAWN_BACKOFF = 10000    -- wait after a whole sweep refuses
    local ROUND_SECONDS = 240000   -- backstop only
    local ROUND_GOAL = 8           -- what the round HUD counts towards

    local round = 0
    local round_started_at = nil
    local round_cleared_at = nil
    local next_spawn_at = nil
    local spawned_this_round = 0
    local alive = 0
    local active_actors = {}

    zm_actor_died = function(event)
        local actor = event and event.target_entity_num
        if actor == nil or active_actors[actor] ~= true then return end
        active_actors[actor] = nil
        alive = math.max(0, alive - 1)
        print("zm actor died", actor, "round", round, "alive", alive)
    end

    -- SPAWNER SELECTION IS ROUTE-BASED, NOT A ZONE-NAME WEIGHT.
    --
    -- The first-position association that produced a 17 receiver / 8 west split is
    -- not strong enough to drive the live director: receiver points 7/8 and west
    -- points 3/5 occupy the same two closets, only 43-63 units apart, while several
    -- first complete retail positions are already 140-300 units from either map
    -- struct. Treating nearest struct as an exact group made this script cycle every
    -- point in receiver/west, including open routes that can never touch a board.
    --
    -- `zmspawncrossesbarrier` asks the world router the actual question for the
    -- current player destination. Prefer those points among the occupied zone and
    -- its adjacent zones. This keeps the map's own zone/spawner data authoritative,
    -- spreads births across distinct closets, and guarantees that a boarded route
    -- is exercised whenever the local zone layout offers one. If a map/zone has no
    -- such route, retain the ordinary adjacent-zone pool rather than spawning none.
    local player_count = 0
    local factory_solo = false
    local factory_two_player = false
    local spawn_zones = {}
    local occupied_zone_name = nil
    local occupied_zone_source = "legacy-first-player"
    local no_eligible_cooperative_zones = false
    local active_zone_count = 0
    local next_zone_check_at = 0
    local first_director_tick = true
    local function zone_index(name)
        if name == nil or name == "" then return nil end
        for zone = 1, zone_count do
            if codol.call("function:zmzonename", zone) == name then
                return zone
            end
        end
        return nil
    end
    -- `cooperative-union-reconstruction` is an explicit OLMOD_ZM_COOP_SPAWN_ZONES=1
    -- experiment, not a recovered retail director rule. The native-side status
    -- query keeps the ordinary first-player path byte-for-byte in charge unless
    -- that option is enabled.
    local function read_occupied_zones(observed_name)
        local source = codol.call("function:zmcooperativezonesource") or
            "legacy-first-player"
        if source == "cooperative-union-reconstruction" then
            local zones = {}
            local names = {}
            local encoded = codol.call("function:zmcooperativespawnzones") or ""
            for token in string.gmatch(encoded, "[^,]+") do
                local zone = tonumber(token)
                if zone ~= nil then
                    zones[#zones + 1] = zone
                    names[#names + 1] = tostring(codol.call(
                        "function:zmzonename", zone))
                end
            end
            return zones, table.concat(names, "+"), source
        end

        local live_name = observed_name or codol.call("function:zmplayerzone")
        local zone = zone_index(live_name)
        if zone == nil then
            zone = home_zone
            live_name = codol.call("function:zmzonename", zone)
        end
        return {zone}, live_name, source
    end

    local function configure_spawn_zones(observed_name, observed_players,
        observed_zones, observed_signature, observed_source)
        player_count = observed_players or
            codol.call("function:zmplayercount") or 0
        if player_count < 1 then return false end
        active_zone_count = codol.call("function:zmactivezonecount") or 0
        factory_solo = zone_count == 12 and at == "receiver_zone" and
            player_count == 1
        factory_two_player = zone_count == 12 and at == "receiver_zone" and
            player_count == 2
        local occupied_zones = observed_zones
        local live_name = observed_signature
        local source = observed_source
        if occupied_zones == nil then
            occupied_zones, live_name, source = read_occupied_zones(observed_name)
        end
        -- A co-op frame may have no eligible living player while the player count
        -- still includes a corpse or a class screen. Pause rather than inventing a
        -- home-zone target. Legacy behaviour retains its existing home-zone fallback.
        if #occupied_zones == 0 then
            occupied_zone_name = ""
            occupied_zone_source = source
            spawn_zones = {}
            no_eligible_cooperative_zones = true
            print("zm has no eligible cooperative zone; spawning paused")
            return false
        end
        no_eligible_cooperative_zones = false
        occupied_zone_name = live_name
        occupied_zone_source = source
        local all_spawn_zones = {}
        local barrier_spawn_zones = {}
        local added_zones = {}
        local function add_zone(zone)
            if added_zones[zone] then return end
            added_zones[zone] = true
            -- Authored does not mean opened. The C++ progression owner activates
            -- the start zone initially and flips exactly one more zone when the
            -- purchased trigger's enter_* flag fires.
            if codol.call("function:zmzoneactive", zone) ~= 1 then return end
            local points = codol.call("function:zmzonespawncount", zone) or 0
            if points <= 0 then return end
            local name = tostring(codol.call("function:zmzonename", zone))
            local all_points = {}
            local barrier_points = {}
            for point = 1, points do
                all_points[#all_points + 1] = point
                local crosses = codol.call(
                    "function:zmspawncrossesbarrier", zone, point)
                if crosses == 1 then
                    barrier_points[#barrier_points + 1] = point
                end
            end
            all_spawn_zones[#all_spawn_zones + 1] = {
                zone = zone, point_ids = all_points, name = name
            }
            if #barrier_points > 0 then
                barrier_spawn_zones[#barrier_spawn_zones + 1] = {
                    zone = zone, point_ids = barrier_points, name = name
                }
            end
        end

        if source == "cooperative-union-reconstruction" then
            -- C++ has already formed the deterministic union of eligible players'
            -- occupied zones and active neighbours in one query. Do not rebuild the
            -- adjacency graph per Lua director tick.
            for i = 1, #occupied_zones do
                add_zone(occupied_zones[i])
            end
        else
            -- Established solo policy: occupied OPEN zone plus OPEN neighbours.
            for i = 1, #occupied_zones do
                local occupied_zone = occupied_zones[i]
                add_zone(occupied_zone)
                local neighbours =
                    codol.call("function:zmzoneadjacentcount", occupied_zone) or 0
                for n = 1, neighbours do
                    local zone = codol.call(
                        "function:zmzoneadjacentat", occupied_zone, n)
                    if zone ~= nil and zone ~= occupied_zone then add_zone(zone) end
                end
            end
        end

        local selection = "adjacent fallback"
        if #barrier_spawn_zones > 0 then
            spawn_zones = barrier_spawn_zones
            selection = "barrier routes"
        else
            spawn_zones = all_spawn_zones
        end
        local names = {}
        for i = 1, #spawn_zones do
            names[#names + 1] = spawn_zones[i].name .. ":" ..
                tostring(#spawn_zones[i].point_ids)
        end
        print("zm spawn zones",
            occupied_zone_name,
            "players", player_count, "source", occupied_zone_source,
            selection, "->", #spawn_zones,
            table.concat(names, ","))
        if #spawn_zones == 0 then
            -- Fail closed. Falling back to every authored zone is precisely how
            -- unopened rooms started spawning zombies before their doors were bought.
            print("zm has no active routable spawn zone; spawning paused")
        end
        return #spawn_zones > 0
    end

    -- THE PER-ROUND QUOTA AND THE CONCURRENCY CAP, both measured.
    --
    -- Full one-player factory rounds read directly from
    -- C-2021-7-31[15-32-16]zm.demo. The old 24/29/34/39 extrapolation was one low
    -- in every round. Round 9 is incomplete in the demo, so only its continuation
    -- (+2 from the late-round curve) remains an explicit inference.
    local solo_factory_waves = {25, 30, 35, 40, 45, 52, 54, 56, 58}
    -- The other two factory captures each carry two client rows. The complete
    -- 20-34-14 rounds measure 36/42/48/54/64/68/73 for rounds 2..8;
    -- 20-21-43 independently measures 68/72 for rounds 7/8. Round 1 (30) and
    -- final-round 76 are continuations, while round 8 uses the lower of the two
    -- actually observed values rather than pretending the one-actor spread does
    -- not exist.
    local two_player_factory_waves = {30, 36, 42, 48, 54, 64, 68, 72, 76}
    local function wave_size(n)
        if factory_solo then
            return solo_factory_waves[n] or (58 + 2 * (n - 9))
        end
        if factory_two_player then
            return two_player_factory_waves[n] or (76 + 4 * (n - 9))
        end
        return 25 + 5 * (n - 1)
    end
    -- THIS SERVER CANNOT HOLD RETAIL'S NUMBER, AND PRETENDING OTHERWISE COSTS 1.6 s
    -- A TICK.
    --
    -- Retail runs 27/30/31 concurrent at rounds 2/3/4 (12.165). This server allocates
    -- an agent slot per actor from `MaximumGameClients (18) .. SvAgentSlotCount (32)`
    -- -- FOURTEEN slots -- and `spawnZombieActor` refuses once they are gone.
    --
    -- With the cap set to the measured 26 the director believed it had room, every
    -- spawn past the 14th refused, and `spawn_one` ran its whole sweep (4 barrier
    -- points, then all 22) every tick with two 1024-configstring model resolves per
    -- attempt. Measured: `zm wave stalled ... 14 of 24` repeating, SCRIPTSLOW 1.0-2.3
    -- SECONDS per tick, thinkUs peaking at 8.3 s. The strike-out logic made it worse
    -- by clearing its counters whenever everything was struck out, so it never
    -- settled.
    --
    -- IDA's sub_471980 confirms a separate five-bit, 32-slot ACTORS namespace.
    -- The server now keeps players in CLIENTS on zm and returns a slot when an actor
    -- corpse is freed, so the measured solo peaks are representable.
    local ACTOR_SLOT_CAP = 32
    -- Retail reaches 25 living actors in round one for only 0.6 seconds: its first
    -- death follows immediately and the population then drains.  Our provisional
    -- actors do not yet have retail's complete damage/death lifecycle, so allowing
    -- that transient peak to become a permanent population leaves all 25 animtrees,
    -- routes and snapshots active forever.  Limit the provisional implementation to
    -- four live actors while pathing is validated. This is not a replacement wave
    -- size: keep the retail quota below and feed replacements after entity_killed
    -- until all 25 have lived. Raise this compatibility ceiling only after live actor
    -- processing stays inside the server-frame budget.
    local IMPLEMENTATION_ALIVE_CAP = 4
    local solo_factory_alive_caps = {25, 27, 30, 31, 31, 31, 31, 31, 31}
    local function alive_cap(n)
        local cap
        if factory_solo then
            cap = solo_factory_alive_caps[n] or 31
        elseif factory_two_player then
            cap = 31
        else
            cap = 25 + n
        end
        if cap > ACTOR_SLOT_CAP then cap = ACTOR_SLOT_CAP end
        if cap > IMPLEMENTATION_ALIVE_CAP then
            cap = IMPLEMENTATION_ALIVE_CAP
        end
        return cap
    end

    local function spawn_interval(round_number, spawned)
        if factory_solo then
            -- The burst applies to the first eighteen BIRTHS of each round. The
            -- previous code compared the ROUND NUMBER with 5/6, so rounds 1-5
            -- spawned their entire quota every 300 ms and dumped all 25 actors
            -- into one path before the first ones had cleared it.
            if spawned < 18 then return 300 end
            return 1500
        end
        if factory_two_player then
            if spawned < 18 then return 500 end
            return 1500
        end
        return 1500
    end

    local function round_opening_delay(n)
        if n == 1 then return ROUND_ONE_DELAY end
        if factory_two_player then
            -- 20-34-14 asserts the first birth 600 ms after the HUD in rounds
            -- 2..6 and 500 ms after it in rounds 7..8.
            return (n <= 6) and 600 or 500
        end
        return NEXT_ROUND_DELAY
    end

    -- ONE ACTOR, TRYING EVERY POINT OF EVERY ZONE UNTIL ONE TAKES.
    --
    -- THE REFUSAL FIX. `spawnZombieActor` refuses a spawn point whose goal the nav
    -- graph cannot walk -- 12.80, because spawning one is strictly worse than not:
    -- it holds an entity number, it is drawn, and it can never move. The old loop
    -- read that as "this zone is done", so bridge_zone, outside_south_zone and
    -- tp_east_zone each lost their whole turn to an unroutable point 1. Every point
    -- is tried now, and the cursor advances zone-major so a wave spreads across the
    -- adjacent zones instead of stacking on one.
    local cursor = 0
    -- REFUSAL COUNTS PER SPAWN POINT, and this is the whole performance fix.
    --
    -- MEASURED with SCRIPTSLOW: one zm_round_tick event took 74-497 MILLISECONDS,
    -- repeatedly, and that lands in the server's `thinkUs` window because the Lua
    -- dispatch runs inside the per-command loop the think timer wraps. On screen it
    -- was heavy lag and rubber-banding.
    --
    -- The cost is `zmspawnactor` re-resolving the body and head model BY NAME on
    -- every call: `resolveModelConfigStringIndex` walks up to 1024 configstrings
    -- doing string compares, plus a findXAsset, twice per attempt. Trying 22 points
    -- a tick is ~45,000 configstring reads a tick.
    --
    -- Routability is a property of the map's nav graph and does not change during a
    -- match, so a point that refuses will refuse again. Two strikes rather than one
    -- because a refusal is also what an exhausted entity pool returns, and that is
    -- transient -- both come back as WorldMutationFailed and the script cannot tell
    -- them apart. If every point ends up struck out the counters reset, so a
    -- transient wipeout heals instead of ending the mode.
    local refusals = {}
    local point_cursors = {}
    local function refusal_key(zone, point)
        return zone * 1000 + point
    end
    local function spawn_one()
        local count = 0
        for i = 1, #spawn_zones do
            count = count + #spawn_zones[i].point_ids
        end
        local attempts = 0
        local skipped = 0
        while attempts < count do
            cursor = cursor + 1
            attempts = attempts + 1
            local zone_at = ((cursor - 1) % #spawn_zones) + 1
            local c = spawn_zones[zone_at]
            local zone, name = c.zone, c.name
            point_cursors[zone] = (point_cursors[zone] or 0) + 1
            local point_at =
                ((point_cursors[zone] - 1) % #c.point_ids) + 1
            local point = c.point_ids[point_at]
            local key = refusal_key(zone, point)
            if (refusals[key] or 0) >= 2 then
                skipped = skipped + 1
            else
                local actor, actor_error, actor_code = codol.call(
                    "function:zmspawnactor", zone, point,
                    zm_actor_model, zm_actor_head)
                if actor ~= nil then
                    refusals[key] = nil
                    return actor, name, point
                end
                refusals[key] = (refusals[key] or 0) + 1
                if actor_code == nil then
                    print("zm spawn refused with no code", actor_error)
                end
            end
        end
        if skipped >= count and count > 0 and alive < alive_cap(round) then
            print("zm every spawn point struck out, clearing refusal counts")
            refusals = {}
        end
        return nil
    end

    local function begin_round(now)
        round = round + 1
        round_started_at = now
        round_cleared_at = nil
        next_spawn_at = now + round_opening_delay(round)
        spawned_this_round = 0
        local _, round_error = codol.call("function:zmsetround", round, ROUND_GOAL)
        if round_error ~= nil then
            print("zm round hud refused", round_error)
        end
        print("zm round begin", round,
            "wave", wave_size(round), "zones", #spawn_zones)
    end

    assert(codol.on("zm_round_tick", function(_, event)
        local now = (event and event.server_time) or 0
        if first_director_tick then
            first_director_tick = false
            local observed_players, player_error, player_code =
                codol.call("function:zmplayercount")
            local observed_zone, zone_error, zone_code =
                codol.call("function:zmplayerzone")
            print("zm director first tick", now,
                "players", observed_players, player_error, player_code,
                "zone", observed_zone, zone_error, zone_code)
        end
        if #spawn_zones == 0 then
            if not no_eligible_cooperative_zones and
                not configure_spawn_zones() then return end
        end
        -- Follow the player during the round. One second is quick beside the demo's
        -- 1.5-second late-round cadence, while avoiding a full zone-model copy on
        -- every 100 ms director tick. Empty means the player is between volumes;
        -- retain the last valid set until another volume contains them.
        if now >= next_zone_check_at then
            next_zone_check_at = now + 1000
            local observed_players =
                codol.call("function:zmplayercount") or player_count
            local observed_zone = codol.call("function:zmplayerzone")
            local observed_active =
                codol.call("function:zmactivezonecount") or active_zone_count
            local observed_source = codol.call("function:zmcooperativezonesource") or
                "legacy-first-player"
            if observed_source == "cooperative-union-reconstruction" then
                local observed_zones, observed_signature =
                    read_occupied_zones(observed_zone)
                if observed_signature ~= occupied_zone_name or
                    observed_source ~= occupied_zone_source or
                        observed_players ~= player_count or
                        observed_active ~= active_zone_count then
                    configure_spawn_zones(observed_zone, observed_players,
                        observed_zones, observed_signature, observed_source)
                end
            -- Preserve the legacy guard exactly: an empty player-zone answer means
            -- that the player is between authored volumes, so retain the last set.
            elseif observed_zone ~= nil and observed_zone ~= "" and
                (observed_zone ~= occupied_zone_name or
                    observed_players ~= player_count or
                    observed_active ~= active_zone_count) then
                configure_spawn_zones(observed_zone, observed_players)
            end
        end
        if no_eligible_cooperative_zones then return end
        if round_started_at == nil then
            begin_round(now)
            return
        end
        -- THE ROUND ENDS WHEN THE WAVE IS DEAD, which is what retail does, with a
        -- timer only as a backstop. `alive` is decremented by the entity_killed
        -- handler below; the timer catches a wave that can never be cleared -- one
        -- whose last zombie is stuck behind geometry, say -- rather than hanging the
        -- match on it.
        local want_now = wave_size(round)
        if spawned_this_round >= want_now and alive <= 0 then
            -- THE PAUSE BETWEEN ROUNDS IS REAL AND IT IS LONG. Measured at 35.8 s and
            -- 41.6 s between rounds on the demo; the mode used to begin the next wave
            -- on the same tick the last one cleared.
            if round_cleared_at == nil then
                round_cleared_at = now
                print("zm round cleared", round, "in",
                    (now - round_started_at) / 1000, "s", "pausing",
                    ROUND_PAUSE / 1000)
            end
            if now - round_cleared_at >= ROUND_PAUSE then
                begin_round(now)
            end
            return
        end
        if now - round_started_at >= ROUND_SECONDS then
            print("zm round timed out", round,
                "spawned", spawned_this_round, "of", want_now, "alive", alive)
            -- Do not merge a stuck wave into a new round while its actors still own
            -- slots. Keep the round alive and report again only after one backstop.
            round_started_at = now
            return
        end
        local want = wave_size(round)
        if spawned_this_round >= want or alive >= alive_cap(round) then
            return
        end
        if next_spawn_at ~= nil and now < next_spawn_at then return end
        local actor, zone, point = spawn_one()
        if actor == nil then
            -- BACK OFF. A failed sweep is expensive -- every attempt re-resolves two
            -- model names against up to 1024 configstrings -- so retrying it on the
            -- next tick is how a stalled wave becomes a frozen server.
            next_spawn_at = now + SPAWN_BACKOFF
            -- Every point of every adjacent zone refused. Worth a line each time:
            -- it means the nav graph reaches none of them, which is a real fault.
            print("zm wave stalled, no spawn point took",
                round, spawned_this_round, want)
            return
        end
        next_spawn_at = now + spawn_interval(round, spawned_this_round)
        spawned_this_round = spawned_this_round + 1
        alive = alive + 1
        active_actors[actor] = true
        print("zm actor spawned", actor,
            "round", round,
            "zone", zone,
            "point", point,
            "wave", spawned_this_round .. "/" .. want)
    end))
end
-- A ZOMBIE DIED. The server publishes entity_killed when a damageable entity's
-- health reaches zero, and the actor stepper plays the death clip and frees the
-- entity after a corpse window -- so there is nothing to clean up here beyond the
-- count the round loop reads.
--
-- Registered outside the zone block on purpose: `alive` is an upvalue of that block
-- and this closure captures it, but the handler has to survive whether or not the
-- map had a zone model.
assert(codol.on("entity_killed", function(entity, event)
    -- Every damageable entity raises this, not only zombies. A map with no zone
    -- model has no director and therefore no counter to move.
    if zm_actor_died ~= nil then
        zm_actor_died(event)
    end
end))

assert(codol.on("player_killed", function(player, event)
    -- DELIBERATELY NO SCORING. dm.lua awards addscore 50 + addkill 1 to the attacker;
    -- in a co-op mode the only way one player kills another is a bug or a bad damage
    -- path, and paying score for it would hide that. Retail zombies scores kills
    -- against AI, and there is no builtin to spawn or identify an AI zombie yet --
    -- see the builtin list in sv_script_builtin_mp.cpp -- so there is nothing
    -- legitimate to score here.
    if event.attacker_entity_num ~= nil and
        event.attacker_entity_num ~= event.target_client_num then
        print("zm player killed by another player", event.attacker_entity_num)
    end

    -- BRING-UP PLACEHOLDER, AND IT IS NOT WHAT RETAIL DOES. Real zombies holds a dead
    -- player out until the next round begins, or until revived; the demo's round
    -- machinery is the `N "zm_begin" 100` command at 0:13.4 and this server has no
    -- round loop to hang that off yet. A flat respawn keeps the map walkable for
    -- bring-up instead of ending the session at the first death. Replace this the
    -- moment rounds exist -- do not let it become the definition of the mode.
    local _, respawn_error, respawn_error_code = codol.call(
        "method:respawn", player, 3000)
    if respawn_error ~= nil then
        print("player respawn deferred", respawn_error, respawn_error_code)
    end
end))
