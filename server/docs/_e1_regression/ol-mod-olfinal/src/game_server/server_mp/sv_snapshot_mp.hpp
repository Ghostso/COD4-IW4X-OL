#pragma once
#include "sv_zm_revive_mp.hpp"
#include "sv_zm_injury_mp.hpp"

#include "sv_collision_mp.hpp"
#include "sv_damage_numbers_mp.hpp"
#include "sv_antilag_mp.hpp"
#include "sv_const_baselines_mp.hpp"
// For HintStringConfigStringBase/Count and NoHintStringIndex, which
// SvPlayerState's cursor-hint members are defined in terms of. sv_gamestate_mp
// depends on nothing but qcommon/msg_mp, so this cannot cycle.
#include "sv_gamestate_mp.hpp"
#include "sv_client_impacts_mp.hpp"
#include "sv_client_events_mp.hpp"
#include "sv_mapents_mp.hpp"
#include "sv_bullet_mp.hpp"
#include "sv_missile_mp.hpp"
#include "sv_grenade_explosion_mp.hpp"
#include "sv_damage_mp.hpp"
#include "sv_radius_damage_mp.hpp"
#include "sv_entity_mp.hpp"
#include "sv_native_entitystate_mp.hpp"
#include "sv_native_pmove_mp.hpp"
#include "sv_native_playerstate_mp.hpp"
#include "sv_perks_mp.hpp"
#include "sv_equipment_mp.hpp"
#include "sv_rewards_mp.hpp"
#include "sv_native_server_entity_mp.hpp"
#include "sv_weapon_fire_mp.hpp"
#include "sv_weapon_movement_mp.hpp"
#include "sv_zm_navgraph_mp.hpp"
#include "sv_zm_lookahead_mp.hpp"
#include "sv_zm_barrier_mp.hpp"
#include "sv_zm_board_flight_mp.hpp"
#include "sv_zm_presentation_mp.hpp"

#include "qcommon/msg_mp.hpp"
#include "qcommon/net_chan_mp.hpp"

#include <array>
#include <cstdint>
#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>
#include <variant>

namespace CodolGameServer
{
    struct SvMapTriggerTable;
    // CODREF(sv_write_snapshot_to_client): these values are recovered CODOL
    // wire domains. The source DTOs below are not native memory layouts.
    constexpr std::uint8_t SnapshotServerCountFlag = 0x04;
    constexpr std::uint8_t SnapshotBaselineFlag = 0x08;
    constexpr std::uint8_t SnapshotSceneBlockFlags = 0x0A;
    // 0x10 -- A NEW ENTITY RESOLVES AGAINST cl.entityBaselines[num], NOT A ZEROED STRUCT.
    //
    // This server has never set it, and that is why map geometry is invisible. Retail's static
    // ET_SCRIPTMOVERs assert almost nothing on the wire -- measured in the 2021 factory demo,
    // entity 43 carries ONE xModelIndex across 349 asserting frames and entity 104 one trBase[2]
    // -- because origin, angles and model all come from the baseline the client builds at MAP
    // LOAD. Without this bit every one of them is decoded from zeroes, so it has no model and
    // renders nothing. re/demo-re/10-snapshot-format.md sec.2:
    //
    //     0x10 -> sub_470F20 @0x471300 calls sub_470E70(entityNumber, Dst):
    //         v2 = dword_77CE488[num];
    //         if (v2 > 0 && v2 < dword_7795824) qmemcpy(Dst, &unk_779E6E0 + 280*v2, 0x118);
    //         else                              memset(Dst, 0, 0x118);
    //
    // THE FALLBACK IS WHY THIS IS SAFE TO SET UNCONDITIONALLY: an entity number the client has
    // no baseline for still gets a zeroed struct, i.e. exactly today's behaviour. The risk is not
    // the flag, it is the NUMBERING -- the client indexes by entity number, so an entity we place
    // at a number the map also uses inherits that map entity's origin and model. Publishing map
    // entities at their own map ordering is what makes the lookup mean what it says.
    //
    // THE NUMBERING IS NOW SETTLED, AND IT WAS NEVER DERIVABLE. `dword_779E6E0` is not built
    // from the map -- the client fills it at map load from `<map>_const.ff`, an asset every map
    // ships (`mp/constbaselines/bl_pc_<map>_<gametype>.bin`). That file IS the numbering:
    // factory's carries 397 entries, entity 37..699, and its 238 brush models are exactly this
    // server's 238 script_brushmodels. sv_const_baselines_mp.hpp holds the extracted table and
    // re/demo-re/16-const-baselines.md the derivation.
    //
    // So the flag is driven by SvSnapshotFrame::useEntityBaselines, which the world sets only
    // when it published this map's static entities on those numbers. On a map with no extracted
    // table it stays off and the numbering stays this server's own.
    //
    // OLMOD_SNAPSHOT_ENTITY_BASELINES=0 turns it off again without a rebuild, so the two wire
    // shapes can be A/B'd against one live client.
    constexpr std::uint8_t SnapshotUseEntityBaselinesFlag = 0x10;
    // ps+0x10's flags word is SHARED with the engine. BG_PlayerStateToEntityState tests
    // (flags & 0x1800) to pick ET_PLAYER over ET_INVISIBLE, and those two bits are the
    // only part of it this server owns -- the engine keeps stance and toggle state in the
    // rest, and PmoveSingle tests bit 0x10000000 of it. Defined once, here: one number in
    // more than one file has already cost this project a live bind() failure and an
    // entire weapon catalogue (sec 43d).
    constexpr std::uint32_t PlayerOtherFlagPlayer = 1u << 12;
    constexpr std::uint32_t PlayerOtherFlagsServerOwnedMask = 0x1800u;
    constexpr std::uint8_t EntityTypeGeneral = 0;
    constexpr std::uint8_t EntityTypePlayer = 1;
    constexpr std::uint8_t EntityTypeCorpse = 2;
    constexpr std::uint8_t EntityTypeItem = 3;
    // ET_SCRIPTMOVER. Promoted out of sv_snapshot_mp.cpp's anonymous namespace
    // when map brush models moved onto it: sub_1F2EF0 is the only presentation
    // handler that reaches R_AddBrushModelToScene, so this eType is what decides
    // whether a brush model is drawn at all. Confirmed against the shipped const
    // baselines -- all 373 of factory's scriptmovers are 6.
    constexpr std::uint8_t EntityTypeScriptMover = 6;
    // ET_ACTOR. The zombies. Netfield table 0x00DA5DE8 in out.exe, 63 fields, and the
    // eType dispatch's entry 19 -- confirmed byte-identical in the .13 image on disk AND
    // read live out of the running client. re/demo-re/20-zm-actor-lifecycle.md.
    //
    // What the five retail zm captures say about one, over 64 actor lives:
    //   * every life opens at pos.trType 1 and NEVER carries any value but 1 or 13;
    //     19 switch to 13 near death and none reverts. pos and apos switch together,
    //     19 times out of 19.
    //   * position and yaw stream almost every frame -- ~2400 assertions each -- while
    //     pos.trDelta is set 18 times in twenty minutes. It is a server-pushed walker,
    //     NOT a client-extrapolated trajectory.
    //   * pitch and roll are ALWAYS zero, and groundEntityNum is always 2047.
    constexpr std::uint8_t EntityTypeActor = 19;

    // 21, AND IT IS WHAT RETAIL ACTUALLY PUBLISHES. Measured across the whole zm
    // capture (12.30): ZERO eType-19 entities alive at any sampled time, while et21
    // runs 3 -> 36 -> 56 -> 30 -> 16, and at t=26350 the live et21 entities are 723,
    // 724, 725 -- exactly the numbers the client's agent array pairs with
    // c_zom_garbageman_body_blue / _worker_ / _ger_. demoq labels 21 ET_ACTOR_CORPSE
    // and they are plainly not corpses; the NUMBER is what is measured, not the name.
    //
    // IT IS NOT COSMETIC. sub_540860 switches on the eType and its `case 19: case 21:`
    // arm ends with `if (a2 && v14 == 21) sub_530E70(Source)` -- so 21 gets a record
    // initialiser that 19 never receives, filling the record from the ENTITY STATE
    // (Source+332, Source+352) rather than from the agent element. Publishing 19 opts
    // out of that path entirely.
    //
    // The 18-field writer transfers unchanged: the per-eType index -> offset map is
    // IDENTICAL for 19 and 21 across every shared index (idx1 +0x040, idx2 +0x018,
    // idx3 +0x01C, idx10 +0x08C, idx11 +0x058, idx14 +0x008, idx19 +0x00C, idx20
    // +0x030 ...), so only the value and its allow-lists move.
    constexpr std::uint8_t EntityTypeActorCorpse = 21;

    // BOTH NUMBERS ARE AN ACTOR. sub_527A70 sends eTypes 19 AND 21 to sub_52FBE0, so
    // the client draws either; the allow-lists must accept either or an actor is
    // dropped before serialization (the 12.14 failure, three times over).
    [[nodiscard]] constexpr bool isActorEType(const std::uint8_t eType)
    {
        return eType == EntityTypeActor || eType == EntityTypeActorCorpse;
    }
    // THE AGENT SLOT SPACE. sub_530C30 walks the record array with `cmp ecx, 20h`,
    // so 32 is the hard count; retail delta-codes 31 of them in the spec capture.
    constexpr std::size_t SvAgentSlotCount = 32;
    inline constexpr std::uint32_t ActorCorpseRingSize = 32;
    // BISECT GATE, OFF. The build that first sent agent elements hung the dedicated
    // during world spawn -- log stops between `SessionStart accepted` and the
    // gameplay script's first print, every server thread in Wait, none running.
    // That is the shape of the loadGameplayScript deadlock the handoff documents,
    // and it is NOT yet established whether this change causes it or merely widens
    // the window. Off restores the wire of the last build that booted.
    //
    // What it disables: the per-actor agentState element, and field 8 in the element
    // writer so a player's element is byte-identical to that build's.
    // THE CLIENT'S DEFAULT AGENT ROW, AND WHY EVERY FIELD BUT ONE WAS WRONG.
    //
    // A snapshot field is XORed against a baseline (writeUnsignedDelta writes
    // `value ^ (baseline & mask)`), so the SERVER'S delta base must equal the
    // CLIENT'S or the value decodes to something neither side chose.
    //
    // When an agent slot appears for the FIRST TIME the client does not start from
    // zero. sub_471980 copies an 88-byte template and hands it to the field decoder
    // as the baseline:
    //     sub_769710(v26, &unk_DA9920, 88);
    //     sub_670FF0(v5, a4, v26, v16, 24, &unk_DA63E8, 3);
    // and unk_DA9920 (out.exe) reads
    //     +0x004 = 345    +0x008 = 2    +0x00C = 1266    +0x010 = 0xFFFFFFFF
    //     +0x014 = 1267   +0x018 = 1317 +0x028 = 3       +0x034 = 3    +0x040 = 1
    //
    // MEASURED CONSEQUENCE (12.27): this server sent modelIndex 310 against a ZERO
    // base, so it transmitted 310; the client computed 310 ^ (1266 & 0x3FF) =
    // 310 ^ 242 = 452 and stored 452 -- read live out of the client's agent array.
    // The model never resolved, record+568 stayed empty and no DObj was built.
    //
    // THE CONTROL THAT PROVES IT: the team field already used SvTeam::Sc (2) as its
    // base -- which is exactly +0x008 -- and that field, alone, landed correctly.
    // The comment on it had found this for one field and never generalised it.
    // THE STRAIGHT-LINE CHASE, OFF BY DEFAULT.
    //
    // stepActorEntities walks every actor at the measured retail speed straight at the
    // nearest player, in the plane, with NO pathing -- so it goes through walls, leaves
    // the spawn closet immediately and ends up standing in the open next to the player.
    // That is not what a zombie does and it makes correct SPAWN placement impossible to
    // see: the actors are on the map's own zombie_spawner structs (12.31/12.32) and then
    // walk off them within a second.
    //
    // It proved what it was built to prove -- a streamed origin moves an actor on the
    // client (12.33) -- so it stays available behind this flag and comes back ON when the
    // goal/barrier pathing replaces the direction.
    constexpr bool SvActorChaseNearestPlayer = false;

    // WALK TO THE SPAWNER'S OWN NAVIGATION NODE. This is what replaces the
    // chase direction the flag above was waiting on.
    //
    // MEASURED, not chosen: zm_factory_sh's MapEnts give 61 of 69 zombie_spawner
    // structs a `target`, all 61 resolve, and all 61 resolve to a `node_pathnode`
    // 159..738 units away. So a zombie leaves its closet along the map's own AI
    // navigation data instead of straight at a player through walls.
    //
    // WHAT THIS IS NOT: full pathfinding. It is ONE hop, to the first node the
    // spawner names. The node graph itself is not in MapEnts -- 994 node_pathnodes
    // carry no `target` chain -- it lives in the `aipaths` asset, which is not
    // parsed. The 53 node_negotiation_begin/end pairs, which DO chain and carry an
    // `animscript`, are the vault/traversal points, i.e. the barriers. Those two
    // are the next measurements, in that order.
    // BACK ON, AND WHAT CHANGED IS THE ROUTE (12.57 / 12.58).
    //
    // It was off because ONE HOP is not a route: walking to the spawner's node and
    // stopping parks a zombie on a waypoint in the open, which is what was seen in
    // game (12.55b). The rest of the route was supposed to come out of the `aipaths`
    // asset -- and `aipaths` is EMPTY in every shipped zone, so it never could.
    //
    // The graph is now MEASURED instead, off 1063 retail zombie walks reconstructed
    // from the zm demos plus the map's own 53 barrier vaults, and the actors route
    // node-to-node with A* toward the nearest living player. See sv_zm_navgraph_mp.hpp.
    //
    // The three things this flag gates that were ALWAYS right stay unchanged: the
    // measured 0.385 u/ms step, the yaw, and STAND STILL WHEN THERE IS NO ROUTE.
    // That last one is not a fallback to soften later -- 5 of factory's 30 spawner
    // goal nodes have no edge in the measured graph, and inventing a path for those
    // is exactly the through-walls behaviour 12.55 removed.
    constexpr bool SvActorWalkToSpawnerGoal = true;

    // How often an exhausted/incomplete route retries. Active routes are rebuilt
    // when the player's destination node changes; periodically rebuilding a valid
    // suffix can reverse the incoming edge and make an actor oscillate at a node.
    constexpr std::uint32_t SvActorRouteReplanMilliseconds = 1000;
    // How close an actor has to get to a waypoint before it takes the next one.
    // Node spacing is 58 units at the median (12.58), so this cannot be much larger
    // without letting an actor skip the node that turns it round a corner.
    // This stepper follows measured node centrelines without the retail AI's corner
    // steering.  A wide arrival radius cuts the corner between consecutive legs and
    // drives the next sweep into the adjacent wall.  Four units is one navigation-hull
    // radius, so it consumes a waypoint without requiring impossible bit-exact contact.
    constexpr float SvActorWaypointArrivalDistance = 4.0f;
    // Pathnode origins sit above an actor's feet (up to about 65 units on the
    // receiver ramp in the live Factory collision), so
    // waypoint arrival cannot demand an equal Z.  It still must reject a node on
    // the floor below: comparing only X/Y let actors standing roughly 98 units
    // above node 614 consume it and begin chasing on the wrong storey.
    constexpr float SvActorWaypointArrivalHeight = 72.0f;
    // KEEP ACTORS ASSIGNED TO THE SAME WINDOW OUT OF ONE BYTE-IDENTICAL PILE.
    //
    // Factory's eight receiver spawners feed five boarded entrances.  A round can
    // therefore put six actors on one approach, and the graph has no retail crowd
    // navigator to keep their capsules apart.  Without a local following distance
    // they all reach the same outside node and render as one central "spawn".  This
    // is the existing formation ring spacing and is slightly wider than one actor
    // capsule: the lowest-numbered actor leads, later actors queue on the route.
    constexpr float SvActorWindowQueueSpacing = 34.0f;
    // A* supplies a shared route centreline, not the retail navigator's local
    // avoidance. Once through a window, make only the rear actor yield. Actors
    // retain the measured graph centreline or exact player bearing instead of
    // receiving a synthetic lateral lane.
    constexpr float SvActorCrowdSeparationRadius = 42.0f;
    constexpr float SvActorCrowdSameFloorHeight = 48.0f;
    // How far from a node a position may be and still be resolved to it. Generous
    // because it is asked of PLAYERS, who stand wherever they like, not just of
    // actors, who stand on spawners.
    constexpr float SvActorNodeSearchRadius = 512.0f;

    // The assigned window is a forced stage of the route, not its destination.
    // Once all boards are torn the actor crosses the map-authored negotiation edge
    // and continues over the measured Factory pathnode graph toward the player.
    constexpr bool SvActorStopAtAssignedWindow = false;

    constexpr std::uint32_t SvAgentDefaultEntityNumber = 345;   // +0x004, idx20
    constexpr std::uint32_t SvAgentDefaultModelIndex = 1266;    // +0x00C, idx8
    // The attachment models, same table, same default row. All four 10-bit slots:
    //   idx13 +0x014 (1267)  idx14 +0x018 (1317)  idx16 +0x01C (0)  idx18 +0x020 (0)
    // and the four 6-bit TAG slots are idx23 +0x024, idx15 +0x028, idx17 +0x02C,
    // idx19 +0x030 -- read straight out of the netfield table at 0xDA63E8.
    constexpr std::uint32_t SvAgentDefaultAttachModel0 = 1267;  // +0x014, idx13
    constexpr std::uint32_t SvAgentDefaultAttachModel1 = 1317;  // +0x018, idx14
    constexpr std::uint32_t SvAgentDefaultAttachTag1 = 3;       // +0x028, idx15
    // ATTACHMENT SLOT 0'S TAG. Read live off the client's default agent row:
    // unk_DA9920 + 0x024 = 0, so 0 is the delta base for field 23.
    constexpr std::uint32_t SvAgentDefaultAttachTag0 = 0;       // +0x024, idx23
    // CODREF(actor_head_attachment): CODOL out.exe DObjCreateDuplicateParts
    // 0x781110 distinguishes empty attachment names (match shared bones) from
    // named parent bones. BO1 0x7E4210 and Ghosts 0x140247490 do the same.
    // The Factory head is a rigged model: preserve the tag-zero contract rather
    // than parenting its whole skeleton to j_head (netconst tag 5). A valid tag
    // name alone does not establish the correct model assembly operation.
    // OLMOD(actor-head-publication): limited to this zombie agent producer;
    // player attachment fields and the shared netfield schema stay unchanged.
    constexpr std::uint16_t SvActorHeadTagIndex = 0;

    // A ZOMBIE ANIMATION INDEX, measured two independent ways (12.52).
    //
    // Walking the shared zombie anim set's BST live in demo playback -- it hangs
    // off record+0x24, is the SAME set pointer on every retail zombie, and holds
    // 116 index->slot pairs -- gives 476->69. And `demoq agents --changes` on
    // the zm capture shows retail ASSERTING idx9 = 476 on real zombies at
    // t=140750, 214750, 215950, 35950 and 1082350. Two sources, one number.
    //
    // 12.36 CLAIMED RETAIL SENDS 0 HERE AND THAT IS WRONG. It sampled the gaps
    // BETWEEN animations, where the field does return to 0, and generalised. The
    // client's own accessor settles it: sub_5242D0 hands the index to sub_524A10,
    // which allocates an animation block ONLY when the index is non-zero, so a
    // constant 0 is a guaranteed bind-pose T-POSE.
    //
    // NOT NECESSARILY 'WALK'. 116 keys were recovered but none are NAMED -- the
    // BST maps index to a slot number, not to a string. This is the most
    // frequently asserted key in the capture, which makes it the best first
    // guess and nothing more. If it plays the wrong motion, try 489, 481, 483
    // or 678, all of which are also valid keys AND observed on the wire.
    constexpr std::uint16_t SvActorAnimIndex = 476;

    // THE BASE ANIMATION, BY NAME. 476 is `ai_zombie_boardtear_l_1` -- a zombie tearing
    // the boards off a barrier, held forever, which is what this server has published on
    // every actor since 12.53 (12.61 named the band and settled it).
    //
    // The whole zombie vocabulary is now named.  The Factory demo settles which
    // locomotion follows the slow receiver traversal: actor 728 changes from
    // `ai_zombie_traverse_v6` to `ai_zombie_walk_fast_v1_t5` at the inside node.
    //
    // A NAME, NOT 707. The client rebuilds its animation band at map load, so a literal
    // index names a different animation on another map or another build -- 12.47 and
    // `codol-client-reresolves-asset-indices`. The dedicated resolves this against its
    // own engine at world spawn and falls back to SvActorAnimIndex if it cannot, because
    // a wrong animation is still better than the T-pose a zero index guarantees.
    constexpr std::string_view SvActorWalkAnimName =
        "ai_zombie_walk_fast_v1_t5";

    // THE BARRIER ANIMATION. `ai_zombie_boardtear_l_1` is what 12.61 measured on the
    // demo as index 476 -- a zombie pulling a board off a window and holding it. It is
    // the game's own string out of a retail capture, not a spelling invented here, and
    // `resolveAnimConfigStringIndex` checks residency before it will return an index,
    // so a build whose zones do not hold it falls back to the walk rather than putting
    // a wrong number on the wire.
    constexpr std::string_view SvActorTearAnimName = "ai_zombie_boardtear_l_1";

    // HOW MANY ANIMATIONS ONE SNAPSHOT'S ALIAS TABLE MAY CARRY.
    //
    // `sub_671650` reads the count with `sub_66ED70`, a BYTE, so 255 is the format's
    // own ceiling. The practical number is far smaller: the table costs 12 bits per
    // entry on every snapshot that carries the section, and the per-record index costs
    // `bit_width(count - 1)` bits per record. Simultaneous transitions can use
    // more than seven distinct clips; retain the wire ceiling, including null.
    constexpr std::size_t SvActorAliasTableMax = 255;

    // THE DEATH ANIMATION, and the health a zombie spawns with.
    //
    // `ai_zombie_death_v1` is the engine's own string, index 517 in this build's
    // band. 150 is a PLACEHOLDER: retail zm scales zombie health per round and no
    // curve for it has been measured here.
    constexpr std::string_view SvActorDeathAnimName = "ai_zombie_death_v1";
    constexpr std::int32_t SvActorSpawnHealth = 150;

    // OLMOD(zm-player-collision): linked actors remain shootable. Player Pmove
    // receives a separate native packed-solid capsule view; actor navigation
    // retains its world/player view and existing body mask. Historical slowdown
    // attribution was disputed by later Lua asset-resolution measurements;
    // current collision performance must be measured, not inferred from it.
    constexpr bool SvActorLinkCollision = true;

    // How long a corpse stays after the death animation starts, before the entity is
    // freed. Long enough for the clip to play; short enough that the 32-slot actor
    // pool is never held by the dead.
    constexpr std::uint32_t SvActorCorpseMilliseconds = 2500;

    // THE MELEE ANIMATION, the range it plays at, and how often it REPLAYS.
    //
    // `ai_zombie_attack_v1` is index 430 here. Both numbers below are placeholders --
    // retail's reach and swing rate are not measured.
    //
    // 12.166: the first cut stopped an actor dead at 72 units, zeroed its velocity
    // and skipped every movement branch, then stamped a ONE-SHOT animation that ends
    // at t=1.0 and holds. Measured: three actors motionless for 25 s at 68-72 units
    // from the player, the walk still weighted underneath at t=0.0000. On screen that
    // is a crowd standing in a ring doing nothing, which is what was reported three
    // separate times as "walking and resetting" and "they all gather here".
    //
    // 40 units is a body's width rather than a car's length, and the swing is
    // re-stamped so it replays instead of freezing on its last frame.
    constexpr std::string_view SvActorAttackAnimName = "ai_zombie_attack_v1";
    constexpr float SvActorAttackRange = 40.0f;
    constexpr std::uint32_t SvActorAttackReplayMilliseconds = 1200;
    // Hold every pursuing actor within melee range. The former rank-based rings
    // changed a survivor's destination whenever another actor died or was freed;
    // that presented as delayed left/right searching even when the player had not
    // moved. Local capsule/crowd steering owns separation and must not redefine the
    // player target.
    constexpr float SvActorPursuitStandOffRadius = 32.0f;
    constexpr float SvActorFormationArrivalDistance = 6.0f;
    // MEASURED from the factory zombie demos. The recording player's damageCount
    // is 12 on 174 of 237 non-zero zombie-era damage events across all five
    // captures, including every hit in the first sustained solo swarm. Those
    // events can arrive 200-500 ms apart when several actors are in reach; 300 ms
    // is the centre of that first measured burst and prevents a full crowd from
    // collapsing into one same-frame hit.
    constexpr std::int32_t SvActorAttackDamage = 12;
    constexpr std::uint32_t SvActorAttackDamageIntervalMilliseconds = 300;
    // The authored zombie hit reaches the native player death path, but the current
    // client stops acknowledging snapshots after that transition and times out. The
    // spawning/barrier work must remain observable while that separate death-state
    // fault is investigated. Keep the measured damage implementation in place and
    // fail it closed for this bring-up build.
    constexpr bool SvActorDealsPlayerDamage = false;

    // RE-ASSERTING THE ANIM INDEX ON A CADENCE. OFF, and 12.97 says why.
    //
    // 12.96 turned this on after reading 12.50's demo dump as "retail re-asserts every
    // 1600-3300 ms, forever". That reading was wrong, and measuring the LIVE demo client
    // settled it: across 26 active actor records, 399 clean reads over 40 s, idx9 changed
    // FOUR TIMES -- two one-shots that fired and cleared back to 0. Retail's zombies walk
    // continuously through all of it. 12.50's intervals are gaps WITHIN a burst; the
    // bursts themselves are minutes apart (slot 0 jumps 44950 -> 213950, a 169 s hole).
    //
    // So idx9 is a sparse one-shot channel and NOT the locomotion driver, which is what
    // 12.36 said originally and what 12.64 concluded from the call graph. Re-asserting it
    // every 1600 ms is ~100x retail's real rate and is the shape 12.77 already measured as
    // an animation that never gets to advance.
    //
    // Left in place, off, because the code is the record of the experiment. Turning it on
    // is only interesting once something else explains continuous locomotion.
    // SEND A REAL ANIMATION ALIAS (12.154).
    //
    // `record+20` is not a wire field. `sub_540040` resolves it from the ALIAS in
    // `record+24` via the actor's own animtree BST (12.153), and this server has
    // only ever sent a one-entry table holding the NULL alias -- so the resolve
    // bails, the key stays 0/2, and each zombie gets one node that freezes.
    //
    // The value sent is `zmActorWalkAnim_`, which Appmain resolves BY NAME from
    // `SvActorWalkAnimName` against this engine's own band, so it is not a literal
    // index ported from a capture.
    //
    // WHAT WOULD FALSIFY IT: if the zombies still hold one pose with the alias on
    // the wire and `record+24` non-zero at the client, the resolve is failing for
    // another reason and this comes straight back out.
    constexpr bool SvActorSendAnimAlias = true;
    constexpr bool SvActorReassertAnim = false;
    constexpr std::uint32_t SvActorAnimReassertMilliseconds = 1600;

    // EXPERIMENT (12.65) -- SEND ANIM INDEX 0, WHICH IS WHAT RETAIL SENDS.
    //
    // 12.64 closed the anim index at the call-graph level: `sub_5242D0` is its ONLY
    // reader, it has exactly one xref (`sub_524A10`), and that function's whole product
    // is the block at `centity+524` whose handle comes back null because
    // `centity+0x22C` is null -- on ours AND on all 41 retail actors, which animate
    // anyway. So the index feeds something inert.
    //
    // If that is right, sending 0 must change NOTHING on screen, and 12.53's claim that
    // "a zero index is a guaranteed bind-pose T-POSE" is wrong as well. If the actors DO
    // fall back to a T-pose, then something reads the index by a path 12.64 did not find
    // and that path is the answer. Either result is worth a cycle; this is the whole
    // experiment and it is one bit wide.
    //
    // Retail sends 0 on 30% of its own asserts, so this is not an invented state.
    //
    // LIVE CLIENT/IDA RESULT, 2026-09-07. Every broken actor had a non-null block at
    // centity+0x20C while all retail actors measured in 12.52 had zero there. In
    // sub_540860 that pointer suppresses the only branch which evaluates lerp.pos and
    // initializes cpose from the authored network origin. The agent anim pair has no
    // other consumer and its block resolves a null handle, so publishing it only leaves
    // actors at the temporary centre pose. Keep this dead channel zero; locomotion is
    // driven by the separate actor animtree/command section.
    constexpr bool SvActorSendAnimIndex = false;
    // SEED THE ACTOR'S ANIMTREE (12.75). The snapshot's sound/command section is what
    // INSTANTIATES a DObj's node tree, and this server has always written it as one zero
    // bit, so no actor has ever had a tree to animate.
    //
    // 12.74 measured the rest of the chain WORKING on this server: the animtree mask
    // arrives as 24, the table loads generic_human and zombie_dog, sub_40B320 provisions
    // columns 3 and 4 on all 32 slots, and every actor's DObj+0 already points at its
    // column-3 cell. The only field still zero is the cell's ROOT NODE INDEX at +4, and
    // sub_7886D0 writes that -- lazily -- the first time any command is applied to the
    // DObj. Retail sends 55,591 of them across 120 target entities in one zm capture,
    // 800-1250 per actor, measured off C-2021-7-31[15-32-16]zm.
    //
    // ONLY TYPES 1, 2 AND 8 REACH THE TREE. sub_527B40's other arms (0xB/0xC/0xD) end in
    // sub_788A50/sub_788A90/sub_789B00 and never touch a node. This writes a type 3
    // (sticky target entity) followed by a type 1, which is the shortest record that
    // reaches sub_7887E0 -> sub_7886D0 -> sub_788540 with no parent.
    //
    // THE ALIAS WIDTH IS FORCED, NOT ASSUMED. byte_7859559 is cross-snapshot state that
    // sub_671730 only rewrites when an alias table is present, so a width this server did
    // not set could desynchronise the whole packet -- the exact failure 12.36 and 12.38
    // each cost a client. Sending a ONE-ENTRY table makes the client compute width 0
    // (`n <= 1 -> 0`) every frame, so the record carries no alias index at all and no
    // agreement about word_7859358's contents is required.
    constexpr bool SvActorSeedAnimTree = true;
    // REFUSE A SPAWNER WHOSE GOAL CANNOT REACH THE PLAYERS (12.80).
    //
    // The alternative was considered and rejected: softening the router so an actor
    // with no route walks toward the player anyway is exactly the through-walls
    // behaviour 12.55 removed, and sv_zm_navgraph_mp.hpp says so in its own header.
    // The graph is a measured floor and it will stay incomplete until more captures
    // are walked; the honest response is to spawn only where the map can be walked,
    // and to say out loud how many spawners that excludes.
    constexpr bool SvActorRefuseUnroutableSpawn = true;
    constexpr bool SvSendActorAgentElements = true;
    // PUBLISH ACTORS AS ENTITIES AT ALL. Separate from the agent gate ON PURPOSE:
    // with this on for the first time, the actors reached the wire and the client
    // stopped completing frames -- stuck on the map-load screen showing "waiting for
    // player data", which is this project's known signature for a desynchronised
    // snapshot cursor. Off restores the last build that booted.
    //
    // Two gates, so the next session can bisect: entity-only (this on, agents off)
    // separates the ET_ACTOR entity writer from the agentState element.
    constexpr bool SvArchiveActorEntities = true;

