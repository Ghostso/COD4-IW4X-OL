#include "server_mp/sv_script_builtin_mp.hpp"
#include "server_mp/sv_script_lua_mp.hpp"
#include "server_mp/sv_script_source_mp.hpp"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace
{
    void require(const bool condition, const std::string &message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }
}

int main()
{
    try
    {
        using namespace CodolGameServer;

        SvServerWorld world;
        const SvResolvedLoadout loadout{
            .primary = {
                .weaponAssetIndex = 165,
                .ammoIndex = 101,
                .clipIndex = 201,
                .clipSize = 30,
                .maxAmmo = 120,
                .fireType = 0,
                .fireTimeMilliseconds = 100,
                .dropTimeMilliseconds = 100,
                .raiseTimeMilliseconds = 120,
                .damageCurve = {
                    .damage = { 33, 33, 33, 0, 0, 24 },
                    .ranges = { 500.0f, 501.0f, 1600.0f, 0.0f, 0.0f, 1601.0f },
                },
                .hitLocationMultipliers = {
                    1.0f, 1.4f, 1.4f, 1.4f, 1.2f, 0.9f, 0.8f,
                    0.8f, 0.6f, 0.6f, 0.1f, 0.1f, 0.5f, 0.5f,
                    0.4f, 0.4f, 0.1f, 0.1f, 0.0f, 0.0f, 1.0f,
                },
                .weaponName = "m4a1tech_mp",
            },
            .secondary = {
                .weaponAssetIndex = 77,
                .ammoIndex = 102,
                .clipIndex = 202,
                .clipSize = 12,
                .maxAmmo = 48,
                .fireType = 1,
                .fireTimeMilliseconds = 200,
                .dropTimeMilliseconds = 80,
                .raiseTimeMilliseconds = 100,
                .damageCurve = {
                    .damage = { 50, 45, 45, 33, 24, 19 },
                    .ranges = { 275.0f, 276.0f, 700.0f, 701.0f, 900.0f, 1200.0f },
                },
                .hitLocationMultipliers = {
                    1.0f, 1.4f, 1.4f, 1.4f, 1.2f, 0.9f, 0.8f,
                    0.8f, 0.6f, 0.6f, 0.1f, 0.1f, 0.5f, 0.5f,
                    0.4f, 0.4f, 0.1f, 0.1f, 0.0f, 0.0f, 1.0f,
                },
                .weaponName = "fa1911ncm_mp",
            },
        };
        std::array<std::uint16_t, 11> characterSelections{};
        characterSelections[2] = 20;
        const auto characterCustomization = SV_ResolveCharacterCustomization(
            characterSelections,
            true,
            1,
            54,
            SvCharacterFaction::Tf);
        require(
            characterCustomization.has_value(),
            "Lua runtime fixture resolves a valid native character presentation");
        const std::array<SvWorldClientInput, 2> clients{
            SvWorldClientInput{
                .clientNum = 0,
                .gameplayState = ClientGameplayState::Playing,
                .team = SvTeam::Tf,
                .loadoutSequence = 1,
                .spawnSequence = 1,
                .resolvedLoadout = loadout,
                .characterCustomization = *characterCustomization,
            },
            SvWorldClientInput{
                .clientNum = 1,
                .gameplayState = ClientGameplayState::Playing,
                .team = SvTeam::Tf,
                .loadoutSequence = 1,
                .spawnSequence = 1,
                .resolvedLoadout = loadout,
                .characterCustomization = *characterCustomization,
            },
        };
        world.setSharedPmoveRunner([](
            SvNativePlayerState &nativePlayerState,
            const SvGameClientCommandState &commandState,
            const SvResolvedLoadout *,
            const SvGlassState &,
            const std::span<const SvCollisionEntity>,
            SvNativePmoveOutput &) {
            SvPlayerState playerState;
            if (!SV_OverlayNativePlayerStateToPlayerState(
                    nativePlayerState,
                    playerState))
            {
                return false;
            }
            playerState.commandTime = commandState.currentUserCmd.commandTime;
            SV_OverlayPlayerStateToNative(playerState, nativePlayerState);
            return true;
        });
        world.setWeaponMovementRunner([](
            const SvWeaponMovementFrameInput &input,
            SvWeaponMovementClientState &,
            const SvResolvedLoadout *resolvedLoadout,
            SvNativeWeaponMovementOutput &) {
            return input.playerState && input.frameTime > 0.0f &&
                resolvedLoadout;
        });
        world.setPlayerStateToEntityStateConverter([](
            SvNativePlayerState &nativePlayerState,
            SvNativeEntityState &nativeEntityState,
            SvNativeEntityStateProjection &projection) {
            SvPlayerState playerState;
            if (!SV_OverlayNativePlayerStateToPlayerState(
                    nativePlayerState, playerState))
                return false;
            const auto decoded = SV_ReadNativeEntityState(nativeEntityState);
            if (!decoded)
                return false;
            projection = *decoded;
            projection.origin = playerState.origin;
            projection.angles = playerState.viewAngles;
            projection.groundEntityNum = playerState.groundEntityNum;
            return true;
        });
        world.setClientEventsHandler([](
            SvPlayerState &,
            const SvGameEntity &,
            const SvNativePlayerState &,
            const SvWeaponAimState &,
            float,
            std::uint32_t,
            SvGlassState &,
            SvGlassDamageState &,
            const SvGlassMapMetadata &,
            std::span<const SvCollisionEntity>,
            std::span<const SvDamageablePlayerView>,
            const SvResolvedLoadout *,
            const std::span<const SvNativePredictableEvent>) {
            return SvClientEventResult::Applied;
        });
        const std::array LuaScriptModels{
            SvScriptModelEntityDefinition{
                .origin = { 40.0f, 50.0f, 60.0f },
                .modelIndex = 100,
                .modelName = "vehicle_uaz_destructible_mp",
                .targetName = "destructible_toy",
                .destructibleType = "vehicle_uaz",
            },
        };
        const std::array LogicalMapEntities{
            SvLogicalMapEntityDefinition{
                .mapOrdinal = 42,
                .fields = {
                    { "classname", "actor_enemy_ship_ar_ak_so" },
                    { "targetname", "deck_wave_one" },
                    { "script_parameters", "bridge" },
                },
                .origin = { 100.0f, 200.0f, 300.0f },
                .angles = { 0.0f, 180.0f, 0.0f },
                .hasOrigin = true,
                .hasAngles = true,
            },
            SvLogicalMapEntityDefinition{
                .mapOrdinal = 43,
                .fields = {
                    { "classname", "trigger_radius" },
                    { "targetname", "bridge_breach_trigger" },
                    { "script_flag", "bridge_player_ready_breach" },
                    { "spawnflags", "1" },
                    { "radius", "64" },
                    { "height", "128" },
                },
                .origin = { 10.0f, 20.0f, 0.0f },
                .hasOrigin = true,
            },
        };
        require(
            world.configureSpawnAndBrushModelEntities(
                { 10.0f, 20.0f, 30.0f },
                { 0.0f, 90.0f, 0.0f },
                FirstDynamicServerEntityNum,
                {},
                LuaScriptModels,
                {},
                {},
                {},
                LogicalMapEntities),
            "Lua runtime fixture configures a valid spawn and map entity");
        world.runFrame(50, clients);
        SvScriptBuiltinRegistry builtins(
            world,
            {},
            [](const std::string_view modelName)
                -> std::optional<std::uint16_t> {
                return modelName == "vehicle_uaz_destroyed"
                    ? std::optional<std::uint16_t>{ 101 }
                    : std::nullopt;
            },
            [](const std::string_view weaponName)
                -> std::optional<std::uint16_t> {
                return weaponName == "ak47_mp"
                    ? std::optional<std::uint16_t>{ 78 }
                    : std::nullopt;
            });
        const std::array<SvScriptValue, 2> getEntArrayArguments{
            std::string("destructible_toy"),
            std::string("targetname"),
        };
        const auto getEntArrayResult = builtins.invoke(
            SvScriptBuiltinKind::Function,
            "getentarray",
            std::nullopt,
            getEntArrayArguments);
        const auto *const queriedEntities =
            std::get_if<SvScriptObjectArray>(&getEntArrayResult.value);
        require(
            getEntArrayResult.succeeded() && queriedEntities &&
                queriedEntities->size() == 1 &&
                (*queriedEntities)[0].kind == SvScriptObjectKind::Entity &&
                (*queriedEntities)[0].id == FirstDynamicServerEntityNum &&
                (*queriedEntities)[0].entityGeneration.has_value(),
            "getentarray returns a generation-safe entity capability");
        const auto groundTiltSpawn = builtins.invoke(
            SvScriptBuiltinKind::Function,
            "spawngroundtiltcontroller");
        const auto *const groundTiltObject =
            std::get_if<SvScriptObjectRef>(&groundTiltSpawn.value);
        const std::array<SvScriptValue, 9> groundTiltArguments{
            std::int64_t{ 7 },
            std::int64_t{ 0 },
            std::int64_t{ 1000 },
            0.0, 0.0, 0.0,
            0.0, 0.0, -10.0,
        };
        const auto groundTiltSet = groundTiltObject
            ? builtins.invoke(
                SvScriptBuiltinKind::Method,
                "setgroundtilttrajectory",
                *groundTiltObject,
                groundTiltArguments)
            : SvScriptBuiltinResult{};
        const std::array<SvScriptValue, 1> groundReferenceArguments{
            groundTiltObject
                ? SvScriptValue{ *groundTiltObject }
                : SvScriptValue{ std::monostate{} },
        };
        const SvScriptObjectRef firstPlayer{
            .kind = SvScriptObjectKind::Player,
            .id = 0,
        };
        const auto groundReferenceSet = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "playersetgroundreferenceent",
            firstPlayer,
            groundReferenceArguments);
        require(
            groundTiltSpawn.succeeded() && groundTiltObject &&
                groundTiltObject->entityGeneration &&
                groundTiltSet.succeeded() &&
                groundReferenceSet.succeeded() &&
                world.runFrame(50, clients),
            "Wetwork ground tilt builtins publish a controller and select it for the player");
        const auto groundTiltHandle = SvEntityHandle{
            .entityNum = groundTiltObject ? groundTiltObject->id : 0,
            .generation =
                groundTiltObject && groundTiltObject->entityGeneration
                    ? *groundTiltObject->entityGeneration
                    : 0,
        };
        const auto groundTiltEntity = world.entity(groundTiltHandle);
        require(
            groundTiltEntity &&
                groundTiltEntity->networkState.eType ==
                    EntityTypeScriptMover &&
                groundTiltEntity->networkState.modelIndex == 0 &&
                groundTiltEntity->networkState.angleTrajectoryType == 7 &&
                groundTiltEntity->networkState.angleTrajectoryTime == 50 &&
                groundTiltEntity->networkState.angleTrajectoryDuration == 1000 &&
                groundTiltEntity->networkState.angles ==
                    SvScriptVector{ 0.0f, 0.0f, 0.0f } &&
                groundTiltEntity->networkState.angleTrajectoryDelta ==
                    SvScriptVector{ 0.0f, 0.0f, -10.0f } &&
                world.playerState(0)->linkEntityNum ==
                    groundTiltHandle.entityNum,
            "Wetwork ground tilt retains the measured mover trajectory and playerState reference");
        const auto groundReferenceClear = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "playersetgroundreferenceent",
            firstPlayer);
        const auto groundTiltDelete = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "delete",
            groundTiltObject ? std::optional{ *groundTiltObject }
                             : std::nullopt);
        require(
            groundReferenceClear.succeeded() &&
                world.playerState(0)->linkEntityNum == EntityNumNone &&
                groundTiltDelete.succeeded() &&
                !world.entity(groundTiltHandle),
            "Wetwork ground reference clears before its generation-safe controller is deleted");
        const std::array<SvScriptValue, 2> actorArguments{
            std::string("actor_enemy_ship_ar_ak_so"),
            std::string("classname"),
        };
        const auto actorResult = builtins.invoke(
            SvScriptBuiltinKind::Function,
            "getentarray",
            std::nullopt,
            actorArguments);
        const auto *const actors =
            std::get_if<SvScriptObjectArray>(&actorResult.value);
        require(actorResult.succeeded() && actors && actors->size() == 1,
            "getentarray exposes logical campaign actor spawners");
        const std::array<SvScriptValue, 1> mapFieldArguments{
            std::string("script_parameters"),
        };
        const auto mapFieldResult = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "getmapfield",
            actors->front(),
            mapFieldArguments);
        const auto *const mapField =
            std::get_if<std::string>(&mapFieldResult.value);
        require(mapFieldResult.succeeded() && mapField && *mapField == "bridge",
            "getmapfield preserves campaign map vocabulary");
        const std::array<SvScriptValue, 5> spawnActorArguments{
            std::int64_t{ 6 },
            std::int64_t{ 262 },
            std::int64_t{ 2 },
            std::int64_t{ 1779 },
            std::int64_t{ 14'800 },
        };
        const auto spawnActorResult = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "spawnactor",
            actors->front(),
            spawnActorArguments);
        const auto *const spawnedActor =
            std::get_if<SvScriptObjectRef>(&spawnActorResult.value);
        require(
            spawnActorResult.succeeded() && spawnedActor &&
                spawnedActor->entityGeneration,
            "spawnactor materializes a campaign spawner");
        const SvEntityHandle spawnedActorHandle{
            .entityNum = spawnedActor->id,
            .generation = *spawnedActor->entityGeneration,
        };
        const auto actorEntity = world.entity(spawnedActorHandle);
        const auto actorState = world.actorAgentState(spawnedActorHandle);
        require(
            actorEntity && actorEntity->networkState.eType == EntityTypeActor &&
                actorEntity->networkState.scriptMoverBrushModelIndex == 262 &&
                actorEntity->currentOrigin == SvScriptVector{ 100.0f, 200.0f, 300.0f } &&
                actorEntity->currentAngles == SvScriptVector{ 0.0f, 180.0f, 0.0f } &&
                actorState && actorState->agentNum == 6 &&
                actorState->fields[SvAgentState::ModelField] == 262 &&
                actorState->fields[SvAgentState::EntityNumField] ==
                    spawnedActorHandle.entityNum &&
                actorState->fields[SvAgentState::TeamField] == 2 &&
                actorState->fields[SvAgentState::AnimationField] == 1779 &&
                actorState->fields[SvAgentState::AnimationStartTimeField] == 14'800,
            "spawnactor joins authored transform to the measured agent presentation");
        const std::array<SvScriptValue, 4> setActorArguments{
            std::int64_t{ 260 },
            std::int64_t{ 2 },
            std::int64_t{ 258 },
            std::int64_t{ 16'700 },
        };
        const auto setActorResult = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "setactorstate",
            *spawnedActor,
            setActorArguments);
        const auto changedActorState = world.actorAgentState(spawnedActorHandle);
        require(
            setActorResult.succeeded() && changedActorState &&
                world.entity(spawnedActorHandle)
                    ->networkState.scriptMoverBrushModelIndex == 260 &&
                changedActorState->agentNum == 6 &&
                changedActorState->fields[SvAgentState::ModelField] == 260 &&
                changedActorState->fields[SvAgentState::EntityNumField] ==
                    spawnedActorHandle.entityNum &&
                changedActorState->fields[SvAgentState::AnimationField] == 258 &&
                changedActorState->fields[SvAgentState::AnimationStartTimeField] == 16'700,
            "setactorstate preserves the join while changing presentation");
        const std::array<SvScriptValue, 4> setActorPositionArguments{
            3293.1,
            -457.4,
            204.0,
            300.0,
        };
        const auto setActorPositionResult = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "setactorposition",
            *spawnedActor,
            setActorPositionArguments);
        const auto movedActor = world.entity(spawnedActorHandle);
        const auto movedActorCollision = world.collisionEntity(
            spawnedActorHandle.entityNum);
        require(
            setActorPositionResult.succeeded() && movedActor &&
                movedActorCollision &&
                movedActor->currentOrigin ==
                    SvScriptVector{ 3293.1f, -457.4f, 204.0f } &&
                movedActor->currentAngles ==
                    SvScriptVector{ 0.0f, 300.0f, 0.0f } &&
                movedActorCollision->origin == movedActor->currentOrigin,
            "setactorposition moves campaign presentation and collision together");
        const std::array<SvScriptValue, 2> attachmentArguments{
            std::int64_t{ 13 },
            std::int64_t{ 479 },
        };
        const auto attachmentResult = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "setagentfield",
            *spawnedActor,
            attachmentArguments);
        require(
            attachmentResult.succeeded() &&
                world.actorAgentState(spawnedActorHandle)
                    ->fields[13] == 479,
            "setagentfield exposes measured campaign attachment fields");
        const auto actorFireQueued = world.queueActorPresentationEvent(
            spawnedActorHandle, { 41, 0 });
        const auto actorAfterFire = world.entity(spawnedActorHandle);
        require(
            actorFireQueued && actorAfterFire &&
                actorAfterFire->networkState.eventSequence == 1 &&
                actorAfterFire->networkState.torsoAnim == 1208 &&
                actorAfterFire->networkState.events[0] ==
                    SvEntityEvent{ 41, 0 },
            "campaign actors publish the demo's EV_FIRE_WEAPON ring event");
        require(
            builtins.contains(SvScriptBuiltinKind::Method, "actorfire"),
            "the Lua bridge exposes traced campaign actor fire");
        require(
            builtins.contains(
                SvScriptBuiltinKind::Method, "setplayerweapons"),
            "the Lua bridge exposes authoritative campaign arsenal changes");
        require(
            builtins.contains(
                SvScriptBuiltinKind::Method, "setplayerweaponammo"),
            "the Lua bridge exposes exact campaign ammunition changes");
        require(
            builtins.contains(
                SvScriptBuiltinKind::Method, "actortracedamage"),
            "the Lua bridge separates campaign actor damage from presentation");
        require(
            builtins.contains(
                SvScriptBuiltinKind::Method, "actorfirepresentation"),
            "the Lua bridge exposes projectile-only actor fire presentation");
        require(
            builtins.contains(SvScriptBuiltinKind::Method, "actorcorpse"),
            "the Lua bridge exposes the recorded campaign actor death transition");
        require(
            builtins.contains(SvScriptBuiltinKind::Method, "playfxontag"),
            "the Lua bridge exposes the Wetwork extraction tag effect");
        require(
            builtins.contains(SvScriptBuiltinKind::Function, "radiusdamageat"),
            "the Lua bridge exposes Wetwork's recorded radius-damage effects");
        require(
            builtins.contains(SvScriptBuiltinKind::Function, "firemagicat"),
            "the Lua bridge exposes Wetwork's opening fire-magic event");
        const auto duplicateActorResult = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "spawnactor",
            actors->front(),
            spawnActorArguments);
        require(
            duplicateActorResult.succeeded() &&
                std::holds_alternative<std::monostate>(duplicateActorResult.value),
            "spawnactor refuses a duplicate active agent slot without leaking a handle");
        const auto actorCorpseResult = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "actorcorpse",
            *spawnedActor,
            std::array<SvScriptValue, 1>{ true });
        const auto retainedCorpse = world.entity(spawnedActorHandle);
        require(
            actorCorpseResult.succeeded() &&
                std::get_if<bool>(&actorCorpseResult.value) &&
                *std::get_if<bool>(&actorCorpseResult.value) &&
                retainedCorpse &&
                retainedCorpse->networkState.eType == EntityTypeActorCorpse &&
                retainedCorpse->networkState.scriptMoverBrushModelIndex == 0 &&
                retainedCorpse->networkState.positionTrajectoryType ==
                    SvCorpseRagdollTrajectoryType &&
                retainedCorpse->networkState.angleTrajectoryType ==
                    SvCorpseRagdollAngleTrajectoryType &&
                !world.actorAgentState(spawnedActorHandle),
            "actorcorpse can begin a retained blast victim in local ragdoll trajectories");
        require(
            std::ranges::none_of(
                world.snapshot().entities,
                [entityNum = actors->front().id](const auto &entity) {
                    return entity.number == entityNum;
                }),
            "logical campaign entities remain absent from snapshots");
        const std::array<SvScriptValue, 2> triggerArguments{
            std::string("bridge_player_ready_breach"),
            std::string("script_flag"),
        };
        const auto triggerResult = builtins.invoke(
            SvScriptBuiltinKind::Function,
            "getentarray",
            std::nullopt,
            triggerArguments);
        const auto *const triggers =
            std::get_if<SvScriptObjectArray>(&triggerResult.value);
        require(triggerResult.succeeded() && triggers && triggers->size() == 1,
            "getentarray queries campaign-specific trigger fields");
        const std::array<SvScriptValue, 1> touchingArguments{
            SvScriptObjectRef{
                .kind = SvScriptObjectKind::Player,
                .id = 0,
            },
        };
        const auto touchingResult = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "istouching",
            triggers->front(),
            touchingArguments);
        const auto *const isTouching =
            std::get_if<bool>(&touchingResult.value);
        require(touchingResult.succeeded() && isTouching && *isTouching,
            "istouching applies trigger_radius bounds to the player box");

        const std::array<SvScriptValue, 1> setModelArguments{
            std::string("vehicle_uaz_destroyed"),
        };
        const auto setModelResult = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "setmodel",
            queriedEntities->front(),
            setModelArguments);
        const std::array<SvScriptValue, 1> unknownModelArguments{
            std::string("missing_model"),
        };
        const auto unknownModelResult = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "setmodel",
            queriedEntities->front(),
            unknownModelArguments);
        const auto queriedModelHandle = SvEntityHandle{
            .entityNum = queriedEntities->front().id,
            .generation = *queriedEntities->front().entityGeneration,
        };
        const auto entityNumberResult = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "getentitynumber",
            queriedEntities->front(),
            {});
        const auto *const entityNumber =
            std::get_if<std::int64_t>(&entityNumberResult.value);
        require(
            entityNumberResult.succeeded() && entityNumber &&
                *entityNumber == queriedModelHandle.entityNum &&
                setModelResult.succeeded() &&
                world.entity(queriedModelHandle)->networkState.modelIndex == 101 &&
                unknownModelResult.error.code ==
                    SvScriptBuiltinErrorCode::InvalidArgumentValue,
            "setmodel resolves a known asset before updating a generation-safe script model");
        const std::array<SvScriptValue, 1> enableDamageArguments{ true };
        const auto enableBeforeHealth = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "setcandamage",
            queriedEntities->front(),
            enableDamageArguments);
        const std::array<SvScriptValue, 1> setHealthArguments{
            std::int64_t{ 50 },
        };
        const auto setHealthResult = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "sethealth",
            queriedEntities->front(),
            setHealthArguments);
        const auto enableDamageResult = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "setcandamage",
            queriedEntities->front(),
            enableDamageArguments);
        const std::array<SvScriptValue, 1> disableDamageArguments{ false };
        const auto disableDamageResult = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "setcandamage",
            queriedEntities->front(),
            disableDamageArguments);
        const auto reenableDamageResult = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "setcandamage",
            queriedEntities->front(),
            enableDamageArguments);
        const auto queriedHandle = SvEntityHandle{
            .entityNum = queriedEntities->front().id,
            .generation = *queriedEntities->front().entityGeneration,
        };
        const auto configuredDamageState = world.entityDamageState(queriedHandle);
        const auto unsafeSetHealth = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "sethealth",
            SvScriptObjectRef{
                .kind = SvScriptObjectKind::Entity,
                .id = queriedHandle.entityNum,
            },
            setHealthArguments);
        auto staleObject = queriedEntities->front();
        ++*staleObject.entityGeneration;
        const auto staleSetHealth = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "sethealth",
            staleObject,
            setHealthArguments);
        require(
            !enableBeforeHealth.succeeded() && setHealthResult.succeeded() &&
                enableDamageResult.succeeded() && disableDamageResult.succeeded() &&
                reenableDamageResult.succeeded() && configuredDamageState &&
                configuredDamageState->health == 50 &&
                configuredDamageState->canTakeDamage &&
                !unsafeSetHealth.succeeded() && !staleSetHealth.succeeded(),
            "entity health and takedamage require ordered generation-safe mutation");
        SvLuaRuntime runtime(builtins);
        require(
            runtime.status() == SvLuaRuntimeStatus{},
            "Lua runtime starts without an active generation");

        SvLuaRuntime schedulerRuntime(builtins);
        constexpr std::string_view SchedulerSource = R"lua(
