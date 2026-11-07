#include "sv_mapents_mp.hpp"

// For FirstDynamicServerEntityNum, which SV_AssignMapEntityNumbers starts the walk at.
#include "sv_entity_mp.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <cstddef>
#include <limits>
#include <map>
#include <numbers>

namespace CodolGameServer
{
    namespace
    {
        class EntityTextParser
        {
        public:
            explicit EntityTextParser(const std::string_view text)
                : text_(text)
            {
            }

            std::optional<std::vector<SvMapEntity>> parse()
            {
                std::vector<SvMapEntity> entities;
                skipWhitespace();
                while (cursor_ < text_.size())
                {
                    if (text_[cursor_++] != '{')
                        return std::nullopt;

                    SvMapEntity entity;
                    skipWhitespace();
                    while (cursor_ < text_.size() && text_[cursor_] != '}')
                    {
                        auto key = quotedString();
                        if (!key)
                            return std::nullopt;
                        skipWhitespace();
                        auto value = quotedString();
                        if (!value)
                            return std::nullopt;
                        entity.fields.emplace_back(std::move(*key), std::move(*value));
                        skipWhitespace();
                    }
                    if (cursor_ >= text_.size() || text_[cursor_++] != '}')
                        return std::nullopt;
                    entities.push_back(std::move(entity));
                    skipWhitespace();
                }
                return entities;
            }

        private:
            void skipWhitespace()
            {
                while (cursor_ < text_.size())
                {
                    const auto character = text_[cursor_];
                    if (character != ' ' && character != '\t' &&
                        character != '\r' && character != '\n')
                    {
                        break;
                    }
                    ++cursor_;
                }
            }

            std::optional<std::string> quotedString()
            {
                if (cursor_ >= text_.size() || text_[cursor_++] != '"')
                    return std::nullopt;
                std::string value;
                while (cursor_ < text_.size())
                {
                    const auto character = text_[cursor_++];
                    if (character == '"')
                        return value;
                    if (character == '\\' && cursor_ < text_.size() &&
                        (text_[cursor_] == '\\' || text_[cursor_] == '"'))
                    {
                        value.push_back(text_[cursor_++]);
                    }
                    else
                    {
                        value.push_back(character);
                    }
                }
                return std::nullopt;
            }

            std::string_view text_;
            std::size_t cursor_{};
        };

        std::optional<std::array<float, 3>> parseVector(const std::string_view text)
        {
            std::array<float, 3> result{};
            auto cursor = text.data();
            const auto end = text.data() + text.size();
            for (auto &value : result)
            {
                while (cursor < end && *cursor == ' ')
                    ++cursor;
                if (cursor == end)
                    return std::nullopt;
                const auto parsed = std::from_chars(cursor, end, value);
                if (parsed.ec != std::errc{} || parsed.ptr == cursor || !std::isfinite(value))
                    return std::nullopt;
                cursor = parsed.ptr;
            }
            while (cursor < end && *cursor == ' ')
                ++cursor;
            return cursor == end ? std::optional{ result } : std::nullopt;
        }

        std::optional<float> parsePositiveFloat(const std::string_view text)
        {
            float result{};
            const auto parsed = std::from_chars(
                text.data(), text.data() + text.size(), result);
            if (parsed.ec != std::errc{} ||
                parsed.ptr != text.data() + text.size() ||
                !std::isfinite(result) || result <= 0.0f)
            {
                return std::nullopt;
            }
            return result;
        }

        std::optional<SvSpawnPoint> spawnFromEntity(
            const SvMapEntity &entity,
            const std::string_view expectedClassName)
        {
            const auto className = entity.value("classname");
            const auto originText = entity.value("origin");
            if (!className || *className != expectedClassName || !originText)
                return std::nullopt;
            const auto origin = parseVector(*originText);
            if (!origin)
                return std::nullopt;

            std::array<float, 3> angles{};
            if (const auto anglesText = entity.value("angles"))
            {
                const auto parsed = parseVector(*anglesText);
                if (!parsed)
                    return std::nullopt;
                angles = *parsed;
            }
            else if (const auto angleText = entity.value("angle"))
            {
                const auto parsed = parseVector(std::string("0 ") +
                    std::string(*angleText) + " 0");
                if (!parsed)
                    return std::nullopt;
                angles = *parsed;
            }
            return SvSpawnPoint{
                .className = std::string(*className),
                .origin = *origin,
                .angles = angles,
            };
        }

        std::optional<std::uint32_t> parseBrushModel(
            const std::string_view text)
        {
            if (text.size() < 2 || text.front() != '*')
                return std::nullopt;
            std::uint32_t result{};
            const auto parsed = std::from_chars(
                text.data() + 1, text.data() + text.size(), result);
            if (parsed.ec != std::errc{} || parsed.ptr != text.data() + text.size() ||
                result == 0 || result > std::numeric_limits<std::uint16_t>::max())
            {
                return std::nullopt;
            }
            return result;
        }

        std::optional<std::uint32_t> parseTriggerModel(
            const std::string_view text)
        {
            if (text.size() < 2 || text.front() != '?')
                return std::nullopt;
            std::uint32_t result{};
            const auto parsed = std::from_chars(
                text.data() + 1, text.data() + text.size(), result);
            if (parsed.ec != std::errc{} ||
                parsed.ptr != text.data() + text.size() ||
                result == 0 ||
                result > std::numeric_limits<std::uint16_t>::max())
            {
                return std::nullopt;
            }
            return result;
        }

        std::optional<std::array<float, 3>> entityAngles(
            const SvMapEntity &entity)
        {
            if (const auto anglesText = entity.value("angles"))
                return parseVector(*anglesText);
            if (const auto angleText = entity.value("angle"))
            {
                return parseVector(
                    std::string("0 ") + std::string(*angleText) + " 0");
            }
            return std::array<float, 3>{};
        }