    // EMIT PLAYERS INTO THE ACTORS SECTION. Retail does NOT, and that is MEASURED: on the
    // spec zm capture (100% endpoint-exact) the earliest assert across all 31 agent slots
    // is t=25750, while the capture starts at 10950 and round 1 at 20250 with the player
    // present throughout. The section is EMPTY for fifteen seconds and then fills from
    // slot 0 at 300 ms intervals -- a zombie spawn wave.
    //
    // This server has always written one element per player here at slot = clientNum,
    // which the client parses as an AGENT and stamps a record for. That is also the only
    // reason the agent slot floor had to be MaximumGameClients.
    //
    // A GATE rather than a deletion: the player write is long-standing, carries its own
    // CODDIFF about the field-21 width, and players currently render. Flip it back if
    // anything about players regresses. re/demo-re/20-zm-actor-lifecycle.md 12.11.5.
    constexpr bool SvEmitPlayersInActorsSection = true;
    inline constexpr std::uint32_t ActorCorpseLerpPrefix = 0x01030000u;
    // CODDIFF(1649370): ET_EVENTS is 23 here, 22 on 3.3.3.3. This build inserted ONE
    // unnamed eType at 22 -- its entityState dispatch has 24 slots where 3.3.3.3 has 23,
    // and it gives index 22 its own netfield table distinct from ET_EVENTS'. Confirmed
    // against the game rather than against the table: the readers clamp eType at 23 and
    // pass `eType - 23` as the event number.
    // OLMOD(section-84): AND NOW ON out.exe, WHICH IS NOT WHERE THIS USED TO POINT. The
    // five addresses this comment carried -- tables 0x00DA6B28 / 0x00DA4920 and readers
    // sub_671250 @0x671355, sub_678390 @0x67845d -- are all OL.exe's, build 1608541,
    // the reference binary. out.exe's are:
    //
    //   dispatch          0x00DA9330, 24 slots, count 63 in every one
    //   index 22 table    0x00DA6B08          ET_EVENTS table   0x00DA4900
    //   readers           sub_671170 `cmp ecx, 17h / jle / mov ecx, 17h` at 0x00671272
    //                     and `add ecx, -17h` at 0x0067129B
    //                     sub_6782A0 same clamp at 0x0067836A
    //
    // The data half of that translation is a uniform -0x20 and the code half is NOT
    // uniform (-0xE0 here, -0xF0 for the 0x678xxx group). Carried at 22, every event entity this server
    // writes is one eType low, and the parameter width looked up for it is the previous
    // event's.
    constexpr std::uint8_t EntityTypeEventBase = 23;
    // EVERY ONE OF THESE IS CHECKED AGAINST OL.exe's OWN NAME ARRAY (0xE5FD38, 185
    // const char* slots, dumped to re/olfinal-events.tsv) AND AGAINST THE RETAIL dm
    // DEMO. Two of them were wrong and both were 3.3.3.3-shaped guesses:
    //
    //   was 0x4A -> EV_SWITCH_OFFHAND     is 0x53 -> EV_BULLET_HIT
    //   was 0x64 -> EV_GRENADE_LETGO      is 0x6F -> EV_PLAY_FX
    //
    // The demo settles it independently of the name array. Every event entity a real
    // server sends carries eType = 23 + eventId, and across the whole 621-second dm
    // match: eType 97 (0x4A) and 123 (0x64) NEVER OCCUR ONCE, while eType 106 (0x53)
    // is the busiest event entity in the game at 474 lives and 1419 field
    // assertions, and eType 134 (0x6F) has 54. `Tools/demo-re/demoq.py census`
    // reproduces those counts.
    //
    // THE eventId ALSO PICKS THE PARAMETER WIDTH -- EntityEventParameterBits is
    // indexed by it -- so a wrong id is not a mislabel, it desynchronises the
    // client's bit cursor for the rest of the snapshot. Bullet hits were being sent
    // 11 bits wide; the correct entry is 8. Checked the other way too: every event
    // eType in the demo carries a parameter that FITS its image-table width.
    constexpr std::uint8_t EventSoundAlias = 0x03;
    constexpr std::uint8_t EventSoundAliasAsMaster = 0x04;
    // CODREF(Wetwork demo 36150): one event-44 carrier appears during the
    // opening helicopter assault at (3301,206,404), parameter 37. The client
    // shares its impact/fire presentation handler with event 43.
    constexpr std::uint8_t EventFireMagic = 0x2C;
    constexpr std::uint8_t EventBulletHit = 0x53;
    constexpr std::uint8_t EventPlayFx = 0x6F;
    // CODREF(Wetwork demo 431650): EV_PLAY_FX_ON_TAG attaches effect slot 41
    // to bone/tag 25 of the extraction CH-46. Its 18-bit parameter packs the
    // 9-bit effect index below the 8-bit DObj bone index; bit 17 is an option
    // flag which this recorded event leaves clear.
    constexpr std::uint8_t EventPlayFxOnTag = 0x71;
    // Wetwork's authored destruction system. EV_EXPLODER selects one of the
    // effect records published at configstring 11990 + eventParm. The demo
    // uses parameters 1..29. EV_PHYS_EXPLOSION_SPHERE carries inner radius,
    // outer radius and magnitude, while EV_EARTHQUAKE carries scale, radius
    // and duration in the same ET_EVENTS union offsets +58/+5C/+60.
    constexpr std::uint8_t EventExploder = 0x82;
    constexpr std::uint8_t EventPhysicsExplosionSphere = 0x83;
    // CODREF(Wetwork demo 416950..420200): event 134 is the six-event
    // sinking damage/effect pulse track. CG_EntityEvent reads a float32 from
    // +58 and two integer words from +5C/+60 before calling 0x004BC960.
    constexpr std::uint8_t EventRadiusDamage = 0x86;
    constexpr std::uint8_t EventEarthquake = 0x88;
    // THE KILL FEED. EV_OBITUARY is slot 143 of that same name array, and the
    // demo agrees without being asked: eType 143 + 23 = 166 has exactly 145
    // lives in the retail dm match and ET_PLAYER has exactly 145 -- one
    // obituary per death, no more and no less. Section 191p spent a day
    // correlating RELIABLE COMMANDS against kills because a feed "must" be a
    // message; it is an entity event, and `@`/`L`/`J`/`K` were all innocent.
    // THE FLESH HIT. Shooting a person currently draws the same gravel puff as
    // shooting the wall behind them, because this server spawns EV_BULLET_HIT
    // (0x53) wherever the bullet lands, person or not. A real server does not:
    // across the retail dm match it sends EV_BULLET_HIT 1419 times and
    // EV_BULLET_HIT_CLIENT_SMALL 204 / _LARGE 90 times on top, and the client
    // handler for those is a SEPARATE case that keeps the tracer origin instead
    // of zeroing it (out.exe 0x00535E91 vs 0x005359DD).
    //
    // SMALL IS SENT FOR EVERY HIT AND LARGE IS NOT SENT AT ALL, ON PURPOSE.
    // Cases 86, 87 and 88 share one block in CG_EntityEvent and the block never
    // reads the event id: it ends in
    //     sub_59A5C0(localClient, es+0x84, es+0xD8, surface, tracerStart,
    //                impactOrigin, es+0xE4)
    // with the id nowhere among the arguments, so the three ids are the same
    // behaviour and the effect is chosen from the WEAPON. Retail's split does
    // correlate with the weapon (1260/1287/1270 small, 1284/1297/1303 large),
    // but the WeaponDef byte that decides it is not identified, and inventing a
    // rule would be guessing a contract for no observable difference.
    constexpr std::uint8_t EventBulletHitClientSmall = 0x56;
    constexpr std::uint8_t EntityTypeBulletHitClient =
        EntityTypeEventBase + EventBulletHitClientSmall;
    static_assert(EntityTypeBulletHitClient == 109);
    // THE TWO CONSTANTS THE DEMO SHOWS ON EVERY FLESH HIT AND NOWHERE ELSE.
    // ET_EVENTS field 6 (es+0x0094) is 7 on all 1419 EV_BULLET_HIT and all 294
    // client hits alike -- a constant, not this server's varying surface index
    // -- and field 15 (es+0x00A0) is 6 on the client hits only. Neither is read
    // by the case-86 block; they are copied because the demo is the
    // specification of what a real server sends, and a value that is constant
    // across a whole match is not a value to invent a meaning for.
    constexpr std::uint8_t ClientBulletImpactSurfaceType = 7;
    constexpr std::uint32_t ClientBulletImpactSurface = 6;
    // THE KNIFE'S OWN IMPACT. Retail sends EV_MELEE_HIT 36 times a match and
    // this server has never sent it once, so knifing a player produces no hit
    // feedback at all. Its shape is the demo's, in all 36 assertions: origin,
    // the attacker in field 9, the weapon in field 16 and eventParm 1 -- with
    // no surface, no impact flags and no hit entity. Unlike the bullet flesh
    // hit it needs NO new writer field; every field it uses is already written.
    constexpr std::uint8_t EventMeleeHit = 0x4B;
    constexpr std::uint8_t EntityTypeMeleeHit =
        EntityTypeEventBase + EventMeleeHit;
    static_assert(EntityTypeMeleeHit == 98);
    // Its eventParm, and EntityEventParameterBits gives id 75 a width of TWO,
    // so this is the whole value space the wire allows.
    constexpr std::uint32_t MeleeHitEventParameter = 1;
    // THE PLAYER'S VOICE. EV_SOUND_ALIAS is event 3 on the ET_PLAYER RING --
    // 896 assertions a match, the largest single gap in the presentation pass --
    // and its 14-bit parameter is a CCS type 5 index in the high `p` band, so it
    // needs no configstring and no precache (sect.191n). NAMED with
    // Tools/olfinal/name-announcers.py, which already solves the base at 512:
    //
    //   p 1693 uk_f1_mp_death   1698 uk_f1_mp_pain    966 ab_f1_..  971 ab_f1_..
    //   p 1745 uk_f2_mp_death   1750 uk_f2_mp_pain   1018 ab_f2_.. 1023 ab_f2_..
    //   p 1797 uk_m1_mp_death   1802 uk_m1_mp_pain   1070 ab_m1_.. 1075 ab_m1_..
    //   p 1849 uk_m2_mp_death   1854 uk_m2_mp_pain   1122 ab_m2_.. 1127 ab_m2_..
    //
    // Sixteen entries: two FACTION prefixes x four CHARACTER voices x
    // {death, pain} -- exactly the base+{0,5,52,57} the parameters showed, with
    // death and pain five apart and the voices fifty-two.
    //
    // THE dm DEMO USES THE uk_ HALF THROUGHOUT, for every player, which is what
    // a free-for-all does with a faction voice -- so uk_ is not a guess, it is
    // what a recording of a real dm match contains. What IS unresolved is the
    // voice: retail's gender follows the CHARACTER MODEL (one player in the demo
    // is on the female pair, the rest male) and each draws from both variants of
    // its gender. Deriving that from the character record is open; alternating
    // m1/m2 by clientNum gives the same spread across players without claiming
    // to know which character is which.
    constexpr std::uint32_t PlayerVocalDeathVoice1 = 1797;   // uk_m1_mp_death
    constexpr std::uint32_t PlayerVocalPainVoice1 = 1802;    // uk_m1_mp_pain
    constexpr std::uint32_t PlayerVocalDeathVoice2 = 1849;   // uk_m2_mp_death
    constexpr std::uint32_t PlayerVocalPainVoice2 = 1854;    // uk_m2_mp_pain
    // EntityEventParameterBits gives event 3 FOURTEEN bits, so all four fit with
    // room to spare. The bound is the wire's, not the table's.
    static_assert(PlayerVocalPainVoice2 < (1u << 14));

    constexpr std::uint8_t EventObituary = 0x8F;
    constexpr std::uint8_t EntityTypeSoundAlias =
        EntityTypeEventBase + EventSoundAlias;
    constexpr std::uint8_t EntityTypeSoundAliasAsMaster =
        EntityTypeEventBase + EventSoundAliasAsMaster;
    constexpr std::uint8_t EntityTypeFireMagic =
        EntityTypeEventBase + EventFireMagic;
    static_assert(EntityTypeFireMagic == 67);
    constexpr std::uint8_t EntityTypeBulletHit =
        EntityTypeEventBase + EventBulletHit;
    constexpr std::uint8_t EntityTypePlayFx =
        EntityTypeEventBase + EventPlayFx;
    constexpr std::uint8_t EntityTypePlayFxOnTag =
        EntityTypeEventBase + EventPlayFxOnTag;
    static_assert(EntityTypePlayFxOnTag == 136);
    constexpr std::uint8_t EntityTypeExploder =
        EntityTypeEventBase + EventExploder;
    constexpr std::uint8_t EntityTypePhysicsExplosionSphere =
        EntityTypeEventBase + EventPhysicsExplosionSphere;
    constexpr std::uint8_t EntityTypeRadiusDamage =
        EntityTypeEventBase + EventRadiusDamage;
    static_assert(EntityTypeRadiusDamage == 157);
    constexpr std::uint8_t EntityTypeEarthquake =
        EntityTypeEventBase + EventEarthquake;
    constexpr std::uint8_t EntityTypeObituary =
        EntityTypeEventBase + EventObituary;
    static_assert(EntityTypeObituary == 166);
    constexpr std::uint32_t SnapshotHistoryCapacity = 32;
    constexpr std::uint32_t SnapshotDeltaWindow = 29;
    static_assert(SnapshotDeltaWindow < SnapshotHistoryCapacity);

    // OLMOD(snapshot-source-schema): gameplay lifecycle, team and loadout
    // records are source-side validated owners. They project into recovered
    // CODOL player/client/entity fields but must never be passed as native ABI.
    enum class ClientGameplayState : std::uint8_t
    {
        Inactive,
        WaitingForLoadout,
        Playing,
    };

    enum class SvCharacterFaction : std::uint8_t
    {
        Tf,
        Sc,
    };

    enum class SvTeam : std::uint8_t
    {
        None,
        Tf,
        Sc,
        Spectator,
    };

    // The character record the engine builds a player's models from: entry 0 is the
    // character item, entries 1..11 are its pieces. Twelve is sub_61B6C0's own contract
    // (it memsets an eleven-pointer output and is fed a twelve-entry record), and it is
    // OlMod::DedicatedSession::CharacterItemCount -- asserted equal in sv_snapshot_mp.cpp
    // rather than assumed here, because this header must not depend on the session
    // protocol.
    constexpr std::size_t SvCharacterRecordEntryCount = 12;

    // THE PROFILE PACKS, THE RECORD ADDRESSES. characterClasses[N].slots holds what
    // the player has equipped DENSELY and in equip order -- measured on a live client
    // the moment an outfit was put on:
    //
    //     slots = 545, 18481, 2137, 0, 0, 0, 0, 0, 0
    //     545   is the character                     -> record entry 0
    //     18481 is a piece whose recordEntry is 7    -> record entry 7 (heg)
    //     2137  is a piece whose recordEntry is 6    -> record entry 6
    //
    // Copying slot k to entry k puts a headgear item in the entry the engine reads as
    // legs, and sub_619AD0 then defaults nothing because the entries it would have
    // filled are already occupied. That is not "no outfit", it is the WRONG models.
    //
    // `recordEntryOf` is the item table -- only a process with the marketplace data
    // loaded can answer it -- and an item it declines to place is DROPPED rather than
    // guessed at. That costs at most one piece and cannot corrupt the rest.
    template <typename RecordEntryOf>
    void SV_PlaceCharacterItemsByRecordEntry(
        const std::span<const std::uint32_t> profileSlots,
        RecordEntryOf &&recordEntryOf,
        std::array<std::uint32_t, SvCharacterRecordEntryCount> &record)
    {
        record = {};
        for (const auto itemId : profileSlots)
        {
            if (!itemId)
                continue;
            const auto entry = recordEntryOf(itemId);
            if (!entry || *entry >= record.size())
                continue;
            // FIRST WRITER WINS. Two items claiming one entry is a profile this side
            // did not write and cannot arbitrate; keeping the earlier one keeps the
            // character -- entry 0, always profile slot 0 -- safe from anything after.
            if (record[*entry])
                continue;
            record[*entry] = itemId;
        }
    }

    struct SvCharacterCustomization
    {
        // CODREF(g_update_client_info): CODOL
        // CG_UpdateCharacterModelsFromClientInfo 0x0051BC80 treats clientInfo
        // field 16 as the model index: zero clears all ten character model
        // slots, while a non-zero value is copied to characterInfo +0x38C.
        // BO1 G_UpdateClientInfo 0x005FCC70 and Ghosts 0x1401167F0 likewise
        // project the authoritative player entity model index into clientInfo.
        // TODO(CODOL): recover the deleted CODOL server producer and exact
        // index namespace. The current value is supplied by the explicit
        // OLMOD(character-model-index-bootstrap) owner, not inferred here.
        std::uint8_t modelIndex{};
        SvCharacterFaction faction{ SvCharacterFaction::Tf };
        bool female{};
        std::uint8_t color{};
        std::uint16_t viewmodelIndex{};
        std::array<std::uint16_t, 11> selectionIds{};
        // The character item id, carried through from the loadout so
        // EngineBindings::resolveCharacterModelNames has its one input (section 67).
        // Deliberately NOT part of SV_PackCharacterCustomization, which is 3.3.3.3's
        // eleven-selection blob and has no consumer on this build.
        // CORRECTION (section 92): "nothing on the wire carries it" was WRONG. This
        // build's clientState field 20, +0x7C, 16 bits IS this value -- a real 1608541
        // server writes this account's own character ids into it (686, 792, 1945, 569,
        // 2056, ...) and asserts it with modelIndex 91% of the time.
        // writeClientInfoDelta sends it, and the member width IS the wire width.
        std::uint16_t characterItemId{};
        // THE WHOLE RECORD, AND IT IS NOT A WIRE FIELD. Entry 0 mirrors
        // characterItemId; entries 1..11 are the outfit pieces the player has equipped,
        // each already sitting in the entry its own item definition claims. Anything
        // left zero is what the engine fills from the character's per-slot defaults --
        // which is what every match before this carried for all eleven.
        //
        // Only the SERVER's DObj reads it today: clientInfo has exactly one character
        // field (index 20, 16 bits) and there is no second one to put pieces in, so a
        // remote player still renders from entry 0 alone. Keeping the record here is
        // what makes the server's own model set and hit detection agree with the outfit
        // the player is wearing, and it is the input any future producer would need.
        std::array<std::uint16_t, SvCharacterRecordEntryCount> recordItemIds{};
        // THE MODELS AN OUTFIT ADDS, as MODEL CONFIG-STRING INDEXES, and not a wire
        // field itself -- writeClientInfoDelta copies these into the four explicit
        // attachment pairs. Zero is absence.
        //
        // Only the EXTRAS go here. A remote client already derives the character's own
        // default set from the character item id, so attaching a default would draw it
        // twice; EngineBindings::characterOutfitAttachmentModels does that subtraction.
        std::array<std::uint16_t, 4> outfitAttachmentModelIndexes{};
        // THE BODY MODEL, AS A MODEL-BAND INDEX, for clientState +0x14. Section 168:
        // this is the model the client draws when the CHARACTER system does not
        // resolve, and it is the difference between a player and nothing. Zero means
        // "not resolved", is never written to the wire, and is not an error.
        std::uint16_t bodyModelConfigStringIndex{};

        bool operator==(const SvCharacterCustomization &) const = default;
    };

    [[nodiscard]] std::optional<SvCharacterCustomization>
    SV_ResolveCharacterCustomization(
        const std::array<std::uint16_t, 11> &selectionIds,
        bool female,
        std::uint8_t color,
        std::uint16_t viewmodelIndex,
        SvCharacterFaction faction,
        std::uint16_t characterItemId = 0,
        const std::array<std::uint16_t, SvCharacterRecordEntryCount>
            &recordItemIds = {});
    [[nodiscard]] std::array<std::uint16_t, 8>
    SV_PackCharacterCustomization(
        const SvCharacterCustomization &customization);

    struct SvResolvedWeapon
    {
        std::uint16_t weaponAssetIndex{};
        std::uint16_t ammoIndex{};
        std::int16_t clipIndex{};
        std::uint16_t clipSize{};
        std::uint16_t maxAmmo{};
        std::uint8_t weaponType{};
        std::uint8_t weaponClass{};
        std::uint8_t penetrateType{};
        std::uint8_t impactType{};
        std::uint8_t fireType{};
        std::uint8_t shotCount{};
        std::uint16_t fireDelayMilliseconds{};
        std::uint16_t fireTimeMilliseconds{};
        std::uint16_t dropTimeMilliseconds{};
        std::uint16_t raiseTimeMilliseconds{};
        float hipSpreadStandMin{};
        float hipSpreadCrouchMin{};
        float hipSpreadProneMin{};
        float hipSpreadStandMax{};
        float hipSpreadCrouchMax{};
        float hipSpreadProneMax{};
        float adsSpread{};
        SvWeaponDamageCurve damageCurve{};
        std::array<float, HitLocationCount> hitLocationMultipliers{};
        // Five flags in the same four-byte storage formerly occupied by four
        // bools; SvResolvedLoadout is embedded in persistent player nodes.
        std::uint32_t aimDownSight : 1 {};
        std::uint32_t hasOverlayReticle : 1 {};
        std::uint32_t rifleBullet : 1 {};
        std::uint32_t bulletExplosiveDamage : 1 {};
        std::uint32_t dualWieldCapable : 1 {};
        std::string weaponName;

        bool operator==(const SvResolvedWeapon &) const = default;
    };

    struct SvResolvedLoadout
    {
        SvResolvedWeapon primary;
        SvResolvedWeapon secondary;

        bool operator==(const SvResolvedLoadout &) const = default;
    };

    [[nodiscard]] bool SV_IsResolvedLoadoutValid(
        const SvResolvedLoadout &loadout);
    [[nodiscard]] const SvResolvedWeapon *SV_FindResolvedWeapon(
        const SvResolvedLoadout &loadout,
        std::uint16_t weaponAssetIndex);

    struct SvHeldWeaponState
    {
        std::uint16_t weaponAssetIndex{};
        bool heldBefore{};
        std::array<bool, 4> unknownState{};

        bool operator==(const SvHeldWeaponState &) const = default;
    };

    struct SvAmmoClipState
    {
        std::int16_t clipIndex{};
        std::array<std::uint16_t, 2> count{};

        bool operator==(const SvAmmoClipState &) const = default;
    };

    struct SvAmmoPoolState
    {
        std::uint16_t ammoIndex{};
        std::uint16_t count{};

        bool operator==(const SvAmmoPoolState &) const = default;
    };

    enum class SvObjectiveState : std::uint8_t
    {
        Empty,
        Active,
        Invisible,
        Done,
        Current,
        Failed,
    };

    struct SvObjective
    {
        SvObjectiveState state{ SvObjectiveState::Empty };
        std::array<float, 3> origin{};
        std::uint16_t icon{};
        std::uint16_t entityNum{};
        std::uint8_t teamNum{};

        bool operator==(const SvObjective &) const = default;
    };

    // MEASURED (dm demo, serverTime 648700). PM_INTERMISSION in IW's own
    // ordering, and the value the retail dm server writes when the match ends;
    // during play the same field reads 0 alive and 8 dead.
    inline constexpr std::uint8_t SvPmTypeIntermission = 5;
    // CODOL PM_DEAD, established by local client consumers and used by the
    // folded die handler in sv_snapshot_mp.cpp.
    inline constexpr std::uint8_t SvPmTypeDead = 8;
    // PM_NORMAL. The value a living, walking player carries, and the ONLY value
    // noclip is allowed to replace or restore -- see applyNoclipHold.
    inline constexpr std::uint8_t SvPmTypeNormal = 0;
    // PM_NOCLIP, **MEASURED** off out.exe rather than carried over from IW's
    // header. PmoveSingle (0x0041CB40) switches on playerState +0x004 and its
    // `case 2` is sub_415FE0 followed by PM_DropTimers -- and sub_415FE0 is
    // PM_NoclipMove beyond argument: it applies friction to +0x03C, builds a
    // wish direction from forwardmove/rightmove with jump (0x1) as up and
    // crouch (0x100000) as down, multiplies the speed by ten while the sprint
    // bit is held, and then adds velocity * frametime straight into the origin
    // at +0x030 with NO trace, NO ground check and NO clip. `case 3` is the
    // same shape around sub_416230, which is PM_UFO.
    //
    // The rest of the switch pins the ordering as IW's ten-entry pmtype_t, not
    // the nine-entry one section 153a guessed at: `case 1` shares its body with
    // `case 9` and both zero the velocity and write groundEntityNum 2047
    // (+0x0C0), which is NORMAL_LINKED and DEAD_LINKED; `case 6` runs no
    // movement handler at all; and PM_NORMAL falls through to `default`.
    inline constexpr std::uint8_t SvPmTypeNoclip = 2;
    // How long the dedicated keeps a player flying after the last message from
    // the key poller. Chosen against the poller's own 500 ms repeat: two missed
    // keep-alives end it. A LOST key-up must not strand anyone in the air.
    inline constexpr std::uint32_t SvNoclipDefaultHoldMilliseconds = 1'500;
    inline constexpr std::uint32_t SvNoclipMaximumHoldMilliseconds = 10'000;
    // How long after a spawn zeroes perks before the real value is written.
    // The gap only has to outlast the client's HUD coming up; retail's own
    // zero-to-value gap in the dm demo is 100 ms at 45600->45700, and its
    // respawn gap is 1.6 s. Half a second sits inside both and is invisible.
    inline constexpr std::uint32_t SvPerkAssertDelayMilliseconds = 500;
    // CODREF(out.exe 1649370): CG_ScriptMover 0x522088 tests this bit and
    // returns at 0x5220A2 for an unlinked figure. It means hidden, not a
    // presentation mode. Intermission players retain it; podium figures clear it.
    inline constexpr std::uint32_t SvEFlagsNoDraw = 0x10;
    inline constexpr std::uint32_t SvEFlagsIntermission = SvEFlagsNoDraw;
    // MEASURED (dm demo): pm_flags becomes 2048 at serverTime 632800, one second
    // after the match is decided at 631800, and the player's origin is not
    // asserted again until the killcam at 642900. Eleven seconds frozen. It is a
    // DIFFERENT mechanism from the intermission at +17000 -- pm_type does not
    // change here at all.
    inline constexpr std::uint32_t SvPmFlagsMatchEndFrozen = 0x800;
    // playerState +0x06C, netfield index 169, on the frame the podium camera
    // takes over. Retail sends 20 and nothing else, ever (HANDOFF 129).
    //
    // DO NOT publish global configstring 5896 + 20. sub_514880 first checks
    // that global slot, then falls through to client config category 9 when it
    // is empty. A live memory walk of category 9 resolves its relative entry
    // 19 to `tag_origin`, which is the retail camera bone. Writing CS 5916
    // replaces client-owned CCS state and makes out.exe raise a blank EXE_ERROR
    // before the camera bind. The numeric 20 and the empty global slot are both
    // required parts of the retail path.
    inline constexpr std::uint32_t SvPodiumViewTag = 20;
    // An entityState eFlags bit a real server sets on 13 ET_SCRIPTMOVER lives across the
    // retail dm match. MEASURED, not named -- what it means is unknown (HANDOFF 135).
    inline constexpr std::uint32_t SvEFlagsScriptMoverMeasuredBit1 = 0x2;
    // THE KILLCAM'S CONSTANTS, ALL FOUR MEASURED IN THE RETAIL dm DEMO.
    //
    //   killCamEntity   2047 on every one of the eight killcams and never
    //                   anything else -- the same all-ones "none" every other
    //                   11-bit entity field uses
    //   the DELAY       the killcam starts EXACTLY 1500 ms after `u 10`, on all
    //                   seven deaths that had one. The seventeen deaths with no
    //                   killcam are the ones whose respawn landed at the same
    //                   1500 ms, so the rule is "at +1500 if still dead" and
    //                   not a selection among deaths
    //   the REWIND      deltaTime runs 6000..6500 on deaths and 16450 at match
    //                   end. Subtracting the 1500 ms delay leaves 4500..5000 ms
    //                   of footage BEFORE the kill; five seconds is the modal
    //                   value and what this server sends. The 500 ms spread has
    //                   no explanation here -- it is not the delay, which is
    //                   constant, so something upstream shortens the replay
    // MEASURED: damageDuration reads 750 on 28 of its 30 assertions in the
    // retail dm demo (the other two are 200 and 737, both once). damageTimer is
    // set to it on the hit and counts down to exactly zero.
    inline constexpr std::uint32_t SvFlinchDurationMilliseconds = 750;
    inline constexpr std::uint32_t SvKillCamEntityNone = 2047;
    // ENTITYNUM_NONE for the cursor hint. The client indexes its centity array
    // with this value directly (`imul edx, 270h` in sub_45A450), so it is the
    // one number that must never be a live entity.
    inline constexpr std::uint32_t SvNoHintEntityNum = 2047;
    // The cursorHint enum, read out of sub_45BA10's icon switch and pinned to
    // the four names at out.exe 0xE59FA0 by dword_1C1DBDC[3]/[4] being the
    // materials sub_44D540 registers as `hint_health` and `hint_friendly`.
    enum class SvCursorHint : std::uint16_t
    {
        None = 0,
        NoIcon = 1,
        Activate = 2,
        Health = 3,
        Friendly = 4,
    };
    // 5..1704 is "weapon (value - 4)" and takes its text from
    // PLATFORM_PICKUPNEWWEAPON rather than from a hint string.
    inline constexpr std::uint16_t SvCursorHintWeaponBase = 4;
    inline constexpr std::uint16_t SvCursorHintMaximum = 1704;

