#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace CodolGameServer
{
    struct SvMapEntity
    {
        std::vector<std::pair<std::string, std::string>> fields;

        [[nodiscard]] std::optional<std::string_view> value(std::string_view key) const;
    };

    // A non-rendering map record made visible to the controlled gameplay VM.
    // Campaign maps put their mission graph in actor and vehicle spawners,
    // trigger volumes, script_structs and script_origins. Those records are
    // gameplay data rather
    // than snapshot entities, so they receive generation-safe source handles but
    // remain excluded from collision and network publication until a mission
    // owner explicitly turns them into an actor, mover, or event.
    struct SvLogicalMapEntityDefinition
    {
        std::size_t mapOrdinal{};
        std::vector<std::pair<std::string, std::string>> fields;
        std::array<float, 3> origin{};
        std::array<float, 3> angles{};
        bool hasOrigin{};
        bool hasAngles{};

        [[nodiscard]] std::optional<std::string_view> value(
            std::string_view key) const;
        bool operator==(const SvLogicalMapEntityDefinition &) const = default;
    };

    struct SvSpawnPoint
    {
        std::string className;
        std::array<float, 3> origin{};
        std::array<float, 3> angles{};

        bool operator==(const SvSpawnPoint &) const = default;
    };

    enum class SvSpawnTeam : std::uint8_t
    {
        Any,
        Tf,
        Sc,
    };

    struct SvModeSpawnPoint
    {
        SvSpawnPoint spawn;
        SvSpawnTeam team{ SvSpawnTeam::Any };

        bool operator==(const SvModeSpawnPoint &) const = default;
    };

    // A zm ZOMBIE SPAWN POINT. One `script_struct` carrying
    // `script_noteworthy "zombie_spawner"`, named by the spawner-group targetname its
    // zone points at. See re/demo-re/21-zm-zones-and-spawners.md.
    struct SvZmSpawnPoint
    {
        std::array<float, 3> origin{};
        std::array<float, 3> angles{};
        // The entity this spawn point targets: retail's navigation goal for the zombie
        // that spawns here. OPTIONAL AND MEASURED SO -- zm_sumpf_sh carries one on only
        // 32 of its 74 points, so an empty goal is normal, not a parse failure.
        std::string goal;

        // THE GOAL'S POSITION, resolved from that name at parse time.
        //
        // MEASURED off zm_factory_sh's own MapEnts: 61 of its 69 `zombie_spawner`
        // structs carry a `target`, ALL 61 resolve, and EVERY one resolves to a
        // `node_pathnode` -- the map's own AI navigation nodes -- 159 to 738 units
        // away. That is retail's pathing data, not a choice made here.
        //
        // `goal` alone was NOT usable: it is a NAME. Reading it as a destination
        // is what the old comment on this struct implied and it is wrong -- the
        // first factory spawn point's target reads `outside_up_spawners`, a
        // spawner-GROUP name, so the string has to be resolved, not trusted.
        std::array<float, 3> goalOrigin{};
        bool hasGoalOrigin{};

        bool operator==(const SvZmSpawnPoint &) const = default;
    };

    // ONE BOARD of a barrier. A `script_brushmodel` carrying
    // `script_parameters "board"`, so it is a real solid brush in the world and comes
    // out of the same `*N` numbering every other brush model does.
    struct SvZmBarrierBoard
    {
        // The `*N` from the `model` key -- retail's own brush model index, and the
        // identity this board is published under.
        std::uint32_t clipHandle{};
        // `script_noteworthy`, 1..6. The board's slot in the barrier, and the order
        // retail tears them in is a per-slot thing rather than a list order.
        std::uint32_t boardIndex{};
        std::array<float, 3> origin{};

        bool operator==(const SvZmBarrierBoard &) const = default;
    };

    // A zm BARRIER: the boarded window a zombie tears open to get inside.
    //
    // MEASURED ACROSS ALL FOUR zm MAPS, and the structure is uniform:
    //
    //   boards      `script_brushmodel` + `script_parameters "board"` +
    //               `script_team "classic_boards"`, grouped by `targetname`, with
    //               `script_noteworthy` giving a 1..6 slot. Factory 168 boards in 28
    //               groups, asylum 147/20, sumpf 114/19, prototype 72/12 -- SIX boards
    //               per group everywhere except three 15-board groups on asylum.
    //   the vault   the group's `targetname` shares its `pfNNN` prefix with a
    //               `node_negotiation_begin` target. Factory joins 28 of 28, sumpf 19
    //               of 19, prototype 12 of 12, asylum 17 of 20 -- and the board
    //               centroid sits a median **27 units** from that begin node on EVERY
    //               map, which is a construction rule rather than a coincidence.
    //
    // So a barrier is a board group plus the traversal co-located with it: the zombie
    // stands OUTSIDE at the begin node, tears the boards, and vaults to the end node
    // INSIDE. Factory's 53 negotiation pairs are more than its 28 barriers because not
    // every traversal is a window -- the rest are interior railings and drops.
    //
    // `script_noteworthy "<zone>_barriers"` anchors exist too, but they are NOT the
    // structure: factory has 12 covering 12 of its 28 groups, and the other three maps
    // have NONE while still having boards. Do not key the parse on them.
    struct SvZmBarrier
    {
        // The board group's `targetname`, e.g. `pf678_auto1`. The barrier's identity.
        std::string name;
        std::vector<SvZmBarrierBoard> boards;
        // Where a zombie stands to tear, and where it ends up. Absent when the group
        // has no matching negotiation pair -- three of asylum's twenty -- which means
        // the boards can be torn but the way through is not declared.
        std::array<float, 3> outside{};
        std::array<float, 3> inside{};
        bool hasVault{};
        // The vault's `animscript`, e.g. `zombie_mantle_over_40`. See 12.61 for why
        // most of these have no playable xanim yet.
        std::string animScript;

        bool operator==(const SvZmBarrier &) const = default;
    };

    // A zm ZONE. An `info_volume` with `script_noteworthy "player_volume"`, whose
    // `targetname` names the zone and whose `target` names its spawner group.
    //
    // A ZONE IS A UNION OF VOLUMES, not one volume: zm_factory_sh carries 32 volumes
    // across 12 zone names, zm_sumpf_sh 48 across 11. `volumeCount` records how many
    // carried this name so a caller can tell a one-volume zone from a stitched one.
    //
    // The volume SHAPE is deliberately absent. `info_volume` carries `"model" "?N"` --
    // a collision-only brush reference, note `?` and not the `*` a script_brushmodel
    // uses -- so the bounds live in the BSP, not the entity string. Point-in-zone needs
    // those bounds and is a separate job from this parse.
    // ONE HALF-SPACE PAIR CUTTING A HULL. `TriggerSlab` in MapEnts.trigger: a unit
    // normal and the interval along it the volume occupies, in the volume's own frame.
    struct SvZmVolumeSlab
    {
        std::array<float, 3> direction{};
        float midPoint{};
        float halfSize{};

        bool operator==(const SvZmVolumeSlab &) const = default;
    };

    // ONE HULL OF A VOLUME: a box, optionally cut by slab planes. A volume is the
    // UNION of its hulls, and this is EXACT -- not the bounding box of them.
    struct SvZmVolumeHull
    {
        std::array<float, 3> midpoint{};
        std::array<float, 3> halfSize{};
        std::vector<SvZmVolumeSlab> slabs;

        bool operator==(const SvZmVolumeHull &) const = default;
    };

    // ONE VOLUME OF A ZONE. A zone is the UNION of these.
    struct SvZmZoneVolume
    {
        // The `?N` from the volume's `model` key. NOT a cmodel handle: `?N` indexes
        // MapEnts.trigger while `*N` indexes the clipmap's cmodel list. They are
        // different arrays, and resolving one through the other returns an unrelated
        // brush -- measured, see the comment on the reader in EngineBindings.
        std::uint32_t triggerModel{};
        std::array<float, 3> origin{};

        // THE SHAPE, filled at world spawn out of MapEnts.trigger and empty until then;
        // the entity string carries none. `hullsResolved` distinguishes "resolved to
        // nothing" from "never asked", so an unresolved volume claims no space at all
        // rather than behaving like a zero-sized box at the world origin.
        std::vector<SvZmVolumeHull> hulls;
        bool hullsResolved{};

        bool operator==(const SvZmZoneVolume &) const = default;
    };

    struct SvZmZone
    {
        std::string name;
        std::string spawnerGroup;
        std::vector<SvZmZoneVolume> volumes;
        std::vector<SvZmSpawnPoint> spawnPoints;
        // Runtime gate owned by the zm match. MapEnts describes every zone, but
        // retail only enables the start zone initially and adds a zone when the
        // door/debris carrying its enter_* script_flag is opened.
        bool active{};

        bool operator==(const SvZmZone &) const = default;
    };

    struct SvMapBrushModelSpawn
    {
        // WHERE THIS ENTITY SITS IN THE MAP'S OWN ENTITY LIST. Retail's static entity
        // table is in allocation order, so brush models -- whose `*N` is an exact identity
        // -- are ORDERED ANCHORS, and the script models between two anchors are the table
        // rows between those same two anchors. Reconstructing that interleave needs the
        // original position, which selecting the two classes into separate vectors throws
        // away. See re/demo-re/16-const-baselines.md.
        std::size_t mapOrdinal{};
        // RETAIL'S OWN ENTITY NUMBER FOR THIS ENTITY, walked out of the map entity
        // string. See SV_AssignMapEntityNumbers and
        // re/demo-re/19-entity-numbering-and-triggers.md. Zero when the walk did not
        // run.
        std::uint32_t walkEntityNum{};
        std::uint32_t clipHandle{};
        std::array<float, 3> origin{};
        std::array<float, 3> angles{};
        std::string scriptGameObjectName;
        std::string targetName;
        std::string destructibleType;
        bool regularMultiplayerEligible{ true };

        bool operator==(const SvMapBrushModelSpawn &) const = default;
    };

    struct SvMapScriptModelSpawn
    {
        // WHERE THIS ENTITY SITS IN THE MAP'S OWN ENTITY LIST. Retail's static entity
        // table is in allocation order, so brush models -- whose `*N` is an exact identity
        // -- are ORDERED ANCHORS, and the script models between two anchors are the table
        // rows between those same two anchors. Reconstructing that interleave needs the
        // original position, which selecting the two classes into separate vectors throws
        // away. See re/demo-re/16-const-baselines.md.
        std::size_t mapOrdinal{};
        // RETAIL'S OWN ENTITY NUMBER FOR THIS ENTITY, walked out of the map entity
        // string. See SV_AssignMapEntityNumbers and
        // re/demo-re/19-entity-numbering-and-triggers.md. Zero when the walk did not
        // run.
        std::uint32_t walkEntityNum{};
        std::string modelName;
        std::array<float, 3> origin{};
        std::array<float, 3> angles{};
        float scale{ 1.0f };
        std::string scriptGameObjectName;
        std::string targetName;
        std::string destructibleType;
        bool regularMultiplayerEligible{ true };

        std::string noteworthy;

        bool operator==(const SvMapScriptModelSpawn &) const = default;
    };

    struct SvMiniMapCorners
    {
        std::array<float, 2> northWest{};
        std::array<float, 2> southEast{};

        bool operator==(const SvMiniMapCorners &) const = default;
    };

    struct SvSdBombSite
    {
        std::string label;
        std::string target;
        std::uint32_t triggerModel{};
        std::uint32_t defuseTriggerModel{};
        std::array<float, 3> origin{};
        std::array<float, 3> angles{};
        std::array<float, 3> defuseOrigin{};
        std::array<float, 3> defuseAngles{};

        bool operator==(const SvSdBombSite &) const = default;
    };

    struct SvSdBombPickup
    {
        std::uint32_t triggerModel{};
        std::array<float, 3> triggerOrigin{};
        std::string visualModelName;
        std::string visualTargetName;
        std::array<float, 3> visualOrigin{};
        std::array<float, 3> visualAngles{};

        bool operator==(const SvSdBombPickup &) const = default;
    };

    [[nodiscard]] std::optional<std::vector<SvMapEntity>> SV_ParseMapEntities(
        std::string_view text);
    // Select the cargoship-style mission records that scripts need to address:
    // actor spawners, triggers, volumes, script structs/origins, and the story
    // player start. Visual script_model/script_brushmodel records already have
    // live SvGameEntity owners and are intentionally not duplicated here.
    [[nodiscard]] std::optional<std::vector<SvLogicalMapEntityDefinition>>
        SV_SelectLogicalMapEntities(std::span<const SvMapEntity> entities);
    // THE END-OF-MATCH CAMERA, which is a map entity and not a dvar or a UI
    // property. `script_struct` with targetname "top_players_camera"; three
    // more named "top_players_loc" carry script_index 0/1/2 and are where the
    // three figures stand, facing it (their yaw is the camera's + 180 on both
    // maps checked). Section 121 measured the camera against the dm demo's own
    // playerState and they agree to the stored decimal.
    [[nodiscard]] std::optional<SvSpawnPoint> SV_SelectTopPlayersCamera(
        std::span<const SvMapEntity> entities);
    // The podium PLACES, ordered by script_index 0/1/2 -- first, second, third.
    // Ordering matters and the mapents do NOT supply it: mp_cross_fire lists
    // script_index 1, then 2, then 0.
    [[nodiscard]] std::vector<SvSpawnPoint> SV_SelectTopPlayersPlaces(
        std::span<const SvMapEntity> entities);
    [[nodiscard]] std::optional<SvSpawnPoint> SV_SelectInitialSpawn(
        std::span<const SvMapEntity> entities,
        std::string_view gameType);
    [[nodiscard]] std::optional<SvSpawnPoint> SV_SelectConnectionSpawn(
        std::span<const SvMapEntity> entities);
    [[nodiscard]] std::optional<std::vector<SvModeSpawnPoint>>
        SV_SelectFactoryArrivalSpawns(std::span<const SvMapEntity> entities);
    [[nodiscard]] std::optional<std::vector<SvModeSpawnPoint>>
        SV_SelectModeSpawnPoints(
            std::span<const SvMapEntity> entities,
            std::string_view gameType);
    // Every distinct classname containing "spawn", with a count, ordered. The
    // base MP maps' entity strings are not in the shipped fastfiles, so which
    // spawn classes a real CODOL map carries cannot be read offline; this
    // reports it from a live load instead of leaving the names a guess.
    [[nodiscard]] std::vector<std::pair<std::string, std::size_t>>
        SV_SpawnClassNameCensus(std::span<const SvMapEntity> entities);
    // RETAIL'S ENTITY NUMBERING, WALKED OUT OF THE MAP ENTITY STRING.
    //
    //   numbers start at 37 and are handed out IN ENTITY-STRING ORDER to every entity
    //   except worldspawn and four classnames: node_pathnode, node_negotiation_begin,
    //   node_negotiation_end, script_struct
    //
    // That is the whole rule. Checked against zm_factory_sh's shipped const-baseline
    // table at 238/238 brush models and 133/133 script models. It is SOLVED, not
    // guessed: the 238 brush models have known numbers (the table stores each one's
    // `*N` and so does the entity string), which gives 237 gap equations in twenty
    // classname unknowns, and fitting them produces exactly this skip set.
    //
    // This replaces matching a script model to a table row BY ORIGIN, which cannot
    // separate the nine co-located pairs zm_factory_sh contains -- two identical
    // `face_identification_machine` at one point, three rack A/B pairs, and five
    // treasure-chest body/lid pairs, one of which lists the lid first. Origin plus
    // xmodel resolved those only if this server's model configstring band agreed with
    // retail's, which was never established. Position needs neither.
    //
    // Returns one number per entity in `entities`, by index; ZERO for an entity the
    // rule skips. See re/demo-re/19-entity-numbering-and-triggers.md.
    [[nodiscard]] std::vector<std::uint32_t> SV_AssignMapEntityNumbers(
        std::span<const SvMapEntity> entities);

    // THE zm ZONE / SPAWNER MODEL, READ OUT OF THE MAP ENTITY STRING ALONE.
    //
    //   info_volume  --target-->  script_struct group  --target-->  goal
    //    "player_volume"           "zombie_spawner"
    //    targetname = ZONE         origin + angles
    //
    // Measured across all four zm maps and it generalises with no exceptions:
    // factory 12 zones / 63 points, sumpf 11 / 74, prototype 3 / 41, asylum 9 / 38 --
    // 35 zones and 216 points, every origin present, every zone target resolving.
    // re/demo-re/21-zm-zones-and-spawners.md, extractor Tools/demo-re/zmzones.py.
    //
    // FAIL-CLOSED, and each rejection below is a contradiction the four shipped maps
    // never produce, so tripping one means the assumption is wrong and NOT that a map
    // is merely unusual: a player_volume with no targetname or no target, two volumes
    // giving one zone name two different groups, a group member that is not a
    // `script_struct` zombie spawner, or a zone whose group has no points at all.
    // Returning nullopt is deliberate -- a partly-parsed zone model would spawn
    // zombies in the wrong places rather than not at all.
    [[nodiscard]] std::optional<std::vector<SvZmZone>> SV_SelectZmZones(
        std::span<const SvMapEntity> entities);

    // EVERY BARRIER ON THE MAP, name-ordered so the result is stable.
    //
    // Groups `script_parameters "board"` brush models by `targetname` and joins each
    // group to the `node_negotiation_begin`/`_end` pair sharing its `pfNNN` prefix,
    // choosing the nearest such pair to the board centroid when a prefix has several.
    // A group with no matching pair is still returned, with `hasVault` false.
    //
    // Empty rather than null on a map with no boards: every zm map measured has some,
    // but an mp map legitimately has none and that is not a parse failure.
    [[nodiscard]] std::vector<SvZmBarrier> SV_SelectZmBarriers(
        std::span<const SvMapEntity> entities);

    // WHICH ZONE A POINT IS IN, or null. Tests every RESOLVED volume of every zone and
    // returns the first containing one; zones are name-ordered, so the answer is stable
    // for a given map and point. A volume whose bounds never resolved is skipped, so a
    // map that failed to resolve reports "no zone" rather than a wrong one.
    //
    // Zones can genuinely overlap in the source data. This returns the first match
    // rather than pretending the map has none -- see section 21b for how often the AABB
    // widens that overlap (0.41% of sampled points resolve to a different zone).
    // WHICH ZONES TOUCH WHICH, as a per-zone list of zone INDICES.
    //
    // Retail's wave director only ever spawns from the players' zone and the ones
    // next to it; a zombie from the far side of the map would spend the whole round
    // walking. There is no adjacency key in MapEnts -- the zones are volumes and
    // nothing declares a neighbour -- so this derives it from the shapes.
    //
    // Two zones are adjacent when any hull of one comes within `tolerance` of any
    // hull of the other on all three axes. The hull bounds are volume-local, so the
    // volume's own origin is added first, exactly as SV_ZmVolumeContains does.
    // Volumes whose hulls never resolved claim no space and so touch nothing.
    [[nodiscard]] std::vector<std::vector<std::size_t>> SV_ZmZoneAdjacency(
        std::span<const SvZmZone> zones, float tolerance = 64.0f);

    [[nodiscard]] const SvZmZone *SV_ZmZoneAt(
        std::span<const SvZmZone> zones,
        const std::array<float, 3> &point);

    // Is a point inside ONE volume -- inside ANY of its hulls, a hull being its box
    // AND every one of its slab planes. Exposed for testing the geometry directly.
    [[nodiscard]] bool SV_ZmVolumeContains(
        const SvZmZoneVolume &volume,
        const std::array<float, 3> &point);

    [[nodiscard]] std::optional<std::vector<SvMapBrushModelSpawn>>
        SV_SelectBrushModelSpawns(std::span<const SvMapEntity> entities);
    [[nodiscard]] std::optional<std::vector<SvMapScriptModelSpawn>>
        SV_SelectScriptModelSpawns(std::span<const SvMapEntity> entities);
    [[nodiscard]] std::optional<SvMiniMapCorners> SV_SelectMiniMapCorners(
        std::span<const SvMapEntity> entities,
        float northYawDegrees,
        float requiredMapAspectRatio = 1.0f);
    [[nodiscard]] std::optional<std::vector<SvSdBombSite>> SV_SelectSdBombSites(
        std::span<const SvMapEntity> entities);
    [[nodiscard]] std::optional<SvSdBombPickup> SV_SelectSdBombPickup(
        std::span<const SvMapEntity> entities);
}