        std::optional<bool> regularMultiplayerEligibility(
            const SvMapEntity &entity)
        {
            auto eligible = true;
            if (const auto specialOps = entity.value("script_specialops"))
            {
                if (*specialOps == "1")
                    eligible = false;
                else if (*specialOps != "0")
                    return std::nullopt;
            }
            if (entity.value("script_specialopsname"))
                eligible = false;
            return eligible;
        }

        std::optional<SvMapBrushModelSpawn> brushModelFromEntity(
            const SvMapEntity &entity)
        {
            const auto modelText = entity.value("model");
            const auto originText = entity.value("origin");
            if (!modelText || !originText)
                return std::nullopt;
            const auto clipHandle = parseBrushModel(*modelText);
            const auto origin = parseVector(*originText);
            if (!clipHandle || !origin)
                return std::nullopt;

            const auto angles = entityAngles(entity);
            const auto regularMultiplayerEligible =
                regularMultiplayerEligibility(entity);
            if (!angles || !regularMultiplayerEligible)
                return std::nullopt;

            return SvMapBrushModelSpawn{
                .clipHandle = *clipHandle,
                .origin = *origin,
                .angles = *angles,
                .scriptGameObjectName =
                    std::string(entity.value("script_gameobjectname").value_or("")),
                .targetName = std::string(entity.value("targetname").value_or("")),
                .destructibleType =
                    std::string(entity.value("destructible_type").value_or("")),
                .regularMultiplayerEligible = *regularMultiplayerEligible,
            };
        }

        std::optional<SvMapScriptModelSpawn> scriptModelFromEntity(
            const SvMapEntity &entity)
        {
            const auto modelName = entity.value("model");
            const auto originText = entity.value("origin");
            if (!modelName || modelName->empty() || modelName->front() == '*' ||
                modelName->find('\0') != std::string_view::npos || !originText)
            {
                return std::nullopt;
            }
            const auto origin = parseVector(*originText);
            const auto angles = entityAngles(entity);
            const auto regularMultiplayerEligible =
                regularMultiplayerEligibility(entity);
            if (!origin || !angles || !regularMultiplayerEligible)
                return std::nullopt;

            auto scale = 1.0f;
            if (const auto scaleText = entity.value("modelscale"))
            {
                const auto parsed = parsePositiveFloat(*scaleText);
                if (!parsed)
                    return std::nullopt;
                scale = *parsed;
            }

            return SvMapScriptModelSpawn{
                .modelName = std::string(*modelName),
                .origin = *origin,
                .angles = *angles,
                .scale = scale,
                .scriptGameObjectName =
                    std::string(entity.value("script_gameobjectname").value_or("")),
                .targetName = std::string(entity.value("targetname").value_or("")),
                .destructibleType =
                    std::string(entity.value("destructible_type").value_or("")),
                .regularMultiplayerEligible = *regularMultiplayerEligible,
                .noteworthy = std::string(entity.value("script_noteworthy").value_or("")),
            };
        }
    }

    std::optional<std::string_view> SvMapEntity::value(const std::string_view key) const
    {
        for (auto field = fields.rbegin(); field != fields.rend(); ++field)
        {
            if (field->first == key)
                return field->second;
        }
        return std::nullopt;
    }

    std::optional<std::string_view> SvLogicalMapEntityDefinition::value(
        const std::string_view key) const
    {
        for (auto field = fields.rbegin(); field != fields.rend(); ++field)
        {
            if (field->first == key)
                return field->second;
        }
        return std::nullopt;
    }

    std::optional<std::vector<SvMapEntity>> SV_ParseMapEntities(const std::string_view text)
    {
        return EntityTextParser(text).parse();
    }

    std::optional<std::vector<SvLogicalMapEntityDefinition>>
        SV_SelectLogicalMapEntities(const std::span<const SvMapEntity> entities)
    {
        const auto isLogicalClass = [](const std::string_view className) {
            return className.starts_with("actor_") ||
                className.starts_with("trigger_") ||
                className.starts_with("script_vehicle_") ||
                className == "info_volume" ||
                className == "script_struct" ||
                className == "script_origin" ||
                className == "info_player_start_so";
        };
        std::vector<SvLogicalMapEntityDefinition> result;
        for (std::size_t ordinal{}; ordinal < entities.size(); ++ordinal)
        {
            const auto &entity = entities[ordinal];
            const auto className = entity.value("classname");
            if (!className || !isLogicalClass(*className))
                continue;

            SvLogicalMapEntityDefinition definition{
                .mapOrdinal = ordinal,
                .fields = entity.fields,
            };
            if (const auto originText = entity.value("origin"))
            {
                const auto origin = parseVector(*originText);
                if (!origin)
                    return std::nullopt;
                definition.origin = *origin;
                definition.hasOrigin = true;
            }
            if (entity.value("angles") || entity.value("angle"))
            {
                const auto angles = entityAngles(entity);
                if (!angles)
                    return std::nullopt;
                definition.angles = *angles;
                definition.hasAngles = true;
            }
            result.push_back(std::move(definition));
        }
        return result;
    }

    std::optional<SvSpawnPoint> SV_SelectTopPlayersCamera(
        const std::span<const SvMapEntity> entities)
    {
        // Matched on TARGETNAME, not classname: the classname is
        // `script_struct`, which mp_cross_fire alone carries 89 of. The
        // targetname is unique on both maps checked.
        for (const auto &entity : entities)
        {
            const auto targetName = entity.value("targetname");
            if (!targetName || *targetName != "top_players_camera")
                continue;
            if (auto camera = spawnFromEntity(entity, "script_struct"))
                return camera;
        }
        return std::nullopt;
    }