    // A CRATE THAT MEANS A GUN. Everything battle royale needs on top of a script
    // model is the answer to "what do I get", and a radius so the server knows when
    // to offer it.
    //
    // THE ORIGIN IS COPIED, NOT LOOKED UP. Loot does not move -- it is a static
    // script mover -- and the alternative is a whole SvGameEntity copy per crate per
    // client per frame just to read three floats out of it.
    // SEPARATES A LOOT ANSWER FROM A TRIGGER ANSWER in the one map that remembers
    // what each client was last told. Trigger indices are small; nothing can reach
    // this bit by counting triggers.
    inline constexpr std::uint32_t SvLootHintKeyBase = 0x10000u;

    struct SvLootItem
    {
        SvEntityHandle handle{};
        std::uint16_t weaponAssetIndex{};
        float radius{};
        std::array<float, 3> origin{};

        bool operator==(const SvLootItem &) const = default;
    };
    inline constexpr std::uint32_t SvKillCamDelayMilliseconds = 1500;
    inline constexpr std::uint32_t SvKillCamPreKillMilliseconds = 5000;

    enum class SvHudElemType : std::uint8_t
    {
        Free = 0,
        // CODREF(1649370): out.exe sub_538B70 case 1 reads the localized
        // string index from hudelem+0x8C (descriptor field 22). The former
        // outcome aliases 4 and 8 were raw XOR payloads from a decoder that
        // did not reconstruct the acknowledged hudelem baseline: 4 is an
        // icon/special path and 8 is a fixed seconds timer.
        Text = 1,
        // THESE NUMBERS ARE OLfinal's, READ OFF A RETAIL OLfinal SERVER, AND
        // THEY ARE NOT 3.3.3.3's. That distinction cost this file real bugs.
        //
        // Everything here used to be justified by addresses in the 0x00BB..0xBF
        // range - 0x00BD81C3, 0x00BD8AF8, sub_BB5680, sub_BB4B70, sub_AB4490.
        // NONE OF THEM MEAN ANYTHING IN out.exe. They are dest1yo's 3.3.3.3
        // client's addresses, and they land in unrelated out.exe code: the
        // function containing 0x00BD81C3 here is sub_BD7780, which registers
        // r_picmip, r_specular and r_displayMode. It is a dvar registrar, not a
        // HUD drawer. The 3.3.3.3 reading was correct FOR 3.3.3.3; importing
        // its type numbering into an OLfinal tree was not.
        //
        // MEASURED instead from C-2021-7-25[1-19-26]dm.demo, which section 109
        // establishes is THIS build (four configstring indices match out.exe,
        // sixteen of sixteen asset names are present in this install's zones,
        // SVC_EOF is 5). Whole elements mined with
        // Tools/olfinal/mine-hudelem-tuples.py, which groups the fields a
        // server asserted in ONE snapshot rather than accumulating a reused
        // slot across the match:
        //
        //   TYPE 5   x=-12 y=-12 w=24 h=48 alignScreen=0x22 target=2047
        //            fromColor=alpha31 color=alpha0 fadeTime=1000
        //            -> the HIT MARKER, and its geometry is exactly what this
        //               file already had. Only the TYPE was 3.3.3.3's.
        //   TYPE 2   y=-50 alignOrg=5 alignScreen=0x22 value=50 label=397
        //            fontScale=0.9 fromFontScale=3.0 scaleTime=200/100
        //            fadeTime=750  -> the SCORE POPUP. Type 2 is unchanged.
        //   TYPE 14  x=7924 y=2161 w=10 h=10 material=151
        //            -> the only WORLD-COORDINATE element with a material.
        //   TYPE 4   640x480 material=1 -> a full-screen backdrop on OLfinal,
        //            which is what an icon elem sent as type 4 would become.
        //
        // Value = 2 survives unchanged; Icon and Waypoint each move by one.
        Value = 2,
        // MEASURED (dm demo, serverTime 632900): the three FFA outcome rows
        // carrying client numbers 6, 3 and 1 all use type 3. IW4's
        // `setPlayerNameString` gives the matching producer responsibility.
        PlayerName = 3,
        Icon = 5,
        // CODREF(factory-link-clock): OLfinal563043 renders recorded type12
        // using material+needle and time+80/duration+84; not a text timer.
        ClockDown = 12,
        Waypoint = 14,
        // CODREF(1649370): sub_538360/sub_538430 prove the OLfinal timer
        // families are 6..8 (seconds) and 9..11 (tenths). They remain outside
        // the server's admitted producer set until a feature needs them.
    };

    struct SvHudElem
    {
        SvHudElemType type{ SvHudElemType::Free };
        std::array<float, 3> origin{};
        std::uint16_t targetEntNum{};
        std::uint16_t materialIndex{};
        std::uint16_t width{};
        std::uint16_t height{};
        std::uint32_t color{};
        float value{};
        std::uint32_t flags{};
        // CODREF: the two alignment fields the client applies to every elem in
        // sub_BB4780, which the drawer prologue calls through sub_BB4B70 before
        // the type switch. With moveTime [elem+74h] <= 0 the non-lerp tail at
        // 0x00BB48A6 loads "ecx,[edx+2Ch]" and "ebx,[edx+28h]":
        //   alignOrg    [elem+28h]  descriptor 15, 4 bits
        //   alignScreen [elem+2Ch]  descriptor 11, 8 bits
        // alignScreen's high nibble picks the horizontal anchor mode passed to
        // sub_B236A0 and its low nibble the vertical mode for sub_B237C0; mode
        // 2 is "screenScale*coord + screenWidth*0.5" (0x00B236D7) and its
        // vertical twin (0x00B237F9), i.e. the screen centre, so an elem placed
        // that way needs no knowledge of the client's resolution. alignOrg
        // then subtracts flt_12F7860[(v>>2)&3]*width horizontally and
        // flt_12F7860[v&3]*height vertically, where flt_12F7860 is
        // {0.0, 0.5, 1.0}: sub-index 1 centres the material on the anchor.
        std::uint8_t alignOrg{};
        std::uint8_t alignScreen{};
        // CODREF: descriptor 16, [elem+14h], bits -86. sub_BB4B70 reads it at
        // 0x00BB4C60 as the text height before the 0.25/0.33/0.5 font-family
        // factor and the screen scale, so a zero here draws nothing. Its wire
        // codec is at 0x00C42EE5 in the generic field reader: SIX RAW BITS
        // divided by 10.0 with no change prefix, i.e. 0.0 to 6.3 in tenths.
        float fontScale{};
        // CODREF: descriptor 20, [elem+24h], 4 bits. sub_BB4B70's FIRST switch
        // maps it to a font handle and a size factor - 1 and 6 give 0.5, 2 and
        // 7 give 1/3, everything else 0.25.
        std::uint8_t font{};
        // CODREF: the colour fade. sub_AB4490 resolves an elem's drawn colour
        // as lerp(fromColor, color, (serverTime - fadeStartTime) / fadeTime),
        // holding at colour once the window closes (0x00AB44B0). So `color` is
        // the END of the fade and `fromColor` its START - the opposite of the
        // reading the names invite. The four live at 0x30/0x34/0x38/0x3C as
        // descriptors 0, 12, 10 and 13.
        std::uint32_t fromColor{};
        std::uint32_t fadeStartTime{};
        std::uint16_t fadeTime{};
        // CODREF: the scale animation, the same shape one struct earlier.
        // sub_BB4B70 lerps [elem+18h] to [elem+14h] across
        // [elem+1Ch, elem+1Ch + elem+20h] at 0x00BB4C3A, so fromFontScale is
        // the start and fontScale the end. Descriptors 19, 16, 17 and 18.
        float fromFontScale{};
        std::uint32_t scaleStartTime{};
        std::uint16_t scaleTime{};
        // CODREF: descriptor 33, [elem+40h], 10 bits - the localized string
        // drawn BESIDE the value. sub_BB4B70 resolves it at 0x00BB4CF6 as
        // sub_B99850(label + 952) into ctx+16, and sub_BB4A30 joins that with
        // the formatted value when both are present, which is how "+" and
        // "100" become one run of text.
        std::uint16_t label{};
        // Descriptor 27, [elem+8Ch], codec -85. Only the text drawers read it:
        // 0x00BD7DC1 and 0x00BD829A do "lea ecx,[ebx+8Ch] / mov eax,
        // offset unk_D0B9F48 / call sub_BB4F50" before the glyph run. Named
        // after IW's hudelem field of the same position and role; the retail
        // demo sets it to the elem's own colour at zero alpha.
        std::uint32_t glowColor{};
        // CODREF: descriptor 21, [elem+88h], a full float. The collector
        // sub_BB5FB0 gathers both arrays and qsorts them with sub_BB5F60,
        // which compares exactly this field, so it is the DRAW ORDER key and
        // a larger value lands on top.
        float sort{};

        // CODREF(factory-link-clock): native HUD+80/+84, descriptors34/41.
        // Type-scoped storage preserves the address-sensitive player layout.
        void setClock(std::uint32_t deadline, std::uint16_t dialMilliseconds) {
            scaleStartTime=deadline; scaleTime=dialMilliseconds;
        }
        [[nodiscard]] bool isClock() const { return type==SvHudElemType::ClockDown; }

        // OLMOD(factory_ammo): type-scoped view of unused icon text fields keeps
        // SvHudElem/WorldClientState layout stable. Writer maps this view only to
        // native size-animation descriptors23..26, never text/value fields.
        void setIconSizeAnimation(std::uint16_t fromWidth, std::uint16_t fromHeight,
            std::uint32_t start, std::uint16_t duration) {
            value = static_cast<float>(fromWidth); label = fromHeight;
            scaleStartTime = start; scaleTime = duration;
        }
        [[nodiscard]] bool hasIconSizeAnimation() const {
            return type == SvHudElemType::Icon && scaleTime != 0;
        }

        bool operator==(const SvHudElem &) const = default;
    };

    // THE PERK MASK A RETAIL OLfinal CLIENT ACTUALLY CARRIED, for 4078 of the
    // 6160 frames of C-2021-7-25[1-19-26]dm.demo - field 123 bits 2 and 7,
    // field 124 bit 24. Three set bits: a default three-perk loadout.
    //
    // THREE IS THE COMMON CASE, NOT THE RULE. The same demo also carries 4-, 5-
    // and 6-bit states - (268, 16777216, 0), (896, 16777216, 0),
    // (300, 16777216, 0), (420, 17039360, 0) - and a PERK GREED wildcard is
    // exactly what puts a player above three. An earlier note here read
    // "exactly three set bits, which is exactly three perks" as if three were
    // a bound; it is a default, and the wider states are loadouts rather than
    // decode noise. Nothing here should assume a count.
    //
    // THIS IS A MEASURED PLACEHOLDER, NOT A LOADOUT. Which perk each bit means
    // is NOT established: the client ships loadoutPerk1/2/3 and
    // mp/coPerkStatsTable.csv is referenced by name in common_mp.ff, but that
    // table asset is not in any zone extracted so far and no ordered perk list
    // has been found to number the bits from. So every player currently gets
    // the same three perks a real player had, rather than the three they chose.
    // When the mapping is derived only the SOURCE of this value changes; the
    // netfield plumbing below is already what retail uses.
    inline constexpr std::array<std::uint32_t, 3> SvRetailLivePerks{
        132u, 16777216u, 0u };

    struct SvPlayerState
    {
        // CODDIFF(sv_build_client_snapshot): this is a typed source projection
        // of recovered playerState fields, not playerState_s. Usercmd-only
        // buttons/moves at the tail are runtime diagnostics and are not emitted
        // by the playerstate delta writer.
        std::uint32_t clientNum{};
        std::uint32_t commandTime{};
        std::uint8_t pmType{};
        // CODOL ps+0x78, field 88 (8 bits). Uses the former alignment byte.
        std::uint8_t killstreak{};
        // CODREF(1649370): playerState +0x3E4, field 53 (11 bits).
        // Use the existing alignment gap before pmTime so WorldClientState's
        // address-sensitive allocation size and all following offsets stay fixed.
        std::uint16_t offhandWeaponAssetIndex{};
        std::uint32_t pmTime{};
        std::uint32_t pmFlags{};
        std::uint32_t eFlags{};
        std::uint32_t otherFlags{};
        // THE PERK SET. Three consecutive 32-bit netfields, indices 123/124/125
        // at offsets 0x584/0x588/0x58C, and this server has never written any of
        // them - which is why no perk icon has ever appeared.
        //
        // PERKS ARE NOT A hudElem, and that was worth measuring before building
        // one. Every material-bearing element in the retail dm demo is the hit
        // marker (24x48), a 120x9 bar, a 640x480 backdrop or a waypoint (10x10);
        // there is no small repeated icon and nothing that looks like a perk
        // row. The client instead ships `loadoutPerk1/2/3` and a
        // `perk_sidebar_hud`, and draws the row from playerState.
        //
        // MEASURED (Tools/olfinal/mine-perk-bits.py over all 6160 snapshots):
        // tracked as a TRIPLE rather than three histograms, because the question
        // is what they hold together at one instant. The dominant live state is
        //
        //     (132, 16777216, 0)   4078 of 6160 frames, EXACTLY THREE SET BITS
        //                          field 123 bits 2 and 7, field 124 bit 24
        //
        // Three bits, three perks, three icons. Field 125 is zero while a player
        // is alive and only carries anything before the first spawn and during
        // the outro, so the live mask is 123 and 124.
        std::array<std::uint32_t, 3> perks{};
        // THE PERK HUD ELEMENT'S OWN VISIBILITY BIT -- netfield index 122, ps+0x580,
        // codec -57 (one bit on the wire, a BYTE in the struct).
        //
        // ui_mp/hud_720.txt's perk_sidebar_hud asks UI expression opcode 244, which
        // occurs exactly twice in that entire 643 KB asset and both times inside that
        // element. Opcode 244 is sub_59FBD0 and it is nothing but
        //
        //     ps[0x580] != 0  ||  cl_ishostasspectator != 0
        //
        // The second is a caster flag and reads 0 for a player, measured live. So this
        // byte is the only thing that can make the element visible, and until now this
        // server never sent field 122 at all - the element was painted every frame and
        // evaluated its own gate to false. See HANDOFF section 117h.
        //
        // PLAYER-ACCEPTED 2026-08-23: with this set whenever a living player holds
        // perks, the sidebar comes up and STAYS up, and a player looking at it called
        // that right. So this is finished as a feature and what follows is a PARITY
        // note, not a defect - do not "fix" it into a flash on somebody's guess.
        //
        // TODO(CODOL): the retail TRIGGER is still not established. The dm demo asserts
        // index 122 nine times (0x7, 1x2) in 621 seconds while perks[0] is asserted 169
        // times in the same match, so "the player has perks" is NOT what retail keys it
        // on, and a demo replay would diff here. Exit condition: decode WHEN the demo's
        // two 1s occur and what changed alongside them.
        std::uint8_t perkHudVisible{};
        // THE COMPASS RADAR BIT -- playerState index 86, +0x0278, ONE bit.
        //
        // DEFAULTS TO 1 BECAUSE THE DEMO DOES. The retail dm match asserts this
        // field exactly twice in 621 seconds:
        //
        //     @43100   (the FIRST snapshot)   (new) -> 1
        //     @648700  (match end / outro)       1 -> 0
        //
        // so it is not a UAV toggle and not a killstreak -- a dm server turns it
        // on before anyone has moved and holds it for the entire match. This
        // server has never sent it at all.
        //
        // THE NAME IS BORROWED AND THE OFFSET IS MEASURED. ps-census calls index
        // 86 `radarEnabled` at `conflict` confidence: that came from MW3, where
        // the field sits at 0x230, and here it is 0x278. What is reproduced here
        // is the OFFSET, the WIDTH and the two TIMES, all read off the demo --
        // the label is not load-bearing. NECESSARY, NOT PROVEN SUFFICIENT: the
        // compass draw (out.exe sub_51A640) picks its blip material from flags
        // on a per-blip record, and whether this bit is what fills that record
        // is NOT established. Do not report the radar as done on this alone.
        std::uint8_t compassRadarEnabled{ 1 };
        std::uint8_t bobCycle{};
        // CODREF(1649370): secured ps+0x260, field 82 / codec -101.
        // Six absolute radar bits; uses the alignment byte before origin.
        std::uint8_t radarFlags{};
        std::array<float, 3> origin{};
        std::array<float, 3> velocity{};
        std::int8_t movementDir{};
        // CODREF(1649370): +0x3E8/+0x3EC/+0x3F0, fields 109..111,
        // button-selected offhand assets. Each uses an existing alignment gap
        // (before gravity/lastSprintStart/legsTimer) to preserve the native node.
        std::uint16_t offhandWeaponSlotA{};
        std::uint32_t gravity{};
        std::uint32_t speed{};
        float moveSpeedScaleMultiplier{};
        std::array<float, 3> deltaAngles{};
        std::array<float, 3> ladderVector{};
        std::array<float, 3> viewAngles{};
        float proneDirection{};
        float proneDirectionPitch{};
        float proneTorsoPitch{};
        std::uint32_t proneTransitionStartTime{};
        std::uint8_t sprintButtonUpRequired{};
        std::uint8_t sprintDelay{};
        std::uint16_t offhandWeaponSlotB{};
        std::uint32_t lastSprintStart{};
        std::uint32_t lastSprintEnd{};
        std::uint32_t sprintStartMaxLength{};
        float mantleYaw{};
        std::uint32_t mantleTimer{};
        std::uint8_t mantleTransitionIndex{};
        std::uint8_t mantleFlags{};
        std::uint16_t offhandWeaponSlotC{};
        std::uint32_t legsTimer{};
        std::uint16_t legsAnim{};
        std::array<std::uint8_t, 2> rewardIdsLow{};
        std::uint32_t torsoTimer{};
        std::uint16_t torsoAnim{};
        std::array<std::uint16_t, 2> weaponAnim{};
        // CODREF(1649370): actionSlotParam[1], ps+658 / field204, key4.
        std::uint16_t rewardActionWeapon{};
        std::array<std::int32_t, 2> weaponTime{};
        std::array<std::int32_t, 2> weaponDelay{};
        std::array<std::int32_t, 2> weaponRestrictKickTime{};
        std::array<std::uint8_t, 2> weaponState{};
        std::array<std::uint8_t, 2> weaponHandFlags{};
        std::array<std::uint8_t, 2> weaponShotCount{};
        std::uint16_t currentWeaponAssetIndex{};
        float weaponPositionFraction{};
        // TODO(CODOL): field 4 / playerState_s +0x4A4 is a -70 time value.
        // Keep the offset-derived name until a CODOL producer closes its
        // gameplay meaning; Ghosts calls its analogue weaponIdleTime.
        std::uint32_t unk04A4Time{};
        float aimSpreadScale{};
        std::int32_t spreadOverride{};
        std::int32_t spreadOverrideState{};
        std::uint16_t viewmodelIndex{};
        std::array<SvHeldWeaponState, 15> heldWeapons{};
        std::array<SvAmmoClipState, 15> ammoClips{};
        std::array<SvAmmoPoolState, 15> ammoPools{};
        std::array<SvObjective, 32> objectives{};
        std::array<SvHudElem, 31> hudCurrent{};
        std::array<SvHudElem, 31> hudArchival{};
        std::uint32_t damageEvent{};
        std::uint32_t damageYaw{};
        std::uint32_t damagePitch{};
        std::uint32_t damageCount{};
        // THE FLINCH, WHICH IS THE HALF OF BEING SHOT THAT LASTS. The four
        // above are the direction indicator and fire once; these two are the
        // hold. MEASURED in the retail dm demo: damageDuration is 750 on 28 of
        // 30 assertions and damageTimer is set to it on the hit and counts down
        // to zero in real time, restarting on a second hit inside the window.
        //
        // flinchYawAnim (index 76, 2 bits, 184 assertions) is the third and is
        // deliberately absent: it is NOT a function of damageYaw. Retail pairs
        // yaw 219 with anim 0, 222 with 2 and 221 with 3, and yaw 255 with 0
        // against 254 with 2 -- so whatever selects it is not on the wire, and
        // 0 is the value the client already holds.
        std::uint32_t damageTimer{};
        std::uint32_t damageDuration{};
        // THE PREDICTABLE EVENT RING, WHICH THIS SERVER ALREADY HAD AND NEVER
        // SENT. It is the single largest thing missing from the playerState:
        // the retail dm demo asserts pe.eventSequence and pe.oldEventSequence
        // 4225 times EACH and the four ring slots about 1200 times each --
        // roughly eleven thousand assertions in one match, and none of them
        // was ours. This is footsteps, landings, weapon fire, reloads and
        // pickups: everything that happens between the kills.
        //
        // AND THE EVENTS ARE NOT NEW WORK. The native engine's own Pmove
        // produces them, SV_ReadNativePredictableEvents already pulls them out
        // of the native playerState after every think, and the bullet path
        // already consumes them. They were read, used server-side, and dropped
        // before the wire.
        //
        // The native offsets and the netfield offsets are the same numbers:
        // PredictableEventSequenceOffset is 0x108, which is netfield index 1,
        // and PredictableEventsOffset is 0x10C, which is index 21. The ring is
        // indexed by `sequence & 3`, so it is copied SLOT FOR SLOT rather than
        // in the order the batch reader returns.
        std::uint32_t predictableEventSequence{};
        std::uint32_t predictableOldEventSequence{};
        std::array<SvEntityEvent, 4> predictableEvents{};
        std::uint32_t health{};
        std::uint32_t maxHealth{};
        std::int32_t deadYaw{};
        std::uint32_t shellshockIndex{};
        std::uint32_t shellshockTime{};
        std::uint32_t shellshockDuration{};
        std::uint8_t spawnGeneration{};
        std::array<std::uint8_t, 3> rewardIdsHigh{};
        float viewHeightCurrent{};
        std::int32_t viewHeightTarget{};
        std::int32_t viewHeightLerpTarget{};
        std::int32_t viewHeightLerpTime{};
        bool viewHeightLerpDown{};
        std::array<std::uint8_t, 3> rewardTargetsHigh{};
        float playerSizeScale{};
        std::uint32_t groundEntityNum{};
        std::uint32_t jumpTime{};
        float jumpOriginZ{};
        std::uint32_t viewEntityNum{};
        // THE USABLE PROMPT -- "hold F to open", the mystery box, the perk
        // machine. Three fields, netfields 67 / 80 / 78, and the client does
        // ALL of the rest: the fade, the icon, the +activate key substitution
        // and the localization lookup. See re/demo-re/18-hint-strings.md.
        //
        // cursorHint IS THE GATE and nothing else is. sub_45A450 reads ps+0x24C
        // first and returns immediately when it is zero, so a hint string with
        // no cursorHint draws nothing at all. Its values are an enum up to 4 --
        // 0 HINT_NONE, 1 HINT_NOICON, 2 HINT_ACTIVATE, 3 HINT_HEALTH,
        // 4 HINT_FRIENDLY -- and 5..1704 means "weapon (value - 4)", which takes
        // its text from PLATFORM_PICKUPNEWWEAPON instead of the string below.
        // Every zm usable prompt in the retail captures is HINT_NOICON.
        std::uint16_t cursorHint{};
        std::array<std::uint8_t, 2> rewardTargetsLow{};
        // The RELATIVE index into configstring band 856. SIGNED -- codec -8,
        // sign-extended from bit 7 by the client -- which is the only thing
        // that makes retail's idle value of -1 expressible.
        //
        // ZERO HERE, NOT -1, AND THAT IS A DELIBERATE DEPARTURE. Retail idles
        // these two at -1 and 2047; this server idles them at 0. The client
        // cannot tell, because sub_45A450 reads cursorHint FIRST and returns
        // before touching either of them, and its own fade-out path writes
        // (0, -1) into the HUD cache regardless of what the playerState says.
        // What the departure buys is that a player who never looks at anything
        // usable pays no bits at all: a null delta baseline is a ZEROED
        // playerState, so retail's sentinels would be sent to every client on
        // its first snapshot forever, to say nothing.
        std::int32_t cursorHintString{};
        // The entity the hint belongs to. The client multiplies it by 624 and
        // indexes its centity array with it, so a value that is neither a live
        // entity nor ENTITYNUM_NONE reads a stranger's centity. Idles at 0 for
        // the reason above; 0 is the worldspawn and is never hinted.
        std::uint32_t cursorHintEntityNum{};
        std::uint32_t movingPlatformEntityNum{};
        std::uint32_t remoteEyesEntityNum{};
        std::uint32_t remoteControlEntityNum{};
        // MEASURED, NOT TRANSFERRED (HANDOFF 129). This member reaches netfield
        // index 168, which is playerState OFFSET 0x068, and the retail dm demo
        // asserts that field EXACTLY ONCE in 621 seconds -- on the frame the
        // podium camera takes over, carrying the camera ENTITY NUMBER (713).
        // Index 169 at +0x06C is asserted on the same frame and only then,
        // carrying 20, a tag index. So this pair is the engine's
        // remoteControlEnt/tag whatever the netfield NAME transfer calls it,
        // and it is how retail moves the outro camera: the player is not
        // teleported, the player's VIEW is handed to an entity that animates.
        //
        // The port's names for this run are shifted by one slot against the
        // transferred names (remoteEyes/remoteControl/remoteTurret sit at
        // 0x05C/0x064/0x068 here, the table says 0x060/0x064/0x068 are
        // remoteEyesEnt/remoteEyesTagname/remoteControlEnt). The OFFSETS are
        // consistent end to end, so nothing is mis-sent -- only mis-named.
        // Renaming is a separate, wide change and is deliberately not done
        // here; see 129 before quoting either name as truth.
        std::uint32_t remoteTurretEntityNum{};
        // +0x06C, netfield index 169, 6 bits. Retail sends 20 with the camera.
        std::uint32_t remoteControlTag{};
        std::uint32_t linkEntityNum{};
        // THE KILLCAM, AND IT IS FOUR FIELDS AND ONE COMMAND (HANDOFF 141).
        //
        // Measured in the retail dm demo, which asserts all four together on
        // exactly eight frames in ten minutes and clears them together after:
        //
        //   136  +0x0C4C  11  killCamEntity        2047 while the killcam runs
        //   137  +0x0C50  11  killCamLookAtEntity  the VICTIM's entity number
        //   138  +0x0C54   8  killCamClientNum     the KILLER's clientNum
        //   142  +0x0C48  32  deltaTime            how far to rewind, in ms
        //
        // On every one of those eight frames the same frame also carries the
        // reliable command `i 0 0.000000 0 1`, and on no other frame in the
        // match does either appear. Seven are deaths, at death-camera + 1500 ms
        // exactly; the eighth is the match-end killcam, with deltaTime 16450
        // instead of the deaths' 6000..6500.
        //
        // The names are `confirmed` in the netfield table, all four are type 0,
        // and their values are a complete specification of the feature: the
        // client already knows how to replay its own snapshot history, and this
        // server had never told it to.
        // Native wire domains are 11/11/8 bits; uint16 still admits invalid
        // wire values for validation. This is NOT a native structure layout.
        std::uint16_t killCamEntityNum{};
        std::uint16_t grenadeEntityNum{};
        std::uint16_t killCamLookAtEntityNum{};
        std::int16_t grenadeTimeLeft{};
        std::uint16_t killCamClientNum{};
        std::uint16_t weaponFlagsLow{};
        std::uint32_t killCamDeltaTime{};
        std::uint32_t buttons{};
        std::int8_t forwardMove{};
        std::int8_t rightMove{};
        // CODREF(1649370): actionSlotType[1], ps+644 / field187.
        // Both action members occupy existing source alignment gaps.
        std::uint8_t rewardActionType{};
        // CODREF(1649370): ps+400, field77, 24 bits. Split source storage
        // preserves the address-sensitive allocation size, like reward slots.
        std::uint8_t weaponFlagsHigh{};

        [[nodiscard]] std::uint32_t weaponFlags() const {
            return weaponFlagsLow | (static_cast<std::uint32_t>(weaponFlagsHigh) << 16);
        }
        void setWeaponFlags(std::uint32_t flags) {
            weaponFlagsLow=static_cast<std::uint16_t>(flags);
            weaponFlagsHigh=static_cast<std::uint8_t>(flags >> 16);
        }

        bool operator==(const SvPlayerState &) const = default;
        [[nodiscard]] std::array<std::uint16_t, 3> offhandWeaponSlots() const
        {
            return { offhandWeaponSlotA, offhandWeaponSlotB, offhandWeaponSlotC };
        }
        // Five runtime slots, distinct from three equipped rewards. Fragmented
        // storage fills existing alignment gaps; native world addresses stay fixed.
        [[nodiscard]] std::array<std::uint8_t, 5> rewardIds() const
        {
            return {rewardIdsLow[0], rewardIdsLow[1], rewardIdsHigh[0],
                rewardIdsHigh[1], rewardIdsHigh[2]};
        }
        [[nodiscard]] std::array<std::uint8_t, 5> rewardTargets() const
        {
            return {rewardTargetsLow[0], rewardTargetsLow[1], rewardTargetsHigh[0],
                rewardTargetsHigh[1], rewardTargetsHigh[2]};
        }
        void setRewardSlots(const std::array<std::uint8_t, 5> &ids,
            const std::array<std::uint8_t, 5> &targets)
        {
            rewardIdsLow = {ids[0], ids[1]};
            rewardIdsHigh = {ids[2], ids[3], ids[4]};
            rewardTargetsLow = {targets[0], targets[1]};
            rewardTargetsHigh = {targets[2], targets[3], targets[4]};
        }
    };