assert(codol.thread(function()
    print("thread_start")
    codol.wait(50)
    print("thread_after_50")
    codol.wait(0)
    print("thread_next_frame")
end))
assert(codol.on("client_spawned", function(_, event)
    print("spawn_wait_start", event.server_time)
    codol.wait(100)
    print("spawn_wait_done")
end))
assert(codol.on("weapon_switch_started", function()
    codol.wait(10)
    error("resumed callback boom")
end))
)lua";
        require(
            schedulerRuntime.reload("tests/scheduler.lua", SchedulerSource) &&
                schedulerRuntime.status().scheduledThreadCount == 1,
            "Lua source can start one generation-owned managed thread");
        const auto schedulerBootLogs = schedulerRuntime.takeLogs();
        require(
            schedulerBootLogs.size() == 1 &&
                schedulerBootLogs[0].message == "thread_start" &&
                schedulerRuntime.advance(49) &&
                schedulerRuntime.takeLogs().empty() &&
                schedulerRuntime.status().scheduledThreadCount == 1 &&
                schedulerRuntime.advance(50),
            "managed threads remain suspended before their server-time deadline");
        const auto schedulerDeadlineLogs = schedulerRuntime.takeLogs();
        require(
            schedulerDeadlineLogs.size() == 1 &&
                schedulerDeadlineLogs[0].message == "thread_after_50" &&
                schedulerRuntime.status().scheduledThreadCount == 1 &&
                schedulerRuntime.advance(50),
            "a zero wait remains queued until a subsequent server frame");
        const auto schedulerNextFrameLogs = schedulerRuntime.takeLogs();
        require(
            schedulerNextFrameLogs.size() == 1 &&
                schedulerNextFrameLogs[0].message == "thread_next_frame" &&
                schedulerRuntime.status().scheduledThreadCount == 0,
            "a managed thread completes and releases its registry owner exactly once");
        const std::array schedulerSpawnEvents{
            SvWorldEvent{
                .sequence = 1,
                .type = SvWorldEventType::ClientSpawned,
                .serverTime = 100,
                .clientNum = 0,
                .spawnSequence = 1,
                .spawnGeneration = 1,
            },
        };
        require(
            schedulerRuntime.dispatchWorldEvents(schedulerSpawnEvents) &&
                schedulerRuntime.status().scheduledThreadCount == 1,
            "world callbacks may suspend without blocking event dispatch");
        const auto schedulerSpawnStartLogs = schedulerRuntime.takeLogs();
        require(
            schedulerSpawnStartLogs.size() == 1 &&
                schedulerSpawnStartLogs[0].message == "spawn_wait_start\t100" &&
                schedulerRuntime.advance(199) &&
                schedulerRuntime.takeLogs().empty() &&
                schedulerRuntime.advance(200),
            "event waits use the authoritative event server time as their base");
        const auto schedulerSpawnDoneLogs = schedulerRuntime.takeLogs();
        require(
            schedulerSpawnDoneLogs.size() == 1 &&
                schedulerSpawnDoneLogs[0].message == "spawn_wait_done" &&
                schedulerRuntime.status().scheduledThreadCount == 0,
            "a suspended world callback resumes at its exact deadline");
        const std::array schedulerWeaponEvents{
            SvWorldEvent{
                .sequence = 2,
                .type = SvWorldEventType::WeaponSwitchStarted,
                .serverTime = 200,
                .clientNum = 0,
                .spawnSequence = 1,
                .spawnGeneration = 1,
                .weaponAssetIndex = 165,
                .weaponName = "m4a1tech_mp",
            },
        };
        require(
            schedulerRuntime.dispatchWorldEvents(schedulerWeaponEvents) &&
                !schedulerRuntime.advance(210) &&
                schedulerRuntime.status().loaded &&
                schedulerRuntime.status().scheduledThreadCount == 0,
            "a resumed callback error is isolated without unloading its generation");
        const auto resumedCallbackLogs = schedulerRuntime.takeLogs();
        require(
            resumedCallbackLogs.size() == 1 &&
                resumedCallbackLogs[0].kind == SvLuaLogKind::RuntimeError &&
                resumedCallbackLogs[0].message.find("resumed callback boom") !=
                    std::string::npos &&
                resumedCallbackLogs[0].traceback.find("tests/scheduler.lua") !=
                    std::string::npos,
            "resumed callback failures retain source and coroutine traceback evidence");
        require(
            schedulerRuntime.dispatchWorldEvents(schedulerSpawnEvents) &&
                schedulerRuntime.status().scheduledThreadCount == 1,
            "scheduler reset fixture owns one pending callback");
        static_cast<void>(schedulerRuntime.takeLogs());
        schedulerRuntime.reset();
        require(
            schedulerRuntime.status() == SvLuaRuntimeStatus{
                .generation = 2,
                .loaded = false,
            } &&
                schedulerRuntime.advance(500) &&
                schedulerRuntime.takeLogs().empty(),
            "reset destroys every pending thread with the old VM generation");

        SvLuaRuntime resumeBudgetRuntime(builtins, {
            .maximumMemoryBytes = 1024 * 1024,
            .maximumInstructionsPerRun = 100'000,
            .instructionHookInterval = 100,
            .maximumSourceBytes = 4096,
            .maximumScheduledThreads = 4,
            .maximumThreadResumesPerFrame = 1,
        });
        require(
            resumeBudgetRuntime.reload("tests/resume_budget.lua", R"lua(
assert(codol.thread(function() codol.wait(10); print("first") end))
assert(codol.thread(function() codol.wait(10); print("second") end))
)lua") &&
                resumeBudgetRuntime.status().scheduledThreadCount == 2 &&
                resumeBudgetRuntime.advance(10),
            "thread scheduler accepts bounded concurrent waits");
        const auto firstBudgetLogs = resumeBudgetRuntime.takeLogs();
        require(
            firstBudgetLogs.size() == 1 &&
                firstBudgetLogs[0].message == "first" &&
                resumeBudgetRuntime.status().scheduledThreadCount == 1 &&
                resumeBudgetRuntime.advance(10),
            "per-frame resume budget leaves later due threads queued in order");
        const auto secondBudgetLogs = resumeBudgetRuntime.takeLogs();
        require(
            secondBudgetLogs.size() == 1 &&
                secondBudgetLogs[0].message == "second" &&
                resumeBudgetRuntime.status().scheduledThreadCount == 0,
            "a subsequent frame drains the next due thread without starvation");

        SvLuaRuntime resumedInstructionLimitRuntime(builtins, {
            .maximumMemoryBytes = 1024 * 1024,
            .maximumInstructionsPerRun = 10'000,
            .instructionHookInterval = 100,
            .maximumSourceBytes = 4096,
        });
        require(
            resumedInstructionLimitRuntime.reload(
                "tests/resumed_instruction_limit.lua", R"lua(
assert(codol.thread(function()
    codol.wait(1)
    while true do end
end))
)lua") &&
                !resumedInstructionLimitRuntime.advance(1),
            "instruction budget remains active after a managed thread resumes");
        const auto resumedInstructionLogs =
            resumedInstructionLimitRuntime.takeLogs();
        require(
            resumedInstructionLogs.size() == 1 &&
                resumedInstructionLogs[0].kind == SvLuaLogKind::RuntimeError &&
                resumedInstructionLogs[0].message.find("instruction budget") !=
                    std::string::npos,
            "resumed instruction exhaustion produces one bounded runtime error");

        SvLuaRuntime nestedThreadBudgetRuntime(builtins, {
            .maximumMemoryBytes = 1024 * 1024,
            .maximumInstructionsPerRun = 10'000,
            .instructionHookInterval = 100,
            .maximumSourceBytes = 4096,
        });
        require(
            !nestedThreadBudgetRuntime.reload(
                "tests/nested_thread_budget.lua", R"lua(
while true do
    assert(codol.thread(function() end))
end
)lua"),
            "nested immediate threads cannot replenish the caller instruction budget");
        const auto nestedThreadBudgetLogs =
            nestedThreadBudgetRuntime.takeLogs();
        require(
            nestedThreadBudgetLogs.size() == 1 &&
                nestedThreadBudgetLogs[0].kind == SvLuaLogKind::RuntimeError &&
                nestedThreadBudgetLogs[0].message.find("instruction budget") !=
                    std::string::npos,
            "nested thread budget exhaustion remains one structured source error");

        SvLuaRuntime nestedCoroutineRuntime(builtins);
        require(
            nestedCoroutineRuntime.reload(
                "tests/nested_coroutine.lua", R"lua(
assert(codol.thread(function()
    codol.wait(1)
    assert(codol.thread(function()
        codol.wait(1)
        print("child_done")
    end))
    print("parent_done")
end))
)lua") &&
                nestedCoroutineRuntime.advance(1),
            "a resumed managed coroutine can start a child thread");
        const auto nestedParentLogs = nestedCoroutineRuntime.takeLogs();
        require(
            nestedParentLogs.size() == 1 &&
                nestedParentLogs[0].message == "parent_done" &&
                nestedCoroutineRuntime.status().scheduledThreadCount == 1 &&
                nestedCoroutineRuntime.advance(2),
            "nested child wait is scheduled relative to the parent resume frame");
        const auto nestedChildLogs = nestedCoroutineRuntime.takeLogs();
        require(
            nestedChildLogs.size() == 1 &&
                nestedChildLogs[0].message == "child_done" &&
                nestedCoroutineRuntime.status().scheduledThreadCount == 0,
            "nested child thread resumes and releases its registry owner");

        SvLuaRuntime topLevelWaitRuntime(builtins);
        require(
            !topLevelWaitRuntime.reload(
                "tests/top_level_wait.lua", "codol.wait(1)"),
            "codol.wait rejects an unmanaged top-level chunk");
        const auto topLevelWaitLogs = topLevelWaitRuntime.takeLogs();
        require(
            topLevelWaitLogs.size() == 1 &&
                topLevelWaitLogs[0].kind == SvLuaLogKind::RuntimeError &&
                topLevelWaitLogs[0].message.find("managed script thread") !=
                    std::string::npos,
            "unmanaged wait failure remains visible through structured logs");

        const auto sourceRoot = std::filesystem::current_path() / "build" /
            "test-temp" / "gameplay-source";
        std::error_code filesystemError;
        std::filesystem::remove_all(sourceRoot, filesystemError);
        require(!filesystemError, "gameplay source fixture starts cleanly");
        std::filesystem::create_directories(
            sourceRoot / "gametypes", filesystemError);
        std::filesystem::create_directories(sourceRoot / "maps", filesystemError);
        require(!filesystemError, "gameplay source fixture directories are created");
        const auto writeSource = [](const std::filesystem::path &path,
                                    const std::string_view source) {
            std::ofstream stream(path, std::ios::binary);
            stream.write(source.data(), static_cast<std::streamsize>(source.size()));
            return stream.good();
        };
        require(
            writeSource(sourceRoot / "common.lua", "order = {'common'}") &&
                writeSource(
                    sourceRoot / "gametypes" / "sd.lua",
                    "table.insert(order, 'gametype')") &&
                writeSource(
                    sourceRoot / "maps" / "mp_crash_tropical.lua",
                    "table.insert(order, 'map')"),
            "gameplay source fixture writes the three controlled layers");
        const auto loadedSource = SV_LoadGameplaySource(
            sourceRoot, "mp_crash_tropical", "sd");
        require(
            loadedSource.succeeded() &&
                loadedSource.gameplaySource.files == std::vector<std::string>{
                    "common.lua",
                    "gametypes/sd.lua",
                    "maps/mp_crash_tropical.lua",
                } &&
                loadedSource.gameplaySource.source.find("'common'") <
                    loadedSource.gameplaySource.source.find("'gametype'") &&
                loadedSource.gameplaySource.source.find("'gametype'") <
                    loadedSource.gameplaySource.source.find("'map'"),
            "controlled gameplay sources combine common, gametype, and map layers in stable order");
        require(
            SV_LoadGameplaySource(sourceRoot, "../escape", "sd").error ==
                    SvGameplaySourceLoadError::InvalidSelection &&
                SV_LoadGameplaySource(sourceRoot, "mp_crash_tropical", "sd", 8)
                        .error == SvGameplaySourceLoadError::SourceTooLarge &&
                SV_LoadGameplaySource(
                    sourceRoot / "missing", "mp_crash_tropical", "sd").error ==
                    SvGameplaySourceLoadError::NoSource,
            "gameplay source loading rejects traversal, bounded-size overflow, and missing generations");
        const auto productionSource = SV_LoadGameplaySource(
            std::filesystem::current_path() / "assets" / "game_scripts",
            "mp_crash_tropical",
            "sd");
        SvLuaRuntime productionRuntime(builtins);
        require(
            productionSource.succeeded() &&
                productionSource.gameplaySource.files ==
                    std::vector<std::string>{
                        "common.lua",
                        "gametypes/sd.lua",
                        "maps/mp_crash_tropical.lua",
                    } &&
                productionRuntime.reload(
                    productionSource.gameplaySource.sourceName,
                    productionSource.gameplaySource.source),
            "production common and SD gameplay sources load as one controlled generation");
        static_cast<void>(productionRuntime.takeLogs());
        const std::array<SvWorldEvent, 1> FriendlyFireEvent{
            SvWorldEvent{
                .sequence = 1,
                .type = SvWorldEventType::PlayerDamage,
                .serverTime = 50,
                .clientNum = 0,
                .spawnSequence = 1,
                .spawnGeneration = 1,
                .weaponAssetIndex = 165,
                .weaponName = "m4a1tech_mp",
                .playerDamage = SvPlayerDamagePayload{
                    .targetClientNum = 0,
                    .inflictorEntityNum = 1,
                    .attackerEntityNum = 1,
                    .damage = 33,
                    .damageFlags = 4,
                    .methodOfDeath = 2,
                    .weaponAssetIndex = 165,
                    .point = std::array<float, 3>{ 10.0f, 20.0f, 30.0f },
                    .direction = std::array<float, 3>{ 1.0f, 0.0f, 0.0f },
                    .hitLocation = 5,
                    .timeOffset = -25,
                    .boneIndex = 17,
                },
            },
        };
        require(
            productionRuntime.dispatchWorldEvents(FriendlyFireEvent) &&
                world.playerState(0)->health == 100 &&
                world.playerState(1)->health == 100,
            "SD friendly-fire mode zero suppresses same-team player damage");

        std::int32_t dmScore = 0;
        std::int32_t dmXp = 0;
        std::int32_t dmKills = 0;
        SvScriptBuiltinRegistry dmBuiltins(
            world,
            {
                .addClientScore = [&](const auto clientNum, const auto delta) {
                    if (clientNum != 1)
                        return false;
                    dmScore += delta;
                    return true;
                },
                .addClientXp = [&](const auto clientNum, const auto delta) {
                    if (clientNum != 1)
                        return false;
                    dmXp += delta;
                    return true;
                },
                .addKillForClient = [&](const auto clientNum, const auto delta) {
                    if (clientNum != 1)
                        return false;
                    dmKills += delta;
                    return true;
                },
            });
        const auto dmSource = SV_LoadGameplaySource(
            std::filesystem::current_path() / "assets" / "game_scripts",
            "mp_nuked",
            "dm");
        SvLuaRuntime dmRuntime(dmBuiltins);
        require(
            dmSource.succeeded() &&
                dmRuntime.reload(
                    dmSource.gameplaySource.sourceName,
                    dmSource.gameplaySource.source),
            "production DM gameplay source loads with the Nuketown map layer");
        static_cast<void>(dmRuntime.takeLogs());
        const auto dmKillEvent = [](const std::uint32_t sequence,
                                    const std::uint8_t hitLocation) {
            return SvWorldEvent{
                .sequence = sequence,
                .type = SvWorldEventType::PlayerKilled,
                .serverTime = static_cast<std::uint32_t>(sequence * 50),
                .clientNum = 0,
                .spawnSequence = 1,
                .spawnGeneration = 1,
                .weaponAssetIndex = 165,
                .weaponName = "m4a1tech_mp",
                .playerKilled = SvPlayerDeathState{
                    .damage = SvPlayerDamagePayload{
                        .targetClientNum = 0,
                        .inflictorEntityNum = 1,
                        .attackerEntityNum = 1,
                        .damage = 100,
                        .methodOfDeath = 2,
                        .weaponAssetIndex = 165,
                        .hitLocation = hitLocation,
                    },
                    .deathAnimationDuration = 725,
                    .serverTime = static_cast<std::uint32_t>(sequence * 50),
                },
            };
        };
        const std::array dmKillEvents{
            dmKillEvent(1, 5),
            dmKillEvent(2, 2),
        };
        require(
            dmRuntime.dispatchWorldEvents(dmKillEvents) &&
                dmScore == 100 && dmXp == 150 && dmKills == 2,
            "DM awards 50 score and XP per enemy kill plus 50 XP for a headshot");
        const auto campaignScriptRoot =
            std::filesystem::current_path() / "assets" / "game_scripts";
        const auto wetworkMetadata = SV_LoadMapScriptMetadata(
            campaignScriptRoot, "coop_training_mp_cargoship");
        const auto wetworkSource = SV_LoadGameplaySource(
            campaignScriptRoot, "coop_training_mp_cargoship", "coop");
        SvLuaRuntime wetworkRuntime(builtins);
        require(
            wetworkMetadata == std::optional{ SvMapScriptMetadata{} } &&
                wetworkSource.succeeded() &&
                wetworkSource.gameplaySource.files ==
                    std::vector<std::string>{
                        "common.lua",
                        "gametypes/coop.lua",
                        "maps/coop_training_mp_cargoship.lua",
                    } &&
                wetworkRuntime.reload(
                    wetworkSource.gameplaySource.sourceName,
                    wetworkSource.gameplaySource.source),
            "Wetwork loads campaign rules and its map layer without MP minimap corners");
        const auto wetworkLogs = wetworkRuntime.takeLogs();
        require(
            wetworkLogs.size() == 1 &&
                wetworkLogs[0].message ==
                    "campaign gametype initialized\tcoop",
            "Wetwork uses the campaign gametype instead of stale DM scoring rules");
        require(
            writeSource(
                sourceRoot / "maps" / "metadata.lua",
                "return { minimap_material = 'compass_test' }") &&
                writeSource(
                    sourceRoot / "maps" / "unbounded.lua",
                    "while true do end") &&
                writeSource(
                    sourceRoot / "maps" / "invalid_metadata.lua",
                    "return { minimap_material = 123 }") &&
                SV_LoadMapScriptMetadata(sourceRoot, "metadata") ==
                    std::optional{ SvMapScriptMetadata{
                        .miniMapMaterial = "compass_test",
                    } } &&
                !SV_LoadMapScriptMetadata(sourceRoot, "unbounded") &&
                !SV_LoadMapScriptMetadata(sourceRoot, "invalid_metadata"),
            "map metadata loading enforces exact declarations and interrupts unbounded chunks");

        constexpr std::string_view FirstSource = R"lua(