    std::vector<SvSpawnPoint> SV_SelectTopPlayersPlaces(
        const std::span<const SvMapEntity> entities)
    {
        // script_index is "0"/"1"/"2" in every map checked, so compare the string
        // rather than parse it -- there is no third form to be liberal about, and
        // a silent parse failure here would put third place on the winner's
        // plinth.
        std::array<std::optional<SvSpawnPoint>, 3> byPlace{};
        for (const auto &entity : entities)
        {
            const auto targetName = entity.value("targetname");
            if (!targetName || *targetName != "top_players_loc")
                continue;
            const auto scriptIndex = entity.value("script_index");
            if (!scriptIndex)
                continue;
            std::size_t place{};
            if (*scriptIndex == "0")
                place = 0;
            else if (*scriptIndex == "1")
                place = 1;
            else if (*scriptIndex == "2")
                place = 2;
            else
                continue;
            if (byPlace[place])
                continue;
            byPlace[place] = spawnFromEntity(entity, "script_struct");
        }
        // Stop at the first gap rather than closing it up: place 2 standing where
        // place 1 should be is a wrong podium, and an empty one is not.
        std::vector<SvSpawnPoint> ordered;
        for (const auto &place : byPlace)
        {
            if (!place)
                break;
            ordered.push_back(*place);
        }
        return ordered;
    }

    std::optional<SvSpawnPoint> SV_SelectInitialSpawn(
        const std::span<const SvMapEntity> entities,
        const std::string_view gameType)
    {
        if (gameType.empty())
            return std::nullopt;

        // Team assignment is not recovered yet; use the attacker side as the
        // deterministic initial single-player role for team-based modes.
        // `_so` IS THE SPECIAL-OPS / CAMPAIGN SPAWN AND IT IS THE ONLY ONE A
        // COOP LEVEL HAS. Counted in coop_training_mp_cargoship's own decrypted
        // zone: worldspawn x1, info_player_start_so x1, trigger_multiple_spawn x2
        // -- no `info_player_start`, no mp_*_spawn of any kind. Without it the
        // selector returned nullopt and the server logged
        // `spawn refused ... NO_SPAWN_POINT`, which reaches the player as a
        // loaded map with no weapon and no viewhands. HANDOFF section 152t.
        // THE `mp_<gametype>_spawn` FORM DOES NOT EXIST FOR MOST TOKENS. Counted in
        // mp_deathmarch_chap1's own decrypted zone: mp_dm_spawn, mp_tdm_spawn,
        // mp_tdm_spawn_allies_start, mp_tdm_spawn_axis_start, worldspawn -- and no
        // mp_zhunt_spawn, no info_player_start of either kind. With only the four
        // gametype-derived names the selector returned nullopt and the server logged
        // `world spawn pending stage=initial_spawn_select` then
        // `spawn refused ... NO_SPAWN_POINT`. HANDOFF section 152w.
        //
        // Fall back to the stock deathmatch and team-deathmatch classes, which every
        // MP-derived map carries whatever mode it is played as.
        const std::array<std::string, 6> classNames{
            "mp_" + std::string(gameType) + "_spawn_attacker",
            "mp_" + std::string(gameType) + "_spawn",
            "info_player_start",
            "info_player_start_so",
            "mp_dm_spawn",
            "mp_tdm_spawn",
        };
        for (const auto &className : classNames)
        {
            for (const auto &entity : entities)
            {
                if (auto spawn = spawnFromEntity(entity, className))
                    return spawn;
            }
        }
        return std::nullopt;
    }

    std::optional<SvSpawnPoint> SV_SelectConnectionSpawn(
        const std::span<const SvMapEntity> entities)
    {
        for (const auto &className :
             { "info_player_start", "info_player_start_so" })
        {
            for (const auto &entity : entities)
            {
                if (auto spawn = spawnFromEntity(entity, className))
                    return spawn;
            }
        }
        return std::nullopt;
    }

    // CODREF(factory-arrival): Factory MapEnts records81..84 name the four
    // initial_spawn_points. Original solo20250 relocates to23,99,94.125;
    // delta-yaw105 agrees with record81's angles0,105,0. Its authored Z120
    // must still pass the native ground trace; it is not the player's feet Z.
    // OLMOD(factory-arrival-selection): preserve map order; multiplayer slot
    // assignment is reconstructed, not recovered original server scripting.
    std::optional<std::vector<SvModeSpawnPoint>> SV_SelectFactoryArrivalSpawns(
        const std::span<const SvMapEntity> entities)
    {
        std::vector<SvModeSpawnPoint> result;
        std::array<bool,4> identifiers{};
        for (const auto &entity : entities)
        {
            if (entity.value("targetname") != "initial_spawn_points") continue;
            const auto id = entity.value("script_int");
            const auto spawn = spawnFromEntity(entity,"script_struct");
            if (!spawn || !entity.value("angles") || !id || id->size()!=1 ||
                (*id)[0]<'1' || (*id)[0]>'4') return std::nullopt;
            const auto index=static_cast<std::size_t>((*id)[0]-'1');
            if (identifiers[index]) return std::nullopt;
            identifiers[index]=true;
            result.push_back({.spawn=*spawn,.team=SvSpawnTeam::Any});
        }
        if(result.size()!=4) return std::nullopt;
        return result;
    }