    // THE WIRE HAS NO TEAMLESS VALUE, AND SENDING ONE KILLS THE CLIENT.
    //
    // Free-for-all represents "no team" as SvTeam::None, which is 0, and that is
    // a sound SERVER-side choice -- onSameTeam is false whenever either side is
    // None, so everyone damages everyone with no special case. The client cannot
    // hold it. CODOL's presentation lookup sub_53F5F0 is:
    //
    //     v1 = 624 * clientNum + <table>;
    //     if (v1[62] == 1) return <tf slot>;
    //     if (v1[62] == 2) return <sc slot>;
    //     return 0;
    //
    // and its caller sub_59CC70 writes v4[251] through the result without
    // checking it. So a player whose team is anything but 1 or 2 makes every
    // OTHER client fault at +0x3EC the moment it has to present them.
    //
    // MEASURED with a hook on that lookup, both clients, one null return each:
    //     client A  index=1 kind=0        client B  index=0 kind=0
    // Each crashed resolving the other, and kind is the team. Four of the last
    // five cycles lost a client to it; it is free-for-all only, which is the
    // mode this project exists to ship.
    //
    // The faction already picks the model, so it is the honest presentation
    // team for a player who has none. Spectator (3) is folded in too -- it is
    // no more representable than 0 is.
    [[nodiscard]] SvTeam SV_PresentableTeam(
        SvTeam team,
        const std::optional<SvCharacterCustomization> &customization);

    // THIS IS THE agentState ELEMENT, not clientState, and the name is one section
    // out. CL_ParseSnapshot (sub_471E90) reads playerState, anims, ACTORS, entities,
    // clients -- and SV_WriteSnapshot's writeClients() sits in the ACTORS slot while
    // writeClientInfos() sits in the clients slot. The 24-entry 0x58 descriptor this
    // writer already cites (0x00DA6408) is agentState's.
    // re/demo-re/20-zm-actor-lifecycle.md sections 12.7 and 12.8.
    struct SvClientState
    {
        // The LIST ELEMENT INDEX, which is the agent SLOT -- five bits, 0..31.
        // agentstate.tsv has no +0x000 row because the slot is not a netfield: the
        // section framing carries it, and the decoder lands it at struct +0x00.
        std::uint32_t clientNum{};
        SvTeam team{ SvTeam::None };
        // agentState field 8, +0x00C, TEN BITS -- an index into this server's model
        // configstring band. THIS IS WHERE AN ET_ACTOR'S MODEL LIVES; entityState
        // carries none for eType 19 (12.5.1). Measured: retail delta-codes 31 slots
        // and each carries one here.
        std::uint16_t modelIndex{};

        // agentState field 20, +0x004, ELEVEN BITS -- the ACTOR'S ENTITY NUMBER.
        // sub_530C90 copies it to record+0x0C, and retail asserts it on every zombie
        // spawn frame (1016 / 177 / 967 in 12.9.1; 723..741 read live out of the
        // client's own agent array in 12.26). This server sent nothing here, so the
        // client kept the default row's 345 -- see SvAgentDefault* below.
        std::uint32_t entityNumber{};

        // agentState fields 13 and 14 -- the FIRST TWO ATTACHMENT MODELS,
        // +0x014 and +0x018, TEN bits each. sub_530C90 resolves four of these to
        // names at record+52+64*i; retail's zombie carries its HEAD in slot 0
        // (c_zom_ger_head beside c_zom_ger_body_blue, read live in 12.25).
        //
        // SLOT 1 IS SENT AS ZERO ON PURPOSE. Its default is 1317, and 12.9.1
        // measured retail asserting 0 there on every spawn frame -- leaving it
        // unsent would attach whatever 1317 names.
        std::uint16_t attachModelIndex0{};
        std::uint16_t attachModelIndex1{};

        // agentState field 15, +0x028, SIX bits -- attachment slot 1's TAG.
        // ITS DEFAULT IS 3, WHICH RESOLVES TO THE BONE NAME "j_elbow_le". Leaving
        // it unsent left a TAG WITH NO MODEL on the record and the head did not
        // render; retail sends 0 here on every zombie (measured live -- retail's
        // agent reads +0x028 = 0 while ours read the default 3). 12.29a.
        std::uint16_t attachTagIndex0{};
        std::uint16_t attachTagIndex1{};
        // CODREF(actor_head_attachment): native agent field12 (+0x34,32bits)
        // -> record+564 -> DObjModel+6 at 0x53004B. This is an attachment
        // collision mask, not a count. Preserve native template3 by default.
        std::uint32_t attachmentIgnoreCollision{3};

        // agentState fields 9 and 10 -- THE ANIMATION PAIR, +0x038 (12 bits) and
        // +0x03C (the -97 TIME codec). Measured on the capture: they always change
        // TOGETHER and both clear to 0 together, which is an anim index plus the
        // serverTime it started at. One zombie's life sets them 44 times.
        //
        // The rootMotion set (idx0/1/2/3/4/5/6) is NOT this: it fires in short
        // episodes, a few times per life, so it is a lunge and not the walk cycle.
        // re/demo-re/20-zm-actor-lifecycle.md 12.34.
        std::uint16_t animIndex{};
        std::uint32_t animStartTime{};

        bool operator==(const SvClientState &) const = default;
    };

    // CODREF(agentstate-wire): campaign AI is carried in the 24-field,
    // 0x58-byte state list immediately before packet entities.  The original
    // reconstruction called that list "clients" and emitted only field 21.
    // Keep the legacy DTO above for DM compatibility while giving campaign
    // actors their complete, separately owned record.
    struct SvAgentState
    {
        static constexpr std::size_t FieldCount = 24;
        static constexpr std::size_t ModelField = 8;
        static constexpr std::size_t AnimationField = 9;
        static constexpr std::size_t AnimationStartTimeField = 10;
        static constexpr std::size_t AttachmentField = 13;
        // AgentState +0x04 is the actor entity number. The native baseline's
        // value is 345; the first Wetwork frame replaces it with 222, 224,
        // 272... and the persistent squad uses 570..574 exactly.
        static constexpr std::size_t EntityNumField = 20;
        static constexpr std::size_t TeamField = 21;

        std::uint32_t agentNum{};
        // Values are indexed by the shipping descriptor table at out.exe
        // 0x00DA63E8. These defaults are the exact 88-byte native template at
        // 0x00DA9920, projected through that table. In particular, entity 345,
        // team 2, model 1266 and the all-ones attachment sentinel are real
        // baseline values; replacing them with zero changes the wire delta.
        std::array<std::uint32_t, FieldCount> fields{
            0, 0, 0, 0, 0, 0, 0, 0,
            1266, 0, 0, 1, 3, 1267, 1317, 3,
            0, 0, 0, 0, 345, 2, 0xFFFFFFFFu, 0,
        };

        bool operator==(const SvAgentState &) const = default;
    };

    struct SvClientInfoState
    {
        SvAbilityModifiers abilities;
        struct ExplicitAttachment
        {
            // CODDIFF(g_update_client_info): CODOL
            // CG_UpdateCharacterModelsFromClientInfo 0x0051BC80 consumes four
            // post-customization attachment pairs from the clientInfo wire.
            // These are configstring-table indexes, not XModel/tag pointers
            // and not the eleven character selection IDs.
            std::uint16_t modelConfigStringIndex{};
            std::uint8_t tagConfigStringIndex{};

            bool operator==(const ExplicitAttachment &) const = default;
        };

        std::uint32_t clientNum{};
        // clientState field 0, +0x140, eleven bits. The client copies this raw
        // entity number to characterInfo+0x394 for its linked living weapon.
        std::uint16_t livingWeaponEntityNum{};
        SvCharacterCustomization customization;
        // TODO(CODOL): recover the server producer equivalent to the
        // BO1/Ghosts G_UpdateClientInfo attachModel/attachTag projection.
        // Empty entries are authoritative absence; callers must not invent a
        // head model, tag_head, or a character-specific fallback here.
        std::array<ExplicitAttachment, 4> explicitAttachments{};
        // The mask this clientInfo publishes on fields 21..32; see SvWorldClientInput
        // for why it lives here and not on the customization it describes.
        std::array<std::uint32_t, SvCharacterRecordEntryCount> characterOptionMask{};
        // Legacy local bookkeeping only. Correction (2026-09-06): native
        // clientInfo+0xA4 is not network clientState+0xA4. Wire field 5 is
        // ability mask word 3, copied into ps+0x59C at 0x54C25A.
        std::uint32_t zombieBattery{};
        // CODREF(g_update_client_info): out.exe descriptor36 at0xDA8228 is
        // clientState+4,11bits;54BC8E copies it to characterInfo+7C. Only ZM
        // supplies this newly recovered field; zero preserves legacy MP wire.
        std::uint32_t zombieScoreboardTeam{};

        bool operator==(const SvClientInfoState &) const = default;
    };

    struct SvEntityState
    {
        // CODDIFF(sv_write_snapshot_to_client): this flattened source record
        // selects recovered eType-owned fields for serialization. It is not
        // the native CODOL entityState_s union or its in-memory layout.
        std::uint32_t number{};
        std::uint8_t eType{};
        std::uint8_t clientNum{};
        std::uint32_t eFlags{};
        std::array<float, 3> origin{};
        std::array<float, 3> angles{};
        std::uint32_t eventParm{};
        std::uint16_t otherEntityNum{};
        std::uint8_t impactSurfaceType{};
        std::uint8_t impactFlags{};
        // CODOL entityState_s +0x5C is an eType-owned union: ET_PLAYER uses
        // movementDir while ET_SCRIPTMOVER uses the model configstring index.
        std::int32_t movementDir{};
        // CODOL ET_PLAYER field 39 owns entityState_s +0x54. The client copies
        // this value into DObj_s::scale while building the world player model.
        float playerSizeScale{};
        std::uint16_t modelIndex{};
        // ET_SCRIPTMOVER +0x60, descriptor 28: named animation's CCS type-18 key.
        // Occupies the old alignment gap; this record's size must not grow.
        std::uint16_t scriptMoverAnimationIndex{};
        // THREE FIELDS EVERY RETAIL ET_SCRIPTMOVER CARRIES AND THIS SERVER SENT
        // ZERO FOR. Measured across the dm demo: field 25 (+0xE4, 8 bits) reads
        // 255 on 2377 of 2390 assertions and field 27 (+0x58, 11 bits) reads
        // 2047 on all 2377 -- 0xFF and 0x7FF, both all-ones, which is what a
        // "none" sentinel looks like. A zero in their place is not a smaller
        // value, it is index 0 of whatever they select.
        //
        // Named by OFFSET because nothing has established what they mean, and
        // section 120 is the record of what inventing a name for a field costs.
        // ET_MISSILE uses the same +58 union word as its launch time. The
        // generic name allows both owners without growing this pinned record.
        std::uint32_t lerpData0058{ 2047 };
        std::uint32_t scriptMoverField00E4{ 255 };
        // Field 47 (+0x98, 5 bits) reads 7 on the demo's podium figures.
        std::uint32_t scriptMoverField0098{};
        // THE `*N` BRUSH MODEL INDEX ON AN ET_SCRIPTMOVER. Field 26, +0x09C, 10
        // bits -- a DIFFERENT field from `modelIndex`, which this eType writes
        // at field 19 / +0x05C as the XModel configstring index.
        //
        // Two fields, two offsets, and a brush model uses only this one: all 238
        // of factory's carry +0x05C == 0 in the shipped const-baseline table
        // (re/demo-re/16-const-baselines.md). The netfield table calls field 26
        // `clientNum`, which is an MW3 name transfer and is wrong here -- the
        // authentic values are 1..238 contiguous, ascending with entity number.
        std::uint16_t scriptMoverBrushModelIndex{};
        // Field 21 (+0x70, codec -7). Retail's podium figures carry 1 and this
        // demo shows no other value anywhere. Named by OFFSET: the netfield
        // table has no name for it either, and 120 is the record of what
        // inventing one costs.
        std::int32_t scriptMoverField0070{};
        // ET_SCRIPTMOVER +0x6C, descriptor 20: absolute animation start time.
        // ET_EVENTS uses this source-side word to hold its +0x60 union payload;
        // the eType-specific writers map it to the appropriate native offset.
        // Reuses the old subject-plus-padding slot to preserve this record's size.
        std::uint32_t scriptMoverAnimationStartTime{};
        // Shared model scale at +54 for movers, corpses and missiles.
        // The zero default is the wire baseline; production models set a
        // positive scale explicitly (ET_SCRIPTMOVER descriptor 46).
        float modelScale{};
        std::uint8_t positionTrajectoryType{};
        // THE PODIUM FIGURE'S SUBJECT: clientNum + 1, or 0 for "nobody" (section
        // 124). Entity field 49, off 0x64, 7 bits. It tells the client WHOSE
        // character to build onto the figure, and it is what makes the three
        // podium models differ while all three share one base model index.
        // Measured exactly against the demo's own roster on the same frame:
        // L 6 1 -> 7, L 3 2 -> 4, L 1 3 -> 2.
        //
        // 0x64 is `offhandWeaponAssetIndex` on ET_PLAYER. entityState_s is one
        // struct and each eType's table reads its own meaning out of the same
        // bytes, which is why this is a separate member and not a reuse of that
        // one -- nothing should be able to put a weapon index on a podium.
        std::uint8_t podiumClientNumPlusOne{};
        std::uint32_t positionTrajectoryTime{};
        std::uint32_t positionTrajectoryDuration{};
        std::array<float, 3> positionTrajectoryDelta{};
        std::uint8_t angleTrajectoryType{};
        std::uint32_t angleTrajectoryTime{};
        std::uint32_t angleTrajectoryDuration{};
        std::array<float, 3> angleTrajectoryDelta{};
        // ONE MEMBER, TWO ET_EVENTS FIELDS, CHOSEN BY eType.
        //
        //   obituary      -> field 13, entityState_s +0x88, 11 bits.  This is
        //                    the offset the netfield table itself calls
        //                    `groundEntityNum`, and CG_Obituary (out.exe
        //                    0x00531080) reads the KILLER out of it:
        //                    `*(es + 136)`, clamped to 18, 2046 for nobody.
        //   bullet impact -> field 23, entityState_s +0x8C, codec -96, the HIT
        //                    entity. Historic use, and the misnomer.
        //
        // IT DOES NOT GET ITS OWN MEMBER, and that is not a style choice:
        // SvEntityState is embedded in the address-keyed WorldClientState, whose
        // size is pinned by a static_assert further down because growing it once
        // broke the death animation (section 184h). Adding a field here fails
        // that assert, and the assert is right.
        std::uint32_t groundEntityNum{};
        // Raw CODOL ET_PLAYER field 35 / entityState_s +0xA0. Kept opaque
        // until its client presentation consumers are fully named.
        // CODDIFF(1649370): TWENTY-EIGHT bits, not 3.3.3.3's thirteen. Codec -55's
        // four present-bit groups reach bit 27 (2<<0, 4<<2, 11<<6, 5<<17, then single
        // bits at 22..27), so the value needs 32 bits to hold and 0x0FFFFFFF to bound.
        // The codec, the field index 37 and the offset 0xA4 were all ported; the TYPE
        // and its bounds were left at 3.3.3.3's two-group 13-bit shape.
        std::uint32_t unk00A0{};
        std::uint32_t solid{};
        std::uint8_t eventSequence{};
        std::array<SvEntityEvent, 4> events{};
        std::uint16_t weaponAssetIndex{};
        // CODOL entityState +0xD2. This is not an unconditional alias of
        // +0xD0: BG_PlayerToEntity_SetMisc 0x004131A0 selects playerState
        // +0x344 for the native WeaponDef-type-3 branch.
        std::uint16_t presentationWeaponAssetIndex{};
        // CODDIFF(bg_player_to_entity_set_misc): CODOL +0x60 is the
        // state-gated offhand weapon selected during weapon states 16..20,
        // not BO1/Ghosts' independent stowed weapon slot.
        std::uint16_t offhandWeaponAssetIndex{};
        // CODDIFF(bg_update_player_dobj): CODOL +0x64 carries the one-based
        // mp/coKnifeStatsTable.csv row selected at playerState +0x33C. The
        // client copies it to characterInfo +0x328 for knife model/timing
        // overrides. It is not a WeaponDef or XModel asset index.
        std::uint16_t coKnifeStatsIndex{};
        // Raw ET_PLAYER field 21 / entityState_s +0xE0. Only byte +0xE2 has a
        // confirmed DObj dirty consumer, so the full dword remains opaque.
        std::uint32_t unk00E0{};
        std::uint16_t legsAnim{};
        std::uint16_t torsoAnim{};
        // ET_PLAYER index 24, entityState +0x7C, SEVEN bits. A real server writes it on
        // every player: exactly 100 at each spawn, then values across 1..127 as the match
        // runs (measured over 600 s of the retail dm capture, 1269 assertions). A field
        // that starts at 100 and moves is a PERCENTAGE, and the playerState this build
        // sends already carries a moveSpeedScaleMultiplier -- so this is very likely its
        // entity-side projection, which is what a client needs to animate a player it is
        // not predicting. This server never sent it, so every remote player arrived with
        // the zero baseline.
        //
        // NOT a confirmed name: the consumer has not been read. It is carried through
        // from the native entity state rather than synthesised, so whatever the engine
        // means by it is what goes on the wire.
        std::uint8_t time2{};
        // CODREF(1649370 4EAAD0/523910): mover +EC low word is parent+1,
        // byte +EE indexes the tag-name band at 12248. Reuse tail padding.
        std::uint8_t scriptMoverTagIndex{};
        std::uint16_t scriptMoverParentNumPlusOne{};

        // ---- ET_ACTOR (eType 19), table 0x00DA5DE8, 63 fields ----
        //
        // EVERY ONE OF THESE IS A SEPARATE MEMBER RATHER THAN A REUSE, for the
        // reason podiumClientNumPlusOne already records: entityState_s is ONE
        // struct and each eType's table reads its own meaning out of the same
        // bytes. +0x08C is `loopSound` here and the ground entity on a corpse;
        // +0x0AC is 24 bits of something here and `solid` on a scriptmover.
        // Sharing a member would let one eType's value land on another's wire.
        //
        // NAMED BY OFFSET wherever nothing has established a meaning. Section
        // 120 is this project's record of what inventing a field name costs.
        //
        // NONE OF THESE CARRIES A NON-ZERO DEFAULT, deliberately. A non-zero
        // default lands in wireZeroBaseline() too, compares equal, and is then
        // never sent -- the exact bug that cost the scriptmover sentinels their
        // first frame. spawnZombieActor sets them explicitly instead.
        //
        // Field 30, +0x054, codec 0 -- a FLOAT. Every living actor read exactly
        // 1.0 across 5,592 live samples over 20 s (section 10); demoq prints it
        // as a small int because codec 0 is decoded raw, which is the
        // representation gap section 10 warns about. It is NOT actor health.
        float actorField0054{};
        // Field 11, +0x058, 32 bits. A PACKED ANIMATION-STATE WORD, and the
        // model-selector hypothesis was tested and REFUTED (section 12.2): at
        // spawn always 0xFF0003xx/0xFF0004xx with a low byte 0..25, later
        // 0x000N0000 with bits 16..23 running 1..13. The layout changes over the
        // life. Unmeasured -- see SvActorSendUnmeasuredSpawnWords.
        std::uint32_t actorField0058{};
        // Field 12, +0x05C, 32 bits. ONE distinct value in the whole census --
        // 0x00FFFFFF on all 51 asserts, and 0x00FFFFFF live. An all-ones
        // sentinel, and a zero here is index 0 of whatever it selects.
        //
        // NOT the xmodel slot. That is +0x05C 10-bit on ET_SCRIPTMOVER; on this
        // eType the same offset is 32 bits and pinned. See actorField009C.
        std::uint32_t actorField005C{};
        // Field 39, +0x084, 11 bits. 2047 on all 51 asserts -- all-ones "none".
        std::uint32_t actorAttackerEntityNum{};
        // Field 10, +0x08C, codec -96. 2046 or 2047; 2046 is codec -96's own
        // one-bit sentinel, which is what writeEntityGround emits for
        // EntityNumWorld. Same codec, same shape, different field.
        std::uint32_t actorLoopSound{};
        // THE APPEARANCE INDEX. Field 29, +0x09C, 10 bits, and the netfield
        // table's name for it -- `clientNum` -- is an unmeasured MW3 transfer
        // that is wrong here, exactly as it was wrong for the `*N` brush model
        // index at this same offset on ET_SCRIPTMOVER (see
        // scriptMoverBrushModelIndex, which renders 238 of factory's doors).
        //
        // MEASURED (re/demo-re/20-zm-actor-lifecycle.md section 12.4): written
        // ONCE on the spawn frame and never again across 367 asserting frames;
        // 13 distinct values 1..409 over the capture. Write-once, per-life
        // constant, 10 bits against a 1024-entry model band. 409 is not a client
        // number -- no zm match has 410 players.
        //
        // NOT PROVEN to select a model. It is the strongest candidate on the
        // table for an actor that validates and does not draw, and it is a
        // one-cycle test.
        //
        // THIS IS THIS SERVER'S BAND INDEX, resolved from a model NAME by
        // zmspawnactor's ModelResolver. Never the demo's literal 287: the client
        // rebuilds its own configstring band at map load, and sending a capture's
        // index is the bug that cost this project three sessions on the doors.
        std::uint16_t actorField009C{};
        // THE ACTOR'S MODEL, and it does NOT go on the entityState wire -- eType 19
        // has no model field at all. It is carried here so the snapshot assembly can
        // build this actor's agentState element, where field 8 / +0x00C is the model.
        // Resolved from a model NAME into this server's own band by zmspawnactor.
        std::uint16_t actorModelIndex{};

        // The actor's HEAD, agentState field 13 (+0x014). Retail pairs one with
        // every body -- c_zom_ger_head beside c_zom_ger_body_blue (12.25). Named by
        // the script and resolved at runtime like the body; never an invented index.
        std::uint16_t actorAttachModelIndex0{};
        // THE ANIM START TIME, and it is a GATE not a decoration: sub_5242D0
        // does `if (!start) index = 0`, so an index sent without a start time is
        // discarded and nothing animates. Stamped at spawn.
        std::uint32_t actorAnimStartTime{};
        // THE ANIMATION THIS ACTOR IS PLAYING, resolved by NAME out of the engine's own
        // band -- never a literal. Zero means "the default", which the agent writer
        // fills in with SvActorAnimIndex. The stepper overrides it for the length of a
        // barrier vault and puts it back afterwards.
        std::uint16_t actorAnimIndex{};
        // WHERE THIS ACTOR IS WALKING. The spawner's own `node_pathnode`, resolved
        // from MapEnts at parse time. Absent means STAND STILL -- 8 of factory's 69
        // spawners have no target, and inventing a destination for those is exactly
        // the straight-line-through-walls behaviour this replaces.
        std::array<float, 3> actorGoal{};
        bool actorHasGoal{};

        // lerp.pos.trDelta -- the actor's VELOCITY, ET_ACTOR fields 31/32/33 at
        // +0x024/028/02C, codec -80 (a raw long, no leading bit). Retail asserts all
        // three ~750 times across the capture while this server sent none.
        //
        // It is NOT how retail moves a zombie -- position is streamed every snapshot
        // (12.33) -- so this is here because the client has to learn a locomotion
        // state from somewhere and the anim index is 0 on every moving retail zombie.
        std::array<float, 3> actorVelocity{};
        // THE AGENT SLOT, 0..31, and it must equal this entity's +0x058 low byte.
        // sub_530BB0 indexes the client's 684-byte record array by that byte and
        // sub_530C90 stamps the same record from the agent element -- so if the two
        // disagree the entity points at a record nobody filled and nothing draws.
        // MEASURED four ways in 12.8.1.
        std::uint8_t actorAgentSlot{};
        // Field 28, +0x0AC, 24 bits. Nine distinct values, none of them a
        // sentinel. The table names it `eventSequence` at `exact` confidence,
        // but the SAME offset is `solid` on a scriptmover and the const
        // baselines settled that one the other way -- so it is carried by offset
        // and left out of the existing uint8 eventSequence member, which is far
        // too narrow to hold 6816015 anyway. Unmeasured.
        std::uint32_t actorField00AC{};
        // Field 5, +0x0B4, codec -75. The counter that sits with the four event
        // slots at +0x0B8/+0x0C0/+0x0C8/+0x0D0 (section 4). Opens at 1 and runs
        // to 30. ONE BYTE: codec -75's fallback arm is a byte XOR, so only
        // 0..255 is expressible on the wire at all.
        std::uint8_t actorField00B4{};
        // Field 53, +0x0E8, 32 bits. 1 on all 51 asserts.
        std::uint32_t actorPartBits0{};

        bool operator==(const SvEntityState &) const = default;
    };

    // THE CLIENT'S BASELINE FOR AN ENTITY IT HAS NEVER SEEN IS A ZEROED STRUCT,
    // SO THE ONE A WRITER COMPARES AGAINST HAS TO BE ZERO TOO.
    //
    // `SvEntityState{}` is NOT zero. Two members carry a non-zero default member
    // initialiser -- lerpData0058 = 2047 and scriptMoverField00E4 = 255,
    // the two all-ones "none" sentinels every retail ET_SCRIPTMOVER asserts --
    // and every writer opens with `const SvEntityState zeroBaseline{}`. A field
    // is written only when it DIFFERS from that baseline, so those two compared
    // equal, were skipped, and the client decoded 0 for both: entity 0 and
    // index 0 of whatever they select, not "none".
    //
    // The defaults were added so that every scriptmover would carry the
    // sentinels, and they cancelled themselves out. Measured after the fact in
    // this server's own recorded demo (HANDOFF 140): retail's podium figures
    // carry `clientLinkInfo 255` and `entToTakeMarksFrom 2047` on their first
    // frame and ours carried neither, three sections after the change that was
    // supposed to send them.
    //
    // Anything with a non-zero default belongs in this function, and the audit
    // that keeps it honest is Tools/olfinal/audit-wire-zero-baseline.py.
    [[nodiscard]] inline SvEntityState wireZeroBaseline() noexcept
    {
        SvEntityState baseline{};
        baseline.lerpData0058 = 0;
        baseline.scriptMoverField00E4 = 0;
        return baseline;
    }

    // OLMOD(game-entity-owner): source transaction owner; this is not the
    // native CODOL gentity_s layout.
    struct SvGameEntity
    {
        SvEntityState networkState;
        SvNativeEntityState nativeEntityState;
        std::uint32_t clientNum{};
        // Source-level collision owner for the recovered capsule/brush subsets
        // of SV_LinkEntity. DObjs and the native CM tree remain separate stages.
        std::optional<std::uint32_t> ownerEntityNum;
        std::array<float, 3> currentOrigin{};
        std::array<float, 3> currentAngles{};
        TraceBounds collisionBounds;
        SvCollisionShape collisionShape{ SvCollisionShape::Capsule };
        std::optional<std::uint32_t> brushModelClipHandle;
        std::string scriptGameObjectName;
        std::string mapClassName;
        std::string mapTargetName;
        std::string mapDestructibleType;
        std::string scriptModelName;
        bool mapModeEligible{ true };
        std::uint32_t numTouch{};
        std::array<std::uint32_t, 32> touchEntities{};
        SvClientImpactBatch clientImpactBatch;
        SvClientImpactCallbackBatch clientImpactCallbackBatch;
        SvClientImpactScriptNotificationBatch clientImpactScriptNotificationBatch;
        std::uint32_t collisionContents{};
        // CODDIFF(sv_add_entities_clients_can_see): this source lifecycle flag
        // currently folds native in-use and not-SVF_NOCLIENT publication. It
        // is not a recovered CODOL gentity_s field and is not an eType-based
        // visibility rule. See shouldArchiveWorldEntity for the exit boundary.
        bool gameplayActive{};
        bool collisionLinked{};
        std::uint32_t lastThinkServerTime{};
        std::uint64_t thinkSequence{};

        struct ScriptNotification
        {
            std::uint16_t weaponAssetIndex{};
            std::string weaponName;

            bool operator==(const ScriptNotification &) const = default;
        };
        std::vector<ScriptNotification> pendingScriptNotifications;
        std::vector<SvPlayerDamagePayload> pendingPlayerDamagePayloads;
        std::vector<SvEntityDamagePayload> pendingEntityDamagePayloads;
        // Extending the vector element keeps this embedded owner's size fixed.
        using PendingEntitySpawn = std::variant<SvBulletImpactEvent, SvMissileSpawnRequest>;
        std::vector<PendingEntitySpawn> pendingEntitySpawns;
        std::optional<SvBulletExecutionStatus> lastBulletExecutionStatus;
        std::vector<SvDamageableEntityView> damageableEntityViews;

        bool operator==(const SvGameEntity &) const = default;
    };

    struct SvBrushModelMotion
    {
        SvEntityHandle handle;
        SvNativeTrajectory position;
        SvNativeTrajectory angles;
        std::uint32_t flags{};
    };

    struct SvBrushModelEntityDefinition
    {
        // Position in the map's own entity list; see SvMapBrushModelSpawn::mapOrdinal.
        // Zero is a legal ordinal, so an all-default definition is indistinguishable from
        // the first entity -- callers that care must supply it.
        std::size_t mapOrdinal{};
        // Retail's own entity number, walked out of the map entity string. See
        // SV_AssignMapEntityNumbers. Zero when the map was not walked.
        std::uint32_t walkEntityNum{};
        std::array<float, 3> origin{};
        std::array<float, 3> angles{};
        SvBrushModelCollision collision;
        std::string scriptGameObjectName;
        std::string targetName;
        std::string destructibleType;
        bool mapModeEligible{ true };
        bool gameplayActive{ true };

        bool operator==(const SvBrushModelEntityDefinition &) const = default;
    };