assert(package == nil and io == nil and os == nil and debug == nil)
assert(dofile == nil and loadfile == nil and load == nil)
assert(collectgarbage == nil and warn == nil)
assert(string.dump == nil and math.random == nil and math.randomseed == nil)

local player, object_error = codol.player(0)
assert(player ~= nil and object_error == nil)
assert(tostring(player) == "codol object")
local grounded, builtin_error, builtin_code = codol.call("method:isonground", player)
assert(grounded == true, tostring(builtin_error) .. ":" .. tostring(builtin_code))
assert(codol.call("method:issameteam", player, player) == true)
local velocity = codol.call("method:getvelocity", player)
assert(type(velocity) == "table" and #velocity == 3)
local destructibles = codol.call(
    "function:getentarray", "destructible_toy", "targetname")
assert(type(destructibles) == "table" and #destructibles == 1)
assert(tostring(destructibles[1]) == "codol object")
assert(codol.call("method:getentitynumber", destructibles[1]) >= 27)
assert(codol.call("method:sethealth", destructibles[1], 75) == nil)
assert(codol.call("method:setcandamage", destructibles[1], true) == nil)
local no_destructibles = codol.call(
    "function:getentarray", "missing", "targetname")
assert(type(no_destructibles) == "table" and #no_destructibles == 0)
local _, vector_error = codol.call(
    "method:finishplayerdamage",
    player,
    nil,
    nil,
    1,
    0,
    0,
    165,
    {"1", 0, 0},
    {1, 0, 0},
    0,
    0,
    0)
assert(vector_error ~= nil)
local mutation = codol.call(
    "method:setweaponammoclip", player, "m4a1tech_mp", 9)
assert(mutation == nil)
assert(codol.on("client_spawned", function(spawned_player, event)
    assert(event.sequence == 7 and event.server_time == 100)
    assert(event.client_num == 0 and event.spawn_sequence == 3)
    assert(event.spawn_generation == 2)
    assert(codol.call(
        "method:setweaponammoclip", spawned_player, "m4a1tech_mp", 8) == nil)
    print("client_spawned", event.sequence)
end))
assert(codol.on("weapon_switch_started", function(_, event)
    assert(event.weapon_asset_index == 165)
    assert(event.weapon_name == "m4a1tech_mp")
    print("weapon_switch_started", event.weapon_asset_index, event.weapon_name)
end))
assert(codol.on("player_damage", function(damaged_player, event)
    assert(damaged_player ~= nil and event.target_client_num == 0)
    assert(event.inflictor_entity_num == 1 and event.attacker_entity_num == 1)
    assert(event.damage == 33 and event.damage_flags == 4)
    assert(event.method_of_death == 2 and event.hit_location == 5)
    assert(event.time_offset == -25 and event.bone_index == 17)
    assert(event.point[1] == 10 and event.point[2] == 20 and event.point[3] == 30)
    assert(event.direction[1] == 1 and event.direction[2] == 0)
    local _, finish_error = codol.call(
        "method:finishplayerdamage",
        damaged_player,
        codol.entity(event.inflictor_entity_num),
        codol.entity(event.attacker_entity_num),
        event.damage,
        event.damage_flags,
        event.method_of_death,
        event.weapon_asset_index,
        event.point,
        event.direction,
        event.hit_location,
        event.time_offset,
        event.bone_index)
    assert(finish_error == nil, tostring(finish_error))
    print("player_damage", event.damage, event.weapon_asset_index)
end))
assert(codol.on("player_killed", function(killed_player, event)
    assert(killed_player ~= nil and event.target_client_num == 0)
    assert(event.attacker_entity_num == 1 and event.damage == 67)
    assert(event.death_animation_duration == 725)
    print("player_killed", event.damage, event.death_animation_duration)
end))
assert(codol.on("entity_damage", function(damaged_entity, event)
    assert(damaged_entity ~= nil and event.target_entity_num >= 27)
    assert(type(event.target_generation) == "number" and event.remaining_health == 30)
    assert(event.attacker_entity_num == 1 and event.damage == 20)
    assert(codol.call("method:sethealth", damaged_entity, 30) == nil)
    print("entity_damage", event.target_generation, event.remaining_health)
end))
assert(codol.on("entity_killed", function(killed_entity, event)
    assert(killed_entity ~= nil and event.target_entity_num >= 27)
    assert(type(event.target_generation) == "number" and event.remaining_health == 0)
    print("entity_killed", event.damage, event.remaining_health)
end))
assert(codol.on("sd_bomb_planted", function(planter, event)
    assert(planter ~= nil and event.actor_client_num == 0)
    assert(event.object_id == 7 and event.site_label == "_a")
    assert(event.origin[1] == 10 and event.origin[2] == 20 and event.origin[3] == 30)
    assert(event.elapsed_milliseconds == 5000)
    print("sd_bomb_planted", event.site_label, event.elapsed_milliseconds)
end))
assert(codol.on("sd_round_ended", function(actor, event)
    assert(actor == nil and event.actor_client_num == nil)
    assert(event.winner == 2 and event.reason == 5)
    print("sd_round_ended", event.winner, event.reason)
end))
assert(codol.on("entity_touch", function(receiver, other, event)
    assert(receiver ~= nil and other ~= nil)
    assert(event.receiver_entity_num ~= event.other_entity_num)
    if event.receiver_entity_num == 0 then
        local grounded = codol.call("method:isonground", receiver)
        assert(grounded == true and event.other_entity_num == 64)
    else
        assert(event.receiver_entity_num == 64 and event.other_entity_num == 0)
    end
    print("entity_touch", event.receiver_entity_num, event.other_entity_num)
end))
print("lua boot", 7, true)
sentinel = "first generation"
)lua";
        if (!runtime.reload("tests/first.lua", FirstSource))
        {
            const auto logs = runtime.takeLogs();
            const auto detail = logs.empty()
                ? std::string("no structured log")
                : logs.back().message + "\n" + logs.back().traceback;
            throw std::runtime_error(
                "Lua runtime loads text source and invokes authoritative builtins: " +
                detail);
        }
        const auto firstStatus = runtime.status();
        const auto firstLogs = runtime.takeLogs();
        require(
            firstStatus.generation == 1 && firstStatus.loaded &&
                firstStatus.sourceName == "tests/first.lua" &&
                firstLogs.size() == 1 &&
                firstLogs[0].level == SvLuaLogLevel::Info &&
                firstLogs[0].kind == SvLuaLogKind::Print &&
                firstLogs[0].generation == 1 &&
                firstLogs[0].sourceName == "tests/first.lua" &&
                firstLogs[0].message == "lua boot\t7\ttrue" &&
                firstLogs[0].traceback.empty(),
            "Lua print emits a bounded structured log entry");
        const auto luaMutatedPlayer = world.playerState(0);
        require(
            luaMutatedPlayer &&
                std::ranges::any_of(
                    luaMutatedPlayer->ammoClips,
                    [](const SvAmmoClipState &clip) {
                        return clip.clipIndex == 201 && clip.count[0] == 9;
                    }),
            "Lua undefined maps to nil while ammo builtin mutation reaches the world");
        const std::array spawnEvents{
            SvWorldEvent{
                .sequence = 7,
                .type = SvWorldEventType::ClientSpawned,
                .serverTime = 100,
                .clientNum = 0,
                .spawnSequence = 3,
                .spawnGeneration = 2,
            },
        };
        require(
            runtime.dispatchWorldEvents(spawnEvents),
            "Lua runtime dispatches authoritative world events");
        const auto spawnLogs = runtime.takeLogs();
        const auto spawnMutatedPlayer = world.playerState(0);
        require(
            spawnLogs.size() == 1 &&
                spawnLogs[0].message == "client_spawned\t7" &&
                spawnMutatedPlayer &&
                std::ranges::any_of(
                    spawnMutatedPlayer->ammoClips,
                    [](const SvAmmoClipState &clip) {
                        return clip.clipIndex == 201 && clip.count[0] == 8;
                    }),
            "world event callbacks receive bounded metadata and mutate the authoritative player");
        const std::array weaponSwitchEvents{
            SvWorldEvent{
                .sequence = 8,
                .type = SvWorldEventType::WeaponSwitchStarted,
                .serverTime = 125,
                .clientNum = 0,
                .spawnSequence = 3,
                .spawnGeneration = 2,
                .weaponAssetIndex = 165,
                .weaponName = "m4a1tech_mp",
            },
        };
        require(
            runtime.dispatchWorldEvents(weaponSwitchEvents),
            "Lua runtime dispatches committed weapon switch notifications");
        const auto weaponSwitchLogs = runtime.takeLogs();
        require(
            weaponSwitchLogs.size() == 1 &&
                weaponSwitchLogs[0].message ==
                    "weapon_switch_started\t165\tm4a1tech_mp",
            "weapon switch callbacks receive the verified weapon asset and name");
        const std::array playerDamageEvents{
            SvWorldEvent{
                .sequence = 9,
                .type = SvWorldEventType::PlayerDamage,
                .serverTime = 150,
                .clientNum = 0,
                .spawnSequence = 3,
                .spawnGeneration = 2,
                .weaponAssetIndex = 165,
                .weaponName = "m4a1tech_mp",
                .playerDamage = SvPlayerDamagePayload{
                    .targetClientNum = 0,
                    .inflictorEntityNum = 1,
                    .attackerEntityNum = 1,
                    .damage = 33,
                    .damageFlags = 4,
                    .methodOfDeath = 2,
                    .weaponAssetIndex = 165,
                    .point = std::array{ 10.0f, 20.0f, 30.0f },
                    .direction = std::array{ 1.0f, 0.0f, 0.0f },
                    .hitLocation = 5,
                    .timeOffset = -25,
                    .boneIndex = 17,
                },
            },
        };
        require(
            runtime.dispatchWorldEvents(playerDamageEvents),
            "Lua runtime dispatches committed PlayerDamage metadata");
        const auto playerDamageLogs = runtime.takeLogs();
        const auto damagedPlayer = world.playerState(0);
        require(
            playerDamageLogs.size() == 1 &&
                playerDamageLogs[0].message == "player_damage\t33\t165" &&
                damagedPlayer && damagedPlayer->health == 67 &&
                damagedPlayer->damageEvent == 0,
            "PlayerDamage callback reaches nonlethal authoritative health before frame feedback");
        const std::array playerKilledEvents{
            SvWorldEvent{
                .sequence = 10,
                .type = SvWorldEventType::PlayerKilled,
                .serverTime = 150,
                .clientNum = 0,
                .spawnSequence = 3,
                .spawnGeneration = 2,
                .weaponAssetIndex = 165,
                .weaponName = "m4a1tech_mp",
                .playerKilled = SvPlayerDeathState{
                    .damage = SvPlayerDamagePayload{
                        .targetClientNum = 0,
                        .inflictorEntityNum = 1,
                        .attackerEntityNum = 1,
                        .damage = 67,
                        .damageFlags = 4,
                        .methodOfDeath = 2,
                        .weaponAssetIndex = 165,
                        .point = std::array{ 10.0f, 20.0f, 30.0f },
                        .direction = std::array{ 1.0f, 0.0f, 0.0f },
                        .hitLocation = 5,
                        .timeOffset = -25,
                        .boneIndex = 17,
                    },
                    .deathAnimationDuration = 725,
                    .serverTime = 150,
                },
            },
        };
        require(
            runtime.dispatchWorldEvents(playerKilledEvents),
            "Lua runtime dispatches committed PlayerKilled metadata");
        const auto playerKilledLogs = runtime.takeLogs();
        require(
            playerKilledLogs.size() == 1 &&
                playerKilledLogs[0].message == "player_killed\t67\t725",
            "PlayerKilled callback receives attribution and native animation duration");
        const SvEntityDamagePayload entityDamagePayload{
            .targetEntityNum = queriedHandle.entityNum,
            .targetGeneration = queriedHandle.generation,
            .inflictorEntityNum = 1,
            .attackerEntityNum = 1,
            .damage = 20,
            .damageFlags = 4,
            .methodOfDeath = 2,
            .weaponAssetIndex = 165,
            .point = std::array{ 10.0f, 20.0f, 30.0f },
            .direction = std::array{ 1.0f, 0.0f, 0.0f },
            .hitLocation = 5,
            .timeOffset = -25,
            .boneIndex = 17,
        };
        const std::array entityDamageEvents{
            SvWorldEvent{
                .sequence = 11,
                .type = SvWorldEventType::EntityDamage,
                .serverTime = 175,
                .clientNum = queriedHandle.entityNum,
                .weaponAssetIndex = 165,
                .weaponName = "m4a1tech_mp",
                .entityDamage = SvEntityDamageEvent{
                    .damage = entityDamagePayload,
                    .remainingHealth = 30,
                },
            },
            SvWorldEvent{
                .sequence = 12,
                .type = SvWorldEventType::EntityKilled,
                .serverTime = 175,
                .clientNum = queriedHandle.entityNum,
                .weaponAssetIndex = 165,
                .weaponName = "m4a1tech_mp",
                .entityDamage = SvEntityDamageEvent{
                    .damage = entityDamagePayload,
                    .remainingHealth = 0,
                },
            },
        };
        const auto entityDamageDispatched =
            runtime.dispatchWorldEvents(entityDamageEvents);
        const auto entityDamageLogs = runtime.takeLogs();
        require(
            entityDamageDispatched,
            "Lua runtime dispatches committed generic entity damage and death metadata: " +
                (entityDamageLogs.empty()
                    ? std::string("no callback log")
                    : entityDamageLogs.front().message));
        require(
            entityDamageLogs.size() == 2 &&
                entityDamageLogs[0].message ==
                    "entity_damage\t" +
                        std::to_string(queriedHandle.generation) + "\t30" &&
                entityDamageLogs[1].message == "entity_killed\t20\t0",
            "generic damage callbacks retain generation and ordered post-hit health");
        const std::array sdEvents{
            SvWorldEvent{
                .sequence = 13,
                .type = SvWorldEventType::SdBombPlanted,
                .serverTime = 200,
                .clientNum = 0,
                .sd = SvSdEventPayload{
                    .actorClientNum = 0,
                    .objectId = 7,
                    .siteLabel = "_a",
                    .origin = std::array{ 10.0f, 20.0f, 30.0f },
                    .elapsedMilliseconds = 5000,
                },
            },
            SvWorldEvent{
                .sequence = 14,
                .type = SvWorldEventType::SdRoundEnded,
                .serverTime = 200,
                .sd = SvSdEventPayload{
                    .winner = SvTeam::Sc,
                    .reason = 5,
                },
            },
        };
        require(
            runtime.dispatchWorldEvents(sdEvents),
            "Lua runtime dispatches committed SD lifecycle events");
        const auto sdLogs = runtime.takeLogs();
        require(
            sdLogs.size() == 2 &&
                sdLogs[0].message == "sd_bomb_planted\t_a\t5000" &&
                sdLogs[1].message == "sd_round_ended\t2\t5",
            "SD callbacks retain actor, objective, position, and round result metadata");
        world.runFrame(50, clients);
        const auto damageFeedbackPlayer = world.playerState(0);
        require(
            damageFeedbackPlayer && damageFeedbackPlayer->health == 67 &&
                damageFeedbackPlayer->damageEvent == 1 &&
                damageFeedbackPlayer->damageYaw == 0 &&
                damageFeedbackPlayer->damagePitch == 0 &&
                damageFeedbackPlayer->damageCount == 33 &&
                damageFeedbackPlayer->aimSpreadScale == 33.0f,
            "P_DamageFeedback projection reaches CODOL playerstate fields on the next frame");
        auto accumulatedDamageArguments = std::array<SvScriptValue, 11>{
            SvScriptObjectRef{ SvScriptObjectKind::Entity, 1 },
            SvScriptObjectRef{ SvScriptObjectKind::Entity, 1 },
            std::int64_t{ 10 },
            std::int64_t{ 4 },
            std::int64_t{ 2 },
            std::int64_t{ 165 },
            SvScriptVector{ 10.0f, 20.0f, 30.0f },
            SvScriptVector{ 1.0f, 0.0f, 0.0f },
            std::int64_t{ 5 },
            std::int64_t{ -25 },
            std::int64_t{ 17 },
        };
        require(
            builtins.invoke(
                SvScriptBuiltinKind::Method,
                "finishplayerdamage",
                SvScriptObjectRef{ SvScriptObjectKind::Player, 0 },
                accumulatedDamageArguments).succeeded(),
            "finishplayerdamage accepts the first same-frame hit");
        accumulatedDamageArguments[2] = std::int64_t{ 7 };
        accumulatedDamageArguments[7] = SvScriptVector{ 0.0f, 1.0f, 0.0f };
        require(
            builtins.invoke(
                SvScriptBuiltinKind::Method,
                "finishplayerdamage",
                SvScriptObjectRef{ SvScriptObjectKind::Player, 0 },
                accumulatedDamageArguments).succeeded(),
            "finishplayerdamage accepts the second same-frame hit");
        world.runFrame(50, clients);
        const auto accumulatedDamagePlayer = world.playerState(0);
        require(
            accumulatedDamagePlayer && accumulatedDamagePlayer->health == 50 &&
                accumulatedDamagePlayer->damageEvent == 2 &&
                accumulatedDamagePlayer->damageYaw == 64 &&
                accumulatedDamagePlayer->damagePitch == 0 &&
                accumulatedDamagePlayer->damageCount == 17 &&
                accumulatedDamagePlayer->aimSpreadScale == 50.0f,
            "same-frame damage accumulates blood and preserves the last hit direction");
        const std::array<SvScriptValue, 11> lethalDamageArguments{
            SvScriptObjectRef{ SvScriptObjectKind::Entity, 1 },
            SvScriptObjectRef{ SvScriptObjectKind::Entity, 1 },
            std::int64_t{ 50 },
            std::int64_t{ 4 },
            std::int64_t{ 2 },
            std::int64_t{ 165 },
            SvScriptVector{ 10.0f, 20.0f, 30.0f },
            SvScriptVector{ 1.0f, 0.0f, 0.0f },
            std::int64_t{ 5 },
            std::int64_t{ -25 },
            std::int64_t{ 17 },
        };
        const auto lethalDamageResult = builtins.invoke(
            SvScriptBuiltinKind::Method,
            "finishplayerdamage",
            SvScriptObjectRef{ SvScriptObjectKind::Player, 0 },
            lethalDamageArguments);
        require(
            !lethalDamageResult.succeeded() &&
                lethalDamageResult.error.code ==
                    SvScriptBuiltinErrorCode::DeathTransitionUnavailable &&
                world.playerState(0)->health == 50,
            "lethal damage remains fail-closed until player_die is restored");
        world.runFrame(501, clients);
        const auto expiredDamageFeedbackPlayer = world.playerState(0);
        require(
            expiredDamageFeedbackPlayer &&
                expiredDamageFeedbackPlayer->damageCount == 0 &&
                expiredDamageFeedbackPlayer->damageEvent == 2,
            "damageCount expires after the native 500 millisecond feedback window");
        const auto friendlyFireDeclaration =
            productionSource.gameplaySource.source.find(
                "codol_friendly_fire_mode = 0");
        require(
            friendlyFireDeclaration != std::string::npos,
            "SD source owns an explicit friendly-fire mode declaration");
        const auto friendlyFireSource = [&](const int mode) {
            auto source = productionSource.gameplaySource.source;
            source.replace(
                friendlyFireDeclaration,
                std::string_view("codol_friendly_fire_mode = 0").size(),
                "codol_friendly_fire_mode = " + std::to_string(mode));
            return source;
        };
        SvLuaRuntime targetFriendlyFireRuntime(builtins);
        require(
            targetFriendlyFireRuntime.reload(
                productionSource.gameplaySource.sourceName,
                friendlyFireSource(1)) &&
                targetFriendlyFireRuntime.dispatchWorldEvents(FriendlyFireEvent) &&
                world.playerState(0)->health == 17 &&
                world.playerState(1)->health == 100,
            "friendly-fire mode one applies full damage only to the target");
        SvLuaRuntime reflectedFriendlyFireRuntime(builtins);
        require(
            reflectedFriendlyFireRuntime.reload(
                productionSource.gameplaySource.sourceName,
                friendlyFireSource(2)) &&
                reflectedFriendlyFireRuntime.dispatchWorldEvents(FriendlyFireEvent) &&
                world.playerState(0)->health == 17 &&
                world.playerState(1)->health == 84,
            "friendly-fire mode two applies half damage only to the attacker");
        SvLuaRuntime sharedFriendlyFireRuntime(builtins);
        const auto sharedReloaded = sharedFriendlyFireRuntime.reload(
            productionSource.gameplaySource.sourceName,
            friendlyFireSource(3));
        const auto sharedDispatched = sharedReloaded &&
            sharedFriendlyFireRuntime.dispatchWorldEvents(FriendlyFireEvent);
        const auto sharedTargetState = world.playerState(0);
        const auto sharedAttackerState = world.playerState(1);
        require(
            sharedDispatched && sharedTargetState && sharedAttackerState &&
                sharedTargetState->health == 1 &&
                sharedAttackerState->health == 68,
            "friendly-fire mode three atomically applies half damage to both players");
        const SvClientImpactBatch luaImpactBatch{
            .sourceEntityNum = 0,
            .inputTouchCount = 1,
            .impactCount = 1,
            .targetEntityNums = { 64 },
        };
        const auto luaTouchNotifications =
            SV_BuildClientImpactScriptNotificationBatch(luaImpactBatch);
        require(
            luaTouchNotifications &&
                runtime.dispatchTouchNotifications(*luaTouchNotifications),
            "Lua runtime consumes committed source-then-target touch notifications");
        const auto touchLogs = runtime.takeLogs();
        require(
            touchLogs.size() == 2 &&
                touchLogs[0].message == "entity_touch\t0\t64" &&
                touchLogs[1].message == "entity_touch\t64\t0",
            "entity-touch callbacks receive typed receiver and other objects in native order");
        auto invalidTouchNotifications = *luaTouchNotifications;
        invalidTouchNotifications.notifications[1].otherEntityNum = 7;
        require(
            !runtime.dispatchTouchNotifications(invalidTouchNotifications),
            "Lua runtime rejects a malformed mirrored touch pair atomically");
        const auto invalidTouchLogs = runtime.takeLogs();
        require(
            invalidTouchLogs.size() == 1 &&
                invalidTouchLogs[0].kind == SvLuaLogKind::HostError &&
                invalidTouchLogs[0].message ==
                    "invalid entity-touch notification batch",
            "invalid touch metadata never reaches gameplay callbacks");
        const std::array invalidGenericTouchEvents{
            SvWorldEvent{
                .type = SvWorldEventType::EntityTouch,
                .clientNum = 0,
            },
        };
        require(
            !runtime.dispatchWorldEvents(invalidGenericTouchEvents),
            "generic world events cannot bypass the dedicated touch ABI");
        const auto invalidGenericTouchLogs = runtime.takeLogs();
        require(
            invalidGenericTouchLogs.size() == 1 &&
                invalidGenericTouchLogs[0].kind == SvLuaLogKind::HostError &&
                invalidGenericTouchLogs[0].message ==
                    "entity touch requires the dedicated notification ABI",
            "entity touch cannot be mis-dispatched with the player-event callback shape");
        auto invalidPlayerDamageEvent = playerDamageEvents.front();
        invalidPlayerDamageEvent.playerDamage->weaponAssetIndex = 77;
        const std::array invalidPlayerDamageEvents{ invalidPlayerDamageEvent };
        require(
            !runtime.dispatchWorldEvents(invalidPlayerDamageEvents),
            "Lua runtime rejects inconsistent PlayerDamage world metadata");
        const auto invalidPlayerDamageLogs = runtime.takeLogs();
        require(
            invalidPlayerDamageLogs.size() == 1 &&
                invalidPlayerDamageLogs[0].kind == SvLuaLogKind::HostError &&
                invalidPlayerDamageLogs[0].message ==
                    "invalid PlayerDamage world event payload",
            "invalid PlayerDamage metadata never reaches gameplay callbacks");
        auto invalidEntityDamageEvent = entityDamageEvents.front();
        invalidEntityDamageEvent.entityDamage->remainingHealth = 0;
        const std::array invalidEntityDamageEvents{ invalidEntityDamageEvent };
        require(
            !runtime.dispatchWorldEvents(invalidEntityDamageEvents),
            "Lua runtime rejects inconsistent EntityDamage world metadata");
        const auto invalidEntityDamageLogs = runtime.takeLogs();
        require(
            invalidEntityDamageLogs.size() == 1 &&
                invalidEntityDamageLogs[0].kind == SvLuaLogKind::HostError &&
                invalidEntityDamageLogs[0].message ==
                    "invalid EntityDamage world event payload",
            "invalid generic damage metadata never reaches gameplay callbacks");

        constexpr std::string_view ReloadSource = R"lua(
assert(sentinel == nil)
local missing, message, code = codol.call(
    "function:getvelocity", codol.player(0))
assert(missing == nil)
assert(type(message) == "string" and message:find("unknown script builtin"))
assert(type(code) == "number")
assert(codol.on("client_disconnected", function()
    error("disconnect callback boom")
end))
print("second generation")
)lua";
        require(
            runtime.reload("tests/reload.lua", ReloadSource),
            "Lua runtime replaces the complete VM generation");
        const auto reloadStatus = runtime.status();
        const auto reloadLogs = runtime.takeLogs();
        require(
            reloadStatus.generation == 2 && reloadStatus.loaded &&
                reloadLogs.size() == 1 &&
                reloadLogs[0].generation == 2 &&
                reloadLogs[0].message == "second generation",
            "Lua reload discards old globals and tags new logs with the generation");
        const std::array disconnectEvents{
            SvWorldEvent{
                .sequence = 8,
                .type = SvWorldEventType::ClientDisconnected,
                .serverTime = 150,
                .clientNum = 0,
                .spawnSequence = 3,
                .spawnGeneration = 2,
            },
        };
        require(
            !runtime.dispatchWorldEvents(disconnectEvents) &&
                runtime.status().loaded,
            "Lua callback failure is isolated without unloading the generation");
        const auto callbackLogs = runtime.takeLogs();
        require(
            callbackLogs.size() == 1 &&
                callbackLogs[0].kind == SvLuaLogKind::RuntimeError &&
                callbackLogs[0].message.find("disconnect callback boom") !=
                    std::string::npos &&
                callbackLogs[0].traceback.find("tests/reload.lua") !=
                    std::string::npos,
            "Lua callback errors retain generation, source, and traceback evidence");

        require(
            !runtime.reload("tests/runtime_error.lua", R"lua(
local function nested()
    error("runtime boom")
end
nested()
)lua"),
            "Lua runtime reports protected execution failures");
        const auto runtimeErrorStatus = runtime.status();
        const auto runtimeErrorLogs = runtime.takeLogs();
        require(
            runtimeErrorStatus.generation == 3 && !runtimeErrorStatus.loaded &&
                runtimeErrorLogs.size() == 1 &&
                runtimeErrorLogs[0].kind == SvLuaLogKind::RuntimeError &&
                runtimeErrorLogs[0].message.find("runtime boom") != std::string::npos &&
                runtimeErrorLogs[0].traceback.find("stack traceback") !=
                    std::string::npos &&
                runtimeErrorLogs[0].traceback.find("tests/runtime_error.lua") !=
                    std::string::npos,
            "Lua runtime error logs preserve the source and traceback");

        const std::string binaryChunk("\x1bLua\x54\0\0", 8);
        require(
            !runtime.reload("tests/binary.lua", binaryChunk),
            "Lua runtime rejects binary chunks through text-only loading");
        const auto binaryStatus = runtime.status();
        const auto binaryLogs = runtime.takeLogs();
        require(
            binaryStatus.generation == 4 && !binaryStatus.loaded &&
                binaryLogs.size() == 1 &&
                binaryLogs[0].kind == SvLuaLogKind::CompileError &&
                binaryLogs[0].sourceName == "tests/binary.lua",
            "binary rejection is visible through structured compile logs");

        SvLuaRuntime instructionLimitedRuntime(builtins, {
            .maximumMemoryBytes = 1024 * 1024,
            .maximumInstructionsPerRun = 10'000,
            .instructionHookInterval = 100,
            .maximumSourceBytes = 1024,
        });
        require(
            !instructionLimitedRuntime.reload(
                "tests/instruction_limit.lua", "while true do end"),
            "Lua runtime interrupts scripts that exceed their instruction budget");
        const auto instructionLogs = instructionLimitedRuntime.takeLogs();
        require(
            instructionLogs.size() == 1 &&
                instructionLogs[0].kind == SvLuaLogKind::RuntimeError &&
                instructionLogs[0].message.find("instruction budget") !=
                    std::string::npos,
            "instruction exhaustion produces a bounded structured runtime error");

        SvLuaRuntime memoryLimitedRuntime(builtins, {
            .maximumMemoryBytes = 128 * 1024,
            .maximumInstructionsPerRun = 1'000'000,
            .instructionHookInterval = 100,
            .maximumSourceBytes = 1024,
        });
        require(
            !memoryLimitedRuntime.reload("tests/memory_limit.lua", R"lua(
local values = {}
for index = 1, 100000 do
    values[index] = string.rep("x", 64)
end
)lua"),
            "Lua runtime allocator rejects scripts that exceed their memory budget");
        const auto memoryLogs = memoryLimitedRuntime.takeLogs();
        require(
            memoryLogs.size() == 1 &&
                memoryLogs[0].kind == SvLuaLogKind::RuntimeError &&
                memoryLogs[0].message.find("memory") != std::string::npos,
            "memory exhaustion produces a bounded structured runtime error");

        require(
            runtime.reload("tests/reset.lua", "print('before reset')"),
            "Lua runtime can recover after compile and runtime failures");
        static_cast<void>(runtime.takeLogs());
        runtime.reset();
        require(
            runtime.status() == SvLuaRuntimeStatus{
                .generation = 6,
                .loaded = false,
            },
            "explicit reset closes the VM and invalidates its generation");

        std::cout << "CodolGameServer Lua runtime tests passed\n";
        return EXIT_SUCCESS;
    }
    catch (const std::exception &error)
    {
        std::cerr << "CodolGameServer Lua runtime tests failed: "
                  << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