    std::optional<std::vector<SvModeSpawnPoint>> SV_SelectModeSpawnPoints(
        const std::span<const SvMapEntity> entities,
        const std::string_view gameType)
    {
        if (gameType.empty())
            return std::nullopt;

        std::vector<SvModeSpawnPoint> result;
        const auto appendClass = [&](const std::string_view className,
                                     const SvSpawnTeam team) {
            for (const auto &entity : entities)
            {
                if (auto spawn = spawnFromEntity(entity, className))
                {
                    result.push_back({
                        .spawn = std::move(*spawn),
                        .team = team,
                    });
                }
            }
        };

        if (gameType == "sd")
        {
            appendClass("mp_sd_spawn_attacker", SvSpawnTeam::Tf);
            appendClass("mp_sd_spawn_defender", SvSpawnTeam::Sc);
        }
        else if (gameType == "cha")
        {
            // CODOL Charge uses the team start sets as fixed respawn pools.
            // Dynamic TDM spawn scoring remains a separate gametype primitive.
            appendClass("mp_tdm_spawn_allies_start", SvSpawnTeam::Tf);
            appendClass("mp_tdm_spawn_axis_start", SvSpawnTeam::Sc);
        }
        else if (gameType == "dm" || gameType == "dmz" || gameType == "zm" ||
            gameType == "zhunt" || gameType == "zarena" || gameType == "td" ||
            gameType == "coop")
        {
            // Free-for-all has no sides, so the whole set is one pool and every
            // point is available to everyone - which is what SvSpawnTeam::Any
            // means to the selector.
            //
            // THE ASSET GAMETYPE AND THE RULES GAMETYPE ARE NOT THE SAME THING
            // (section 152n). The token picks which FASTFILES load and must match what
            // the client's playlist loaded, or the level checksum rejects the
            // join. The RULES come from gametypes/<token>.lua, and dmz and zm
            // are both served with a COPY of dm.lua -- so for spawning they are
            // deathmatch and draw from the same pool.
            //
            // Listing them here is what turns a single fallback point into the
            // whole set. Measured on mp_battlecity: the map carries
            // mp_dm_spawn x18 and mp_tdm_spawn x18, this chain did not match
            // "dmz", the selector fell through to SV_SelectInitialSpawn and
            // logged "selected 1 from info_player_start", and the player
            // spawned UNDER the map.
            appendClass("mp_dm_spawn", SvSpawnTeam::Any);
        }

        if (!result.empty())
            return result;

        const auto fallback = SV_SelectInitialSpawn(entities, gameType);
        if (!fallback)
            return std::nullopt;
        result.push_back({
            .spawn = *fallback,
            .team = SvSpawnTeam::Any,
        });
        return result;
    }

    std::vector<std::pair<std::string, std::size_t>> SV_SpawnClassNameCensus(
        const std::span<const SvMapEntity> entities)
    {
        std::vector<std::pair<std::string, std::size_t>> result;
        for (const auto &entity : entities)
        {
            // player_start too: info_player_start carries no "spawn" in its name
            // and is exactly the class whose absence blocked a map, so a census
            // that cannot show it missing is not much of a census.
            const auto className = entity.value("classname");
            if (!className || (className->find("spawn") == std::string_view::npos &&
                    className->find("player_start") == std::string_view::npos))
            {
                continue;
            }
            const auto found = std::ranges::find(
                result, *className, &std::pair<std::string, std::size_t>::first);
            if (found == result.end())
                result.emplace_back(std::string(*className), 1);
            else
                ++found->second;
        }
        std::ranges::sort(result);
        return result;
    }

    std::vector<std::uint32_t> SV_AssignMapEntityNumbers(
        const std::span<const SvMapEntity> entities)
    {
        // The four classnames that do NOT consume a number. Everything else does --
        // info_volume, trigger_use, trigger_multiple, script_origin and the actor
        // spawners included, all of which the fit assigns a weight of 1.
        static constexpr std::string_view Skipped[]{
            "node_pathnode",
            "node_negotiation_begin",
            "node_negotiation_end",
            "script_struct",
            // From zm_asylum_sh, the only one of the four zm maps carrying any:
            // fitting the rule against its own 193 brush anchors predicts 192 of 192
            // gaps with zero error and differs in exactly this classname, 15 of them,
            // with the walk running exactly 15 ahead without it.
            "info_vehicle_node",
        };
        std::vector<std::uint32_t> numbers(entities.size(), 0u);
        auto next = FirstDynamicServerEntityNum;
        for (std::size_t index = 0; index < entities.size(); ++index)
        {
            const auto className = entities[index].value("classname");
            if (!className || *className == "worldspawn")
                continue;
            if (std::ranges::find(Skipped, *className) != std::ranges::end(Skipped))
                continue;
            numbers[index] = next++;
        }
        return numbers;
    }

    std::optional<std::vector<SvMapBrushModelSpawn>>
        SV_SelectBrushModelSpawns(const std::span<const SvMapEntity> entities)
    {
        std::vector<SvMapBrushModelSpawn> result;
        const auto numbers = SV_AssignMapEntityNumbers(entities);
        std::size_t ordinal{};
        for (const auto &entity : entities)
        {
            const auto className = entity.value("classname");
            ++ordinal;
            if (!className || *className != "script_brushmodel")
                continue;
            auto spawn = brushModelFromEntity(entity);
            if (!spawn)
                return std::nullopt;
            // ordinal - 1: the position of THIS entity, counted over the whole
            // list so the two classes share one axis.
            spawn->mapOrdinal = ordinal - 1;
            spawn->walkEntityNum = numbers[ordinal - 1];
            result.push_back(*spawn);
        }
        return result;
    }

    std::optional<std::vector<SvMapScriptModelSpawn>>
        SV_SelectScriptModelSpawns(const std::span<const SvMapEntity> entities)
    {
        std::vector<SvMapScriptModelSpawn> result;
        const auto numbers = SV_AssignMapEntityNumbers(entities);
        std::size_t ordinal{};
        for (const auto &entity : entities)
        {
            const auto className = entity.value("classname");
            ++ordinal;
            if (!className || *className != "script_model")
                continue;
            auto spawn = scriptModelFromEntity(entity);
            if (!spawn)
                return std::nullopt;
            // ordinal - 1: the position of THIS entity, counted over the whole
            // list so the two classes share one axis.
            spawn->mapOrdinal = ordinal - 1;
            spawn->walkEntityNum = numbers[ordinal - 1];
            result.push_back(*spawn);
        }
        return result;
    }