    struct SvScriptModelEntityDefinition
    {
        // Position in the map's own entity list; see SvMapBrushModelSpawn::mapOrdinal.
        // Zero is a legal ordinal, so an all-default definition is indistinguishable from
        // the first entity -- callers that care must supply it.
        std::size_t mapOrdinal{};
        // Retail's own entity number, walked out of the map entity string. See
        // SV_AssignMapEntityNumbers. Zero when the map was not walked.
        std::uint32_t walkEntityNum{};
        std::array<float, 3> origin{};
        std::array<float, 3> angles{};
        std::uint16_t modelIndex{};
        std::string modelName;
        float scale{ 1.0f };
        std::string scriptGameObjectName;
        std::string targetName;
        std::string destructibleType;
        bool mapModeEligible{ true };
        bool gameplayActive{ true };

        std::string noteworthy;

        bool operator==(const SvScriptModelEntityDefinition &) const = default;
    };

    struct SvScriptModelDamageOwnerDefinition
    {
        std::size_t scriptModelIndex{};
        SvEntityDamageState state;
        SvEntityDamageHandler handler;
    };

    struct SvWorldSpawnPoint
    {
        std::array<float, 3> origin{};
        std::array<float, 3> angles{};
        SvTeam team{ SvTeam::None };
        // The zm spawner's own navigation goal, when the map gives it one.
        // Empty for every non-zm caller, which is why it is defaulted rather
        // than required.
        std::array<float, 3> goalOrigin{};
        bool hasGoalOrigin{};

        bool operator==(const SvWorldSpawnPoint &) const = default;
    };

    struct SvBrushModelActivationStatus
    {
        std::size_t total{};
        std::size_t tagged{};
        std::size_t active{};

        bool operator==(const SvBrushModelActivationStatus &) const = default;
    };

    // THE TOLERANCE RETAIL USES TO DECIDE THE CLIENT'S PREDICTION IS RIGHT.
    // out.exe's own writer compares the SQUARED distance against 0.0099999998,
    // i.e. a tenth of a unit.
    constexpr float SvPredictedOriginToleranceSquared = 0.01f;

    // THE CLIENT'S OWN PREDICTED RESULT, WHICH IT SENDS BACK IN EVERY MOVE
    // PACKET AND WHICH THIS SERVER PARSED AND THREW AWAY UNTIL NOW.
    //
    // The five longs that follow the usercmds in a clc move packet are these
    // four values plus one that has only ever been observed as zero. They were
    // read into ClientPredictedState, stored on the slot, printed to a
    // three-shot sample log and never used. The sample log is what identified
    // them: `predicted=1140621312,1095761920,3277423512,1354,0` decodes to the
    // floats 505.0, 13.0, -217.5 and the integer 1354, and this server's own
    // capsule log for the same client reads
    // `eType=1 origin=505.0,13.0,-217.5`. Three floats and a command time.
    //
    // CODREF(msg_write_delta_playerstate): out.exe's writer sub_678740 reads
    // exactly these -- ctx->[16] + 1760/1764/1768 against the playerState
    // origin it is about to send, and +1772 against its commandTime.
    struct SvClientPrediction
    {
        std::array<float, 3> origin{};
        std::uint32_t commandTime{};
        bool valid{};

        bool operator==(const SvClientPrediction &) const = default;
    };

    // Native PM_UpdateHoldBreath owns these at playerState +0x298/+0x29C.
    // Keep them beside SvPlayerState because WorldClientState's size is an
    // address-sensitive engine contract.
    struct SvHoldBreathState
    {
        std::uint32_t clientNum{};
        float swayScale{ 1.0f };
        std::uint32_t timer{};

        bool operator==(const SvHoldBreathState &) const = default;
    };

    enum class SvAnimationCommandType : std::uint8_t
    {
        SetGoalWeight = 1,
        ClearTree = 11,
    };

    // CODREF(cl_parse_packet_anims): out.exe 0x471D80 reads a separate
    // snapshot command list after playerstate. 0x671700 expands each wire
    // selector into this semantic record and 0x527B40 applies it to the
    // entity's DObj/XAnim tree. These are source DTOs, not the native 52-byte
    // ring layout.
    struct SvAnimationCommand
    {
        SvAnimationCommandType type{ SvAnimationCommandType::SetGoalWeight };
        std::uint32_t time{};
        std::uint32_t entityNum{};
        std::uint16_t animationKey{};
        float weight{ 1.0f };
        float rate{ 1.0f };
        float blendTime{ 0.2f };
        std::uint8_t flags{ 1 };

        bool operator==(const SvAnimationCommand &) const = default;
    };

    struct SvSnapshotFrame
    {
        // OLMOD(snapshot-frame-owner): immutable source aggregate admitted by
        // SV_ValidateSnapshotFrame before a per-client wire message is built.
        std::uint32_t serverTime{};
        // Retail's ACTORS list is an agent namespace on zm maps. Player rows live
        // in the separate CLIENTS list and must not consume any of its 32 slots.
        // Other modes retain the legacy player rows until their team field has a
        // separately recovered wire owner.
        bool emitPlayersInActorsSection{ SvEmitPlayersInActorsSection };
        // THE ACTORS SECTION'S NON-PLAYER ELEMENTS, kept OUT of `clients`.
        //
        // `clients` is the server's per-player bookkeeping AND the wire list for the
        // ACTORS section, and it cannot be both once agents exist: five consumers
        // assume one entry per player -- the sorted-unique bound, the
        // playerStates.size() == clients.size() check, the clientInfo lookup, the
        // index walk, and the ET_PLAYER entity-to-client resolve. Putting agents in
        // there rejected EVERY frame (`frameReject=player_client_count`, snapshots=0,
        // client stuck on the map-load screen).
        //
        // So agents live here and are merged into the section at write time, after the
        // players and at higher slots, which keeps the list ascending as the framing
        // requires. re/demo-re/20-zm-actor-lifecycle.md 12.7-12.8.
        std::vector<SvClientState> agents;
        std::uint8_t flags{};
        std::array<float, 3> mapCenter{};
        std::vector<SvPlayerState> playerStates;
        std::vector<SvAnimationCommand> animationCommands;
        std::vector<SvClientState> clients;
        std::vector<SvEntityState> entities;
        std::vector<SvClientInfoState> clientInfos;
        std::vector<SvGlassPieceStateRecord> glassPieces;
        // Set when this map's static entities were published on RETAIL'S entity
        // numbers -- i.e. the map has a shipped const-baseline table and the
        // world used it. It is the precondition for SnapshotUseEntityBaselinesFlag:
        // bit 0x10 tells the client to resolve a new entity against
        // cl.entityBaselines[number], which is only ever right when the numbers
        // agree with the table the client loaded at map load. Off on a map this
        // build has no table for, where the numbering is this server's own.
        bool useEntityBaselines{};
        // The table the client loaded at map load, so the entity writers delta against the
        // SAME records the client resolves against. Non-null exactly when
        // useEntityBaselines is set: the flag and the delta base are ONE decision, and
        // setting the flag without moving the base is what made 237 correctly-numbered
        // doors XOR themselves to zero.
        const SvConstBaselineTable *constBaselines{};
        // Appended so existing positional frame fixtures retain their source
        // layout. Retail multiplayer leaves this empty; campaign fills it.
        std::vector<SvAgentState> campaignAgents;
        // PlayerState fields used only by mission-owned camera/link tracks.
        // Keep them out of SvPlayerState: that type lives in WorldClientState,
        // whose node size is pinned because the retained engine keys native
        // player state accessors to addresses inside the node.
        struct PlayerViewLinkState
        {
            std::uint32_t clientNum{};
            std::array<float, 2> clampBase{};
            std::array<float, 2> clampRange{};
            std::array<float, 3> linkAngles{};
            std::uint8_t linkFlags{};

            bool operator==(const PlayerViewLinkState &) const = default;
        };
        std::vector<PlayerViewLinkState> playerViewLinkStates;
        std::vector<SvHoldBreathState> playerHoldBreathStates;
        // Immutable per-recipient T15 state; no native/client-node layout change.
        std::vector<SvClientDamageNumbers> playerDamageNumbers;
        std::vector<SvClientZombieInjuries> playerZombieInjuries;
        // OLMOD(factory_view_fx): immutable recipient metadata, never a wire
        // field or native client-node member. Filter both sides of each delta.
        std::map<std::uint16_t,std::uint32_t> viewFxRecipients;

        // Recipient identity stays in playerStates. Only its serialized view
        // follows the subject; never copy a survivor into the dead world owner.
        std::map<std::uint32_t, std::uint32_t> zombieSpectatorTargets;
        // Recipient-only treatment presentation; never change the held inventory.
        std::map<std::uint32_t, std::uint32_t> zombieReviverGenerations;
        std::map<std::uint32_t, std::uint32_t> factoryTravelerGenerations;

        bool operator==(const SvSnapshotFrame &) const = default;
    };

    [[nodiscard]] std::optional<SvPlayerState> SV_PlayerSnapshotView(
        const SvSnapshotFrame &frame, std::uint32_t recipient);

    [[nodiscard]] bool SV_WritePacketEntities(
        MsgWriter &message,
        const std::vector<SvEntityState> &entities,
        const std::vector<SvEntityState> *baseline = nullptr,
        std::array<float, 3> mapCenter = {},
        std::uint32_t serverTime = 0,
        // The map's shipped baselines, when the snapshot carries flag 0x10. A NEW entity
        // whose number is in this table is delta'd against its record instead of against a
        // zeroed struct, which is what the client on the other end will do with it.
        const SvConstBaselineTable *constBaselines = nullptr);
    [[nodiscard]] bool SV_WriteGlassChanges(
        MsgWriter &message,
        const std::vector<SvGlassPieceStateRecord> &glassPieces,
        const std::vector<SvGlassPieceStateRecord> *baseline = nullptr);
    [[nodiscard]] bool SV_WriteAnimationCommands(
        MsgWriter &message,
        const std::vector<SvAnimationCommand> &commands,
        const std::vector<SvAnimationCommand> *baseline = nullptr,
        std::uint32_t serverTime = 0);
    [[nodiscard]] bool SV_WriteAgentStates(
        MsgWriter &message,
        const std::vector<SvAgentState> &agents,
        const std::vector<SvAgentState> *baseline = nullptr,
        std::uint32_t serverTime = 0);

    struct SvWorldClientInput
    {
        // OLMOD(world-frame-input): control-plane lifecycle snapshot consumed
        // at begin/end frame; no corresponding native CODOL aggregate exists.
        std::uint32_t clientNum{};
        std::optional<UserCmd> spawnUserCmdBaseline;
        ClientGameplayState gameplayState{ ClientGameplayState::Inactive };
        SvTeam team{ SvTeam::None };
        std::uint32_t loadoutSequence{};
        std::uint32_t spawnSequence{};
        std::optional<SvResolvedLoadout> resolvedLoadout;
        std::optional<SvCharacterCustomization> characterCustomization;
        // THE OUTFIT AS THE CLIENT READS IT: netfields 21..32, a 384-BIT SELECTION
        // MASK over the character definition's own option list. Bit i selects option
        // i -- sub_80E600 tests `[request+0x10 + (i>>5)*4] & (1<<(i&31))` for every i
        // below charDef+36 and renders charDef+40's u16 at that index. Section 184.
        //
        // IT IS NOT A MEMBER OF SvCharacterCustomization, AND THAT IS A MEASUREMENT,
        // NOT A PREFERENCE. It was, for one build. The customization is held BY VALUE
        // inside WorldClientState -- the std::unordered_map node that also holds the
        // address-keyed native playerState -- and the extra 48 bytes cost living
        // players their leg animation on 5.3% of sampled frames (0 of 5830 on the
        // build before it), so every death came back durationMs=-1 and T-posed.
        // Reverting the same commit restored it: durationMs 1816 and 2983. Both
        // directions measured. Section 184h.
        //
        // So it travels on the TRANSIENT input and lands on the WIRE struct, neither
        // of which the engine keys to an address.
        std::array<std::uint32_t, SvCharacterRecordEntryCount> characterOptionMask{};
        // OLMOD(factory-class-confirmation): transient policy, not native layout.
        bool factoryClassSelection{};
    };

    struct SvGameClientCommandState
    {
        UserCmd currentUserCmd;
        std::optional<UserCmd> oldUserCmd;
        std::uint32_t lastCmdTime{};

        bool operator==(const SvGameClientCommandState &) const = default;
    };

    struct SvPlayerDamageFeedbackState
    {
        std::uint32_t damageBlood{};
        std::optional<std::array<float, 3>> damageFrom;
        std::optional<std::uint32_t> damageTime;

        bool operator==(const SvPlayerDamageFeedbackState &) const = default;
    };

    struct SvPlayerDeathState
    {
        SvPlayerDamagePayload damage;
        std::int32_t deathAnimationDuration{};
        std::uint32_t serverTime{};
        // The weapon the player was holding when they died. The native
        // conversion zeroes it one frame later - measured going 354 -> 0 at
        // msDead=50 - and a body with no weapon is not what a real one looks
        // like, so it is captured here and re-applied while the body is held.
        std::uint16_t weaponAssetIndex{};

        bool operator==(const SvPlayerDeathState &) const = default;
    };

    struct SvPredictableEventStatus
    {
        std::uint32_t commandTime{};
        std::int32_t oldSequence{};
        std::int32_t currentSequence{};
        std::uint32_t count{};
        std::array<SvNativePredictableEvent, 4> events{};
        SvClientEventResult handlerResult{ SvClientEventResult::Applied };

        bool operator==(const SvPredictableEventStatus &) const = default;
    };

    struct SvEntityDamageEvent
    {
        SvEntityDamagePayload damage;
        std::int32_t remainingHealth{};
        std::int32_t previousHealth{};

        bool operator==(const SvEntityDamageEvent &) const = default;
    };

    // OLMOD(game-client-owner): source command candidate and long-lived native
    // FALL DAMAGE ARRIVES AS AN EVENT; THE ENGINE ALREADY COMPUTES IT.
    //
    // This server drives the retained PmoveSingle, so out.exe's own PM_CrashLand
    // -- 0x004166C0, the single caller is PM_GroundTrace's landing branch at
    // 0x004171CF -- runs on every landing and raises EV_LANDING_PAIN itself.
    // Nothing here recomputes fall height, gravity or a damage curve: doing so
    // would be a second, divergent implementation of a function the process is
    // already executing correctly.
    //
    // 0x9E IS RE-DERIVED ON OLfinal, NOT CARRIED. out.exe's event-name table is
    // stored highest-index-first with EV_NONE last; indexing back from EV_NONE
    // reproduces all EIGHT event ids this project had already recovered by
    // other means (0x17 OFFHAND_END_NOTIFY, 0x1D RELOAD_START_NOTIFY, 0x1E
    // RELOAD_ADDAMMO, 0x23 WEAPON_SWITCH_STARTED, 0x36..0x39 the SV_FIRE
    // family), which is what makes the landing block trustworthy:
    //   0x9C EV_JUMP   0x9D EV_LANDING_HARD   0x9E EV_LANDING_PAIN   0x9F EV_MANTLE
    // EV_LANDING_HARD is the painless heavy landing and is deliberately NOT
    // damage.
    inline constexpr std::int32_t SvEventLandingPain = 0x9E;
    // THE KNOWN-LIVE CONTROL FOR THE ONE ABOVE. Every jump ends in a landing
    // and almost none of them hurt -- one retail dm match carries 96
    // EV_LANDING_HARD against 4 EV_LANDING_PAIN. So a cycle that logs no
    // landing of EITHER kind says the event never reached this server, while
    // one that logs hard landings and no painful ones says only that nobody
    // jumped off anything high enough. Without the control those two read
    // identically, and the second is by far the more likely.
    inline constexpr std::int32_t SvEventLandingHard = 0x9D;

    // AND THE PARAMETER IS NOT THE DAMAGE. It is a packed word, and reading it
    // as a plain number kills the player on any landing that hurts at all: the
    // damage sits at bit 5, so a 12-damage fall reads as 384 or more.
    //
    // PM_CrashLand builds it inline at 0x00416964..0x0041697E, and the four
    // instructions are the whole specification:
    //
    //   mov  eax, ecx        ; ecx = pm->groundTrace.surfaceFlags (pm+0x48,
    //   shr  eax, 0Ch        ;       which is groundTrace+0x10 -- the project's
    //   and  eax, 1          ;       own trace_t already puts surfaceFlags at
    //   shl  eax, 7          ;       +0x10, and sv_bullet_mp reads the surface
    //   or   eax, [ebp-4]    ;       type out of >>20 & 0x1F exactly like this)
    //   shl  eax, 5          ; [ebp-4] = the damage, from the curve helper at
    //   or   eax, esi        ; 0x00416590; esi = (surfaceFlags >> 20) & 0x1F
    //
    //   bits 0..4   surface type index, for the client's landing sound
    //   bits 5..11  THE DAMAGE
    //   bit  12     set when surfaceFlags & 0x1000 chose the soft-surface curve
    //
    // Seven bits is exactly enough because the curve helper's cap is a literal
    // 100 (0x64 at 0x004165C6), or 10 (0x0A at 0x004165A5) on the soft-surface
    // branch. EV_LANDING_HARD at 0x00416AB4 packs the same way -- an intensity
    // clamped to 24 shifted up by 5, over the same surface index -- which is
    // what says the layout is a convention and not a coincidence.
    //
    // Two suppressions live in the same tail and cost us nothing to honour,
    // because pmove applies them before the event exists: surfaceFlags & 0x2000
    // raises no event at all, and a surface type of 0 raises no event either.
    inline constexpr std::int32_t SvLandingPainDamageShift = 5;
    inline constexpr std::int32_t SvLandingPainDamageMask = 0x7F;

    // The damage PM_CrashLand decided, out of the event parameter it packed it
    // into. Pure, so the layout is testable without a pmove.
    [[nodiscard]] std::uint32_t SV_LandingPainDamage(std::int32_t eventParameter);

    // AND RETAIL TAKES ONE LESS THAN THAT OFF THE PLAYER. Measured, not
    // reasoned: Tools/demo-re/landing-pain.py pulls every EV_LANDING_PAIN out of
    // the recorder's own playerState ring and reads the STATS health either side
    // of it. Fifteen landings moved health at all, across a dm, a dom and a
    // zsurv demo, and all fifteen moved it by the packed damage MINUS ONE --
    // 34->33, 31->30, 25->24, down to 2->1. The 2->1 one is the load-bearing
    // sample: the player was on 71 health, not 100, so "he was really on 101"
    // cannot explain the gap.
    //
    // WHAT IT IS NOT. Neither PM_CrashLand's curve helper (0x00416590, which
    // truncates (h-min)/(max-min)*maxDamage) nor the alternate curve that can
    // overwrite it (0x0040B950, the same shape times a literal 100.0) adds one
    // anywhere, so the difference is on the applying side and not in the packing
    // this decodes. A multiplier a shade under 1 fits the same fifteen samples
    // -- the largest drop measured is 34, which is not enough to separate them
    // -- so this is written as the simpler rule that fits, and the corpus is
    // named so a bigger fall can settle it later.
    [[nodiscard]] std::uint32_t SV_FallDamageApplied(std::uint32_t packedDamage);

    // HEALTH REGEN, MEASURED OFF RETAIL RATHER THAN CHOSEN.
    //
    // Health does not travel as a netfield -- it rides the snapshot stats
    // section (ps_trailing T1) as an i16 -- so the curve is readable straight
    // off a retail capture with Tools/demo-re/health-timeline.py. Two demos
    // eighteen months and one gametype apart agree:
    //
    //   2021 dm  (the spec demo)   delay 5000 ms x11 (one 1600)  200 hp/s x13
    //   2020 war (independent)     delay 5000 ms x2  (one 5050)  200 hp/s x4
    //
    // The retail steps are +20 health per 100 ms frame, which is where the
    // per-second figure comes from; nothing here infers a model beyond those
    // two numbers. The rate is expressed in ABSOLUTE health per second and not
    // as a fraction of maxHealth: every measured life had maxHealth 100, so the
    // two models are indistinguishable in this corpus and the absolute reading
    // is the one that does not invent a dependency the evidence cannot support.
    inline constexpr std::uint32_t SvHealthRegenDelayMilliseconds = 5000;
    inline constexpr std::uint32_t SvHealthRegenHealthPerSecond = 200;

    // What regen needs to know per client, and it is deliberately NOT on
    // SvGameClient -- same reason noclipHoldUntil_ is not: that struct is
    // copied whole every think and its offset 0 is load-bearing for the native
    // pointer obfuscation, and growing it is already recorded as having broken
    // death-animation selection once (2026-08-24, the killcam fields).
    struct SvHealthRegenState
    {
        std::uint32_t lastDamageTime{};
        // Unsigned to match SvPlayerState::health exactly. Signed here made the
        // damage site's designated initialiser a narrowing conversion in a
        // braced-init-list, which is ill-formed, not merely a warning.
        std::uint32_t healthAtDamage{};

        bool operator==(const SvHealthRegenState &) const = default;
    };

    // Health at `serverTime` for a client last damaged at `state`, given the
    // measured delay and rate. Pure, so the curve is testable without a world:
    // returns the health the player should now have, never above maxHealth and
    // never below what they already have.
    [[nodiscard]] std::uint32_t SV_RegeneratedHealth(
        const SvHealthRegenState &state,
        std::uint32_t currentHealth,
        std::uint32_t maxHealth,
        std::uint32_t serverTime,
        std::uint32_t frameMilliseconds);

    // byte image owner; this is not the native CODOL gclient_s layout.
    struct SvGameClient
    {
        // THE NATIVE BUFFER GOES FIRST SO THAT NOTHING ELSE CAN MOVE IT.
        //
        // It used to sit AFTER playerState, which means every field added to
        // SvPlayerState changed its offset -- and therefore its address, since
        // these live in an unordered_map node. CODOL stores a function pointer
        // as key ^ function ^ THE PAIRED SLOT'S OWN ADDRESS (see
        // rebindNativePlayerStateAccessors), so an address that moves is not a
        // detail of layout, it is the thing the obfuscation is keyed to.
        //
        // 2026-08-24: four playerState members were added for the killcam and
        // the death animation stopped selecting -- durationMs went from 2250 to
        // -1, "no animation matched", and every death T-posed. The A/B is
        // recorded in the handoff: the same match on the previous build
        // animates. By elimination it is that commit -- the other three in the
        // range only run AFTER match completion, and the FIRST death of a match
        // failed too -- and the only part of it that runs before a death is
        // this struct getting bigger.
        //
        // Offset 0 cannot move. The static_assert below is what makes that a
        // rule rather than an accident of declaration order.
        SvNativePlayerState nativePlayerState;
        SvPlayerState playerState;
        // CODREF(client_spawn): the last life the spawn animation event was
        // fired for. The torso animation has no per-frame writer, so it must
        // be re-established once per life; see runServerSpawnAnimation.
        std::uint8_t spawnAnimationGeneration{};
        ClientGameplayState gameplayState{ ClientGameplayState::Inactive };
        SvTeam team{ SvTeam::None };
        std::uint32_t loadoutSequence{};
        std::uint32_t appliedSpawnSequence{};
        std::optional<SvResolvedLoadout> resolvedLoadout;
        std::optional<SvGameClientCommandState> commandState;
        SvWeaponMovementClientState weaponMovementState;
        SvWeaponAimState weaponAimState;
        SvPlayerDamageFeedbackState damageFeedbackState;
        std::optional<SvPlayerDeathState> deathState;
        std::optional<std::uint32_t> respawnTime;
        SvPredictableEventStatus predictableEventStatus;
        float currentAimSpreadScale{};
        bool spawnedThisFrame{};

        bool operator==(const SvGameClient &) const = default;
    };

    // ADDING A PLAYERSTATE FIELD MUST NOT MOVE THE NATIVE BUFFER. It is keyed
    // to its own address by CODOL's pointer obfuscation, and this fails the
    // BUILD rather than the death animation, which is how it failed last time.
    static_assert(offsetof(SvGameClient, nativePlayerState) == 0);

    // OLMOD(world-native-adapters): callbacks isolate native/shared primitives
    // from source candidates. Their signatures describe project transaction
    // boundaries, not recovered CODOL function ABIs.
    using SvSharedPmoveRunner = std::function<bool(
        SvNativePlayerState &nativePlayerState,
        const SvGameClientCommandState &commandState,
        const SvResolvedLoadout *resolvedLoadout,
        const SvGlassState &glassState,
        std::span<const SvCollisionEntity> collisionEntities,
        SvNativePmoveOutput &output)>;

    using SvWeaponMovementRunner = std::function<bool(
        const SvWeaponMovementFrameInput &input,
        SvWeaponMovementClientState &clientState,
        const SvResolvedLoadout *resolvedLoadout,
        SvNativeWeaponMovementOutput &output)>;

    using SvPlayerStateToEntityStateConverter = std::function<bool(
        SvNativePlayerState &nativePlayerState,
        SvNativeEntityState &nativeEntityState,
        SvNativeEntityStateProjection &projection)>;

    using SvDeathAnimationRunner = std::function<std::optional<std::int32_t>(
        SvNativePlayerState &nativePlayerState,
        std::uint32_t randomSeed,
        const SvDeathAnimationConditions &conditions)>;

    // The spawn event takes no conditions; it used to share the death typedef
    // and would have inherited the new argument for no reason.
    using SvSpawnAnimationRunner = std::function<std::optional<std::int32_t>(
        SvNativePlayerState &nativePlayerState,
        std::uint32_t randomSeed)>;

    using SvClientEventsHandler = std::function<SvClientEventResult(
        SvPlayerState &playerState,
        SvGameEntity &entity,
        // This is the staged native image. Grenade timer consumption must
        // commit or roll back with the same command as its projectile.
        SvNativePlayerState &nativePlayerState,
        const SvWeaponAimState &weaponAimState,
        float currentAimSpreadScale,
        std::uint32_t serverTime,
        SvGlassState &glassState,
        SvGlassDamageState &glassDamageState,
        const SvGlassMapMetadata &glassMetadata,
        std::span<const SvCollisionEntity> collisionEntities,
        std::span<const SvDamageablePlayerView> damageablePlayers,
        const SvResolvedLoadout *resolvedLoadout,
        std::span<const SvNativePredictableEvent> events)>;

    using SvPointTraceRunner = std::function<std::optional<TraceResult>(
        const SvPointTraceRequest &request,
        const SvGlassState &glassState,
        std::span<const SvCollisionEntity> collisionEntities)>;

    using SvRadiusDamageVisibilityRunner = std::function<std::optional<bool>(
        const SvRadiusDamageTraceRequest &request,
        const SvGlassState &glassState,
        std::span<const SvCollisionEntity> collisionEntities)>;

    // OLMOD(capsule-entity-collision): section 74. The capsule path had no
    // server-side entry at all -- every capsule query came in through the
    // native pmove trace callback, which supplies its own filter and always
    // excludes the moving player. That made entity-vs-entity collision
    // unreachable by any instrument on a one-player map. This is the same
    // shape as SvPointTraceRunner and exists for the same reason.
    using SvCapsuleTraceRunner = std::function<std::optional<TraceResult>(
        const std::array<float, 3> &start,
        const std::array<float, 3> &end,
        const TraceBounds &bounds,
        std::uint32_t contentMask,
        const SvGlassState &glassState,
        std::span<const SvCollisionEntity> collisionEntities,
        const SvTraceEntityFilter &filter)>;

    // CODREF(bg_update_player_dobj): the shared animation globals carry a
    // CLOCK, and every native animation call reads it. CODOL mirrors two
    // millisecond times into the anim-condition block - one at +0x96DD8, one
    // at +0x96DDC - and the owner of that block is responsible for keeping
    // them current. This project owns that block on the server, so the server
    // time has to reach it; without it the block's zeroed clock freezes every
    // animation. See EngineBindings::installServerAnimConditionStorage.
    using SvNativeEntityMirrorSynchronizer = std::function<bool(
        SvNativeEntityMirrorPhase phase,
        std::span<const SvCollisionEntity> collisionEntities,
        std::span<const SvNativeEntityStateSource> entityStates,
        std::uint32_t serverTime)>;

    using SvClientImpactsDispatcher = std::function<void(
        const SvClientImpactCallbackBatch &callbacks)>;

    using SvClientImpactsScriptDispatcher = std::function<void(
        const SvClientImpactScriptNotificationBatch &notifications)>;

    using SvEntityTouchHandler = std::function<void(
        const SvClientImpactCallback &callback)>;

    enum class SvWorldEventType : std::uint8_t
    {
        ClientSpawned = 1,
        ClientDisconnected = 2,
        WeaponSwitchStarted = 3,
        PlayerDamage = 4,
        EntityTouch = 5,
        PlayerKilled = 6,
        EntityDamage = 7,
        EntityKilled = 8,
        SdBombPickedUp = 9,
        SdBombDropped = 10,
        SdPlantStarted = 11,
        SdPlantCancelled = 12,
        SdBombPlanted = 13,
        SdDefuseStarted = 14,
        SdDefuseCancelled = 15,
        SdBombDefused = 16,
        SdBombExploded = 17,
        SdRoundEnded = 18,
        WeaponChanged = 19,
        // A ONCE-A-SECOND HEARTBEAT FOR THE ZM ROUND DIRECTOR.
        //
        // The gametype script owns spawning -- every zm builtin is script-facing --
        // but the script had no way to be woken. `codol.on` carries seventeen
        // reactive events and no periodic one, so a round loop written in Lua could
        // only ever run at map load, which is exactly the one-shot spawn 12.159 is
        // about. Raised from stepActorEntities, which already runs every frame.
        ZmRoundTick = 20,
    };

    struct SvSdEventPayload
    {
        std::optional<std::uint32_t> actorClientNum;
        std::optional<std::uint32_t> objectId;
        std::optional<std::string> siteLabel;
        std::optional<std::array<float, 3>> origin;
        std::optional<SvTeam> winner;
        std::uint32_t reason{};
        std::uint32_t elapsedMilliseconds{};

        bool operator==(const SvSdEventPayload &) const = default;
    };

