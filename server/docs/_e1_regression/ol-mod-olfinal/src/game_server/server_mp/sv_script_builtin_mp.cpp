#include "sv_script_builtin_mp.hpp"

#include "sv_client_mp.hpp"
#include "sv_gamestate_mp.hpp"
#include <array>
#include <cmath>
#include <cstdlib>
#include <limits>
#include <string_view>
#include <utility>

namespace CodolGameServer
{
    namespace
    {
        SvScriptBuiltinResult success(SvScriptValue value)
        {
            return {
                .value = std::move(value),
            };
        }

        SvScriptBuiltinResult failure(
            const SvScriptBuiltinErrorCode code,
            std::string message)
        {
            return {
                .error = {
                    .code = code,
                    .message = std::move(message),
                },
            };
        }

        std::optional<SvScriptBuiltinResult> validatePlayerMethod(
            const SvServerWorld &world,
            const SvScriptBuiltinCall &call,
            const std::size_t expectedArgumentCount,
            std::optional<SvPlayerState> &playerState)
        {
            if (call.arguments.size() != expectedArgumentCount)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " received an invalid argument count");
            }
            if (!call.self)
            {
                return failure(
                    SvScriptBuiltinErrorCode::MissingSelf,
                    call.id.name + " requires a player object");
            }
            if (call.self->kind != SvScriptObjectKind::Player)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    call.id.name + " requires a player object");
            }

            playerState = world.playerState(call.self->id);
            const auto gameplayState = world.gameplayState(call.self->id);
            if (!playerState || !gameplayState)
            {
                return failure(
                    SvScriptBuiltinErrorCode::ObjectNotFound,
                    "player object does not exist");
            }
            if (*gameplayState != ClientGameplayState::Playing)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidObjectState,
                    "player object is not in Playing state");
            }
            return std::nullopt;
        }

        SvScriptBuiltinResult ammoMutationResult(
            const SvServerWorld::WeaponAmmoMutationResult result)
        {
            switch (result)
            {
            case SvServerWorld::WeaponAmmoMutationResult::Applied:
                return success(std::monostate{});
            case SvServerWorld::WeaponAmmoMutationResult::ClientNotFound:
                return failure(
                    SvScriptBuiltinErrorCode::ObjectNotFound,
                    "player object does not exist");
            case SvServerWorld::WeaponAmmoMutationResult::NotPlaying:
                return failure(
                    SvScriptBuiltinErrorCode::InvalidObjectState,
                    "player object is not in Playing state");
            case SvServerWorld::WeaponAmmoMutationResult::WeaponNotOwned:
                return failure(
                    SvScriptBuiltinErrorCode::WeaponNotOwned,
                    "player does not own the requested weapon");
            case SvServerWorld::WeaponAmmoMutationResult::AmmoStateMissing:
                return failure(
                    SvScriptBuiltinErrorCode::InvalidAmmoState,
                    "weapon ammo state is unavailable");
            }
            return failure(
                SvScriptBuiltinErrorCode::InvalidAmmoState,
                "weapon ammo mutation returned an invalid result");
        }

        std::optional<SvScriptBuiltinResult> readAmmoArguments(
            const SvScriptBuiltinCall &call,
            std::string_view &weaponName,
            std::int64_t &count)
        {
            const auto *weapon = std::get_if<std::string>(&call.arguments[0]);
            const auto *integer = std::get_if<std::int64_t>(&call.arguments[1]);
            if (!weapon || weapon->empty() || !integer)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    call.id.name + " expects a weapon name and integer count");
            }
            weaponName = *weapon;
            count = *integer;
            return std::nullopt;
        }


        // THE zm ZONE BUILTINS. re/demo-re/21-zm-zones-and-spawners.md.
        //
        // INDEX-BASED ON PURPOSE. SvScriptValue has no table or list-of-strings type,
        // so the script cannot be handed the zone model as a structure; it walks it
        // with a count and an index instead. Zones are ordered by name, so an index is
        // stable for a given map and a script may cache it within a round.
        std::optional<SvScriptBuiltinResult> readZmIndex(
            const SvScriptBuiltinCall &call,
            const std::size_t argument,
            const std::size_t limit,
            std::size_t &out)
        {
            const auto *integer =
                std::get_if<std::int64_t>(&call.arguments[argument]);
            if (!integer)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    call.id.name + " expects integer indices");
            }
            // ONE-BASED, because Lua is. A script that writes `for i = 1, count` is
            // reading the zone it thinks it is.
            if (*integer < 1 || static_cast<std::uint64_t>(*integer) > limit)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    call.id.name + " index " + std::to_string(*integer) +
                        " is outside 1.." + std::to_string(limit));
            }
            out = static_cast<std::size_t>(*integer) - 1;
            return std::nullopt;
        }

        std::optional<SvScriptBuiltinResult> zmZoneModel(
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider,
            std::vector<SvZmZone> &out)
        {
            if (!provider)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidObjectState,
                    call.id.name + " has no zone provider");
            }
            out = provider();
            return std::nullopt;
        }

        SvScriptBuiltinResult zmZoneCount(
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider)
        {
            std::vector<SvZmZone> zones;
            if (auto error = zmZoneModel(call, provider, zones))
                return *error;
            return success(static_cast<std::int64_t>(zones.size()));
        }

        SvScriptBuiltinResult zmZoneName(
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider)
        {
            if (call.arguments.size() != 1)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " expects a zone index");
            }
            std::vector<SvZmZone> zones;
            if (auto error = zmZoneModel(call, provider, zones))
                return *error;
            std::size_t zone{};
            if (auto error = readZmIndex(call, 0, zones.size(), zone))
                return *error;
            return success(zones[zone].name);
        }

        SvScriptBuiltinResult zmZoneSpawnCount(
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider)
        {
            if (call.arguments.size() != 1)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " expects a zone index");
            }
            std::vector<SvZmZone> zones;
            if (auto error = zmZoneModel(call, provider, zones))
                return *error;
            std::size_t zone{};
            if (auto error = readZmIndex(call, 0, zones.size(), zone))
                return *error;
            return success(
                static_cast<std::int64_t>(zones[zone].spawnPoints.size()));
        }

        SvScriptBuiltinResult zmZoneActive(
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider)
        {
            if (call.arguments.size() != 1)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " expects a zone index");
            }
            std::vector<SvZmZone> zones;
            if (auto error = zmZoneModel(call, provider, zones))
                return *error;
            std::size_t zone{};
            if (auto error = readZmIndex(call, 0, zones.size(), zone))
                return *error;
            return success(static_cast<std::int64_t>(zones[zone].active ? 1 : 0));
        }

        SvScriptBuiltinResult zmActiveZoneCount(
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider)
        {
            if (!call.arguments.empty())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " expects no arguments");
            }
            std::vector<SvZmZone> zones;
            if (auto error = zmZoneModel(call, provider, zones))
                return *error;
            return success(static_cast<std::int64_t>(std::ranges::count_if(
                zones, [](const SvZmZone &zone) { return zone.active; })));
        }

        // HOW MANY ZONES TOUCH THIS ONE. See SV_ZmZoneAdjacency for what "touch"
        // means -- it is derived from the volume hulls, because MapEnts declares no
        // neighbour relation of its own.
        SvScriptBuiltinResult zmZoneAdjacentCount(
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider)
        {
            if (call.arguments.size() != 1)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " expects a zone index");
            }
            std::vector<SvZmZone> zones;
            if (auto error = zmZoneModel(call, provider, zones))
                return *error;
            std::size_t zone{};
            if (auto error = readZmIndex(call, 0, zones.size(), zone))
                return *error;
            const auto adjacency = SV_ZmZoneAdjacency(zones);
            return success(static_cast<std::int64_t>(adjacency[zone].size()));
        }

        // The nth zone touching this one, as a 1-based zone index -- the same
        // numbering zmzonename and zmzonespawncount take.
        SvScriptBuiltinResult zmZoneAdjacentAt(
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider)
        {
            if (call.arguments.size() != 2)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " expects a zone index and a neighbour index");
            }
            std::vector<SvZmZone> zones;
            if (auto error = zmZoneModel(call, provider, zones))
                return *error;
            std::size_t zone{};
            if (auto error = readZmIndex(call, 0, zones.size(), zone))
                return *error;
            const auto adjacency = SV_ZmZoneAdjacency(zones);
            std::size_t neighbour{};
            if (auto error =
                    readZmIndex(call, 1, adjacency[zone].size(), neighbour))
            {
                return *error;
            }
            return success(
                static_cast<std::int64_t>(adjacency[zone][neighbour] + 1u));
        }

        // DOES A ZOMBIE SPAWNED HERE HAVE TO COME THROUGH A WINDOW?
        //
        // The real question the gametype script has been approximating with zone
        // adjacency. See SvServerWorld::zmSpawnCrossesBarrier: it runs an A* per
        // call, so the script must ask once per spawn point and cache the answer.
        SvScriptBuiltinResult zmSpawnCrossesBarrier(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider)
        {
            if (call.arguments.size() != 2)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " expects a zone index and a spawn point index");
            }
            std::vector<SvZmZone> zones;
            if (auto error = zmZoneModel(call, provider, zones))
                return *error;
            std::size_t zone{};
            if (auto error = readZmIndex(call, 0, zones.size(), zone))
                return *error;
            std::size_t point{};
            if (auto error =
                    readZmIndex(call, 1, zones[zone].spawnPoints.size(), point))
            {
                return *error;
            }
            const auto &spawn = zones[zone].spawnPoints[point];
            // A point with no goal has no route to test, and 8 of factory's 69
            // spawners carry none. That is "no", not an error.
            if (!spawn.hasGoalOrigin)
                return success(std::int64_t{ 0 });
            return success(static_cast<std::int64_t>(
                world.zmSpawnCrossesBarrier(spawn.goalOrigin) ? 1 : 0));
        }

        // WHAT THE ROUND HUD SHOWS. The script owns the round loop, and this is the
        // only way it can say so -- nothing else in this server decides a round.
        SvScriptBuiltinResult zmSetRound(SvServerWorld &world, const SvScriptBuiltinCall &call)
        {
            if (call.arguments.size() != 2)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " expects a round and a round goal");
            }
            const auto *round = std::get_if<std::int64_t>(&call.arguments[0]);
            const auto *goal = std::get_if<std::int64_t>(&call.arguments[1]);
            if (!round || !goal)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    call.id.name + " expects two integers");
            }
            if (*round < 1 || *round > 255 || *goal < 0 || *goal > 255)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    call.id.name + " round must be 1..255 and goal 0..255");
            }
            SV_SetZmRound(
                static_cast<std::uint32_t>(*round),
                static_cast<std::uint32_t>(*goal));
            // OLMOD(zm-round-colors): reuse the validated wave director input;
            // no second timer, global HUD readback or per-actor phase clock.
            world.setZmPresentationRound(static_cast<std::uint32_t>(*round));
            return success(static_cast<std::int64_t>(*round));
        }

        std::optional<SvScriptBuiltinResult> readZmSpawnPoint(
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider,
            SvZmSpawnPoint &out)
        {
            if (call.arguments.size() != 2)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " expects a zone index and a spawn point index");
            }
            std::vector<SvZmZone> zones;
            if (auto error = zmZoneModel(call, provider, zones))
                return error;
            std::size_t zone{};
            if (auto error = readZmIndex(call, 0, zones.size(), zone))
                return error;
            std::size_t point{};
            if (auto error =
                    readZmIndex(call, 1, zones[zone].spawnPoints.size(), point))
            {
                return error;
            }
            out = zones[zone].spawnPoints[point];
            return std::nullopt;
        }

        SvScriptBuiltinResult zmSpawnOrigin(
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider)
        {
            SvZmSpawnPoint point;
            if (auto error = readZmSpawnPoint(call, provider, point))
                return *error;
            return success(SvScriptVector{ point.origin });
        }

        SvScriptBuiltinResult zmSpawnAngles(
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider)
        {
            SvZmSpawnPoint point;
            if (auto error = readZmSpawnPoint(call, provider, point))
                return *error;
            return success(SvScriptVector{ point.angles });
        }

        // PUT A MODEL IN THE CLIENT'S BAND BEFORE ANYTHING SPAWNS.
        // precachemodel(modelName) -> the band index the clients will resolve.
        //
        // zmspawnactor sends a model INDEX in the agent element, and the client
        // resolves it against ITS OWN band -- which holds only what this server has
        // transmitted. Until this ran, index 308 was empty on the client, the record's
        // model name stayed "" and sub_52FBE0 built no DObj: zombies were on the wire,
        // validated, and invisible. re/demo-re/20-zm-actor-lifecycle.md 12.21.
        //
        // CALL IT AT SCRIPT INIT. It publishes into the gamestate, so it has to happen
        // before a client is served one; doing it at spawn time is a LIVE configstring
        // change and the client could not enter the session at all (12.21).
        SvScriptBuiltinResult precacheModel(
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ModelPrecacher &modelPrecacher)
        {
            if (call.arguments.size() != 1)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " expects a model name");
            }
            const auto *modelName = std::get_if<std::string>(&call.arguments[0]);
            if (!modelName || modelName->empty())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    call.id.name + " expects a model name");
            }
            if (!modelPrecacher)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidObjectState,
                    call.id.name + " has no model precacher");
            }
            if (!modelPrecacher(*modelName))
            {
                // REFUSED, NOT IGNORED. A model the dedicated cannot resolve is one
                // zmspawnactor will refuse later anyway, and a silent success here
                // would hide it until the zombie failed to draw.
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    call.id.name + " could not precache model " + *modelName);
            }
            return success(true);
        }

        // SPAWN ONE ZOMBIE AT A ZONE'S SPAWN POINT. Bring-up: it stands still.
        // zmspawnactor(zoneIndex, spawnPointIndex, modelName) -> entity number.
        //
        // The model is named, never numbered. The client rebuilds its own model
        // configstring band at map load, so an index that is right in one session is
        // wrong in the next -- see the note on resolveModelConfigStringIndex and
        // re/demo-re on the client re-resolving asset indices.
        SvScriptBuiltinResult zmSpawnActor(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider,
            const SvScriptBuiltinRegistry::ModelResolver &modelResolver)
        {
            if (call.arguments.size() != 3 && call.arguments.size() != 4)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name +
                        " expects a zone index, a spawn point index, a model name"
                        " and optionally a head model name");
            }
            const auto *modelName = std::get_if<std::string>(&call.arguments[2]);
            if (!modelName || modelName->empty())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    call.id.name + " expects a model name");
            }
            std::vector<SvZmZone> zones;
            if (auto error = zmZoneModel(call, provider, zones))
                return *error;
            std::size_t zone{};
            if (auto error = readZmIndex(call, 0, zones.size(), zone))
                return *error;
            std::size_t point{};
            if (auto error =
                    readZmIndex(call, 1, zones[zone].spawnPoints.size(), point))
            {
                return *error;
            }
            if (!modelResolver)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidObjectState,
                    call.id.name + " has no model resolver");
            }
            const auto modelIndex = modelResolver(*modelName);
            if (!modelIndex)
            {
                // REFUSED, NOT DEFAULTED. Spawning with model index 0 puts a zombie
                // shaped like nothing at all into the world and hides the real fault,
                // which is that the map did not precache this model.
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    call.id.name + " could not resolve model " + *modelName);
            }
            // THE HEAD IS OPTIONAL AND REFUSED IF NAMED BUT UNRESOLVABLE. A zombie
            // with no head still draws; one with a head index the dedicated invented
            // would attach whatever sits at that slot on the client.
            std::uint16_t headIndex{};
            if (call.arguments.size() == 4)
            {
                const auto *headName = std::get_if<std::string>(&call.arguments[3]);
                if (!headName || headName->empty())
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        call.id.name + " expects a head model name");
                }
                const auto resolved = modelResolver(*headName);
                if (!resolved)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentValue,
                        call.id.name + " could not resolve head model " + *headName);
                }
                headIndex = *resolved;
            }
            const auto &spawn = zones[zone].spawnPoints[point];
            const auto number = world.spawnZombieActor(
                SvWorldSpawnPoint{
                    .origin = spawn.origin,
                    .angles = spawn.angles,
                    // THE MAP'S OWN NAVIGATION NODE for this spawner, already
                    // resolved from the goal NAME at parse time.
                    .goalOrigin = spawn.goalOrigin,
                    .hasGoalOrigin = spawn.hasGoalOrigin,
                },
                *modelIndex,
                headIndex);
            if (!number)
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    call.id.name + " could not spawn an actor");
            }
            return success(static_cast<std::int64_t>(*number));
        }

        // SPAWN ONE ZOMBIE AT AN EXPLICIT POSITION.
        // zmspawnactorat(position, yaw, modelName) -> entity number.
        //
        // SEPARATE FROM zmspawnactor ON PURPOSE. That one spawns at a map spawner,
        // and every zm spawner sits in a closet behind the barriers -- by design,
        // that is where zombies come from. So it answers "are the spawners where I
        // think they are" and CANNOT answer "does an ET_ACTOR draw", because nothing
        // is ever in a position to see one. This takes a position so the second
        // question can be asked on its own.
        SvScriptBuiltinResult zmSpawnActorAt(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ModelResolver &modelResolver)
        {
            // FOUR ARGS NOW, the fourth an OPTIONAL head model -- the same shape
            // zmspawnactor already takes. Without it this builtin could put a
            // zombie in view but never a zombie with a HEAD, which is exactly
            // the thing 12.48 needs looking at.
            if (call.arguments.size() != 3 && call.arguments.size() != 4)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " expects a position, a yaw, a model name"
                    " and optionally a head model name");
            }
            const auto *position = std::get_if<SvScriptVector>(&call.arguments[0]);
            const auto *modelName = std::get_if<std::string>(&call.arguments[2]);
            if (!position || !modelName || modelName->empty())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    call.id.name + " expects a position vector and a model name");
            }
            float yaw{};
            if (const auto *number = std::get_if<double>(&call.arguments[1]))
                yaw = static_cast<float>(*number);
            else if (const auto *integer = std::get_if<std::int64_t>(&call.arguments[1]))
                yaw = static_cast<float>(*integer);
            else
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    call.id.name + " expects a numeric yaw");
            }
            bool finitePosition = std::isfinite(yaw);
            for (const auto value : *position)
            {
                if (!std::isfinite(value))
                    finitePosition = false;
            }
            if (!finitePosition)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    call.id.name + " expects a finite position and yaw");
            }
            if (!modelResolver)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidObjectState,
                    call.id.name + " has no model resolver");
            }
            const auto modelIndex = modelResolver(*modelName);
            if (!modelIndex)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    call.id.name + " could not resolve model " + *modelName);
            }
            // THE HEAD, REFUSED IF NAMED BUT UNRESOLVABLE -- same rule as
            // zmspawnactor, so a typo fails loudly instead of drawing headless.
            std::uint16_t headIndex{};
            if (call.arguments.size() == 4)
            {
                const auto *headName = std::get_if<std::string>(&call.arguments[3]);
                if (!headName || headName->empty())
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        call.id.name + " expects a head model name");
                }
                const auto resolved = modelResolver(*headName);
                if (!resolved)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentValue,
                        call.id.name + " could not resolve head model " + *headName);
                }
                headIndex = *resolved;
            }
            // Pitch and roll stay zero -- spawnZombieActor forces them anyway, and
            // every retail actor carries zero in both, always.
            const auto number = world.spawnZombieActor(
                SvWorldSpawnPoint{ .origin = *position, .angles = { 0.0f, yaw, 0.0f } },
                *modelIndex,
                headIndex);
            if (!number)
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    call.id.name + " could not spawn an actor");
            }
            return success(static_cast<std::int64_t>(*number));
        }

        SvScriptBuiltinResult zmZoneAt(
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider)
        {
            if (call.arguments.size() != 1)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " expects a position");
            }
            const auto *position = std::get_if<SvScriptVector>(&call.arguments[0]);
            if (!position)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    call.id.name + " expects a position vector");
            }
            std::vector<SvZmZone> zones;
            if (auto error = zmZoneModel(call, provider, zones))
                return *error;
            const auto *zone = SV_ZmZoneAt(zones, *position);
            // AN EMPTY NAME IS A REAL ANSWER, NOT AN ERROR. Standing outside every
            // zone is an ordinary place to be -- the volumes do not tile the map --
            // and failing here would make a script treat "nowhere" as a fault.
            return success(zone ? zone->name : std::string{});
        }

        SvScriptBuiltinResult zmPlayerCount(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            if (!call.arguments.empty())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " expects no arguments");
            }
            // World events run after beginFrame and before endFrame. During that
            // interval snapshot().playerStates is deliberately empty: endFrame
            // assembles the candidate snapshot transactionally. clientStates_,
            // exposed through playerState(), is the authoritative live frame state
            // and already contains every active client at this callback boundary.
            std::int64_t playerCount{};
            for (std::uint32_t clientNum = 0;
                 clientNum < MaximumGameClients;
                 ++clientNum)
            {
                if (world.playerState(clientNum))
                    ++playerCount;
            }
            return success(playerCount);
        }

        // This is deliberately an opt-in reconstruction.  Retail's co-op director
        // selection rule is not recovered, while the existing first-client query is
        // established solo behaviour and must stay intact when the option is absent.
        // OLMOD(cooperative_spawn_zones): opt-in project policy, not recovered retail director logic.
        [[nodiscard]] bool cooperativeZmSpawnZonesEnabled()
        {
            const auto *const value = std::getenv("OLMOD_ZM_COOP_SPAWN_ZONES");
            return value && std::string_view(value) == "1";
        }

        // Return zone-model indices, in zone-model order.  The order therefore does
        // not depend on unordered world storage or the order clients joined.  A
        // player is eligible only while the world still owns a Playing life with
        // nonzero health.  Do not infer gameplay lifecycle from pmType: scripted
        // positioning may temporarily use a normal movement type for another state.
        [[nodiscard]] std::vector<std::size_t> cooperativeZmOccupiedZones(
            const SvServerWorld &world,
            const std::vector<SvZmZone> &zones)
        {
            std::vector<bool> occupied(zones.size());
            for (std::uint32_t clientNum{};
                 clientNum < MaximumGameClients;
                ++clientNum)
            {
                const auto player = world.playerState(clientNum);
                const auto gameplayState = world.gameplayState(clientNum);
                if (!player || !player->health || world.zombieDowned(clientNum) || !gameplayState ||
                    *gameplayState != ClientGameplayState::Playing)
                    continue;
                const auto *const zone = SV_ZmZoneAt(zones, player->origin);
                if (!zone)
                    continue;
                const auto index = static_cast<std::size_t>(zone - zones.data());
                if (index < occupied.size())
                    occupied[index] = true;
            }

            std::vector<std::size_t> result;
            result.reserve(zones.size());
            for (std::size_t index{}; index < occupied.size(); ++index)
            {
                if (occupied[index])
                    result.push_back(index);
            }
            return result;
        }

        SvScriptBuiltinResult zmCooperativeZoneSource(const SvScriptBuiltinCall &call)
        {
            if (!call.arguments.empty())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " expects no arguments");
            }
            return success(std::string(cooperativeZmSpawnZonesEnabled()
                    ? "cooperative-union-reconstruction"
                    : "legacy-first-player"));
        }

        SvScriptBuiltinResult zmCooperativeSpawnZones(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider)
        {
            if (!call.arguments.empty())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " expects no arguments");
            }
            if (!cooperativeZmSpawnZonesEnabled())
                return success(std::string{});
            std::vector<SvZmZone> zones;
            if (auto error = zmZoneModel(call, provider, zones))
                return *error;
            const auto occupied = cooperativeZmOccupiedZones(world, zones);
            const auto adjacency = SV_ZmZoneAdjacency(zones);
            std::vector<bool> selected(zones.size());
            for (const auto occupiedZone : occupied)
            {
                if (zones[occupiedZone].active)
                    selected[occupiedZone] = true;
                for (const auto neighbour : adjacency[occupiedZone])
                {
                    if (zones[neighbour].active)
                        selected[neighbour] = true;
                }
            }

            // One compact response gives Lua a stable, final target set.  That keeps
            // adjacency calculation on its one-second source-status poll instead of
            // rebuilding it once for every selected zone.
            std::string result;
            for (std::size_t index{}; index < selected.size(); ++index)
            {
                if (!selected[index])
                    continue;
                if (!result.empty())
                    result.push_back(',');
                result += std::to_string(index + 1u);
            }
            return success(std::move(result));
        }

        SvScriptBuiltinResult zmPlayerZone(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider)
        {
            if (!call.arguments.empty())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " expects no arguments");
            }

            std::optional<SvPlayerState> player;
            for (std::uint32_t clientNum = 0;
                 clientNum < MaximumGameClients;
                 ++clientNum)
            {
                player = world.playerState(clientNum);
                if (player)
                    break;
            }
            if (!player)
                return success(std::string{});

            std::vector<SvZmZone> zones;
            if (auto error = zmZoneModel(call, provider, zones))
                return *error;
            const auto *zone = SV_ZmZoneAt(zones, player->origin);
            // The volumes do not tile the map. Preserve the same empty-name contract
            // as zmzoneat so a director can retain its last usable zone while the
            // player crosses a gap instead of treating an ordinary position as an
            // engine failure.
            return success(zone ? zone->name : std::string{});
        }

        SvScriptBuiltinResult zmSpawnGoal(
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ZmZoneProvider &provider)
        {
            SvZmSpawnPoint point;
            if (auto error = readZmSpawnPoint(call, provider, point))
                return *error;
            // AN EMPTY STRING IS A REAL ANSWER, not a missing one: zm_sumpf_sh carries
            // a goal on only 32 of its 74 spawn points.
            return success(point.goal);
        }

        SvScriptBuiltinResult getVelocity(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 0, playerState))
                return std::move(*error);
            return success(playerState->velocity);
        }

        SvScriptBuiltinResult isOnGround(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 0, playerState))
                return std::move(*error);
            return success(playerState->groundEntityNum != EntityNumNone);
        }

        SvScriptBuiltinResult isSameTeam(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 1, playerState))
                return std::move(*error);
            const auto *other = std::get_if<SvScriptObjectRef>(&call.arguments[0]);
            if (!other || other->kind != SvScriptObjectKind::Player)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "issameteam expects a player object");
            }
            if (!world.playerTeam(other->id))
            {
                return failure(
                    SvScriptBuiltinErrorCode::ObjectNotFound,
                    "issameteam player does not exist");
            }
            return success(world.onSameTeam(call.self->id, other->id));
        }

        SvScriptBuiltinResult setWeaponAmmoClip(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 2, playerState))
                return std::move(*error);
            std::string_view weaponName;
            std::int64_t count{};
            if (auto error = readAmmoArguments(call, weaponName, count))
                return std::move(*error);
            return ammoMutationResult(world.setWeaponAmmoClip(
                call.self->id, weaponName, count));
        }

        SvScriptBuiltinResult setWeaponAmmoStock(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 2, playerState))
                return std::move(*error);
            std::string_view weaponName;
            std::int64_t count{};
            if (auto error = readAmmoArguments(call, weaponName, count))
                return std::move(*error);
            return ammoMutationResult(world.setWeaponAmmoStock(
                call.self->id, weaponName, count));
        }

        SvScriptBuiltinResult respawn(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 1, playerState))
                return std::move(*error);
            const auto *delay = std::get_if<std::int64_t>(&call.arguments[0]);
            if (!delay || *delay < 0 || *delay > 60'000)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "respawn expects a delay from 0 through 60000 milliseconds");
            }
            switch (world.requestPlayerRespawn(
                call.self->id, static_cast<std::uint32_t>(*delay)))
            {
            case SvServerWorld::RespawnRequestResult::Queued:
                return success(std::monostate{});
            case SvServerWorld::RespawnRequestResult::ClientNotFound:
                return failure(
                    SvScriptBuiltinErrorCode::ObjectNotFound,
                    "respawn player does not exist");
            case SvServerWorld::RespawnRequestResult::NotPlaying:
            case SvServerWorld::RespawnRequestResult::NotDead:
                return failure(
                    SvScriptBuiltinErrorCode::InvalidObjectState,
                    "respawn requires a dead Playing player");
            case SvServerWorld::RespawnRequestResult::InvalidDelay:
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "respawn delay is invalid");
            }
            return failure(
                SvScriptBuiltinErrorCode::WorldMutationFailed,
                "respawn returned an invalid result");
        }

        SvScriptBuiltinResult saveCheckpoint(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 0, playerState))
                return std::move(*error);
            if (!world.savePlayerRespawnCheckpoint(call.self->id))
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidObjectState,
                    "savecheckpoint requires a live Playing player");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult setMapGameObjects(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            constexpr std::size_t MaximumGameObjectNames = 32;
            constexpr std::size_t MaximumGameObjectNameLength = 64;
            if (call.arguments.size() > MaximumGameObjectNames)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "setmapgameobjects received too many names");
            }
            std::array<std::string_view, MaximumGameObjectNames> names{};
            for (std::size_t index = 0; index < call.arguments.size(); ++index)
            {
                const auto *name = std::get_if<std::string>(&call.arguments[index]);
                if (!name)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "setmapgameobjects expects string names");
                }
                if (name->empty() || name->size() > MaximumGameObjectNameLength)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentValue,
                        "setmapgameobjects names must be non-empty and at most 64 bytes");
                }
                names[index] = *name;
            }
            if (!world.setMapGameObjects(
                    std::span(names.data(), call.arguments.size())))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setmapgameobjects could not update the server world");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult getEntArray(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            if (call.arguments.size() != 2)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "getentarray expects a value and key");
            }
            const auto *value = std::get_if<std::string>(&call.arguments[0]);
            const auto *key = std::get_if<std::string>(&call.arguments[1]);
            if (!value || !key)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "getentarray expects string arguments");
            }
            if (value->empty() || key->empty() || key->size() > 64 ||
                key->find('\0') != std::string::npos)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "getentarray received an invalid value or key");
            }
            SvScriptObjectArray objects;
            for (const auto handle : world.findMapEntities(*value, *key))
            {
                objects.push_back({
                    .kind = SvScriptObjectKind::Entity,
                    .id = handle.entityNum,
                    .entityGeneration = handle.generation,
                });
            }
            return success(std::move(objects));
        }

        std::optional<SvScriptBuiltinResult> validateEntityMethod(
            const SvServerWorld &world,
            const SvScriptBuiltinCall &call,
            const std::size_t expectedArgumentCount,
            SvEntityHandle &handle)
        {
            if (call.arguments.size() != expectedArgumentCount)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name + " received an invalid argument count");
            }
            if (!call.self)
            {
                return failure(
                    SvScriptBuiltinErrorCode::MissingSelf,
                    call.id.name + " requires an entity object");
            }
            if (call.self->kind != SvScriptObjectKind::Entity ||
                !call.self->entityGeneration)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    call.id.name +
                        " requires a generation-safe entity object");
            }
            handle = {
                .entityNum = call.self->id,
                .generation = *call.self->entityGeneration,
            };
            if (!world.entity(handle))
            {
                return failure(
                    SvScriptBuiltinErrorCode::ObjectNotFound,
                    call.id.name + " entity does not exist");
            }
            return std::nullopt;
        }

        // WHERE IS IT? The one question the script layer could not ask.
        //
        // `getvelocity` shipped and `getorigin` did not, which reads like an oversight
        // rather than a decision -- they are adjacent fields of the same struct. The
        // absence is load-bearing though: without it a script cannot place anything
        // relative to anything else, so loot could only ever go at coordinates typed
        // into the source by hand, and the play-area circle could not test whether a
        // player is inside it. Both of those are BattleCity.
        //
        //     local where = codol.call("method:getorigin", player)
        //     where[1], where[2], where[3]   -- x, y, z
        //
        // TAKES A PLAYER OR AN ENTITY, dispatched on the receiver's kind rather than
        // split into two names. Callers do not care which they are holding -- "put loot
        // near this thing" is the same sentence either way -- and the two validators
        // already return the right error for the wrong receiver.
        //
        // The player branch reports playerState.origin, which is the pmove result the
        // client is told about, NOT the entity's currentOrigin. They agree while a
        // player is alive; playerState is the one that stays correct across a respawn.
        SvScriptBuiltinResult getOrigin(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            if (call.self && call.self->kind == SvScriptObjectKind::Entity)
            {
                SvEntityHandle handle;
                if (auto error = validateEntityMethod(world, call, 0, handle))
                    return std::move(*error);
                const auto entity = world.entity(handle);
                if (!entity)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::ObjectNotFound,
                        "getorigin entity does not exist");
                }
                return success(entity->currentOrigin);
            }
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 0, playerState))
                return std::move(*error);
            return success(playerState->origin);
        }

        SvScriptBuiltinResult setScriptedPosition(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 5, playerState))
                return std::move(*error);
            std::array<float, 3> origin{};
            for (std::size_t axis = 0; axis < origin.size(); ++axis)
            {
                const auto *value = std::get_if<double>(&call.arguments[axis]);
                if (!value || !std::isfinite(*value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "setscriptedposition expects three finite origin numbers");
                }
                origin[axis] = static_cast<float>(*value);
            }
            const auto *pmType =
                std::get_if<std::int64_t>(&call.arguments[3]);
            const auto *pmFlags =
                std::get_if<std::int64_t>(&call.arguments[4]);
            if (!pmType || !pmFlags || *pmType < 0 || *pmType > UINT8_MAX ||
                *pmFlags < 0 ||
                static_cast<std::uint64_t>(*pmFlags) > UINT32_MAX)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "setscriptedposition expects uint8 pmType and uint32 pmFlags");
            }
            if (!world.setPlayerScriptedPosition(
                    call.self->id,
                    origin,
                    static_cast<std::uint8_t>(*pmType),
                    static_cast<std::uint32_t>(*pmFlags)))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setscriptedposition could not update the player");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult clearScriptedPosition(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 0, playerState))
                return std::move(*error);
            if (!world.clearPlayerScriptedPosition(call.self->id))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "clearscriptedposition could not update the player");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult setScriptedViewAngles(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 3, playerState))
                return std::move(*error);
            std::array<float, 3> viewAngles{};
            for (std::size_t axis = 0; axis < viewAngles.size(); ++axis)
            {
                const auto *value = std::get_if<double>(&call.arguments[axis]);
                if (!value || !std::isfinite(*value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "setscriptedviewangles expects three finite angle numbers");
                }
                viewAngles[axis] = static_cast<float>(*value);
            }
            if (!world.setPlayerScriptedViewAngles(call.self->id, viewAngles))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setscriptedviewangles requires an active scripted position");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult setScriptedViewClamp(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 4, playerState))
                return std::move(*error);
            std::array<float, 4> values{};
            for (std::size_t index = 0; index < values.size(); ++index)
            {
                const auto *value = std::get_if<double>(&call.arguments[index]);
                if (!value || !std::isfinite(*value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "setscriptedviewclamp expects base pitch/yaw and range pitch/yaw");
                }
                values[index] = static_cast<float>(*value);
            }
            if (!world.setPlayerScriptedViewClamp(
                    call.self->id,
                    { values[0], values[1] },
                    { values[2], values[3] }))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setscriptedviewclamp requires an active scripted position");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult setScriptedLinkState(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 4, playerState))
                return std::move(*error);
            const auto *flags = std::get_if<std::int64_t>(&call.arguments[0]);
            if (!flags || *flags < 0 || *flags > 7)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "setscriptedlinkstate expects three-bit link flags");
            }
            std::array<float, 3> linkAngles{};
            for (std::size_t axis = 0; axis < linkAngles.size(); ++axis)
            {
                const auto *value =
                    std::get_if<double>(&call.arguments[axis + 1]);
                if (!value || !std::isfinite(*value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "setscriptedlinkstate expects finite pitch/yaw/roll angles");
                }
                linkAngles[axis] = static_cast<float>(*value);
            }
            if (!world.setPlayerScriptedLinkState(
                    call.self->id,
                    static_cast<std::uint8_t>(*flags),
                    linkAngles))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setscriptedlinkstate requires an active scripted position");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult setShellshock(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 2, playerState))
                return std::move(*error);
            const auto *profileIndex =
                std::get_if<std::int64_t>(&call.arguments[0]);
            const auto *durationMilliseconds =
                std::get_if<std::int64_t>(&call.arguments[1]);
            if (!profileIndex || !durationMilliseconds)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "setshellshock expects integer profile and duration values");
            }
            if (*profileIndex <= 0 || *profileIndex > 0xF ||
                *durationMilliseconds <= 0 ||
                *durationMilliseconds > UINT16_MAX)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "setshellshock expects profile 1..15 and duration 1..65535");
            }
            if (!world.setPlayerShellshock(
                    call.self->id,
                    static_cast<std::uint8_t>(*profileIndex),
                    static_cast<std::uint16_t>(*durationMilliseconds)))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setshellshock could not update the player");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult setObjective(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 8, playerState))
                return std::move(*error);

            const auto *slot = std::get_if<std::int64_t>(&call.arguments[0]);
            const auto *state = std::get_if<std::int64_t>(&call.arguments[1]);
            const auto *icon = std::get_if<std::int64_t>(&call.arguments[5]);
            const auto *entityNum =
                std::get_if<std::int64_t>(&call.arguments[6]);
            const auto *teamNum =
                std::get_if<std::int64_t>(&call.arguments[7]);
            if (!slot || !state || !icon || !entityNum || !teamNum)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "setobjective expects integer slot, state, icon, entityNum, and teamNum values");
            }
            if (*slot < 0 || *slot >= 32 || *state < 0 || *state > 5 ||
                *icon < 0 || *icon > 0xFFF ||
                *entityNum < 0 || *entityNum > EntityNumNone ||
                *teamNum < 0 || *teamNum > 0xF)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "setobjective values exceed the CODOL objective wire domains");
            }

            std::array<float, 3> origin{};
            for (std::size_t axis = 0; axis < origin.size(); ++axis)
            {
                const auto *value =
                    std::get_if<double>(&call.arguments[axis + 2]);
                if (!value || !std::isfinite(*value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "setobjective expects three finite origin numbers");
                }
                origin[axis] = static_cast<float>(*value);
            }

            auto objectives = playerState->objectives;
            objectives[static_cast<std::size_t>(*slot)] = SvObjective{
                .state = static_cast<SvObjectiveState>(*state),
                .origin = origin,
                .icon = static_cast<std::uint16_t>(*icon),
                .entityNum = static_cast<std::uint16_t>(*entityNum),
                .teamNum = static_cast<std::uint8_t>(*teamNum),
            };
            if (!world.setPlayerObjectives(call.self->id, objectives))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setobjective could not update the player");
            }
            return success(std::monostate{});
        }

        // Return the stable wire number carried by a generation-safe entity
        // object. Event callbacks reconstruct their Lua userdata, so userdata
        // identity cannot associate a killed actor with its reusable agent slot.
        SvScriptBuiltinResult getEntityNumber(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            SvEntityHandle handle;
            if (auto error = validateEntityMethod(world, call, 0, handle))
                return std::move(*error);
            return success(static_cast<std::int64_t>(handle.entityNum));
        }

        SvScriptBuiltinResult getMapEntityField(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            SvEntityHandle handle;
            if (auto error = validateEntityMethod(world, call, 1, handle))
                return std::move(*error);
            const auto *key = std::get_if<std::string>(&call.arguments[0]);
            if (!key)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "getmapfield expects a string key");
            }
            if (key->empty() || key->size() > 64 ||
                key->find('\0') != std::string::npos)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "getmapfield received an invalid key");
            }
            const auto value = world.mapEntityField(handle, *key);
            return value ? success(*value) : success(std::monostate{});
        }

        SvScriptBuiltinResult isTouchingPlayer(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            SvEntityHandle handle;
            if (auto error = validateEntityMethod(world, call, 1, handle))
                return std::move(*error);
            const auto *const player =
                std::get_if<SvScriptObjectRef>(&call.arguments[0]);
            if (!player || player->kind != SvScriptObjectKind::Player)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "istouching expects a player object");
            }
            const auto state = world.playerState(player->id);
            const auto gameplay = world.gameplayState(player->id);
            if (!state || !gameplay)
            {
                return failure(
                    SvScriptBuiltinErrorCode::ObjectNotFound,
                    "istouching player does not exist");
            }
            if (*gameplay != ClientGameplayState::Playing)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidObjectState,
                    "istouching player is not in Playing state");
            }
            return success(
                world.logicalMapEntityTouchesPlayer(handle, player->id));
        }

        // PUT A WEAPON IN A PLAYER'S HANDS. What a loot crate is FOR.
        //
        //     codol.call("method:giveweapon", player, "ak104dmz_mp")
        //
        // Takes a NAME, not an index: the weapon band is per-map, so a number written
        // into a script is a number that is wrong on the next map. Names come from the
        // band dump (OLMOD_DUMP_WEAPON_BAND=1, archived in re/).
        //
        // The grant is server-owned state re-asserted every frame, because the native
        // pmove deletes weapons the player was not natively given -- see
        // SvServerWorld::givePlayerWeapon. It survives until the next spawn.
        SvScriptBuiltinResult giveWeapon(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::WeaponResolver &resolveWeapon)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 1, playerState))
                return std::move(*error);
            // A NAME OR A RAW INDEX. Names are preferred and are what a real script
            // should use, but a MODULAR weapon -- which is what battle royale loot
            // actually is -- has no plain name in the band to resolve: its
            // configstring is a `**` definition, not `ak104dmz_mp`. So the loot band's
            // own numbers have to be passable directly.
            std::optional<std::uint16_t> weaponIndex;
            if (const auto *const index = std::get_if<std::int64_t>(&call.arguments[0]))
            {
                if (*index <= 0 || *index >= WeaponConfigStringCount)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentValue,
                        "giveweapon received a weapon index outside the band");
                }
                weaponIndex = static_cast<std::uint16_t>(*index);
            }
            else if (const auto *const weaponName =
                    std::get_if<std::string>(&call.arguments[0]);
                weaponName && !weaponName->empty())
            {
                weaponIndex = resolveWeapon ? resolveWeapon(*weaponName) : std::nullopt;
                if (!weaponIndex)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentValue,
                        "giveweapon could not resolve the weapon -- it must be a name "
                        "this build's weapon band publishes");
                }
            }
            else
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "giveweapon expects a weapon name or a weapon index");
            }
            if (!world.givePlayerWeapon(playerState->clientNum, *weaponIndex))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "giveweapon could not grant the weapon");
            }
            return success(static_cast<std::int64_t>(*weaponIndex));
        }

        SvScriptBuiltinResult setPlayerWeapons(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (call.arguments.size() != 3 && call.arguments.size() != 4)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "setplayerweapons expects primary, secondary, optional supplemental, and selected indexes");
            }
            if (auto error = validatePlayerMethod(
                    world, call, call.arguments.size(), playerState))
                return std::move(*error);
            std::array<std::uint16_t, 4> weaponIndexes{};
            const auto selectedArgument = call.arguments.size() - 1;
            for (std::size_t index{}; index < call.arguments.size(); ++index)
            {
                const auto *const value =
                    std::get_if<std::int64_t>(&call.arguments[index]);
                const auto permitsNone = index == selectedArgument;
                if (!value || *value < (permitsNone ? 0 : 1) ||
                    *value >= WeaponConfigStringCount)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentValue,
                        "setplayerweapons expects nonzero owned weapon indexes and a selected index or zero");
                }
                weaponIndexes[index] = static_cast<std::uint16_t>(*value);
            }
            const std::uint16_t supplemental = call.arguments.size() == 4
                ? weaponIndexes[2]
                : std::uint16_t{};
            const auto selected = weaponIndexes[selectedArgument];
            if (!world.setPlayerWeapons(
                    call.self->id,
                    weaponIndexes[0], weaponIndexes[1], selected,
                    supplemental))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setplayerweapons could not replace the active player's arsenal");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult weaponIndex(
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::WeaponResolver &resolveWeapon)
        {
            if (call.self)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "weaponindex is a function");
            }
            if (call.arguments.size() != 1)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "weaponindex expects one weapon name or modular definition");
            }
            const auto *const name =
                std::get_if<std::string>(&call.arguments[0]);
            if (!name || name->empty() || name->size() >= 128 ||
                name->find('\0') != std::string::npos)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "weaponindex expects a non-empty weapon name or modular definition");
            }
            const auto index = resolveWeapon
                ? resolveWeapon(*name)
                : std::nullopt;
            if (!index || !*index || *index >= WeaponConfigStringCount)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "weaponindex could not resolve a registered weapon");
            }
            return success(static_cast<std::int64_t>(*index));
        }

        SvScriptBuiltinResult setPlayerWeaponAmmo(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 3, playerState))
                return std::move(*error);
            const auto *const weapon =
                std::get_if<std::int64_t>(&call.arguments[0]);
            const auto *const clip =
                std::get_if<std::int64_t>(&call.arguments[1]);
            const auto *const stock =
                std::get_if<std::int64_t>(&call.arguments[2]);
            if (!weapon || *weapon < 1 ||
                *weapon >= WeaponConfigStringCount || !clip || !stock)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "setplayerweaponammo expects a weapon index, clip count, and stock count");
            }
            return ammoMutationResult(world.setPlayerWeaponAmmo(
                call.self->id,
                static_cast<std::uint16_t>(*weapon), *clip, *stock));
        }

        SvScriptBuiltinResult setEntityHealth(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            SvEntityHandle handle;
            if (auto error = validateEntityMethod(world, call, 1, handle))
                return std::move(*error);
            const auto *health = std::get_if<std::int64_t>(&call.arguments[0]);
            if (!health || *health < 1 ||
                *health > std::numeric_limits<std::int32_t>::max())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "sethealth expects a positive 32-bit integer");
            }
            auto state = world.entityDamageState(handle).value_or(
                SvEntityDamageState{
                    .kind = SvEntityDamageKind::Generic,
                });
            state.health = static_cast<std::int32_t>(*health);
            if (!world.setEntityDamageState(handle, state))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "sethealth could not update the entity");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult setCanDamage(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            if (call.arguments.size() != 1)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "setcandamage received an invalid argument count");
            }
            const auto *enabled = std::get_if<bool>(&call.arguments[0]);
            if (!enabled)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "setcandamage expects a boolean");
            }
            if (call.self && call.self->kind == SvScriptObjectKind::Player)
            {
                std::optional<SvPlayerState> playerState;
                if (auto error = validatePlayerMethod(
                        world, call, 1, playerState))
                {
                    return std::move(*error);
                }
                if (!world.setPlayerCanTakeDamage(call.self->id, *enabled))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::WorldMutationFailed,
                        "setcandamage could not update the player");
                }
                return success(std::monostate{});
            }
            SvEntityHandle handle;
            if (auto error = validateEntityMethod(world, call, 1, handle))
                return std::move(*error);
            auto state = world.entityDamageState(handle);
            if (!state)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidObjectState,
                    "setcandamage requires initialized entity health");
            }
            state->canTakeDamage = *enabled;
            if (!world.setEntityDamageState(handle, *state))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setcandamage could not update the entity");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult setModel(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ModelResolver &resolveModel)
        {
            SvEntityHandle handle;
            if (auto error = validateEntityMethod(world, call, 1, handle))
                return std::move(*error);
            const auto *modelName = std::get_if<std::string>(&call.arguments[0]);
            if (!modelName || modelName->empty())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "setmodel expects a non-empty model name");
            }
            const auto modelIndex = resolveModel
                ? resolveModel(*modelName)
                : std::nullopt;
            if (!modelIndex)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "setmodel could not resolve the model asset");
            }
            if (!world.setScriptModelIndex(
                    handle, *modelIndex, *modelName))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setmodel could not update the script model");
            }
            return success(std::monostate{});
        }

        // PLACE A MODEL IN THE WORLD -- the primitive a loot system needs, and the one
        // thing the script layer could not do.
        //
        // `setmodel` already existed, so a script could give an entity a model, but
        // nothing could put it anywhere: there is no setorigin in the builtin table.
        // That is why `dmz.lua` cannot place loot, and why the loot band published in
        // the gamestate has nothing on the ground to match it.
        //
        // This alone is not enough to build loot with -- see `spawnModel` below for why
        // `codol.entity(n)` cannot produce something to call this ON.
        //
        // NO NEW WORLD CODE WAS NEEDED. `SvServerWorld::setScriptModelPresentation`
        // already takes a model index, a name, an ORIGIN, angles and an active flag in
        // one call, and already validates them (finite vectors, real asset, script-mover
        // eType, native mirror rollback on failure). This only exposes it.
        //
        //     codol.call("method:setmodelat", ent, "model_name", x, y, z)
        //     codol.call("method:setmodelat", ent, "model_name", x, y, z, yaw)
        //
        // Angles default to zero in the four-argument form.
        //
        // Angles are (pitch, yaw, roll) and only yaw is taken: loot lying on the ground
        // wants a facing, not a tumble, and a script that can set pitch can stand a crate
        // on its corner. Widen it when something needs it.
        SvScriptBuiltinResult setModelAt(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ModelResolver &resolveModel)
        {
            // validateEntityMethod checks an EXACT count, so the optional yaw is
            // resolved here first rather than by calling it twice and reporting whichever
            // error came second.
            const auto argumentCount = call.arguments.size();
            if (argumentCount != 4 && argumentCount != 5)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "setmodelat expects (model, x, y, z) or (model, x, y, z, yaw)");
            }
            SvEntityHandle handle;
            if (auto error = validateEntityMethod(world, call, argumentCount, handle))
                return std::move(*error);
            const auto *modelName = std::get_if<std::string>(&call.arguments[0]);
            if (!modelName || modelName->empty())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "setmodelat expects a non-empty model name");
            }
            std::array<float, 3> origin{};
            for (std::size_t axis = 0; axis < 3; ++axis)
            {
                const auto *value = std::get_if<double>(&call.arguments[axis + 1]);
                if (!value || !std::isfinite(*value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "setmodelat expects three finite numbers for the origin");
                }
                origin[axis] = static_cast<float>(*value);
            }
            std::array<float, 3> angles{};
            if (argumentCount == 5)
            {
                const auto *yaw = std::get_if<double>(&call.arguments[4]);
                if (!yaw || !std::isfinite(*yaw))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "setmodelat's optional fifth argument is a finite yaw");
                }
                angles[1] = static_cast<float>(*yaw);
            }
            const auto modelIndex = resolveModel
                ? resolveModel(*modelName)
                : std::nullopt;
            if (!modelIndex)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "setmodelat could not resolve the model asset -- it must be a name "
                    "this map's model band publishes");
            }
            if (!world.setScriptModelPresentation(
                    handle, *modelIndex, *modelName, origin, angles, true))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setmodelat could not place the script model");
            }
            return success(std::monostate{});
        }

        // ALLOCATE A WORLD ENTITY. Without this the script layer cannot build loot at
        // all, and the reason is easy to miss: `codol.entity(n)` LOOKS like a
        // constructor and is not one.
        //
        //     codol.entity(37)   -- "give me a handle to entity 37"
        //     codol.entity()     -- error: object id must be an integer
        //
        // It is `createObject(..., Entity)` in sv_script_lua_mp.cpp, which wraps an
        // entity NUMBER that already exists into a userdata. Nothing in the sixteen
        // builtins allocated a slot, so the only entities a script could ever touch were
        // the ones the map shipped -- 31 script models on mp_battlecity, all of them
        // scenery the map wants where it put them. A loot system needs entities that did
        // not exist when the map was compiled.
        //
        //     local crate = codol.call("function:spawnmodel", "model_name", x, y, z)
        //     if crate then codol.call("method:sethealth", crate, 1) end
        //
        // There is no `codol.spawnmodel` shorthand: the bridge exposes six fields
        // (player, entity, call, on, wait, thread) and every builtin goes through
        // `call` with a "kind:name" key. The object metatable carries no __index
        // either, so `crate:sethealth(1)` is not a thing on this bridge.
        //
        // Returns the entity on success and nil on failure, so a script can spawn until
        // the pool says no without a pcall around every call. Failure is expected and
        // ordinary here: the pool is finite (dynamic numbers start at 37) and a loot
        // routine that scatters a hundred crates WILL hit the end of it.
        //
        // THE SPAWN IS ROLLED BACK IF THE MODEL DOES NOT TAKE. An allocated entity with
        // no model is a slot that can never be recovered -- the script has no handle to
        // free it with, because it never got one -- so the two steps are one transaction
        // rather than two builtins the caller has to sequence correctly.
        SvScriptBuiltinResult spawnModel(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::ModelResolver &resolveModel)
        {
            const auto argumentCount = call.arguments.size();
            if (argumentCount != 4 && argumentCount != 5)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "spawnmodel expects (model, x, y, z) or (model, x, y, z, yaw)");
            }
            const auto *modelName = std::get_if<std::string>(&call.arguments[0]);
            if (!modelName || modelName->empty())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "spawnmodel expects a non-empty model name");
            }
            std::array<float, 3> origin{};
            for (std::size_t axis = 0; axis < 3; ++axis)
            {
                const auto *value = std::get_if<double>(&call.arguments[axis + 1]);
                if (!value || !std::isfinite(*value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "spawnmodel expects three finite numbers for the origin");
                }
                origin[axis] = static_cast<float>(*value);
            }
            std::array<float, 3> angles{};
            if (argumentCount == 5)
            {
                const auto *yaw = std::get_if<double>(&call.arguments[4]);
                if (!yaw || !std::isfinite(*yaw))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "spawnmodel's optional fifth argument is a finite yaw");
                }
                angles[1] = static_cast<float>(*yaw);
            }
            // Resolve the asset BEFORE taking a slot. A name the map's model band does
            // not publish is the common script bug, and refusing it here costs the pool
            // nothing.
            const auto modelIndex = resolveModel
                ? resolveModel(*modelName)
                : std::nullopt;
            if (!modelIndex)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "spawnmodel could not resolve the model asset -- it must be a name "
                    "this map's model band publishes");
            }
            // spawnScriptModel, NOT spawnEntity + setScriptModelPresentation. The
            // first version of this builtin did the latter and every single spawn
            // failed: setScriptModelPresentation demands the entity ALREADY be a
            // script mover carrying a model, which a blank slot never is. It also
            // sets the gameplayActive flag without which nothing is ever published
            // to a client.
            const auto handle = world.spawnScriptModel(
                *modelIndex, *modelName, origin, angles);
            if (!handle)
            {
                // The pool refusing is ordinary, not exceptional; see above.
                return success(std::monostate{});
            }
            return success(SvScriptObjectRef{
                .kind = SvScriptObjectKind::Entity,
                .id = handle->entityNum,
                .entityGeneration = handle->generation,
            });
        }

        SvScriptBuiltinResult spawnGroundTiltController(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            if (call.self)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "spawngroundtiltcontroller is a function");
            }
            if (!call.arguments.empty())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "spawngroundtiltcontroller expects no arguments");
            }
            const auto handle = world.spawnGroundTiltController();
            if (!handle)
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "spawngroundtiltcontroller could not publish the controller");
            }
            return success(SvScriptObjectRef{
                .kind = SvScriptObjectKind::Entity,
                .id = handle->entityNum,
                .entityGeneration = handle->generation,
            });
        }

        SvScriptBuiltinResult setGroundTiltTrajectory(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            constexpr std::size_t ArgumentCount = 9;
            SvEntityHandle handle;
            if (auto error = validateEntityMethod(
                    world, call, ArgumentCount, handle))
            {
                return std::move(*error);
            }
            const auto *type = std::get_if<std::int64_t>(&call.arguments[0]);
            const auto *timeOffset =
                std::get_if<std::int64_t>(&call.arguments[1]);
            const auto *duration =
                std::get_if<std::int64_t>(&call.arguments[2]);
            if (!type || !timeOffset || !duration || *type < 0 ||
                *type > std::numeric_limits<std::uint8_t>::max() ||
                *duration < 0 ||
                *duration > std::numeric_limits<std::uint32_t>::max())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "setgroundtilttrajectory expects uint8 type, signed time offset, and uint32 duration");
            }
            const auto trajectoryTime =
                static_cast<std::int64_t>(world.snapshot().serverTime) +
                *timeOffset;
            if (trajectoryTime < 0 ||
                trajectoryTime > std::numeric_limits<std::uint32_t>::max())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "setgroundtilttrajectory time is outside the server clock");
            }
            std::array<float, 3> angles{};
            std::array<float, 3> angularDelta{};
            for (std::size_t axis{}; axis < 3; ++axis)
            {
                const auto *base =
                    std::get_if<double>(&call.arguments[axis + 3]);
                const auto *delta =
                    std::get_if<double>(&call.arguments[axis + 6]);
                if (!base || !delta || !std::isfinite(*base) ||
                    !std::isfinite(*delta))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "setgroundtilttrajectory expects six finite angle numbers");
                }
                angles[axis] = static_cast<float>(*base);
                angularDelta[axis] = static_cast<float>(*delta);
            }
            if (!world.setGroundTiltControllerTrajectory(
                    handle,
                    static_cast<std::uint8_t>(*type),
                    static_cast<std::uint32_t>(trajectoryTime),
                    static_cast<std::uint32_t>(*duration),
                    angles,
                    angularDelta))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setgroundtilttrajectory could not update the controller");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult playerSetGroundReferenceEnt(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            if (call.arguments.size() > 1)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "playersetgroundreferenceent expects zero or one entity");
            }
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(
                    world, call, call.arguments.size(), playerState))
            {
                return std::move(*error);
            }
            if (call.arguments.empty())
            {
                if (!world.clearPlayerGroundReference(call.self->id))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::WorldMutationFailed,
                        "playersetgroundreferenceent could not clear the reference");
                }
                return success(std::monostate{});
            }
            const auto *object =
                std::get_if<SvScriptObjectRef>(&call.arguments.front());
            if (!object || object->kind != SvScriptObjectKind::Entity ||
                !object->entityGeneration)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "playersetgroundreferenceent expects a generation-safe entity");
            }
            if (!world.setPlayerGroundReference(
                    call.self->id,
                    SvEntityHandle{
                        .entityNum = object->id,
                        .generation = *object->entityGeneration,
                    }))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "playersetgroundreferenceent could not select the controller");
            }
            return success(std::monostate{});
        }

        // Play one named animation on an existing map script_model. The model
        // and transform remain map-authored; this only publishes the mover's
        // animation fields and the packet-animation clear/goal pair required
        // by CG_ScriptMover.
        SvScriptBuiltinResult playAnimation(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::AnimationResolver &resolveAnimation)
        {
            const auto argumentCount = call.arguments.size();
            if (argumentCount != 1 && argumentCount != 2)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "playanimation expects (animation) or (animation, flags)");
            }
            SvEntityHandle handle;
            if (auto error = validateEntityMethod(
                    world, call, argumentCount, handle))
            {
                return std::move(*error);
            }
            const auto *name = std::get_if<std::string>(&call.arguments[0]);
            if (!name || name->empty())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "playanimation expects a non-empty animation name");
            }
            std::uint8_t flags = 1;
            if (argumentCount == 2)
            {
                const auto *value =
                    std::get_if<std::int64_t>(&call.arguments[1]);
                if (!value || *value < 0 || *value > 3)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentValue,
                        "playanimation flags must be an integer from 0 through 3");
                }
                flags = static_cast<std::uint8_t>(*value);
            }
            const auto animationIndex = resolveAnimation
                ? resolveAnimation(*name)
                : std::nullopt;
            if (!animationIndex)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "playanimation could not resolve the named animation");
            }
            const auto startTime = world.snapshot().serverTime;
            if (!world.setScriptModelAnimation(
                    handle, *animationIndex, startTime, flags))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "playanimation could not animate the script model");
            }
            return success(std::monostate{});
        }

        // Campaign dialogue is a positional ET_EVENTS sound carrier in the
        // retail snapshot. The script names the alias and supplies the decoded
        // origin; the native resolver owns the client-specific CCS index.
        SvScriptBuiltinResult playSoundAt(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::SoundResolver &resolveSound)
        {
            if (call.self)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "playsoundat is a function");
            }
            if (call.arguments.size() != 4 && call.arguments.size() != 5)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "playsoundat expects (alias, x, y, z) or (alias, x, y, z, as_master)");
            }
            const auto *alias = std::get_if<std::string>(&call.arguments[0]);
            if (!alias || alias->empty() || alias->size() >= 128 ||
                alias->find('\0') != std::string::npos)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "playsoundat expects a non-empty sound alias");
            }
            std::array<float, 3> origin{};
            for (std::size_t axis{}; axis < origin.size(); ++axis)
            {
                const auto *value =
                    std::get_if<double>(&call.arguments[axis + 1]);
                if (!value || !std::isfinite(*value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "playsoundat expects three finite origin numbers");
                }
                origin[axis] = static_cast<float>(*value);
            }
            bool asMaster{};
            if (call.arguments.size() == 5)
            {
                const auto *value = std::get_if<bool>(&call.arguments[4]);
                if (!value)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "playsoundat's optional fifth argument is a boolean");
                }
                asMaster = *value;
            }
            const auto parameter = resolveSound
                ? resolveSound(*alias)
                : std::nullopt;
            if (!parameter)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "playsoundat could not resolve the alias in the client's sound table");
            }
            if (!world.spawnSoundAliasEvent(*parameter, origin, asMaster))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "playsoundat could not publish the sound event");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult triggerExploder(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            if (call.self)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "triggerexploder is a function");
            }
            if (call.arguments.size() != 1)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "triggerexploder expects an event index");
            }
            const auto *index =
                std::get_if<std::int64_t>(&call.arguments[0]);
            if (!index || *index <= 0 || *index > 0xFF)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "triggerexploder expects an index from 1 through 255");
            }
            if (!world.spawnExploderEvent(static_cast<std::uint8_t>(*index)))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "triggerexploder could not publish the event");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult fireMagicAt(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            if (call.self)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "firemagicat is a function");
            }
            if (call.arguments.size() != 4)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "firemagicat expects (event_parameter, x, y, z)");
            }
            const auto *parameter =
                std::get_if<std::int64_t>(&call.arguments[0]);
            std::array<float, 3> origin{};
            for (std::size_t axis{}; axis < origin.size(); ++axis)
            {
                const auto *value =
                    std::get_if<double>(&call.arguments[axis + 1]);
                if (!value || !std::isfinite(*value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "firemagicat expects three finite origin numbers");
                }
                origin[axis] = static_cast<float>(*value);
            }
            if (!parameter || *parameter <= 0 || *parameter > 0xFF)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "firemagicat expects a parameter from 1 through 255");
            }
            if (!world.spawnFireMagicEvent(
                    static_cast<std::uint8_t>(*parameter), origin))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "firemagicat could not publish the event");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult playFxAt(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            if (call.self)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "playfxat is a function");
            }
            if (call.arguments.size() != 7)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "playfxat expects (effect_index, x, y, z, pitch, yaw, roll)");
            }
            const auto *effect =
                std::get_if<std::int64_t>(&call.arguments[0]);
            std::array<float, 6> values{};
            for (std::size_t index{}; index < values.size(); ++index)
            {
                const auto *value =
                    std::get_if<double>(&call.arguments[index + 1]);
                if (!value || !std::isfinite(*value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "playfxat expects six finite transform numbers");
                }
                values[index] = static_cast<float>(*value);
            }
            if (!effect || *effect <= 0 ||
                *effect >= EffectConfigStringCount)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "playfxat expects an effect index from 1 through 399");
            }
            if (!world.spawnWorldFxEvent(
                    static_cast<std::uint16_t>(*effect),
                    { values[0], values[1], values[2] },
                    { values[3], values[4], values[5] }))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "playfxat could not publish the event");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult playFxOnTag(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            SvEntityHandle target;
            if (auto error = validateEntityMethod(world, call, 5, target))
                return *error;
            const auto *effect =
                std::get_if<std::int64_t>(&call.arguments[0]);
            const auto *tag =
                std::get_if<std::int64_t>(&call.arguments[1]);
            std::array<float, 3> origin{};
            for (std::size_t index{}; index < origin.size(); ++index)
            {
                const auto *value =
                    std::get_if<double>(&call.arguments[index + 2]);
                if (!value || !std::isfinite(*value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "playfxontag expects three finite origin numbers");
                }
                origin[index] = static_cast<float>(*value);
            }
            if (!effect || *effect <= 0 ||
                *effect >= EffectConfigStringCount ||
                !tag || *tag < 0 || *tag >= 0xFF)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "playfxontag expects effect 1..399 and tag 0..254");
            }
            if (!world.spawnWorldFxOnTagEvent(
                    target,
                    static_cast<std::uint16_t>(*effect),
                    static_cast<std::uint8_t>(*tag),
                    origin))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "playfxontag could not publish the event");
            }
            return success(std::monostate{});
        }

        std::optional<SvScriptBuiltinResult> readScriptedMissileState(
            const SvServerWorld &world,
            const SvScriptBuiltinCall &call,
            SvMissileNetworkState &state)
        {
            if (call.arguments.size() != 14)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    call.id.name +
                        " expects (weapon, position_type, position_time_offset, "
                        "x, y, z, dx, dy, dz, angle_type, pitch, yaw, roll, "
                        "launch_time_offset)");
            }
            const auto *weapon = std::get_if<std::int64_t>(&call.arguments[0]);
            const auto *positionType =
                std::get_if<std::int64_t>(&call.arguments[1]);
            const auto *positionTimeOffset =
                std::get_if<std::int64_t>(&call.arguments[2]);
            const auto *angleType =
                std::get_if<std::int64_t>(&call.arguments[9]);
            const auto *launchTimeOffset =
                std::get_if<std::int64_t>(&call.arguments[13]);
            if (!weapon || *weapon <= 0 ||
                *weapon >= WeaponConfigStringCount ||
                !positionType || (*positionType != 1 && *positionType != 2) ||
                !positionTimeOffset || !angleType ||
                (*angleType != 0 && *angleType != 1) ||
                !launchTimeOffset)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    call.id.name +
                        " received an unsupported recorded missile field");
            }
            std::array<float, 9> values{};
            for (std::size_t index{}; index < values.size(); ++index)
            {
                const auto argumentIndex = index < 6 ? index + 3 : index + 4;
                const auto *value =
                    std::get_if<double>(&call.arguments[argumentIndex]);
                if (!value || !std::isfinite(*value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        call.id.name +
                            " expects nine finite trajectory numbers");
                }
                values[index] = static_cast<float>(*value);
            }
            const auto now = static_cast<std::int64_t>(
                world.snapshot().serverTime);
            const auto positionTime = now + *positionTimeOffset;
            const auto launchTime = now + *launchTimeOffset;
            if (positionTime < std::numeric_limits<std::int32_t>::min() ||
                positionTime > std::numeric_limits<std::int32_t>::max() ||
                launchTime < 0 ||
                launchTime > std::numeric_limits<std::uint32_t>::max())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    call.id.name + " received a trajectory time outside the wire domain");
            }

            // CODREF(Wetwork demo ET_MISSILE): the capture's RPG rows use
            // eFlags 0x1000, scale 1, no attached ground entity, linear or
            // gravity position trajectories, and stationary angle trajectories.
            state = {
                .number = 0,
                .weapon = static_cast<std::uint16_t>(*weapon),
                .owner = EntityNumWorld,
                .ground = EntityNumNone,
                .eFlags = 0x1000,
                .position = {
                    .type = static_cast<std::int32_t>(*positionType),
                    .time = static_cast<std::int32_t>(positionTime),
                    .duration = 0,
                    .base = { values[0], values[1], values[2] },
                    .delta = { values[3], values[4], values[5] },
                },
                .angles = {
                    .type = static_cast<std::int32_t>(*angleType),
                    .time = 0,
                    .duration = 0,
                    .base = { values[6], values[7], values[8] },
                    .delta = {},
                },
                .scale = 1.0f,
                .launchTime = static_cast<std::uint32_t>(launchTime),
            };
            return std::nullopt;
        }

        SvScriptBuiltinResult spawnScriptedMissile(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            if (call.self)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "spawnscriptedmissile is a function");
            }
            SvMissileNetworkState state;
            if (auto error = readScriptedMissileState(world, call, state))
                return std::move(*error);
            const auto handle = world.spawnScriptedMissile(state);
            if (!handle)
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "spawnscriptedmissile could not publish the missile");
            }
            return success(SvScriptObjectRef{
                .kind = SvScriptObjectKind::Entity,
                .id = handle->entityNum,
                .entityGeneration = handle->generation,
            });
        }

        SvScriptBuiltinResult setScriptedMissile(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            SvEntityHandle handle;
            if (auto error = validateEntityMethod(world, call, 14, handle))
                return std::move(*error);
            SvMissileNetworkState state;
            if (auto error = readScriptedMissileState(world, call, state))
                return std::move(*error);
            if (!world.setScriptedMissileState(handle, state))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setscriptedmissile could not update the missile");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult earthquakeAt(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            if (call.self)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "earthquakeat is a function");
            }
            if (call.arguments.size() != 6)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "earthquakeat expects (x, y, z, scale, radius, duration_ms)");
            }
            std::array<float, 3> origin{};
            for (std::size_t axis{}; axis < origin.size(); ++axis)
            {
                const auto *value =
                    std::get_if<double>(&call.arguments[axis]);
                if (!value || !std::isfinite(*value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "earthquakeat expects three finite origin numbers");
                }
                origin[axis] = static_cast<float>(*value);
            }
            const auto *scale = std::get_if<double>(&call.arguments[3]);
            const auto *radius = std::get_if<double>(&call.arguments[4]);
            const auto *duration =
                std::get_if<std::int64_t>(&call.arguments[5]);
            if (!scale || !radius || !duration ||
                !std::isfinite(*scale) || *scale <= 0.0 ||
                !std::isfinite(*radius) || *radius <= 0.0 ||
                *duration <= 0 || *duration > 0xFFFF)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "earthquakeat expects positive finite scale/radius and a 1..65535 ms duration");
            }
            if (!world.spawnEarthquakeEvent(
                    origin,
                    static_cast<float>(*scale),
                    static_cast<float>(*radius),
                    static_cast<std::uint16_t>(*duration)))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "earthquakeat could not publish the event");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult physicsExplosionSphereAt(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            if (call.self)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "physicsexplosionsphereat is a function");
            }
            if (call.arguments.size() != 6)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "physicsexplosionsphereat expects (x, y, z, inner_radius, outer_radius, magnitude)");
            }
            std::array<float, 6> values{};
            for (std::size_t index{}; index < values.size(); ++index)
            {
                const auto *value =
                    std::get_if<double>(&call.arguments[index]);
                if (!value || !std::isfinite(*value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "physicsexplosionsphereat expects six finite numbers");
                }
                values[index] = static_cast<float>(*value);
            }
            if (values[3] < 0.0f || values[4] <= 0.0f ||
                values[4] < values[3] || values[5] <= 0.0f)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "physicsexplosionsphereat expects 0 <= inner <= outer and positive magnitude");
            }
            if (!world.spawnPhysicsExplosionSphereEvent(
                    { values[0], values[1], values[2] },
                    values[3], values[4], values[5]))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "physicsexplosionsphereat could not publish the event");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult radiusDamageAt(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            if (call.self)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "radiusdamageat is a function");
            }
            if (call.arguments.size() != 6)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "radiusdamageat expects (x, y, z, effect_radius, data1, data2)");
            }
            std::array<float, 3> origin{};
            for (std::size_t axis{}; axis < origin.size(); ++axis)
            {
                const auto *value =
                    std::get_if<double>(&call.arguments[axis]);
                if (!value || !std::isfinite(*value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "radiusdamageat expects three finite origin numbers");
                }
                origin[axis] = static_cast<float>(*value);
            }
            const auto *effectRadius =
                std::get_if<double>(&call.arguments[3]);
            const auto *data1 =
                std::get_if<std::int64_t>(&call.arguments[4]);
            const auto *data2 =
                std::get_if<std::int64_t>(&call.arguments[5]);
            if (!effectRadius || !std::isfinite(*effectRadius) ||
                *effectRadius <= 0.0 || !data1 || *data1 <= 0 ||
                *data1 > std::numeric_limits<std::int32_t>::max() ||
                !data2 || *data2 <= 0 ||
                static_cast<std::uint64_t>(*data2) >
                    std::numeric_limits<std::uint32_t>::max())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "radiusdamageat expects a positive radius and positive 32-bit data words");
            }
            if (!world.spawnRadiusDamageEvent(
                    origin,
                    static_cast<float>(*effectRadius),
                    static_cast<std::uint32_t>(*data1),
                    static_cast<std::uint32_t>(*data2)))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "radiusdamageat could not publish the event");
            }
            return success(std::monostate{});
        }

        // Materialize one of the campaign map's actor spawners. The map entity
        // contributes the authored origin and angles. AgentState +0x04 is the
        // spawned entity number and is filled transactionally by spawnActor.
        //
        //     local actor = codol.call("method:spawnactor", spawner,
        //         slot, model, team, animation, animation_start_time)
        //
        // Model numbers are deliberately accepted here because this is the
        // map-specific model configstring index measured from the recording.
        SvScriptBuiltinResult spawnActor(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            SvEntityHandle spawner;
            if (auto error = validateEntityMethod(world, call, 5, spawner))
                return std::move(*error);
            const auto className = world.mapEntityField(spawner, "classname");
            if (!className || !className->starts_with("actor_"))
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "spawnactor requires a campaign actor spawner");
            }
            const auto source = world.entity(spawner);
            if (!source)
            {
                return failure(
                    SvScriptBuiltinErrorCode::ObjectNotFound,
                    "spawnactor spawner does not exist");
            }

            constexpr std::array<std::uint32_t, 5> Maximum{
                23, 0x3FF, 0x7FF, 0xFFF,
                std::numeric_limits<std::uint32_t>::max(),
            };
            std::array<std::uint32_t, 5> values{};
            for (std::size_t index = 0; index < values.size(); ++index)
            {
                const auto *integer =
                    std::get_if<std::int64_t>(&call.arguments[index]);
                if (!integer || *integer < 0 ||
                    static_cast<std::uint64_t>(*integer) > Maximum[index])
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentValue,
                        "spawnactor expects bounded integer agent fields");
                }
                values[index] = static_cast<std::uint32_t>(*integer);
            }

            SvAgentState agent;
            agent.agentNum = values[0];
            agent.fields[SvAgentState::ModelField] = values[1];
            agent.fields[SvAgentState::TeamField] = values[2];
            agent.fields[SvAgentState::AnimationField] = values[3];
            agent.fields[SvAgentState::AnimationStartTimeField] = values[4];
            const auto handle = world.spawnActor(
                agent, source->currentOrigin, source->currentAngles);
            if (!handle)
                return success(std::monostate{});
            return success(SvScriptObjectRef{
                .kind = SvScriptObjectKind::Entity,
                .id = handle->entityNum,
                .entityGeneration = handle->generation,
            });
        }

        // Update the presentation row without replacing the actor entity or its
        // stable low-word join key. This is what lets mission phases change poses
        // and weapons while the actor remains the same network object.
        SvScriptBuiltinResult setActorState(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            SvEntityHandle actor;
            if (auto error = validateEntityMethod(world, call, 4, actor))
                return std::move(*error);
            auto agent = world.actorAgentState(actor);
            if (!agent)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "setactorstate requires a campaign actor");
            }
            constexpr std::array<std::uint32_t, 4> Maximum{
                0x3FF, 0x7FF, 0xFFF,
                std::numeric_limits<std::uint32_t>::max(),
            };
            std::array<std::uint32_t, 4> values{};
            for (std::size_t index = 0; index < values.size(); ++index)
            {
                const auto *integer =
                    std::get_if<std::int64_t>(&call.arguments[index]);
                if (!integer || *integer < 0 ||
                    static_cast<std::uint64_t>(*integer) > Maximum[index])
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentValue,
                        "setactorstate expects bounded integer agent fields");
                }
                values[index] = static_cast<std::uint32_t>(*integer);
            }
            agent->fields[SvAgentState::ModelField] = values[0];
            agent->fields[SvAgentState::TeamField] = values[1];
            agent->fields[SvAgentState::AnimationField] = values[2];
            agent->fields[SvAgentState::AnimationStartTimeField] = values[3];
            if (!world.setActorAgentState(actor, *agent))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setactorstate could not update the actor");
            }
            return success(std::monostate{});
        }

        // Campaign spawner targets are authored navigation goals.  Keep the
        // interpolation policy in the map script while this primitive owns the
        // joined ET_ACTOR transform and collision/native synchronization.
        //
        //     codol.call("method:setactorposition", actor, x, y, z, yaw)
        SvScriptBuiltinResult setActorPosition(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            SvEntityHandle actor;
            if (auto error = validateEntityMethod(world, call, 4, actor))
                return std::move(*error);
            if (!world.actorAgentState(actor))
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "setactorposition requires a campaign actor");
            }
            std::array<float, 3> origin{};
            for (std::size_t axis = 0; axis < origin.size(); ++axis)
            {
                const auto *value = std::get_if<double>(&call.arguments[axis]);
                if (!value || !std::isfinite(*value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "setactorposition expects finite origin numbers and yaw");
                }
                origin[axis] = static_cast<float>(*value);
            }
            const auto *yaw = std::get_if<double>(&call.arguments[3]);
            if (!yaw || !std::isfinite(*yaw))
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "setactorposition expects finite origin numbers and yaw");
            }
            if (!world.setActorTransform(
                    actor, origin,
                    { 0.0f, static_cast<float>(*yaw), 0.0f }))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setactorposition could not move the actor");
            }
            return success(std::monostate{});
        }

        // Move Wetwork's helicopter cast with one collision/native mirror
        // rebuild. Arguments are the receiver's x/y/z/yaw followed by repeated
        // (actor, x, y, z, yaw) groups.
        SvScriptBuiltinResult setActorPositions(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            if (call.arguments.size() < 4 ||
                (call.arguments.size() - 4) % 5 != 0)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "setactorpositions received an invalid argument count");
            }
            if (!call.self)
            {
                return failure(
                    SvScriptBuiltinErrorCode::MissingSelf,
                    "setactorpositions requires an entity object");
            }
            if (call.self->kind != SvScriptObjectKind::Entity ||
                !call.self->entityGeneration)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "setactorpositions requires a generation-safe entity object");
            }

            std::vector<SvActorTransform> transforms;
            transforms.reserve(1 + (call.arguments.size() - 4) / 5);
            const auto appendTransform =
                [&](const SvEntityHandle actor,
                    const std::size_t valueOffset)
                    -> std::optional<SvScriptBuiltinResult> {
                    if (!world.entity(actor))
                    {
                        return failure(
                            SvScriptBuiltinErrorCode::ObjectNotFound,
                            "setactorpositions actor does not exist");
                    }
                    std::array<float, 3> origin{};
                    for (std::size_t axis = 0; axis < origin.size(); ++axis)
                    {
                        const auto *value = std::get_if<double>(
                            &call.arguments[valueOffset + axis]);
                        if (!value || !std::isfinite(*value))
                        {
                            return failure(
                                SvScriptBuiltinErrorCode::InvalidArgumentType,
                                "setactorpositions expects finite origin numbers and yaw");
                        }
                        origin[axis] = static_cast<float>(*value);
                    }
                    const auto *yaw = std::get_if<double>(
                        &call.arguments[valueOffset + 3]);
                    if (!yaw || !std::isfinite(*yaw))
                    {
                        return failure(
                            SvScriptBuiltinErrorCode::InvalidArgumentType,
                            "setactorpositions expects finite origin numbers and yaw");
                    }
                    transforms.push_back({
                        .actor = actor,
                        .origin = origin,
                        .angles = { 0.0f, static_cast<float>(*yaw), 0.0f },
                    });
                    return std::nullopt;
                };

            const SvEntityHandle receiver{
                .entityNum = call.self->id,
                .generation = *call.self->entityGeneration,
            };
            if (auto error = appendTransform(receiver, 0))
                return std::move(*error);
            for (std::size_t offset = 4;
                 offset < call.arguments.size(); offset += 5)
            {
                const auto *object = std::get_if<SvScriptObjectRef>(
                    &call.arguments[offset]);
                if (!object || object->kind != SvScriptObjectKind::Entity ||
                    !object->entityGeneration)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "setactorpositions expects generation-safe actor objects");
                }
                const SvEntityHandle actor{
                    .entityNum = object->id,
                    .generation = *object->entityGeneration,
                };
                if (auto error = appendTransform(actor, offset + 1))
                    return std::move(*error);
            }
            if (!world.setActorTransforms(transforms))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setactorpositions could not move the actors");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult finishDamageResult(
            SvServerWorld::FinishPlayerDamageResult result,
            std::string_view builtinName);

        // One native campaign-rifle trace. The confirmed Wetwork recording
        // carries EV_FIRE_WEAPON (41, parameter 0) on ET_ACTOR. The mission
        // can publish that presentation independently from its one damage
        // attempt per burst; damage still uses the ordinary retained
        // finishPlayerDamage owner and requires a clear locational trace.
        SvScriptBuiltinResult actorFire(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call,
            const SvScriptBuiltinRegistry::WeaponResolver &resolveWeapon,
            bool publishPresentation)
        {
            SvEntityHandle actor;
            if (auto error = validateEntityMethod(world, call, 3, actor))
                return std::move(*error);
            if (!world.actorAgentState(actor))
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "actorfire requires a campaign actor");
            }
            const auto *target =
                std::get_if<SvScriptObjectRef>(&call.arguments[0]);
            const auto *damage = std::get_if<std::int64_t>(&call.arguments[1]);
            if (!target || target->kind != SvScriptObjectKind::Player ||
                target->id >= MaximumGameClients || !damage || *damage < 1 ||
                *damage > std::numeric_limits<std::int32_t>::max())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "actorfire expects a player and positive damage");
            }
            const auto targetState = world.playerState(target->id);
            const auto targetGameplay = world.gameplayState(target->id);
            const auto actorEntity = world.entity(actor);
            if (!targetState || !targetGameplay || !actorEntity)
            {
                return failure(
                    SvScriptBuiltinErrorCode::ObjectNotFound,
                    "actorfire target or actor no longer exists");
            }
            if (*targetGameplay != ClientGameplayState::Playing ||
                !targetState->health)
            {
                return success(false);
            }

            std::optional<std::uint16_t> weaponIndex;
            if (const auto *index =
                    std::get_if<std::int64_t>(&call.arguments[2]);
                index && *index > 0 && *index <= MaximumWeaponAssetIndex)
            {
                weaponIndex = static_cast<std::uint16_t>(*index);
            }
            else if (const auto *name =
                    std::get_if<std::string>(&call.arguments[2]);
                name && !name->empty())
            {
                weaponIndex = resolveWeapon ? resolveWeapon(*name) : std::nullopt;
            }
            if (!weaponIndex)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "actorfire could not resolve its weapon");
            }

            auto start = actorEntity->currentOrigin;
            auto end = targetState->origin;
            start[2] += 48.0f;
            end[2] += 48.0f;
            const auto trace = world.tracePoint(SvPointTraceRequest{
                .start = start,
                .end = end,
                .contentMask = PlayerCollisionContentMask,
                .filter = {
                    .passEntityNum = actor.entityNum,
                },
                .mode = SvPointTraceMode::RifleLocational,
                .allowChildren = true,
            });
            if (!trace)
            {
                return failure(
                    SvScriptBuiltinErrorCode::MatchStateUnavailable,
                    "actorfire requires the retained point trace");
            }
            const bool reachedTarget = trace->fraction >= 1.0f ||
                (trace->hitType == TraceHitTypeEntity &&
                    trace->hitId == target->id);
            if (!reachedTarget)
                return success(false);

            std::array<float, 3> direction{};
            float lengthSquared{};
            for (std::size_t axis = 0; axis < direction.size(); ++axis)
            {
                direction[axis] = end[axis] - start[axis];
                lengthSquared += direction[axis] * direction[axis];
            }
            if (!(lengthSquared > 0.0f) || !std::isfinite(lengthSquared))
                return success(false);
            const auto inverseLength = 1.0f / std::sqrt(lengthSquared);
            for (auto &part : direction)
                part *= inverseLength;

            if (publishPresentation &&
                !world.queueActorPresentationEvent(actor, { 41, 0 }))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "actorfire could not queue EV_FIRE_WEAPON");
            }
            return finishDamageResult(
                world.finishPlayerDamage(SvPlayerDamagePayload{
                    .targetClientNum = target->id,
                    .inflictorEntityNum = actor.entityNum,
                    .attackerEntityNum = actor.entityNum,
                    .damage = static_cast<std::int32_t>(*damage),
                    .methodOfDeath = 2,
                    .weaponAssetIndex = *weaponIndex,
                    .direction = direction,
                }),
                call.id.name);
        }

        // RPG damage is carried by Wetwork's recovered ET_MISSILE track. Its
        // source actor still needs the ordinary fire event and weapon pose,
        // without adding a second hitscan wound on top of the projectile.
        SvScriptBuiltinResult actorFirePresentation(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            SvEntityHandle actor;
            if (auto error = validateEntityMethod(world, call, 0, actor))
                return std::move(*error);
            if (!world.actorAgentState(actor))
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "actorfirepresentation requires a campaign actor");
            }
            if (!world.queueActorPresentationEvent(actor, { 41, 0 }))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "actorfirepresentation could not queue EV_FIRE_WEAPON");
            }
            return success(std::monostate{});
        }

        SvScriptBuiltinResult actorCorpse(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            if (call.arguments.size() > 1)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentCount,
                    "actorcorpse expects an optional ragdoll boolean");
            }
            SvEntityHandle actor;
            if (auto error = validateEntityMethod(
                    world, call, call.arguments.size(), actor))
                return std::move(*error);
            bool startRagdoll = false;
            if (!call.arguments.empty())
            {
                const auto *value = std::get_if<bool>(&call.arguments[0]);
                if (!value)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentType,
                        "actorcorpse expects an optional ragdoll boolean");
                }
                startRagdoll = *value;
            }
            if (!world.convertActorToCorpse(actor, startRagdoll))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "actorcorpse could not convert the campaign actor");
            }
            return success(true);
        }

        SvScriptBuiltinResult setAgentField(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            SvEntityHandle actor;
            if (auto error = validateEntityMethod(world, call, 2, actor))
                return std::move(*error);
            auto agent = world.actorAgentState(actor);
            const auto *field = std::get_if<std::int64_t>(&call.arguments[0]);
            const auto *value = std::get_if<std::int64_t>(&call.arguments[1]);
            if (!agent)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidSelf,
                    "setagentfield requires a campaign actor");
            }
            if (!field || *field < 0 ||
                *field >= static_cast<std::int64_t>(SvAgentState::FieldCount) ||
                *field == static_cast<std::int64_t>(SvAgentState::EntityNumField) ||
                !value || *value < 0 ||
                static_cast<std::uint64_t>(*value) >
                    std::numeric_limits<std::uint32_t>::max())
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "setagentfield expects a mutable field index and uint32 value");
            }
            agent->fields[static_cast<std::size_t>(*field)] =
                static_cast<std::uint32_t>(*value);
            if (!world.setActorAgentState(actor, *agent))
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "setagentfield rejected a value outside that field's wire domain");
            }
            return success(std::monostate{});
        }

        // RETURN A SLOT TO THE POOL. The other half of spawnmodel: loot that has been
        // picked up has to stop existing, and a match that scatters loot every round
        // would otherwise exhaust the dynamic region and then silently stop spawning.
        //
        //     codol.call("method:delete", crate)
        //
        // The generation check in validateEntityMethod makes a double delete safe -- the
        // second call holds a stale generation and is refused as ObjectNotFound rather
        // than freeing whatever now occupies that number.
        SvScriptBuiltinResult deleteEntity(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            SvEntityHandle handle;
            if (auto error = validateEntityMethod(world, call, 0, handle))
                return std::move(*error);
            if (!world.freeEntity(handle))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "delete could not free the entity");
            }
            return success(std::monostate{});
        }

        // WHAT IS IN THE CRATE.
        //
        //     codol.call("method:setloot", crate, 1149, 60)
        //
        // spawnmodel puts a box in the world and that is all it does -- it is a script
        // MOVER, the same thing a moving platform is, and nothing about it says
        // "weapon". This is the line that makes it loot: the weapon it hands over and
        // the distance at which the server offers it.
        //
        // A RAW WEAPON INDEX, for the reason giveweapon takes one: battle royale loot
        // is MODULAR, and a modular weapon's configstring is a `**` definition with no
        // plain name to resolve. The numbers come out of the map's own loot band.
        //
        // THE RADIUS IS PER ITEM rather than one server-wide constant, because a care
        // package pod and a pistol-ammo box are not the same size and the prompt should
        // appear when the player is at the model, not when they are at its centre.
        SvScriptBuiltinResult setLoot(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            SvEntityHandle handle;
            if (auto error = validateEntityMethod(world, call, 2, handle))
                return std::move(*error);
            const auto *const weaponIndex =
                std::get_if<std::int64_t>(&call.arguments[0]);
            if (!weaponIndex || *weaponIndex <= 0 ||
                *weaponIndex >= WeaponConfigStringCount)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "setloot expects a weapon index inside this build's weapon band");
            }
            // EITHER SPELLING OF A NUMBER. Lua hands an integer literal over as an
            // integer and `60.0` as a double, and a radius is exactly the argument
            // somebody writes both ways.
            double radius{};
            if (const auto *const value = std::get_if<double>(&call.arguments[1]))
                radius = *value;
            else if (const auto *const whole =
                    std::get_if<std::int64_t>(&call.arguments[1]))
                radius = static_cast<double>(*whole);
            else
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "setloot expects a pickup radius");
            }
            if (!std::isfinite(radius) || radius <= 0.0)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "setloot expects a positive finite pickup radius");
            }
            if (!world.registerLootItem(
                    handle,
                    static_cast<std::uint16_t>(*weaponIndex),
                    static_cast<float>(radius)))
            {
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    "setloot could not register the item");
            }
            return success(static_cast<std::int64_t>(*weaponIndex));
        }

        bool readOptionalEntityNum(
            const SvScriptValue &value,
            std::optional<std::uint32_t> &entityNum)
        {
            if (std::holds_alternative<std::monostate>(value))
            {
                entityNum.reset();
                return true;
            }
            const auto *object = std::get_if<SvScriptObjectRef>(&value);
            if (!object || object->id >= MaximumGameEntities)
                return false;
            entityNum = object->id;
            return true;
        }

        template <typename Integer>
        bool readInteger(
            const SvScriptValue &value,
            const std::int64_t minimum,
            const std::int64_t maximum,
            Integer &result)
        {
            const auto *integer = std::get_if<std::int64_t>(&value);
            if (!integer || *integer < minimum || *integer > maximum)
                return false;
            result = static_cast<Integer>(*integer);
            return true;
        }

        bool readOptionalVector(
            const SvScriptValue &value,
            std::optional<SvScriptVector> &vector)
        {
            if (std::holds_alternative<std::monostate>(value))
            {
                vector.reset();
                return true;
            }
            const auto *input = std::get_if<SvScriptVector>(&value);
            if (!input)
                return false;
            vector = *input;
            return true;
        }

        bool readPlayerDamagePayload(
            const std::span<const SvScriptValue> arguments,
            const std::uint32_t targetClientNum,
            SvPlayerDamagePayload &payload)
        {
            if (arguments.size() != 11)
                return false;
            payload.targetClientNum = targetClientNum;
            std::int64_t damage{};
            std::int64_t damageFlags{};
            std::int64_t methodOfDeath{};
            std::int64_t weaponAssetIndex{};
            std::int64_t hitLocation{};
            std::int64_t timeOffset{};
            std::int64_t boneIndex{};
            if (!readOptionalEntityNum(arguments[0], payload.inflictorEntityNum) ||
                !readOptionalEntityNum(arguments[1], payload.attackerEntityNum) ||
                !readInteger(arguments[2], 1,
                    std::numeric_limits<std::int32_t>::max(), damage) ||
                !readInteger(arguments[3], 0, 0xFFFFFFFFLL, damageFlags) ||
                !readInteger(arguments[4], 0, MethodOfDeathCount - 1,
                    methodOfDeath) ||
                !readInteger(
                    arguments[5], 1, MaximumWeaponAssetIndex, weaponAssetIndex) ||
                !readOptionalVector(arguments[6], payload.point) ||
                !readOptionalVector(arguments[7], payload.direction) ||
                !readInteger(arguments[8], 0, HitLocationCount - 1,
                    hitLocation) ||
                !readInteger(arguments[9],
                    std::numeric_limits<std::int32_t>::min(),
                    std::numeric_limits<std::int32_t>::max(), timeOffset) ||
                !readInteger(arguments[10], 0, 0xFFFF, boneIndex))
            {
                return false;
            }
            payload.damage = static_cast<std::int32_t>(damage);
            payload.damageFlags = static_cast<std::uint32_t>(damageFlags);
            payload.methodOfDeath = static_cast<std::uint8_t>(methodOfDeath);
            payload.weaponAssetIndex = static_cast<std::uint16_t>(weaponAssetIndex);
            payload.hitLocation = static_cast<std::uint8_t>(hitLocation);
            payload.timeOffset = static_cast<std::int32_t>(timeOffset);
            payload.boneIndex = static_cast<std::uint16_t>(boneIndex);
            return true;
        }

        SvScriptBuiltinResult finishDamageResult(
            const SvServerWorld::FinishPlayerDamageResult result,
            const std::string_view builtinName)
        {
            switch (result)
            {
            case SvServerWorld::FinishPlayerDamageResult::Applied:
                return success(std::monostate{});
            case SvServerWorld::FinishPlayerDamageResult::ClientNotFound:
                return failure(
                    SvScriptBuiltinErrorCode::ObjectNotFound,
                    std::string(builtinName) + " target does not exist");
            case SvServerWorld::FinishPlayerDamageResult::NotPlaying:
                return failure(
                    SvScriptBuiltinErrorCode::InvalidObjectState,
                    std::string(builtinName) + " target is not Playing");
            case SvServerWorld::FinishPlayerDamageResult::InvalidPayload:
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    std::string(builtinName) + " payload is invalid");
            case SvServerWorld::FinishPlayerDamageResult::DeathTransitionUnavailable:
                return failure(
                    SvScriptBuiltinErrorCode::DeathTransitionUnavailable,
                    std::string(builtinName) +
                        " death transition is not restored");
            case SvServerWorld::FinishPlayerDamageResult::NativeMirrorUnavailable:
                return failure(
                    SvScriptBuiltinErrorCode::WorldMutationFailed,
                    std::string(builtinName) +
                        " native entity mirror rejected the damage transaction");
            }
            return failure(
                SvScriptBuiltinErrorCode::WorldMutationFailed,
                std::string(builtinName) + " returned an invalid result");
        }

        SvScriptBuiltinResult finishPlayerDamage(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            // CODREF(g_damage): BO1 PlayerCmd_finishPlayerDamage 0x006080A0
            // and Ghosts 0x1401218E0 are the script-to-native boundary after
            // player_damage policy. They validate metadata, update feedback
            // and dispatch pain/last-stand/die handlers.
            // CODDIFF(g_damage): this Lua method exposes the currently typed
            // subset and delegates an atomic world mutation; it is not a
            // replacement claim for the COD script VM or gentity handler table.
            constexpr std::size_t ArgumentCount = 11;
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(
                    world, call, ArgumentCount, playerState))
            {
                return std::move(*error);
            }

            SvPlayerDamagePayload payload;
            if (!readPlayerDamagePayload(
                    call.arguments, call.self->id, payload))
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "finishplayerdamage received invalid damage metadata");
            }
            return finishDamageResult(
                world.finishPlayerDamage(payload), call.id.name);
        }

        SvScriptBuiltinResult finishSharedPlayerDamage(
            SvServerWorld &world,
            const SvScriptBuiltinCall &call)
        {
            std::optional<SvPlayerState> playerState;
            if (auto error = validatePlayerMethod(world, call, 12, playerState))
                return std::move(*error);
            const auto *other = std::get_if<SvScriptObjectRef>(&call.arguments[0]);
            if (!other || other->kind != SvScriptObjectKind::Player)
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "finishsharedplayerdamage expects a second player object");
            }
            if (other->id == call.self->id ||
                !world.onSameTeam(call.self->id, other->id))
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
                    "finishsharedplayerdamage requires distinct same-team players");
            }
            SvPlayerDamagePayload first;
            if (!readPlayerDamagePayload(
                    std::span(call.arguments).subspan(1),
                    call.self->id,
                    first))
            {
                return failure(
                    SvScriptBuiltinErrorCode::InvalidArgumentType,
                    "finishsharedplayerdamage received invalid damage metadata");
            }
            auto second = first;
            second.targetClientNum = other->id;
            const std::array payloads{ first, second };
            return finishDamageResult(
                world.finishPlayerDamageBatch(payloads), call.id.name);
        }
    }

    bool SvScriptBuiltinResult::succeeded() const
    {
        return error.code == SvScriptBuiltinErrorCode::None;
    }

    SvScriptBuiltinRegistry::SvScriptBuiltinRegistry(
        SvServerWorld &world,
        MatchScoreCallbacks matchScoreCallbacks,
        ModelResolver modelResolver,
        WeaponResolver weaponResolver,
        ZmZoneProvider zmZoneProvider,
        ModelPrecacher modelPrecacher,
        MissionCallbacks missionCallbacks,
        SoundResolver soundResolver,
        AnimationResolver animationResolver)
        : world_(world),
          matchScoreCallbacks_(std::move(matchScoreCallbacks)),
          missionCallbacks_(std::move(missionCallbacks)),
          modelResolver_(std::move(modelResolver)),
          weaponResolver_(std::move(weaponResolver)),
          zmZoneProvider_(std::move(zmZoneProvider)),
          modelPrecacher_(std::move(modelPrecacher)),
          soundResolver_(std::move(soundResolver)),
          animationResolver_(std::move(animationResolver))
    {
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmzonecount" },
            [this](SvServerWorld &, const SvScriptBuiltinCall &call) {
                return zmZoneCount(call, zmZoneProvider_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmzonename" },
            [this](SvServerWorld &, const SvScriptBuiltinCall &call) {
                return zmZoneName(call, zmZoneProvider_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmzonespawncount" },
            [this](SvServerWorld &, const SvScriptBuiltinCall &call) {
                return zmZoneSpawnCount(call, zmZoneProvider_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmzoneactive" },
            [this](SvServerWorld &, const SvScriptBuiltinCall &call) {
                return zmZoneActive(call, zmZoneProvider_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmactivezonecount" },
            [this](SvServerWorld &, const SvScriptBuiltinCall &call) {
                return zmActiveZoneCount(call, zmZoneProvider_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmspawnorigin" },
            [this](SvServerWorld &, const SvScriptBuiltinCall &call) {
                return zmSpawnOrigin(call, zmZoneProvider_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmspawnangles" },
            [this](SvServerWorld &, const SvScriptBuiltinCall &call) {
                return zmSpawnAngles(call, zmZoneProvider_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmspawnactorat" },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                return zmSpawnActorAt(world, call, modelResolver_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "precachemodel" },
            [this](SvServerWorld &, const SvScriptBuiltinCall &call) {
                return precacheModel(call, modelPrecacher_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmspawnactor" },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                return zmSpawnActor(world, call, zmZoneProvider_, modelResolver_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmzoneat" },
            [this](SvServerWorld &, const SvScriptBuiltinCall &call) {
                return zmZoneAt(call, zmZoneProvider_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmplayercount" },
            [](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                return zmPlayerCount(world, call);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmplayerzone" },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                return zmPlayerZone(world, call, zmZoneProvider_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmcooperativezonesource" },
            [](SvServerWorld &, const SvScriptBuiltinCall &call) {
                return zmCooperativeZoneSource(call);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmcooperativespawnzones" },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                return zmCooperativeSpawnZones(world, call, zmZoneProvider_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Function, "zmzoneadjacentcount" },
            [this](SvServerWorld &, const SvScriptBuiltinCall &call) {
                return zmZoneAdjacentCount(call, zmZoneProvider_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Function, "zmzoneadjacentat" },
            [this](SvServerWorld &, const SvScriptBuiltinCall &call) {
                return zmZoneAdjacentAt(call, zmZoneProvider_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Function, "zmspawncrossesbarrier" },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                return zmSpawnCrossesBarrier(world, call, zmZoneProvider_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmsetround" },
            [](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                return zmSetRound(world, call);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "zmspawngoal" },
            [this](SvServerWorld &, const SvScriptBuiltinCall &call) {
                return zmSpawnGoal(call, zmZoneProvider_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Function,
                "setmapgameobjects",
            },
            setMapGameObjects);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "getentarray" },
            getEntArray);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "weaponindex" },
            [this](SvServerWorld &, const SvScriptBuiltinCall &call) {
                return weaponIndex(call, weaponResolver_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "sethealth" },
            setEntityHealth);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "setcandamage" },
            setCanDamage);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "setmodel" },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                return setModel(world, call, modelResolver_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "setmodelat" },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                return setModelAt(world, call, modelResolver_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "spawnmodel" },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                return spawnModel(world, call, modelResolver_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Function,
                "spawngroundtiltcontroller",
            },
            spawnGroundTiltController);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "setgroundtilttrajectory",
            },
            setGroundTiltTrajectory);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "playersetgroundreferenceent",
            },
            playerSetGroundReferenceEnt);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "playanimation" },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                return playAnimation(world, call, animationResolver_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "playsoundat" },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                return playSoundAt(world, call, soundResolver_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Function,
                "triggerexploder",
            },
            triggerExploder);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "firemagicat" },
            fireMagicAt);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "playfxat" },
            playFxAt);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "playfxontag" },
            playFxOnTag);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Function,
                "spawnscriptedmissile",
            },
            spawnScriptedMissile);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "setscriptedmissile",
            },
            setScriptedMissile);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Function, "earthquakeat" },
            earthquakeAt);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Function,
                "physicsexplosionsphereat",
            },
            physicsExplosionSphereAt);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Function,
                "radiusdamageat",
            },
            radiusDamageAt);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "spawnactor" },
            spawnActor);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "setactorstate" },
            setActorState);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "setactorposition",
            },
            setActorPosition);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "setactorpositions",
            },
            setActorPositions);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "actorfire" },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                return actorFire(world, call, weaponResolver_, true);
            });
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "actortracedamage",
            },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                return actorFire(world, call, weaponResolver_, false);
            });
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "actorfirepresentation",
            },
            actorFirePresentation);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "actorcorpse" },
            actorCorpse);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "setagentfield" },
            setAgentField);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "delete" },
            deleteEntity);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "setloot" },
            setLoot);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "getvelocity" },
            getVelocity);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "getorigin" },
            getOrigin);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "setscriptedposition",
            },
            setScriptedPosition);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "setscriptedviewangles",
            },
            setScriptedViewAngles);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "setscriptedviewclamp",
            },
            setScriptedViewClamp);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "setscriptedlinkstate",
            },
            setScriptedLinkState);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "clearscriptedposition",
            },
            clearScriptedPosition);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "setshellshock",
            },
            setShellshock);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "setobjective" },
            setObjective);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "getentitynumber" },
            getEntityNumber);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "sendservercommand",
            },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                std::optional<SvPlayerState> playerState;
                if (const auto invalid = validatePlayerMethod(
                        world, call, 1, playerState))
                {
                    return *invalid;
                }
                const auto *command =
                    std::get_if<std::string>(&call.arguments[0]);
                if (!command || command->empty() || command->size() >= 1024 ||
                    command->find('\0') != std::string::npos)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentValue,
                        "sendservercommand expects a non-empty command shorter than 1024 bytes");
                }
                if (!missionCallbacks_.sendServerCommand ||
                    !missionCallbacks_.sendServerCommand(
                        call.self->id, *command))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::MatchStateUnavailable,
                        "sendservercommand could not queue the command");
                }
                return success(std::monostate{});
            });
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Function,
                "setconfigstring",
            },
            [this](SvServerWorld &, const SvScriptBuiltinCall &call) {
                if (call.self)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidSelf,
                        "setconfigstring is a function");
                }
                if (call.arguments.size() != 2)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentCount,
                        "setconfigstring expects an index and value");
                }
                const auto *index =
                    std::get_if<std::int64_t>(&call.arguments[0]);
                const auto *value =
                    std::get_if<std::string>(&call.arguments[1]);
                if (!index || !value || *index < 0 ||
                    *index > std::numeric_limits<std::uint16_t>::max() ||
                    value->size() >= 1000 ||
                    value->find('\0') != std::string::npos)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentValue,
                        "setconfigstring expects a uint16 index and value shorter than 1000 bytes");
                }
                if (!missionCallbacks_.setConfigString ||
                    !missionCallbacks_.setConfigString(
                        static_cast<std::uint16_t>(*index), *value))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::MatchStateUnavailable,
                        "setconfigstring could not update authoritative state");
                }
                return success(std::monostate{});
            });
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Function,
                "servertime",
            },
            [](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                if (call.self)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidSelf,
                        "servertime is a function");
                }
                if (!call.arguments.empty())
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentCount,
                        "servertime expects no arguments");
                }
                return success(
                    static_cast<std::int64_t>(world.snapshot().serverTime));
            });
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Function,
                "finishmission",
            },
            [this](SvServerWorld &, const SvScriptBuiltinCall &call) {
                if (call.self)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidSelf,
                        "finishmission is a function");
                }
                if (!call.arguments.empty())
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentCount,
                        "finishmission expects no arguments");
                }
                if (!missionCallbacks_.finishMission ||
                    !missionCallbacks_.finishMission())
                {
                    return failure(
                        SvScriptBuiltinErrorCode::MatchStateUnavailable,
                        "finishmission is unavailable outside an active campaign mission");
                }
                return success(std::monostate{});
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "getmapfield" },
            getMapEntityField);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "istouching" },
            isTouchingPlayer);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "giveweapon" },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                return giveWeapon(world, call, weaponResolver_);
            });
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "setplayerweapons",
            },
            setPlayerWeapons);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "setplayerweaponammo",
            },
            setPlayerWeaponAmmo);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "isonground" },
            isOnGround);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "issameteam" },
            isSameTeam);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "setweaponammoclip",
            },
            setWeaponAmmoClip);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "setweaponammostock",
            },
            setWeaponAmmoStock);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "respawn" },
            respawn);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "savecheckpoint",
            },
            saveCheckpoint);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "finishplayerdamage",
            },
            finishPlayerDamage);
        handlers_.emplace(
            SvScriptBuiltinId{
                SvScriptBuiltinKind::Method,
                "finishsharedplayerdamage",
            },
            finishSharedPlayerDamage);
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "addscore" },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                std::optional<SvPlayerState> playerState;
                if (const auto invalid = validatePlayerMethod(
                        world, call, 1, playerState))
                {
                    return *invalid;
                }
                const auto *delta = std::get_if<std::int64_t>(&call.arguments[0]);
                if (!delta || *delta < -1'000'000 || *delta > 1'000'000)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentValue,
                        "addscore expects a bounded integer delta");
                }
                if (!matchScoreCallbacks_.addClientScore ||
                    !matchScoreCallbacks_.addClientScore(
                        call.self->id, static_cast<std::int32_t>(*delta)))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::MatchStateUnavailable,
                        "addscore could not update authoritative match state");
                }
                return success(std::monostate{});
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "addxp" },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                std::optional<SvPlayerState> playerState;
                if (const auto invalid = validatePlayerMethod(
                        world, call, 1, playerState))
                {
                    return *invalid;
                }
                const auto *delta = std::get_if<std::int64_t>(&call.arguments[0]);
                if (!delta || *delta < -1'000'000 || *delta > 1'000'000)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentValue,
                        "addxp expects a bounded integer delta");
                }
                if (!matchScoreCallbacks_.addClientXp ||
                    !matchScoreCallbacks_.addClientXp(
                        call.self->id, static_cast<std::int32_t>(*delta)))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::MatchStateUnavailable,
                        "addxp could not update authoritative match state");
                }
                return success(std::monostate{});
            });
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "addteamscore" },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                std::optional<SvPlayerState> playerState;
                if (const auto invalid = validatePlayerMethod(
                        world, call, 1, playerState))
                {
                    return *invalid;
                }
                const auto *delta = std::get_if<std::int64_t>(&call.arguments[0]);
                if (!delta || *delta < -1'000'000 || *delta > 1'000'000)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentValue,
                        "addteamscore expects a bounded integer delta");
                }
                if (!matchScoreCallbacks_.addTeamScoreForClient ||
                    !matchScoreCallbacks_.addTeamScoreForClient(
                        call.self->id, static_cast<std::int32_t>(*delta)))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::MatchStateUnavailable,
                        "addteamscore could not update authoritative match state");
                }
                return success(std::monostate{});
            });
        // Free-for-all's counterpart to addteamscore. cha keeps the DISPLAY score
        // and the counter the limit reads apart - addscore 100 for the scoreboard,
        // addteamscore 1 for the 50-kill limit - and free-for-all has no team to
        // put the second one on. Without it the only counter left was the 100 per
        // kill display score, which crosses a 30 limit on the first kill and ended
        // every match immediately.
        handlers_.emplace(
            SvScriptBuiltinId{ SvScriptBuiltinKind::Method, "addkill" },
            [this](SvServerWorld &world, const SvScriptBuiltinCall &call) {
                std::optional<SvPlayerState> playerState;
                if (const auto invalid = validatePlayerMethod(
                        world, call, 1, playerState))
                {
                    return *invalid;
                }
                const auto *delta = std::get_if<std::int64_t>(&call.arguments[0]);
                if (!delta || *delta < -1'000'000 || *delta > 1'000'000)
                {
                    return failure(
                        SvScriptBuiltinErrorCode::InvalidArgumentValue,
                        "addkill expects a bounded integer delta");
                }
                if (!matchScoreCallbacks_.addKillForClient ||
                    !matchScoreCallbacks_.addKillForClient(
                        call.self->id, static_cast<std::int32_t>(*delta)))
                {
                    return failure(
                        SvScriptBuiltinErrorCode::MatchStateUnavailable,
                        "addkill could not update authoritative match state");
                }
                return success(std::monostate{});
            });
    }

    void SvScriptBuiltinRegistry::setAnimationResolver(
        AnimationResolver resolver)
    {
        animationResolver_ = std::move(resolver);
    }

    bool SvScriptBuiltinRegistry::contains(
        const SvScriptBuiltinKind kind,
        const std::string_view name) const
    {
        return handlers_.contains({ kind, std::string(name) });
    }

    std::size_t SvScriptBuiltinRegistry::size() const
    {
        return handlers_.size();
    }

    SvScriptBuiltinResult SvScriptBuiltinRegistry::invoke(
        const SvScriptBuiltinKind kind,
        const std::string_view name,
        const std::optional<SvScriptObjectRef> self,
        const std::span<const SvScriptValue> arguments) const
    {
        SvScriptBuiltinCall call{
            .id = { kind, std::string(name) },
            .self = self,
            .arguments = { arguments.begin(), arguments.end() },
        };
        const auto handler = handlers_.find(call.id);
        if (handler == handlers_.end())
        {
            return failure(
                SvScriptBuiltinErrorCode::UnknownBuiltin,
                "unknown script builtin: " + call.id.name);
        }
        return handler->second(world_, call);
    }
}