    std::optional<SvMiniMapCorners> SV_SelectMiniMapCorners(
        const std::span<const SvMapEntity> entities,
        const float northYawDegrees,
        const float requiredMapAspectRatio)
    {
        if (!std::isfinite(northYawDegrees) ||
            !std::isfinite(requiredMapAspectRatio) || requiredMapAspectRatio < 0.0f)
        {
            return std::nullopt;
        }

        std::array<std::array<float, 2>, 2> corners{};
        std::size_t cornerCount{};
        for (const auto &entity : entities)
        {
            if (entity.value("targetname") !=
                std::optional<std::string_view>{ "minimap_corner" })
            {
                continue;
            }
            const auto originText = entity.value("origin");
            const auto origin = originText ? parseVector(*originText) : std::nullopt;
            if (!origin || cornerCount >= corners.size())
                return std::nullopt;
            corners[cornerCount++] = { (*origin)[0], (*origin)[1] };
        }
        if (cornerCount != corners.size())
            return std::nullopt;

        const auto radians = northYawDegrees *
            std::numbers::pi_v<float> / 180.0f;
        const std::array north{ std::cos(radians), std::sin(radians) };
        const std::array west{ -north[1], north[0] };
        const std::array difference{
            corners[1][0] - corners[0][0],
            corners[1][1] - corners[0][1],
        };
        const auto dot = [](const auto &left, const auto &right) {
            return left[0] * right[0] + left[1] * right[1];
        };
        const auto northDistance = dot(difference, north);
        SvMiniMapCorners result;
        if (dot(difference, west) > 0.0f)
        {
            if (northDistance > 0.0f)
            {
                result.northWest = corners[1];
                result.southEast = corners[0];
            }
            else
            {
                const std::array side{
                    north[0] * northDistance,
                    north[1] * northDistance,
                };
                result.northWest = {
                    corners[1][0] - side[0], corners[1][1] - side[1] };
                result.southEast = {
                    corners[0][0] + side[0], corners[0][1] + side[1] };
            }
        }
        else if (northDistance > 0.0f)
        {
            const std::array side{
                north[0] * northDistance,
                north[1] * northDistance,
            };
            result.northWest = {
                corners[0][0] + side[0], corners[0][1] + side[1] };
            result.southEast = {
                corners[1][0] - side[0], corners[1][1] - side[1] };
        }
        else
        {
            result.northWest = corners[0];
            result.southEast = corners[1];
        }

        if (requiredMapAspectRatio > 0.0f)
        {
            const std::array diagonal{
                result.northWest[0] - result.southEast[0],
                result.northWest[1] - result.southEast[1],
            };
            const auto northPortion = dot(diagonal, north);
            const auto westPortion = dot(diagonal, west);
            if (northPortion <= 0.0f || westPortion <= 0.0f)
                return std::nullopt;
            const auto aspectRatio = westPortion / northPortion;
            const auto axis = aspectRatio < requiredMapAspectRatio ? west : north;
            const auto portion = aspectRatio < requiredMapAspectRatio
                ? westPortion : northPortion;
            const auto increase = aspectRatio < requiredMapAspectRatio
                ? requiredMapAspectRatio / aspectRatio
                : aspectRatio / requiredMapAspectRatio;
            const std::array addition{
                axis[0] * portion * (increase - 1.0f) * 0.5f,
                axis[1] * portion * (increase - 1.0f) * 0.5f,
            };
            for (std::size_t index = 0; index < addition.size(); ++index)
            {
                result.northWest[index] += addition[index];
                result.southEast[index] -= addition[index];
            }
        }
        return result;
    }

    std::optional<std::vector<SvSdBombSite>> SV_SelectSdBombSites(
        const std::span<const SvMapEntity> entities)
    {
        std::vector<SvSdBombSite> result;
        for (const auto &entity : entities)
        {
            if (entity.value("classname") !=
                    std::optional<std::string_view>{ "trigger_use_touch" } ||
                entity.value("targetname") !=
                    std::optional<std::string_view>{ "bombzone" } ||
                entity.value("script_gameobjectname") !=
                    std::optional<std::string_view>{ "bombzone" })
            {
                continue;
            }
            if (entity.value("script_bombmode_original") !=
                    std::optional<std::string_view>{ "1" })
            {
                continue;
            }
            const auto specialOps = entity.value("script_specialops");
            if (specialOps && *specialOps != "0")
                continue;
            const auto label = entity.value("script_label");
            const auto target = entity.value("target");
            const auto model = entity.value("model");
            const auto originText = entity.value("origin");
            const auto triggerModel = model
                ? parseTriggerModel(*model)
                : std::nullopt;
            const auto origin = originText
                ? parseVector(*originText)
                : std::nullopt;
            const auto angles = entityAngles(entity);
            if (!label || (*label != "_a" && *label != "_b") ||
                !target || target->empty() ||
                target->find('\0') != std::string_view::npos ||
                !triggerModel || !origin || !angles)
            {
                return std::nullopt;
            }
            if (std::ranges::any_of(result, [label](const SvSdBombSite &site) {
                    return site.label == *label;
                }))
            {
                return std::nullopt;
            }

            const auto visualMatches = [&](const SvMapEntity &candidate) {
                    return candidate.value("classname") ==
                            std::optional<std::string_view>{ "script_model" } &&
                        candidate.value("targetname") == target &&
                        candidate.value("script_gameobjectname") ==
                            std::optional<std::string_view>{ "bombzone" } &&
                        regularMultiplayerEligibility(candidate) == true;
                };
            const auto visual = std::ranges::find_if(entities, visualMatches);
            if (visual == entities.end())
                return std::nullopt;
            if (std::ranges::find_if(std::next(visual), entities.end(),
                    visualMatches) != entities.end())
            {
                return std::nullopt;
            }
            const auto defuseTarget = visual->value("target");
            if (!defuseTarget || defuseTarget->empty())
                return std::nullopt;
            const auto defuseMatches = [&](const SvMapEntity &candidate) {
                    return candidate.value("classname") ==
                            std::optional<std::string_view>{ "trigger_use_touch" } &&
                        candidate.value("targetname") == defuseTarget &&
                        candidate.value("script_gameobjectname") ==
                            std::optional<std::string_view>{ "bombzone" } &&
                        regularMultiplayerEligibility(candidate) == true;
                };
            const auto defuseTrigger =
                std::ranges::find_if(entities, defuseMatches);
            if (defuseTrigger == entities.end())
                return std::nullopt;
            if (std::ranges::find_if(std::next(defuseTrigger), entities.end(),
                    defuseMatches) != entities.end())
            {
                return std::nullopt;
            }
            const auto defuseModelText = defuseTrigger->value("model");
            const auto defuseOriginText = defuseTrigger->value("origin");
            const auto defuseModel = defuseModelText
                ? parseTriggerModel(*defuseModelText)
                : std::nullopt;
            const auto defuseOrigin = defuseOriginText
                ? parseVector(*defuseOriginText)
                : std::nullopt;
            const auto defuseAngles = entityAngles(*defuseTrigger);
            if (!defuseModel || !defuseOrigin || !defuseAngles)
                return std::nullopt;
            result.push_back({
                .label = std::string(*label),
                .target = std::string(*target),
                .triggerModel = *triggerModel,
                .defuseTriggerModel = *defuseModel,
                .origin = *origin,
                .angles = *angles,
                .defuseOrigin = *defuseOrigin,
                .defuseAngles = *defuseAngles,
            });
        }
        if (result.size() != 2)
            return std::nullopt;
        std::ranges::sort(result, {}, &SvSdBombSite::label);
        if (result[0].label != "_a" || result[1].label != "_b")
            return std::nullopt;
        return result;
    }