    struct SvWorldEvent
    {
        // OLMOD(world-event-journal): post-commit observer record used by the
        // backend/Lua bridge. It is neither a snapshot event nor a GSC notify.
        std::uint32_t sequence{};
        SvWorldEventType type{};
        std::uint32_t serverTime{};
        std::uint32_t clientNum{};
        std::uint32_t spawnSequence{};
        std::uint8_t spawnGeneration{};
        std::uint16_t weaponAssetIndex{};
        std::string weaponName;
        std::optional<SvPlayerDamagePayload> playerDamage;
        std::optional<SvPlayerDeathState> playerKilled;
        std::optional<SvEntityDamageEvent> entityDamage;
        std::optional<SvZmAwardEvent> zombieAward;
        std::optional<SvSdEventPayload> sd;

        bool operator==(const SvWorldEvent &) const = default;
    };

    enum class SvClientThinkFailureStage : std::uint32_t
    {
        None,
        NotPlaying,
        SpawnedThisFrame,
        NonIncreasingCommandTime,
        InvalidInputState,
        NativePmoveUnavailable,
        NativePmoveRejected,
        InvalidPmoveOutput,
        NativePlayerStateProjection,
        NativeCommandTimeMismatch,
        WeaponMovementRejected,
        InvalidWeaponMovementOutput,
        EntityStateConversion,
        PostConversionProjection,
        EntityStateDecode,
        PredictableEventDecode,
        ConvertedStateMismatch,
        ClientEventsUnsupported,
        ClientEventsRejected,
        FinalProjection,
        FinalStateMismatch,
        InvalidClientImpacts,
        NativeEntityMirrorUnavailable,
        NativePmoveInvalidBinding,
        NativePmoveInvalidCommand,
        NativePmoveWrongThread,
        NativePmoveReentrantCall,
        NativePmoveHandlerSlotBusy,
        NativePmoveAnimConditionInstallFailed,
        NativePmoveNonIncreasingCommandTime,
        NativePmoveSliceLimitExceeded,
        NativePmoveCommandTimeNotAdvanced,
        NativePmoveNativeException,
        NativePmoveHandlerRestoreFailed,
        NativePmoveTraceFailed,
        NativePmoveAnimConditionRestoreFailed,
        NativePmoveInvalidOutput,
    };

    struct SvClientThinkStatus
    {
        // OLMOD(client-think-diagnostics): source-only failure telemetry. It
        // must not influence native command acceptance or wire state.
        std::uint32_t lastAttemptedCommandTime{};
        std::uint32_t lastCommittedCommandTime{};
        // The two clocks the command is measured against. A handful of stale in-flight
        // commands and a client whose whole time base is behind the server produce the
        // same failure stage and are told apart only by the gap.
        std::uint32_t playerStateCommandTime{};
        std::uint32_t serverTime{};
        SvClientThinkFailureStage failureStage{};
        std::uint32_t failureCount{};
        std::optional<SvNativePlayerStateActionDiagnostics>
            nativeActionDiagnostics;

        bool operator==(const SvClientThinkStatus &) const = default;
    };

    [[nodiscard]] std::string_view SV_ClientThinkFailureStageName(
        SvClientThinkFailureStage stage);

    enum class SvSnapshotFrameValidationFailure : std::uint8_t
    {
        None,
        SceneFlags,
        MapCenter,
        PlayerStateOrder,
        AnimationCommands,
        ClientOrder,
        ClientTeam,
        AgentOrder,
        AgentDomain,
        EntityOrder,
        ClientInfoOrder,
        Glass,
        PlayerClientCount,
        ClientInfoOwner,
        ClientInfoDomain,
        PlayerStateClientJoin,
        PlayerStateDomain,
        PlayerEntityJoin,
        PlayerEntityDomain,
        EntityDomain,
    };

    [[nodiscard]] std::string_view SV_SnapshotFrameValidationFailureName(
        SvSnapshotFrameValidationFailure failure);

    enum class SvSnapshotWriteFailure : std::uint8_t
    {
        None,
        InvalidFrame,
        MissingPlayerState,
        InvalidBaselineFrame,
        MissingBaselinePlayerState,
        MapCenterMismatch,
        DeltaWithoutBaseline,
        BaselineInitializationWithBaseline,
        PlayerState,
        AnimationCommands,
        Clients,
        PacketEntities,
        ClientInfos,
        Glass,
        Overflow,
    };

    [[nodiscard]] std::string_view SV_SnapshotWriteFailureName(
        SvSnapshotWriteFailure failure);

    [[nodiscard]] bool SV_ValidateSnapshotFrame(
        const SvSnapshotFrame &frame,
        SvSnapshotFrameValidationFailure *failure = nullptr);
    [[nodiscard]] bool SV_WriteSnapshot(
        MsgWriter &message,
        const SvSnapshotFrame &frame,
        const SvSnapshotFrame *baseline,
        std::uint32_t clientNum,
        std::uint8_t deltaMessageDistance,
        bool initializeBaselineCache,
        const SvClientPrediction *clientPrediction = nullptr,
        SvSnapshotWriteFailure *failure = nullptr);

    struct SvActorTransform
    {
        SvEntityHandle actor;
        std::array<float, 3> origin{};
        std::array<float, 3> angles{};
    };

    class SvServerWorld
    {
        // OLMOD(server-world-owner): aggregate transaction/lifecycle owner for
        // the reconstructed dedicated path. This is deliberately not a source
        // declaration of level_locals_t, g_entities or level.clients.
    public:
        enum class FinishPlayerDamageResult : std::uint8_t
        {
            Applied,
            ClientNotFound,
            NotPlaying,
            InvalidPayload,
            DeathTransitionUnavailable,
            NativeMirrorUnavailable,
        };

        enum class WeaponAmmoMutationResult : std::uint8_t
        {
            Applied,
            ClientNotFound,
            NotPlaying,
            WeaponNotOwned,
            AmmoStateMissing,
        };

        enum class RespawnRequestResult : std::uint8_t
        {
            Queued,
            ClientNotFound,
            NotPlaying,
            NotDead,
            InvalidDelay,
        };

        void reset();
        bool configureSpawn(
            std::array<float, 3> origin,
            std::array<float, 3> angles);
        bool configureSpawnPoints(
            std::span<const SvWorldSpawnPoint> spawnPoints,
            std::optional<SvWorldSpawnPoint> waitingForLoadoutPoint = std::nullopt);
        // Story missions respawn at the last committed checkpoint rather than
        // returning to their one map-entry spawn. Capture the authoritative
        // feet/view pose here so a later death can reuse the normal
        // SV_ClientSpawn transaction with a per-client spawn point.
        [[nodiscard]] bool savePlayerRespawnCheckpoint(
            std::uint32_t clientNum);
        bool configureMapCenter(std::array<float, 3> mapCenter);
        [[nodiscard]] bool configureGlassMap(
            const SvGlassMapMetadata &metadata,
            SvGlassDamageThresholds thresholds);
        // THE ZOMBIE NAVIGATION GRAPH, handed in at world spawn. An EMPTY graph is a
        // legitimate configuration and the normal one -- see sv_zm_navgraph_mp.hpp.
        void setZmNavGraph(SvZmNavGraph graph);
        [[nodiscard]] const SvZmNavGraph &zmNavGraph() const { return zmNavGraph_; }
        // Select the retail 32-slot agent-only ACTORS namespace for zm. Kept as
        // explicit world state so snapshot assembly and actor allocation make the
        // same decision from the first frame of the map.
        void setZmActorNamespaceEnabled(bool enabled);
        void setZmReconstructedFeedbackEnabled(bool enabled);
        bool zmReconstructedFeedbackEnabled() const { return zmActorNamespaceEnabled_ && zmReconstructedFeedbackEnabled_; }
        // CAN AN ACTOR SPAWNED ON THIS GOAL EVER REACH THE PLAYERS?
        //
        // The navgraph is measured off demo trajectories and is a FLOOR, not retail's
        // own graph: on zm_factory_sh its 1100 nodes fall into 207 connected
        // components -- 837 in the main body and 186 nodes with no edge at all.
        // MEASURED 12.80: of four actors spawned across four zones, two started on
        // isolated nodes (339 and 306, each a component of ONE) and A* returned an
        // empty route for both, every frame, forever.
        //
        // `true` when the goal resolves to a node in the main component -- the one the
        // players' own node is in. This is a REACHABILITY test, not a fallback: an
        // unroutable goal still gets no invented path, it simply never gets an actor.
        [[nodiscard]] bool zmGoalRoutable(const std::array<float, 3> &goal) const;
        // The index SvActorWalkAnimName resolved to on THIS engine, or 0 when it did
        // not resolve, in which case actors keep SvActorAnimIndex.
        void setZmActorWalkAnim(std::uint16_t animIndex);
        void setZmActorTearAnim(std::uint16_t animIndex);
        void setZmTearClips(const SvZmTearClips &clips);
        void setZmBoardTrajectoryEvaluator(SvTrajectoryEvaluator evaluate);
        void setZmPresentation(std::span<const SvZmOutfit> outfits,
            std::span<const SvZmDeathClip> deaths, SvZmDeathFx fx = {});
        // OLMOD(zm-round-colors): the existing Lua round owner supplies this;
        // it changes future spawns only, never an existing actor or corpse.
        std::uint32_t zmPresentationRound() const { return zmPresentationRound_; }
        bool consumeZombieDown(std::uint32_t clientNum);
        void setZmPresentationRound(std::uint32_t round) { if (round >= 1 && round <= 255) zmPresentationRound_ = round; }
        void setZmActorDeathAnim(std::uint16_t animIndex);
        void setZmActorAttackAnim(std::uint16_t animIndex);
        // THE MAP'S BARRIERS, handed in at world spawn beside the graph. Keyed here
        // by the node pair of their traversal, because that pair is the leg an actor
        // walks and is how the stepper recognises a boarded window.
        void setZmBarriers(std::span<const SvZmBarrier> barriers);
        [[nodiscard]] std::size_t zmBarrierCount() const { return zmBarriers_.size(); }
        // The nearest window which has a settled torn board that a player can
        // rebuild, measured from the player to the barrier's authored inside node.
        [[nodiscard]] std::optional<std::string> repairableZmBarrierAt(
            const std::array<float, 3> &origin) const;
        // Starts one retail-shaped two-stage board return. Completion, not the key
        // press, restores collision and makes that board tearable again.
        [[nodiscard]] bool repairZmBarrier(std::string_view barrierName);
        // DOES A ZOMBIE SPAWNED AT THIS GOAL HAVE TO COME THROUGH A WINDOW?
        //
        // 12.67a measured that only 5 of factory's 30 spawner goals route to the
        // players across a barrier at all; the rest walk in over open ground. The
        // gametype script has been choosing spawn zones by ADJACENCY as a proxy for
        // this, and adjacency is not the same question -- reported from the map as
        // zombies strolling into the yard instead of tearing through a board.
        //
        // Routes and the barrier edge set both live here, so this is the only place
        // the real question can be asked. It runs an A* per call, so the caller must
        // ask ONCE per spawn point and cache -- 12.163 is what per-tick pathfinding
        // in the script costs.
        [[nodiscard]] bool zmSpawnCrossesBarrier(
            const std::array<float, 3> &goal) const;
        void setSharedPmoveRunner(SvSharedPmoveRunner runner);
        void setWeaponMovementRunner(SvWeaponMovementRunner runner);
        void setPlayerStateToEntityStateConverter(
            SvPlayerStateToEntityStateConverter converter);
        void setDeathAnimationRunner(SvDeathAnimationRunner runner);
        // ALT-FIRE IS A CLIENT COMMAND, NOT A BUTTON. The player's menu calls
        // it "Weapon Attachments" and it sits beside the killstreaks on 4-7,
        // none of which are `+` binds -- so it never reaches a usercmd. It
        // arrives as the reliable command `n 89`, measured with an exact count
        // match: ten presses, ten commands. Queued here and consumed by the
        // next clientThink, which turns it into the one rising edge the
        // existing toggle already knows how to handle.
        void requestAltWeaponToggle(std::uint32_t clientNum);
        // Raise a pain or death vocal on a player's OWN event ring. Staged into
        // playerEventRings_ rather than written to the entity: that ring is
        // server-owned and clientThink republishes the entity FROM it every
        // frame, so an event written straight to the entity is overwritten by
        // the next merge.
        void stagePlayerVocal(
            std::uint32_t clientNum, std::uint32_t parameter, bool force);
        void setSpawnAnimationRunner(SvSpawnAnimationRunner runner);
        void setClientEventsHandler(SvClientEventsHandler handler);
        void setMissileFrameRunner(SvMissileFrameRunner runner);
        // OLMOD(factory_special_reconstruction): map-scoped capability registry.
        [[nodiscard]] bool spawnFactoryViewFx(std::uint32_t clientNum, std::uint16_t slot);
        void stepFactoryWeaponLights(const std::array<std::uint16_t,3> &slots);
        void setFactoryMonkeySong(std::uint16_t alias) { factoryTrapFx_.monkeySong=alias; }
        void setFactorySpecialWeapons(std::map<std::uint16_t,SvFactorySpecialKind> weapons,
            std::map<std::uint16_t,SvFactorySpecialCombat> combat = {}, SvFactoryTrapFx fx = {});
        [[nodiscard]] std::optional<SvFactorySpecialKind> factorySpecialWeapon(std::uint16_t asset) const;
        [[nodiscard]] SvMissileFrameResult stepFactorySpecialMissile(
            SvFactorySpecialKind kind,const SvServerMissile &missile,
            const std::array<float,3> &origin,std::uint32_t now) const;
        void applyFactorySpecialImpact(const SvFactorySpecialImpact &impact);
        void stepFactorySpecialPresentation();
        [[nodiscard]] std::optional<std::array<float,3>> factoryMonkeyTarget(
            const std::array<float,3> &from) const;
        [[nodiscard]] bool replaceFactoryEquipment(std::uint32_t clientNum,
            std::size_t slot,const SvOffhandWeapon &replacement,std::uint32_t costRaw=0);
        // SECTION 190: weapon asset index -> its alt, read off weaponDefinition
        // +3720 by EngineBindings (which owns the module base). 0 means the
        // weapon has no alt, which is the answer for most of them.
        using SvAltFireResolver =
            std::function<std::uint16_t(std::uint16_t weaponAssetIndex)>;
        void setAltFireResolver(SvAltFireResolver resolver);
        void setClientImpactsDispatcher(
            SvClientImpactCallbackOrder callbackOrder,
            SvClientImpactsDispatcher dispatcher);
        void setClientImpactsScriptDispatcher(
            SvClientImpactsScriptDispatcher dispatcher);
        [[nodiscard]] bool setPlayerTouchHandler(
            std::uint32_t clientNum,
            SvEntityTouchHandler handler);
        [[nodiscard]] bool setEntityTouchHandler(
            SvEntityHandle handle,
            SvEntityTouchHandler handler);
        [[nodiscard]] bool setEntityDamageState(
            SvEntityHandle handle,
            std::optional<SvEntityDamageState> state);
        [[nodiscard]] std::optional<SvEntityDamageState> entityDamageState(
            SvEntityHandle handle) const;
        [[nodiscard]] std::optional<SvEntityDamageRuntimeStatus>
        entityDamageRuntimeStatus(std::uint32_t entityNum) const;
        [[nodiscard]] bool setEntityDamageHandler(
            SvEntityHandle handle,
            SvEntityDamageHandler handler);
        [[nodiscard]] bool configureEntityDamageOwner(
            SvEntityHandle handle,
            SvEntityDamageState state,
            SvEntityDamageHandler handler);
        void setPointTraceRunner(SvPointTraceRunner runner);
        void setRadiusDamageVisibilityRunner(SvRadiusDamageVisibilityRunner runner);
        void setCapsuleTraceRunner(SvCapsuleTraceRunner runner);
        void setNativeEntityMirrorSynchronizer(
            SvNativeEntityMirrorSynchronizer synchronizer);
        [[nodiscard]] bool sharedPmoveAvailable() const;
        [[nodiscard]] bool nativeEntityMirrorSynchronized() const;
        [[nodiscard]] std::optional<TraceResult> tracePoint(
            const SvPointTraceRequest &request) const;
        [[nodiscard]] std::optional<bool> traceRadiusDamageVisibility(
            const SvRadiusDamageTraceRequest &request) const;
        [[nodiscard]] std::optional<TraceResult> traceCapsule(
            const std::array<float, 3> &start,
            const std::array<float, 3> &end,
            const TraceBounds &bounds,
            std::uint32_t contentMask,
            const SvTraceEntityFilter &filter) const;
        [[nodiscard]] bool configureEntityPool(
            std::uint32_t firstDynamicEntityNum);
        [[nodiscard]] bool configureSpawnAndBrushModelEntities(
            std::array<float, 3> origin,
            std::array<float, 3> angles,
            std::uint32_t firstDynamicEntityNum,
            std::span<const SvBrushModelEntityDefinition> brushDefinitions,
            std::span<const SvScriptModelEntityDefinition> scriptModelDefinitions = {},
            std::span<const SvScriptModelDamageOwnerDefinition>
                scriptModelDamageOwners = {},
            // The map's own name, used to find its shipped const-baseline table
            // and publish every brush model on RETAIL'S entity number. Empty --
            // or a map this build has no extracted table for -- falls back to
            // sequential numbering, which renders but is not 1/1.
            std::string_view mapName = {},
            // AND THE GAMETYPE, because the table is keyed on the PAIR. An MP map
            // ships one per gametype -- mp_nuked has thirteen -- and the entity
            // numbering differs between them.
            std::string_view gameType = {},
            // Hidden source owners for campaign actor spawners, triggers and
            // script data. They are queryable by Lua but are not published.
            std::span<const SvLogicalMapEntityDefinition>
                logicalMapEntities = {});
        [[nodiscard]] bool configureBrushModelEntities(
            std::uint32_t firstDynamicEntityNum,
            std::span<const SvBrushModelEntityDefinition> definitions);
        // One podium figure: an ET_SCRIPTMOVER standing on a `top_players_loc`
        // struct, carrying clientNum + 1 so the client builds THAT player's
        // character onto it (section 124).
        // SPAWN ONE ZOMBIE. Bring-up: it stands still. Position streaming, the
        // terminal trType-13 state and death all come later; this exists to prove an
        // ET_ACTOR reaches the client and draws at all.
        // appearanceIndex goes to entityState field 29 / +0x09C, this eType's own
        // 10-bit index -- NOT to modelIndex, which is the scriptmover xmodel slot
        // and selects nothing on an actor. It must already be resolved from a model
        // NAME into this server's band.
        // Allocate a runtime entity at or above a floor, instead of from the
        // pool's sequential free list. reserve() is a no-op on a number already
        // reserved and refuses one in use, so this walks past both.
        [[nodiscard]] std::optional<SvEntityHandle> spawnEntityAtOrAbove(
            std::uint32_t floor);

        // ADVANCE EVERY LIVE ACTOR ONE FRAME. Retail streams a zombie's POSITION
        // every snapshot and does not extrapolate: on the capture, pos.trBase X and Y
        // assert ~130,000 times each while pos.trDelta asserts ~750, and both trTypes
        // are set ONCE at spawn and never re-asserted.
        // re/demo-re/20-zm-actor-lifecycle.md 12.33.
        // Planar distance to the nearest living, playing player, or nullopt when
        // there is none.
        [[nodiscard]] std::optional<float> nearestPlayerDistance(
            const std::array<float, 3> &from) const;
        // The actual origin of the nearest living, playing player. The nav node is
        // only the graph destination; an actor must still walk the final node->player
        // leg after the route is exhausted.
        [[nodiscard]] std::optional<std::array<float, 3>> nearestPlayerOrigin(
            const std::array<float, 3> &from) const;
        [[nodiscard]] std::optional<std::uint32_t> nearestPlayerClientNum(
            const std::array<float, 3> &from) const;
        void stepActorEntities(std::uint32_t frameMilliseconds);
        void stepZmBarrierMotions();
        void stepFactoryDoorMotions();
        // OLMOD(factory_power): one map-scoped owner for the eight power pieces.
        bool stepFactoryPowerMotions();
        // OLMOD(factory_perk_machines): class-preserving, generation-owned purchases.
        bool zombieRevivalEnabled_{}, zombieRevivalActive_{}, zombieTeamWiped_{};
        // OLMOD(factory-debug-godmode): explicit local-test opt-in, not a retail rule.
        bool factoryDebugGodmode_{};
        // Side owner: never grow the address-sensitive SvGameClient/WorldClientState.
        std::unordered_map<std::uint32_t, SvZombieDownedState> zombieDowned_;
        struct ZombieDownedInventory
        {
            std::uint8_t generation{};
            std::uint16_t weapon{},offhand{},reward{};
            std::array<std::uint16_t,3> offhandSlots{};
            std::array<SvHeldWeaponState,15> held{};
            std::array<SvAmmoClipState,15> clips{};
            std::array<SvAmmoPoolState,15> pools{};
            std::optional<SvResolvedLoadout> loadout;
            std::optional<SvResolvedWeapon> grantedWeapon;
        };
        std::map<std::uint32_t,ZombieDownedInventory> zombieDownedInventories_;
        std::uint16_t zombieFallbackPistol_{};
        struct FactoryArrivalHold
        {
            std::uint32_t birth{};
            std::uint8_t generation{};
            bool active{};
        };
        bool factoryArrivalMap_{};
        std::map<std::uint32_t,FactoryArrivalHold> factoryArrivalHolds_;
        std::map<std::uint32_t,std::pair<std::uint8_t,std::array<float,3>>> factoryTravelHolds_;
        bool prepareZombieDownedInventory(SvGameClient &client,ZombieDownedInventory &saved) const;
        void restoreZombieDownedInventory(SvGameClient &client,const ZombieDownedInventory &saved);
        void sendZombieDownedPresentation(std::uint32_t client,bool downed,std::uint16_t weapon);
        bool factoryPerkMachinesEnabled_{};
        // OLMOD(factory_interactables): independent, default-off Factory owner
        // for the mystery box, Pack-a-Punch and teleporter transactions.
        bool factoryInteractablesEnabled_{};
        struct FactoryPurchasedPerkLife { std::uint8_t generation{}; std::uint32_t mask{}; };
        std::map<std::uint32_t,FactoryPurchasedPerkLife> factoryPurchasedPerks_;
        bool factoryPowerMotionEnabled_{}, factoryPowerBound_{}, factoryPowerFailed_{}, factoryPowerComplete_{};
        std::optional<std::uint32_t> factoryPowerStarted_;
        std::uint16_t factoryPowerLeverModel_{}, factoryPowerBodyModel_{};
        std::vector<SvEntityHandle> factoryPowerHandles_;

        // ONE ACTOR'S PLANNED ROUTE through the nav graph.
        //
        // Kept HERE and not on SvEntityState because a route is server bookkeeping
        // that never reaches the wire, and SvEntityState is copied whole every frame
        // for the delta comparison.
        struct ActorRoute
        {
            std::vector<std::uint16_t> nodes;
            std::size_t cursor{};
            std::uint32_t plannedAtMilliseconds{};
            // Cumulative diagnostics survive sparse route reports; no per-step I/O.
            std::uint64_t shortcutChecks{};
            std::uint64_t shortcutAccepted{};
            std::uint32_t lastShortcutAt{};
            std::array<float,3> directPursuitTarget{};
            std::array<float,3> directPursuitPlayer{};
            std::uint32_t directPursuitCheckedAt{};
            bool directPursuitClear{};
            std::uint64_t directPursuitChecks{};
            std::uint64_t directPursuitAccepted{};
            // Prediction-traced OpenBLOPS-style forward point.  It is refreshed at
            // a bounded cadence so route smoothing cannot become a per-frame trace
            // multiplier when a full wave is alive.
            std::array<float,3> lookaheadTarget{};
            // CODREF(actor_path_lookahead): server-only prediction state. No
            // actor/player wire field, native layout or multiplayer state changes.
            SvZmAreaLookahead lookaheadArea{};
            std::array<float,3> lookaheadDirection{};
            std::size_t lookaheadLastNode{};
            std::uint32_t lookaheadCheckedAt{};
            std::size_t lookaheadCursor{};
            bool lookaheadClear{};
            // The node the route was planned TOWARD. When the player moves to a
            // different node the route is stale even if the timer has not expired.
            std::uint16_t destination{};
            // The spawner's linked goal identifies its entrance.  Factory goals sit
            // immediately outside a boarded negotiation edge; keep that edge assigned
            // until the actor has crossed it so A* cannot choose an open shortcut.
            std::optional<std::pair<std::uint16_t, std::uint16_t>> spawnBarrier;
            bool spawnBarrierResolved{};
            bool spawnBarrierPassed{};
            // A cleared receiver window is an authored negotiation, not a normal
            // collision-free walk edge.  Retain its endpoints and clock so the
            // actor follows the Factory demo's mantle motion exactly once, while
            // every ordinary route leg continues to use world collision.
            bool windowTraverseActive{};
            bool windowTraverseLanding{};
            std::optional<std::pair<std::uint16_t,std::uint16_t>> negotiationActive;
            std::optional<std::pair<std::uint16_t,std::uint16_t>> negotiationCompleted;
            std::uint32_t negotiationStartedAt{};
            std::array<float,3> negotiationOffset{};
            std::uint32_t windowTraverseStartedAt{};
            std::array<float, 3> windowTraverseStart{};
            std::array<float, 3> windowTraverseEnd{};
            std::uint16_t windowTraverseEndNode{};
            std::uint16_t windowTraverseAnim{};
            unsigned windowTraverseVariant{};
            float windowTraverseYaw{};
            // Spawn closets and the authored receiver-window mantle need the
            // compact route probe: their static collision intentionally overlaps
            // the actor while it is outside the playable space. Once the actor
            // has reached ordinary map space, promote it exactly once to the same
            // player-sized horizontal capsule used by its linked collision body.
            // Never demote it again after promotion; doing so would let an actor
            // that entered a wall resume moving through it.
            bool fullNavigationBounds{};
            // A sparse graph edge can describe a corridor that bends around a
            // world brush.  Once collision chooses a side of that brush, retain
            // the choice for this waypoint. Recomputing it from the shrinking
            // node vector every frame flips the tangent at the node's Y value and
            // leaves the actor oscillating at the wall instead of rounding it.
            std::optional<std::uint16_t> wallFollowWaypoint;
            std::int8_t wallFollowSign{};
            // The last graph node actually reached. Periodic replans retain the
            // waypoint in flight at cursor zero, so cursor-1 alone cannot identify
            // the physical edge currently being attempted.
            std::optional<std::uint16_t> previousNode;
            // Demo-inferred edges that this actor's capsule proved are blocked by
            // static world collision. They are excluded from subsequent A* routes.
            std::vector<std::pair<std::uint16_t, std::uint16_t>> blockedEdges;
            std::optional<std::pair<std::uint16_t, std::uint16_t>> blockedCandidate;
            std::uint32_t blockedCandidateSince{};
            // A partial trace is only proof of a bad inferred edge when the
            // actor is no longer getting closer to its waypoint.  Lateral wall
            // motion alone must not clear the timer: that was the endless
            // wall-hugging failure this state is meant to detect.
            float blockedCandidateDistance{};
            bool planned{};
        };

        // The node nearest a living player, or nullopt when nobody is playing.
        [[nodiscard]] std::optional<std::uint16_t> nearestPlayerNavNode(
            const std::array<float, 3> &from) const;

        [[nodiscard]] std::optional<std::array<float, 3>> nearestPlayerPosition(
            const std::array<float, 3> &from) const;

        [[nodiscard]] std::optional<std::uint32_t> spawnZombieActor(
            const SvWorldSpawnPoint &place,
            std::uint16_t appearanceIndex,
            std::uint16_t headIndex = 0);