    std::optional<SvSdBombPickup> SV_SelectSdBombPickup(
        const std::span<const SvMapEntity> entities)
    {
        std::optional<SvSdBombPickup> result;
        for (const auto &trigger : entities)
        {
            if (trigger.value("classname") !=
                    std::optional<std::string_view>{ "trigger_multiple" } ||
                trigger.value("targetname") !=
                    std::optional<std::string_view>{ "sd_bomb_pickup_trig" } ||
                trigger.value("script_gameobjectname") !=
                    std::optional<std::string_view>{ "sd" })
            {
                continue;
            }
            const auto triggerEligible = regularMultiplayerEligibility(trigger);
            if (!triggerEligible)
                return std::nullopt;
            if (!*triggerEligible)
                continue;
            if (result)
                return std::nullopt;
            const auto modelText = trigger.value("model");
            const auto originText = trigger.value("origin");
            const auto triggerModel = modelText
                ? parseTriggerModel(*modelText)
                : std::nullopt;
            const auto triggerOrigin = originText
                ? parseVector(*originText)
                : std::nullopt;
            if (!triggerModel || !triggerOrigin)
                return std::nullopt;

            const SvMapEntity *visual{};
            for (const auto &candidate : entities)
            {
                if (candidate.value("classname") !=
                        std::optional<std::string_view>{ "script_model" } ||
                    candidate.value("targetname") !=
                        std::optional<std::string_view>{ "sd_bomb" } ||
                    candidate.value("script_gameobjectname") !=
                        std::optional<std::string_view>{ "sd" } ||
                    regularMultiplayerEligibility(candidate) != true)
                {
                    continue;
                }
                if (visual)
                    return std::nullopt;
                visual = &candidate;
            }
            if (!visual)
                return std::nullopt;
            const auto visualModel = visual->value("model");
            const auto visualOriginText = visual->value("origin");
            const auto visualOrigin = visualOriginText
                ? parseVector(*visualOriginText)
                : std::nullopt;
            const auto visualAngles = entityAngles(*visual);
            if (!visualModel || visualModel->empty() ||
                visualModel->front() == '*' || visualModel->front() == '?' ||
                visualModel->find('\0') != std::string_view::npos ||
                !visualOrigin || !visualAngles)
            {
                return std::nullopt;
            }
            result = SvSdBombPickup{
                .triggerModel = *triggerModel,
                .triggerOrigin = *triggerOrigin,
                .visualModelName = std::string(*visualModel),
                .visualTargetName = std::string(*visual->value("targetname")),
                .visualOrigin = *visualOrigin,
                .visualAngles = *visualAngles,
            };
        }
        return result;
    }