        [[nodiscard]] std::optional<std::uint32_t> spawnPodiumFigure(
            const SvWorldSpawnPoint &place,
            std::uint8_t clientNumPlusOne,
            std::uint16_t modelIndex);
        void revealPodiumFigures();
        bool setPodiumFigureAnimation(std::uint32_t entityNum,
            std::uint16_t animationIndex, std::uint32_t startTime,
            std::uint8_t flags = 1, bool clearTree = false,
            std::uint16_t fadeOutAnimationIndex = 0);
        [[nodiscard]] std::optional<std::uint32_t> spawnPodiumWeapon(
            std::uint32_t figureEntityNum, std::uint16_t weaponAssetIndex,
            std::uint8_t tagIndex);
        // The outro CAMERA as an ENTITY (HANDOFF 129). Retail's is a map
        // scriptmover that has existed since map load and simply starts moving
        // at match-end +16950; this server has no such entity, so it spawns one
        // on the map's own `top_players_camera` and hands every player's view
        // to it. The hidden tag carrier supplies the DObj the client requires
        // to resolve the playerState camera tag.
        [[nodiscard]] std::optional<std::uint32_t> spawnPodiumCamera(
            const SvWorldSpawnPoint &place,
            std::uint16_t tagCarrierModelIndex,
            std::uint32_t trajectoryStartTime = 0);
        // Switch the camera from retail's 500 ms type-7 entrance into its
        // measured 16.5-second type-4 motion without discontinuity.
        bool continuePodiumCameraMotion(
            std::uint32_t entityNum, std::uint32_t trajectoryStartTime);
        // CREATE A SCRIPT MODEL THAT THE MAP DOES NOT CONTAIN. The loot primitive.
        //
        // setScriptModelPresentation is a MUTATOR, not a constructor: it requires
        // eType == EntityTypeScriptMover and a non-zero modelIndex before it will
        // touch an entity, which is exactly right for moving one of the map's own
        // script models and useless for making a new one. spawnEntity() hands back a
        // blank slot -- eType 0, no model, gameplayActive false -- so the two do not
        // compose, and every loot spawn failed on that gap.
        //
        // Modelled on spawnPodiumFigure, which is the only other place this server
        // creates a script mover from nothing, and which documents the trap: an entity
        // is filtered out of the snapshot before publication unless gameplayActive is
        // set, and the staging pass that sets it for MAP script models runs on mode
        // changes, so an entity created mid-match is never staged and never drawn.
        //
        // SCENERY, NOT AN OBSTACLE. Collision is deliberately left unlinked with the
        // default capsule, so loot cannot become an invisible wall. Pickup will need a
        // linked volume; that belongs with the touch wiring, not here.
        // Spawn every player with empty hands; see SvClientSpawnConfig::unarmed.
        // The world owns the spawn call and does not know the gametype, so the
        // gametype owner sets this once at match configure.
        void setUnarmedSpawns(bool unarmed);
        // The weapon an unarmed spawn holds; see
        // SvClientSpawnConfig::unarmedWeaponAssetIndex. Set separately from the flag
        // because the gametype owner knows the MODE and only the asset owner can
        // resolve a NAME to an index.
        void setUnarmedSpawnWeapon(std::uint16_t weaponAssetIndex);
        // GIVE A PLAYER A WEAPON -- the owner this server has never had, and the
        // reason both loot pickup and the fists spawn were stuck.
        //
        // The native pmove DELETES a weapon the player was not properly given: the
        // measurement was `weapon ACROSS PMOVE before=1137 after=0` on the very first
        // frame, heldWeapons wiped with it. Nothing here can perform the native give,
        // so a grant is recorded as SERVER-OWNED STATE and re-asserted after every
        // pmove, the same way setPlayerNoclip holds noclip. Empty hands are simply the
        // grant a player starts with.
        //
        // The resolver turns a weapon asset index into a full definition (ammo index,
        // clip index, clip size, max ammo). Without it a grant cannot fill ammo and
        // the weapon would be unfireable, so a grant is refused when it is unset.
        using WeaponDefinitionResolver =
            std::function<bool(std::uint16_t, SvResolvedWeapon &)>;
        void setWeaponDefinitionResolver(WeaponDefinitionResolver resolver);
        void setZombieFallbackPistol(std::uint16_t weapon) { zombieFallbackPistol_=weapon; }
        void setLivingWeaponRightTag(std::uint8_t tagIndex);
        // HOW THE CLIENT IS TOLD. The current weapon is not a playerstate netfield on
        // this build, so it never rides the snapshot -- the server has to SAY it, with
        // the reliable command `a <weaponAssetIndex>`.
        //
        // MEASURED in C-2021-7-25[22-23-22]dmz: `a` fires at spawn and again inside
        // every cursorHint window where the player takes something, and three of its
        // six values (1184, 1193, 1186) are entries of that match's OWN loot band
        // (cs 12506..12692, 1148..1211). The other three sit just above the band, which
        // is what a freshly registered modular variant of a looted gun would look like.
        // Its values are always >= firstDynamicWeapon; the `w` command's are always
        // small and static, so `w` is something else.
        using ReliableCommandSender =
            std::function<bool(std::uint32_t, const std::string &)>;
        void setReliableCommandSender(ReliableCommandSender sender);
        [[nodiscard]] bool givePlayerWeapon(
            std::uint32_t clientNum,
            std::uint16_t weaponAssetIndex);
        // Replace the active player's authoritative weapons without
        // changing their multiplayer class selection. Campaign scripts use
        // this for retail's fixed mission arsenal and scripted handoffs. The
        // supplemental slot carries Wetwork's temporary insertion weapon.
        [[nodiscard]] bool setPlayerWeapons(
            std::uint32_t clientNum,
            std::uint16_t primaryWeaponAssetIndex,
            std::uint16_t secondaryWeaponAssetIndex,
            std::uint16_t selectedWeaponAssetIndex,
            std::uint16_t supplementalWeaponAssetIndex = 0);
        [[nodiscard]] WeaponAmmoMutationResult setPlayerWeaponAmmo(
            std::uint32_t clientNum,
            std::uint16_t weaponAssetIndex,
            std::int64_t clipCount,
            std::int64_t stockCount);
        // Drop back to empty hands. Called at spawn so a life does not inherit the
        // last one's loot.
        void clearPlayerWeaponGrant(std::uint32_t clientNum);
        [[nodiscard]] std::uint16_t playerGrantedWeapon(
            std::uint32_t clientNum) const;
        [[nodiscard]] bool unarmedSpawns() const;
        [[nodiscard]] std::optional<SvEntityHandle> spawnScriptModel(
            std::uint16_t modelIndex,
            std::string_view modelName,
            const std::array<float, 3> &origin,
            const std::array<float, 3> &angles);
        // Point one player's view at `entityNum`, tag `tag`. ADDITIVE: the
        // origin-move intermission stays, so if the client ignores this the
        // view is still held where 121 put it.
        bool setPlayerPodiumView(
            std::uint32_t clientNum, std::uint32_t entityNum, std::uint32_t tag);
        void clearPlayerPodiumView(std::uint32_t clientNum);
        // THE KILLCAM (HANDOFF 141). Four playerState fields asserted together
        // and cleared together; `i 0 0.000000 0 1` rides the same frame and is
        // queued by the caller, because it is a reliable command and this owns
        // only world state.
        bool setPlayerKillCam(
            std::uint32_t clientNum,
            std::uint32_t lookAtEntityNum,
            std::uint32_t killerClientNum,
            std::uint32_t deltaTime);
        void clearPlayerKillCam(std::uint32_t clientNum);
        // NOCLIP IS A HELD STATE, NOT A WRITE. holdMatchCompletionState says
        // why: "the world rebuilds each client's playerState from pmove, so a
        // single write is overwritten on the very next frame". This records the
        // request and clientThink re-applies it ahead of every pmove until it
        // expires. holdMilliseconds 0 takes SvNoclipDefaultHoldMilliseconds.
        bool setPlayerNoclip(
            std::uint32_t clientNum,
            bool enabled,
            std::uint32_t holdMilliseconds = 0);
        [[nodiscard]] bool playerNoclip(std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<SvEntityHandle> spawnEntity();
        // A model-less ET_SCRIPTMOVER used as the client-visible angular
        // reference for a tilting world.  Wetwork selects one of these through
        // playerState field 231 while the freighter sinks; it is presentation
        // only and never enters collision.
        [[nodiscard]] std::optional<SvEntityHandle>
            spawnGroundTiltController();
        [[nodiscard]] bool setGroundTiltControllerTrajectory(
            SvEntityHandle controller,
            std::uint8_t trajectoryType,
            std::uint32_t trajectoryTime,
            std::uint32_t trajectoryDuration,
            const std::array<float, 3> &angles,
            const std::array<float, 3> &angularDelta);
        [[nodiscard]] bool setPlayerGroundReference(
            std::uint32_t clientNum,
            SvEntityHandle controller);
        [[nodiscard]] bool clearPlayerGroundReference(
            std::uint32_t clientNum);
        // Campaign AI is a joined pair: ET_ACTOR supplies world transform and
        // events, while the 24-row agentState list supplies presentation.
        // Creating either half alone is refused at snapshot admission.
        [[nodiscard]] std::optional<SvEntityHandle> spawnActor(
            const SvAgentState &agent,
            const std::array<float, 3> &origin,
            const std::array<float, 3> &angles);
        [[nodiscard]] bool setActorAgentState(
            SvEntityHandle actor,
            const SvAgentState &agent);
        [[nodiscard]] std::optional<SvAgentState> actorAgentState(
            SvEntityHandle actor) const;
        // Move a joined campaign actor as one source transaction.  The
        // snapshot transform, collision capsule and native mirror must always
        // describe the same position; a failed native mirror rolls the source
        // entity back before returning to script.
        [[nodiscard]] bool setActorTransform(
            SvEntityHandle actor,
            const std::array<float, 3> &origin,
            const std::array<float, 3> &angles);
        // Move a linked campaign cast in one transaction. Wetwork carries seven
        // actors on the helicopter and updates them together every 100 ms; doing
        // seven independent mutations rebuilt the complete collision/native
        // mirror seven times and starved the scripted camera timeline.
        [[nodiscard]] bool setActorTransforms(
            std::span<const SvActorTransform> transforms);
        // CODREF(Wetwork ET_ACTOR -> ET_ACTOR_CORPSE): a dead actor keeps its
        // entity number and model, releases the joined agent row immediately,
        // and moves into the client's 32-slot actor-corpse presentation ring.
        // The cargo-hold detonation begins in this build's proven local
        // ragdoll trajectories; ordinary weapon deaths retain the stationary
        // COD4 Actor_BecomeCorpse transition.
        [[nodiscard]] bool retainZombieCorpse(SvEntityHandle actor);
        [[nodiscard]] bool convertActorToCorpse(
            SvEntityHandle actor,
            bool startRagdoll = false);
        // Campaign actors publish the same four-slot entity event ring as
        // players. Wetwork's hostile gunshots are event 41 with parameter 0;
        // keeping the append here makes generation and eType checks part of
        // the world mutation instead of trusting a map script with raw state.
        // Original Factory arrival: ET_SCRIPTMOVER event113 on its own ring.
        [[nodiscard]] bool queueScriptModelSoundEvent(SvEntityHandle carrier, std::uint16_t alias);
        [[nodiscard]] bool queueScriptModelFxEvent(
            SvEntityHandle carrier, std::uint16_t effect, std::uint8_t bone);
        [[nodiscard]] bool queueActorPresentationEvent(
            SvEntityHandle actor,
            const SvEntityEvent &event);
        // Publish one positional sound through the client's sound-alias
        // constant-string table. Campaign dialogue uses the ordinary
        // ET_EVENTS sound carrier, so it remains spatial and audible to every
        // client instead of being reduced to a local UI command.
        [[nodiscard]] bool spawnSoundAliasEvent(
            std::uint16_t eventParameter,
            const std::array<float, 3> &origin,
            bool asMaster = false);
        [[nodiscard]] bool spawnWorldFxEvent(
            std::uint16_t eventParameter,
            const std::array<float, 3> &origin,
            const std::array<float, 3> &angles);
        [[nodiscard]] bool spawnFireMagicEvent(
            std::uint8_t eventParameter,
            const std::array<float, 3> &origin);
        [[nodiscard]] bool spawnWorldFxOnTagEvent(
            SvEntityHandle target,
            std::uint16_t effectIndex,
            std::uint8_t tagIndex,
            const std::array<float, 3> &origin);
        // Campaign recordings contain scripted rockets whose trajectories are
        // presentation, not player-owned grenade simulation. They use the
        // recovered ET_MISSILE state and ordinary entity lifetime while staying
        // outside missiles_, so the gameplay runner cannot collide or detonate
        // them a second time.
        [[nodiscard]] std::optional<SvEntityHandle> spawnScriptedMissile(
            const SvMissileNetworkState &state);
        [[nodiscard]] bool setScriptedMissileState(
            SvEntityHandle handle,
            const SvMissileNetworkState &state);
        [[nodiscard]] bool spawnExploderEvent(std::uint8_t eventParameter, SvEntityHandle *created = nullptr);
        [[nodiscard]] bool spawnPhysicsExplosionSphereEvent(
            const std::array<float, 3> &origin,
            float innerRadius,
            float outerRadius,
            float magnitude);
        [[nodiscard]] bool spawnRadiusDamageEvent(
            const std::array<float, 3> &origin,
            float effectRadius,
            std::uint32_t data1,
            std::uint32_t data2);
        [[nodiscard]] bool spawnEarthquakeEvent(
            const std::array<float, 3> &origin,
            float scale,
            float radius,
            std::uint16_t durationMilliseconds);
        [[nodiscard]] bool freeEntity(SvEntityHandle handle);
        // The Scavenger pack is a real ET_ITEM, not an invisible server trigger.
        // Retail drops weapon asset 902 (`scavenger_bag_mp`) on a non-suicide
        // player death and removes it only after an eligible player actually
        // receives ammunition.
        [[nodiscard]] std::optional<SvEntityHandle> spawnScavengerBag(
            std::uint32_t victimClientNum,
            std::uint16_t itemWeaponAssetIndex);
        [[nodiscard]] std::vector<std::uint32_t> updateScavengerBags();
        [[nodiscard]] std::optional<SvServerMissile> missile(SvEntityHandle handle) const;
        // THE KILL FEED IS AN ENTITY EVENT (section 191q). One temp entity per
        // death, eType 166, carrying victim / attacker / weapon-or-means and
        // nothing else -- no origin, which is why it needs no PVS and reaches
        // every client. `attackerClientNum` may be EntityNumWorld for a death
        // nobody owns, and may equal the victim for a suicide; CG_Obituary
        // handles both and prints no line for either.
        [[nodiscard]] bool spawnObituaryEvent(
            std::uint32_t victimClientNum,
            std::uint32_t attackerClientNum,
            std::uint16_t eventParameter);
        // OLMOD(player-corpse-pool): a corpse is a SEPARATE entity from the
        // player who died, because the respawn resets the player's own entity
        // and the death animation has to keep playing after it. The dm demo
        // shows 18 distinct corpse entity numbers across a whole match - more
        // deaths than that by far - so the policy is a fixed pool the size of
        // MaximumGameClients with the oldest recycled, not a timeout nobody
        // measured.
        bool spawnPlayerCorpse(
            const SvGameEntity &deadPlayer,
            std::uint32_t deathAnimationDuration);
        void updatePlayerCorpses();
        [[nodiscard]] std::optional<SvGameEntity> entity(
            SvEntityHandle handle) const;
        [[nodiscard]] std::optional<SvEntityHandle> findScriptModel(
            const SvScriptModelEntityDefinition &definition) const;
        [[nodiscard]] std::vector<SvEntityHandle> findMapEntities(
            std::string_view value,
            std::string_view key) const;
        [[nodiscard]] std::optional<std::string> mapEntityField(
            SvEntityHandle handle,
            std::string_view key) const;
        [[nodiscard]] bool setScriptModelTransformAndActive(
            SvEntityHandle handle,
            const std::array<float, 3> &origin,
            const std::array<float, 3> &angles,
            bool active);
        // Commit trajectory bases to the snapshot and evaluated poses to collision.
        // The evaluator is the current build's native BG_EvaluateTrajectory adapter.
        // This does not schedule tears, impacts, or completion of a board animation.
        [[nodiscard]] bool setBrushModelMotion(
            SvEntityHandle handle,
            const SvNativeTrajectory &position,
            const SvNativeTrajectory &angles,
            std::uint32_t flags,
            std::int32_t atTime,
            const SvTrajectoryEvaluator &evaluate);
        // One collision/native-mirror commit for all moving boards in a frame.
        [[nodiscard]] bool setBrushModelMotions(
            std::span<const SvBrushModelMotion> motions,
            std::int32_t atTime,
            const SvTrajectoryEvaluator &evaluate);
        // Factory-only non-solid presentation; accepts ordinary native trajectories.
        [[nodiscard]] bool setFactoryTravelHold(std::uint32_t client,std::uint8_t generation,bool enabled);
        [[nodiscard]] bool factoryTravelHeld(std::uint32_t client,std::uint8_t generation) const;
        [[nodiscard]] bool teleportFactoryPlayer(std::uint32_t clientNum,
            std::uint8_t expectedLifeGeneration,const std::array<float,3>&destination,
            float yaw,std::uint32_t costRaw, std::optional<float> pitch=std::nullopt);
        // Recorded map gate only; current pose is evaluated separately from wire base.
        [[nodiscard]] bool setFactoryPackDoorMotion(SvEntityHandle handle,
            const SvNativeTrajectory &position,std::int32_t atTime);
        [[nodiscard]] bool setFactoryBoxModelMotion(SvEntityHandle handle,
            const SvNativeTrajectory &position);
        [[nodiscard]] bool setScriptModelIndex(
            SvEntityHandle handle,
            std::uint16_t modelIndex,
            std::string_view modelName);
        [[nodiscard]] bool setScriptModelPresentation(
            SvEntityHandle handle,
            std::uint16_t modelIndex,
            std::string_view modelName,
            const std::array<float, 3> &origin,
            const std::array<float, 3> &angles,
            bool active);
        [[nodiscard]] bool bindScriptModelAnimationTree(
            SvEntityHandle handle, std::uint8_t treeIndex);
        // Start one named XAnim on an existing map script_model. Campaign
        // geometry such as Wetwork's hull panels is already present and only
        // needs the animation state plus its matching packet-animation goal.
        [[nodiscard]] bool setScriptModelAnimation(
            SvEntityHandle handle,
            std::uint16_t animationIndex,
            std::uint32_t startTime,
            std::uint8_t flags = 1);
        [[nodiscard]] std::size_t entityCount() const;
        // Source-level capsule owner for target/impact regression. This does
        // not register a native DObj/CM-tree entity or serialize a snapshot.
        [[nodiscard]] bool linkEntityCollision(
            SvEntityHandle handle,
            std::optional<std::uint32_t> ownerEntityNum,
            const std::array<float, 3> &origin,
            const TraceBounds &bounds,
            std::uint32_t contents);
        [[nodiscard]] bool linkBrushModelCollision(
            SvEntityHandle handle,
            std::optional<std::uint32_t> ownerEntityNum,
            const std::array<float, 3> &origin,
            const std::array<float, 3> &angles,
            const SvBrushModelCollision &model);
        [[nodiscard]] bool setBrushModelGameplayActive(
            SvEntityHandle handle,
            bool active);
        // Atomically spends Factory battery and removes every brush/script model
        // named by a door/debris trigger's target key. A failed native publication
        // rolls the whole group back and spends nothing.
        [[nodiscard]] bool purchaseMapTargetGroup(
            std::uint32_t clientNum,
            std::uint32_t cost,
            std::string_view targetName);
        // Opens an authored door/debris target group without charging a player.
        // Factory's two electric doors take this path together on the power-switch
        // frame; the retail demo proves they are not separate 10000 purchases.
        [[nodiscard]] bool openMapTargetGroup(std::string_view targetName);
        // Atomically spends zombie battery and adds one retail perk bit. A perk
        // already owned is refused and therefore cannot charge twice.
        [[nodiscard]] bool factoryPerkMachinesEnabled() const { return factoryPerkMachinesEnabled_; }
        [[nodiscard]] bool factoryInteractablesEnabled() const { return factoryInteractablesEnabled_; }
        [[nodiscard]] bool factoryPowerMotionEnabled() const { return factoryPowerMotionEnabled_; }
        [[nodiscard]] bool activateFactoryPower(std::uint16_t leverModel, std::uint16_t bodyModel);
        // OLMOD(debug_battery): bounded opt-in debug currency, no score/kill award.
        [[nodiscard]] bool debugGrantFactoryBattery(std::uint32_t clientNum);
        // OLMOD(factory_ammo): refill owned firearm magazines and reserves;
        // leave equipment/class unchanged. Charge after native overlay validation.
        // Box Max Ammo includes this life's held equipment; paid stations retain
        // their separately verified firearm-only policy.
        [[nodiscard]] bool refillFactoryAmmo(std::uint32_t clientNum, std::uint32_t cost = 0,
            bool boxReward = false);
        [[nodiscard]] bool canRefillFactoryAmmo(std::uint32_t clientNum, std::uint32_t cost,
            bool boxReward = false) const;
        // OLMOD(factory_weapon_exchange): Factory-only selected firearm replacement.
        // This changes the current life's live resolved loadout, never the saved
        // multiplayer class. The caller owns prompt/hold state and queues client
        // selection only after this atomic source/native transaction succeeds.
        [[nodiscard]] bool replaceFactoryWeapon(std::uint32_t clientNum,
            std::uint16_t expectedAssetIndex,
            std::uint16_t replacementAssetIndex,
            std::uint32_t costRaw, std::string_view *refusal = nullptr);
        // Applies one exact Factory battery debit/refund only for the current
        // life. It refuses overflow/cap clipping so a failed refund is visible
        // to the caller instead of silently losing currency.
        [[nodiscard]] bool changeFactoryBattery(std::uint32_t clientNum,
            std::int64_t deltaRaw, std::uint8_t expectedLifeGeneration);
        [[nodiscard]] std::optional<std::uint32_t> factoryBattery(
            std::uint32_t clientNum, std::uint8_t expectedLifeGeneration) const;
        // A reusable, non-solid Factory box presentation entity.
        // Its weapon asset index is consumed by the native model-less
        // ET_SCRIPTMOVER path; callers reuse the returned handle per roll and
        // free it through freeEntity when the offer closes.
        [[nodiscard]] std::optional<SvEntityHandle> spawnFactoryWeaponDisplay(
            std::uint16_t weaponAssetIndex,
            const std::array<float, 3> &origin,
            const std::array<float, 3> &angles);
        [[nodiscard]] bool setFactoryWeaponDisplay(SvEntityHandle handle,
            std::uint16_t weaponAssetIndex,
            const std::array<float, 3> &origin,
            const std::array<float, 3> &angles);
        [[nodiscard]] bool setFactoryWeaponDisplayMotion(SvEntityHandle handle,
            std::uint16_t weaponAssetIndex,
            const SvNativeTrajectory &position,
            const std::array<float, 3> &angles);
        [[nodiscard]] bool purchaseZombiePerk(
            std::uint32_t clientNum,
            std::uint32_t cost,
            std::size_t word,
            std::uint32_t mask);
        [[nodiscard]] bool setMapGameObjects(
            std::span<const std::string_view> allowedGameObjectNames);
        [[nodiscard]] SvBrushModelActivationStatus brushModelActivationStatus()
            const;
        [[nodiscard]] bool unlinkEntityCollision(SvEntityHandle handle);
        [[nodiscard]] bool setGlassPieceState(
            std::uint32_t pieceIndex,
            SvGlassPieceState state,
            std::optional<SvGlassImpact> impact = std::nullopt);
        bool beginFrame(
            std::uint32_t frameMilliseconds,
            std::span<const SvWorldClientInput> activeClients);
        [[nodiscard]] bool clientThink(
            std::uint32_t clientNum,
            const UserCmd &command);
        bool endFrame(std::span<const SvWorldClientInput> activeClients);
        // Lifecycle-only convenience for frames with no dispatched commands.
        bool runFrame(
            std::uint32_t frameMilliseconds,
            std::span<const SvWorldClientInput> activeClients);
        [[nodiscard]] const SvSnapshotFrame &snapshot() const;
        [[nodiscard]] std::optional<SvPlayerState> playerState(
            std::uint32_t clientNum) const;
        // Tests a live player's collision box against one of the hidden map
        // trigger records exposed to mission Lua. Brush triggers use the
        // MapEnts TriggerModel/TriggerHull/TriggerSlab data extracted from the
        // fastfile; trigger_radius uses the stock radius/height AABB rule.
        [[nodiscard]] bool logicalMapEntityTouchesPlayer(
            SvEntityHandle handle,
            std::uint32_t clientNum) const;
        [[nodiscard]] bool setPlayerObjectives(
            std::uint32_t clientNum,
            const std::array<SvObjective, 32> &objectives);
        // Scripted sequences such as Wetwork's helicopter flight temporarily
        // protect a player without changing health or the native playerState
        // image. The owner is generation-scoped side storage; a new life is
        // damageable even if the previous script never reached its cleanup.
        [[nodiscard]] bool setPlayerCanTakeDamage(
            std::uint32_t clientNum, bool enabled);
        // Drives a player along a mission-owned path while retained Pmove still
        // consumes the real usercmd. The hold is re-applied after Pmove so a
        // single script write cannot be erased before the snapshot is built.
        [[nodiscard]] bool setPlayerScriptedPosition(
            std::uint32_t clientNum,
            const std::array<float, 3> &origin,
            std::uint8_t pmType,
            std::uint32_t pmFlags);
        [[nodiscard]] bool setPlayerScriptedViewAngles(
            std::uint32_t clientNum,
            const std::array<float, 3> &viewAngles);
        [[nodiscard]] bool setPlayerScriptedViewClamp(
            std::uint32_t clientNum,
            const std::array<float, 2> &clampBase,
            const std::array<float, 2> &clampRange);
        [[nodiscard]] bool setPlayerScriptedLinkState(
            std::uint32_t clientNum,
            std::uint8_t linkFlags,
            const std::array<float, 3> &linkAngles);
        [[nodiscard]] bool clearPlayerScriptedPosition(std::uint32_t clientNum);
        // Starts one client-side shellshock profile at the current mission
        // frame. The three fields are one state transition on the wire; callers
        // supply the profile index and lifetime rather than editing them apart.
        [[nodiscard]] bool setPlayerShellshock(
            std::uint32_t clientNum,
            std::uint8_t profileIndex,
            std::uint16_t durationMilliseconds);
        // Puts one client into the end-of-match state. Named after what it is
        // rather than after the two fields it writes, because a caller has no
        // business knowing that intermission IS pm_type 5 plus eFlags 16.
        // The camera is optional so a map without the entity still gets the
        // pm_type/eFlags half rather than nothing.
        // Hold a player where they stand for the end-of-match wait. Captures
        // the position on the first call and re-applies it every frame after,
        // because pmove rebuilds playerState and would walk them off it.
        [[nodiscard]] bool setPlayerMatchEndFreeze(std::uint32_t clientNum);
        void clearMatchEndFreeze();
        // Once the match is decided nothing spawns or respawns. See the spawn
        // gate in the client walk.
        void setMatchCompleted(bool completed);
        [[nodiscard]] bool setPlayerIntermission(
            std::uint32_t clientNum,
            const std::optional<SvWorldSpawnPoint> &camera = std::nullopt);
        // The perk HUD reacts to a clear->set EDGE on ps.perks, not to its
        // value: sub_52B8E0 diffs it against a cache at +0x1930D8 and only
        // calls add-perk for newly set bits. So perks have to be WRITABLE
        // after the spawn that zeroed them.
        [[nodiscard]] bool setPlayerAbilities(
            std::uint32_t clientNum, const SvAbilityModifiers &abilities);
        [[nodiscard]] bool equipPlayerEquipment(
            std::uint32_t clientNum, const SvResolvedEquipment &equipment);
        [[nodiscard]] bool grantPlayerUav(std::uint32_t clientNum,
            const SvRewardWeapon &weapon);
        [[nodiscard]] bool consumePlayerUavAction(std::uint32_t clientNum,
            std::uint16_t weaponAssetIndex);
        [[nodiscard]] bool setPlayerRadarFlags(std::uint32_t clientNum, std::uint8_t flags);
        [[nodiscard]] const SvResolvedEquipment *playerEquipment(
            std::uint32_t clientNum, std::uint8_t spawnGeneration) const;

        [[nodiscard]] bool setPlayerPerks(
            std::uint32_t clientNum,
            const std::array<std::uint32_t, 3> &perks);
        // THE USABLE PROMPT, SET AS ONE THING. The three playerState fields are
        // not independent -- a hint string with no cursorHint draws nothing and
        // an entity number with no cursorHint is dead weight -- and the same
        // argument that put setPlayerPerks and its visibility bit in one call
        // applies here. `hintStringIndex` is RELATIVE to configstring band 856.
        [[nodiscard]] bool setPlayerCursorHint(
            std::uint32_t clientNum,
            SvCursorHint hint,
            std::int32_t hintStringIndex,
            std::uint32_t hintEntityNum);
        // Back to (0, 0, 0). Retail idles at (0, -1, 2047); the client cannot
        // tell, and zero is free on the wire. See SvPlayerState::cursorHintString.
        [[nodiscard]] bool clearPlayerCursorHint(std::uint32_t clientNum);
        // THE PICKUP PROMPT, WHICH IS A DIFFERENT PROMPT. cursorHint above 4 is not
        // an enum value at all -- it is `weapon + 4`, and the client draws the gun's
        // own icon and PLATFORM_PICKUPNEWWEAPON instead of reading a hint string
        // (re/demo-re/18-hint-strings.md sec 3, sub_45BA10). That is why this is a
        // second entry point rather than another SvCursorHint case: the enum stops at
        // 4 and everything this needs starts at 5.
        //
        // hintEntityNum MATTERS HERE and does not on a text prompt. The client
        // multiplies it by 624 into its centity array, and the weapon path is the one
        // that actually follows it -- so a loot prompt has to name a live entity,
        // which is exactly what the crate is.
        [[nodiscard]] bool setPlayerWeaponCursorHint(
            std::uint32_t clientNum,
            std::uint16_t weaponAssetIndex,
            std::uint32_t hintEntityNum);
        // THE LOOT TABLE. Registration is the script's job -- it spawned the model and
        // it decides what is in it -- and everything after that is the server's.
        [[nodiscard]] bool registerLootItem(
            SvEntityHandle handle,
            std::uint16_t weaponAssetIndex,
            float radius);
        [[nodiscard]] bool removeLootItem(SvEntityHandle handle);
        // LIVE ITEMS ONLY. An entity freed by anything other than a pickup would
        // otherwise leave a crate that still offers a gun from a slot somebody else
        // now owns, which is the generation bug this pool exists to prevent.
        [[nodiscard]] std::vector<SvLootItem> lootItems() const;
        [[nodiscard]] bool setPlayerHudElems(
            std::uint32_t clientNum,
            const std::array<SvHudElem, 31> &current,
            const std::array<SvHudElem, 31> &archival);
        [[nodiscard]] bool setPlayerKillstreak(std::uint32_t clientNum,
            std::uint8_t value);
        [[nodiscard]] bool clearPlayerRewardState(std::uint32_t clientNum);
        [[nodiscard]] bool setPlayerEquippedRewards(std::uint32_t clientNum,
            const std::array<std::uint8_t, 3> &ids,
            const std::array<std::uint8_t, 3> &targets);
        [[nodiscard]] std::optional<SvWeaponAimState> weaponAimState(
            std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<float> currentAimSpreadScale(
            std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<SvGameEntity> playerEntity(
            std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<SvClientThinkStatus> clientThinkStatus(
            std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<SvBulletExecutionStatus>
            bulletExecutionStatus(std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<SvPredictableEventStatus>
            predictableEventStatus(std::uint32_t clientNum) const;
        [[nodiscard]] std::span<const SvCollisionEntity> collisionEntities() const;
        [[nodiscard]] std::span<const SvCollisionEntity> playerMovementCollisionEntities() const;
        [[nodiscard]] std::optional<SvCollisionEntity> collisionEntity(
            std::uint32_t entityNum) const;
        [[nodiscard]] std::optional<ClientGameplayState> gameplayState(
            std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<SvTeam> playerTeam(
            std::uint32_t clientNum) const;
        [[nodiscard]] bool onSameTeam(
            std::uint32_t firstClientNum,
            std::uint32_t secondClientNum) const;
        [[nodiscard]] bool acceptsClientThink(std::uint32_t clientNum) const;
        [[nodiscard]] WeaponAmmoMutationResult setWeaponAmmoClip(
            std::uint32_t clientNum,
            std::string_view weaponName,
            std::int64_t count);
        [[nodiscard]] WeaponAmmoMutationResult setWeaponAmmoStock(
            std::uint32_t clientNum,
            std::string_view weaponName,
            std::int64_t count);
        [[nodiscard]] RespawnRequestResult requestPlayerRespawn(
            std::uint32_t clientNum,
            std::uint32_t delayMilliseconds);
        [[nodiscard]] bool zombieRevivalActive() const { return zombieRevivalActive_; }
        [[nodiscard]] bool zombieTeamWiped() const { return zombieTeamWiped_; }
        [[nodiscard]] bool zombieDowned(std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<SvZombieDownedState> zombieDownedState(std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<std::uint32_t> zombieReviveTarget(std::uint32_t reviver) const;
        [[nodiscard]] bool zombieReviveHeld(std::uint32_t reviver) const;
        [[nodiscard]] bool processZombieReviveUse(std::uint32_t reviver, bool held);
        void stepZombieRevives();
        [[nodiscard]] FinishPlayerDamageResult finishPlayerDamage(
            const SvPlayerDamagePayload &payload);
        [[nodiscard]] FinishPlayerDamageResult finishPlayerDamageBatch(
            std::span<const SvPlayerDamagePayload> payloads);
        [[nodiscard]] std::optional<SvResolvedLoadout> resolvedLoadout(
            std::uint32_t clientNum) const;
        [[nodiscard]] std::span<const SvWorldEvent> frameEvents() const;
        [[nodiscard]] std::optional<SvZmScoreFeedback> zombieScoreFeedback(std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<SvWorldEvent> lastEvent() const;
        void appendSdEvent(
            SvWorldEventType type,
            SvSdEventPayload payload);
        [[nodiscard]] bool spawnConfigured() const;
        // How many script models were published on retail's own entity numbers at the
        // last world spawn. Diagnostic: the rest are on sequential numbers, which is
        // correct but not 1/1.
        [[nodiscard]] std::size_t constBaselineScriptModelCount() const
        {
            return constBaselineScriptModels_;
        }
        [[nodiscard]] std::uint32_t glassPieceCount() const;

    private:
        [[nodiscard]] std::optional<SvPlayerState> factoryAmmoRefillCandidate(std::uint32_t clientNum,
            bool boxReward) const;
        struct WorldClientState
        {
            SvGameEntity entity;
            SvGameClient client;
            SvClientThinkStatus thinkStatus;
            std::optional<SvCharacterCustomization> characterCustomization;
        };

        // THE SIZE OF THIS NODE IS A BEHAVIOUR, NOT A DETAIL. Section 184h.
        //
        // WorldClientState is the mapped type of a std::unordered_map, and it holds
        // SvGameClient -- whose member 0 is the native playerState the engine keys to
        // its own address. Section 141 pinned that member at OFFSET 0 and the assert
        // below it still holds; what section 184h found is that the offset was never
        // what moved. Forty-eight bytes added to SvCharacterCustomization, which this
        // struct holds BY VALUE, changed only the NODE SIZE -- and living players lost
        // their leg animation on 5.3% of sampled frames (222 of 4153, against 0 of
        // 5830 before), every death returned durationMs=-1, and every corpse T-posed.
        // A/B/A: reverting gave 1816/2883, moving the field off the customization gave
        // 2883/2883 with the identical mask still on the wire.
        //
        // WHERE is proved; WHY node size matters to an address-keyed slot is not, and
        // this comment does not pretend otherwise.
        //
        // SO IF YOU ARE HERE BECAUSE THIS FAILED: do not just update the number. The
        // number is cheap to change and the animation is not covered by any test. Add
        // the field, run a live cycle, kill a player, and read `durationMs` out of
        // CodolGameServer.log -- positive means it still selects, -1 means you have
        // just done what section 184h did. THEN update the number.
        // The ZM actor wire state adds 80 bytes to SvGameEntity, which this
        // player-owned node also embeds. Keep the merged size pinned so any
        // further accidental growth still stops the build; the live animation
        // cycle remains the required behavioral check described above.
        static_assert(sizeof(WorldClientState) == 25184);
        static_assert(offsetof(SvPlayerState, offhandWeaponAssetIndex) == 10);
        static_assert(offsetof(SvPlayerState, pmTime) == 12);
        static_assert(offsetof(SvPlayerState, offhandWeaponSlotA) + 2 ==
            offsetof(SvPlayerState, gravity));
        static_assert(offsetof(SvPlayerState, offhandWeaponSlotB) + 2 ==
            offsetof(SvPlayerState, lastSprintStart));
        static_assert(offsetof(SvPlayerState, offhandWeaponSlotC) + 2 ==
            offsetof(SvPlayerState, legsTimer));
        // And the struct that actually got grown, pinned separately because it is the
        // tempting one: it looks like a plain value type and it is embedded above.
        static_assert(sizeof(SvCharacterCustomization) == 64);

        // THE SERVER OWNS A PLAYER'S ENTITY EVENT RING, and it has to, because
        // it adds events the native projection knows nothing about.
        //
        // The first attempt emitted `native sequence + this frame's additions`.
        // That drops shots: fire on two consecutive frames with no native event
        // (a footstep, a jump) in between and both frames emit the SAME
        // sequence, so the client sees no change and skips the second. The
        // player's words were "it seems to be working, but not for every single
        // shot", which is exactly that.
        //
        // Nor can the offset simply be added to the native sequence: the client
        // reads slot = sequence & 3, so shifting our sequence past the native
        // one would make it read NATIVE events out of the wrong slots.
        //
        // So the ring is rebuilt: new native events are copied in at OUR
        // sequence, then our own are appended, and the whole thing is stored
        // back after the event handler runs.
        //
        // IT LIVES BESIDE WorldClientState, NOT IN IT. That struct holds
        // SvGameEntity and SvGameClient by value and its size is pinned by the
        // static_assert above -- section 184h grew it once and every corpse
        // T-posed. `mutable` because clientThinkReal is const.
        //
        // CAVEAT, stated rather than hidden: a REJECTED command candidate does
        // not roll this back, so a rejected frame can leave the sequence one
        // ahead. Rejections are rare (frameReject=none across the logs) and the
        // cost is one missed dispatch, not a desync -- the client resyncs its
        // cursor whenever the sequence moves the other way.
        struct SvPlayerEventRing
        {
            std::uint8_t lastNativeSequence{};
            std::uint8_t sequence{};
            std::array<SvEntityEvent, 4> ring{};
            bool seeded{};
        };
        mutable std::unordered_map<std::uint32_t, SvPlayerEventRing>
            playerEventRings_;
        // Last time each client used its voice, for the pain cooldown. See
        // stagePlayerVocal: retail grunts about once per LIFE, not once per hit.
        std::unordered_map<std::uint32_t, std::uint32_t> lastPlayerVocalTime_;
        // One pending alt-fire toggle per client. A plain array so nothing is
        // added to a struct the address-keyed native buffer contains.
        // mutable for the same reason playerEventRings_ is: the think that
        // consumes it is const.
        mutable std::array<bool, MaximumGameClients> pendingAltToggle_{};

        [[nodiscard]] SvClientThinkFailureStage clientThinkReal(
            SvGameEntity &entity,
            SvGameClient &client,
            SvGlassState &glassState,
            SvGlassDamageState &glassDamageState,
            const SvResolvedLoadout *resolvedLoadout) const;
        void appendEvent(
            SvWorldEventType type,
            std::uint32_t clientNum,
            std::uint32_t spawnSequence,
            std::uint8_t spawnGeneration,
            std::uint16_t weaponAssetIndex = 0,
            std::string_view weaponName = {});
        void appendPlayerDamageEvent(
            const SvPlayerDamagePayload &payload,
            std::uint32_t spawnSequence,
            std::uint8_t spawnGeneration,
            std::string_view weaponName);
        void appendEntityDamageEvent(
            const SvEntityDamageEvent &damageEvent,
            std::string_view weaponName,
            bool beforeFrameEventRotation = false,
            bool headlessDecay = false);
        // Raise ZmRoundTick. Rate-limited by the caller, not here.
        void queueZmRoundTickEvent(std::uint32_t serverTime);
        void queuePlayerKilledEvent(
            const SvPlayerDeathState &death,
            std::uint32_t spawnSequence,
            std::uint8_t spawnGeneration,
            std::string_view weaponName);
        // Applied to the CANDIDATE playerState at the top of clientThink, so
        // the native pmove is the thing that flies the player rather than this
        // server moving anyone itself.
        void applyNoclipHold(
            std::uint32_t clientNum, SvPlayerState &playerState);
        [[nodiscard]] std::optional<SvAbilityModifiers>
            effectivePlayerAbilities(
                std::uint32_t clientNum,
                std::uint8_t spawnGeneration) const;
        void markPlayerPainted(std::uint32_t clientNum);
        void clearPlayerPaint(std::uint32_t clientNum);
        void expirePaintedPlayers();
        void dispatchEntityTouchHandlers(
            const SvClientImpactCallbackBatch &callbacks);
        void rebuildCollisionView(
            SvNativeEntityMirrorPhase phase =
                SvNativeEntityMirrorPhase::Collision);
        [[nodiscard]] bool refreshClientCollisionView(
            std::uint32_t clientNum);

        struct DynamicEntityTouchHandler
        {
            std::uint32_t generation{};
            SvEntityTouchHandler handler;
        };

        struct DynamicEntityDamageHandler
        {
            std::uint32_t generation{};
            SvEntityDamageHandler handler;
        };

        struct PendingAnimationCommand
        {
            SvAnimationCommand command;
            std::uint8_t framesRemaining{};
        };

        SvSnapshotFrame snapshot_;
        // Retail carries each new packet-animation operation through four
        // consecutive snapshot frames. The writer may then reuse an equal
        // record from the selected delta baseline. This survives beginFrame's
        // snapshot reset and is decremented only after endFrame commits.
        std::vector<PendingAnimationCommand> pendingAnimationCommands_;
        // Survives the per-frame `snapshot_ = {}` in beginFrame, which is what
        // stamps SvSnapshotFrame::useEntityBaselines. Set once at world spawn:
        // true only when this map's static entities went out on retail's own
        // entity numbers.
        // PER PLAYER. Exact-client IDA establishes clientState field 1 (+0x40,
        // 32 bits) as the source copied to characterInfo+0xA4, which the Factory
        // battery HUD reads. Field 5 is an ability word and must never carry this.
        std::array<std::uint32_t, MaximumGameClients> zombieBattery_{};
        std::array<std::uint32_t, MaximumGameClients> debugBatteryReadyTime_{};
        bool constBaselineNumbering_{};
        const SvConstBaselineTable *constBaselineTable_{};
        // Base-map rows materialized by retail for an add-on campaign map.
        // They are presentation-only: no collision or script owner is needed.
        std::vector<SvEntityState> staticBaselineEntities_;
        // Wetwork's admission frame excludes ET_PLAYER entities. The player's
        // own state is carried by playerState/clientState during this phase.
        bool wetworkInitialScene_{};
        // Keep Wetwork's opening snapshots limited to the recorded 880-row
        // admission scene until retail begins publishing live intro entities.
        std::optional<std::uint32_t> wetworkRecordedOpeningUntil_;
        // How many script models landed on retail's own numbers. Reported rather than
        // required: a prop that cannot be resolved to a single table row stays on a
        // sequential number, which is correct but costs wire bytes.
        std::size_t constBaselineScriptModels_{};
        bool unarmedSpawns_{};
        std::uint16_t unarmedSpawnWeapon_{};
        WeaponDefinitionResolver weaponDefinitionResolver_;
        std::uint8_t livingWeaponRightTag_{};
        struct LivingWeaponChild
        {
            // Generation zero is a valid first life. Use an invalid entity
            // number for absence, not the generation counter.
            SvEntityHandle handle{EntityNumNone, 0};
            std::uint16_t weaponAssetIndex{};
        };
        // Outside WorldClientState because its native mirror has a fixed size.
        // The second native child field remains zero until it is recovered.
        std::array<LivingWeaponChild, MaximumGameClients> livingWeaponChildren_{};
        std::vector<SvLootItem> lootItems_;
        ReliableCommandSender reliableCommandSender_;
        // One granted weapon per client. A single slot is deliberate for now: it is
        // what "walk over a crate, hold that gun" needs, and a second slot is a
        // weapon-switch contract that nothing has measured yet.
        struct SvWeaponGrant
        {
            SvResolvedWeapon weapon;
            bool active{};
        };
        std::array<SvWeaponGrant, MaximumGameClients> weaponGrants_{};
        std::vector<SvWorldSpawnPoint> spawnPoints_;
        std::optional<SvWorldSpawnPoint> waitingForLoadoutPoint_;
        std::unordered_map<std::uint32_t, SvWorldSpawnPoint>
            playerRespawnCheckpoints_;
        struct SvScriptedPlayerPosition
        {
            std::array<float, 3> origin{};
            std::uint8_t pmType{};
            std::uint32_t pmFlags{};
            std::optional<std::array<float, 3>> viewAngles;
            std::array<float, 2> viewAngleClampBase{};
            std::array<float, 2> viewAngleClampRange{};
            std::array<float, 3> linkAngles{};
            std::uint8_t linkFlags{};
        };
        // Mission side storage. Keeping this outside WorldClientState preserves
        // the address-keyed native player image's guarded allocation size.
        std::unordered_map<std::uint32_t, SvScriptedPlayerPosition>
            scriptedPlayerPositions_;
        // PER CLIENT, NOT ONE FOR ALL OF THEM. A single string means two
        // clients alternate `client=0` and `client=1` through it, the
        // comparison never matches, and a diagnostic meant to fire on a
        // CHANGE fires on every frame instead. It is the same shape as the
        // shared edge-trigger that blinded three states in section 118.
        std::unordered_map<std::uint32_t, std::string> spawnRefusalReasons_;
        SvSharedPmoveRunner sharedPmoveRunner_;
        SvWeaponMovementRunner weaponMovementRunner_;
        SvPlayerStateToEntityStateConverter playerStateToEntityStateConverter_;
        SvDeathAnimationRunner deathAnimationRunner_;
        SvSpawnAnimationRunner spawnAnimationRunner_;
        SvClientEventsHandler clientEventsHandler_;
        SvMissileFrameRunner missileFrameRunner_;
        SvAltFireResolver altFireResolver_;
        std::optional<SvClientImpactCallbackOrder> clientImpactCallbackOrder_;
        SvClientImpactsDispatcher clientImpactsDispatcher_;
        SvClientImpactsScriptDispatcher clientImpactsScriptDispatcher_;
        std::unordered_map<std::uint32_t, SvEntityTouchHandler>
            playerTouchHandlers_;
        std::unordered_map<std::uint32_t, DynamicEntityTouchHandler>
            entityTouchHandlers_;
        SvPointTraceRunner pointTraceRunner_;
        SvRadiusDamageVisibilityRunner radiusDamageVisibilityRunner_;
        SvCapsuleTraceRunner capsuleTraceRunner_;
        SvNativeEntityMirrorSynchronizer nativeEntityMirrorSynchronizer_;
        bool nativeEntityMirrorSynchronized_{};
        std::unordered_map<std::uint32_t, WorldClientState> clientStates_;
        // clientNum -> protected spawn generation. This deliberately lives
        // beside WorldClientState: changing that node's size has broken native
        // animation selection before, while damage admission is server-only.
        std::unordered_map<std::uint32_t, std::uint8_t>
            playerDamageProtectionGeneration_;
        // Side storage keeps WorldClientState and its native pmove image stable.
        struct AbilityLife
        {
            std::uint8_t spawnGeneration{};
            SvAbilityModifiers modifiers;
        };
        std::unordered_map<std::uint32_t, AbilityLife> playerAbilities_;
        struct PaintedLife
        {
            std::uint8_t spawnGeneration{};
            std::uint32_t expireTime{};
        };
        std::unordered_map<std::uint32_t, PaintedLife> paintedPlayers_;
        struct EquipmentLife
        {
            std::uint8_t spawnGeneration{};
            SvResolvedEquipment equipment;
        };
        std::unordered_map<std::uint32_t, EquipmentLife> playerEquipment_;
        struct WeaponObservation
        {
            std::uint32_t spawnSequence{};
            std::uint16_t weapon{};
        };
        std::unordered_map<std::uint32_t, WeaponObservation> observedWeapons_;
        // THE MEASURED NAVIGATION GRAPH for the loaded map, or empty. Empty is the
        // normal case: only zm_factory_sh has one, and a map without one parks its
        // actors on their spawners rather than improvising a path.
        SvZmNavGraph zmNavGraph_;
        // THE CONNECTED COMPONENT OF EVERY NODE, and which one is the map's main body.
        // Recomputed whenever the graph is installed. See zmGoalRoutable.
        std::vector<std::uint16_t> zmNavComponent_;
        std::uint16_t zmNavMainComponent_{};
        // ONE BARRIER. `boardClipHandles` are the boards' `*N` in slot order,
        // resolved to live entities LAZILY: brush models spawn on a different path
        // from this one and there is no ordering guarantee at world spawn.
        struct BarrierState
        {
            std::string name;
            std::vector<std::uint32_t> boardClipHandles;
            struct Board
            {
                std::uint32_t clip{};
                const SvZmBoardFlightProfile *profile{};
                std::optional<SvEntityHandle> handle;
                std::optional<std::uint32_t> releasedAt;
                SvNativeTrajectory homePosition{};
                SvNativeTrajectory homeAngles{};
                std::uint32_t homeFlags{};
                std::array<float, 3> repairStartOrigin{};
                std::array<float, 3> repairStartAngles{};
                std::optional<std::uint32_t> repairStartedAt;
                bool homeCaptured{};
                bool settled{};
            };
            std::array<Board,6> boards{};
            SvZmBarrierController controller;
            std::array<std::optional<SvEntityHandle>,3> occupants{};
            std::uint16_t outsideNode{};
            std::uint16_t insideNode{};
            std::size_t torn{};
        };
        std::map<std::pair<std::uint16_t, std::uint16_t>, BarrierState> zmBarriers_;
        std::uint16_t zmActorWalkAnim_{};
        // The index SvActorTearAnimName resolved to, or 0 when this build does not
        // hold it. Zero means the barrier state keeps the walk, which is wrong-looking
        // but never a wrong index.
        std::uint16_t zmActorTearAnim_{};
        SvZmTearClips zmTearClips_{};
        SvTrajectoryEvaluator zmBoardTrajectoryEvaluator_;
        // The last server time a ZmRoundTick was raised. Retail's early-round
        // cadence is 300 ms, so the director heartbeat is 100 ms.
        std::uint32_t zmRoundTickMilliseconds_{};
        std::uint32_t zmPresentationRound_{1};
        std::vector<SvZmOutfit> zmOutfits_;
        std::vector<SvZmDeathClip> zmDeaths_;
        SvZmDeathFx zmDeathFx_{};
        std::uint32_t zmDeathFxDiagnosticCount_{};
        // OLMOD(damage-number-owner): per-world/per-client life, at most 32 rings.
        std::map<std::uint32_t, SvClientDamageNumbers> zombieDamageNumbers_;
        std::map<std::uint32_t, SvClientZombieInjuries> zombieInjuries_;
        // Source-owned display reward state; separate from battery and native layouts.
        std::map<std::uint32_t, SvZmScoreFeedback> zombieScoreFeedback_;
        // OLMOD(death_fx_owner): generation-qualified, bounded by live actors;
        // kept outside SvEntityState/native mirrored layouts.
        struct ZmDeathFxState
        {
            SvEntityHandle handle;
            std::uint16_t body{}, attachment0{}, attachment1{}, effect{};
            std::uint8_t bone{255};
            std::uint32_t ignoreCollision{}, modelAt{}, playedAt{};
            bool applied{}, played{}, stopped{};
            SvZmOutfit outfit{};
            std::int32_t maxHealth{SvActorSpawnHealth};
            bool bodyDamaged{}, headless{}, electrical{}, pendingHead{};
            std::uint32_t headDue{}, dotAt{};
            // OLMOD(refined_fx): bounded generation-owned presentation sequence.
            std::uint16_t downAnimation{};
            std::uint32_t downAt{}, downMilliseconds{}, retireAt{};
            bool downStarted{};
            std::int32_t dotDamage{};
            SvEntityDamagePayload headCause{};
            struct Emission
            {
                std::uint16_t effect{};
                std::uint8_t bone{255};
                std::uint32_t due{}, started{};
                bool played{}, stopped{};
            };
            std::array<Emission,4> emissions{};
        };
        std::map<std::uint32_t, ZmDeathFxState> zmDeathFxStates_;
        // OLMOD(zm-face-glow): no native DTO/layout changes; one owner per life.
        struct ZmFaceGlowState
        {
            SvEntityHandle handle;
            SvZmOutfit outfit;
            std::uint16_t body{},head{};
            std::uint32_t due{};
            std::array<bool,2> playing{};
        };
        std::map<std::uint32_t,ZmFaceGlowState> zmFaceGlowStates_;
        std::uint32_t zmFaceGlowDiagnosticCount_{};
        void stepZmFaceGlow(SvGameEntity &entity,std::uint32_t now);
        void stageZmDeathFx(const SvEntityDamageEvent &damage);
        void stepZmDeathFx(SvGameEntity &entity, std::uint32_t now);
        void applyZmHeadLoss(ZmDeathFxState &state, std::uint32_t now);
        std::uint32_t zmDamageRandom_{1}, zmHeadFrame_{}, zmHeadsThisFrame_{};
        std::uint32_t zmDamageRoll(std::uint32_t bound);
        std::uint32_t zmOutfitSequence_{}, zmDeathSequence_{};
        std::uint16_t zmActorDeathAnim_{};
        std::uint16_t zmActorAttackAnim_{};
        // Actors whose health has reached zero: entity number -> the server time the
        // death animation started. Presentation candidates transfer it into the
        // separate corpse pool after the clip, retaining this original death time.
        std::map<std::uint32_t, std::uint32_t> zmActorDeadAt_;
        struct ZmRetainedCorpse { SvEntityHandle handle; std::uint32_t diedAt; std::uint8_t slot; };
        std::vector<ZmRetainedCorpse> zmRetainedCorpses_;
        // Actor melee is selected while the actor map is being iterated, but the
        // existing player-damage transaction can spawn a corpse and therefore may
        // mutate the entity map. Stage one hit per target and commit it only after
        // the actor loop and the begin-frame native mirror have completed.
        std::vector<SvPlayerDamagePayload> pendingActorPlayerDamage_;
        std::unordered_map<std::uint32_t, std::uint32_t>
            zmPlayerNextActorHitMilliseconds_;
        // ENTITIES THE ACTOR STEPPER WANTS GONE, freed after the frame commits.
        //
        // `freeEntity` is a generation-owned G_FreeEntity operation and it cannot run
        // inside the frame transaction: doing it from stepActorEntities threw
        // "entity free rollback lost FIFO ownership" and killed the dedicated. The
        // barrier tear had always called it from there and got away with it only
        // because a bare `SvEntityHandle{ num }` carries generation 0 and the free
        // silently failed -- fixing that generation is what exposed this.
        std::vector<std::uint32_t> pendingActorFrees_;
        std::unordered_map<std::uint32_t, ActorRoute> actorRoutes_;
        // clientNum -> the serverTime the hold expires at. Absent means not
        // flying. Deliberately NOT a field on SvGameClient: that struct is
        // copied whole every think and its offset 0 is load-bearing for the
        // native pointer obfuscation, so the flag lives beside it instead.
        std::unordered_map<std::uint32_t, std::uint32_t> noclipHoldUntil_;
        // clientNum -> when they were last hurt and what they were left on.
        // Absent means never damaged this life, so nothing to regenerate. Reset
        // on spawn, because a fresh life starts at full health.
        std::unordered_map<std::uint32_t, SvHealthRegenState> healthRegen_;
        // clientNum -> fall damage raised by pmove this think and not yet
        // committed. Deferred rather than applied inline because the think that
        // observes the event is mid-flight through the client's own state, and
        // finishPlayerDamage owns that state's damage/death transition. Drained
        // at the top of the next beginFrame, before regen, so the regen window
        // this damage opens is the one regen then reads.
        // `mutable` because the think that OBSERVES the landing event is a
        // const method -- it reads the client's state and must not alter it.
        // Recording that a fall happened is bookkeeping for a later frame, not
        // a mutation of the state being thought about.
        mutable std::unordered_map<std::uint32_t, std::uint32_t>
            pendingFallDamage_;
        // Where each client stood when the match ended. See setPlayerMatchEndFreeze.
        std::unordered_map<std::uint32_t, std::array<float, 3>>
            matchEndFreezeOrigins_;
        bool matchCompleted_{};
        std::unique_ptr<SvEntityPool> entityPool_;
        // THE FLOOR RUNTIME ACTORS ALLOCATE ABOVE. One past the highest number
        // the map's const-baseline table names, or FirstDynamicServerEntityNum
        // when the map has no table.
        //
        // MEASURED, and NOT a correctness requirement: the pool already reserves
        // every const-baseline number, so an actor in the gaps resolves a zeroed
        // client baseline and this server deltas against zero -- the two agree
        // and nothing is inherited. This is fidelity. Retail numbers its actors
        // 488..815 on factory, above the map's last static entity (625), and
        // sixteen of the seventeen measured lives sit above it -- one did not,
        // so it is retail's convention rather than an invariant.
        // re/demo-re/20-zm-actor-lifecycle.md section 4a.
        std::uint32_t actorEntityFloor_{ FirstDynamicServerEntityNum };
        // THE AGENT SLOT POOL. sub_530C30 scans exactly 0x20 records, so there are
        // 32 slots and no more. This server already puts one element per PLAYER in
        // this list keyed by clientNum, so actors take slots from above the client
        // range and cannot collide with them.
        //
        // A slot is baked into the actor's entityState +0x058 at spawn and must not
        // move for the life of the entity, which is why it is allocated once here
        // rather than derived per frame from the snapshot's ordering.
        std::array<bool, SvAgentSlotCount> agentSlotsInUse_{};
        bool zmActorNamespaceEnabled_{};
        bool zmReconstructedFeedbackEnabled_{};
        std::unordered_map<std::uint32_t, SvGameEntity> entities_;
        // OLMOD(factory-door-motion): keep metadata outside address-sensitive
        // WorldClientState/SvGameEntity. A generation-qualified map owns the move.
        struct FactoryDoorMotionState {
            SvEntityHandle handle;
            std::uint16_t profile{};
            std::optional<std::uint32_t> started;
            bool complete{};
        };
        std::unordered_map<std::uint32_t, FactoryDoorMotionState> factoryDoorMotions_;
        std::vector<SvAgentState> campaignAgents_;
        std::uint32_t nextActorCorpseSlot_{};
        // Full campaign key/value records stay outside SvGameEntity. That
        // native-adjacent structure has a guarded byte size; mission metadata
        // is source-only and follows the same generation-safe entity handle.
        std::unordered_map<std::uint32_t, SvLogicalMapEntityDefinition>
            logicalMapEntities_;
        const SvMapTriggerTable *logicalMapTriggerTable_{};
        std::unordered_map<std::uint32_t, SvServerMissile> missiles_;
        std::map<std::uint16_t,SvFactorySpecialKind> factorySpecialWeapons_;
        std::map<std::uint16_t,SvFactorySpecialCombat> factorySpecialCombat_;
        SvFactoryTrapFx factoryTrapFx_;
        // Source-owned only; the guarded WorldClientState layout is unchanged.
        std::map<std::uint32_t,std::pair<SvEntityHandle,std::uint32_t>> factoryViewFxRecipients_;
        std::map<std::uint32_t,std::uint32_t> factoryViewFxNext_;
        struct FactoryTrapPresentation {
            SvEntityHandle missile;
            std::optional<SvEntityHandle> emitter;
        };
        std::map<std::uint32_t,FactoryTrapPresentation> factoryTrapPresentation_;
        struct FactorySpecialStatus {
            SvEntityHandle handle;
            std::uint32_t until{};
            bool frozen{},shrunk{};
            float originalScale{1.f};
            std::uint32_t shrinkStarted{};
        };
        std::map<std::uint32_t,FactorySpecialStatus> factorySpecialStatuses_;
        struct SvScavengerBag
        {
            SvEntityHandle handle;
            std::uint32_t victimClientNum{};
            std::uint32_t ownerClearTime{};
            std::uint32_t expireTime{};
            std::array<float, 3> pickupOrigin{};
        };
        std::unordered_map<std::uint32_t, SvScavengerBag> scavengerBags_;
        // Round-robin cursor into the fixed corpse ring, NOT the entity pool.
        std::uint32_t nextPlayerCorpseSlot_{};
        // A corpse is a THREE-STAGE entity on the wire, measured off the dm demo
        // (Tools/ffa/corpse-lifetime.py following one slot end to end):
        //   1. spawn   - re-initialise bit set, trType 1, anims written ONCE
        //   2. settle  - the re-initialise bit clears once the death animation
        //                has had time to run
        //   3. ragdoll - trType 13 + aprType 10, about a second after the spawn
        // Deadline of 0 means the stage is already done for that slot.
        struct SvPlayerCorpseStages
        {
            std::uint32_t clearReinitialiseTime{};
            std::uint32_t ragdollTime{};
        };
        std::array<SvPlayerCorpseStages, PlayerCorpseRingSize> corpseStages_{};
        std::unordered_map<std::uint32_t, SvEntityDamageState>
            entityDamageStates_;
        std::unordered_map<std::uint32_t, DynamicEntityDamageHandler>
            entityDamageHandlers_;
        SvGlassState glassState_;
        SvGlassMapMetadata glassMetadata_;
        SvGlassDamageState glassDamageState_;
        std::vector<SvCollisionEntity> collisionEntities_;
        // OLMOD(zm-player-collision): Pmove adds native packed-solid cyborg
        // capsules; actor navigation retains the actor-free world view above.
        std::vector<SvCollisionEntity> playerMovementCollisionEntities_;
        // Bullets retain their existing body contents and optional skeletal pose.
        std::vector<SvCollisionEntity> bulletCollisionEntities_;
        SvAntiLagHistory antiLagHistory_;
        std::uint32_t frameMilliseconds_{100};
        std::uint32_t eventSequence_{};
        std::vector<SvWorldEvent> frameEvents_;
        std::vector<SvWorldEvent> deferredEvents_;
        std::optional<SvWorldEvent> lastEvent_;
    };
}