    std::vector<SvZmBarrier> SV_SelectZmBarriers(
        const std::span<const SvMapEntity> entities)
    {
        // The `pfNNN` prefix is what joins a board group to its traversal. Everything
        // after the first underscore differs between the two -- factory's boards are
        // `pf678_auto1` and its negotiation pair is `pf678_auto2108` -- so the prefix
        // is the whole of the key.
        const auto prefixOf = [](const std::string_view name) {
            const auto cut = name.find('_');
            return cut == std::string_view::npos ? name : name.substr(0, cut);
        };

        // PASS 1 -- the boards, grouped by targetname.
        std::map<std::string, std::vector<SvZmBarrierBoard>> groups;
        for (const auto &entity : entities)
        {
            if (entity.value("script_parameters") != "board")
                continue;
            const auto name = entity.value("targetname");
            const auto modelText = entity.value("model");
            const auto originText = entity.value("origin");
            if (!name || name->empty() || !modelText || !originText)
                continue;
            const auto clipHandle = parseBrushModel(*modelText);
            const auto origin = parseVector(*originText);
            if (!clipHandle || !origin)
                continue;
            // `script_noteworthy` is the 1..6 slot. A board without one still counts as
            // a board -- the group is what matters -- so index 0 records "unslotted"
            // rather than dropping it and changing the count.
            std::uint32_t boardIndex{};
            if (const auto slot = entity.value("script_noteworthy"))
            {
                std::from_chars(slot->data(), slot->data() + slot->size(), boardIndex);
            }
            groups[std::string(*name)].push_back(SvZmBarrierBoard{
                .clipHandle = *clipHandle,
                .boardIndex = boardIndex,
                .origin = *origin,
            });
        }
        if (groups.empty())
            return {};

        // PASS 2 -- the traversals, indexed by prefix. A `begin` names its `end` in
        // `target`; both carry a position and the begin carries the animscript.
        struct Traversal
        {
            std::array<float, 3> outside{};
            std::array<float, 3> inside{};
            std::string animScript;
        };
        std::map<std::string, std::vector<Traversal>> traversals;
        std::map<std::string, std::array<float, 3>> ends;
        for (const auto &entity : entities)
        {
            if (entity.value("classname") != "node_negotiation_end")
                continue;
            const auto name = entity.value("targetname");
            const auto originText = entity.value("origin");
            if (!name || !originText)
                continue;
            if (const auto origin = parseVector(*originText))
                ends.emplace(std::string(*name), *origin);
        }
        for (const auto &entity : entities)
        {
            if (entity.value("classname") != "node_negotiation_begin")
                continue;
            const auto target = entity.value("target");
            const auto originText = entity.value("origin");
            if (!target || !originText)
                continue;
            const auto found = ends.find(std::string(*target));
            const auto origin = parseVector(*originText);
            if (found == ends.end() || !origin)
                continue;
            traversals[std::string(prefixOf(*target))].push_back(Traversal{
                .outside = *origin,
                .inside = found->second,
                .animScript = std::string(entity.value("animscript").value_or("")),
            });
        }

        // PASS 3 -- join. Nearest traversal of the matching prefix to the board
        // centroid, which is the median-27-unit relationship the census measured.
        std::vector<SvZmBarrier> result;
        result.reserve(groups.size());
        for (auto &[name, boards] : groups)
        {
            std::ranges::sort(boards, {}, &SvZmBarrierBoard::boardIndex);
            SvZmBarrier barrier{ .name = name, .boards = std::move(boards) };
            std::array<float, 3> centroid{};
            for (const auto &board : barrier.boards)
            {
                for (std::size_t axis = 0; axis < 3; ++axis)
                    centroid[axis] += board.origin[axis];
            }
            for (auto &axis : centroid)
                axis /= static_cast<float>(barrier.boards.size());

            const auto candidates = traversals.find(std::string(prefixOf(name)));
            if (candidates != traversals.end() && !candidates->second.empty())
            {
                const auto *best = &candidates->second.front();
                auto bestDistance = std::numeric_limits<float>::infinity();
                for (const auto &candidate : candidates->second)
                {
                    const auto dx = candidate.outside[0] - centroid[0];
                    const auto dy = candidate.outside[1] - centroid[1];
                    const auto distance = dx * dx + dy * dy;
                    if (distance >= bestDistance)
                        continue;
                    bestDistance = distance;
                    best = &candidate;
                }
                barrier.outside = best->outside;
                barrier.inside = best->inside;
                barrier.animScript = best->animScript;
                barrier.hasVault = true;
            }
            result.push_back(std::move(barrier));
        }
        return result;
    }

    std::optional<std::vector<SvZmZone>> SV_SelectZmZones(
        const std::span<const SvMapEntity> entities)
    {
        // PASS 1 -- the zones. Every `info_volume` carrying
        // `script_noteworthy "player_volume"` names a zone in `targetname` and its
        // spawner group in `target`. Several volumes share one zone name, so this
        // folds them and counts how many contributed.
        std::vector<SvZmZone> zones;
        for (const auto &entity : entities)
        {
            const auto className = entity.value("classname");
            const auto noteworthy = entity.value("script_noteworthy");
            if (!className || *className != "info_volume" ||
                !noteworthy || *noteworthy != "player_volume")
            {
                continue;
            }
            const auto name = entity.value("targetname");
            const auto group = entity.value("target");
            // A player_volume with no name or no group cannot be placed. All 132
            // player_volumes across the four zm maps carry both.
            if (!name || name->empty() || !group || group->empty())
                return std::nullopt;

            // The volume's own identity and position. The SHAPE is not here -- the
            // entity string has none -- so bounds stay zeroed until world spawn
            // resolves the `?N` against the engine.
            const auto modelText = entity.value("model");
            if (!modelText)
                return std::nullopt;
            const auto triggerModel = parseTriggerModel(*modelText);
            const auto originText = entity.value("origin");
            if (!triggerModel || !originText)
                return std::nullopt;
            const auto origin = parseVector(*originText);
            if (!origin)
                return std::nullopt;
            const SvZmZoneVolume volume{
                .triggerModel = *triggerModel,
                .origin = *origin,
            };

            auto existing = std::ranges::find_if(
                zones, [&name](const SvZmZone &zone) { return zone.name == *name; });
            if (existing == zones.end())
            {
                zones.push_back(SvZmZone{
                    .name = std::string(*name),
                    .spawnerGroup = std::string(*group),
                    .volumes = { volume },
                });
                continue;
            }
            // Two volumes claiming one zone name for DIFFERENT groups is a
            // contradiction this parse cannot resolve, not a merge to paper over.
            if (existing->spawnerGroup != *group)
                return std::nullopt;
            existing->volumes.push_back(volume);
        }
        if (zones.empty())
            return std::nullopt;

        // PASS 2 -- the spawn points. A group member is a `script_struct` whose
        // `targetname` is the group name and which carries a zombie-spawner
        // noteworthy. `zombie_dog_spawner` is admitted alongside `zombie_spawner`
        // because zm_factory_sh carries a dog spawner and nothing here needs to
        // separate them yet.
        for (const auto &entity : entities)
        {
            const auto targetName = entity.value("targetname");
            if (!targetName || targetName->empty())
                continue;
            auto zone = std::ranges::find_if(
                zones,
                [&targetName](const SvZmZone &candidate) {
                    return candidate.spawnerGroup == *targetName;
                });
            if (zone == zones.end())
                continue;

            const auto className = entity.value("classname");
            const auto noteworthy = entity.value("script_noteworthy");
            if (!className || *className != "script_struct" || !noteworthy ||
                (*noteworthy != "zombie_spawner" && *noteworthy != "zombie_dog_spawner"))
            {
                // Something other than a zombie spawn point is answering to a
                // spawner-group name. Across the four zm maps every one of the 216
                // group members is a `script_struct` zombie spawner, so this is a
                // broken assumption rather than an odd map.
                return std::nullopt;
            }

            const auto originText = entity.value("origin");
            if (!originText)
                return std::nullopt;
            const auto origin = parseVector(*originText);
            if (!origin)
                return std::nullopt;

            std::array<float, 3> angles{};
            if (const auto anglesText = entity.value("angles"))
            {
                const auto parsed = parseVector(*anglesText);
                if (!parsed)
                    return std::nullopt;
                angles = *parsed;
            }

            // The goal is OPTIONAL by measurement -- see the struct comment.
            const auto goal = entity.value("target");
            zone->spawnPoints.push_back(SvZmSpawnPoint{
                .origin = *origin,
                .angles = angles,
                .goal = goal ? std::string(*goal) : std::string{},
            });
        }

        // RESOLVE EVERY GOAL NAME TO A POSITION. A second pass, because a
        // spawner can target a node that appears later in the entity list.
        //
        // MEASURED, zm_factory_sh MapEnts: 61 of its 69 `zombie_spawner`
        // structs carry a `target`, ALL 61 resolve, and every one resolves to
        // a `node_pathnode` -- the map's own AI navigation nodes -- 159 to 738
        // units away. That is retail's pathing data, not a choice made here.
        //
        // THE NAME ALONE WAS NOT USABLE. This struct's old comment called
        // `goal` "retail's navigation goal", but it is a NAME and the first
        // factory spawn point's reads `outside_up_spawners` -- a spawner GROUP.
        // It has to be resolved, never trusted as a destination.
        //
        // An unresolved goal stays ABSENT rather than defaulting: a zombie with
        // no goal must stand still, not walk to (0,0,0).
        for (auto &zone : zones)
        {
            for (auto &point : zone.spawnPoints)
            {
                if (point.goal.empty())
                    continue;
                for (const auto &candidate : entities)
                {
                    const auto name = candidate.value("targetname");
                    if (!name || *name != point.goal)
                        continue;
                    if (const auto goalOriginText = candidate.value("origin"))
                    {
                        if (const auto parsed = parseVector(*goalOriginText))
                        {
                            point.goalOrigin = *parsed;
                            point.hasGoalOrigin = true;
                        }
                    }
                    break;
                }
            }
        }

        // A zone that resolves to no spawn points would silently stop spawning in
        // that part of the map. All 35 zones across the four zm maps carry at least
        // two, so an empty one means the group name did not resolve.
        for (const auto &zone : zones)
        {
            if (zone.spawnPoints.empty())
                return std::nullopt;
        }
        std::ranges::sort(zones, {}, &SvZmZone::name);
        return zones;
    }

    bool SV_ZmVolumeContains(
        const SvZmZoneVolume &volume,
        const std::array<float, 3> &point)
    {
        if (!volume.hullsResolved)
            return false;
        // Hull bounds are VOLUME-LOCAL; the entity's own origin is where the shape
        // sits. No rotation: not one of the 132 player_volumes across the four zm maps
        // carries an `angles` key.
        const std::array<float, 3> local{
            point[0] - volume.origin[0],
            point[1] - volume.origin[1],
            point[2] - volume.origin[2],
        };
        for (const auto &hull : volume.hulls)
        {
            bool inside = true;
            for (std::size_t axis = 0; axis < 3 && inside; ++axis)
            {
                if (std::abs(local[axis] - hull.midpoint[axis]) > hull.halfSize[axis])
                    inside = false;
            }
            if (!inside)
                continue;
            // Then every slab. A hull with none is a plain box, which is the common
            // case: 19 of factory's 32 volumes and all 36 of asylum's.
            for (const auto &slab : hull.slabs)
            {
                const auto distance = local[0] * slab.direction[0] +
                    local[1] * slab.direction[1] + local[2] * slab.direction[2];
                if (std::abs(distance - slab.midPoint) > slab.halfSize)
                {
                    inside = false;
                    break;
                }
            }
            if (inside)
                return true;
        }
        return false;
    }

    std::vector<std::vector<std::size_t>> SV_ZmZoneAdjacency(
        const std::span<const SvZmZone> zones, const float tolerance)
    {
        struct Box
        {
            std::array<float, 3> low{};
            std::array<float, 3> high{};
        };
        std::vector<std::vector<Box>> boxes(zones.size());
        for (std::size_t index = 0; index < zones.size(); ++index)
        {
            for (const auto &volume : zones[index].volumes)
            {
                if (!volume.hullsResolved)
                    continue;
                for (const auto &hull : volume.hulls)
                {
                    Box box;
                    for (std::size_t axis = 0; axis < 3; ++axis)
                    {
                        const auto centre =
                            volume.origin[axis] + hull.midpoint[axis];
                        box.low[axis] = centre - hull.halfSize[axis];
                        box.high[axis] = centre + hull.halfSize[axis];
                    }
                    boxes[index].push_back(box);
                }
            }
        }
        const auto touches = [tolerance](const Box &a, const Box &b) {
            for (std::size_t axis = 0; axis < 3; ++axis)
            {
                if (a.low[axis] - tolerance > b.high[axis] ||
                    b.low[axis] - tolerance > a.high[axis])
                {
                    return false;
                }
            }
            return true;
        };
        std::vector<std::vector<std::size_t>> adjacency(zones.size());
        for (std::size_t left = 0; left < zones.size(); ++left)
        {
            for (std::size_t right = left + 1; right < zones.size(); ++right)
            {
                bool adjacent = false;
                for (const auto &a : boxes[left])
                {
                    for (const auto &b : boxes[right])
                    {
                        if (touches(a, b))
                        {
                            adjacent = true;
                            break;
                        }
                    }
                    if (adjacent)
                        break;
                }
                if (adjacent)
                {
                    adjacency[left].push_back(right);
                    adjacency[right].push_back(left);
                }
            }
        }
        return adjacency;
    }

    const SvZmZone *SV_ZmZoneAt(
        const std::span<const SvZmZone> zones,
        const std::array<float, 3> &point)
    {
        for (const auto &zone : zones)
        {
            for (const auto &volume : zone.volumes)
            {
                if (SV_ZmVolumeContains(volume, point))
                    return &zone;
            }
        }
        return nullptr;
    }
}
