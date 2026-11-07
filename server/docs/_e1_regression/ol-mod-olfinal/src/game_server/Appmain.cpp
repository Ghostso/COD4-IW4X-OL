#include "server_mp/sv_zm_special_mp.hpp"
#include "server_mp/sv_zm_factory_room_patch.hpp"
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "ClientNoclipHotkey.hpp"
#include "EngineBindings.hpp"
#include "SessionAssetRegistry.hpp"
#include "GameStateConfiguration.hpp"
#include "ClientProcessPatches.hpp"
#include "DisconnectWitness.hpp"
#include "ClientAnimtreeHook.hpp"
#include "ClientRenderFrameHook.hpp"
#include "DedicatedSessionConsumption.hpp"
#include "DedicatedProcessPatches.hpp"
#include "ClientCommandTrace.hpp"
#include "FrameHook.hpp"
#include "../client_bridge/ClientSessionBridge.hpp"
#include "server_mp/sv_bullet_mp.hpp"
#include "server_mp/sv_client_events_mp.hpp"
#include "server_mp/sv_const_baselines_mp.hpp"
#include "server_mp/sv_destructible_mp.hpp"
#include "server_mp/sv_frame_diagnostics.hpp"
#include "server_mp/sv_gamestate_mp.hpp"
#include "server_mp/sv_battlechatter_mp.hpp"
#include "server_mp/sv_main_mp.hpp"
#include "server_mp/sv_mapents_mp.hpp"
#include "server_mp/sv_network_mp.hpp"
#include "server_mp/sv_playlist_mp.hpp"
#include "server_mp/sv_script_source_mp.hpp"
#include "server_mp/sv_zm_navgraph_mp.hpp"
#include "../shared/DedicatedControl.hpp"
#include "../shared/ProcessRole.hpp"
#include "../shared/RuntimeLog.hpp"

#include <algorithm>
#include <array>
#include <charconv>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <deque>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <limits>
#include <map>
#include <mutex>
#include <unordered_map>
#include <thread>
#include <atomic>
#include <optional>
#include <span>
#include <string>
#include <utility>
#include <vector>

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerConfigureBooking(
    const char *command);

namespace
{
    using RuntimeClock = std::chrono::steady_clock;

    CodolGameServer::EngineBindings Bindings;
    CodolGameServer::SvTimingAccumulator ServerFrameTiming;
    CodolGameServer::SvTimingAccumulator NetworkSendTiming;
    std::array<CodolGameServer::SvTimingAccumulator,
        CodolGameServer::MaximumGameClients> SnapshotBuildTiming;
    void logGameServer(std::string_view message);
    std::string_view alphaWeaponPortStatusName(
        CodolGameServer::AlphaWeaponPortStatus status);

    // The locational hit probe was useful while validating player damage, but
    // walking every collision entity and formatting a large line for every
    // bullet is far too expensive for normal play (especially automatic fire).
    constexpr bool BulletTraceDiagnostics = false;

    // THE GAMETYPE PIN'S REASON DOES NOT APPLY TO EVERY GAMETYPE, AND PINNING THEM ALL
    // BREAKS THE MAPS THAT SHIP AN ADDON. Section 187o pins a booked gametype to `dm`
    // because a TEAM script puts two players on one side and `issameteam` then blocks
    // all damage. That reason is about the SCRIPT, so the test is the script:
    //
    //     assets/game_scripts/gametypes/<token>.lua  IS dm.lua  ->  already teamless,
    //                                                                nothing to pin
    //     cha.lua, sd.lua, zm.lua                    differ      ->  real sides, pin
    //
    // Pinning a teamless token is not merely redundant, it is HARMFUL. Section 152o:
    // the token selects the FASTFILE SET, and the client loads whatever ITS PLAYLIST
    // says. On `mp_battlecity` the client loads base + `dmz_addon` and computes
    // 2566829241, while a dedicated pinned to `dm` loads base only and computes
    // 994462206 -- the exact mismatch §152n diagnosed, reaching the player as the level
    // -file dialog. `mp_nuked` hid this for months because `cha` has no addon there, so
    // pinning cha->dm changes no file and the checksums agree anyway.
    //
    // DERIVED BY DIFFING THE SCRIPTS, not chosen. Re-derive with:
    //     for g in *.lua; do diff -q dm.lua $g; done
    // and revisit this list if any of these ever stops being a dm.lua copy -- giving
    // dmz.lua real duo teams, for instance, would put `dmz` back on the pinned side.
    bool gameTypeIsTeamless(const std::string &gameType)
    {
        return gameType == "dm" || gameType == "dmz" || gameType == "zarena" ||
            gameType == "zhunt" || gameType == "coop" || gameType == "td";
    }

    std::uint64_t elapsedMicroseconds(const RuntimeClock::time_point start)
    {
        return static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::microseconds>(
                RuntimeClock::now() - start).count());
    }

    std::optional<std::uint64_t> currentThreadCpuMicroseconds()
    {
        FILETIME created{},exited{},kernel{},user{};
        if (!GetThreadTimes(GetCurrentThread(),&created,&exited,&kernel,&user))
            return std::nullopt;
        const auto ticks=[](const FILETIME &time) {
            return (std::uint64_t{time.dwHighDateTime}<<32)|time.dwLowDateTime;
        };
        return (ticks(kernel)+ticks(user))/10u;
    }

    std::string formatTimingWindow(
        const CodolGameServer::SvTimingWindow &timing)
    {
        std::string result = std::to_string(timing.lastMicroseconds) + "/" +
            std::to_string(timing.averageMicroseconds()) + "/" +
            std::to_string(timing.maximumMicroseconds) + " buckets=";
        for (std::size_t index{}; index < timing.buckets.size(); ++index)
        {
            if (index)
                result += ",";
            result += std::to_string(timing.buckets[index]);
        }
        return result;
    }

    std::vector<std::uint8_t> buildGameState(
        const CodolGameServer::SvGameState &gameState,
        const std::uint32_t clientNum,
        const std::uint32_t reliableSequence)
    {
        std::vector<std::uint8_t> buffer(64 * 1024);
        CodolGameServer::EngineMsgWriter message(Bindings, buffer);
        if (!CodolGameServer::SV_WriteGameState(
                message, gameState, clientNum, reliableSequence))
        {
            return {};
        }
        const auto data = message.data();
        return { data.begin(), data.end() };
    }

    std::vector<std::uint8_t> buildSnapshot(
        const CodolGameServer::SvSnapshotFrame &frame,
        const CodolGameServer::SvSnapshotFrame *baseline,
        const std::uint32_t clientNum,
        const std::uint8_t deltaMessageDistance,
        const bool initializeBaselineCache,
        const CodolGameServer::SvClientPrediction *const clientPrediction)
    {
        const auto timingStart = RuntimeClock::now();
        std::vector<std::uint8_t> buffer(64 * 1024);
        CodolGameServer::EngineMsgWriter message(Bindings, buffer);
        CodolGameServer::SvSnapshotWriteFailure failure{};
        if (!CodolGameServer::SV_WriteSnapshot(
                message,
                frame,
                baseline,
                clientNum,
                deltaMessageDistance,
                initializeBaselineCache,
                clientPrediction,
                &failure))
        {
            static std::array<CodolGameServer::SvSnapshotWriteFailure,
                CodolGameServer::MaximumGameClients> lastFailures{};
            if (clientNum < lastFailures.size() &&
                lastFailures[clientNum] != failure)
            {
                lastFailures[clientNum] = failure;
                logGameServer(
                    "snapshot build rejected client=" +
                    std::to_string(clientNum) + " failure=" +
                    std::string(CodolGameServer::SV_SnapshotWriteFailureName(
                        failure)) + " baseline=" +
                    std::to_string(baseline ? 1 : 0) + " delta=" +
                    std::to_string(deltaMessageDistance) + " init=" +
                    std::to_string(initializeBaselineCache ? 1 : 0));
            }
            if (clientNum < SnapshotBuildTiming.size())
            {
                SnapshotBuildTiming[clientNum].record(
                    elapsedMicroseconds(timingStart));
            }
            return {};
        }
        // THE BYTES THIS SERVER ACTUALLY PUT ON THE WIRE, so the demo decoder can be the
        // oracle for them.
        //
        // Tools/demo-re/codol_snapshot.py is a transcription of the client's own reader,
        // validated 11,136/11,136 against recorded demos. Feeding it what was really sent
        // answers questions that reading the writer cannot: a value XORed against the
        // WRONG baseline still has the right framing, so it decodes cleanly to the end
        // and is silently wrong. That is not hypothetical -- `0xFFFFFF ^ 0xFFFFFF = 0`
        // turned a correct-looking snapshot into a black screen on this project once
        // already (codol-snapshot-xor-baseline).
        //
        // OFF unless OLMOD_SNAPSHOT_HEX is set, and capped: a snapshot is built per
        // client per frame, so an uncapped dump buries the log it lives in. The cap
        // counts BUILDS, not frames, so two clients halve the frames covered -- which is
        // fine, both are equally valid samples. Dumped here rather than inside
        // SV_WriteSnapshot because MsgWriter is an abstract interface with no byte
        // accessor; this is the call site that owns the buffer.
        static const long snapshotHexLimit = [] {
            const char *const value = std::getenv("OLMOD_SNAPSHOT_HEX");
            if (!value || !value[0])
                return 0L;
            const auto parsed = std::strtol(value, nullptr, 10);
            return parsed > 0 ? parsed : 16L;
        }();
        static std::atomic<long> snapshotHexDumped{ 0 };
        // AND A DUMP OF THE FIRST N FRAMES CANNOT SEE A KILL TWO MINUTES IN.
        // OLMOD_SNAPSHOT_HEX_OBITUARY=1 spends the same budget on the frames
        // that carry an EV_OBITUARY instead, which is what turns "the server
        // says it archived one" into "these are the bytes the client was
        // handed" -- Tools/demo-re decodes them offline.
        static const bool snapshotHexObituaryOnly = [] {
            const char *const value = std::getenv("OLMOD_SNAPSHOT_HEX_OBITUARY");
            return value && value[0] && value[0] != '0';
        }();
        const auto data = message.data();
        const auto frameCarriesObituary =
            !snapshotHexObituaryOnly ||
            std::ranges::any_of(frame.entities, [](const auto &entity) {
                return entity.eType == CodolGameServer::EntityTypeObituary;
            });
        if (snapshotHexLimit && frameCarriesObituary &&
            snapshotHexDumped.load(std::memory_order_relaxed) < snapshotHexLimit)
        {
            const auto sequence =
                snapshotHexDumped.fetch_add(1, std::memory_order_relaxed);
            if (sequence < snapshotHexLimit)
            {
                static constexpr char Digits[] = "0123456789ABCDEF";
                std::string hex;
                hex.reserve(data.size() * 2);
                for (const auto value : data)
                {
                    hex.push_back(Digits[(static_cast<unsigned>(value) >> 4) & 0xF]);
                    hex.push_back(Digits[static_cast<unsigned>(value) & 0xF]);
                }
                logGameServer(
                    "SNAPHEX seq=" + std::to_string(sequence) + " client=" +
                    std::to_string(clientNum) + " serverTime=" +
                    std::to_string(frame.serverTime) + " delta=" +
                    std::to_string(deltaMessageDistance) + " baseline=" +
                    std::to_string(baseline ? 1 : 0) + " init=" +
                    std::to_string(initializeBaselineCache ? 1 : 0) + " len=" +
                    std::to_string(data.size()) + " " + hex);
            }
        }
        if (clientNum < SnapshotBuildTiming.size())
        {
            SnapshotBuildTiming[clientNum].record(
                elapsedMicroseconds(timingStart));
        }
        return { data.begin(), data.end() };
    }

    CodolGameServer::ServerCore Server(
        buildGameState,
        buildSnapshot,
        [](const std::string_view modelName) {
            return Bindings.resolveModelConfigStringIndex(modelName);
        },
        [](const std::string_view weaponName) {
            return Bindings.resolveWeaponConfigStringIndex(weaponName);
        },
        [](const std::string_view aliasName) {
            return Bindings.resolveSoundAliasEventParameter(aliasName);
        });
    CodolGameServer::SvUdpTransport Network;
    // The plugin remains loaded for the process lifetime. Avoid joining a
    // control thread from DLL teardown while the Windows loader lock is held.
    OlMod::DedicatedControl::Server *DedicatedControlServer{};
    OlMod::ClientSessionBridge *ClientSessionBridge{};
    std::mutex DedicatedControlMutex;
    std::deque<std::string> DedicatedBookingCommands;
    struct QueuedDedicatedSessionStart
    {
        std::uint64_t requestId{};
        OlMod::DedicatedSession::SessionStart session;
    };
    std::deque<QueuedDedicatedSessionStart> DedicatedSessionStarts;
    // Live loadout refreshes (§157c). Queued on the control thread, applied on
    // the game thread in processDedicatedControlMessages so gameState_ and the
    // registry are only touched from the frame loop.
    struct QueuedLoadoutUpdate
    {
        std::uint64_t requestId{};
        std::uint64_t userId{};
        OlMod::DedicatedSession::LoadoutRequest loadout;
    };
    std::deque<QueuedLoadoutUpdate> DedicatedLoadoutUpdates;
    // Announcer auditions (191n). Same shape and the same reason: queued on the
    // control thread, sent on the game thread, because queueLocalSound writes
    // into the client reliable rings the frame loop owns.
    std::deque<std::uint16_t> DedicatedAnnouncerAuditions;
    std::deque<std::vector<std::uint8_t>> DedicatedRawCommands;
    // Defined below, next to the SessionStart loadout resolution it mirrors.
    bool refreshMemberLoadout(
        std::uint64_t userId,
        const OlMod::DedicatedSession::LoadoutRequest &request);
    struct DedicatedMapGenerationPreparation
    {
        std::uint64_t requestId{};
        std::string mapName;
        std::string gameType;
        bool levelWorldInitialized{};
        bool configStringsCleared{};
    };
    std::optional<DedicatedMapGenerationPreparation>
        DedicatedMapGeneration;
    CodolGameServer::DedicatedSessionConsumptionTracker
        DedicatedSessionConsumption;
    CodolGameServer::GameStateConfigurationTracker GameStateConfiguration;
    std::optional<OlMod::DedicatedSession::SessionStart> ActiveDedicatedSession;
    struct PreparedSessionMember
    {
        std::uint64_t xuid{};
        std::string username;
        std::uint32_t characterIndex{};
        CodolGameServer::ClientCharacterPresentation characterPresentation;
        std::map<std::string, CodolGameServer::ClientWeaponLoadout> loadouts;
        std::map<std::string, CodolGameServer::SvResolvedPerks> perks;
        std::map<std::string, OlMod::DedicatedSession::EquipmentRequest> equipment;
        std::map<std::string, CodolGameServer::SvResolvedEquipment> offhands;
        std::optional<CodolGameServer::SvResolvedRewards> rewards;
    };
    struct PreparedClientLoadouts
    {
        std::uint64_t requestSequence{};
        std::uint64_t sessionGeneration{};
        std::vector<PreparedSessionMember> members;
    };
    CodolGameServer::SessionAssetRegistry RegisteredSessionAssets;
    struct LoadoutPreparationStatus
    {
        std::uint32_t attemptCount{};
        std::int32_t currentCharacter{-1};
        std::uint32_t resolvedClassMask{};
        std::uint32_t registeredClassMask{};
    };
    std::mutex LoadoutMutex;
    std::optional<PreparedClientLoadouts> PreparedLoadouts;
    std::uint64_t LoadoutPrepareRequestSequence{};
    LoadoutPreparationStatus LoadoutPreparation;
    std::optional<std::uint32_t> LastLoadoutPrepareAttempt;
    std::optional<std::uint64_t> LastLoadoutPrepareRequestSequence;
    std::mutex StartupMutex;
    std::mutex BookingMutex;
    CodolGameServer::SvPendingBooking PendingBooking;
    std::mutex WorldAssetMutex;
    struct PendingWorldAssetRequest
    {
        std::string mapName;
        std::string gameType;
        std::optional<std::vector<CodolGameServer::SvMapEntity>> mapEntities;
        std::string lastFailureStage;
        std::uint32_t lastAttemptMilliseconds{};
        bool attempted{};
    };
    std::optional<PendingWorldAssetRequest> PendingWorldAsset;
    constexpr float SpawnGroundTraceDistance = 8192.0f;
    bool Installed{};
    std::optional<CodolGameServer::DedicatedProcessPatchResult>
        DedicatedProcessPatch;
    std::optional<CodolGameServer::ClientProcessPatchResult>
        ClientProcessPatch;
    std::optional<CodolGameServer::ClientProcessPatchResult>
        ClientLoopFxPatch;
    std::optional<CodolGameServer::ClientProcessPatchResult>
        ClientEntityEventWeaponPatch;
    std::optional<CodolGameServer::ClientProcessPatchResult>
        ClientEntityEventRangePatch;
    std::optional<CodolGameServer::ClientProcessPatchResult>
        ClientAmmoLookupWeaponPatch;
    std::optional<CodolGameServer::ClientProcessPatchResult>
        ClientUiOperatorResolverPatch;
    std::optional<CodolGameServer::ClientProcessPatchResult>
        ClientWeaponInventoryPatch;
    std::optional<CodolGameServer::UnsignedFastfilePatchResult>
        UnsignedFastfilePatch;
    bool UnsignedFastfilePatchAttempted{};
    bool ClientProcessPatchAttempted{};

    void prepareClientAlphaWeaponsForGamestate()
    {
        const auto status = Bindings.installAlphaWeaponPorts();
        logGameServer(
            "client gamestate alpha weapon restore status=" +
            std::string(alphaWeaponPortStatusName(status)));
    }

    // OLMOD(section-94): A HIT IS NOT DAMAGE, and the reason is the pass filter.
    //
    // Section 73g item 4 has been open since a player could first be shot: sv_bullet_mp turns
    // partGroup into a hit location and a multiplier, builds an SvPlayerDamagePayload, appends a
    // player-damage world event and hands it to the gametype script -- and NOT ONE LINE of that
    // has ever run, because every bullet this server fires reports hitEntity=none. It is not
    // that the path is wrong. It is that SV_BulletTrace passes the SHOOTER, correctly, and with
    // one client in the map the shooter is the only collision entity there is.
    //
    // Section 74 hit exactly this shape on the capsule path and section 73h's "this needs a
    // second player and a person at the screen" was RETRACTED: the question was reachable, and
    // every existing caller just excluded the answer. Same here.
    //
    // The probe changes TWO things and nothing else:
    //   * passFiringEntity = false, so the shooter is a legal candidate
    //   * the BASIS is replaced with a line that has already been measured to hit him --
    //     section 73's locational probe segment 1, from origin - 64 on Y at z + 42, aimed +Y,
    //     which reports fraction=0.437363 partGroup=5 on every cycle. Firing from the real
    //     muzzle with no pass filter would start INSIDE his own capsule, which is section 74's
    //     other lesson: aim a server-side probe at a line you have already measured clear.
    // Bullet_Endpos, SV_BulletTrace, the damage curve, the hit-location multiplier, the payload
    // build, the event append and the script dispatch are all the real path, untouched.
    bool bulletSelfDamageProbeEnabled()
    {
        static const bool enabled = [] {
            std::array<char, 8> value{};
            const auto size = GetEnvironmentVariableA(
                "OLMOD_BULLET_SELF_DAMAGE_PROBE",
                value.data(),
                static_cast<DWORD>(value.size()));
            return size == 1 && value[0] == '1';
        }();
        return enabled;
    }

    bool bulletPenetrationDiagnosticsEnabled()
    {
        static const bool enabled = [] {
            std::array<char, 8> value{};
            const auto size = GetEnvironmentVariableA(
                "OLMOD_LOG_BULLET_PENETRATION",
                value.data(),
                static_cast<DWORD>(value.size()));
            return size == 1 && value[0] == '1';
        }();
        return enabled;
    }

    CodolGameServer::SvFireWeaponResult executeServerBulletFire(
        const std::uint32_t serverTime,
        CodolGameServer::SvGlassState &glassState,
        CodolGameServer::SvGlassDamageState &glassDamageState,
        const CodolGameServer::SvGlassMapMetadata &glassMetadata,
        const std::span<const CodolGameServer::SvCollisionEntity>
            collisionEntities,
        const std::span<const CodolGameServer::SvDamageablePlayerView>
            damageablePlayers,
        CodolGameServer::SvPlayerState &playerState,
        CodolGameServer::SvGameEntity &entity,
        const CodolGameServer::SvResolvedWeapon &weapon,
        const CodolGameServer::SvWeaponFireBasis &basis,
        const CodolGameServer::SvWeaponSpreadResult &spread,
        const CodolGameServer::SvFireWeaponEvent &event)
    {
        // OLMOD(server-bullet-fire-composition): Appmain owns dependency
        // assembly between the source command transaction and retained native
        // endpos/trace helpers. This named entry is not CODOL FireWeapon.
        const auto plan = CodolGameServer::SV_BuildBulletFirePlan({
            .commandTime = playerState.commandTime,
            .hand = event.hand,
            .weaponType = weapon.weaponType,
            .weaponClass = weapon.weaponClass,
            .penetrateType = weapon.penetrateType,
            .shotCount = weapon.shotCount,
            .damageCurve = weapon.damageCurve,
            .rifleBullet = weapon.rifleBullet != 0,
            .bulletExplosiveDamage = weapon.bulletExplosiveDamage != 0,
        });
        if (!plan)
            return CodolGameServer::SvFireWeaponResult::Failed;

        // OLMOD(section-94): the self-damage probe. Off by default and inert when off; when on
        // it rewrites the basis to the one line section 73 measured through this player and
        // stops the trace from passing him. It fires the REAL path -- see the note on
        // bulletSelfDamageProbeEnabled.
        auto probeBasis = basis;
        const auto selfDamageProbe = bulletSelfDamageProbeEnabled();
        if (selfDamageProbe)
        {
            const auto &origin = playerState.origin;
            probeBasis.muzzleTrace = {
                origin[0], origin[1] - 64.0f, origin[2] + 42.0f };
            probeBasis.forward = { 0.0f, 1.0f, 0.0f };
            probeBasis.right = { 1.0f, 0.0f, 0.0f };
            probeBasis.up = { 0.0f, 0.0f, 1.0f };
        }

        CodolGameServer::SvBulletExecutionStatus executionStatus;
        std::vector<CodolGameServer::SvBulletImpactEvent> bulletImpactEvents;
        const auto penetrationDiagnostics =
            plan->penetrate && bulletPenetrationDiagnosticsEnabled();
        const auto result = CodolGameServer::SV_ExecuteBulletFire({
            .commandTime = playerState.commandTime,
            .plan = *plan,
            .basis = probeBasis,
            .spread = spread,
            .damageCurve = weapon.damageCurve,
            .hitLocationMultipliers = weapon.hitLocationMultipliers,
            .weaponAssetIndex = weapon.weaponAssetIndex,
            .firingEntityNum = entity.networkState.number,
            .levelTime = static_cast<std::int32_t>(serverTime),
            .rifleBullet = weapon.rifleBullet != 0,
            .passFiringEntity = !selfDamageProbe,
        },
            glassMetadata,
            [](const CodolGameServer::SvBulletEndposRequest &request) {
                return Bindings.calculateBulletEndpos(request);
            },
            [&glassState, collisionEntities, penetrationDiagnostics](
                const CodolGameServer::SvPointTraceRequest &request) {
                const auto trace = Bindings.traceServerPoint(
                    request, glassState, collisionEntities);
                if (penetrationDiagnostics)
                {
                    static std::uint32_t reports{};
                    if (reports++ < 96)
                    {
                        char line[320]{};
                        std::snprintf(
                            line,
                            sizeof(line),
                            "bullet-penetration-trace mode=%s "
                            "start=%.2f,%.2f,%.2f end=%.2f,%.2f,%.2f "
                            "result=%s hitType=%u hitId=%u fraction=%.4f "
                            "startSolid=%d allSolid=%d surface=%u",
                            request.entitiesOnly
                                ? "entities"
                                : request.worldOnly ? "world" : "initial",
                            request.start[0], request.start[1], request.start[2],
                            request.end[0], request.end[1], request.end[2],
                            trace ? "ok" : "unavailable",
                            trace ? trace->hitType : 0,
                            trace ? trace->hitId : 0,
                            trace ? trace->fraction : 0.0f,
                            trace && trace->startSolid ? 1 : 0,
                            trace && trace->allSolid ? 1 : 0,
                            trace
                                ? ((trace->surfaceFlags >> 20) & 0x1F)
                                : 0);
                        OlMod::RuntimeLog::write(
                            OlMod::RuntimeLog::Channel::GameServer, line);
                    }
                }
                return trace;
            },
            [](const CodolGameServer::SvBulletTraceInput &,
               const CodolGameServer::TraceResult &,
               std::uint32_t) -> std::optional<bool> {
                // TODO(CODOL): Replace the no-penetration continuation stub
                // after reverse trace, material depth loss and recursive
                // Bullet_Process ownership are recovered.
                return false;
            },
            [](const std::array<float, 3> &direction) {
                return Bindings.directionToByte(direction);
            },
            damageablePlayers,
            entity.damageableEntityViews,
            glassDamageState,
            glassState,
            entity.pendingPlayerDamagePayloads,
            entity.pendingEntityDamagePayloads,
            bulletImpactEvents,
            &executionStatus,
            [](const std::uint16_t weaponAssetIndex,
               const std::uint8_t surfaceType) {
                return Bindings.surfacePenetrationDepth(
                    weaponAssetIndex, surfaceType);
            });
        if (penetrationDiagnostics && executionStatus.traced)
        {
            static std::uint32_t reports{};
            if (reports++ < 48)
            {
                char line[320]{};
                std::snprintf(
                    line,
                    sizeof(line),
                    "bullet-penetration-result shooter=%u weapon=%u "
                            "result=%u hitEntity=%u playerDamage=%d entityDamage=%d "
                            "impacts=%zu hitType=%u hitId=%u fraction=%.4f "
                            "surfaceFlags=0x%08X surface=%u",
                    entity.networkState.number,
                    weapon.weaponAssetIndex,
                    static_cast<unsigned>(result),
                    executionStatus.hitEntityNum.value_or(
                        CodolGameServer::BulletNoneEntityNum),
                    executionStatus.playerDamageStaged ? 1 : 0,
                    executionStatus.entityDamageStaged ? 1 : 0,
                    bulletImpactEvents.size(),
                    executionStatus.trace.hitType,
                    executionStatus.trace.hitId,
                    executionStatus.trace.fraction,
                    executionStatus.trace.surfaceFlags,
                    (executionStatus.trace.surfaceFlags >> 20) & 0x1F);
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, line);
            }
        }
        for (auto &impact : bulletImpactEvents)
            entity.pendingEntitySpawns.emplace_back(std::move(impact));
        // SECTION 191z: SAY WHICH REFUSAL IT WAS, ONCE PER KIND PER WEAPON.
        //
        // A refused shot rejects the WHOLE usercmd upstream
        // (`client_events_rejected`), so the player sees no damage, no
        // movement commit and a desync -- three symptoms, one cause, and the
        // stage name distinguishes none of the thirteen ways to get here.
        // Silent while shots are landing; the first alt-fire burst printed
        // nothing but `bullet-hit ... damageStaged=1` and a stage name.
        if (result == CodolGameServer::SvBulletFireExecutionResult::Failed)
        {
            static std::mutex bulletFailureMutex;
            static std::set<std::pair<std::string, std::uint16_t>> bulletFailuresSeen;
            const auto *const reason = CodolGameServer::SV_LastBulletFireFailure();
            auto report = false;
            {
                const std::lock_guard<std::mutex> guard(bulletFailureMutex);
                report = bulletFailuresSeen.size() < 64 &&
                    bulletFailuresSeen.emplace(reason, weapon.weaponAssetIndex).second;
            }
            if (report)
            {
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer,
                    std::string("bullet fire REFUSED reason=") + reason +
                        " weapon=" + std::to_string(weapon.weaponAssetIndex) +
                        " type=" + std::to_string(weapon.weaponType) +
                        " class=" + std::to_string(weapon.weaponClass) +
                        " shotCount=" + std::to_string(weapon.shotCount) +
                        " hitEntity=" +
                        (executionStatus.hitEntityNum
                             ? std::to_string(*executionStatus.hitEntityNum)
                             : std::string("none")) +
                        " partGroup=" +
                        std::to_string(executionStatus.trace.partGroup) +
                        " staged=" +
                        std::to_string(executionStatus.playerDamageStaged ? 1 : 0));
            }
        }
        if (executionStatus.traced)
            entity.lastBulletExecutionStatus = executionStatus;
        // OLMOD(locational-hit-diagnostics): report the hit against the pose the
        // trace ACTUALLY saw. The control-socket readout joins the target's
        // origin from whichever frame it happens to sample and records no
        // stance at all, so a hit skeleton that is one stance low and a target
        // that was simply crouching produce identical numbers there - of 26
        // measured player hits only one could be pinned to a known stance
        // afterwards. `collisionEntities` is the exact list this trace ran
        // against, and a live player's bounds carry the stance directly:
        // SV_EncodePlayerSolid publishes maxs[2] 70 standing / 50 crouch / 30
        // prone, measured off retail's own dm recording.
        // TODO(CODOL): remove once the locational hit heights are confirmed
        // against a known target stance.
        // OLMOD(locational-miss-diagnostics): a MISS has to be visible too.
        // Logging only entity hits made a shot that passed straight through a
        // player indistinguishable from a shot never fired: after the script
        // model sponge was removed, the post-respawn magazine produced no lines
        // at all, and the control socket showed the last trace stopping in a
        // wall 1007 units away while the target stood 148 units away. So report
        // every committed trace together with the player capsules that were
        // actually in the list it ran against, and how close the ray came to
        // each - a capsule that is absent, or present but never intersected,
        // are different bugs with the same symptom.
        // TODO(CODOL): remove once a post-respawn player is hittable.
        if constexpr (BulletTraceDiagnostics)
        {
            if (executionStatus.traced)
            {
                std::string capsules;
                for (const auto &candidate : collisionEntities)
                {
                    if (candidate.shape != CodolGameServer::SvCollisionShape::Capsule)
                        continue;
                    // Perpendicular distance from the shot to the capsule's axis,
                    // clamped to the segment, in the plane - the same quantity the
                    // broadphase decides candidacy on.
                    const auto &s = executionStatus.start;
                    const auto &e = executionStatus.end;
                    std::array<double, 3> d{ e[0] - s[0], e[1] - s[1], e[2] - s[2] };
                    std::array<double, 3> w{
                        candidate.origin[0] - s[0],
                        candidate.origin[1] - s[1],
                        candidate.origin[2] - s[2] };
                    const auto dd = d[0] * d[0] + d[1] * d[1] + d[2] * d[2];
                    const auto t = dd > 0.0
                        ? std::clamp((w[0] * d[0] + w[1] * d[1] + w[2] * d[2]) / dd,
                              0.0, 1.0)
                        : 0.0;
                    const auto nearest = std::hypot(
                        w[0] - d[0] * t, w[1] - d[1] * t);
                    char entry[112]{};
                    std::snprintf(
                        entry,
                        sizeof(entry),
                        " #%u{linked=%d maxsZ=%.0f axisDist=%.1f}",
                        candidate.entityNum,
                        candidate.linked ? 1 : 0,
                        candidate.bounds.midpoint[2] + candidate.bounds.halfSize[2],
                        nearest);
                    capsules += entry;
                }
                char summary[512]{};
                std::snprintf(
                    summary,
                    sizeof(summary),
                    "bullet-trace shooter=%u hitType=%u hitEntity=%s fraction=%.4f "
                    "travelled=%.0f capsules=%zu%s",
                    entity.networkState.number,
                    executionStatus.trace.hitType,
                    executionStatus.hitEntityNum
                        ? std::to_string(*executionStatus.hitEntityNum).c_str()
                        : "none",
                    executionStatus.trace.fraction,
                    executionStatus.trace.fraction * std::hypot(
                        std::hypot(
                            executionStatus.end[0] - executionStatus.start[0],
                            executionStatus.end[1] - executionStatus.start[1]),
                        executionStatus.end[2] - executionStatus.start[2]),
                    capsules.size(),
                    capsules.c_str());
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, summary);
            }
        }
        if constexpr (BulletTraceDiagnostics)
        {
          if (executionStatus.traced && executionStatus.hitEntityNum &&
            executionStatus.trace.hitType == 1)
          {
            const auto hitEntityNum = *executionStatus.hitEntityNum;
            const auto target = std::ranges::find_if(
                collisionEntities,
                [hitEntityNum](const CodolGameServer::SvCollisionEntity &candidate) {
                    return candidate.entityNum == hitEntityNum;
                });
            if (target != collisionEntities.end())
            {
                const auto &trace = executionStatus.trace;
                const auto axis = [&](const std::size_t index) {
                    return executionStatus.start[index] +
                        (executionStatus.end[index] - executionStatus.start[index]) *
                            trace.fraction;
                };
                char line[512]{};
                std::snprintf(
                    line,
                    sizeof(line),
                    // Report player and generic-entity staging separately. Zombies use
                    // the latter, so a single damageStaged flag was misleading here.
                    "bullet-hit shooter=%u target=%u part=%u group=%u "
                    "playerDamageStaged=%d entityDamageStaged=%d "
                    "hitZ=%.2f hitRadial=%.2f "
                    "targetOrigin=%.2f,%.2f,%.2f "
                    "targetMaxsZ=%.2f targetMinsZ=%.2f targetMaxsX=%.2f "
                    "targetYaw=%.2f targetScale=%.3f eyeZ=%.2f",
                    entity.networkState.number,
                    hitEntityNum,
                    trace.partName,
                    trace.partGroup,
                    executionStatus.playerDamageStaged ? 1 : 0,
                    executionStatus.entityDamageStaged ? 1 : 0,
                    axis(2) - target->origin[2],
                    std::hypot(
                        axis(0) - target->origin[0], axis(1) - target->origin[1]),
                    target->origin[0], target->origin[1], target->origin[2],
                    target->bounds.midpoint[2] + target->bounds.halfSize[2],
                    target->bounds.midpoint[2] - target->bounds.halfSize[2],
                    target->bounds.halfSize[0],
                    target->angles[1],
                    target->modelScale,
                    executionStatus.start[2] - playerState.origin[2]);
                OlMod::RuntimeLog::write(
                    OlMod::RuntimeLog::Channel::GameServer, line);
            }
          }
        }

        switch (result)
        {
        case CodolGameServer::SvBulletFireExecutionResult::Applied:
            return CodolGameServer::SvFireWeaponResult::Applied;
        case CodolGameServer::SvBulletFireExecutionResult::DeferredImpact:
            return CodolGameServer::SvFireWeaponResult::DeferredImpact;
        default:
            return CodolGameServer::SvFireWeaponResult::Failed;
        }
    }

    // OLMOD(server-melee-composition): the melee counterpart of
    // executeServerBulletFire. Same dependency assembly, same candidate
    // ownership -- the payload lands in entity.pendingPlayerDamagePayloads and
    // is committed by clientThink only if the whole usercmd succeeds.
    std::optional<std::uint16_t> resolveServerMeleeDamage(
        const std::uint16_t weaponAssetIndex)
    {
        // SIDE STORAGE BY ASSET, because SvResolvedWeapon is held inside the
        // address-sensitive WorldClientState node. Growing that node broke
        // corpse animation in section 184h. WeaponDefs are immutable after
        // registration, so one native read per newly seen asset is enough.
        static std::mutex cacheMutex;
        static std::unordered_map<std::uint16_t, std::uint16_t> cache;
        const std::lock_guard<std::mutex> guard(cacheMutex);
        if (const auto found = cache.find(weaponAssetIndex);
            found != cache.end())
        {
            return found->second;
        }

        CodolGameServer::ClientWeaponSelection selection{};
        if (!Bindings.readWeaponSelection(weaponAssetIndex, selection) ||
            !selection.meleeDamage ||
            selection.meleeDamage >
                std::numeric_limits<std::uint16_t>::max())
        {
            return std::nullopt;
        }
        const auto damage = static_cast<std::uint16_t>(selection.meleeDamage);
        cache.emplace(weaponAssetIndex, damage);
        return damage;
    }

    CodolGameServer::SvMeleeAttackResult executeServerMeleeAttack(
        const std::uint32_t serverTime,
        CodolGameServer::SvGlassState &glassState,
        CodolGameServer::SvGlassDamageState &glassDamageState,
        const CodolGameServer::SvGlassMapMetadata &glassMetadata,
        const std::span<const CodolGameServer::SvCollisionEntity>
            collisionEntities,
        const std::span<const CodolGameServer::SvDamageablePlayerView>
            damageablePlayers,
        CodolGameServer::SvGameEntity &entity,
        const CodolGameServer::SvResolvedWeapon &weapon,
        const CodolGameServer::SvWeaponFireBasis &basis)
    {
        const auto meleeDamage = resolveServerMeleeDamage(
            weapon.weaponAssetIndex);
        if (!meleeDamage)
            return CodolGameServer::SvMeleeAttackResult::Failed;

        // Where the staged payloads end BEFORE the swing, so the one this swing
        // adds can be identified without the melee path having to report it.
        const auto payloadsBefore = entity.pendingPlayerDamagePayloads.size();
        const auto result = CodolGameServer::SV_ExecuteMeleeAttack(
            {
                .basis = basis,
                .weaponAssetIndex = weapon.weaponAssetIndex,
                .meleeDamage = *meleeDamage,
                .firingEntityNum = entity.networkState.number,
                .levelTime = static_cast<std::int32_t>(serverTime),
                .glassPieceCount = static_cast<std::uint32_t>(
                    glassMetadata.initialPieces.size()),
            },
            [&glassState, collisionEntities](
                const CodolGameServer::SvPointTraceRequest &request) {
                return Bindings.traceServerPoint(
                    request, glassState, collisionEntities);
            },
            [](const CodolGameServer::SvBulletTraceInput &,
               const CodolGameServer::TraceResult &,
               std::uint32_t) -> std::optional<bool> {
                // Melee does not penetrate; the first thing the swing reaches
                // is the thing it hits.
                return false;
            },
            glassMetadata,
            [](const std::array<float, 3> &direction) {
                return Bindings.directionToByte(direction);
            },
            damageablePlayers,
            entity.damageableEntityViews,
            entity.pendingPlayerDamagePayloads,
            entity.pendingEntityDamagePayloads,
            glassDamageState,
            glassState);
        // SAY IT, ONCE PER SWING. A knife that does not kill is the reported
        // bug, and the two ways it can fail -- the trace finding nobody, and
        // the trace finding somebody who is not a damageable player -- are
        // indistinguishable without this line. Melee is rare enough per match
        // that one line per swing is not the section 104 flood.
        char line[192]{};
        std::snprintf(
            line,
            sizeof(line),
            "melee attacker=%u weapon=%u damage=%u result=%s "
            "damageablePlayers=%zu damageableEntities=%zu",
            entity.networkState.number,
            weapon.weaponAssetIndex,
            static_cast<unsigned>(*meleeDamage),
            result == CodolGameServer::SvMeleeAttackResult::Applied ? "APPLIED"
                : result == CodolGameServer::SvMeleeAttackResult::Glass
                    ? "GLASS"
                : result == CodolGameServer::SvMeleeAttackResult::Missed
                    ? "missed"
                    : "FAILED",
            damageablePlayers.size(),
            entity.damageableEntityViews.size());
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer, line);

        // AND THE KNIFE'S OWN IMPACT EVENT. A swing that connects has always
        // staged damage and shown the victim NOTHING -- retail sends
        // EV_MELEE_HIT 36 times a match and this server never sent it once.
        // Everything it needs is already in the payload the swing just staged:
        // the hit point, the attacker and the weapon. Read from there rather
        // than threaded back out of SV_ExecuteMeleeAttack, so the melee
        // transaction keeps its single output and its signature.
        if (result == CodolGameServer::SvMeleeAttackResult::Applied &&
            entity.pendingPlayerDamagePayloads.size() > payloadsBefore)
        {
            const auto &staged = entity.pendingPlayerDamagePayloads.back();
            if (staged.point)
            {
                const CodolGameServer::SvBulletImpactEvent meleeImpact{
                    .position = *staged.point,
                    .weaponAssetIndex = weapon.weaponAssetIndex,
                    .sourceEntityNum = static_cast<std::uint16_t>(
                        entity.networkState.number),
                    .melee = true,
                };
                if (CodolGameServer::SV_IsBulletImpactEventValid(meleeImpact))
                    entity.pendingEntitySpawns.push_back(meleeImpact);
            }
        }
        return result;
    }

    std::optional<CodolGameServer::ClientRawInputPatchResult>
        ClientRawInputPatch;
    bool ClientRawInputWindowReady{};
    std::uint32_t LastRuntimeStatusLogMilliseconds{};
    CodolGameServer::ServerStatus LastLoggedServerStatus{};
    CodolGameServer::SvNetworkStatus LastLoggedNetworkStatus{};
    std::optional<CodolGameServer::AlphaWeaponPortStatus>
        LastLoggedAlphaWeaponPortStatus{};
    std::array<std::optional<CodolGameServer::SvClientThinkStatus>, 18>
        LastLoggedClientThinkStatus{};
    std::array<std::string, 18> LastLoggedClientIngressState{};
    std::array<std::uint32_t, 18> LastLoggedUnsupportedDiscardCounts{};
    std::array<std::string, 18> LastLoggedClientRejectState{};

    struct DObjLocationalProbeState
    {
        std::uint32_t attemptCount{};
        bool completed{};
    };
    DObjLocationalProbeState DObjLocationalProbe;

    // OLMOD(capsule-entity-collision): section 74. The counterpart of the
    // locational probe, for the CAPSULE path. Section 73h said this question
    // needed a second player and a person at the screen; it does not, because
    // the one player already in the map IS a linked entity and a capsule
    // sweep through him with no pass filter has exactly one candidate.
    struct CapsuleEntityProbeState
    {
        std::uint32_t attemptCount{};
        bool completed{};
    };
    CapsuleEntityProbeState CapsuleEntityProbe;

    void logGameServer(const std::string_view message)
    {
        OlMod::RuntimeLog::write(
            OlMod::RuntimeLog::Channel::GameServer, message);
    }

    std::string_view alphaWeaponPortStatusName(
        const CodolGameServer::AlphaWeaponPortStatus status)
    {
        using Status = CodolGameServer::AlphaWeaponPortStatus;
        switch (status)
        {
        case Status::Disabled: return "disabled";
        case Status::WaitingForCommonAssets: return "waiting-common-assets";
        case Status::WaitingForWeaponRegistry: return "waiting-weapon-registry";
        case Status::WrongThread: return "wrong-thread";
        case Status::SourceAssetMissing: return "source-asset-missing";
        case Status::InvalidDefinition: return "invalid-definition";
        case Status::LinkFailed: return "link-failed";
        case Status::RegistrationFailed: return "registration-failed";
        case Status::Ready: return "ready";
        }
        return "unknown";
    }

    void installClientInputPatches(const OlMod::ProcessRole role)
    {
        if (role == OlMod::ProcessRole::Dedicated)
            return;
        if (!ClientProcessPatchAttempted)
        {
            ClientProcessPatchAttempted = true;
            std::array<char, 8> value{};
            const auto size = GetEnvironmentVariableA(
                "CODOL_CLIENT_EXECUTION_STATE_PATCH",
                value.data(),
                value.size());
            const auto enabled = !size ||
                (value[0] != '0' && value[0] != 'n' && value[0] != 'N' &&
                    value[0] != 'f' && value[0] != 'F');
            if (!enabled)
            {
                logGameServer("client execution state patch disabled");
            }
            else
            {
                ClientProcessPatch =
                    CodolGameServer::installClientProcessPatches();
                logGameServer(std::string("client process patch ") +
                    CodolGameServer::clientProcessPatchResultName(
                        *ClientProcessPatch));
            }
            ClientLoopFxPatch =
                CodolGameServer::installClientLoopFxNullGuardPatch();
            logGameServer(std::string("client loop FX null guard patch ") +
                CodolGameServer::clientProcessPatchResultName(
                    *ClientLoopFxPatch));
            ClientEntityEventWeaponPatch =
                CodolGameServer::installClientEntityEventWeaponGuardPatch();
            logGameServer(
                std::string("client entity-event weapon null guard patch ") +
                CodolGameServer::clientProcessPatchResultName(
                    *ClientEntityEventWeaponPatch));
            ClientEntityEventRangePatch =
                CodolGameServer::installClientEntityEventRangeGuardPatch();
            logGameServer(
                std::string("client entity-event range guard patch ") +
                    CodolGameServer::clientProcessPatchResultName(
                        *ClientEntityEventRangePatch));
            ClientAmmoLookupWeaponPatch =
                CodolGameServer::installClientAmmoLookupWeaponGuardPatch();
            logGameServer(
                std::string("client ammo-lookup weapon null guard patch ") +
                CodolGameServer::clientProcessPatchResultName(
                    *ClientAmmoLookupWeaponPatch));
            ClientWeaponInventoryPatch =
                CodolGameServer::installClientWeaponInventoryGuardPatch();
            logGameServer(
                std::string("client weapon-inventory null guard patch ") +
                CodolGameServer::clientProcessPatchResultName(
                    *ClientWeaponInventoryPatch));
            ClientUiOperatorResolverPatch =
                CodolGameServer::installClientUiOperatorResolverGuardPatch();
            logGameServer(
                std::string("client UI operator range guard patch ") +
                CodolGameServer::clientProcessPatchResultName(
                    *ClientUiOperatorResolverPatch));
            const auto batteryDisplayPatch =
                CodolGameServer::installClientBatteryDisplayPatch();
            logGameServer(std::string("client battery HUD divisor patch ") +
                CodolGameServer::clientProcessPatchResultName(batteryDisplayPatch));
        }
        if (ClientRawInputPatch)
            return;

        std::array<char, 8> value{};
        const auto size = GetEnvironmentVariableA(
            "CODOL_RAW_MOUSE_INPUT", value.data(), value.size());
        const auto enabled = !size ||
            (value[0] != '0' && value[0] != 'n' && value[0] != 'N' &&
                value[0] != 'f' && value[0] != 'F');
        if (!enabled)
        {
            logGameServer("client raw input patch disabled");
            return;
        }
        ClientRawInputPatch = CodolGameServer::installClientRawInputPatch();
        logGameServer(std::string("client raw input patch ") +
            CodolGameServer::clientRawInputPatchResultName(
                *ClientRawInputPatch));
        // WHO DISCONNECTS THE CLIENT. Off unless OLMOD_DISCONNECT_WITNESS=1; it patches
        // five bytes of the client's own CL_Disconnect to log its caller once. See
        // DisconnectWitness.cpp -- this exists because mp_battlecity reaches cls.state 10
        // and then zeroes it a second later with no Com_Error and no fault.
        {
            const auto witness = CodolGameServer::installDisconnectWitness();
            if (witness != CodolGameServer::DisconnectWitnessResult::NotRequested)
            {
                logGameServer(std::string("disconnect witness ") +
                    CodolGameServer::disconnectWitnessResultName(witness));
            }
        }

        // PUBLISH THE TCLS MAPPING FROM IN HERE, and say whether it was needed.
        //
        // TenProxy opens TCLS_SHAREDMEMEMORY<pid> during this process's own startup and dies
        // at [100] if it cannot. SampleLauncher creates that name from ANOTHER process, which
        // works on Windows and was measured NOT to under Wine: the mapping existed twice over
        // and TenProxy still got Error code = 2. A name that exists and cannot be opened from
        // the target process is a namespace boundary, and publishing harder from outside does
        // not cross one.
        //
        // This runs in the client, ~30 s before TenProxy asked on the failing machine, so it
        // cannot lose on timing either. And it reports ALREADY VISIBLE when the cross-process
        // mapping was reachable, which is the measurement nothing else could take.
        const auto tclsMapping = CodolGameServer::publishTclsMapping();
        if (tclsMapping != CodolGameServer::TclsMappingResult::NotRequested)
        {
            logGameServer(std::string("tcls mapping ") +
                CodolGameServer::tclsMappingResultName(tclsMapping));
        }

        // OWN EVERY ITEM. Off unless OLMOD_UNLOCK_ALL=1, and it says which of the six
        // outcomes it got -- "UNEXPECTED BYTES" is the one that matters, because it means
        // this is not the build the predicate was read from and NOTHING was written.
        const auto unlockAll = CodolGameServer::installUnlockAllPatch();
        if (unlockAll != CodolGameServer::UnlockAllPatchResult::NotRequested)
        {
            logGameServer(std::string("unlock-all patch ") +
                CodolGameServer::unlockAllPatchResultName(unlockAll));
        }
        // READABLE players/config_mp.cfg. Off unless OLMOD_PLAINTEXT_CONFIG=1. The game
        // already writes that file as text and re-encrypts it in a second pass, so this
        // skips the second pass and the matching decrypt on load -- two one-byte jumps.
        const auto plaintextConfig =
            CodolGameServer::installPlaintextConfigPatch();
        if (plaintextConfig !=
            CodolGameServer::PlaintextConfigPatchResult::NotRequested)
        {
            logGameServer(std::string("plaintext-config patch ") +
                CodolGameServer::plaintextConfigPatchResultName(plaintextConfig));
        }
        // RAISE com_maxfps' REGISTERED MAX. Off unless OLMOD_MAXFPS_CEILING=<n>. Only the
        // dvar's upper BOUND moves; its default stays 200, so this changes nothing until
        // somebody sets the dvar. Above ~320 the client outruns the server's per-frame
        // usercmd queue -- see the ceiling note in the header.
        const auto maxFpsCeiling =
            CodolGameServer::installMaxFpsCeilingPatch();
        if (maxFpsCeiling !=
            CodolGameServer::MaxFpsCeilingPatchResult::NotRequested)
        {
            logGameServer(std::string("maxfps-ceiling patch ") +
                CodolGameServer::maxFpsCeilingPatchResultName(maxFpsCeiling));
        }

        // 12.140: the animtree resolve hook. Opt-in via CODOL_ANIMTREE_RESOLVE_HOOK=1
        // -- it rewrites a call inside the client's own map-load path, so it does not
        // ship enabled.
        {
            const auto animtreeHook =
                CodolGameServer::installClientAnimtreeHook();
            logGameServer(std::string("client animtree resolve hook ") +
                CodolGameServer::animtreeHookResultName(animtreeHook));
        }

        // THE RENDER-FRAME HOOK. Opt-in via CODOL_IMAGE_UPLOAD_HOOK=1. It exists
        // because a GfxImage cannot be published by linking alone: image+0 is an
        // IDirect3DTexture9 that sub_BE7470 has to create, the device carries no
        // D3DCREATE_MULTITHREADED, and its thread is NOT the one running Com_Frame.
        // See ClientRenderFrameHook.hpp for the measurement.
        {
            const auto renderHook =
                CodolGameServer::installClientRenderFrameHook();
            logGameServer(std::string("client render frame hook ") +
                CodolGameServer::renderFrameHookResultName(renderHook));

            // CODOL_FORGE_BUNDLE names a CodolForge staging bundle.json and
            // publishes the WHOLE chain from in here - images, then the materials
            // that name them, then the models that name those. That ordering is
            // the point: publishing from an injected thread cannot survive a zone
            // transition, and this runs on the far side of one.
            if (renderHook == CodolGameServer::RenderFrameHookResult::Installed)
            {
                std::array<char, 512> bundle{};
                const auto bundleSize = GetEnvironmentVariableA(
                    "CODOL_FORGE_BUNDLE", bundle.data(),
                    static_cast<DWORD>(bundle.size()));
                if (bundleSize > 0 && bundleSize < bundle.size())
                {
                    std::array<char, 256> clone{};
                    const auto cloneSize = GetEnvironmentVariableA(
                        "CODOL_FORGE_CLONE", clone.data(),
                        static_cast<DWORD>(clone.size()));
                    CodolGameServer::ForgeChainRequest request;
                    request.bundlePath = bundle.data();
                    request.cloneSource = (cloneSize > 0 && cloneSize < clone.size())
                        ? std::string(clone.data())
                        : std::string("mc/mtl_t6_wpn_pda");
                    std::string chainError;
                    const bool queued =
                        CodolGameServer::queueForgeChain(request, chainError);
                    logGameServer(std::string("forge chain ") +
                        (queued ? "queued from " : "refused: ") +
                        (queued ? request.bundlePath : chainError));
                }
            }

            // With the hook up, CODOL_FORGE_IMAGE_DIR publishes every .iwi in a
            // directory. This is how the image path is exercised without a
            // bundle; CODOL_FORGE_BUNDLE above is the complete route.
            if (renderHook == CodolGameServer::RenderFrameHookResult::Installed)
            {
                std::array<char, 512> directory{};
                const auto size = GetEnvironmentVariableA(
                    "CODOL_FORGE_IMAGE_DIR", directory.data(),
                    static_cast<DWORD>(directory.size()));
                if (size > 0 && size < directory.size())
                {
                    const auto report =
                        CodolGameServer::queueForgeImageDirectory(directory.data());
                    logGameServer("forge images queued " +
                        std::to_string(report.queued) + "/" +
                        std::to_string(report.found) + " from " + directory.data());
                    for (const auto &failure : report.failures)
                    {
                        logGameServer("forge image " + failure.first +
                            " refused: " + failure.second);
                    }
                }
            }
        }
    }

    bool dobjLocationalProbeEnabled()
    {
        static const bool enabled = [] {
            std::array<char, 8> value{};
            const auto size = GetEnvironmentVariableA(
                "OLMOD_DOBJ_LOCATIONAL_PROBE",
                value.data(),
                static_cast<DWORD>(value.size()));
            return size == 1 && value[0] == '1';
        }();
        return enabled;
    }

    // OLMOD(section-79-ui-dvar-cache): THE CLIENT'S GAMETYPE DVAR CACHE, AND WHY
    // A LEVEL LOAD FAULTS WITHOUT IT.
    //
    // Every cycle that lost the client died at 0x0043204F with edx = 0, which is
    // `mov edx,[0x032AA908]; mov ecx,[edx+0x0C]` -- the CACHED POINTER to the
    // g_gametype dvar, then its string. The dvar itself is fine; only the cache
    // is missing. That cache has exactly one writer, `sub_4E8990`, whose caller
    // chain is gated on DB_IsZoneLoaded("ui_mp"), and a client we drive straight
    // into a match never loads the legacy UI zone. CL_ParseGamestate -> the level
    // load -> mp/gametypeWeaponCustomTable.csv then dereferences NULL on the
    // FIRST weapon it resolves, so the fault is unconditional once we get there.
    //
    // This runs in the CLIENT process only. It is SILENT while the cache is
    // populated -- if this ever stops printing, the engine got there first and
    // the repair is dead code that should be deleted rather than kept.
    bool clientUiDvarRepairEnabled()
    {
        static const bool enabled = [] {
            std::array<char, 8> value{};
            const auto size = GetEnvironmentVariableA(
                "OLMOD_CLIENT_UI_DVAR_REPAIR",
                value.data(),
                static_cast<DWORD>(value.size()));
            // Default ON: without it no cycle reaches a spawn at all.
            return !(size == 1 && value[0] == '0');
        }();
        return enabled;
    }

    // OLMOD(section-79d): AND IT MUST BE ABLE TO SEE THE ENGINE WIN.
    // The first version repaired on the first frame the cache was NULL, which
    // makes the question "does the engine ever fill it on its own?" permanently
    // unanswerable -- the repair always gets there first. Hold off for a while,
    // report the NULL->populated transition if it happens, and only then repair.
    // The match flow needs ninety seconds from client start to gamestate, so a
    // thirty-second wait is comfortably ahead of the reader.
    std::uint32_t clientUiDvarRepairDelayMs()
    {
        static const std::uint32_t delay = [] {
            std::array<char, 16> value{};
            const auto size = GetEnvironmentVariableA(
                "OLMOD_CLIENT_UI_DVAR_REPAIR_DELAY_MS",
                value.data(),
                static_cast<DWORD>(value.size()));
            if (size == 0 || size >= value.size())
                return 30000u;
            const auto parsed = std::strtoul(value.data(), nullptr, 10);
            return static_cast<std::uint32_t>(parsed);
        }();
        return delay;
    }

    void maintainClientGametypeDvarCache(const std::uint32_t nowMilliseconds)
    {
        auto *const base = Bindings.module();
        if (!base)
            return;

        static bool reported = false;
        static bool repaired = false;
        static bool settled = false;
        static std::uint32_t firstNullTick{};

        const auto cache = *reinterpret_cast<const std::uint32_t *>(
            base + CodolGameServer::EngineBindings::GametypeDvarCacheRva);
        if (cache != 0)
        {
            // The whole point of the delay: if this fires with repaired == false,
            // the ENGINE filled it and the repair is dead code.
            if (reported && !settled)
            {
                settled = true;
                std::array<char, 160> line{};
                std::snprintf(
                    line.data(),
                    line.size(),
                    "client gametype dvar cache POPULATED by=%s cache=0x%08X "
                    "afterMs=%lu",
                    repaired ? "repair" : "THE ENGINE",
                    cache,
                    static_cast<unsigned long>(nowMilliseconds - firstNullTick));
                logGameServer(line.data());
            }
            return;
        }

        using IsZoneLoaded = int(__cdecl *)(const char *);
        const auto isZoneLoaded = reinterpret_cast<IsZoneLoaded>(
            base + CodolGameServer::EngineBindings::IsZoneLoadedRva);
        const auto *const uiZoneName = reinterpret_cast<const char *>(
            base + CodolGameServer::EngineBindings::UiZoneNameRva);
        const auto flags = *reinterpret_cast<const std::uint8_t *>(
            base + CodolGameServer::EngineBindings::UiZoneStateFlagsRva);

        if (!reported)
        {
            reported = true;
            firstNullTick = nowMilliseconds;
            std::array<char, 192> line{};
            std::snprintf(
                line.data(),
                line.size(),
                "client gametype dvar cache NULL zone=%s loaded=%d "
                "stateFlags=0x%02X repair=%d",
                uiZoneName,
                isZoneLoaded(uiZoneName) ? 1 : 0,
                static_cast<unsigned>(flags),
                clientUiDvarRepairEnabled() ? 1 : 0);
            logGameServer(line.data());
        }

        if (!clientUiDvarRepairEnabled() || repaired)
            return;
        if (nowMilliseconds - firstNullTick < clientUiDvarRepairDelayMs())
            return;
        repaired = true;

        // Logged BEFORE the call on purpose: if the client dies inside the
        // registration this line is the only thing that says so.
        logGameServer("client gametype dvar cache repair CALLING sub_4E8990");
        using RegisterGameplayDvars = void(__cdecl *)();
        reinterpret_cast<RegisterGameplayDvars>(
            base + CodolGameServer::EngineBindings::RegisterGameplayDvarsRva)();

        const auto after = *reinterpret_cast<const std::uint32_t *>(
            base + CodolGameServer::EngineBindings::GametypeDvarCacheRva);
        std::array<char, 96> done{};
        std::snprintf(
            done.data(),
            done.size(),
            "client gametype dvar cache repair RETURNED cache=0x%08X",
            after);
        logGameServer(done.data());
    }

    bool capsuleEntityProbeEnabled()
    {
        static const bool enabled = [] {
            std::array<char, 8> value{};
            const auto size = GetEnvironmentVariableA(
                "OLMOD_CAPSULE_ENTITY_PROBE",
                value.data(),
                static_cast<DWORD>(value.size()));
            return size == 1 && value[0] == '1';
        }();
        return enabled;
    }

    std::optional<CodolGameServer::SvGlassDamageThresholds>
        glassDamageThresholds()
    {
        // TODO(CODOL): Remove the Ghosts-derived recovery defaults once a
        // CODOL server glass_map (type 17) supplies the native thresholds.
        CodolGameServer::SvGlassDamageThresholds thresholds{
            .weaken = 25,
            .destroy = 100,
        };
        const auto read = [](const char *const name,
                              std::uint16_t &output) {
            std::array<char, 16> value{};
            const auto size = GetEnvironmentVariableA(
                name, value.data(), static_cast<DWORD>(value.size()));
            if (!size)
                return true;
            if (size >= value.size())
                return false;
            std::uint32_t parsed{};
            const auto [end, error] = std::from_chars(
                value.data(), value.data() + size, parsed);
            if (error != std::errc{} || end != value.data() + size ||
                !parsed || parsed > std::numeric_limits<std::uint16_t>::max())
            {
                return false;
            }
            output = static_cast<std::uint16_t>(parsed);
            return true;
        };
        if (!read("OLMOD_GLASS_DAMAGE_TO_WEAKEN", thresholds.weaken) ||
            !read("OLMOD_GLASS_DAMAGE_TO_DESTROY", thresholds.destroy) ||
            thresholds.weaken > thresholds.destroy)
        {
            return std::nullopt;
        }
        return thresholds;
    }

    void runDObjLocationalProbe()
    {
        constexpr std::uint32_t ProbeClientNum = 0;
        constexpr std::uint32_t MaximumAttempts = 3;
        if (!dobjLocationalProbeEnabled() ||
            DObjLocationalProbe.completed ||
            DObjLocationalProbe.attemptCount >= MaximumAttempts ||
            !Server.worldNativeEntityMirrorSynchronized())
        {
            return;
        }

        const auto sample = Server.worldPlayerSample(ProbeClientNum);
        if (!sample || sample->playerState.pmType != 0)
            return;

        const auto origin = sample->playerState.origin;
        const std::array<std::pair<std::array<float, 3>,
            std::array<float, 3>>, 3> segments{
            std::pair{
                std::array{ origin[0] - 64.0f, origin[1], origin[2] + 42.0f },
                std::array{ origin[0] + 64.0f, origin[1], origin[2] + 42.0f }},
            std::pair{
                std::array{ origin[0], origin[1] - 64.0f, origin[2] + 42.0f },
                std::array{ origin[0], origin[1] + 64.0f, origin[2] + 42.0f }},
            std::pair{
                std::array{ origin[0], origin[1], origin[2] + 96.0f },
                std::array{ origin[0], origin[1], origin[2] + 8.0f }},
        };

        ++DObjLocationalProbe.attemptCount;
        for (std::size_t segmentIndex{};
             segmentIndex < segments.size();
             ++segmentIndex)
        {
            const auto result = Server.traceWorldPoint({
                .start = segments[segmentIndex].first,
                .end = segments[segmentIndex].second,
                .contentMask = CodolGameServer::BulletLocationalContentMask,
                .mode = CodolGameServer::SvPointTraceMode::BulletLocational,
                .allowChildren = true,
            });
            if (!result)
            {
                logGameServer(
                    "DObj locational probe unavailable attempt=" +
                    std::to_string(DObjLocationalProbe.attemptCount) +
                    " segment=" + std::to_string(segmentIndex));
                return;
            }

            logGameServer(
                "DObj locational probe result attempt=" +
                std::to_string(DObjLocationalProbe.attemptCount) +
                " segment=" + std::to_string(segmentIndex) +
                " fraction=" + std::to_string(result->fraction) +
                " hitType=" + std::to_string(result->hitType) +
                " hitId=" + std::to_string(result->hitId) +
                " modelIndex=" + std::to_string(result->modelIndex) +
                " partName=" + std::to_string(result->partName) +
                " partGroup=" + std::to_string(result->partGroup));
            if (result->fraction < 1.0f &&
                result->hitId == ProbeClientNum && result->partName != 0)
            {
                DObjLocationalProbe.completed = true;
                logGameServer("DObj locational probe completed");
                return;
            }
        }
    }

    void runCapsuleEntityProbe()
    {
        constexpr std::uint32_t ProbeClientNum = 0;
        constexpr std::uint32_t MaximumAttempts = 3;
        if (!capsuleEntityProbeEnabled() ||
            CapsuleEntityProbe.completed ||
            CapsuleEntityProbe.attemptCount >= MaximumAttempts)
        {
            return;
        }

        const auto sample = Server.worldPlayerSample(ProbeClientNum);
        if (!sample || sample->playerState.pmType != 0)
            return;
        const auto entity = Server.worldPlayerEntity(ProbeClientNum);
        if (!entity)
            return;

        // A player-sized capsule swept THROUGH the player, with no pass
        // filter, so he is a legal candidate.
        //
        // THE FIRST VERSION OF THIS SWEPT 64 UNITS ALONG X AND STARTED INSIDE
        // A WALL: fraction=0.047302 hitType=1 hitId=2046 startSolid=1, where
        // 2046 is the world. The locational probe's own segment 0 had already
        // measured that wall at 0.116 of 128 units -- about 15 units out --
        // and I aimed at it anyway. A world hit NEARER than the player is not
        // a failure of the entity half; it means the entity half never got a
        // chance, exactly as segment 0 of the locational probe does not.
        //
        // So it sweeps several lines and stops at the first ENTITY hit. The
        // short ones matter most: a player capsule has a radius near 15, so
        // 40 units of separation clears the two capsules at the start and
        // still crosses the player, and 40 units of open space is a much
        // weaker assumption about a map than 64.
        const auto origin = sample->playerState.origin;
        const std::array<std::pair<std::array<float, 3>,
            std::array<float, 3>>, 5> segments{
            std::pair{
                std::array{ origin[0], origin[1] - 40.0f, origin[2] },
                std::array{ origin[0], origin[1] + 40.0f, origin[2] }},
            std::pair{
                std::array{ origin[0] - 40.0f, origin[1], origin[2] },
                std::array{ origin[0] + 40.0f, origin[1], origin[2] }},
            std::pair{
                std::array{ origin[0], origin[1] - 64.0f, origin[2] },
                std::array{ origin[0], origin[1] + 64.0f, origin[2] }},
            std::pair{
                std::array{ origin[0], origin[1] - 40.0f, origin[2] + 16.0f },
                std::array{ origin[0], origin[1] + 40.0f, origin[2] + 16.0f }},
            std::pair{
                std::array{ origin[0] - 40.0f, origin[1] - 40.0f, origin[2] },
                std::array{ origin[0] + 40.0f, origin[1] + 40.0f, origin[2] }},
        };

        ++CapsuleEntityProbe.attemptCount;
        for (std::size_t segmentIndex{};
             segmentIndex < segments.size();
             ++segmentIndex)
        {
            const auto result = Server.traceWorldCapsule(
                segments[segmentIndex].first,
                segments[segmentIndex].second,
                entity->collisionBounds,
                CodolGameServer::PlayerCollisionContentMask,
                CodolGameServer::SvTraceEntityFilter{});
            if (!result)
            {
                logGameServer(
                    "capsule entity probe unavailable attempt=" +
                    std::to_string(CapsuleEntityProbe.attemptCount) +
                    " segment=" + std::to_string(segmentIndex));
                return;
            }

            logGameServer(
                "capsule entity probe result attempt=" +
                std::to_string(CapsuleEntityProbe.attemptCount) +
                " segment=" + std::to_string(segmentIndex) +
                " fraction=" + std::to_string(result->fraction) +
                " hitType=" + std::to_string(result->hitType) +
                " hitId=" + std::to_string(result->hitId) +
                " startSolid=" + std::to_string(result->startSolid ? 1 : 0));
            if (result->hitType != 0 && result->hitId == ProbeClientNum)
            {
                CapsuleEntityProbe.completed = true;
                logGameServer("capsule entity probe completed");
                return;
            }
        }
    }

    std::string_view loadoutResolveFailureName(
        const CodolGameServer::ClientLoadoutResolveFailure failure)
    {
        using Failure = CodolGameServer::ClientLoadoutResolveFailure;
        switch (failure)
        {
        case Failure::None: return "none";
        case Failure::StagedSlot: return "staged_slot";
        case Failure::NativeResolverUnavailable: return "native_resolver_unavailable";
        case Failure::ItemName: return "item_name";
        case Failure::BaseWeaponLookup: return "base_weapon_lookup";
        case Failure::BaseWeaponResolver: return "base_weapon_resolver";
        case Failure::DefaultAttachments: return "default_attachments";
        case Failure::EquippedAttachmentName: return "equipped_attachment_name";
        case Failure::EquippedAttachmentSlot: return "equipped_attachment_slot";
        case Failure::AttachmentMerge: return "attachment_merge";
        case Failure::AttachmentLookup: return "attachment_lookup";
        case Failure::AttachmentCapacity: return "attachment_capacity";
        case Failure::ModularWeaponResolver: return "modular_weapon_resolver";
        case Failure::WeaponDefinition: return "weapon_definition";
        case Failure::ModularWeaponDependency: return "modular_weapon_dependency";
        case Failure::AttachmentModelResolution: return "attachment_model_resolution";
        }
        return "unknown";
    }

    std::filesystem::path executableDirectory()
    {
        std::array<wchar_t, 32768> path{};
        const auto size = GetModuleFileNameW(
            nullptr, path.data(), static_cast<DWORD>(path.size()));
        if (!size || size >= path.size())
            return std::filesystem::current_path();
        return std::filesystem::path(path.data()).parent_path();
    }

    std::filesystem::path gameplayScriptRoot()
    {
        return executableDirectory() / L"Ayria" / L"Assets" / L"OlMod" /
            L"GameScripts";
    }

    std::optional<float> parseFiniteFloat(std::string_view value)
    {
        while (!value.empty() && value.front() == ' ')
            value.remove_prefix(1);
        while (!value.empty() && value.back() == ' ')
            value.remove_suffix(1);
        float result{};
        const auto parsed = std::from_chars(
            value.data(), value.data() + value.size(), result);
        return parsed.ec == std::errc{} &&
                parsed.ptr == value.data() + value.size() &&
                std::isfinite(result)
            ? std::optional{ result }
            : std::nullopt;
    }

    void drainGameplayScriptLogs()
    {
        for (const auto &entry : Server.takeGameplayScriptLogs())
        {
            const auto kind = [&entry]() -> std::string_view {
                switch (entry.kind)
                {
                case CodolGameServer::SvLuaLogKind::Print: return "print";
                case CodolGameServer::SvLuaLogKind::CompileError:
                    return "compile_error";
                case CodolGameServer::SvLuaLogKind::RuntimeError:
                    return "runtime_error";
                case CodolGameServer::SvLuaLogKind::HostError:
                    return "host_error";
                }
                return "unknown";
            }();
            auto message = "gameplay script generation=" +
                std::to_string(entry.generation) + " kind=" +
                std::string(kind) + " source=" + entry.sourceName +
                " message=" + entry.message;
            if (!entry.traceback.empty())
                message += " traceback=" + entry.traceback;
            logGameServer(message);
        }
    }

    bool configureBooking(
        const char *command,
        std::optional<OlMod::DedicatedSession::BookingSelection> selection,
        std::optional<OlMod::DedicatedSession::MatchRules> matchRules,
        CodolGameServer::SvConfigStringGenerationRequirement
            generationRequirement = CodolGameServer::
                SvConfigStringGenerationRequirement::NewGeneration);

    OlMod::DedicatedControl::GameServerEndpointStatus dedicatedEndpointStatus()
    {
        const auto server = Server.status();
        const auto transport = Network.status();
        return {
            .sessionConfigured = server.sessionConfigured,
            .enabled = server.enabled,
            .bound = transport.bound,
            .port = transport.port,
        };
    }

    std::string dedicatedGameplayStatusPayload()
    {
        const auto source = Server.gameplayPresentationStatus();
        const auto optionalClient = [](const std::optional<std::uint32_t> value) {
            return value.value_or(std::numeric_limits<std::uint32_t>::max());
        };
        OlMod::DedicatedControl::GameplayStatus status{
            .serverTime = source.serverTime,
            .sd = {
                .roundConfigured = source.sd.round.configured,
                .roundArmed = source.sd.round.armed,
                .roundCompleted = source.sd.round.completed,
                .roundsPlayed = source.sd.round.roundsPlayed,
                .roundWinner = static_cast<std::uint32_t>(
                    source.sd.round.winner),
                .roundEndReason = static_cast<std::uint32_t>(
                    source.sd.round.endReason),
                .bombConfigured = source.sd.bomb.configured,
                .bombPhase = static_cast<std::uint32_t>(source.sd.bomb.phase),
                .attackers = source.sd.teams.attackers,
                .defenders = source.sd.teams.defenders,
                .attackersAlive = source.sd.teams.attackersAlive,
                .defendersAlive = source.sd.teams.defendersAlive,
                .carrierClientNum = optionalClient(
                    source.sd.bomb.carrierClientNum),
                .planterClientNum = optionalClient(
                    source.sd.bomb.planterClientNum),
                .defuserClientNum = optionalClient(
                    source.sd.bomb.defuserClientNum),
                .plantedSiteLabel = static_cast<std::uint32_t>(
                    source.sd.bomb.plantedSiteLabel &&
                            source.sd.bomb.plantedSiteLabel->size() == 1
                        ? static_cast<unsigned char>(
                            (*source.sd.bomb.plantedSiteLabel)[0])
                        : 0),
                .phaseStartServerTime =
                    source.sd.bomb.phaseStartServerTime,
                .plantedServerTime = source.sd.bomb.plantedServerTime,
            },
        };
        status.clients.reserve(source.clients.size());
        for (const auto &sourceClient : source.clients)
        {
            const auto ingress = Server.clientIngressStatus(
                sourceClient.clientNum);
            const auto peerTransport = ingress
                ? Network.peerStatus(ingress->peer)
                : std::nullopt;
            const auto think = Server.worldClientThinkStatus(
                sourceClient.clientNum);
            // OLMOD(locational-hit-readout): schema 5. Frida cannot sample this
            // - CodolGameServerControl.py --pid <dedicated> terminated the
            // dedicated two runs out of three - so the authoritative origin and
            // the last committed bullet trace travel over the control socket
            // instead. start + (end - start) * fraction is the world point the
            // server resolved the hit to, and subtracting the TARGET's origin
            // from the same sample gives its height above their feet.
            const auto worldPlayerState = Server.worldPlayerState(
                sourceClient.clientNum);
            const auto bullet = Server.worldBulletExecutionStatus(
                sourceClient.clientNum);
            const auto &lastDispatched = ingress
                ? ingress->lastDispatchedUserCmd
                : std::optional<CodolGameServer::UserCmd>{};
            OlMod::DedicatedControl::GameplayClientStatus client{
                .clientNum = sourceClient.clientNum,
                .gameplayState = static_cast<std::uint32_t>(
                    sourceClient.gameplayState),
                .team = static_cast<std::uint32_t>(sourceClient.team),
                .reliableSequence = sourceClient.reliable.sequence,
                .reliableAcknowledge = sourceClient.reliable.acknowledge,
                .peerIpv4 = ingress ? ingress->peer.ipv4 : 0,
                .peerPort = ingress
                    ? ingress->peer.port
                    : std::uint16_t{},
                .lastPacketReceivedTime = ingress
                    ? ingress->lastPacketTime
                    : 0,
                .incomingSequence = ingress ? ingress->incomingSequence : 0,
                .outgoingSequence = ingress ? ingress->outgoingSequence : 0,
                .messageAcknowledge = ingress
                    ? ingress->messageAcknowledge
                    : 0,
                .udpSendAttempts = peerTransport
                    ? peerTransport->sendAttempts
                    : 0,
                .udpSendSucceeded = peerTransport
                    ? peerTransport->sendSucceeded
                    : 0,
                .udpSendFailed = peerTransport
                    ? peerTransport->sendFailed
                    : 0,
                .udpBytesSent = peerTransport ? peerTransport->bytesSent : 0,
                .lastUdpSendTime = peerTransport
                    ? peerTransport->lastSendTime
                    : 0,
                .lastUdpSendBytes = peerTransport
                    ? peerTransport->lastSendBytes
                    : 0,
                .lastUdpSendError = peerTransport
                    ? peerTransport->lastSendError
                    : 0,
                .pendingUserCmdCount = sourceClient.pendingUserCmdCount,
                .oldestPendingUserCmdTime = optionalClient(
                    sourceClient.oldestPendingUserCmdTime),
                .newestPendingUserCmdTime = optionalClient(
                    sourceClient.newestPendingUserCmdTime),
                .lastReceivedUserCmdTime = optionalClient(
                    sourceClient.lastReceivedUserCmdTime),
                .lastDispatchedUserCmdTime = optionalClient(
                    sourceClient.lastDispatchedUserCmdTime),
                .lastExecutedUserCmdTime = optionalClient(
                    sourceClient.lastExecutedUserCmdTime),
                .lastDiscardedUserCmdTime = optionalClient(
                    sourceClient.lastDiscardedUserCmdTime),
                .discardedUnsupportedUserCmds =
                    sourceClient.discardedUnsupportedUserCmds,
                .lastDiscardedRejectedUserCmdTime = optionalClient(
                    ingress && ingress->lastDiscardedRejectedUserCmd
                        ? std::optional{
                              ingress->lastDiscardedRejectedUserCmd->commandTime }
                        : std::nullopt),
                .discardedRejectedUserCmds = ingress
                    ? ingress->discardedRejectedUserCmds
                    : 0,
                .clientThinkLastAttemptedCommandTime = optionalClient(
                    think ? std::optional{ think->lastAttemptedCommandTime }
                          : std::nullopt),
                .clientThinkLastCommittedCommandTime = optionalClient(
                    think ? std::optional{ think->lastCommittedCommandTime }
                          : std::nullopt),
                .clientThinkFailureStage = think
                    ? static_cast<std::uint32_t>(think->failureStage)
                    : 0,
                .clientThinkFailureCount = think ? think->failureCount : 0,
                .lastDispatchedButtons = lastDispatched
                    ? lastDispatched->buttons : 0,
                .lastDispatchedAngles = lastDispatched
                    ? std::array<std::uint32_t, 3>{
                          lastDispatched->angles[0], lastDispatched->angles[1],
                          lastDispatched->angles[2] }
                    : std::array<std::uint32_t, 3>{},
                .lastDispatchedWeapon = lastDispatched
                    ? static_cast<std::uint32_t>(lastDispatched->weapon) : 0u,
                .lastDispatchedOffhand = lastDispatched
                    ? static_cast<std::uint32_t>(lastDispatched->offHandIndex)
                    : 0u,
                .lastDispatchedForwardMove = lastDispatched
                    ? static_cast<std::int32_t>(lastDispatched->forwardMove)
                    : 0,
                .lastDispatchedRightMove = lastDispatched
                    ? static_cast<std::int32_t>(lastDispatched->rightMove)
                    : 0,
                .snapshotPlayerEntityMask =
                    sourceClient.snapshotPlayerEntityMask,
                .snapshotClientInfoMask =
                    sourceClient.snapshotClientInfoMask,
                .origin = worldPlayerState
                    ? worldPlayerState->origin
                    : std::array<float, 3>{},
                .viewAngles = worldPlayerState
                    ? worldPlayerState->viewAngles
                    : std::array<float, 3>{},
                .health = worldPlayerState ? worldPlayerState->health : 0,
                .bulletCommandTime = bullet
                    ? bullet->commandTime
                    : std::numeric_limits<std::uint32_t>::max(),
                .bulletStart = bullet ? bullet->start : std::array<float, 3>{},
                .bulletEnd = bullet ? bullet->end : std::array<float, 3>{},
                .bulletFraction = bullet ? bullet->trace.fraction : 0.0f,
                .bulletHitType = bullet ? bullet->trace.hitType : 0u,
                .bulletHitEntityNum = bullet
                    ? bullet->hitEntityNum.value_or(
                          CodolGameServer::BulletNoneEntityNum)
                    : CodolGameServer::BulletNoneEntityNum,
                .bulletModelIndex = bullet ? bullet->trace.modelIndex : 0u,
                .bulletPartName = bullet ? bullet->trace.partName : 0u,
                .bulletPartGroup = bullet ? bullet->trace.partGroup : 0u,
                .bulletResult = bullet
                    ? static_cast<std::uint32_t>(bullet->result)
                    : 0u,
            };
            for (std::size_t index{}; index < client.objectives.size(); ++index)
            {
                client.objectives[index] = {
                    .state = static_cast<std::uint32_t>(
                        sourceClient.objectives[index].state),
                    .icon = sourceClient.objectives[index].icon,
                };
            }
            client.recentReliableCommands.reserve(
                sourceClient.reliable.recentCommands.size());
            for (const auto &sourceCommand :
                 sourceClient.reliable.recentCommands)
            {
                client.recentReliableCommands.push_back({
                    .sequence = sourceCommand.sequence,
                    .command = sourceCommand.command,
                });
            }
            status.clients.push_back(std::move(client));
        }
        return OlMod::DedicatedControl::encodeGameplayStatus(status);
    }

    void logDedicatedProcessPatchFailure(
        const CodolGameServer::DedicatedProcessPatchResult result)
    {
        logGameServer(std::string("dedicated startup patch failed result=") +
            CodolGameServer::dedicatedProcessPatchResultName(result));
    }

    void ensureClientSessionBridge()
    {
        if (ClientSessionBridge && ClientSessionBridge->running())
            return;
        if (!ClientSessionBridge)
            ClientSessionBridge = new OlMod::ClientSessionBridge();

        static std::uint32_t lastAttemptMilliseconds{};
        const auto now = GetTickCount();
        if (lastAttemptMilliseconds && now - lastAttemptMilliseconds < 1000)
            return;
        lastAttemptMilliseconds = now;
        // WHAT A DIAGNOSTIC CAN BE ASKED FOR, AND WHY IT ONLY STARTS THINGS.
        //
        // Each of these used to cost a full cycle -- rebuild, relaunch, and the player
        // queueing up again -- to answer a question that is a loop over a table the
        // running client already holds. They start on a detached thread and report to the
        // log or a CSV; nothing is carried back over the bridge, so a slow audit can
        // never hold up the capture path.
        ClientSessionBridge->setDiagnostic(
            [](const std::string_view name) -> std::string {
                if (name == "item-names")
                {
                    std::thread([] { Bindings.auditItemNames(); }).detach();
                    return "item-names started -> Ayria\\Logs\\item-names.csv";
                }
                if (name == "equipped-equipment")
                {
                    std::thread([] { Bindings.auditEquippedEquipment(); }).detach();
                    return "equipped-equipment started -> CodolGameServer.log";
                }
                if (name == "equipped-perks")
                {
                    std::thread([] { Bindings.auditEquippedPerks(); }).detach();
                    return "equipped-perks started -> CodolGameServer.log";
                }
                if (name == "weapon-table")
                {
                    std::thread([] { Bindings.auditWeaponItemsTable(); }).detach();
                    return "weapon-table started -> log + Ayria\\Logs\\weapon-slots.csv";
                }
                if (name == "reward-table")
                {
                    std::thread([] { Bindings.auditRewardTable(); }).detach();
                    return "reward-table started -> reward-table-<pid>.csv + log";
                }
                if (name == "alpha-barrett-templates")
                {
                    std::thread([] {
                        Bindings.auditAlphaBarrettAssetTemplates();
                    }).detach();
                    return "alpha-barrett-templates started -> "
                           "alpha-barrett-final-templates-<pid>.tsv + log";
                }
                if (name == "unlock-coverage")
                {
                    std::thread([] { Bindings.reportUnlockAllCoverage(); }).detach();
                    return "unlock-coverage started -> log";
                }
                // WATCH THE CLIENT DISPATCH EVERY RELIABLE COMMAND. Unlike the three above
                // this one is not a sweep on a thread -- it patches a prologue and then
                // records from whatever thread the engine dispatches on. So it runs INLINE
                // here: a detached thread would report success before the patch existed, and
                // "did the hook install" is the only question its reply can usefully answer.
                if (name == "trace-commands")
                {
                    return CodolGameServer::installClientCommandTrace(Bindings)
                        ? CodolGameServer::clientCommandTraceStatus()
                        : "trace-commands FAILED to install -- see client-commands.csv for "
                          "the reason, or the prologue moved in this build";
                }
                if (name == "trace-commands-stop")
                {
                    CodolGameServer::stopClientCommandTrace();
                    return CodolGameServer::clientCommandTraceStatus();
                }
                if (name == "trace-commands-status")
                {
                    return CodolGameServer::clientCommandTraceStatus();
                }
                // THE PLAYERSTATE MIRROR. Also inline, and for a different reason from the
                // command trace: it starts a thread, and whether that thread STARTED is the
                // only thing its reply can honestly report.
                if (name == "trace-playerstate")
                {
                    return CodolGameServer::installPlayerStateTrace(Bindings, 8)
                        ? CodolGameServer::playerStateTraceStatus()
                        : "trace-playerstate FAILED to start";
                }
                if (name == "trace-playerstate-stop")
                {
                    CodolGameServer::stopPlayerStateTrace();
                    return CodolGameServer::playerStateTraceStatus();
                }
                if (name == "trace-playerstate-status")
                {
                    return CodolGameServer::playerStateTraceStatus();
                }
                // WHAT com_maxfps IS AND WHAT THE CLIENT ACTUALLY REACHES. The dvar is
                // registered max=200, and Com_Frame's limiter is 1000/maxfps in INTEGER
                // milliseconds plus Sleep(1), so 200 lands at ~186-190. Zero skips the
                // limiter outright. These measure it instead of arguing about it.
                if (name == "fps")
                {
                    return CodolGameServer::startFpsProbe(Bindings, false, 0, 3000)
                        ? "fps probe sampling 3s -> log"
                        : "fps probe FAILED to start";
                }
                if (name == "fps-uncap")
                {
                    return CodolGameServer::startFpsProbe(Bindings, true, 0, 3000)
                        ? "com_maxfps <- 0, sampling 3s -> log"
                        : "fps probe FAILED to start";
                }
                if (name == "fps-restore")
                {
                    return CodolGameServer::startFpsProbe(Bindings, true, 200, 3000)
                        ? "com_maxfps <- 200, sampling 3s -> log"
                        : "fps probe FAILED to start";
                }
                // ANY VALUE, BECAUSE HARDCODING TWO OF THEM WAS THE MISTAKE. The first
                // version of this probe shipped `fps-uncap` (0) and `fps-restore` (200)
                // and nothing else, so the very next question -- "try 250" -- could not be
                // answered without a rebuild and a cycle, on a tool whose entire purpose is
                // trying values. A diagnostic that can only ask the questions its author
                // already thought of is a worse instrument than one that takes an argument.
                if (name.starts_with("fps-set-"))
                {
                    const auto digits = name.substr(8);
                    std::uint32_t requested{};
                    const auto *const first = digits.data();
                    const auto *const last = first + digits.size();
                    const auto parsed = std::from_chars(first, last, requested);
                    if (parsed.ec != std::errc{} || parsed.ptr != last ||
                        requested > 10000)
                    {
                        return "fps-set-<n> needs a whole number 0..10000; 0 removes the "
                               "limiter entirely";
                    }
                    return CodolGameServer::startFpsProbe(
                               Bindings, true, requested, 3000)
                        ? "com_maxfps <- " + std::to_string(requested) +
                            ", sampling 3s -> log"
                        : "fps probe FAILED to start";
                }
                return "unknown diagnostic '" + std::string(name) +
                    "'; known: item-names, weapon-table, reward-table, alpha-barrett-templates, "
                    "unlock-coverage, trace-commands, "
                    "trace-commands-stop, trace-commands-status, fps, fps-uncap, "
                    "fps-restore, fps-set-<n>";
            });

        if (ClientSessionBridge->start(
                OlMod::DedicatedControl::configuredClientBridgePort()))
        {
            logGameServer("client session bridge listening port=" +
                std::to_string(
                    OlMod::DedicatedControl::configuredClientBridgePort()));
        }
    }

    void ensureDedicatedControlServer()
    {
        if (DedicatedControlServer && DedicatedControlServer->running())
            return;
        if (!DedicatedControlServer)
            DedicatedControlServer = new OlMod::DedicatedControl::Server();

        static std::uint32_t lastAttemptMilliseconds{};
        const auto now = GetTickCount();
        if (lastAttemptMilliseconds && now - lastAttemptMilliseconds < 1000)
            return;
        lastAttemptMilliseconds = now;
        const auto started = DedicatedControlServer->start(
            OlMod::DedicatedControl::configuredPort(),
            [](const OlMod::DedicatedControl::Message &message) {
                if (message.type ==
                    OlMod::DedicatedControl::MessageType::ConfigureSession)
                {
                    const auto descriptor = std::span(
                        reinterpret_cast<const std::uint8_t *>(
                            message.payload.data()),
                        message.payload.size());
                    const auto configured = !descriptor.empty() &&
                        Server.configureSessionDescriptor(descriptor) &&
                        Network.start();
                    if (configured)
                        Server.setEnabled(true);
                    const auto endpoint = dedicatedEndpointStatus();
                    logGameServer(
                        std::string("ConfigureSession ") +
                        (configured ? "accepted" : "rejected") +
                        " bytes=" + std::to_string(descriptor.size()) +
                        " endpoint=" + std::to_string(endpoint.port));
                    return OlMod::DedicatedControl::Response{
                        .status = configured
                            ? OlMod::DedicatedControl::ResponseStatus::Accepted
                            : OlMod::DedicatedControl::ResponseStatus::Rejected,
                        .payload = OlMod::DedicatedControl::encodeEndpointStatus(
                            dedicatedEndpointStatus()),
                    };
                }
                if (message.type ==
                    OlMod::DedicatedControl::MessageType::QueryEndpoint)
                {
                    if (!message.payload.empty())
                    {
                        return OlMod::DedicatedControl::Response{
                            .status = OlMod::DedicatedControl::ResponseStatus::InvalidMessage,
                        };
                    }
                    return OlMod::DedicatedControl::Response{
                        .status = OlMod::DedicatedControl::ResponseStatus::Accepted,
                        .payload = OlMod::DedicatedControl::encodeEndpointStatus(
                            dedicatedEndpointStatus()),
                    };
                }
                if (message.type ==
                    OlMod::DedicatedControl::MessageType::QueryGameplayStatus)
                {
                    if (!message.payload.empty())
                    {
                        return OlMod::DedicatedControl::Response{
                            .status = OlMod::DedicatedControl::ResponseStatus::InvalidMessage,
                        };
                    }
                    const auto payload = dedicatedGameplayStatusPayload();
                    return OlMod::DedicatedControl::Response{
                        .status = payload.empty()
                            ? OlMod::DedicatedControl::ResponseStatus::Rejected
                            : OlMod::DedicatedControl::ResponseStatus::Accepted,
                        .payload = payload,
                    };
                }
                if(message.type==OlMod::DedicatedControl::MessageType::DebugGrantBattery) {
                    std::optional<std::uint32_t> target;
                    bool valid=message.payload.empty();
                    if(!message.payload.empty()) {
                        std::uint32_t slot{};
                        const auto parsed=std::from_chars(message.payload.data(),
                            message.payload.data()+message.payload.size(),slot);
                        valid=parsed.ec==std::errc{} &&
                            parsed.ptr==message.payload.data()+message.payload.size() && slot<18;
                        if(valid)target=slot;
                    }
                    const bool accepted=valid && Server.debugGrantFactoryBattery(message.peerIpv4,target);
                    return OlMod::DedicatedControl::Response{
                        .status=accepted ? OlMod::DedicatedControl::ResponseStatus::Accepted
                                         : OlMod::DedicatedControl::ResponseStatus::Rejected};
                }
                if (message.type ==
                    OlMod::DedicatedControl::MessageType::SetNoclip)
                {
                    const auto request =
                        OlMod::DedicatedControl::decodeNoclipRequest(
                            message.payload);
                    if (!request)
                    {
                        return OlMod::DedicatedControl::Response{
                            .status = OlMod::DedicatedControl::
                                ResponseStatus::InvalidMessage,
                        };
                    }
                    const auto resolved = Server.setPlayerNoclipForSender(
                        request->userId,
                        message.peerIpv4,
                        request->enabled,
                        request->holdMilliseconds);
                    // SILENT WHEN HEALTHY. The poller repeats twice a second
                    // while the key is down, and a line per repeat would bury
                    // every other diagnostic in the log. Only the EDGES speak,
                    // plus every failure -- a request that resolves to nobody
                    // is the one thing worth hearing about every time.
                    static std::map<std::uint32_t, bool> announced;
                    auto &last = announced[message.peerIpv4];
                    if (last != request->enabled || !resolved)
                    {
                        last = request->enabled;
                        logGameServer(
                            std::string("noclip ") +
                            (request->enabled ? "on" : "off") + " from=" +
                            OlMod::DedicatedControl::ipv4Text(
                                message.peerIpv4) +
                            (resolved
                                ? " client=" +
                                    std::to_string(resolved->clientNum) +
                                    " xuid=" + std::to_string(resolved->xuid) +
                                    (resolved->ambiguous
                                        ? " (SHARED ADDRESS, took the lowest"
                                          " active slot)"
                                        : "")
                                : std::string(" NO ACTIVE CLIENT AT THAT"
                                              " ADDRESS")));
                    }
                    return OlMod::DedicatedControl::Response{
                        .status = resolved
                            ? OlMod::DedicatedControl::ResponseStatus::Accepted
                            : OlMod::DedicatedControl::ResponseStatus::Rejected,
                    };
                }
                if (message.type ==
                    OlMod::DedicatedControl::MessageType::SessionStart)
                {
                    const auto session =
                        OlMod::DedicatedSession::decodeSessionStart({
                            reinterpret_cast<const std::uint8_t *>(
                                message.payload.data()),
                            message.payload.size(),
                        });
                    if (!session)
                    {
                        logGameServer("SessionStart rejected: invalid payload");
                        return OlMod::DedicatedControl::Response{
                            .status = OlMod::DedicatedControl::ResponseStatus::InvalidMessage,
                        };
                    }
                    // PIN THE GAMETYPE HERE, AT THE ONE FUNNEL EVERY PATH USES.
                    //
                    // Section 187o. The first attempt pinned it in
                    // CODOL_GameServerConfigureBooking, next to
                    // readClientBookingSelection -- and the served gametype stayed
                    // `cha`, because a SessionStart arrives as a CONTROL MESSAGE with
                    // its booking already decided by the backend dispatcher and never
                    // passes through that export at all. Measured: no `PINNED` line and
                    // `configureGameState entry booked=cha` in the same cycle.
                    //
                    // WHY IT MATTERS: dm.lua leaves every player at team None so
                    // `issameteam` is false for every pair and everyone is damageable;
                    // cha.lua puts players on real sides. Two players on one side cannot
                    // hurt each other, which is what "I still can't do damage" is.
                    //
                    // The MAP and members still come from the real booking. Only the
                    // gametype is pinned, until team assignment splits two players.
                    auto pinnedSession = *session;
                    // `zm` is not an ordinary team-vs-team script.  It owns the
                    // zombie round, spawner, barrier and AI setup, so replacing it
                    // with dm leaves the Factory map loaded but never starts the
                    // zombie game.  Keep the damage-workaround pin for the PvP team
                    // modes it was written for, but never apply it to Zombie Siege.
                    if (pinnedSession.booking.gameType != "zm" &&
                        !gameTypeIsTeamless(pinnedSession.booking.gameType))
                    {
                        logGameServer(
                            "SessionStart gametype PINNED " +
                            pinnedSession.booking.gameType +
                            " -> dm (section 187o: a team mode leaves both players on"
                            " one side and nothing can be damaged); map=" +
                            pinnedSession.booking.mapName + " kept");
                        pinnedSession.booking.gameType = "dm";
                    }
                    {
                        const std::lock_guard lock(DedicatedControlMutex);
                        DedicatedSessionStarts.push_back({
                            .requestId = message.requestId,
                            .session = pinnedSession,
                        });
                        DedicatedSessionConsumption.queued(message.requestId);
                    }
                    logGameServer(
                        "SessionStart queued request=" +
                        std::to_string(message.requestId) + " map=" +
                        pinnedSession.booking.mapName + " gametype=" +
                        pinnedSession.booking.gameType + " members=" +
                        std::to_string(pinnedSession.members.size()));
                    return OlMod::DedicatedControl::Response{
                        .status = OlMod::DedicatedControl::ResponseStatus::Accepted,
                    };
                }
                if (message.type ==
                    OlMod::DedicatedControl::MessageType::UpdateLoadout)
                {
                    // payload = u64 userId + encode(LoadoutRequest). Decoded here,
                    // applied on the game thread (§157c).
                    if (message.payload.size() < sizeof(std::uint64_t))
                    {
                        return OlMod::DedicatedControl::Response{
                            .status = OlMod::DedicatedControl::ResponseStatus::InvalidMessage,
                        };
                    }
                    std::uint64_t userId{};
                    std::memcpy(
                        &userId, message.payload.data(), sizeof(userId));
                    const auto loadout = OlMod::DedicatedSession::decodeLoadout({
                        reinterpret_cast<const std::uint8_t *>(
                            message.payload.data()) + sizeof(userId),
                        message.payload.size() - sizeof(userId),
                    });
                    if (!userId || !loadout ||
                        !OlMod::DedicatedSession::valid(*loadout))
                    {
                        logGameServer("UpdateLoadout rejected: invalid payload");
                        return OlMod::DedicatedControl::Response{
                            .status = OlMod::DedicatedControl::ResponseStatus::InvalidMessage,
                        };
                    }
                    {
                        const std::lock_guard lock(DedicatedControlMutex);
                        DedicatedLoadoutUpdates.push_back({
                            .requestId = message.requestId,
                            .userId = userId,
                            .loadout = *loadout,
                        });
                    }
                    logGameServer(
                        "UpdateLoadout queued request=" +
                        std::to_string(message.requestId) + " user=" +
                        std::to_string(userId) + " classMask=" +
                        std::to_string(loadout->classMask));
                    return OlMod::DedicatedControl::Response{
                        .status = OlMod::DedicatedControl::ResponseStatus::Accepted,
                    };
                }
                if (message.type ==
                    OlMod::DedicatedControl::MessageType::PlayAnnouncer)
                {
                    if (message.payload.size() < sizeof(std::uint16_t))
                    {
                        return OlMod::DedicatedControl::Response{
                            .status = OlMod::DedicatedControl::ResponseStatus::InvalidMessage,
                        };
                    }
                    std::uint16_t announcerParameter{};
                    std::memcpy(
                        &announcerParameter,
                        message.payload.data(),
                        sizeof(announcerParameter));
                    // The SAME bound queueLocalSound enforces. A parameter below
                    // the constant-string base would address the MAP's alias
                    // table and play whatever ambience that index happens to
                    // hold, which is the 100..102 mistake of section 112b in a
                    // new costume - so it is refused rather than played.
                    if (announcerParameter <
                            CodolGameServer::SoundAliasConstantStringBase ||
                        announcerParameter >=
                            CodolGameServer::LocalSoundEventParameterMaximum)
                    {
                        logGameServer(
                            "PlayAnnouncer rejected: parameter " +
                            std::to_string(announcerParameter) +
                            " is outside the announcer band");
                        return OlMod::DedicatedControl::Response{
                            .status = OlMod::DedicatedControl::ResponseStatus::InvalidMessage,
                        };
                    }
                    {
                        const std::lock_guard lock(DedicatedControlMutex);
                        DedicatedAnnouncerAuditions.push_back(announcerParameter);
                    }
                    logGameServer(
                        "PlayAnnouncer queued request=" +
                        std::to_string(message.requestId) + " p " +
                        std::to_string(announcerParameter));
                    return OlMod::DedicatedControl::Response{
                        .status = OlMod::DedicatedControl::ResponseStatus::Accepted,
                    };
                }
                if (message.type ==
                    OlMod::DedicatedControl::MessageType::SendRawCommand)
                {
                    // OPT-IN ONLY. A malformed binary reliable command can
                    // desync the netchan or take the client down -- section
                    // 181's `%` crash is the precedent -- so this stays off
                    // unless someone has deliberately switched it on.
                    std::size_t length{};
                    char allow[8]{};
                    const auto enabled =
                        getenv_s(&length, allow, sizeof(allow),
                                 "OLMOD_ALLOW_RAW_COMMAND") == 0 &&
                        length && allow[0] == '1';
                    if (!enabled || message.payload.empty())
                    {
                        logGameServer(
                            "SendRawCommand refused: set "
                            "OLMOD_ALLOW_RAW_COMMAND=1 to replay raw wire "
                            "bytes into a live match");
                        return OlMod::DedicatedControl::Response{
                            .status = OlMod::DedicatedControl::ResponseStatus::InvalidMessage,
                        };
                    }
                    {
                        const std::lock_guard lock(DedicatedControlMutex);
                        DedicatedRawCommands.emplace_back(
                            message.payload.begin(), message.payload.end());
                    }
                    logGameServer(
                        "SendRawCommand queued request=" +
                        std::to_string(message.requestId) + " bytes=" +
                        std::to_string(message.payload.size()));
                    return OlMod::DedicatedControl::Response{
                        .status = OlMod::DedicatedControl::ResponseStatus::Accepted,
                    };
                }
                if (message.type !=
                    OlMod::DedicatedControl::MessageType::Booking)
                {
                    return OlMod::DedicatedControl::Response{
                        .status = OlMod::DedicatedControl::ResponseStatus::UnsupportedMessage,
                    };
                }
                if (message.payload.empty() ||
                    message.payload.size() > OlMod::DedicatedControl::MaximumPayloadSize)
                {
                    return OlMod::DedicatedControl::Response{
                        .status = OlMod::DedicatedControl::ResponseStatus::InvalidMessage,
                    };
                }
                const std::lock_guard lock(DedicatedControlMutex);
                DedicatedBookingCommands.push_back(message.payload);
                return OlMod::DedicatedControl::Response{
                    .status = OlMod::DedicatedControl::ResponseStatus::Accepted,
                };
            });
        if (started)
        {
            logGameServer("dedicated control listening port=" +
                std::to_string(OlMod::DedicatedControl::configuredPort()));
        }
    }

    void processDedicatedControlMessages()
    {
        std::deque<std::string> commands;
        std::deque<QueuedDedicatedSessionStart> sessions;
        std::deque<QueuedDedicatedSessionStart> deferredSessions;
        std::deque<QueuedLoadoutUpdate> loadoutUpdates;
        std::deque<std::uint16_t> announcerAuditions;
        std::deque<std::vector<std::uint8_t>> rawCommands;
        {
            const std::lock_guard lock(DedicatedControlMutex);
            commands.swap(DedicatedBookingCommands);
            sessions.swap(DedicatedSessionStarts);
            loadoutUpdates.swap(DedicatedLoadoutUpdates);
            announcerAuditions.swap(DedicatedAnnouncerAuditions);
            rawCommands.swap(DedicatedRawCommands);
        }
        for (const auto &raw : rawCommands)
        {
            const auto clients = Server.sendRawCommand(raw);
            std::string hex;
            for (const auto byte : raw)
            {
                static constexpr char Digits[] = "0123456789abcdef";
                hex += Digits[byte >> 4];
                hex += Digits[byte & 0xF];
            }
            logGameServer(
                "SendRawCommand sent " + std::to_string(raw.size()) +
                " bytes clients=" + std::to_string(clients) + " " + hex);
        }
        for (const auto announcerParameter : announcerAuditions)
        {
            const auto clients = Server.playAnnouncerLine(announcerParameter);
            logGameServer(
                "PlayAnnouncer sent p " + std::to_string(announcerParameter) +
                " clients=" + std::to_string(clients));
        }
        // LIVE LOADOUT REFRESHES, on the game thread. Independent of the session
        // pipeline below: a refresh only re-registers a member's weapons and
        // broadcasts their config strings; it never books or loads a map. §157c.
        for (const auto &update : loadoutUpdates)
        {
            const auto applied = refreshMemberLoadout(update.userId, update.loadout);
            logGameServer(
                std::string(applied ? "UpdateLoadout applied"
                                    : "UpdateLoadout FAILED") +
                " request=" + std::to_string(update.requestId) + " user=" +
                std::to_string(update.userId) + " classMask=" +
                std::to_string(update.loadout.classMask));
        }
        for (const auto &queued : sessions)
        {
            const auto &session = queued.session;
            std::vector<CodolGameServer::SessionRosterMember> roster;
            roster.reserve(session.members.size());
            std::ranges::transform(
                session.members,
                std::back_inserter(roster),
                [](const auto &member) {
                    return CodolGameServer::SessionRosterMember{
                        .xuid = member.userId,
                        .username = member.username,
                    };
                });
            std::uint32_t requestedClassMask{};
            for (const auto &member : session.members)
                requestedClassMask |= member.loadout.classMask;
            {
                const std::lock_guard lock(DedicatedControlMutex);
                DedicatedSessionConsumption.processing(
                    queued.requestId, requestedClassMask);
            }
            if (!Server.stageSessionRoster(queued.requestId, roster))
            {
                logGameServer("session roster rejected request=" +
                    std::to_string(queued.requestId));
                const std::lock_guard lock(DedicatedControlMutex);
                DedicatedSessionConsumption.failed(
                    CodolGameServer::DedicatedSessionConsumeStage::
                        SessionRosterRejected,
                    -1,
                    0);
                continue;
            }
            const auto failSession = [&](const auto stage,
                                         const std::int32_t failedClassIndex,
                                         const std::uint32_t resolvedClassMask) {
                static_cast<void>(Server.rollbackSessionRoster(queued.requestId));
                const std::lock_guard lock(DedicatedControlMutex);
                DedicatedSessionConsumption.failed(
                    stage, failedClassIndex, resolvedClassMask);
            };
            // Zone residency belongs to the map/gametype pair, not to a
            // matchmaking request. Re-entering the retail zone loader for a
            // second request on the already resident Wetwork map faults inside
            // out.exe. Reuse the loaded generation until the requested level
            // actually changes.
            const auto sameMapGeneration = DedicatedMapGeneration &&
                DedicatedMapGeneration->mapName == session.booking.mapName &&
                DedicatedMapGeneration->gameType == session.booking.gameType;
            if (!sameMapGeneration)
            {
                if (!Bindings.beginLevelZoneLoad(
                        session.booking.mapName,
                        session.booking.gameType))
                {
                    logGameServer("map asset load rejected map=" +
                        session.booking.mapName + " gametype=" +
                        session.booking.gameType);
                    failSession(
                        CodolGameServer::DedicatedSessionConsumeStage::
                            MapAssetLoadFailed,
                        -1,
                        0);
                    continue;
                }
                DedicatedMapGeneration = DedicatedMapGenerationPreparation{
                    .requestId = queued.requestId,
                    .mapName = session.booking.mapName,
                    .gameType = session.booking.gameType,
                };
                logGameServer("map asset load requested map=" +
                    session.booking.mapName + " gametype=" +
                    session.booking.gameType);
                {
                    const std::lock_guard lock(DedicatedControlMutex);
                    DedicatedSessionConsumption.waiting(
                        CodolGameServer::DedicatedSessionConsumeStage::
                            WaitingForMapAssets);
                }
                deferredSessions.push_back(queued);
                continue;
            }

            if (!Bindings.zoneLoaded(DedicatedMapGeneration->mapName))
            {
                const std::lock_guard lock(DedicatedControlMutex);
                DedicatedSessionConsumption.waiting(
                    CodolGameServer::DedicatedSessionConsumeStage::
                        WaitingForMapAssets);
                deferredSessions.push_back(queued);
                continue;
            }
            if (!DedicatedMapGeneration->levelWorldInitialized)
            {
                if (!Bindings.initializeLevelWorld(
                        DedicatedMapGeneration->mapName,
                        DedicatedMapGeneration->gameType))
                {
                    logGameServer("world initialization failed map=" +
                        DedicatedMapGeneration->mapName);
                    failSession(
                        CodolGameServer::DedicatedSessionConsumeStage::
                            WorldInitializationFailed,
                        -1,
                        0);
                    continue;
                }
                DedicatedMapGeneration->levelWorldInitialized = true;
                logGameServer("world initialized map=" +
                    DedicatedMapGeneration->mapName);
            }
            if (!DedicatedMapGeneration->configStringsCleared)
            {
                if (!Bindings.CCS_Clear())
                {
                    logGameServer("CCS generation reset failed");
                    failSession(
                        CodolGameServer::DedicatedSessionConsumeStage::
                            ConfigStringGenerationResetFailed,
                        -1,
                        0);
                    continue;
                }
                DedicatedMapGeneration->configStringsCleared = true;
                logGameServer("CCS generation reset complete");
            }
            // The client can only become ready for gamestate after it has
            // received the gamestate message. Waiting here would therefore
            // deadlock the dedicated handshake before configureBooking() can
            // publish the pending gamestate. Readiness remains an explicit
            // post-gamestate gate below in the native client state machine.
            const auto initialized = Bindings.CCS_Initialized();
            if (!initialized && !Bindings.CCS_EnsureInitialized())
            {
                const std::lock_guard lock(DedicatedControlMutex);
                DedicatedSessionConsumption.failed(
                    CodolGameServer::DedicatedSessionConsumeStage::
                        ConstantConfigStringsInitializationFailed,
                    -1,
                    0);
                deferredSessions.push_back(queued);
                continue;
            }
            if (!Bindings.initializeMantleAnimations())
            {
                logGameServer("mantle animation initialization failed");
                failSession(
                    CodolGameServer::DedicatedSessionConsumeStage::
                        WorldInitializationFailed,
                    -1,
                    0);
                continue;
            }
            const auto weaponRegistryStatus =
                Bindings.ensureWeaponRegistryInitialized();
            if (weaponRegistryStatus !=
                CodolGameServer::WeaponRegistryInitializationStatus::Ready)
            {
                if (weaponRegistryStatus != CodolGameServer::
                        WeaponRegistryInitializationStatus::
                            CommonAssetsUnavailable)
                {
                    logGameServer("weapon registry initialization failed status=" +
                        std::to_string(static_cast<std::uint32_t>(
                            weaponRegistryStatus)));
                }
                if (weaponRegistryStatus == CodolGameServer::
                        WeaponRegistryInitializationStatus::
                            CommonAssetsUnavailable)
                {
                    const std::lock_guard lock(DedicatedControlMutex);
                    DedicatedSessionConsumption.failed(
                        CodolGameServer::DedicatedSessionConsumeStage::
                            WeaponRegistryUnavailable,
                        -1,
                        0);
                    deferredSessions.push_back(queued);
                }
                else
                {
                    failSession(
                        CodolGameServer::DedicatedSessionConsumeStage::
                            WeaponRegistryInitializationFailed,
                        -1,
                        0);
                }
                continue;
            }
            const auto animationStatus =
                Bindings.initializeServerAnimationContext(
                    DedicatedMapGeneration->mapName,
                    DedicatedMapGeneration->gameType);
            if (animationStatus != CodolGameServer::
                    ServerAnimationInitializationStatus::Ready)
            {
                logGameServer("server animation initialization failed status=" +
                    std::string(CodolGameServer::
                        ServerAnimationInitializationStatusName(
                            animationStatus)));
                failSession(
                    CodolGameServer::DedicatedSessionConsumeStage::
                        WorldInitializationFailed,
                    -1,
                    0);
                continue;
            }
            PreparedClientLoadouts prepared;
            prepared.members.reserve(session.members.size());
            std::uint32_t resolvedClassMask{};
            std::int32_t failedClassIndex{-1};
            bool memberResolutionFailed{};
            for (const auto &sessionMember : session.members)
            {
                PreparedSessionMember preparedMember{
                    .xuid = sessionMember.userId,
                    .username = sessionMember.username,
                    .characterIndex = sessionMember.loadout.characterIndex,
                };
                const auto presentation =
                    Bindings.resolveSessionCharacterPresentation(
                        sessionMember.loadout);
                // CODDIFF(character_customization): THIS RESOLVER DOES NOT
                // EXIST ON OLfinal. CharacterSelectionResolve,
                // WorldCharacterModelResolve and both of their tables are
                // absent - handoff section 16a, re-checked in 18d on 1649370 -
                // because OLfinal replaced the whole scheme with an
                // item-driven one whose `ctx` argument and selection-id
                // ordering are still unknown.
                //
                // What it produces is COSMETIC: a character index, a colour, a
                // viewmodel index and eleven model selection ids. Failing the
                // entire match on it means no player ever loads a map on this
                // build over a wrong player model, which is the wrong trade.
                // So when the resolver is ABSENT - not when it is present and
                // rejects something - carry the character index through and go
                // on, loudly.
                // OLMOD(section-48-input-probe): print what the room roster holds at the
                // exact moment model resolution is attempted. Section 48c has asked
                // "are there real character item ids anywhere this server can reach"
                // since it was written, and the only answer on record is the
                // selectionIds=1,0,0,... placeholder -- which is this server's own
                // output, not a measurement of the engine's input.
                logGameServer(Bindings.reportSessionMemberItemHandles());
                if (!presentation &&
                    !Bindings.characterPresentationResolverAvailable())
                {
                    logGameServer(
                        "character presentation UNPORTED on this build "
                        "(CharacterSelectionResolve is absent, section 16a) - "
                        "continuing with character index " +
                        std::to_string(sessionMember.loadout.characterIndex) +
                        " and NO model selection; the player model, colour and "
                        "viewmodel will be wrong");
                    // AND IT HAS TO VALIDATE, OR "continue loudly" NEVER SPAWNS ANYONE.
                    // Carrying only the character index leaves viewmodelIndex 0 and all
                    // eleven selectionIds 0, and validCharacterCustomization rejects
                    // exactly that -- it requires a non-zero viewmodel and at least one
                    // non-zero selection. The customization then resolves to nullopt, and
                    // the spawn conjunction in SvServerWorld drops the term in silence, so
                    // picking a class does nothing on screen forever and the client
                    // re-sends the pick until it gives up.
                    //
                    // The trade this branch already chose was a WRONG player model over a
                    // failed match. A zeroed one is not wrong, it is invalid, which is a
                    // different and much worse thing. So fill the two fields the validator
                    // insists on with the smallest legal placeholders: viewmodel 1, and
                    // selection 0 set to 1 (slot 0 is 7 bits, so 1..128 are legal). The
                    // model, colour and viewmodel remain wrong exactly as advertised --
                    // now they are wrong AND the player spawns.
                    // AND SINCE SECTION 67 IT CARRIES THE ONE THING MODEL
                    // RESOLUTION ACTUALLY NEEDS. characterItemIds[0] is
                    // characterClasses[<character>].slots[0] -- the character item
                    // itself -- and sub_619AD0 derives the other eleven record entries
                    // from that character's own per-slot defaults. The viewmodel and
                    // selectionIds below stay the placeholders they were; they are the
                    // WIRE fields and this is not one.
                    //
                    // A zero here is not a defect: it is every match this build ran
                    // before the capture existed, and resolveCharacterModelNames refuses
                    // a zero rather than resolving definition index 0.
                    const auto characterItemId =
                        sessionMember.loadout.characterItemIds.empty()
                            ? std::uint32_t{}
                            : sessionMember.loadout.characterItemIds.front();
                    // AND THE OUTFIT, which is the other eleven entries. The capture
                    // already places each equipped piece at the record entry its own
                    // item definition claims, so this is a copy and not a re-derivation
                    // -- the client is the side that can read the item table.
                    static_assert(
                        std::tuple_size_v<decltype(
                            CodolGameServer::ClientCharacterPresentation{}
                                .recordItemIds)> ==
                        OlMod::DedicatedSession::CharacterItemCount,
                        "the presentation record and the session record must be the "
                        "same twelve entries, or an outfit lands in the wrong slot");
                    std::array<std::uint16_t,
                        OlMod::DedicatedSession::CharacterItemCount> recordItemIds{};
                    for (std::size_t entry = 0;
                        entry < recordItemIds.size() &&
                            entry < sessionMember.loadout.characterItemIds.size();
                        ++entry)
                    {
                        const auto itemId =
                            sessionMember.loadout.characterItemIds[entry];
                        if (itemId && itemId <= 0xFFFFu)
                            recordItemIds[entry] =
                                static_cast<std::uint16_t>(itemId);
                    }
                    preparedMember.characterPresentation =
                        CodolGameServer::ClientCharacterPresentation{
                            .characterIndex =
                                sessionMember.loadout.characterIndex,
                            .viewmodelIndex = 1,
                            .selectionIds = { 1 },
                            .characterItemId = characterItemId <= 0xFFFFu
                                ? static_cast<std::uint16_t>(characterItemId)
                                : std::uint16_t{},
                            .recordItemIds = recordItemIds,
                        };
                }
                else if (!presentation)
                {
                    logGameServer("character presentation failed xuid=" +
                        std::to_string(sessionMember.userId) + " character=" +
                        std::to_string(sessionMember.loadout.characterIndex));
                    const auto resolveStatus =
                        Bindings.characterPresentationResolveStatus();
                    // WHICH of the nine ways it failed, in the log rather than
                    // only in a control-message field nothing prints. "failed
                    // xuid=... character=3" is true of all nine.
                    logGameServer(
                        "character presentation detail failure=" +
                        std::to_string(static_cast<std::uint32_t>(
                            resolveStatus.failure)) +
                        " recordIndex=" +
                        std::to_string(resolveStatus.recordIndex) +
                        " itemId=" + std::to_string(resolveStatus.itemId));
                    failSession(
                        CodolGameServer::DedicatedSessionConsumeStage::
                            CharacterPresentationFailed,
                        -1,
                        resolvedClassMask);
                    {
                        const std::lock_guard lock(DedicatedControlMutex);
                        DedicatedSessionConsumption.characterFailure(
                            static_cast<std::uint32_t>(resolveStatus.failure),
                            resolveStatus.recordIndex,
                            resolveStatus.itemId);
                    }
                    memberResolutionFailed = true;
                    break;
                }
                else
                {
                    preparedMember.characterPresentation = *presentation;
                }
                preparedMember.rewards = Bindings.resolveSessionRewards(sessionMember.loadout);
                if (!preparedMember.rewards)
                    logGameServer("reward resolution unavailable xuid=" +
                        std::to_string(sessionMember.userId));
                std::uint32_t memberClassMask{};
                for (std::uint32_t classIndex = 0;
                     classIndex < sessionMember.loadout.classes.size();
                     ++classIndex)
                {
                    if (!(sessionMember.loadout.classMask & (1u << classIndex)))
                        continue;
                    const auto loadout = Bindings.resolveSessionWeaponLoadout(
                        sessionMember.loadout, classIndex);
                    const auto perks = Bindings.resolveSessionPerks(
                        sessionMember.loadout, classIndex);
                    const auto offhands = Bindings.resolveSessionEquipment(
                        sessionMember.loadout, classIndex);
                    if (!offhands)
                        logGameServer("equipment resolution failed xuid=" +
                            std::to_string(sessionMember.userId) + " class=" + std::to_string(classIndex));
                    if (!loadout || !perks || !offhands)
                    {
                        if (failedClassIndex < 0)
                        {
                            failedClassIndex =
                                static_cast<std::int32_t>(classIndex);
                        }
                        const auto &loadoutClass =
                            sessionMember.loadout.classes[classIndex];
                        logGameServer("loadout class skipped xuid=" +
                            std::to_string(sessionMember.userId) + " class=" +
                            std::to_string(classIndex) + " primaryItem=" +
                            std::to_string(loadoutClass.weapons[0].itemId) +
                            " secondaryItem=" +
                            std::to_string(loadoutClass.weapons[1].itemId) +
                            " failure=" + std::string(loadoutResolveFailureName(
                                Bindings.loadoutResolveFailure())));
                        continue;
                    }
                    preparedMember.loadouts.emplace(
                        "custom" + std::to_string(classIndex + 1), *loadout);
                    preparedMember.perks.emplace(
                        "custom" + std::to_string(classIndex + 1), *perks);
                    preparedMember.equipment.emplace(
                        "custom" + std::to_string(classIndex + 1),
                        sessionMember.loadout.classes[classIndex].equipment);
                    preparedMember.offhands.emplace(
                        "custom" + std::to_string(classIndex + 1), *offhands);
                    memberClassMask |= 1u << classIndex;
                }
                if (!memberClassMask)
                {
                    logGameServer("loadout resolution failed xuid=" +
                        std::to_string(sessionMember.userId) + " class=" +
                        std::to_string(failedClassIndex));
                    failSession(
                        CodolGameServer::DedicatedSessionConsumeStage::
                            WeaponLoadoutFailed,
                        failedClassIndex,
                        resolvedClassMask);
                    memberResolutionFailed = true;
                    break;
                }
                resolvedClassMask |= memberClassMask;
                prepared.members.push_back(std::move(preparedMember));
            }
            if (memberResolutionFailed)
                continue;
            if (!configureBooking(
                    session.bookingCommand.c_str(),
                    session.booking,
                    session.matchRules,
                    CodolGameServer::SvConfigStringGenerationRequirement::
                        CurrentGeneration))
            {
                logGameServer("booking configuration failed request=" +
                    std::to_string(queued.requestId));
                failSession(
                    CodolGameServer::DedicatedSessionConsumeStage::
                        ConfigureBookingFailed,
                    -1,
                    resolvedClassMask);
                continue;
            }
            {
                const std::lock_guard lock(LoadoutMutex);
                prepared.requestSequence = LoadoutPrepareRequestSequence;
                prepared.sessionGeneration = queued.requestId;
                PreparedLoadouts = std::move(prepared);
                LoadoutPreparation.currentCharacter =
                    static_cast<std::int32_t>(
                        session.members.front().loadout.characterIndex);
                LoadoutPreparation.resolvedClassMask = resolvedClassMask;
                LoadoutPreparation.registeredClassMask = resolvedClassMask;
                ++LoadoutPreparation.attemptCount;
            }
            ActiveDedicatedSession = session;
            logGameServer(
                "SessionStart accepted request=" +
                std::to_string(queued.requestId) + " map=" +
                session.booking.mapName + " gametype=" +
                session.booking.gameType + " classMask=" +
                std::to_string(resolvedClassMask));
            {
                const std::lock_guard lock(DedicatedControlMutex);
                DedicatedSessionConsumption.accepted(resolvedClassMask);
            }
        }
        if (!deferredSessions.empty())
        {
            const std::lock_guard lock(DedicatedControlMutex);
            while (!deferredSessions.empty())
            {
                DedicatedSessionStarts.push_front(
                    std::move(deferredSessions.back()));
                deferredSessions.pop_back();
            }
        }
        for (const auto &command : commands)
        {
            static_cast<void>(CODOL_GameServerConfigureBooking(command.c_str()));
        }
    }

    struct CodolWorldPlayerSampleV1
    {
        std::uint32_t structSize{};
        std::uint32_t schemaVersion{};
        std::uint32_t frameNumber{};
        std::uint32_t serverTime{};
        std::uint32_t userCmdValid{};
        std::uint32_t userCmdCommandTime{};
        std::uint32_t userCmdButtons{};
        std::array<std::uint32_t, 3> userCmdAngles{};
        std::uint32_t userCmdWeapon{};
        std::uint32_t userCmdOffHandIndex{};
        std::uint32_t userCmdLastWeaponAltModeSwitch{};
        std::int32_t userCmdForwardMove{};
        std::int32_t userCmdRightMove{};
        std::uint32_t playerCommandTime{};
        std::array<float, 3> playerOrigin{};
        std::array<float, 3> playerVelocity{};
        std::uint32_t groundEntityNum{};
        std::uint32_t gravity{};
        std::uint32_t speed{};
        float moveSpeedScaleMultiplier{};
        std::uint32_t pmTime{};
        std::uint32_t pmFlags{};
        std::uint32_t jumpTime{};
        float jumpOriginZ{};
        std::uint32_t eFlags{};
        std::uint32_t otherFlags{};
        float viewHeightCurrent{};
        std::int32_t viewHeightTarget{};
        std::int32_t viewHeightLerpTarget{};
        std::int32_t viewHeightLerpTime{};
        std::uint32_t viewHeightLerpDown{};
        std::uint32_t weaponValid{};
        std::uint32_t currentWeaponAssetIndex{};
        std::int32_t weaponTime{};
        std::int32_t weaponDelay{};
        std::uint32_t weaponState{};
        std::uint32_t weaponAnim{};
        std::uint32_t clipAmmo{};
        std::uint32_t weaponType{};
        std::uint32_t fireType{};
        std::uint32_t definitionFireDelay{};
        std::uint32_t definitionFireTime{};
    };

    static_assert(sizeof(CodolWorldPlayerSampleV1) == 192);
    static_assert(alignof(CodolWorldPlayerSampleV1) == alignof(std::uint32_t));

    struct CodolWorldPlayerSampleV2
    {
        CodolWorldPlayerSampleV1 base{};
        std::uint32_t pmType{};
        std::array<float, 3> viewAngles{};
        std::array<float, 3> deltaAngles{};
        std::array<float, 3> ladderVector{};
        std::uint32_t sprintButtonUpRequired{};
        std::uint32_t sprintDelay{};
        std::uint32_t lastSprintStart{};
        std::uint32_t lastSprintEnd{};
        std::uint32_t sprintStartMaxLength{};
        float mantleYaw{};
        std::uint32_t mantleTimer{};
        std::uint32_t mantleTransitionIndex{};
        std::uint32_t mantleFlags{};
        float weaponPositionFraction{};
        std::array<std::uint32_t, 2> weaponAnim{};
        std::array<std::int32_t, 2> weaponTime{};
        std::array<std::int32_t, 2> weaponDelay{};
        std::array<std::uint32_t, 2> weaponState{};
        std::array<std::uint32_t, 2> weaponHandFlags{};
        std::array<std::uint32_t, 2> weaponShotCount{};
        std::uint32_t legsTimer{};
        std::uint32_t legsAnim{};
        std::uint32_t torsoTimer{};
        std::uint32_t torsoAnim{};
        float proneDirection{};
        float proneDirectionPitch{};
        float proneTorsoPitch{};
        std::uint32_t bobCycle{};
    };

    static_assert(sizeof(CodolWorldPlayerSampleV2) == 352);
    static_assert(offsetof(CodolWorldPlayerSampleV2, pmType) == 192);

    CodolWorldPlayerSampleV1 makeWorldPlayerSampleV1(
        const CodolGameServer::SvWorldPlayerSample &sample,
        const std::uint32_t structSize = sizeof(CodolWorldPlayerSampleV1),
        const std::uint32_t schemaVersion = 1)
    {
        CodolWorldPlayerSampleV1 result{
            .structSize = structSize,
            .schemaVersion = schemaVersion,
            .frameNumber = sample.frameNumber,
            .serverTime = sample.serverTime,
            .playerCommandTime = sample.playerState.commandTime,
            .playerOrigin = sample.playerState.origin,
            .playerVelocity = sample.playerState.velocity,
            .groundEntityNum = sample.playerState.groundEntityNum,
            .gravity = sample.playerState.gravity,
            .speed = sample.playerState.speed,
            .moveSpeedScaleMultiplier = sample.playerState.moveSpeedScaleMultiplier,
            .pmTime = sample.playerState.pmTime,
            .pmFlags = sample.playerState.pmFlags,
            .jumpTime = sample.playerState.jumpTime,
            .jumpOriginZ = sample.playerState.jumpOriginZ,
            .eFlags = sample.playerState.eFlags,
            .otherFlags = sample.playerState.otherFlags,
            .viewHeightCurrent = sample.playerState.viewHeightCurrent,
            .viewHeightTarget = sample.playerState.viewHeightTarget,
            .viewHeightLerpTarget = sample.playerState.viewHeightLerpTarget,
            .viewHeightLerpTime = sample.playerState.viewHeightLerpTime,
            .viewHeightLerpDown = sample.playerState.viewHeightLerpDown ? 1u : 0u,
        };
        if (sample.lastReceivedUserCmd)
        {
            result.userCmdValid = 1;
            result.userCmdCommandTime = sample.lastReceivedUserCmd->commandTime;
            result.userCmdButtons = sample.lastReceivedUserCmd->buttons;
            result.userCmdAngles = {
                sample.lastReceivedUserCmd->angles[0],
                sample.lastReceivedUserCmd->angles[1],
                sample.lastReceivedUserCmd->angles[2],
            };
            result.userCmdWeapon = sample.lastReceivedUserCmd->weapon;
            result.userCmdOffHandIndex = sample.lastReceivedUserCmd->offHandIndex;
            result.userCmdLastWeaponAltModeSwitch =
                sample.lastReceivedUserCmd->lastWeaponAltModeSwitch;
            result.userCmdForwardMove = sample.lastReceivedUserCmd->forwardMove;
            result.userCmdRightMove = sample.lastReceivedUserCmd->rightMove;
        }
        if (sample.weapon)
        {
            result.weaponValid = 1;
            result.currentWeaponAssetIndex = sample.weapon->currentWeaponAssetIndex;
            result.weaponTime = sample.weapon->weaponTime;
            result.weaponDelay = sample.weapon->weaponDelay;
            result.weaponState = sample.weapon->weaponState;
            result.weaponAnim = sample.weapon->weaponAnim;
            result.clipAmmo = sample.weapon->clipAmmo;
            result.weaponType = sample.weapon->weaponType;
            result.fireType = sample.weapon->fireType;
            result.definitionFireDelay = sample.weapon->definitionFireDelay;
            result.definitionFireTime = sample.weapon->definitionFireTime;
        }
        return result;
    }

    CodolGameServer::SvResolvedWeapon toResolvedWeapon(
        const CodolGameServer::ClientWeaponSelection &weapon)
    {
        return {
            .weaponAssetIndex = static_cast<std::uint16_t>(weapon.weaponAssetIndex),
            .ammoIndex = static_cast<std::uint16_t>(weapon.ammoIndex),
            .clipIndex = static_cast<std::int16_t>(weapon.clipIndex),
            .clipSize = static_cast<std::uint16_t>(weapon.clipSize),
            .maxAmmo = static_cast<std::uint16_t>(weapon.maxAmmo),
            .weaponType = static_cast<std::uint8_t>(weapon.weaponType),
            .weaponClass = static_cast<std::uint8_t>(weapon.weaponClass),
            .penetrateType = static_cast<std::uint8_t>(weapon.penetrateType),
            .impactType = static_cast<std::uint8_t>(weapon.impactType),
            .fireType = static_cast<std::uint8_t>(weapon.fireType),
            .shotCount = static_cast<std::uint8_t>(weapon.shotCount),
            .fireDelayMilliseconds = static_cast<std::uint16_t>(
                weapon.fireDelayMilliseconds),
            .fireTimeMilliseconds = static_cast<std::uint16_t>(
                weapon.fireTimeMilliseconds),
            .dropTimeMilliseconds = static_cast<std::uint16_t>(
                weapon.dropTimeMilliseconds),
            .raiseTimeMilliseconds = static_cast<std::uint16_t>(
                weapon.raiseTimeMilliseconds),
            .hipSpreadStandMin = weapon.hipSpreadStandMin,
            .hipSpreadCrouchMin = weapon.hipSpreadCrouchMin,
            .hipSpreadProneMin = weapon.hipSpreadProneMin,
            .hipSpreadStandMax = weapon.hipSpreadStandMax,
            .hipSpreadCrouchMax = weapon.hipSpreadCrouchMax,
            .hipSpreadProneMax = weapon.hipSpreadProneMax,
            .adsSpread = weapon.adsSpread,
            .damageCurve = weapon.damageCurve,
            .hitLocationMultipliers = weapon.hitLocationMultipliers,
            .aimDownSight = weapon.aimDownSight != 0,
            .hasOverlayReticle = weapon.hasOverlayReticle != 0,
            .rifleBullet = weapon.rifleBullet != 0,
            .bulletExplosiveDamage = weapon.bulletExplosiveDamage != 0,
            .dualWieldCapable = weapon.dualWieldCapable,
            .weaponName = weapon.weaponName,
        };
    }

    CodolGameServer::SvResolvedLoadout toResolvedLoadout(
        const CodolGameServer::ClientWeaponLoadout &loadout)
    {
        return {
            .primary = toResolvedWeapon(loadout.primary),
            .secondary = toResolvedWeapon(loadout.secondary),
        };
    }

    struct RecordedCampaignWeapon
    {
        std::uint16_t recordedIndex;
        std::string_view definition;
    };

    // CODREF(C-2021-7-25[22-11-33]coop.demo): Wetwork's complete dynamic
    // weapon band. The numbers on the left are recording-local and are kept
    // only to make later traces readable. Every raw definition is registered
    // through CODOL before the outgoing gamestate is assembled, because the
    // player's own five classes change where this dense tail begins.
    constexpr std::array RecordedWetworkWeapons{
        RecordedCampaignWeapon{ 1163, "** 646 0 0 8738 9321" },
        RecordedCampaignWeapon{ 1164, "** 249 0 0" },
        RecordedCampaignWeapon{ 1165, "** 583 0 0 9930 10545 6690 8738 9321 6747 6825" },
        RecordedCampaignWeapon{ 1166, "** 604 0 0 9930 8738 6747 9321 10545 6690 6825" },
        RecordedCampaignWeapon{ 1167, "** 1108 0 0 9321 6747 6825" },
        RecordedCampaignWeapon{ 1168, "** 1038 140 0 10545 6690 8738 9321 13351 6747 6825" },
        RecordedCampaignWeapon{ 1169, "** 225 0 0" },
        RecordedCampaignWeapon{ 1170, "** 670 0 0 9930 8738 6747 10545 9321 6690 6825" },
        RecordedCampaignWeapon{ 1171, "** 180 0 0 8738 6747 9321 10545 6690 6825" },
        RecordedCampaignWeapon{ 1172, "** 652 0 0 8738" },
        RecordedCampaignWeapon{ 1173, "** 839 0 0 9930 8539 8738 6747 9321 6690 10545 6825" },
        RecordedCampaignWeapon{ 1174, "** 320 0 0 6747 8738 9321 6825" },
        RecordedCampaignWeapon{ 1175, "** 409 0 0 8738 6747 9321 10545 6690 6825" },
        RecordedCampaignWeapon{ 1176, "** 625 0 0 9930 8738 6747 9321 6690 6825" },
        RecordedCampaignWeapon{ 1177, "** 810 72 0 9930 9321 2481 10545" },
        RecordedCampaignWeapon{ 1178, "** 788 0 0 4274 6747 9321 6825" },
        RecordedCampaignWeapon{ 1179, "** 965 0 0 4274 6747 9321 6825" },
        RecordedCampaignWeapon{ 1180, "** 956 0 0 15202 9321 10545" },
        RecordedCampaignWeapon{ 1181, "** 1001 0 0 8738 6747 9321 10545 6690 6825" },
        RecordedCampaignWeapon{ 1182, "** 992 0 0 9321" },
        RecordedCampaignWeapon{ 1183, "** 981 0 0 6747 9321 10545 6825" },
        RecordedCampaignWeapon{ 1184, "** 805 0 0 9930 9321 10545" },
        RecordedCampaignWeapon{ 1185, "** 356 0 0 9930 8738 6747 9321 10545 6690 6825" },
        RecordedCampaignWeapon{ 1186, "** 1106 0 0 9321 6747 6825" },
        RecordedCampaignWeapon{ 1187, "** 571 0 0 10545 6690 8738 9321 8539 13199" },
        RecordedCampaignWeapon{ 1188, "** 639 0 0 9930 8738 6747 9321 6825" },
        RecordedCampaignWeapon{ 1189, "** 939 0 0 8738 6747 6825" },
        RecordedCampaignWeapon{ 1190, "** 633 0 0" },
        RecordedCampaignWeapon{ 1191, "** 215 0 0 8539 8738 9321 13199 10545" },
        RecordedCampaignWeapon{ 1192, "** 854 0 0 6747 9321 6825" },
        RecordedCampaignWeapon{ 1193, "** 200 0 0 8738 6747 9321 10545 6690 6825" },
        RecordedCampaignWeapon{ 1194, "** 134 0 0 9930 8738 6747 9321 10545 6690 6825" },
        RecordedCampaignWeapon{ 1195, "** 730 0 0 9930 6747 9321 6690 6825" },
        RecordedCampaignWeapon{ 1196, "** 374 0 0 10545 9321 6747 6825" },
        RecordedCampaignWeapon{ 1197, "** 992 0 0 6206 9321" },
        RecordedCampaignWeapon{ 1198, "** 78 0 0 9930 2795 2592 6747 9321 6690 8738 6825" },
        RecordedCampaignWeapon{ 1199, "** 583 0 0 9930 14255 3282 10545 8738 9321 6747" },
        RecordedCampaignWeapon{ 1200, "** 939 0 0 5188 15612 7978 8738 6825" },
        RecordedCampaignWeapon{ 1201, "** 1106 0 0 6945 9321 6747 6825" },
        RecordedCampaignWeapon{ 1202, "** 730 0 0 9930 4945 6747 9321 6690 6825" },
        RecordedCampaignWeapon{ 1203, "** 1155 0 0" },
        RecordedCampaignWeapon{ 1204, "** 348 11 0 9840 10975 1691 6747 9321 6825" },
        RecordedCampaignWeapon{ 1205, "** 538 0 0 9930 8738 6747 6690 6825" },
        RecordedCampaignWeapon{ 1206, "** 22 0 0 1178 10545 6690 8738 9321 6747" },
        RecordedCampaignWeapon{ 1207, "** 78 0 0 9930 25 6747 9321 6690 8738" },
        RecordedCampaignWeapon{ 1208, "** 41 0 0 9930 1676 6690 8738 6747 9321 10545" },
        RecordedCampaignWeapon{ 1209, "** 41 0 0 9930 9416 6690 8738 6747 9321 10545" },
        RecordedCampaignWeapon{ 1210, "** 41 0 0 9930 6690 8738 6747 9321 10545 6825" },
        RecordedCampaignWeapon{ 1211, "** 41 0 0 9930 4170 6690 8738 6747 9321 10545" },
        RecordedCampaignWeapon{ 1212, "** 22 0 0 15297 652 5414 6690 8738 9321 6747" },
        RecordedCampaignWeapon{ 1213, "** 1029 0 0 10545 6690 8738 9321 6747 6825" },
    };

    enum class WeaponConfigRegistrationFailure
    {
        None,
        Dependency,
        Weapon,
    };

    WeaponConfigRegistrationFailure registerWeaponConfigString(
        CodolGameServer::SvGameState &gameState,
        CodolGameServer::ClientWeaponSelection &weapon,
        const std::uint16_t firstDynamicWeaponAssetIndex)
    {
        std::vector<std::uint16_t> attachmentAssetIndexes;
        attachmentAssetIndexes.reserve(weapon.attachmentCount);
        for (std::size_t index = 0; index < weapon.attachmentCount; ++index)
        {
            attachmentAssetIndexes.push_back(static_cast<std::uint16_t>(
                weapon.attachmentAssetIndexes[index]));
        }
        const auto originalWeaponAssetIndex = weapon.weaponAssetIndex;
        for (const auto &dependency : weapon.modularDependencies)
        {
            if (!CodolGameServer::SV_RegisterModularWeaponConfigString(
                    gameState, firstDynamicWeaponAssetIndex, dependency))
            {
                return WeaponConfigRegistrationFailure::Dependency;
            }
        }
        const auto registeredWeaponAssetIndex =
            CodolGameServer::SV_RegisterModularWeaponConfigString(
            gameState,
            firstDynamicWeaponAssetIndex,
            {
                .baseWeaponAssetIndex = static_cast<std::uint16_t>(
                    weapon.baseWeaponAssetIndex),
                .value8 = static_cast<std::uint8_t>(weapon.modularValue8),
                .optionalValue9 = static_cast<std::uint16_t>(
                    weapon.modularValue9),
                .attachmentAssetIndexes = std::move(attachmentAssetIndexes),
            });
        if (!registeredWeaponAssetIndex)
            return WeaponConfigRegistrationFailure::Weapon;

        weapon.weaponAssetIndex = *registeredWeaponAssetIndex;
        if (weapon.clipIndex == static_cast<std::int32_t>(originalWeaponAssetIndex))
            weapon.clipIndex = *registeredWeaponAssetIndex;
        return WeaponConfigRegistrationFailure::None;
    }

    // THE LIVE REFRESH (§157c). The same registration as above, but against the
    // RUNNING gamestate and broadcasting each newly added config string to every
    // client with the '%' command -- no world rebuild.
    std::vector<std::uint8_t> buildWeaponConfigStringUpdatePayload(
        const std::uint16_t weaponAssetIndex,
        const CodolGameServer::SvModularWeaponConfigString &configString)
    {
        std::array<std::uint8_t, 4096> buffer{};
        CodolGameServer::EngineMsgWriter message(Bindings, buffer);
        CodolGameServer::SV_WriteWeaponConfigStringUpdateCommand(
            message, weaponAssetIndex, configString);
        if (message.overflowed())
            return {};
        const auto data = message.data();
        return { data.begin(), data.end() };
    }

    bool liveRegisterWeaponConfigString(
        CodolGameServer::ClientWeaponSelection &weapon,
        const std::uint16_t firstDynamicWeaponAssetIndex)
    {
        for (const auto &dependency : weapon.modularDependencies)
        {
            if (!Server.registerDynamicWeaponConfigString(
                    dependency, firstDynamicWeaponAssetIndex,
                    buildWeaponConfigStringUpdatePayload))
            {
                return false;
            }
        }
        std::vector<std::uint16_t> attachmentAssetIndexes;
        attachmentAssetIndexes.reserve(weapon.attachmentCount);
        for (std::size_t index = 0; index < weapon.attachmentCount; ++index)
        {
            attachmentAssetIndexes.push_back(static_cast<std::uint16_t>(
                weapon.attachmentAssetIndexes[index]));
        }
        const auto originalWeaponAssetIndex = weapon.weaponAssetIndex;
        const auto registered = Server.registerDynamicWeaponConfigString(
            {
                .baseWeaponAssetIndex = static_cast<std::uint16_t>(
                    weapon.baseWeaponAssetIndex),
                .value8 = static_cast<std::uint8_t>(weapon.modularValue8),
                .optionalValue9 = static_cast<std::uint16_t>(
                    weapon.modularValue9),
                .attachmentAssetIndexes = std::move(attachmentAssetIndexes),
            },
            firstDynamicWeaponAssetIndex,
            buildWeaponConfigStringUpdatePayload);
        if (!registered)
            return false;
        weapon.weaponAssetIndex = *registered;
        if (weapon.clipIndex ==
            static_cast<std::int32_t>(originalWeaponAssetIndex))
        {
            weapon.clipIndex = *registered;
        }
        return true;
    }

    // Refresh ONE roster member's weapons in place. Weapons-only for now: the
    // member's character is preserved (a live character-model swap is a separate
    // follow-up). §160: the new weapons are APPENDED to the live gamestate's
    // dynamic block (no '%' broadcast -- that trips the client's 181 weapon-index
    // check, [[codol-181-is-weapon-index-vs-slot]]); the member reaches them by
    // BACKING OUT AND REJOINING, which re-parses the whole gamestate and
    // registers the weapons at their correct dense slots. Run --update-loadout
    // while the player is at the menu; their rejoin spawns the new guns, no world
    // rebuild and no disturbance to the other players.
    bool refreshMemberLoadout(
        const std::uint64_t userId,
        const OlMod::DedicatedSession::LoadoutRequest &request)
    {
        const auto firstDynamicWeaponAssetIndex =
            Bindings.firstDynamicWeaponAssetIndex();
        if (!firstDynamicWeaponAssetIndex)
            return false;

        CodolGameServer::RegisteredSessionAssets member;
        {
            const std::lock_guard lock(LoadoutMutex);
            const auto *const presentation =
                RegisteredSessionAssets.character(userId);
            if (!presentation)
                return false;
            member.characterPresentation = *presentation;
        }

        member.rewards = Bindings.resolveSessionRewards(request);
        if (!member.rewards)
            logGameServer("reward refresh unavailable xuid=" + std::to_string(userId));
        for (std::uint32_t classIndex = 0;
             classIndex < request.classes.size(); ++classIndex)
        {
            if (!(request.classMask & (1u << classIndex)))
                continue;
            const auto perks = Bindings.resolveSessionPerks(request, classIndex);
            const auto offhands = Bindings.resolveSessionEquipment(request, classIndex);
            if (!perks || !offhands)
                return false;
            auto primary = Bindings.resolveWeaponSelection(
                request.classes[classIndex].weapons[0]);
            auto secondary = Bindings.resolveWeaponSelection(
                request.classes[classIndex].weapons[1]);
            if (!primary || !secondary)
                return false;
            // §161a: DO NOT strip attachments here. The strip existed only to keep
            // the retired '%' broadcast small; with the broadcast gone the live
            // path must resolve weapons EXACTLY as SessionStart does (it uses the
            // same resolveWeaponRequest), so the appended dynamic-weapon block is
            // byte-identical to the one a SessionStart would build -- same
            // attachments, same nested modularDependencies published in order.
            // Stripping made them DIFFERENT: the stripped weapons never dedup
            // against SessionStart's attachment'd ones and the dropped
            // dependencies shift the client's registration counter, so on a
            // reconnect re-parse a weapon landed at slot+1 and Com_Error(181)'d
            // (measured 2026-08-26: `181 ** 646 0 0 1243 1242`). Identical to
            // SessionStart is the invariant; SessionStart is proven to spawn.
            CodolGameServer::ClientWeaponLoadout loadout{
                .characterIndex = request.characterIndex,
                .classIndex = classIndex,
                .primary = *primary,
                .secondary = *secondary,
            };
            if (!liveRegisterWeaponConfigString(
                    loadout.primary, *firstDynamicWeaponAssetIndex) ||
                !liveRegisterWeaponConfigString(
                    loadout.secondary, *firstDynamicWeaponAssetIndex))
            {
                return false;
            }
            member.loadouts.emplace(
                "custom" + std::to_string(classIndex + 1),
                toResolvedLoadout(loadout));
            member.perks.emplace("custom" + std::to_string(classIndex + 1), *perks);
            member.equipment.emplace("custom" + std::to_string(classIndex + 1),
                request.classes[classIndex].equipment);
            member.offhands.emplace("custom" + std::to_string(classIndex + 1), *offhands);
        }
        if (member.loadouts.empty())
            return false;

        const std::lock_guard lock(LoadoutMutex);
        return RegisteredSessionAssets.updateMember(userId, std::move(member));
    }

    bool prepareClientLoadouts()
    {
        std::uint64_t requestSequence{};
        {
            const std::lock_guard lock(LoadoutMutex);
            requestSequence = LoadoutPrepareRequestSequence;
        }
        const auto characterIndex = Bindings.currentCharacterIndex();
        const auto characterPresentation = characterIndex
            ? Bindings.resolveClientCharacterPresentation(*characterIndex)
            : std::nullopt;
        PreparedClientLoadouts prepared;
        PreparedSessionMember preparedMember;
        std::uint32_t resolvedClassMask{};
        std::uint32_t registeredClassMask{};
        if (characterIndex)
        {
            prepared.requestSequence = requestSequence;
            preparedMember.characterIndex = *characterIndex;
            if (characterPresentation)
                preparedMember.characterPresentation = *characterPresentation;
        }
        for (std::uint32_t index = 0; index < 5; ++index)
        {
            if (!characterIndex || !characterPresentation)
                break;
            const auto selectedLoadout = "custom" + std::to_string(index + 1);
            const auto loadout = Bindings.resolveClientWeaponLoadout(
                selectedLoadout, *characterIndex);
            if (!loadout)
                continue;
            resolvedClassMask |= 1u << index;
            registeredClassMask |= 1u << index;
            preparedMember.loadouts.emplace(selectedLoadout, *loadout);
        }
        if (characterPresentation && !preparedMember.loadouts.empty())
            prepared.members.push_back(std::move(preparedMember));
        const auto finalCharacterIndex = Bindings.currentCharacterIndex();
        const auto succeeded = characterPresentation && !prepared.members.empty() &&
            finalCharacterIndex == characterIndex;
        const std::lock_guard lock(LoadoutMutex);
        ++LoadoutPreparation.attemptCount;
        LoadoutPreparation.currentCharacter = finalCharacterIndex
            ? static_cast<std::int32_t>(*finalCharacterIndex)
            : -1;
        LoadoutPreparation.resolvedClassMask = resolvedClassMask;
        LoadoutPreparation.registeredClassMask = registeredClassMask;
        if (requestSequence != LoadoutPrepareRequestSequence)
            return false;
        if (succeeded)
        {
            PreparedLoadouts = std::move(prepared);
        }
        else if (finalCharacterIndex && PreparedLoadouts &&
            (PreparedLoadouts->members.empty() ||
                PreparedLoadouts->members.front().characterIndex !=
                    *finalCharacterIndex))
        {
            PreparedLoadouts.reset();
        }
        return succeeded;
    }

    bool configureGameStateImpl(
        const std::string_view mapName,
        const std::string_view bookingGameType,
        const std::uint32_t configStringChecksum,
        const std::uint32_t checksumFeed = 0)
    {
        // Every caller reaches here holding the token the client BOOKED. This is
        // the one place it becomes the gametype the server runs, so nothing
        // downstream - serverinfo, the spawn class lookup, the per-gametype gates
        // - has to know both vocabularies.
        const auto gameType =
            CodolGameServer::SV_EngineGameType(bookingGameType);
        GameStateConfiguration.processing();
        logGameServer(
            "configureGameState entry map=" + std::string(mapName) +
            " booked=" + std::string(bookingGameType) +
            " engine=" + std::string(gameType) +
            " checksum=" + std::to_string(configStringChecksum));
        if (!configStringChecksum)
        {
            GameStateConfiguration.failed(
                CodolGameServer::GameStateConfigurationStage::InvalidChecksum);
            return false;
        }
        std::optional<std::uint32_t> currentCharacter;
        if (OlMod::processRole() == OlMod::ProcessRole::Dedicated)
        {
            const std::lock_guard lock(LoadoutMutex);
            if (PreparedLoadouts && !PreparedLoadouts->members.empty())
                currentCharacter =
                    PreparedLoadouts->members.front().characterIndex;
        }
        else
        {
            currentCharacter = Bindings.currentCharacterIndex();
        }
        if (!currentCharacter)
        {
            GameStateConfiguration.failed(
                CodolGameServer::GameStateConfigurationStage::CharacterUnavailable);
            return false;
        }
        CodolGameServer::SvGameState gameState{
            .mapName = std::string(mapName),
            .gameType = std::string(gameType),
            .configStringChecksum = configStringChecksum,
            .checksumFeed = checksumFeed,
        };
        CodolGameServer::SV_PopulateRequiredConfigStrings(gameState);
        // BATTLE ROYALE'S LOOT BAND, INTO THE GAMESTATE ITSELF.
        //
        // THE MODE'S SERVER LOGIC WAS STRIPPED WHEN THE GAME SHUT DOWN; THE CLIENT IS
        // INTACT. This is a reimplementation against a client that still knows what it
        // wants, and the retail demos are the specification.
        //
        // MEASURED 2026-09-04 by diffing `@gamestate` configstrings of two captures in
        // Essential/demos:
        //
        //     cs 12500-13000   retail dm = 0 entries      retail dmz = 65 entries
        //     cs 12504         "mp/dmzloot.csv"           the loot table asset
        //     cs 12506..12692  64 entries, values 1148..1211
        //
        // Nothing in this server ever wrote above 12246, so a dmz client was handed a
        // battle royale with no loot table and no lootable weapons.
        //
        // IT GOES IN HERE AND NOT THROUGH SV_SetConfigString, WHICH CANNOT CARRY IT.
        // That setter opens with `if (!gameStateConfigured_) return 0;`, so it is a
        // silent no-op before the gamestate exists -- and once it exists the setter only
        // emits a live `d` command, reaching a client that has already parsed its
        // gamestate. Both were tried on 2026-09-04 and neither put a byte in the
        // gamestate: the late one logged `clients=1` and changed nothing, the early one
        // logged `clients=0 + 0/64 slots` and stored nothing. This map IS the
        // gamestate's, so an entry here is simply part of it.
        //
        // THE LAYOUT IS PER MATCH, NOT FIXED. C-2021-7-25[22-0-7]dmz and
        // C-2021-7-25[22-23-22]dmz both carry 65 entries over the same range, but 28 of
        // the 64 indices differ and the values reorder -- retail randomises loot
        // placement every game. This replays ONE real layout verbatim rather than
        // inventing one; a generator needs the slot semantics out of mp/dmzloot.csv.
        //
        // Values are ABSOLUTE weapon indices, left as captured: this build reports
        // firstDynamicWeapon=1147 on mp_battlecity and the captured values start at
        // 1148, so the two agree without rebasing.
        // THE LOOT BAND IS NOW A SUSPECT, SO IT HAS A SWITCH.
        //
        // The client kicks with XBOXLIVE_CANTJOINSESSION from sub_514540, and that
        // function is a CONFIGSTRING VALIDATOR: it takes an index in [0, 0x31D9), reads a
        // per-configstring type byte at `0x77D8250 + index`, and if the byte is neither
        // 0x15 nor >= 0x17 it calls the CCS clear and raises ERR_SERVERDISCONNECT.
        //
        // We publish cs 12504..12692 for dmz, inside that range, and the client has NEVER
        // been tested entering a match without them -- the band was added before the
        // snapshot entry flag that first let it in at all. If those indices carry a type
        // the client does not accept, this is exactly the failure we see.
        //
        // OLMOD_DMZ_LOOT_BAND=0 removes them for a run. Default stays on: retail sends
        // them, and dmz cannot work without loot eventually.
        static const bool lootBandEnabled = [] {
            const char *const value = std::getenv("OLMOD_DMZ_LOOT_BAND");
            return !(value && value[0] == '0');
        }();
        if (gameType == "dmz" && lootBandEnabled)
        {
            struct LootSlot
            {
                std::uint16_t index;
                std::uint16_t weapon;
            };
            static constexpr std::array<LootSlot, 64> LootBand{ {
            { 12506, 1149 }, { 12507, 1150 }, { 12508, 1151 }, { 12509, 1152 },
            { 12510, 1153 }, { 12511, 1154 }, { 12512, 1155 }, { 12513, 1156 },
            { 12516, 1157 }, { 12517, 1158 }, { 12520, 1159 }, { 12521, 1160 },
            { 12528, 1161 }, { 12529, 1162 }, { 12530, 1163 }, { 12537, 1164 },
            { 12538, 1165 }, { 12539, 1166 }, { 12540, 1167 }, { 12541, 1168 },
            { 12542, 1169 }, { 12546, 1170 }, { 12547, 1171 }, { 12548, 1172 },
            { 12549, 1173 }, { 12550, 1174 }, { 12551, 1175 }, { 12555, 1176 },
            { 12556, 1177 }, { 12557, 1178 }, { 12558, 1179 }, { 12559, 1180 },
            { 12560, 1181 }, { 12564, 1182 }, { 12565, 1183 }, { 12568, 1184 },
            { 12569, 1185 }, { 12570, 1189 }, { 12571, 1190 }, { 12576, 1191 },
            { 12577, 1192 }, { 12584, 1193 }, { 12585, 1194 }, { 12592, 1186 },
            { 12593, 1187 }, { 12602, 1195 }, { 12603, 1196 }, { 12610, 1197 },
            { 12611, 1198 }, { 12614, 1199 }, { 12615, 1200 }, { 12616, 1148 },
            { 12617, 1201 }, { 12618, 1202 }, { 12619, 1203 }, { 12620, 1204 },
            { 12623, 1205 }, { 12625, 1206 }, { 12628, 1207 }, { 12629, 1208 },
            { 12631, 1209 }, { 12632, 1210 }, { 12634, 1211 }, { 12692, 1188 }
            } };
            gameState.configStrings.emplace(12504, "mp/dmzloot.csv");
            for (const auto &slot : LootBand)
            {
                gameState.configStrings.emplace(
                    slot.index, std::to_string(slot.weapon));
            }
            logGameServer(
                "dmz loot band INTO GAMESTATE cs 12504=mp/dmzloot.csv + " +
                std::to_string(LootBand.size()) + " slots (" +
                std::to_string(LootBand.front().index) + ".." +
                std::to_string(LootBand.back().index) + "), weapons " +
                std::to_string(LootBand.front().weapon) + ".." +
                std::to_string(LootBand.back().weapon));
        }
        gameState.configStrings.emplace(
            CodolGameServer::TimescaleConfigStringIndex, "0 0 1 1");
        // The client already carries this material: sub_BB5680 resolves an
        // icon elem through configstring materialIndex+4355, and a read-only
        // walk of that configstring range in a live client finds
        // "damage_feedback" there, next to damage_feedback_endgame,
        // damage_feedback_j and kill_feedback. Nothing needs precaching; this
        // only asks the engine for the index it already has.
        gameState.damageFeedbackMaterial =
            Bindings.resolveServerMaterialConfigStringIndex("damage_feedback");
        if (gameState.gameType == "zm") {
            gameState.factoryAmmoMaterials = {
                Bindings.resolveServerMaterialConfigStringIndex("progress_bar_fill").value_or(0),
                Bindings.resolveServerMaterialConfigStringIndex("progress_bar_bg").value_or(0)};
            // Original Factory's no-pistol down grants a modular M9 (base646).
            // Resolve the resident base by name; never reuse a recording's forged index.
            gameState.zombieFallbackPistol=Bindings.resolveBaseWeaponAssetIndex("m9_mp").value_or(0);
            gameState.zombieReviveMaterials = {
                Bindings.resolveServerMaterialConfigStringIndex("waypoint_last_stand_localized").value_or(0),
                Bindings.resolveServerMaterialConfigStringIndex("waypoint_revive_new").value_or(0)};
            if (gameState.mapName=="zm_factory_sh") {
                const auto *option=std::getenv("OLMOD_FACTORY_TELEPORTERS");
                const std::array<std::string,3> names{
                    "zombie_stopwatchneedle","zombie_stopwatch","zombie_stopwatch_glass"};
                if (option && std::string_view(option)=="1" &&
                    std::ranges::all_of(names,[](const auto &name) {
                        return Bindings.findXAsset(5,name.c_str(),false).data!=nullptr;
                    })) {
                    if (const auto first=Bindings.firstDynamicServerMaterialIndex()) {
                        std::map<std::uint16_t,std::string> occupied;
                        bool complete=true;
                        for (std::uint16_t i=*first;i<CodolGameServer::ServerMaterialConfigStringCount;++i) {
                            const auto value=Bindings.readConfigString(
                                CodolGameServer::ServerMaterialConfigStringBase+i,64);
                            if (!value) {complete=false;break;}
                            if (!value->empty()) occupied.emplace(i,*value);
                        }
                        if (complete) {
                            const auto indices=CodolGameServer::SV_RegisterDynamicServerMaterials(
                                gameState,*first,names,occupied);
                            if (indices) gameState.factoryClockMaterials={(*indices)[1],(*indices)[2]};
                        }
                        logGameServer("Factory clock registration boundary="+std::to_string(*first)+
                            " face="+std::to_string(gameState.factoryClockMaterials[0])+
                            " glass="+std::to_string(gameState.factoryClockMaterials[1]));
                    }
                }
                if (!gameState.factoryClockMaterials[0])
                    logGameServer("Factory clock unavailable: missing artwork, dynamic boundary or namespace");
            }
        }
        gameState.killFeedbackMaterial =
            Bindings.resolveServerMaterialConfigStringIndex("kill_feedback");
        gameState.scavengerBagWeaponAssetIndex =
            Bindings.resolveBaseWeaponAssetIndex("scavenger_bag_mp");
        // resolveSoundAliasEventParameters answers from the client's own DB and
        // soundalias configstrings, and its configstring comparison is exact,
        // so ask it for both spellings rather than assuming CODOL kept IW4's
        // capitalisation. An unknown alias simply returns nothing.
        {
            const std::vector<std::string> hitAliases{
                "MP_hit_alert", "mp_hit_alert",
            };
            const auto hitParameters =
                Bindings.resolveSoundAliasEventParameters(hitAliases);
            for (std::size_t index{}; index < hitParameters.size(); ++index)
            {
                if (!hitParameters[index] || !*hitParameters[index])
                    continue;
                gameState.damageFeedbackSound = hitParameters[index];
                logGameServer(
                    "damage feedback sound alias=" + hitAliases[index] +
                    " eventParameter=" +
                    std::to_string(*hitParameters[index]));
                break;
            }

            // THE KILL SOUND. `mp_hit_alert` above was already the right guess
            // and the demo now CONFIRMS it: naming every `p <n>` a retail dm
            // server sent, through configstring 3624+n, gives
            //
            //     p 11  x84  mp_hit_alert     the hit marker's sound
            //     p 15  x28  mp_hit_kill      the kill's
            //     p 29  x4   mp_headshot
            //
            // Resolved by NAME for the same reason the hit alias is: the alias
            // INDEX is handed out per match as sounds are first needed, so 15
            // is only `mp_hit_kill` in the match that assigned it that way.
            // The name is the portable half, and this is what
            // resolveSoundAliasEventParameters takes.
            const std::vector<std::string> killAliases{
                "MP_hit_kill", "mp_hit_kill",
            };
            const auto killParameters =
                Bindings.resolveSoundAliasEventParameters(killAliases);
            for (std::size_t index{}; index < killParameters.size(); ++index)
            {
                if (!killParameters[index] || !*killParameters[index])
                    continue;
                gameState.killFeedbackSound = killParameters[index];
                logGameServer(
                    "kill feedback sound alias=" + killAliases[index] +
                    " eventParameter=" +
                    std::to_string(*killParameters[index]));
                break;
            }
            if (!gameState.killFeedbackSound)
            {
                logGameServer(
                    "kill feedback sound UNRESOLVED - neither MP_hit_kill nor "
                    "mp_hit_kill is in this client's soundalias configstrings");
            }

            const std::vector<std::string> scavengerAliases{
                "scavenger_pack_pickup",
            };
            const auto scavengerParameters =
                Bindings.resolveSoundAliasEventParameters(scavengerAliases);
            if (!scavengerParameters.empty() && scavengerParameters.front() &&
                *scavengerParameters.front())
            {
                gameState.scavengerPickupSound = scavengerParameters.front();
                logGameServer(
                    "scavenger pickup sound eventParameter=" +
                    std::to_string(*scavengerParameters.front()));
            }

            // OLMOD(splash-sound): the medal banner's own audio does not exist
            // on this build. sub_C1C860 plays column 9 of mp/splashTable.csv
            // (VA 0x0057C9D8), skipping an empty cell or the literal "null",
            // and 3.3.3.3's table backreferences column 9 on every medal row,
            // so a retail client is silent for them too. Ask for a reward-ish
            // alias the same way, by NAME and in priority order, and let
            // resolveSoundAliasEventParameters answer from the client's own DB
            // and configstrings. Both are aliases this build's own splash table
            // uses inline - row 1 mp_challenge_complete and row 0 mp_level_up -
            // so they are known to exist here rather than guessed. An unknown
            // alias simply returns nothing and the banner stays silent.
            // These are read off THIS build, live: the CCS constant-string
            // table was dumped from a running client (type 5 = the sound alias
            // pool, 1507 entries) and only 68 of them are not announcer
            // voice-over - the rest carry ab_/uk_/za_/rb_ language prefixes.
            // mp_challenge_complete and mp_level_up are NOT among them; the
            // splash table references them but this map does not load them,
            // which is the same reason mp_hit_alert never resolved either.
            // mp_bonus_start, mp_ingame_summary and mp_capture_flag ARE loaded
            // and are the closest thing this build has to a reward stinger -
            // retail's own splash table uses mp_bonus_start on row 79.
// RESULT, 2026-08-17: all 75 were auditioned live, one per hit, and NONE of
            // them is a medal sound. That is the honest answer rather than a
            // near-miss: this build's networked constant-string table simply has
            // no reward cue in it. The real ones exist as ASSETS in
            // common_mp.ff - mp_challenge_complete, mp_level_up, and the
            // ui_reward_bronze/silver/gold/rare family whose audio is
            // main\sound\mp\ui_medal_reward_get.mp3 - but none of them is in
            // the networked table, so no server can reference one. Retail is
            // silent here for the same reason (2d-quindecies: every medal row's
            // column 9 is a backreference).
            //
            // Left empty deliberately. Shipping a wrong sound is worse than
            // none; the resolution path below still works, so a single name
            // here is all it takes if a suitable alias is ever found or added.
            const std::vector<std::string> splashAliases{};
            const auto splashParameters =
                Bindings.resolveSoundAliasEventParameters(splashAliases);
            for (std::size_t index{}; index < splashParameters.size(); ++index)
            {
                if (!splashParameters[index] || !*splashParameters[index])
                    continue;
                gameState.splashSound = splashParameters[index];
                logGameServer(
                    "splash sound alias=" + splashAliases[index] +
                    " eventParameter=" +
                    std::to_string(*splashParameters[index]));
                break;
            }
            if (!gameState.splashSound)
            {
                logGameServer("splash sound unresolved; medals stay silent");
                // TODO(CODOL): no alias has ever resolved, hit alert included.
                // Report what the two index sources hold instead of guessing
                // more names. Remove once a sound alias resolves.
                Bindings.logServerSoundAliasTables(40);
            }
        }
        logGameServer(
            "damage feedback material=" +
            (gameState.damageFeedbackMaterial
                    ? std::to_string(*gameState.damageFeedbackMaterial)
                    : std::string("unavailable")) +
            " killMaterial=" +
            (gameState.killFeedbackMaterial
                    ? std::to_string(*gameState.killFeedbackMaterial)
                    : std::string("unavailable")) +
            " sound=" +
            (gameState.damageFeedbackSound
                    ? std::to_string(*gameState.damageFeedbackSound)
                    : std::string("unavailable")));
        if (gameType == "sd")
        {
            const auto targetA = Bindings.resolveServerMaterialConfigStringIndex(
                "waypoint_target_a");
            const auto targetB = Bindings.resolveServerMaterialConfigStringIndex(
                "waypoint_target_b");
            const auto defendA = Bindings.resolveServerMaterialConfigStringIndex(
                "waypoint_defend_a");
            const auto defendB = Bindings.resolveServerMaterialConfigStringIndex(
                "waypoint_defend_b");
            const auto defuseA = Bindings.resolveServerMaterialConfigStringIndex(
                "waypoint_defuse_a");
            const auto defuseB = Bindings.resolveServerMaterialConfigStringIndex(
                "waypoint_defuse_b");
            const auto bomb = Bindings.resolveServerMaterialConfigStringIndex(
                "waypoint_bomb");
            const auto escort = Bindings.resolveServerMaterialConfigStringIndex(
                "waypoint_escort");
            if (!targetA || !targetB || !defendA || !defendB ||
                !defuseA || !defuseB || !bomb || !escort)
            {
                GameStateConfiguration.failed(
                    CodolGameServer::GameStateConfigurationStage::
                        ObjectiveMaterialUnavailable);
                return false;
            }
            gameState.sdObjectiveMaterials = CodolGameServer::SvSdObjectiveMaterials{
                .targetA = *targetA,
                .targetB = *targetB,
                .defendA = *defendA,
                .defendB = *defendB,
                .defuseA = *defuseA,
                .defuseB = *defuseB,
                .bomb = *bomb,
                .escort = *escort,
            };
        }
        std::optional<std::vector<CodolGameServer::SvMapEntity>> mapEntities;
        const auto scriptRoot = gameplayScriptRoot();
        const auto mapScriptPath = scriptRoot / L"maps" /
            (std::string(mapName) + ".lua");
        std::error_code mapScriptError;
        const auto mapScriptExists = std::filesystem::exists(
            mapScriptPath, mapScriptError);
        const auto mapMetadata = CodolGameServer::SV_LoadMapScriptMetadata(
            scriptRoot, mapName);
        if (mapScriptError || mapScriptExists != mapMetadata.has_value())
        {
            GameStateConfiguration.failed(
                CodolGameServer::GameStateConfigurationStage::
                    MiniMapUnavailable);
            return false;
        }
        // MAP ENTITIES ARE READ FOR EVERY MAP THAT HAS A SCRIPT, not only those that
        // carry a minimap. Spawn points come from this entity string and from nothing
        // else, so gating it on miniMapMaterial silently made "this map has no compass"
        // mean "this map has no spawns": configureWorldSpawn then failed on
        // `initial_spawn_ground_trace`, and a client that got that far sat forever at
        // NO_SPAWN_POINT with the map loaded around it.
        //
        // A compass and a spawn list are unrelated, and the coupling was an MP-only
        // assumption. Zombies has no compass to name: none of the three retail
        // zm_factory_sh demos emits a compass configstring while the retail dm gamestate
        // does, and out.exe's only compass_map_* string is compass_map_awareness_radar
        // @ 0xDB1D0C -- the per-map materials live in fastfiles and no zombies one
        // exists. Those maps still need their spawns.
        //
        // MP maps are unaffected: mp_nuked and mp_crash_tropical both set
        // miniMapMaterial, so both blocks below run for them exactly as before.
        if (mapMetadata)
        {
            const auto entityText = Bindings.readMapEntityString(mapName);
            mapEntities = entityText
                ? CodolGameServer::SV_ParseMapEntities(*entityText)
                : std::nullopt;
            if (mapEntities)
            {
                // Which spawn classes a CODOL map actually carries cannot be read
                // offline - the base MP entity strings are in none of the 244
                // shipped fastfiles, only coop/asym addons are - so report it
                // from the live load rather than leaving the names assumed.
                std::string census;
                for (const auto &[className, count] :
                     CodolGameServer::SV_SpawnClassNameCensus(*mapEntities))
                {
                    if (!census.empty())
                        census += ", ";
                    census += className + " x" + std::to_string(count);
                }
                logGameServer(
                    "map spawn classes " + std::string(mapName) + " " +
                    std::string(gameType) + ": " +
                    (census.empty() ? "(none)" : census));
            }
        }
        if (mapMetadata && mapMetadata->miniMapMaterial)
        {
            const auto nativeNorthYaw = Bindings.readConfigString(
                CodolGameServer::NorthYawConfigStringIndex, 64);
            const auto northYaw = nativeNorthYaw
                ? (nativeNorthYaw->empty()
                    ? std::optional{ 0.0f }
                    : parseFiniteFloat(*nativeNorthYaw))
                : std::nullopt;
            const auto corners = mapEntities && northYaw
                ? CodolGameServer::SV_SelectMiniMapCorners(
                    *mapEntities, *northYaw)
                : std::nullopt;
            if (!corners || !CodolGameServer::SV_SetMiniMapConfigStrings(
                    gameState,
                    *northYaw,
                    {
                        .material = *mapMetadata->miniMapMaterial,
                        .upperLeft = corners->northWest,
                        .lowerRight = corners->southEast,
                    }))
            {
                GameStateConfiguration.failed(
                    CodolGameServer::GameStateConfigurationStage::
                        MiniMapUnavailable);
                return false;
            }
        }
        PreparedClientLoadouts prepared;
        {
            const std::lock_guard lock(LoadoutMutex);
            if (!PreparedLoadouts ||
                PreparedLoadouts->requestSequence !=
                    LoadoutPrepareRequestSequence ||
                PreparedLoadouts->members.empty() ||
                PreparedLoadouts->members.front().characterIndex !=
                    *currentCharacter)
            {
                GameStateConfiguration.failed(
                    CodolGameServer::GameStateConfigurationStage::
                        PreparedLoadoutMismatch);
                return false;
            }
            prepared = *PreparedLoadouts;
        }
        const auto sessionGeneration = prepared.sessionGeneration;
        if (sessionGeneration)
        {
            std::vector<std::pair<std::uint64_t, std::string>> identities;
            identities.reserve(prepared.members.size());
            std::ranges::transform(
                prepared.members,
                std::back_inserter(identities),
                [](const auto &member) {
                    return std::pair{ member.xuid, member.username };
                });
            std::ranges::sort(identities, {}, [](const auto &identity) {
                return identity.first;
            });
            gameState.playerNames.reserve(identities.size());
            std::ranges::transform(
                identities,
                std::back_inserter(gameState.playerNames),
                [](const auto &identity) { return identity.second; });
            CodolGameServer::SV_PopulateRequiredConfigStrings(gameState);
        }
        const auto firstDynamicWeaponAssetIndex =
            Bindings.firstDynamicWeaponAssetIndex();
        if (!firstDynamicWeaponAssetIndex)
        {
            GameStateConfiguration.failed(
                CodolGameServer::GameStateConfigurationStage::
                    DynamicWeaponRangeUnavailable);
            return false;
        }
        GameStateConfiguration.dynamicWeaponRange(
            *firstDynamicWeaponAssetIndex);

        if (mapName == "coop_training_mp_cargoship" && gameType == "coop")
        {
            std::string mapping;
            for (const auto &weapon : RecordedWetworkWeapons)
            {
                const auto registered =
                    Bindings.registerModularWeaponConfigString(
                        weapon.definition);
                if (!registered)
                {
                    logGameServer(
                        "Wetwork weapon registration failed retail=" +
                        std::to_string(weapon.recordedIndex) +
                        " definition=\"" + std::string(weapon.definition) +
                        "\"");
                    GameStateConfiguration.failed(
                        CodolGameServer::GameStateConfigurationStage::
                            DynamicWeaponRegistryRegistrationFailed);
                    return false;
                }
                mapping += (mapping.empty() ? "" : ", ") +
                    std::to_string(weapon.recordedIndex) + "->" +
                    std::to_string(*registered);
            }
            logGameServer("Wetwork weapon map " + mapping);
        }

        const auto nativeDynamicWeaponConfigStrings =
            Bindings.readDynamicWeaponConfigStrings(
                *firstDynamicWeaponAssetIndex);
        if (!nativeDynamicWeaponConfigStrings)
        {
            // The outgoing indexes must be the indexes in the native registry:
            // pmove uses those same values after the client spawns. Inventing a
            // dense outgoing tail here can make a client display Barrett while
            // the server executes a different WeaponDef (observed as the fully
            // functional knife fallback). Wait for a coherent native tail.
            GameStateConfiguration.failed(
                CodolGameServer::GameStateConfigurationStage::
                    DynamicWeaponRegistryUnavailable);
            return false;
        }
        for (std::size_t offset = 0;
             offset < nativeDynamicWeaponConfigStrings->size();
             ++offset)
        {
            const auto registered =
                CodolGameServer::SV_RegisterModularWeaponConfigString(
                    gameState,
                    *firstDynamicWeaponAssetIndex,
                    (*nativeDynamicWeaponConfigStrings)[offset]);
            const auto expected = static_cast<std::uint32_t>(
                *firstDynamicWeaponAssetIndex) + offset;
            if (!registered || *registered != expected)
            {
                GameStateConfiguration.failed(
                    CodolGameServer::GameStateConfigurationStage::
                        DynamicWeaponRegistryRegistrationFailed);
                return false;
            }
        }

        // SEED RETAIL'S WEAPON SET (12.127). Measured, not invented: these are the
        // 34 modular weapon config strings a retail zm server published, read
        // verbatim out of C-2021-7-31[15-32-16]zm's own gamestate at config string
        // indices 7119-7152, i.e. weapon asset indices 1159-1192.
        //
        // WHY A WEAPON CHANGE IS AN ANIMATION EXPERIMENT. 12.126 measured, on the
        // same binary minutes apart: retail loads 50 zones (~37 of them weapon
        // zones) and builds a 123-entry generic_human animtree; this server loads
        // 18 zones (3 weapon zones) and builds a 519-entry one. Everything wrong
        // with the zombies follows from that table -- 12.124/12.125 -- so the
        // question is whether the weapon zone set is what determines it.
        //
        // This is the experiment 12.92 refused to run. The user asked for it and
        // I withdrew it on the claim that loadouts come from the backend; the
        // backend supplies the LOADOUT, but the gamestate's weapon config strings
        // are this server's to publish, and they are what the client precaches
        // zones from.
        //
        // ADDITIVE AND SKIP-ON-CLASH. Anything already registered -- the dynamic
        // range above, or a member loadout -- wins; this only fills gaps, so a
        // failure to place one entry cannot break a session that worked before.
        if constexpr (CodolGameServer::SvSeedRetailWeaponSet)
        {
            static constexpr std::array<std::pair<std::uint16_t,
                std::string_view>, 34> retailWeaponConfigStrings{{
                {1159, "** 646 0 0 8738 9321"},
                {1160, "** 249 0 0"},
                {1161, "** 583 0 0 9930 10545 6690 8738 9321 6747 6825"},
                {1162, "** 604 0 0 9930 8738 6747 9321 10545 6690 6825"},
                {1163, "** 1108 0 0 9321 6747 6825"},
                {1164, "** 1038 140 0 10545 6690 8738 9321 13351 6747 6825"},
                {1165, "** 225 0 0"},
                {1166, "** 670 0 0 9930 8738 6747 10545 9321 6690 6825"},
                {1167, "** 180 0 0 8738 6747 9321 10545 6690 6825"},
                {1168, "** 652 0 0 8738"},
                {1169, "** 839 0 0 9930 8539 8738 6747 9321 6690 10545 6825"},
                {1170, "** 320 0 0 6747 8738 9321 6825"},
                {1171, "** 409 0 0 8738 6747 9321 10545 6690 6825"},
                {1172, "** 625 0 0 9930 8738 6747 9321 6690 6825"},
                {1173, "** 810 72 0 9930 9321 2481 10545"},
                {1174, "** 788 0 0 4274 6747 9321 6825"},
                {1175, "** 965 0 0 4274 6747 9321 6825"},
                {1176, "** 956 0 0 15202 9321 10545"},
                {1177, "** 1001 0 0 8738 6747 9321 10545 6690 6825"},
                {1178, "** 992 0 0 9321"},
                {1179, "** 981 0 0 6747 9321 10545 6825"},
                {1180, "** 805 0 0 9930 9321 10545"},
                {1181, "** 356 0 0 9930 8738 6747 9321 10545 6690 6825"},
                {1182, "** 1106 0 0 9321 6747 6825"},
                {1183, "** 571 0 0 10545 6690 8738 9321 8539 13199"},
                {1184, "** 639 0 0 9930 8738 6747 9321 6825"},
                {1185, "** 939 0 0 8738 6747 6825"},
                {1186, "** 633 0 0"},
                {1187, "** 215 0 0 8539 8738 9321 13199 10545"},
                {1188, "** 854 0 0 6747 9321 6825"},
                {1189, "** 200 0 0 8738 6747 9321 10545 6690 6825"},
                {1190, "** 134 0 0 9930 8738 6747 9321 10545 6690 6825"},
                {1191, "** 730 0 0 9930 6747 9321 6690 6825"},
                {1192, "** 374 0 0 10545 9321 6747 6825"},
            }};
            std::size_t seeded = 0;
            std::size_t skipped = 0;
            for (const auto &[assetIndex, value] : retailWeaponConfigStrings)
            {
                const auto parsed =
                    CodolGameServer::SV_ParseModularWeaponConfigString(value);
                if (!parsed) { ++skipped; continue; }
                if (CodolGameServer::SV_AddModularWeaponConfigString(
                        gameState, assetIndex, *parsed))
                {
                    ++seeded;
                }
                else
                {
                    ++skipped;
                }
            }
            logGameServer(
                "retail weapon set seeded=" + std::to_string(seeded) +
                " skipped=" + std::to_string(skipped) +
                " firstDynamic=" +
                std::to_string(*firstDynamicWeaponAssetIndex));
        }

        CodolGameServer::SessionAssetRegistry::Members
            registeredSessionMembers;
        for (const auto &preparedMember : prepared.members)
        {
            CodolGameServer::RegisteredSessionAssets registeredMember{
                .characterPresentation =
                    preparedMember.characterPresentation,
                .perks = preparedMember.perks,
                .equipment = preparedMember.equipment,
                .offhands = preparedMember.offhands,
                .rewards = preparedMember.rewards,
            };
            for (const auto &[name, cachedLoadout] : preparedMember.loadouts)
            {
                const auto classIndex = name.size() == 7 &&
                        name.starts_with("custom") &&
                        name.back() >= '1' && name.back() <= '5'
                    ? static_cast<std::int32_t>(name.back() - '1')
                    : -1;
                auto registeredLoadout = cachedLoadout;
                const auto primary = registerWeaponConfigString(
                    gameState,
                    registeredLoadout.primary,
                    *firstDynamicWeaponAssetIndex);
                if (primary != WeaponConfigRegistrationFailure::None)
                {
                    GameStateConfiguration.failed(
                        primary == WeaponConfigRegistrationFailure::Dependency
                            ? CodolGameServer::GameStateConfigurationStage::
                                PrimaryDependencyRegistrationFailed
                            : CodolGameServer::GameStateConfigurationStage::
                                PrimaryWeaponRegistrationFailed,
                        classIndex);
                    return false;
                }
                const auto secondary = registerWeaponConfigString(
                    gameState,
                    registeredLoadout.secondary,
                    *firstDynamicWeaponAssetIndex);
                if (secondary != WeaponConfigRegistrationFailure::None)
                {
                    GameStateConfiguration.failed(
                        secondary == WeaponConfigRegistrationFailure::Dependency
                            ? CodolGameServer::GameStateConfigurationStage::
                                SecondaryDependencyRegistrationFailed
                            : CodolGameServer::GameStateConfigurationStage::
                                SecondaryWeaponRegistrationFailed,
                        classIndex);
                    return false;
                }
                if (classIndex >= 0)
                {
                    GameStateConfiguration.registeredClass(
                        static_cast<std::uint32_t>(classIndex));
                }
                registeredMember.loadouts.emplace(
                    name, toResolvedLoadout(registeredLoadout));
            }
            if (registeredMember.loadouts.empty() ||
                !registeredSessionMembers.emplace(
                    preparedMember.xuid, std::move(registeredMember)).second)
            {
                GameStateConfiguration.failed(
                    CodolGameServer::GameStateConfigurationStage::
                        PreparedLoadoutMismatch);
                return false;
            }
        }
        const auto finalCharacter =
            OlMod::processRole() == OlMod::ProcessRole::Dedicated
            ? std::optional<std::uint32_t>{
                prepared.members.front().characterIndex }
            : Bindings.currentCharacterIndex();
        if (!finalCharacter ||
            *finalCharacter != prepared.members.front().characterIndex)
        {
            GameStateConfiguration.failed(
                CodolGameServer::GameStateConfigurationStage::CharacterChanged);
            return false;
        }
        CodolGameServer::SessionAssetRegistry nextSessionAssets;
        if (!nextSessionAssets.replace(std::move(registeredSessionMembers)))
        {
            GameStateConfiguration.failed(
                CodolGameServer::GameStateConfigurationStage::
                    PreparedLoadoutMismatch);
            return false;
        }
        if (!Server.configureGameState(
                std::move(gameState), sessionGeneration))
        {
            GameStateConfiguration.failed(
                CodolGameServer::GameStateConfigurationStage::ServerCommitFailed);
            return false;
        }
        {
            const std::lock_guard lock(LoadoutMutex);
            RegisteredSessionAssets = std::move(nextSessionAssets);
        }
        const std::lock_guard lock(WorldAssetMutex);
        PendingWorldAsset = PendingWorldAssetRequest{
            .mapName = std::string(mapName),
            .gameType = std::string(gameType),
            .mapEntities = std::move(mapEntities),
        };
        GameStateConfiguration.accepted();
        return true;
    }

    bool configureGameState(
        const std::string_view mapName,
        const std::string_view gameType,
        const std::uint32_t configStringChecksum,
        const std::uint32_t checksumFeed = 0)
    {
        std::uint64_t sessionGeneration{};
        {
            const std::lock_guard lock(LoadoutMutex);
            if (PreparedLoadouts)
                sessionGeneration = PreparedLoadouts->sessionGeneration;
        }
        const auto configured = configureGameStateImpl(
            mapName, gameType, configStringChecksum, checksumFeed);
        if (!configured && sessionGeneration)
            static_cast<void>(Server.rollbackSessionRoster(sessionGeneration));
        return configured;
    }

    void configurePendingWorldSpawn(const std::uint32_t nowMilliseconds)
    {
        const auto status = Server.status();
        for (const auto &drop : Server.takeTimeoutDrops())
        {
            const auto *const cause =
                drop.cause == CodolGameServer::SvClientSystem::TimeoutDrop::Cause::Leave
                    ? "client leave"
                    : "client timeout";
            logGameServer(std::string(cause) + " client=" + std::to_string(drop.clientNum) +
                " xuid=" + std::to_string(drop.xuid) +
                " state=" + std::to_string(static_cast<unsigned>(drop.state)) +
                " last_packet=" + std::to_string(drop.lastPacketTime) +
                " profile=" + std::to_string(drop.profileStatsReceivedMask) +
                        "/" + std::to_string(drop.profileStatsRequiredMask) +
                        " profile_complete=" +
                        std::to_string(drop.profileStatsComplete ? 1 : 0) +
                        " gamestate_stage=" +
                        std::to_string(drop.gameStateUpdateStage) +
                        " session_generation=" +
                        std::to_string(drop.sessionGeneration) +
                        " generation_active=" +
                        std::to_string(drop.sessionGenerationActive ? 1 : 0) +
                        " msg_ack=" +
                        std::to_string(drop.messageAcknowledge) +
                        " reliable_ack=" +
                        std::to_string(drop.reliableAcknowledge));
        }
        if (!status.gameStateConfigured || !status.activeClients ||
            status.worldSpawnConfigured)
        {
            return;
        }

        std::optional<PendingWorldAssetRequest> request;
        {
            const std::lock_guard lock(WorldAssetMutex);
            if (!PendingWorldAsset ||
                (PendingWorldAsset->attempted &&
                    nowMilliseconds - PendingWorldAsset->lastAttemptMilliseconds < 1000))
            {
                return;
            }
            PendingWorldAsset->attempted = true;
            PendingWorldAsset->lastAttemptMilliseconds = nowMilliseconds;
            request = PendingWorldAsset;
        }

        const auto preparationStart = RuntimeClock::now();
        // OLMOD(world-preparation-lookups): cache only within this setup attempt.
        // Colour variants share damage models/head bones and FX. Repeating the
        // same native DB/CCS scans blocks the frame thread (and network service)
        // during join. No cache survives a failed attempt or a zone generation.
        std::map<std::pair<std::string,std::string>,std::optional<std::uint8_t>> boneResults;
        std::map<std::array<std::string,3>,std::optional<std::uint8_t>> attachmentResults;
        std::map<std::string,std::optional<std::uint16_t>> effectResults;
        std::uint32_t lookupRequests{}, lookupMisses{};
        const auto boneIndex = [&](const std::string_view model, const std::string_view bone) {
            ++lookupRequests;
            const auto key=std::pair{std::string(model),std::string(bone)};
            if(const auto found=boneResults.find(key);found!=boneResults.end())return found->second;
            ++lookupMisses;
            const auto result=Bindings.modelBoneIndex(model,bone);
            boneResults.emplace(key,result);
            return result;
        };
        const auto attachmentIndex = [&](const std::string_view body,
            const std::string_view head, const std::string_view bone) {
            ++lookupRequests;
            const auto key=std::array{std::string(body),std::string(head),std::string(bone)};
            if(const auto found=attachmentResults.find(key);found!=attachmentResults.end())return found->second;
            ++lookupMisses;
            const auto result=Bindings.attachmentBoneIndex(body,head,bone);
            attachmentResults.emplace(key,result);
            return result;
        };
        const auto effectParameter = [&](const std::string_view name) {
            ++lookupRequests;
            const auto key=std::string(name);
            if(const auto found=effectResults.find(key);found!=effectResults.end())return found->second;
            ++lookupMisses;
            const auto result=Bindings.resolveEffectEventParameter(name);
            effectResults.emplace(key,result);
            return result;
        };

        const auto reportFailure = [&request](std::string stage) {
            bool changed{};
            {
                const std::lock_guard lock(WorldAssetMutex);
                if (PendingWorldAsset && request &&
                    PendingWorldAsset->mapName == request->mapName &&
                    PendingWorldAsset->gameType == request->gameType &&
                    PendingWorldAsset->lastFailureStage != stage)
                {
                    PendingWorldAsset->lastFailureStage = stage;
                    changed = true;
                }
            }
            if (changed)
            {
                logGameServer(
                    "world spawn pending map=" + request->mapName +
                    " stage=" + stage);
            }
        };

        const auto entityText = request->mapEntities
            ? std::optional<std::string>{}
            : Bindings.readMapEntityString(request->mapName);
        if (!request->mapEntities && !entityText)
        {
            reportFailure("map_entity_asset");
            return;
        }
        const auto glassMetadata =
            Bindings.resolveGlassMapMetadata(request->mapName);
        if (!glassMetadata)
        {
            reportFailure("glass_map_metadata");
            return;
        }
        const auto glassThresholds = glassDamageThresholds();
        if (!glassThresholds)
        {
            reportFailure("glass_damage_thresholds");
            return;
        }
        if (!Server.configureGlassMap(*glassMetadata, *glassThresholds))
        {
            reportFailure("glass_world_commit");
            return;
        }
        const auto entities = request->mapEntities
            ? request->mapEntities
            : CodolGameServer::SV_ParseMapEntities(*entityText);
        if (!entities)
        {
            reportFailure("map_entity_parse");
            return;
        }
        // OLMOD(const-baselines): THE ENTITY NUMBER IS THE IDENTITY, and it is not something
        // this server derives -- it is shipped data.
        //
        // A census used to run here, printing every map entity in parse order, to test the
        // hypothesis that retail numbers by position among ALL map entities. That hypothesis
        // is dead: hill-climbing it plateaued at 288/397 with an incoherent skip-set, because
        // the gaps encode which entities take a slot and the entity list does not say.
        //
        // The answer is `<map>_const.ff`, an asset every map ships:
        // `mp/constbaselines/bl_pc_<map>_<gametype>.bin` IS retail's table, and the client
        // loads it at map load and indexes cl.entityBaselines out of it by entity number.
        // sv_const_baselines_mp.hpp carries the extracted numbers; re/demo-re/16-const-baselines.md
        // has the derivation. This log says whether this map got them.
        {
            const auto *const constBaselines =
                CodolGameServer::SV_ConstBaselineTable(
                    request->mapName, request->gameType);
            if (constBaselines)
            {
                std::size_t brushModels = 0;
                for (const auto &entry : constBaselines->entries)
                    brushModels += entry.brushModelIndex ? 1 : 0;
                logGameServer(
                    "const baselines map=" + std::string(request->mapName) +
                    " gametype=" + std::string(constBaselines->gameType) +
                    " entries=" +
                    std::to_string(constBaselines->entries.size()) +
                    " brushModels=" + std::to_string(brushModels) +
                    " -- static entities publish on retail's numbers and "
                    "snapshot flag 0x10 is armed");
            }
            else
            {
                logGameServer(
                    "const baselines map=" + std::string(request->mapName) +
                    " NONE -- no extracted table for this map, static entities "
                    "fall back to sequential numbering and snapshot flag 0x10 "
                    "stays off (see re/demo-re/16-const-baselines.md)");
            }
            // TEMPORARY: the map's OWN order for the two classes that take a static
            // entity slot. Retail's table is in allocation order -- brush `*N` rises
            // strictly with slot order -- so brush models are exact ordered ANCHORS, and
            // the script models between two consecutive anchors must be the table rows
            // between those same two anchors, in order. Position within an anchored
            // bracket is an identity in a way an origin is not.
            //
            // Logged raw so the hypothesis can be tested against the shipped table before
            // any of it is believed.
            {
                std::size_t ordinal = 0;
                for (const auto &entity : *entities)
                {
                    const auto className = entity.value("classname").value_or("");
                    const auto model = entity.value("model").value_or("");
                    if (className == "script_brushmodel")
                    {
                        logGameServer(
                            "static order [" + std::to_string(ordinal++) +
                            "] brush model=" + std::string(model));
                    }
                    else if (className == "script_model")
                    {
                        const auto origin = entity.value("origin").value_or("");
                        logGameServer(
                            "static order [" + std::to_string(ordinal++) +
                            "] script model=" + std::string(model) +
                            " origin=" + std::string(origin));
                    }
                }
            }
            logGameServer(
                "mapent census total=" + std::to_string(entities->size()) +
                " firstDynamicEntityNum=" +
                std::to_string(CodolGameServer::FirstDynamicServerEntityNum));
        }

        const auto brushSpawns = CodolGameServer::SV_SelectBrushModelSpawns(*entities);
        if (!brushSpawns)
        {
            reportFailure("brush_spawn_parse");
            return;
        }
        const auto scriptModelSpawns =
            CodolGameServer::SV_SelectScriptModelSpawns(*entities);
        if (!scriptModelSpawns)
        {
            reportFailure("script_model_spawn_parse");
            return;
        }
        // ZM ZONES AND SPAWN POINTS -- OBSERVATION ONLY. Step 1 of the zombie work:
        // nothing consumes this yet. It parses the zone/spawner model out of the map
        // entity string and LOGS the counts so the parse can be checked against the
        // measured numbers BEFORE anything is built on it.
        //
        // re/demo-re/21-zm-zones-and-spawners.md predicts, per map:
        //     zm_factory_sh   12 zones / 63 spawn points / 61 with a goal
        //     zm_sumpf_sh     11 zones / 74 spawn points / 32 with a goal
        //     zm_prototype_sh  3 zones / 41 spawn points / 41 with a goal
        //     zm_asylum_sh     9 zones / 38 spawn points / 38 with a goal
        // Those are the numbers this line must print. A different count means the
        // parse is wrong, not that the map is unusual.
        //
        // A PARSE FAILURE IS LOGGED AND IGNORED ON PURPOSE. This is new code on a path
        // four zm maps already load correctly; refusing the world spawn over an
        // observational parser would turn a wrong count into a broken map.
        if (request->gameType == "zm")
        {
            auto zmZones = CodolGameServer::SV_SelectZmZones(*entities);
            if (!zmZones)
            {
                logGameServer(
                    "zm zones PARSE FAILED map=" + request->mapName +
                    " (observational, world spawn continues)");
            }
            else
            {
                // RESOLVE EACH VOLUME'S SHAPE OUT OF MapEnts.trigger.
                //
                // NOT through resolveBrushModelCollision. That indexes the clipmap's
                // cmodel list while `?N` indexes MapEnts.trigger, and routing zone
                // volumes through it reported success on all 32 and returned a
                // different brush every time -- see the comment on the reader.
                //
                // A volume that will not resolve is LEFT UNRESOLVED, and the
                // containment test skips it, so the failure mode is "no zone" rather
                // than a confidently wrong one.
                std::size_t zmVolumes{};
                std::size_t zmResolved{};
                std::size_t zmHulls{};
                std::size_t zmSlabs{};
                for (auto &zone : *zmZones)
                {
                    for (auto &volume : zone.volumes)
                    {
                        ++zmVolumes;
                        auto hulls = Bindings.resolveTriggerModelHulls(
                            request->mapName, volume.triggerModel);
                        if (!hulls || hulls->empty())
                            continue;
                        zmHulls += hulls->size();
                        for (const auto &hull : *hulls)
                            zmSlabs += hull.slabs.size();
                        volume.hulls = std::move(*hulls);
                        volume.hullsResolved = true;
                        ++zmResolved;
                    }
                }

                std::size_t zmSpawnPoints{};
                std::size_t zmWithGoal{};
                std::string zmDetail;
                for (const auto &zone : *zmZones)
                {
                    zmSpawnPoints += zone.spawnPoints.size();
                    for (const auto &point : zone.spawnPoints)
                    {
                        if (!point.goal.empty())
                            ++zmWithGoal;
                    }
                    zmDetail += " " + zone.name + "(v" +
                        std::to_string(zone.volumes.size()) + ",p" +
                        std::to_string(zone.spawnPoints.size()) + ")";
                }
                // HAND THE MODEL TO THE SCRIPT LAYER. Step 2: the zm builtins read
                // it from here. Still nothing spawns -- this only makes the parsed
                // zones reachable from zm.lua.
                Server.setZmZones(*zmZones);
                logGameServer(
                    "zm zones parsed map=" + request->mapName +
                    " zones=" + std::to_string(zmZones->size()) +
                    " spawnPoints=" + std::to_string(zmSpawnPoints) +
                    " withGoal=" + std::to_string(zmWithGoal) +
                    " volumes=" + std::to_string(zmVolumes) +
                    " hullsResolved=" + std::to_string(zmResolved) +
                    " hulls=" + std::to_string(zmHulls) +
                    " slabs=" + std::to_string(zmSlabs) + zmDetail);
            }

            // THE NAVIGATION GRAPH, measured off the zm demos because `aipaths` is
            // empty in every shipped zone. re/demo-re/20-zm-actor-lifecycle.md 12.57.
            //
            // AN EMPTY GRAPH IS A LEGITIMATE ANSWER, not a world-spawn failure: only
            // zm_factory_sh has a measured graph, and SV_BuildZmNavGraph also returns
            // nothing when the loaded map's nodes disagree with the table it was built
            // from. Either way the actors park on their spawners, which is correct
            // placement (12.31) rather than a degraded mode.
            CodolGameServer::SvZmNavGroundResolver navGroundResolver;
            // OLMOD(factory-reference-bootstrap): opt-in donor walks use native-world
            // floor and body checks; see navigation-increment-20260920.md.
            CodolGameServer::SvZmNavWalkValidator navReferenceWalkValidator;
            auto navSource = CodolGameServer::SvZmNavSource::CodolRecovered;
            const auto *const requestedNavSource =
                std::getenv("OLMOD_ZM_NAV_SOURCE");
            const auto bo1HybridRequested = requestedNavSource &&
                std::string_view(requestedNavSource) == "bo1_hybrid";
            if (request->mapName == "zm_factory_sh")
            {
                navGroundResolver = [](std::size_t, const std::array<float, 3> &origin)
                    -> std::optional<float> {
                    auto start = origin;
                    auto end = origin;
                    start[2] += 1.0f;
                    end[2] -= 256.0f;
                    const auto hit = Bindings.traceWorld(
                        start, end, CodolGameServer::PointTraceBounds,
                        CodolGameServer::PlayerCollisionContentMask &
                            ~CodolGameServer::PlayerCollisionContents,
                        CodolGameServer::SvGlassState{});
                    if (!hit || hit->startSolid || hit->allSolid ||
                        hit->fraction < 0.0f || hit->fraction >= 1.0f ||
                        hit->normal[2] < 0.7f)
                        return std::nullopt;
                    return start[2] + (end[2] - start[2]) * hit->fraction;
                };
                logGameServer("zm grounded navigation enabled (world-only ground; actor collision retained)");
                if (bo1HybridRequested)
                {
                    navSource = CodolGameServer::SvZmNavSource::Bo1Hybrid;
                    navReferenceWalkValidator = [](const std::array<float, 3> &from,
                                                    const std::array<float, 3> &to) {
                        const auto ground = [](const std::array<float, 3> &point)
                            -> std::optional<float> {
                            auto start = point;
                            auto end = point;
                            start[2] += 18.0f;
                            end[2] -= 32.0f;
                            const auto hit = Bindings.traceWorld(
                                start, end, CodolGameServer::PointTraceBounds,
                                CodolGameServer::PlayerCollisionContentMask &
                                    ~CodolGameServer::PlayerCollisionContents,
                                CodolGameServer::SvGlassState{});
                            if (!hit || hit->startSolid || hit->allSolid ||
                                hit->fraction < 0.0f || hit->fraction >= 1.0f ||
                                hit->normal[2] < 0.7f)
                                return std::nullopt;
                            return start[2] + (end[2] - start[2]) * hit->fraction;
                        };
                        const auto clear = [](const std::array<float, 3> &start,
                                              const std::array<float, 3> &end) {
                            constexpr CodolGameServer::TraceBounds body{
                                .midpoint = {0.0f, 0.0f, 35.0f},
                                .halfSize = {15.0f, 15.0f, 34.0f}};
                            const auto hit = Bindings.traceWorld(
                                start, end, body,
                                CodolGameServer::PlayerCollisionContentMask &
                                    ~CodolGameServer::PlayerCollisionContents,
                                CodolGameServer::SvGlassState{});
                            return hit && !hit->startSolid && !hit->allSolid &&
                                hit->fraction >= 0.999f;
                        };
                        // BO1's stored ordinary graph includes staircase links.
                        // The flat-only validator rejected both teleporter-room
                        // stairs even though the live CODOL world exposes every
                        // tread. Admit either a fully flat corridor or a bounded
                        // sequence of legal 18-unit steps; both paths still require
                        // continuous live floor support and actor-sized clearance.
                        return CodolGameServer::SV_ZmSupportedWalk(
                                   from, to, ground, clear, 260.0f) ||
                            CodolGameServer::SV_ZmSupportedStairWalk(
                                from, to, ground, clear);
                    };
                    logGameServer(
                        "zm nav source=bo1_hybrid requested (CODOL base; "
                        "BO1 ordinary walks require live corridor validation)");
                }
            }
            else if (bo1HybridRequested)
            {
                logGameServer("zm nav source=bo1_hybrid ignored outside zm_factory_sh");
            }
            auto zmNavGraph = CodolGameServer::SV_BuildZmNavGraph(
                *entities, request->mapName,
                [](const std::string_view animName) {
                    return Bindings.resolveAnimConfigStringIndex(animName);
                }, navGroundResolver, navSource, navReferenceWalkValidator);
            if (const auto *room = std::getenv("OLMOD_FACTORY_ROOM_DRAFT");
                room && std::string_view(room) == "1" &&
                request->mapName == "zm_factory_sh" && bo1HybridRequested)
            {
                logGameServer("FACTORYROOM " + CodolGameServer::SV_ApplyFactoryRoomDraft(
                    zmNavGraph, navGroundResolver, navReferenceWalkValidator,
                    [](const std::array<float,3>& from,const std::array<float,3>& to) {
                        // Same compact landing hull as stepZombieActors, restricted
                        // by the caller to the two known short window-exit ports.
                        const auto clear=[](const auto &a,const auto &b) {
                            constexpr CodolGameServer::TraceBounds compact{{0,0,28},{1,1,20}};
                            const auto hit=Bindings.traceWorld(a,b,compact,
                                CodolGameServer::PlayerCollisionContentMask & ~CodolGameServer::PlayerCollisionContents,
                                CodolGameServer::SvGlassState{});
                            return hit && !hit->startSolid && !hit->allSolid && hit->fraction>=0.999f;
                        };
                        const auto ground=[](const auto &p)->std::optional<float> {
                            auto a=p,b=p;a[2]+=18;b[2]-=32;
                            const auto hit=Bindings.traceWorld(a,b,CodolGameServer::PointTraceBounds,
                                CodolGameServer::PlayerCollisionContentMask & ~CodolGameServer::PlayerCollisionContents,
                                CodolGameServer::SvGlassState{});
                            if(!hit||hit->startSolid||hit->allSolid||hit->fraction>=1||hit->normal[2]<0.7f)return {};
                            return a[2]+(b[2]-a[2])*hit->fraction;
                        };
                        return CodolGameServer::SV_ZmSupportedStairWalk(from,to,ground,clear,32.0f,18.0f);
                    }));
            }
            const auto zmNavNodes = zmNavGraph.nodes.size();
            const auto zmNavEdges = zmNavGraph.adjacency.size() / 2u;
            const auto zmNavVaults = zmNavGraph.vaultAnim.size();
            const auto *const zmNavTable =
                CodolGameServer::SV_ZmNavTable(request->mapName);
            // Diagnostic only: authored node Z is not the walking surface. Keep
            // the current graph untouched while measuring retained world collision
            // under its nodes for comparison with absolute Factory demo positions.
            // One map-load pass, opt-in; never runs in the actor/frame loop.
            if (const auto *audit = std::getenv("OLMOD_ZM_NODE_GROUND_AUDIT");
                audit && std::string_view(audit) == "1")
            {
                for (std::size_t node = 0; node < zmNavGraph.nodes.size(); ++node)
                {
                    auto start = zmNavGraph.nodes[node];
                    auto end = start;
                    start[2] += 1.0f;
                    end[2] -= 256.0f;
                    const auto hit = Bindings.traceWorld(
                        start, end, CodolGameServer::PointTraceBounds,
                        CodolGameServer::PlayerCollisionContentMask &
                            ~CodolGameServer::PlayerCollisionContents,
                        CodolGameServer::SvGlassState{});
                    logGameServer("ZMNODEGROUND node=" + std::to_string(node) +
                        " authoredZ=" + std::to_string(zmNavGraph.nodes[node][2]) +
                        " fraction=" + (hit ? std::to_string(hit->fraction) : "missing") +
                        " z=" + (hit ? std::to_string(start[2] +
                            (end[2] - start[2]) * hit->fraction) : "missing") +
                        " startSolid=" + std::to_string(hit && hit->startSolid) +
                        " allSolid=" + std::to_string(hit && hit->allSolid) +
                        " normalZ=" + (hit ? std::to_string(hit->normal[2]) : "missing"));
                }
            }
            // Research-only, one map-load pass. Compare a rejected node chord
            // against absolute demo20-21-43 actor810, 921800..924950. World-only
            // sweeps do not establish clearance against dynamic doors or actors.
            if (const auto *audit = std::getenv("OLMOD_ZM_CORRIDOR_AUDIT");
                audit && std::string_view(audit) == "1" &&
                request->mapName == "zm_factory_sh" && navGroundResolver &&
                zmNavGraph.nodes.size() > 871u)
            {
                constexpr std::array<std::array<float, 3>, 7> samples{{
                    {-757.0f,-281.0f,67.0f}, {-744.0f,-328.0f,67.0f},
                    {-738.0f,-353.0f,68.0f}, {-730.0f,-378.0f,68.0f},
                    {-723.0f,-403.0f,67.0f}, {-717.0f,-422.0f,67.0f},
                    {-698.0f,-478.0f,67.0f}}};
                const auto probe = [&](const std::string &label,
                                       const std::array<float,3> &start,
                                       const std::array<float,3> &end) {
                    constexpr CodolGameServer::TraceBounds body{
                        .midpoint = {0.0f,0.0f,35.0f},
                        .halfSize = {15.0f,15.0f,34.0f}};
                    const auto hit = Bindings.traceWorld(start,end,body,
                        CodolGameServer::PlayerCollisionContentMask &
                            ~CodolGameServer::PlayerCollisionContents,
                        CodolGameServer::SvGlassState{});
                    logGameServer("ZMCORRIDOR " + label +
                        " fraction=" + (hit ? std::to_string(hit->fraction) : "missing") +
                        " startSolid=" + std::to_string(hit && hit->startSolid) +
                        " allSolid=" + std::to_string(hit && hit->allSolid) +
                        " normalZ=" + (hit ? std::to_string(hit->normal[2]) : "missing"));
                };
                probe("chord869to871",zmNavGraph.nodes[869],zmNavGraph.nodes[871]);
                for (std::size_t i=1;i<samples.size();++i)
                    probe("demo810leg"+std::to_string(i),samples[i-1],samples[i]);
                // Humanoid710's walk handoff through the climb exit, same demo.
                constexpr std::array<std::array<float,3>,7> climbExit{{
                    {62,213,96},{59,212,95},{54,208,95},{48,205,95},
                    {43,201,95},{37,198,95},{31,195,93}}};
                for (std::size_t i=0;i<climbExit.size();++i)
                    probe("climbExit710point"+std::to_string(i),climbExit[i],climbExit[i]);
            }
            Server.setZmNavGraph(std::move(zmNavGraph));
            // THE BARRIERS. A board group joined to the traversal sharing its `pfNNN`
            // prefix -- 12.66. Expect 28 barriers / 168 boards / 28 vaulted on factory.
            const auto zmBarriers =
                CodolGameServer::SV_SelectZmBarriers(*entities);
            std::size_t zmBoards{};
            std::size_t zmVaulted{};
            std::map<std::size_t, std::size_t> zmBoardsPer;
            for (const auto &barrier : zmBarriers)
            {
                zmBoards += barrier.boards.size();
                zmVaulted += barrier.hasVault ? 1u : 0u;
                ++zmBoardsPer[barrier.boards.size()];
            }
            std::string zmBoardShape;
            for (const auto &[count, howMany] : zmBoardsPer)
            {
                zmBoardShape += " " + std::to_string(howMany) + "x" +
                    std::to_string(count);
            }
            // AFTER the nav graph: a barrier is keyed by the node pair of its traversal,
            // so the graph has to exist before the barriers can be resolved onto it.
            Server.setZmBarriers(zmBarriers);
            logGameServer(
                "zm barriers map=" + request->mapName +
                " barriers=" + std::to_string(zmBarriers.size()) +
                " boards=" + std::to_string(zmBoards) +
                " vaulted=" + std::to_string(zmVaulted) +
                // How many resolved onto a graph EDGE, which is what the stepper can
                // actually gate on. Lower than `vaulted` means some traversals are not
                // in the graph -- expected, the graph is a measured floor (12.58).
                " onGraph=" + std::to_string(Server.zmBarrierCount()) +
                " groups:" + zmBoardShape);

            // THE BASE ANIMATION, resolved the same way and for the same reason. 476 --
            // what every actor has published since 12.53 -- is `ai_zombie_boardtear_l_1`,
            // a zombie tearing boards off a barrier, held forever (12.61).
            const auto zmWalkAnim = Bindings.resolveAnimConfigStringIndex(
                CodolGameServer::SvActorWalkAnimName);
            Server.setZmActorWalkAnim(zmWalkAnim.value_or(std::uint16_t{}));
            const auto zmTearAnim = Bindings.resolveAnimConfigStringIndex(
                CodolGameServer::SvActorTearAnimName);
            Server.setZmActorTearAnim(zmTearAnim.value_or(std::uint16_t{}));
            CodolGameServer::SvZmTearClips tearClips{};
            std::size_t tearClipCount{};
            if (request->mapName == "zm_factory_sh")
            {
                for (std::size_t lane=0; lane<3; ++lane)
                    for (std::size_t slot=0; slot<6; ++slot)
                    {
                        const auto name=std::string("ai_zombie_boardtear_") +
                            "lmr"[lane] + "_" + std::to_string(slot+1);
                        const auto alias=Bindings.resolveAnimConfigStringIndex(name);
                        const auto markers=Bindings.animationNotifyTimes(name);
                        if (!alias || !markers) continue;
                        std::optional<float> boardTime, endTime;
                        bool duplicate=false;
                        for (const auto &[id,seconds] : *markers)
                        {
                            const auto marker=Bindings.animationNotifyName(id);
                            if (marker == "board")
                            {
                                duplicate |= boardTime.has_value();
                                boardTime=seconds;
                            }
                            else if (marker == "end")
                            {
                                duplicate |= endTime.has_value();
                                endTime=seconds;
                            }
                        }
                        if (!duplicate && boardTime && endTime)
                            tearClips[lane][slot]=CodolGameServer::SV_ZmTearClipFromMarkers(
                                *alias,*boardTime,*endTime);
                        if (tearClips[lane][slot].valid()) ++tearClipCount;
                    }
            }
            // Resolve once per map, never by scanning assets in the actor frame.
            // Empty entries stay unresolved; no guessed alias or fallback timer.
            Server.setZmTearClips(tearClips);
            Server.setZmBoardTrajectoryEvaluator([](const CodolGameServer::SvNativeTrajectory &trajectory,
                std::int32_t atTime, std::array<float,3> &point) {
                const auto evaluated=Bindings.evaluateTrajectory(trajectory,atTime);
                if (!evaluated) return false;
                point=*evaluated;
                return true;
            });
            logGameServer("zm tear marker profiles resolved=" + std::to_string(tearClipCount) + "/18");
            const auto zmDeathAnim = Bindings.resolveAnimConfigStringIndex(
                CodolGameServer::SvActorDeathAnimName);
            Server.setZmActorDeathAnim(zmDeathAnim.value_or(std::uint16_t{}));
            // OLMOD(factory_presentation_preview): opt-in and map-scoped. Resolve
            // names from resident bands only, once per map; no DB loading in ticks.
            // TODO(CODOL): recover damage predicates and outfit RNG. This restores
            // recorded clips/pairs, not the missing original server decision owner.
            std::vector<CodolGameServer::SvZmOutfit> zmOutfits;
            std::vector<CodolGameServer::SvZmDeathClip> zmDeaths;
            CodolGameServer::SvZmDeathFx zmDeathFx{};
            const auto *presentation=std::getenv("OLMOD_FACTORY_PRESENTATION");
            if(request->mapName=="zm_factory_sh" && presentation && std::string_view(presentation)=="1")
            {
                const auto models=Bindings.modelConfigStringBand();
                const auto lookup=[&](const std::string &name)->std::uint16_t {
                    for(const auto &[index,entry]:models) if(entry==name)return index;
                    return 0;
                };
                // OLMOD(zm-round-colors): tag resident aliases once; spawn-time
                // color selection is independent of the clothing-family cycle.
                using BodyColor = CodolGameServer::SvZmBodyColor;
                struct ColorSpec { const char *suffix; BodyColor color; };
                const ColorSpec colors[]{ {"_body_blue",BodyColor::Blue},
                    {"_body",BodyColor::Base},{"_body_orange",BodyColor::Orange},
                    {"_body_red",BodyColor::Red},{"_body_yel",BodyColor::Yellow} };
                for(const auto &[suffix,color]:colors)
                    for(const auto *family:{"garbageman","worker","secunityguard"})
                    {
                        const auto stem="c_zom_"+std::string(family);
                        const auto body=lookup(stem+suffix),head=lookup(stem+"_head");
                        if(body && head)
                        {
                            CodolGameServer::SvZmOutfit outfit{body,head};
                            outfit.color=color;
                            const auto *deathFx = std::getenv("OLMOD_FACTORY_DEATH_FX");
                            if (deathFx && std::string_view(deathFx)=="1")
                            {
                                outfit.torso=lookup(stem+"_body_torso_1");
                                outfit.lower=lookup(stem+"_body_lowclean");
                                outfit.behead=lookup(stem+"_body_behead");
                                outfit.neckBone=boneIndex(stem+suffix,"j_neck").value_or(255);
                                outfit.torsoBone=boneIndex(stem+"_body_torso_1","j_spinelower").value_or(255);
                                outfit.leftArmOff=lookup(stem+"_body_larmoff_1");
                                outfit.leftArmBone=boneIndex(stem+"_body_larmoff_1","j_shoulder_le").value_or(255);
                                outfit.rightArmOff=lookup(stem+"_body_rarmoff_1");
                                outfit.rightArmBone=boneIndex(stem+"_body_rarmoff_1","j_shoulder_ri").value_or(255);
                                outfit.shockBone=boneIndex(stem+suffix,"j_spineupper").value_or(255);
                                // Reuse a body-bone index only if every loaded damage
                                // variant agrees; never guess a composed head index.
                                for(const auto tail:{"_body_torso_1","_body_rarmoff_1","_body_larmoff_1"})
                                    if(lookup(stem+tail) && boneIndex(stem+tail,"j_spineupper").value_or(255)!=outfit.shockBone)
                                        outfit.shockBone=255;
                                // Eye attachment indices are composed-DObj indices,
                                // not the standalone head model's bone numbers.
                                // Keep absent until that composition is resolved.
                            }
                            const auto *eyes=std::getenv("OLMOD_FACTORY_FACE_GLOW");
                            if(eyes && std::string_view(eyes)=="1")
                            {
                                // CODREF(actor_head_attachment): recorded event113
                                // targets composed left-eye86 / tag_mouth97. Resolve
                                // names against every supported body, not magic IDs.
                                const auto tag=[&](const char *name) {
                                    const auto index=attachmentIndex(stem+suffix,stem+"_head",name);
                                    if(!index)return std::uint8_t{255};
                                    for(const auto tail:{"_body_torso_1","_body_rarmoff_1","_body_larmoff_1"})
                                        if(lookup(stem+tail) && attachmentIndex(stem+tail,stem+"_head",name)!=index)
                                            return std::uint8_t{255};
                                    return *index;
                                };
                                const char *phase=color==BodyColor::Blue?"blue":
                                    color==BodyColor::Yellow?"yellow":color==BodyColor::Orange?"orange":nullptr;
                                // Ordinary body-color pairing only. The original
                                // special red/global switch trigger is unresolved.
                                if(phase)
                                {
                                    outfit.eyeGlowBone=tag("j_eyeball_le");
                                    outfit.mouthGlowBone=tag("tag_mouth");
                                    outfit.eyeGlow=effectParameter("maps/zombie/zm_eye_lensflare_"+std::string(phase)).value_or(0);
                                    outfit.mouthGlow=effectParameter("zombie/mouth_glow_"+std::string(phase)+"_small").value_or(0);
                                    logGameServer("ZMFACE resolved body="+std::to_string(body)+" eye="+std::to_string(outfit.eyeGlow)+
                                        " mouth="+std::to_string(outfit.mouthGlow)+" bones="+std::to_string(outfit.eyeGlowBone)+","+std::to_string(outfit.mouthGlowBone));
                                }
                            }
                            zmOutfits.push_back(outfit);
                        }
                    }
                for(const auto &spec:CodolGameServer::SvZmDeathSpecs)
                    if(const auto alias=Bindings.resolveAnimConfigStringIndex(spec.name); alias && *alias)
                        zmDeaths.push_back({*alias,spec.milliseconds,spec.weight,0,0,0,0,spec.electrical});
                const auto *deathFx = std::getenv("OLMOD_FACTORY_DEATH_FX");
                if (deathFx && std::string_view(deathFx)=="1")
                {
                    zmDeathFx.neck=effectParameter(
                        "misc/fx_zombie_bloodspurt_codo").value_or(0);
                    zmDeathFx.torso=effectParameter(
                        "weapon/bullet/fx_flesh_gib_fatal_01_blue").value_or(0);
                    const auto *bo1=std::getenv("OLMOD_FACTORY_BO1_DAMAGE");
                    zmDeathFx.bo1Derived=bo1 && std::string_view(bo1)=="1";
                    const auto *refined=std::getenv("OLMOD_FACTORY_REFINED_FX");
                    zmDeathFx.refined=zmDeathFx.bo1Derived && refined && std::string_view(refined)=="1";
                    if(zmDeathFx.refined)
                    {
                        // CODREF(xanim_shared_actor_blend): native 0x786E70 clock;
                        // original July31 demo actor808 A-loop -> E-down (850ms),
                        // 727 B->B (600), 799 D->B (550), 743 E->A (350).
                        // OLMOD(refined_fx): representative recorded pairs, not a
                        // recovered selection table. No verified C-loop pair here.
                        struct Pair {const char *base,*loop,*down;unsigned hold,settle;};
                        const Pair pairs[]{
                            {"ai_zombie_tesla_death_a","ai_zombie_tesla_death_a_loop","ai_zombie_tesla_death_e_down",850,3250},
                            {"ai_zombie_tesla_death_b","ai_zombie_tesla_death_b_loop","ai_zombie_tesla_death_b_down",600,3884},
                            {"ai_zombie_tesla_death_d","ai_zombie_tesla_death_d_loop","ai_zombie_tesla_death_b_down",550,3884},
                            {"ai_zombie_tesla_death_e","ai_zombie_tesla_death_e_loop","ai_zombie_tesla_death_a_down",350,3850}};
                        for(const auto &p:pairs)
                        {
                            const auto base=Bindings.resolveAnimConfigStringIndex(p.base);
                            const auto loop=Bindings.resolveAnimConfigStringIndex(p.loop);
                            const auto down=Bindings.resolveAnimConfigStringIndex(p.down);
                            if(!base || !loop || !down)continue;
                            for(auto &clip:zmDeaths)if(clip.animation==*base)
                            {
                                clip.loopAnimation=*loop;clip.downAnimation=*down;
                                clip.loopMilliseconds=p.hold;clip.downMilliseconds=p.settle;
                                logGameServer("ZMFX sequence base="+std::to_string(*base)+" loop="+std::to_string(*loop)+" down="+std::to_string(*down));
                            }
                        }
                    }
                    if(zmDeathFx.bo1Derived)
                    {
                        zmDeathFx.randomSeed=static_cast<std::uint32_t>(
                            std::chrono::steady_clock::now().time_since_epoch().count());
                        zmDeathFx.shock=effectParameter("maps/zombie/fx_zombie_tesla_shock").value_or(0);
                        zmDeathFx.shockEyes=effectParameter("maps/zombie/fx_zombie_tesla_shock_eyes").value_or(0);
                        // Literal names exist in the supplied CODOL zombie zone.
                        // Accept only names actually resolved in this map's weapon band.
                        // This is BO1-derived classification, not recovered CODOL damage code.
                        for(const auto name:{"tesla_gun_zm","tesla_gun_upgraded","tesla_gun_upgraded_zm"})
                            if(const auto index=Bindings.resolveWeaponConfigStringIndex(name);index && *index)
                                {
                                zmDeathFx.electricalWeapons.push_back(*index);
                                logGameServer("ZMFX electrical weapon name="+std::string(name)+" index="+std::to_string(*index));
                            }
                        for(const auto name:{"m1911_zm","flamethrower_zm","freezegun_zm","freezegun_upgraded_zm"})
                            if(const auto index=Bindings.resolveWeaponConfigStringIndex(name);index && *index)
                                zmDeathFx.excludedWeapons.push_back(*index);
                        logGameServer("ZMFX BO1 policy enabled seed="+std::to_string(zmDeathFx.randomSeed)+
                            " electricalWeapons="+std::to_string(zmDeathFx.electricalWeapons.size())+
                            " shock="+std::to_string(zmDeathFx.shock)+" shockEyes="+std::to_string(zmDeathFx.shockEyes));
                    }
                    for (const auto &o:zmOutfits)
                        logGameServer("ZMFX resolved body="+std::to_string(o.body)+
                            " head="+std::to_string(o.head)+" behead="+std::to_string(o.behead)+
                            " torso="+std::to_string(o.torso)+" lower="+std::to_string(o.lower)+
                            " neckBone="+std::to_string(o.neckBone)+" torsoBone="+std::to_string(o.torsoBone)+
                            " rightArm="+std::to_string(o.rightArmOff)+" rightArmBone="+std::to_string(o.rightArmBone)+
                            " leftArm="+std::to_string(o.leftArmOff)+" leftArmBone="+std::to_string(o.leftArmBone));
                    logGameServer("ZMFX resolved neck="+std::to_string(zmDeathFx.neck)+
                        " torso="+std::to_string(zmDeathFx.torso)+" policy="+(zmDeathFx.bo1Derived?"BO1-derived":"lethal-reconstructed"));
                }
            }
            // OLMOD(factory-arrival): resident name resolution once per map.
            // The world owns two fixed, noncolliding carriers; no view overlay.
            std::uint16_t arrivalModel{};
            std::array<std::uint16_t,3> arrivalEffects{};
            std::uint8_t arrivalBone{};
            if (const auto *entry = std::getenv("OLMOD_FACTORY_ENTRY");
                entry && std::string_view(entry) == "1")
            {
                const auto bone = boneIndex("tag_origin", "tag_origin");
                if (bone && *bone != 255)
                {
                    arrivalModel = Bindings.resolveModelConfigStringIndex("tag_origin").value_or(0);
                    arrivalBone = *bone;
                    arrivalEffects = {
                        effectParameter("maps/zombie/fx_portable_teleporter").value_or(0),
                        effectParameter("maps/zombie/fx_zombie_spatial_switching_flash").value_or(0),
                        effectParameter("maps/zombie/fx_zombie_spatial_switching").value_or(0)};
                }
                logGameServer("Factory arrival resolved model=" + std::to_string(arrivalModel) +
                    " bone=" + std::to_string(arrivalBone) + " fx=" +
                    std::to_string(arrivalEffects[0]) + "," + std::to_string(arrivalEffects[1]) +
                    "," + std::to_string(arrivalEffects[2]));
            }
            Server.setFactoryArrivalFx(arrivalModel,arrivalEffects,arrivalBone);
            CodolGameServer::SvFactoryTeleporterResources teleportResources{};
            if(const auto *option=std::getenv("OLMOD_FACTORY_TELEPORTERS");
                option && std::string_view(option)=="1" && request->mapName=="zm_factory_sh" && request->gameType=="zm") {
                // Resident names from Factory assets; resolve once, never in the frame loop.
                teleportResources.packModelOn=Bindings.resolveModelConfigStringIndex("zombie_vending_packapunch_on").value_or(0);
                teleportResources.packGlow=effectParameter("misc/fx_zombie_cola_on_blue_glow").value_or(0);
                teleportResources.packHum=Bindings.resolveSoundAliasEventParameter("zmb_perks_packa_loop").value_or(0);
                constexpr std::array<std::string_view,4> packTags{
                    "tag_on_glow_right1","tag_on_glow_left1","tag_on_glow_right","tag_on_glow_left"};
                for (std::size_t i=0;i<packTags.size();++i)
                    teleportResources.packGlowBones[i]=boneIndex("zombie_vending_packapunch_on",packTags[i]).value_or(255);
                // The gamestate owner registers these dynamic names before
                // client admission. setFactoryTeleporterResources retains its pair.
                teleportResources.model=Bindings.resolveModelConfigStringIndex("tag_origin").value_or(0);
                teleportResources.bone=boneIndex("tag_origin","tag_origin").value_or(255);
                teleportResources.padStart=effectParameter("maps/zombie/fx_transporter_pad_start").value_or(0);
                teleportResources.beam=effectParameter("maps/zombie/fx_transporter_beam").value_or(0);
                if(const auto *travel=std::getenv("OLMOD_FACTORY_BO1_TELEPORT_TRAVEL");travel && std::string_view(travel)=="1") {
                    teleportResources.roomFlash=effectParameter("maps/zombie/fx_zombie_flashback_american").value_or(0);
                    teleportResources.coreChargeBeam=effectParameter("maps/zombie/fx_zombie_mainframe_beam_start").value_or(0);
                    teleportResources.coreChargeFlat=effectParameter("maps/zombie/fx_zombie_mainframe_flat_start").value_or(0);
                    teleportResources.coreBeam=effectParameter("maps/zombie/fx_zombie_mainframe_beam").value_or(0);
                    teleportResources.coreFlat=effectParameter("maps/zombie/fx_zombie_mainframe_flat").value_or(0);
                    teleportResources.travelSound=Bindings.resolveSoundAliasEventParameter("cyborg_telepoter_travel").value_or(0);
                    logGameServer("Factory BO1-DERIVED travel FX room="+std::to_string(teleportResources.roomFlash)+
                        " core="+std::to_string(teleportResources.coreBeam)+" sound="+std::to_string(teleportResources.travelSound));
                }
                teleportResources.linkSingle=effectParameter("maps/zombie/fx_zombie_mainframe_link_single").value_or(0);
                teleportResources.linkAll=effectParameter("maps/zombie/fx_zombie_mainframe_link_all").value_or(0);
                logGameServer("Factory teleport FX resolved="+std::to_string(teleportResources.padStart)+","+
                    std::to_string(teleportResources.beam)+","+std::to_string(teleportResources.linkSingle)+","+std::to_string(teleportResources.linkAll));
            }
            Server.setFactoryTeleporterResources(teleportResources);
            CodolGameServer::SvFactoryBoxResources boxResources;
            if (const auto *interact=std::getenv("OLMOD_FACTORY_INTERACTABLES");
                request->mapName=="zm_factory_sh" && request->gameType=="zm" &&
                interact && std::string_view(interact)=="1") {
                boxResources.openAnimation=Bindings.resolveAnimConfigStringIndex("codo_treasure_chest_box_open").value_or(0);
                boxResources.closeAnimation=Bindings.resolveAnimConfigStringIndex("codo_treasure_chest_box_close").value_or(0);
                const std::array<std::uint16_t,2> boxAnimations{
                    boxResources.openAnimation,boxResources.closeAnimation};
                boxResources.animationTree=Bindings.resolveScriptModelAnimationTree(boxAnimations).value_or(0);
                // Original box carriers use resident tag_origin/root and two
                // looping native definitions. Missing assets disable only FX.
                boxResources.effectModel=Bindings.resolveModelConfigStringIndex("tag_origin").value_or(0);
                boxResources.effectBone=boneIndex("tag_origin","tag_origin").value_or(255);
                boxResources.effects={
                    effectParameter("env/light/fx_ray_sun_sm_short").value_or(0),
                    effectParameter("zombie/treasure_box2").value_or(0)};
                boxResources.bearModel=Bindings.resolveModelConfigStringIndex("zombie_teddybear").value_or(0);
                boxResources.ammoModel=Bindings.resolveModelConfigStringIndex("zombie_ammocan").value_or(0);
                boxResources.relocationEffect=effectParameter("misc/fx_zombie_couch_effect").value_or(0);
                logGameServer("Factory box FX model="+std::to_string(boxResources.effectModel)+
                    " bone="+std::to_string(boxResources.effectBone)+" effects="+
                    std::to_string(boxResources.effects[0])+","+std::to_string(boxResources.effects[1]));
                // OLMOD(factory_box): offer only entries in the native dynamic
                // tail which the gamestate already published before world setup.
                // The old first-64 scan picked arbitrary low static WeaponDefs;
                // those can be gameplay-valid while resolving only a tag_origin
                // placeholder on the client. A modular record is the existing
                // client assembly contract -- this path never materializes or
                // broadcasts a new weapon for a box roll.
                const auto firstDynamic=Bindings.firstDynamicWeaponAssetIndex();
                const auto dynamicTail=firstDynamic
                    ? Bindings.readDynamicWeaponConfigStrings(*firstDynamic)
                    : std::nullopt;
                std::size_t rejected{};
                std::vector<std::uint16_t> bases;
                if(dynamicTail) {
                    bases.reserve(dynamicTail->size());
                    // Read both ends of the native definition+3720 links now.
                    // Child modes are not independent box rewards, even when
                    // their own outgoing alt pointer is zero. Do not use the
                    // process-wide cached alt table for this map's new tail.
                    std::set<std::uint16_t> alternateChildren;
                    for(std::uint32_t host=1;host<CodolGameServer::WeaponConfigStringCount;++host)
                        if(const auto alt=Bindings.altWeaponAssetIndex(host))alternateChildren.insert(alt);
                    for(std::size_t offset{};offset<dynamicTail->size();++offset) {
                        const auto asset=static_cast<std::uint32_t>(*firstDynamic+offset);
                        if(asset>=CodolGameServer::WeaponConfigStringCount) { ++rejected; continue; }
                        const auto &config=(*dynamicTail)[offset];
                        boxResources.weaponBases.emplace(static_cast<std::uint16_t>(asset),config.baseWeaponAssetIndex);
                        if(!config.baseWeaponAssetIndex ||
                            std::ranges::find(bases,config.baseWeaponAssetIndex)!=bases.end()) {
                            ++rejected;continue;
                        }
                        CodolGameServer::ClientWeaponSelection selection{};
                        if(!Bindings.readWeaponSelection(asset,selection)) { ++rejected;continue; }
                        const auto weapon=toResolvedWeapon(selection);
                        if(weapon.weaponType!=CodolGameServer::WeaponTypeBullet ||
                            !weapon.clipSize || !weapon.maxAmmo) { ++rejected;continue; }
                        CodolGameServer::SvResolvedWeapon alternate;
                        if(CodolGameServer::SV_LookupAltWeaponForHost(
                                static_cast<std::uint16_t>(asset),alternate) ||
                            alternateChildren.contains(static_cast<std::uint16_t>(asset))) {
                            logGameServer("Factory box exclude alternate asset="+std::to_string(asset));
                            ++rejected;continue;
                        }
                        bases.push_back(config.baseWeaponAssetIndex);
                        const auto center=Bindings.weaponDisplayBodyCenter(static_cast<std::uint16_t>(asset));
                        boxResources.weapons.push_back({static_cast<std::uint16_t>(asset),
                            "** "+std::to_string(config.baseWeaponAssetIndex),center.value_or(std::array<float,3>{})});
                        logGameServer("Factory box display asset="+std::to_string(asset)+
                            " bodyCenter="+(center?std::to_string((*center)[0])+","+
                                std::to_string((*center)[1]):"unavailable"));
                    }
                }
                logGameServer("Factory box resources dynamic="+
                    std::to_string(dynamicTail?dynamicTail->size():0)+
                    " playable="+std::to_string(boxResources.weapons.size())+
                    " duplicateOrRejected="+std::to_string(rejected)+
                    " firstDynamic="+std::to_string(firstDynamic.value_or(0))+
                    " animations="+std::to_string(boxResources.openAnimation)+","+
                    std::to_string(boxResources.closeAnimation)+
                    " tree="+std::to_string(boxResources.animationTree));
            }
            std::map<std::uint16_t,CodolGameServer::SvFactorySpecialKind> specialWeapons;
            std::map<std::uint16_t,CodolGameServer::SvFactorySpecialCombat> specialCombat;
            if(const auto *setting=std::getenv("OLMOD_FACTORY_RECONSTRUCTED_POOL");
                setting && std::string_view(setting)=="1" && boxResources.openAnimation) {
                // OLMOD(factory_special_reconstruction): fixed named catalogue;
                // class guns remain an explicit alternate pool, never its source.
                boxResources.reconstructedPool=true;boxResources.weapons.clear();
                boxResources.weaponBases.clear();
                for(const auto &entry:CodolGameServer::FactoryReconstructedBoxPool) {
                    if(entry.kind==CodolGameServer::SvFactorySpecialKind::Ammo)continue;
                    const auto asset=Bindings.resolveWeaponConfigStringIndex(entry.weapon);
                    if(!asset || !*asset) {logGameServer("Factory special unavailable name="+std::string(entry.weapon));continue;}
                    if(entry.equipment) {
                        const auto equipment=Bindings.resolveFactorySpecialEquipment(entry.weapon);
                        if(!equipment || equipment->weaponAssetIndex!=*asset)continue;
                        boxResources.equipment.emplace(*asset,*equipment);
                    } else {
                        CodolGameServer::ClientWeaponSelection selection{};
                        if(!Bindings.readWeaponSelection(*asset,selection) || selection.weaponType!=2)continue;
                    }
                    boxResources.weaponBases.emplace(*asset,*asset);
                    boxResources.weapons.push_back({*asset,std::string(entry.weapon),
                        Bindings.weaponDisplayBodyCenter(*asset).value_or(std::array<float,3>{}),entry.weight});
                    specialWeapons.emplace(*asset,entry.kind);
                    logGameServer("Factory special reconstruction name="+std::string(entry.weapon)+
                        " asset="+std::to_string(*asset)+" weight="+std::to_string(entry.weight));
                }
                logGameServer("Factory special reconstruction eligible="+std::to_string(specialWeapons.size())+
                    " ammoWeight=15; weights renormalized, not original CODOL odds");
            }
            if(boxResources.reconstructedPool) {
                // OLMOD(factory_offhand_continuation): only resident, validated
                // offhands are admitted; this does not change FFA's dispatch.
                using Kind=CodolGameServer::SvFactorySpecialKind;
                for(const auto &[name,kind]:std::array{
                    std::pair{"frag_grenade_mp",Kind::Grenade},std::pair{"fragshort_grenade_mp",Kind::Grenade},
                    std::pair{"semtex_mp",Kind::Grenade},std::pair{"flash_grenade_mp",Kind::Flash},
                    std::pair{"concussion_grenade_mp",Kind::Flash},std::pair{"emp_grenade_mp",Kind::Flash},
                    std::pair{"smoke_grenade_mp",Kind::Smoke}}) {
                    const auto asset=Bindings.resolveWeaponConfigStringIndex(name);
                    if(!asset || !Bindings.resolveGrenadeLaunchParameters(*asset))continue;
                    const auto blast=Bindings.resolveGrenadeBlastParameters(*asset);
                    if(kind==Kind::Grenade && !blast)continue;
                    specialWeapons.emplace(*asset,kind);
                    specialCombat.emplace(*asset,blast ? CodolGameServer::SvFactorySpecialCombat{
                        static_cast<float>(blast->radius),blast->innerDamage,blast->outerDamage,blast->traceAlongContact} :
                        CodolGameServer::SvFactorySpecialCombat{250,0,0,false});
                    logGameServer("Factory offhand ready name="+std::string(name)+" asset="+std::to_string(*asset));
                }
                // Class equipment can be a named variant rather than the base
                // grenade above. Admit only supported families and validate the
                // variant's own native launch/blast fields; never replace its ID.
                std::map<std::uint16_t,std::string> equippedNames;
                {
                    const std::lock_guard loadoutLock(LoadoutMutex);
                    for(const auto &[xuid,member]:RegisteredSessionAssets.members())
                        for(const auto &[loadout,equipment]:member.offhands)
                            for(const auto &weapon:equipment.weapons)
                                if(weapon.weaponAssetIndex)
                                    equippedNames.emplace(weapon.weaponAssetIndex,weapon.weaponName);
                }
                for(const auto &[asset,name]:equippedNames) {
                    if(specialWeapons.contains(asset))continue;
                    std::optional<Kind> kind;
                    if(name.find("frag")!=std::string::npos || name.find("semtex")!=std::string::npos)kind=Kind::Grenade;
                    else if(name.find("flash")!=std::string::npos || name.find("concussion")!=std::string::npos ||
                        name.find("emp_grenade")!=std::string::npos)kind=Kind::Flash;
                    else if(name.find("smoke")!=std::string::npos)kind=Kind::Smoke;
                    const auto launch=Bindings.resolveGrenadeLaunchParameters(asset);
                    const auto blast=Bindings.resolveGrenadeBlastParameters(asset);
                    if(!kind || !launch || (*kind==Kind::Grenade && !blast)) {
                        logGameServer("Factory offhand unsupported name="+name+" asset="+std::to_string(asset));
                        continue;
                    }
                    specialWeapons.emplace(asset,*kind);
                    specialCombat.emplace(asset,blast ? CodolGameServer::SvFactorySpecialCombat{
                        static_cast<float>(blast->radius),blast->innerDamage,blast->outerDamage,blast->traceAlongContact} :
                        CodolGameServer::SvFactorySpecialCombat{250,0,0,false});
                    logGameServer("Factory offhand variant ready name="+name+" asset="+std::to_string(asset));
                }
            }
            CodolGameServer::SvFactoryTrapFx trapFx;
            if(boxResources.reconstructedPool)trapFx={boxResources.effectModel,boxResources.effectBone,{
                    effectParameter("maps/zombie/fx_zombie_fire_trap_med_sh").value_or(0),
                    effectParameter("maps/zombie/fx_freeze_trap_active_loop").value_or(0),
                    effectParameter("maps/zombie/fx_zombie_wire_spark").value_or(0),
                    effectParameter("maps/zombie/fx_zombie_shrink_trap_looping").value_or(0)}};
            if(boxResources.reconstructedPool) {
                trapFx.monkeyModel=Bindings.resolveModelConfigStringIndex("weapon_zombie_monkey_bomb").value_or(0);
                trapFx.monkeyAnimation=Bindings.resolveAnimConfigStringIndex("o_monkey_bomb").value_or(0);
                const std::array<std::uint16_t,1> monkeyAnimations{trapFx.monkeyAnimation};
                if(trapFx.monkeyAnimation)
                    trapFx.monkeyTree=Bindings.resolveScriptModelAnimationTree(monkeyAnimations).value_or(0);
                trapFx.monkeySong=Bindings.resolveSoundAliasEventParameter("zmb_monkey_song").value_or(0);
                logGameServer("Factory monkey model="+std::to_string(trapFx.monkeyModel)+
                    " anim="+std::to_string(trapFx.monkeyAnimation)+" tree="+std::to_string(trapFx.monkeyTree)+
                    " song="+std::to_string(trapFx.monkeySong));
            }
            Server.setFactorySpecialWeapons(std::move(specialWeapons),std::move(specialCombat),trapFx);
            if(boxResources.reconstructedPool) {
                const std::array names{"maps/zombie/fx_zombie_tesla_tube_view",
                    "maps/zombie/fx_zombie_tesla_tube_view2","maps/zombie/fx_zombie_tesla_tube_view3"};
                for(std::size_t i=0;i<names.size();++i)
                    boxResources.teslaViewEffects[i]=effectParameter(names[i]).value_or(0);
            }
            Server.setFactoryBoxResources(std::move(boxResources));
            Server.setZmPresentation(zmOutfits,zmDeaths,zmDeathFx);
            logGameServer("ZM presentation preview outfits="+std::to_string(zmOutfits.size())+
                " deaths="+std::to_string(zmDeaths.size())+" reconstructed-selection=1");

            const auto zmAttackAnim = Bindings.resolveAnimConfigStringIndex(
                CodolGameServer::SvActorAttackAnimName);
            Server.setZmActorAttackAnim(zmAttackAnim.value_or(std::uint16_t{}));
            // THE ZOMBIE SUBSET OF THE ANIMATION BAND, ONCE PER WORLD SPAWN.
            //
            // Per-state selection has to be built from names this engine actually
            // holds, and this is the only place that list exists. One pass over 4096
            // configstrings at map load, filtered to `zombie` and capped, so it cannot
            // become the per-frame scan section 119q is about.
            {
                const auto animBand = Bindings.animConfigStringBand();
                // Explicit, bounded map-load audit. Never poll asset metadata or
                // emit marker logs from the actor tick (lag-sensitive path).
                const auto *notifyAudit = std::getenv("OLMOD_ZM_NOTIFY_AUDIT");
                if (request->mapName == "zm_factory_sh" && notifyAudit &&
                    std::string_view(notifyAudit) == "1")
                {
                    std::size_t inspected{};
                    for (const auto &[index, name] : animBand)
                    {
                        if (!(name.starts_with("ai_zombie_boardtear_l_") ||
                              name.starts_with("ai_zombie_boardtear_m_") ||
                              name.starts_with("ai_zombie_boardtear_r_")))
                            continue;
                        if (inspected++ >= 18u)
                            break;
                        const auto markers = Bindings.animationNotifyTimes(name);
                        logGameServer("ZMNOTIFY clip=" + name + " key=" +
                            std::to_string(index) + " count=" +
                            (markers ? std::to_string(markers->size()) : "unavailable"));
                        if (!markers)
                            continue;
                        for (const auto &[id, seconds] : *markers)
                        {
                            const auto markerName = Bindings.animationNotifyName(id);
                            logGameServer("ZMNOTIFY marker clip=" + name +
                                " id=" + std::to_string(id) + " seconds=" +
                                std::to_string(seconds) + " name=" +
                                markerName.value_or("unresolved"));
                        }
                    }
                }
                std::vector<std::string> zmAnimNames;
                for (const auto &[index, name] : animBand)
                {
                    if (name.find("zombie") != std::string::npos)
                        zmAnimNames.push_back(std::to_string(index) + "=" + name);
                }
                logGameServer(
                    "zm animband map=" + request->mapName +
                    " total=" + std::to_string(animBand.size()) +
                    " zombie=" + std::to_string(zmAnimNames.size()) +
                    " tearAnim=" + (zmTearAnim ? std::to_string(*zmTearAnim)
                                               : std::string("UNRESOLVED")));
                // CHUNKED, NOT TRUNCATED. The first cut capped at 96 and the band
                // holds 427, so the names that matter -- walk, attack, death, taunt --
                // fell off the end and cost a cycle. 64 per line keeps each record
                // readable without losing any of it.
                for (std::size_t first = 0; first < zmAnimNames.size(); first += 64u)
                {
                    std::string chunk;
                    for (std::size_t at = first;
                         at < zmAnimNames.size() && at < first + 64u; ++at)
                    {
                        chunk += " " + zmAnimNames[at];
                    }
                    logGameServer(
                        "zm animband part=" + std::to_string(first / 64u) + chunk);
                }
            }
            logGameServer(
                "zm navgraph map=" + request->mapName +
                " table=" + (zmNavTable ? "yes" : "none") +
                " nodes=" + std::to_string(zmNavNodes) +
                " edges=" + std::to_string(zmNavEdges) +
                " source=" + (navSource == CodolGameServer::SvZmNavSource::Bo1Hybrid
                    ? "bo1_hybrid" : "codol_recovered") +
                " referenceNodes=" + std::to_string(zmNavGraph.referenceNodes) +
                " referenceEdges=" + std::to_string(zmNavGraph.referenceEdgesAccepted) +
                "/" + std::to_string(zmNavGraph.referenceEdgesConsidered) +
                // How many negotiation edges got a playable animation. Expect all 53
                // on Factory: the demo identifies `zombie_mantle_over_40` as the
                // slow `ai_zombie_traverse_v6` sequence.
                " vaults=" + std::to_string(zmNavVaults) +
                " walkAnim=" + (zmWalkAnim ? std::to_string(*zmWalkAnim)
                                           : std::string("UNRESOLVED, keeping 476")) +
                // The one line that matters when zombies do not move: a table that
                // exists but a graph that does not means the loaded map's nodes did
                // not match it, and every actor will park.
                (zmNavTable && zmNavNodes == 0
                     ? " REJECTED (map nodes do not match the table)"
                     : ""));
        }

        // An add-on campaign map owns its map entities in a separate fastfile.
        // Those entities can name XModels which are resident in the add-on but
        // absent from the base multiplayer model configstring band. The client
        // still needs a band index for every script_model we publish. Reserve
        // empty slots before resolving the entity list so the existing live model
        // publisher can assign and precache those campaign models. Wetwork has
        // eight unique script-model names; sixteen leaves room for the roster's
        // body and hands while keeping this bounded like the existing outfit path.
        {
            const auto band = Bindings.modelConfigStringBand();
            std::set<std::uint16_t> used;
            for (const auto &[index, name] : band)
                used.insert(index);
            std::vector<std::uint16_t> free;
            for (std::uint16_t index = 1;
                 index < CodolGameServer::ModelConfigStringCount &&
                     free.size() < 16;
                 ++index)
            {
                if (!used.contains(index))
                    free.push_back(index);
            }
            Server.setOutfitModelSlots(std::move(free));
        }
        std::optional<CodolGameServer::SvSdBombPickup> sdBombPickup;
        if (request->gameType == "sd")
        {
            const auto bombSites =
                CodolGameServer::SV_SelectSdBombSites(*entities);
            const auto bombPickup =
                CodolGameServer::SV_SelectSdBombPickup(*entities);
            if (!bombSites || !bombPickup)
            {
                reportFailure("sd_bomb_object_select");
                return;
            }
            sdBombPickup = *bombPickup;
            const auto pickupCollision =
                Bindings.resolveBrushModelCollision(bombPickup->triggerModel);
            if (!pickupCollision)
            {
                reportFailure("sd_bomb_pickup_resolve");
                return;
            }
            const CodolGameServer::SvTriggerVolume pickupTrigger{
                .objectId = bombPickup->triggerModel,
                .origin = bombPickup->triggerOrigin,
                .collision = *pickupCollision,
            };
            std::vector<CodolGameServer::SvSdBombSiteRuntime> siteRuntime;
            siteRuntime.reserve(bombSites->size());
            for (const auto &site : *bombSites)
            {
                const auto plantCollision =
                    Bindings.resolveBrushModelCollision(site.triggerModel);
                const auto defuseCollision =
                    Bindings.resolveBrushModelCollision(site.defuseTriggerModel);
                if (!plantCollision || !defuseCollision)
                {
                    reportFailure("sd_bomb_trigger_resolve_" + site.label);
                    return;
                }
                siteRuntime.push_back({
                    .label = site.label,
                    .plantTrigger = {
                        .objectId = site.triggerModel,
                        .origin = site.origin,
                        .angles = site.angles,
                        .collision = *plantCollision,
                    },
                    .defuseTrigger = {
                        .objectId = site.defuseTriggerModel,
                        .origin = site.defuseOrigin,
                        .angles = site.defuseAngles,
                        .collision = *defuseCollision,
                    },
                });
            }
            if (!Server.configureSdBombRuntime(
                    *bombSites, pickupTrigger, siteRuntime))
            {
                reportFailure("sd_bomb_runtime_commit");
                return;
            }
        }
        std::vector<CodolGameServer::SvBrushModelEntityDefinition> brushModels;
        brushModels.reserve(brushSpawns->size());
        std::size_t activeBrushModels{};
        for (const auto &brushSpawn : *brushSpawns)
        {
            const auto collision =
                Bindings.resolveBrushModelCollision(brushSpawn.clipHandle);
            if (!collision)
            {
                reportFailure(
                    "brush_resolve_" +
                    std::to_string(brushSpawn.clipHandle));
                return;
            }
            // OLMOD(entity-publication-bootstrap): this combines current map
            // eligibility with recovered serializer coverage. It is not the
            // missing CODOL gentity in-use/SVF_NOCLIENT producer.
            const auto gameplayActive =
                brushSpawn.regularMultiplayerEligible &&
                brushSpawn.scriptGameObjectName.empty();
            brushModels.push_back({
                .mapOrdinal = brushSpawn.mapOrdinal,
                .walkEntityNum = brushSpawn.walkEntityNum,
                .origin = brushSpawn.origin,
                .angles = brushSpawn.angles,
                .collision = *collision,
                .scriptGameObjectName = brushSpawn.scriptGameObjectName,
                .targetName = brushSpawn.targetName,
                .destructibleType = brushSpawn.destructibleType,
                .mapModeEligible = brushSpawn.regularMultiplayerEligible,
                .gameplayActive = gameplayActive,
            });
            activeBrushModels += gameplayActive ? 1 : 0;
        }
        std::vector<CodolGameServer::SvScriptModelEntityDefinition> scriptModels;
        scriptModels.reserve(scriptModelSpawns->size());
        std::vector<CodolGameServer::SvScriptModelDamageOwnerDefinition>
            scriptModelDamageOwners;
        std::size_t activeScriptModels{};
        for (const auto &scriptModelSpawn : *scriptModelSpawns)
        {
            auto modelIndex = Bindings.resolveModelConfigStringIndex(
                scriptModelSpawn.modelName);
            if (!modelIndex)
            {
                modelIndex = Server.registerOutfitModelConfigString(
                    scriptModelSpawn.modelName);
            }
            if (!modelIndex)
            {
                reportFailure(
                    "script_model_index_" + scriptModelSpawn.modelName);
                return;
            }
            // OLMOD(entity-publication-bootstrap): see shouldArchiveWorldEntity.
            // This is a source policy boundary, not recovered CODOL visibility.
            const auto gameplayActive =
                scriptModelSpawn.regularMultiplayerEligible &&
                scriptModelSpawn.scriptGameObjectName.empty();
            scriptModels.push_back({
                .mapOrdinal = scriptModelSpawn.mapOrdinal,
                .walkEntityNum = scriptModelSpawn.walkEntityNum,
                .origin = scriptModelSpawn.origin,
                .angles = scriptModelSpawn.angles,
                .modelIndex = *modelIndex,
                .modelName = scriptModelSpawn.modelName,
                .scale = scriptModelSpawn.scale,
                .scriptGameObjectName = scriptModelSpawn.scriptGameObjectName,
                .targetName = scriptModelSpawn.targetName,
                .destructibleType = scriptModelSpawn.destructibleType,
                .mapModeEligible =
                    scriptModelSpawn.regularMultiplayerEligible,
                .gameplayActive = gameplayActive,
                .noteworthy = scriptModelSpawn.noteworthy,
            });
            const auto *const destructible = gameplayActive
                ? CodolGameServer::SV_FindIw4DestructibleDefinition(
                      scriptModelSpawn.destructibleType)
                : nullptr;
            if (destructible)
            {
                auto presentation =
                    CodolGameServer::SV_ResolveDestructiblePresentation(
                        *destructible,
                        [](const std::string_view modelName) {
                            return Bindings.resolveModelConfigStringIndex(
                                modelName);
                        });
                const auto initialState =
                    CodolGameServer::SV_InitializeDestructibleDamageState(
                        *destructible);
                if (!initialState || !presentation)
                {
                    reportFailure(
                        "destructible_owner_" +
                        std::string(destructible->type));
                    return;
                }
                scriptModelDamageOwners.push_back({
                    .scriptModelIndex = scriptModels.size() - 1,
                    .state = *initialState,
                    .handler = [destructible, presentation =
                                    std::move(*presentation)](
                                   const CodolGameServer::SvEntityDamagePayload
                                       &payload,
                                   const CodolGameServer::SvEntityDamageState
                                       &state,
                                   const std::uint16_t modelIndex) {
                        return CodolGameServer::SV_ApplyDestructibleEntityDamage(
                            *destructible,
                            presentation,
                            payload,
                            state,
                            modelIndex);
                    },
                });
            }
            activeScriptModels += gameplayActive ? 1 : 0;
        }
        // THE END-OF-MATCH CAMERA IS A MAP ENTITY (section 121). Absent is not
        // an error -- a map with no `top_players_camera` keeps the pm_type-only
        // intermission it had before -- so this logs which it was and moves on.
        auto topPlayersCamera =
            CodolGameServer::SV_SelectTopPlayersCamera(*entities);
        if (topPlayersCamera)
        {
            Server.setTopPlayersCamera(CodolGameServer::SvWorldSpawnPoint{
                .origin = topPlayersCamera->origin,
                .angles = topPlayersCamera->angles,
            });
            logGameServer(
                "top_players_camera " + std::string(request->mapName) +
                " origin " + std::to_string(topPlayersCamera->origin[0]) + "," +
                std::to_string(topPlayersCamera->origin[1]) + "," +
                std::to_string(topPlayersCamera->origin[2]) + " angles " +
                std::to_string(topPlayersCamera->angles[0]) + "," +
                std::to_string(topPlayersCamera->angles[1]) + "," +
                std::to_string(topPlayersCamera->angles[2]));
        }
        else
        {
            Server.setTopPlayersCamera(std::nullopt);
            logGameServer(
                "no top_players_camera in " + std::string(request->mapName) +
                " -- the end-of-match view will not move");
        }
        {
            auto places = CodolGameServer::SV_SelectTopPlayersPlaces(*entities);
            std::vector<CodolGameServer::SvWorldSpawnPoint> podiumPlaces;
            for (const auto &place : places)
            {
                podiumPlaces.push_back(CodolGameServer::SvWorldSpawnPoint{
                    .origin = place.origin,
                    .angles = place.angles,
                });
            }
            logGameServer(
                "top_players_loc " + std::string(request->mapName) + " places=" +
                std::to_string(podiumPlaces.size()));
            Server.setTopPlayersPlaces(std::move(podiumPlaces));
        }
        // WHAT BASE MODELS DOES THIS MAP ACTUALLY OFFER? Section 124 records
        // that retail's shared podium model index 121 cannot be ported -- an
        // index addresses the ENGINE's per-map band -- so the podium has to pick
        // by NAME, and nothing had ever looked at what names are on offer. One
        // pass, at map load, logged in full so the choice is made from evidence.
        {
            const auto band = Bindings.modelConfigStringBand();
            std::string sample;
            std::size_t characters{};
            for (const auto &[index, name] : band)
            {
                // The character families, by the slot prefixes section 67 named:
                // cha fpa boo fja han hea ves heg.
                const auto isCharacter =
                    name.rfind("fpa_", 0) == 0 || name.rfind("cha_", 0) == 0 ||
                    name.rfind("boo_", 0) == 0 || name.rfind("fja_", 0) == 0 ||
                    name.rfind("han_", 0) == 0 || name.rfind("hea_", 0) == 0 ||
                    name.rfind("ves_", 0) == 0 || name.rfind("heg_", 0) == 0;
                if (!isCharacter)
                    continue;
                ++characters;
                if (sample.size() < 1200)
                    sample += " " + std::to_string(index) + ":" + name;
            }
            // THE GENERIC BODY. mp_rust_long publishes exactly one model per
            // character slot at indices 2..6 -- boo/fja/fpa/han/hea -- which is
            // the map's own default character. The `fpa_` one is the body, and
            // it is what a podium figure falls back to when the band does not
            // publish that player's own (section 125).
            for (const auto &[index, name] : band)
            {
                if (name.rfind("fpa_", 0) != 0)
                    continue;
                Server.setPodiumFallbackModel(index, name);
                logGameServer(
                    "podium fallback body " + std::to_string(index) + ":" + name);
                break;
            }
            logGameServer(
                "model band " + std::string(request->mapName) + " entries=" +
                std::to_string(band.size()) + " characterModels=" +
                std::to_string(characters) + sample);
            // Empty model slots were reserved before script-model resolution so
            // add-on campaign entities and roster cosmetics share one collision-
            // free allocation pool.
            // AND PUBLISH EVERY ROSTERED CHARACTER'S BODY MODEL RIGHT HERE, INTO THE
            // GAMESTATE. Section 168.
            //
            // The body model at clientState +0x14 is only useful if the client can
            // RESOLVE that index, and it resolves it through configstring
            // 2568 + index. Registering it from the customization provider publishes it
            // LIVE, after every client already holds its gamestate -- so a client only
            // learns it from a reliable command arriving while it is loading a map, and
            // one measurably does not end up with it: the wire carried body418 in every
            // write to both observers, `cs 2986 fpa_goose_ss_m_15` is in one client's
            // demo, and the other still wrote an EMPTY model name.
            //
            // This runs during world configuration, BEFORE gameStateConfigured_ lets any
            // gamestate go out, so the band entry is part of the gamestate every client
            // receives and there is no live delivery to miss. The outfit comment next
            // door already said the real answer was "a GAMESTATE change, not a per-spawn
            // one"; this is that.
            {
                const std::lock_guard lock(LoadoutMutex);
                std::set<std::string> published;
                for (const auto &[memberXuid, member] :
                    RegisteredSessionAssets.members())
                {
                    const auto &presentation = member.characterPresentation;
                    if (presentation.characterItemId == 0)
                        continue;
                    CodolGameServer::SvCharacterCustomization probe{};
                    probe.characterItemId = presentation.characterItemId;
                    probe.recordItemIds = presentation.recordItemIds;
                    probe.recordItemIds[0] = probe.characterItemId;
                    // THE BODY AND THE HANDS. `han_` is the character's own viewhands
                    // and mp_nuked does not publish it -- `viewhands: character hands
                    // NOT IN BAND name=han_infbasea_tf_m_00` -- which is the only
                    // reason a player still wears tf141's. Same band, same gamestate,
                    // same two-step; nothing about it is body-specific.
                    for (const auto &name :
                        Bindings.characterResolvedModelNames(probe))
                    {
                        const auto isBody = name.rfind("fpa_", 0) == 0;
                        const auto isHands = name.rfind("han_", 0) == 0;
                        if (!isBody && !isHands)
                            continue;
                        if (published.contains(name))
                            continue;
                        published.insert(name);
                        if (Bindings.resolveModelConfigStringIndex(name))
                            continue;   // the map already publishes it
                        const auto index =
                            Server.registerOutfitModelConfigString(name);
                        logGameServer(
                            std::string("character ") +
                            (isBody ? "body" : "hands") +
                            " published INTO THE GAMESTATE name=" + name +
                            (index ? " index=" + std::to_string(*index)
                                   : std::string{ " -- NO BAND SLOT" }) +
                            " xuid=" + std::to_string(memberXuid));
                    }
                }
            }
        }
        // NO ACTOR-MODEL PUBLISH HERE. Two attempts, both of which broke the
        // session -- see re/demo-re/20-zm-actor-lifecycle.md 12.21/12.22.
        //
        // 1. Publishing at first-zombie-spawn: a LIVE configstring change after
        //    clients hold their gamestate. Client could not enter at all
        //    (无法加入游戏会话), reproduced twice.
        // 2. Publishing here at world configuration, driven off the map's own
        //    actor_* entities: the client TIMED OUT a few seconds in
        //    (`client timeout ... last_packet=`, snapshots stopped at 141).
        //    AND IT PUBLISHED THE WRONG MODELS. The map's actor entities name
        //    c_zom_juggernaut_body_RED, c_zom_ger_body_YEL and zombie_wolf --
        //    only zombie_wolf is even in the dedicated band (index 409) -- while
        //    zm.lua spawns c_zom_ger_body1 (index 308), which is NOT named by any
        //    actor_* entity. So the map entities are the wrong source for this.
        //
        // The client still needs the index published (its band is whatever the
        // SERVER transmits), so this is unfinished, not abandoned. Whatever does
        // it must publish the model the SCRIPT actually spawns, at the index the
        // dedicated resolved, before gameStateConfigured_ -- and the `|` precache
        // needs re-examining, since forcing an XModel load is the prime suspect
        // for the timeout.

        // Warm the script-selected Factory appearance lookups during map setup,
        // without publishing or changing a configstring. Both names already live
        // in this map's model band; this only fills the resolver's validated hints
        // so the first live spawn does not perform the 1023-slot scans.
        if (request->gameType == "zm")
        {
            for (const auto name : {
                     std::string_view{ "c_zom_ger_body_blue" },
                     std::string_view{ "c_zom_ger_head" } })
            {
                const auto index = Bindings.resolveModelConfigStringIndex(name);
                logGameServer(
                    "zm actor model lookup primed name=" + std::string(name) +
                    (index ? " index=" + std::to_string(*index)
                           : std::string{ " -- NOT IN CURRENT MODEL BAND" }));
            }
        }

        auto modeSpawns = CodolGameServer::SV_SelectModeSpawnPoints(
            *entities, request->gameType);
        // OLMOD(factory-arrival-selection): opt-in Factory route only. Use its
        // authored platform points, then the existing native capsule ground
        // trace and atomic ClientSpawn (including usercmd-relative view yaw).
        // Connection parking remains separate; no live teleport/input writer.
        const auto entryFlag = std::getenv("OLMOD_FACTORY_ENTRY");
        const bool factoryArrivalSpawns = request->gameType == "zm" &&
            request->mapName == "zm_factory_sh" && entryFlag &&
            std::string_view(entryFlag) == "1";
        if (factoryArrivalSpawns)
        {
            modeSpawns = CodolGameServer::SV_SelectFactoryArrivalSpawns(*entities);
            if (!modeSpawns)
            {
                reportFailure("factory_arrival_spawn_records");
                return;
            }
            logGameServer("Factory arrival uses authored initial_spawn_points; native ground trace follows");
        }
        auto connectionSpawn =
            CodolGameServer::SV_SelectConnectionSpawn(*entities);
        if (!modeSpawns)
        {
            reportFailure("initial_spawn_select");
            return;
        }
        if (!connectionSpawn && !modeSpawns->empty())
        {
            // Not every CODOL MP map ships an info_player_start - mp_estate_tropical
            // does not, and the search-and-destroy maps that do are the only ones
            // this path had ever been run against. The connection spawn is just
            // where a client is parked before it spawns for real, so any valid
            // point serves; refusing the whole map for want of one classname does
            // not.
            connectionSpawn = modeSpawns->front().spawn;
            logGameServer(
                "no info_player_start in " + std::string(request->mapName) +
                ", parking connections on " + connectionSpawn->className);
        }
        if (!connectionSpawn)
        {
            reportFailure("connection_spawn_select");
            return;
        }
        // Report what the map actually offered and which class the selection came
        // from. The base MP entity strings are in none of the shipped fastfiles,
        // so this is the only place the real spawn classnames can be observed.
        {
            std::string census;
            for (const auto &[className, count] :
                 CodolGameServer::SV_SpawnClassNameCensus(*entities))
            {
                if (!census.empty())
                    census += ", ";
                census += className + " x" + std::to_string(count);
            }
            std::string chosen;
            for (const auto &modeSpawn : *modeSpawns)
            {
                if (chosen.find(modeSpawn.spawn.className) == std::string::npos)
                    chosen += (chosen.empty() ? "" : ",") + modeSpawn.spawn.className;
            }
            logGameServer(
                "map spawn classes " + std::string(request->mapName) + " " +
                std::string(request->gameType) + ": " +
                (census.empty() ? "(none)" : census) + " | selected " +
                std::to_string(modeSpawns->size()) + " from " +
                (chosen.empty() ? "(none)" : chosen));
        }

        std::vector<CodolGameServer::SvWorldSpawnPoint> worldSpawnPoints;
        worldSpawnPoints.reserve(modeSpawns->size());
        std::size_t rejectedSpawns{};
        for (auto &modeSpawn : *modeSpawns)
        {
            auto traceEnd = modeSpawn.spawn.origin;
            traceEnd[2] -= SpawnGroundTraceDistance;
            const auto trace = Bindings.traceCapsule(
                modeSpawn.spawn.origin,
                traceEnd,
                CodolGameServer::StandingPlayerTraceBounds,
                0,
                CodolGameServer::PlayerCollisionContentMask);
            if (!trace || trace->fraction >= 1.0f || trace->allSolid ||
                trace->startSolid || !trace->walkable ||
                trace->hitId != CodolGameServer::EntityNumWorld)
            {
                // A single unusable point used to abort the whole world spawn, so
                // free-for-all never spawned anyone: sd ships two small hand-placed
                // sets that all pass, while a dm pool is an order of magnitude
                // larger and only needs one point over a gap or inside geometry to
                // take the entire match down with it.
                //
                // Drop the point instead. The set is a pool to pick from, not a
                // contract that every entry is standable, and requiring all of them
                // made the strictest possible reading of it fatal.
                ++rejectedSpawns;
                continue;
            }
            for (std::size_t index = 0;
                 index < modeSpawn.spawn.origin.size();
                 ++index)
            {
                modeSpawn.spawn.origin[index] +=
                    (traceEnd[index] - modeSpawn.spawn.origin[index]) *
                    trace->fraction;
            }
            const auto team = [spawnTeam = modeSpawn.team] {
                switch (spawnTeam)
                {
                case CodolGameServer::SvSpawnTeam::Tf:
                    return CodolGameServer::SvTeam::Tf;
                case CodolGameServer::SvSpawnTeam::Sc:
                    return CodolGameServer::SvTeam::Sc;
                case CodolGameServer::SvSpawnTeam::Any:
                    return CodolGameServer::SvTeam::None;
                }
                return CodolGameServer::SvTeam::None;
            }();
            worldSpawnPoints.push_back({
                .origin = modeSpawn.spawn.origin,
                .angles = modeSpawn.spawn.angles,
                .team = team,
            });
            if (factoryArrivalSpawns)
                logGameServer("Factory arrival grounded origin=" +
                    std::to_string(modeSpawn.spawn.origin[0]) + "," +
                    std::to_string(modeSpawn.spawn.origin[1]) + "," +
                    std::to_string(modeSpawn.spawn.origin[2]) + " yaw=" +
                    std::to_string(modeSpawn.spawn.angles[1]));
        }
        if (rejectedSpawns)
        {
            // Never silently: a pool quietly shrinking to a handful of points is
            // a spawn-camping bug that would present as bad map design.
            logGameServer(
                "spawn points rejected by the ground trace: " +
                std::to_string(rejectedSpawns) + " of " +
                std::to_string(modeSpawns->size()) + " map=" +
                std::string(request->mapName));
        }
        if (worldSpawnPoints.empty())
        {
            reportFailure("initial_spawn_ground_trace");
            return;
        }
        // WHAT WEAPON IS EACH INDEX? OLMOD_DUMP_WEAPON_BAND=1.
        //
        // Retail BattleCity does NOT spawn you empty-handed: the footage shows bare
        // hands holding a HAMMER, which is why the hands are drawn at all -- weapon
        // index 0 has no viewmodel, so "no weapon" and "no hands" are the same state.
        // Finding the melee index means reading the band rather than guessing, and the
        // obvious guess was already wrong once: 1148 looked like a melee slot because
        // it sat just under the loot values and carried no ammo, but the captured loot
        // band lists it at cs 12616, so it is lootable like the rest.
        //
        // Same shape as the model dump below: index first so the output greps, and the
        // absolute weapon asset index printed alongside so it can be pasted straight
        // into a loadout or a loot table.
        if (const auto *const dumpWeapons = std::getenv("OLMOD_DUMP_WEAPON_BAND");
            dumpWeapons && dumpWeapons[0] == '1')
        {
            std::size_t published{};
            for (std::uint16_t index = 1;
                 index < CodolGameServer::WeaponConfigStringCount; ++index)
            {
                const auto *const name = Bindings.nativeConfigString(
                    CodolGameServer::WeaponConfigStringBase + index);
                if (!name || name[0] == '\0')
                    continue;
                ++published;
                logGameServer(
                    "weapon band [" + std::to_string(index) + "] " + name);
            }
            logGameServer(
                "weapon band total=" + std::to_string(published) + " map=" +
                std::string(request->mapName) + " gametype=" +
                std::string(request->gameType));
        }
        // WHAT MODELS CAN A SCRIPT ACTUALLY PLACE? OLMOD_DUMP_MODEL_BAND=1.
        //
        // `spawnmodel` and `setmodelat` both go through
        // resolveModelConfigStringIndex, which only accepts a name the map's model
        // configstring band ALREADY publishes -- it walks 2568+1 .. 2568+1023 looking
        // for an exact string match and returns nullopt otherwise. A loot script
        // therefore cannot invent a model name; it has to pick from this list, and
        // until it is dumped nobody knows what is on it for a given map.
        //
        // Printed here rather than at gamestate build because this is the moment the
        // band is complete: the map's own assets are registered and the script is about
        // to load. One line per entry, index first, so the output greps.
        if (const auto *const dumpBand = std::getenv("OLMOD_DUMP_MODEL_BAND");
            dumpBand && dumpBand[0] == '1')
        {
            std::size_t published{};
            for (std::uint16_t index = 1;
                 index < CodolGameServer::ModelConfigStringCount; ++index)
            {
                const auto *const name = Bindings.nativeConfigString(
                    CodolGameServer::ModelConfigStringBase + index);
                if (!name || name[0] == '\0')
                    continue;
                ++published;
                logGameServer(
                    "model band [" + std::to_string(index) + "] " + name);
            }
            logGameServer(
                "model band total=" + std::to_string(published) + " map=" +
                std::string(request->mapName) + " gametype=" +
                std::string(request->gameType));
        }
        const auto logicalMapEntities =
            CodolGameServer::SV_SelectLogicalMapEntities(*entities);
        if (!logicalMapEntities)
        {
            reportFailure("logical_map_entity_parse");
            return;
        }
        logGameServer(
            "logical map entities map=" + request->mapName +
            " count=" + std::to_string(logicalMapEntities->size()));
        if (!Server.configureWorldSpawn(
                worldSpawnPoints,
                brushModels,
                scriptModels,
                scriptModelDamageOwners,
                CodolGameServer::SvWorldSpawnPoint{
                    .origin = connectionSpawn->origin,
                    .angles = connectionSpawn->angles,
                },
                request->mapName,
                request->gameType,
                *logicalMapEntities))
        {
            reportFailure("world_commit");
            return;
        }

        // EMPTY HANDS ARE A WEAPON. Resolved here because this is where the
        // weapon band is live and the asset owner is reachable; the mode decision
        // itself was made at gametype configure. `dmz_empty_mp` sits at 1137 on
        // mp_battlecity, in the dmz cluster next to dmz_gas_mp and dmzhealneedle_mp,
        // but it is looked up BY NAME because the band is per-map.
        if (request->gameType == "dmz")
        {
            constexpr std::string_view EmptyHandsWeapon = "dmz_empty_mp";
            const auto emptyHands =
                Bindings.resolveWeaponConfigStringIndex(EmptyHandsWeapon);
            if (emptyHands)
            {
                Server.setUnarmedSpawnWeapon(*emptyHands);
                logGameServer(
                    "dmz empty hands weapon " + std::string(EmptyHandsWeapon) +
                    " = " + std::to_string(*emptyHands));
            }
            else
            {
                // Not fatal: the spawn falls back to index 0, which is armless but
                // still unarmed. Say so, because "no hands" is the symptom.
                logGameServer(
                    "dmz empty hands weapon " + std::string(EmptyHandsWeapon) +
                    " NOT FOUND in the weapon band -- spawning with index 0, which "
                    "draws no viewmodel and so no hands");
            }
        }

        const auto script = CodolGameServer::SV_LoadGameplaySource(
            gameplayScriptRoot(), request->mapName, request->gameType);
        if (!script.succeeded())
        {
            logGameServer(
                "gameplay script unavailable map=" + request->mapName +
                " gametype=" + request->gameType + " error=" +
                std::string(CodolGameServer::SV_GameplaySourceLoadErrorName(
                    script.error)) + " detail=" + script.detail);
        }
        else if (!Server.loadGameplayScript(
                     script.gameplaySource.sourceName,
                     script.gameplaySource.source))
        {
            logGameServer(
                "gameplay script rejected map=" + request->mapName +
                " gametype=" + request->gameType);
        }
        else
        {
            const auto scriptStatus = Server.gameplayScriptStatus();
            const auto brushStatus = Server.worldBrushModelActivationStatus();
            std::string files;
            for (const auto &file : script.gameplaySource.files)
            {
                if (!files.empty())
                    files.push_back(',');
                files.append(file);
            }
            logGameServer(
                "gameplay script loaded generation=" +
                std::to_string(scriptStatus.generation) + " source=" +
                scriptStatus.sourceName + " files=" + files +
                " brushModels=" + std::to_string(brushStatus.total) +
                " taggedBrushModels=" + std::to_string(brushStatus.tagged) +
                " activeBrushModels=" + std::to_string(brushStatus.active));
        }
        drainGameplayScriptLogs();

        if (sdBombPickup)
        {
            constexpr std::string_view SdBombPresentationModel =
                "prop_suitcase_bomb";
            const auto sourceModelIndex = Bindings.resolveModelConfigStringIndex(
                sdBombPickup->visualModelName);
            const auto presentationModelIndex =
                Bindings.resolveModelConfigStringIndex(SdBombPresentationModel);
            const CodolGameServer::SvScriptModelEntityDefinition visualDefinition{
                .origin = sdBombPickup->visualOrigin,
                .angles = sdBombPickup->visualAngles,
                .modelIndex = sourceModelIndex.value_or(0),
                .modelName = sdBombPickup->visualModelName,
                .scale = 1.0f,
                .scriptGameObjectName = "sd",
                .targetName = sdBombPickup->visualTargetName,
                .mapModeEligible = true,
                .gameplayActive = false,
            };
            if (!sourceModelIndex || !presentationModelIndex ||
                !Server.configureSdBombPresentation(
                    visualDefinition,
                    *presentationModelIndex,
                    SdBombPresentationModel))
            {
                reportFailure("sd_bomb_presentation_commit");
                return;
            }

            // Crash inherits the COD4/IW4 SAS-versus-OpFor faction pairing.
            // TF consumes the allies spawn set and SC consumes the axis set in
            // this server, so their loaded CODOL leader packs are uk/ab.
            // TODO(CODOL): Resolve these prefixes from CODOL's map faction
            // owner before enabling SD presentation on additional maps.
            if (request->mapName == "mp_crash" ||
                request->mapName == "mp_crash_tropical")
            {
                constexpr std::array<std::string_view, 14> TeamSuffixes{
                    "search_destroy", "obj_destroy", "obj_defend",
                    "bomb_taken", "bomb_lost", "bomb_planted",
                    "bomb_defused", "lastalive", "encourage_win",
                    "encourage_lost", "mission_success", "mission_fail",
                    "draw", "switching",
                };
                std::vector<std::string> aliases{
                    "mp_war_objective_lost", "mp_war_objective_taken",
                };
                for (const auto prefix : { "uk", "ab" })
                {
                    for (const auto suffix : TeamSuffixes)
                    {
                        aliases.push_back(
                            std::string(prefix) + "_1mc_" +
                            std::string(suffix));
                    }
                }
                const auto parameters =
                    Bindings.resolveSoundAliasEventParameters(aliases);
                const auto parameter = [&](const std::size_t index) {
                    return index < parameters.size()
                        ? parameters[index].value_or(0)
                        : std::uint16_t{};
                };
                const auto resolveTeam = [&](const std::size_t offset) {
                    return CodolGameServer::SvSdTeamSoundPresentation{
                        .searchDestroy = parameter(offset),
                        .objectiveDestroy = parameter(offset + 1),
                        .objectiveDefend = parameter(offset + 2),
                        .bombTaken = parameter(offset + 3),
                        .bombLost = parameter(offset + 4),
                        .bombPlanted = parameter(offset + 5),
                        .bombDefused = parameter(offset + 6),
                        .lastAlive = parameter(offset + 7),
                        .roundWon = parameter(offset + 8),
                        .roundLost = parameter(offset + 9),
                        .matchWon = parameter(offset + 10),
                        .matchLost = parameter(offset + 11),
                        .draw = parameter(offset + 12),
                        .sideSwitch = parameter(offset + 13),
                    };
                };
                const CodolGameServer::SvSdSoundPresentation soundPresentation{
                    .objectiveLost = parameter(0),
                    .objectiveTaken = parameter(1),
                    .tf = resolveTeam(2),
                    .sc = resolveTeam(2 + TeamSuffixes.size()),
                };
                if (!Server.configureSdSoundPresentation(soundPresentation))
                {
                    logGameServer(
                        "sd sound presentation unavailable map=" +
                        request->mapName);
                }
            }
        }

        // OLMOD(brushmodel-census): one-shot inventory of what the map actually carries.
        //
        // The doors do not render because this server publishes NO brush models at all: the
        // model configstring band (ModelConfigStringBase 2568) never receives a `* N` entry,
        // and retail's zm_factory_sh gamestate carries 34 of them (`* 1159`..`* 1192`, demo
        // C-2021-7-31[15-32-16]zm cs 2979/2980 and 2995..3026). `clipHandle` below IS the N.
        // Retail publishes 34 of the 238, so the open question is WHICH -- and a door is
        // identifiable by its targetname / script_gameobjectname, which the parser already
        // keeps. Printed once per world spawn so the selection can be made from data.
        for (std::size_t i = 0; i < brushModels.size(); ++i)
        {
            const auto &b = brushModels[i];
            logGameServer(
                "brushmodel census [" + std::to_string(i) + "] clip=*" +
                std::to_string(b.collision.clipHandle) +
                " contents=0x" + [&] {
                    char buffer[16]{};
                    std::snprintf(buffer, sizeof(buffer), "%08X", b.collision.contents);
                    return std::string(buffer);
                }() +
                " origin=" + std::to_string(b.origin[0]) + "," +
                std::to_string(b.origin[1]) + "," + std::to_string(b.origin[2]) +
                " targetname=" + (b.targetName.empty() ? "-" : b.targetName) +
                " gameobject=" + (b.scriptGameObjectName.empty()
                    ? "-" : b.scriptGameObjectName) +
                " destructible=" + (b.destructibleType.empty()
                    ? "-" : b.destructibleType) +
                " mpEligible=" + (b.mapModeEligible ? "1" : "0") +
                " active=" + (b.gameplayActive ? "1" : "0"));
        }

        logGameServer(
            "world spawn configured map=" + request->mapName +
            " preparationMs=" + std::to_string(std::chrono::duration_cast<std::chrono::milliseconds>(
                RuntimeClock::now()-preparationStart).count()) +
            " cachedLookups=" + std::to_string(lookupRequests-lookupMisses) +
            "/" + std::to_string(lookupRequests) +
            " spawnPoints=" + std::to_string(worldSpawnPoints.size()) +
            " brushModels=" + std::to_string(brushModels.size()) +
            " conservativeActiveBrushModels=" +
            std::to_string(activeBrushModels) +
            " scriptModels=" + std::to_string(scriptModels.size()) +
            " scriptModelsOnRetailNumbers=" +
            std::to_string(Server.constBaselineScriptModelCount()) +
            " conservativeActiveScriptModels=" +
            std::to_string(activeScriptModels) +
            " destructibleDamageOwners=" +
            std::to_string(scriptModelDamageOwners.size()) +
            " glassPieces=" +
            std::to_string(glassMetadata->initialPieces.size()) +
            " glassThresholds=" + std::to_string(glassThresholds->weaken) +
            "/" + std::to_string(glassThresholds->destroy));

        const std::lock_guard lock(WorldAssetMutex);
        if (PendingWorldAsset &&
            PendingWorldAsset->mapName == request->mapName &&
            PendingWorldAsset->gameType == request->gameType)
        {
            PendingWorldAsset.reset();
        }
    }

    bool configurePendingBooking(const bool mayInitializeConfigStrings)
    {
        const std::lock_guard lock(BookingMutex);
        const auto initialized = Bindings.CCS_Initialized();
        auto ready = PendingBooking.observeConfigStrings(
            initialized,
            Bindings.CCS_GetChecksum(),
            mayInitializeConfigStrings);
        if (!ready && PendingBooking.pending() && !initialized &&
            mayInitializeConfigStrings && Bindings.CCS_EnsureInitialized())
        {
            ready = PendingBooking.observeConfigStrings(
                true, Bindings.CCS_GetChecksum(), true);
        }
        if (!ready)
            return false;
        // The frame thread stops within two seconds of the booking being accepted, somewhere past
        // here (sec 36d). Everything from this point is reachable only once configureBooking has
        // returned true, which no run before 2026-08-19 ever did -- so bracket it and let the last
        // line printed name the region.
        logGameServer(
            "pending booking ready: configuring gamestate map=" +
            ready->rotation.mapName + " gametype=" + ready->rotation.gameType);
        if (!configureGameState(
            ready->rotation.mapName,
            ready->rotation.gameType,
            ready->configStringChecksum))
        {
            PendingBooking.cancel();
            return false;
        }
        return PendingBooking.commit(*ready);
    }

    // A HANG ON ONE THREAD CANNOT REPORT ITSELF. The dedicated's frame thread stops a few
    // seconds after the gamestate is configured (sec 36d): the process stays alive, the control
    // thread keeps answering and keeps writing to this same log, and the frame thread simply
    // stops. Nothing it could print would ever come out, because it is the thread that is stuck.
    //
    // So the report has to come from somewhere else. The frame thread only STORES a phase, which
    // costs an atomic write per stage, and a watchdog on its own thread notices when the tick
    // counter stops moving and prints the phase it stopped in. That turns "the log went quiet"
    // into "it went quiet in <phase>", which is the whole question.
    //
    // Deliberately one-shot per stall: a watchdog that repeats every interval buries the log it
    // is trying to make readable.
    std::uint32_t LastCensusConnectedClients{};
    std::atomic<std::uint32_t> FramePhase{};
    std::atomic<std::uint64_t> FrameTick{};
    std::atomic<bool> FrameWatchdogRunning{};

    // A duplicate of the frame thread, so the watchdog can look at where it is stopped. Opened
    // once, from the frame thread itself, because that is the only place that knows which one it
    // is.
    std::atomic<HANDLE> FrameThreadHandle{};

    bool readProcessValue(const std::uintptr_t *address, std::uintptr_t &value);

    // "module+0xRVA" for a code address, or a bare address when it belongs to no loaded module.
    // A module identifies ownership, not the operation: ntdll also contains heap
    // and other active runtime code, so resolve the address before calling it a wait.
    std::string describeCodeAddress(const void *const address)
    {
        char buffer[160]{};
        HMODULE module{};
        if (GetModuleHandleExA(
                GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                    GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                static_cast<LPCSTR>(address),
                &module) && module)
        {
            char path[MAX_PATH]{};
            if (GetModuleFileNameA(module, path, sizeof(path)))
            {
                const char *name = std::strrchr(path, '\\');
                name = name ? name + 1 : path;
                std::snprintf(
                    buffer, sizeof(buffer), "%s+0x%X", name,
                    static_cast<unsigned>(
                        reinterpret_cast<const std::uint8_t *>(address) -
                        reinterpret_cast<const std::uint8_t *>(module)));
                return buffer;
            }
        }
        std::snprintf(buffer, sizeof(buffer), "0x%08X",
            static_cast<unsigned>(reinterpret_cast<std::uintptr_t>(address)));
        return buffer;
    }

    // WHERE IS IT PARKED. Suspend for the length of one GetThreadContext, read EIP, then scan the
    // top of the stack for values that land in a loaded module -- return addresses, mixed with
    // some noise, which is enough to name the caller when EIP itself is a syscall stub. x86 release
    // code omits frame pointers often enough that an EBP walk is not dependable; a scan is.
    std::string describeFrameThreadStall()
    {
        auto *const thread=FrameThreadHandle.load(std::memory_order_acquire);
        if (!thread) return "frame thread handle unavailable";
        CONTEXT context{};
        context.ContextFlags=CONTEXT_CONTROL|CONTEXT_INTEGER;
        std::array<std::uintptr_t,1024> stack{};
        SIZE_T bytes{};
        if (SuspendThread(thread)==static_cast<DWORD>(-1))
            return "frame thread could not be suspended";
        const auto captured=GetThreadContext(thread,&context);
        if (captured)
            ReadProcessMemory(GetCurrentProcess(),
                reinterpret_cast<const void *>(static_cast<std::uintptr_t>(context.Esp)),
                stack.data(),sizeof(stack),&bytes);
        // No heap allocation, logging or loader lookup while the target is
        // suspended: it may own precisely those locks. Resume before formatting.
        ResumeThread(thread);
        if (!captured) return "frame thread context unavailable";
        std::string result="eip="+describeCodeAddress(
            reinterpret_cast<const void *>(context.Eip));
        std::size_t found{};
        for (std::size_t index=0;index<bytes/sizeof(stack[0]) && found<32;++index)
        {
            const auto candidate=stack[index];
            if (candidate<0x10000) continue;
            MEMORY_BASIC_INFORMATION region{};
            if (!VirtualQuery(reinterpret_cast<const void *>(candidate),
                    &region,sizeof(region)) || region.State!=MEM_COMMIT ||
                !(region.Protect & (PAGE_EXECUTE|PAGE_EXECUTE_READ|
                    PAGE_EXECUTE_READWRITE|PAGE_EXECUTE_WRITECOPY))) continue;
            HMODULE module{};
            if (!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|
                    GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                    reinterpret_cast<LPCSTR>(candidate),&module) || !module) continue;
            result+=(found ? " <- " : " stack: ")+describeCodeAddress(
                reinterpret_cast<const void *>(candidate));
            ++found;
        }
        return result;
    }

    // The stack pointer of a suspended thread is trustworthy, but the range above it is not
    // guaranteed mapped for the whole scan. Read through the API that reports failure instead of
    // faulting.
    bool readProcessValue(const std::uintptr_t *const address, std::uintptr_t &value)
    {
        SIZE_T read{};
        return ReadProcessMemory(
                   GetCurrentProcess(), address, &value, sizeof(value), &read) &&
            read == sizeof(value);
    }

    const char *framePhaseName(const std::uint32_t phase)
    {
        switch (phase)
        {
        // Each name is the region the frame thread has ENTERED, i.e. the work between this
        // mark and the next one. A stall reports the phase it is inside, not the one it finished.
        case 0: return "not_started";
        case 1: return "entry";
        case 2: return "role_and_client_patches";
        case 3: return "dedicated_control";
        case 4: return "loadout_refresh";
        case 5: return "pending_booking_and_worldspawn";
        case 6: return "server_frame(Server.onComFrame)";
        case 7: return "dobj_probe_script_logs_and_net_send";
        case 8: return "status_and_periodic_report";
        }
        return "unknown";
    }

    void markFramePhase(const std::uint32_t phase)
    {
        FramePhase.store(phase, std::memory_order_release);
        FrameTick.fetch_add(1, std::memory_order_acq_rel);
    }

    void startFrameWatchdog()
    {
        if (FrameWatchdogRunning.exchange(true))
            return;
        std::thread([] {
            std::uint64_t lastTick = 0;
            std::uint32_t stalledFor = 0;
            bool reported = false;
            for (;;)
            {
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
                const auto tick = FrameTick.load(std::memory_order_acquire);
                if (tick != lastTick)
                {
                    lastTick = tick;
                    stalledFor = 0;
                    reported = false;
                    continue;
                }
                if (!tick)
                    continue;               // the frame thread has never run; not a stall
                stalledFor += 100;
                if (stalledFor < 300 || reported ||
                    FramePhase.load(std::memory_order_acquire)!=6)
                    continue;
                reported = true;
                logGameServer(
                    std::string("FRAME THREAD STALLED for ") +
                    std::to_string(stalledFor) + "ms in phase=" +
                    framePhaseName(FramePhase.load(std::memory_order_acquire)) +
                    " tick=" + std::to_string(tick) + " " +
                    describeFrameThreadStall());
            }
        }).detach();
    }

    void onServerFrame(const std::uint32_t nowMilliseconds)
    {
        if (!FrameThreadHandle.load(std::memory_order_acquire))
        {
            HANDLE duplicate{};
            if (DuplicateHandle(
                    GetCurrentProcess(), GetCurrentThread(),
                    GetCurrentProcess(), &duplicate,
                    THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT |
                        THREAD_QUERY_INFORMATION,
                    FALSE, 0))
            {
                HANDLE expected{};
                if (!FrameThreadHandle.compare_exchange_strong(
                        expected, duplicate))
                {
                    CloseHandle(duplicate);
                }
            }
        }
        startFrameWatchdog();
        markFramePhase(1);
        if (!Bindings.observeGameThread())
            return;
        markFramePhase(2);
        Bindings.auditXModelSurfaces();
        const auto alphaWeaponPortStatus = Bindings.installAlphaWeaponPorts();
        Bindings.auditAlphaWeaponModelPointers();
        if (alphaWeaponPortStatus !=
                CodolGameServer::AlphaWeaponPortStatus::Disabled &&
            (!LastLoggedAlphaWeaponPortStatus ||
                *LastLoggedAlphaWeaponPortStatus != alphaWeaponPortStatus))
        {
            logGameServer(
                "alpha weapon port status=" + std::string(
                    alphaWeaponPortStatusName(alphaWeaponPortStatus)));
            LastLoggedAlphaWeaponPortStatus = alphaWeaponPortStatus;
        }
        const auto role = OlMod::processRole();
        if (role != OlMod::ProcessRole::Dedicated)
        {
            if (ClientProcessPatch &&
                (*ClientProcessPatch ==
                        CodolGameServer::ClientProcessPatchResult::Patched ||
                    *ClientProcessPatch == CodolGameServer::
                        ClientProcessPatchResult::AlreadyPatched))
            {
                SetThreadExecutionState(ES_DISPLAY_REQUIRED);
            }
            if (ClientRawInputPatch &&
                (*ClientRawInputPatch ==
                        CodolGameServer::ClientRawInputPatchResult::Patched ||
                    *ClientRawInputPatch == CodolGameServer::
                        ClientRawInputPatchResult::AlreadyPatched) &&
                !ClientRawInputWindowReady)
            {
                ClientRawInputWindowReady =
                    CodolGameServer::maintainClientRawInputWindow();
                if (ClientRawInputWindowReady)
                    logGameServer("client raw input window ready");
            }
            maintainClientGametypeDvarCache(nowMilliseconds);
            ensureClientSessionBridge();
            if (ClientSessionBridge)
            {
                ClientSessionBridge->process([] {
                    // OLMOD(section-48-input-probe): THIS RUNS IN THE CLIENT PROCESS, and
                    // that is the whole point. The first version of this probe fired on
                    // the session-start path, which is the DEDICATED process, and
                    // reported count=0 -- true, and useless, because the dedicated
                    // out.exe never joins a lobby room. The roster and the public profile
                    // both live over here.
                    //
                    // Throttled on CHANGE like LastCaptureRefusal below it, so a steady
                    // state prints once rather than every bridge tick.
                    static std::string LastRosterReport;
                    auto rosterReport = Bindings.reportSessionMemberItemHandles();
                    if (rosterReport != LastRosterReport)
                    {
                        LastRosterReport = rosterReport;
                        logGameServer("client-side " + rosterReport);
                    }
                    // SECOND, and only under OLMOD_PROBE_PROFILE_SLOTS=1. The roster line
                    // above is already written by the time this makes its native call, so
                    // if the call takes the process down the measurement survives.
                    // THE CLIENT'S OWN VIEW OF EVERY PLAYER'S CHARACTER, edge-triggered
                    // on change so a healthy client says it once. This is the side an
                    // invisible player fails on, and nothing has ever read it.
                    static std::string LastCharacterInfoReport;
                    auto characterInfoReport = Bindings.reportClientCharacterInfo();
                    if (!characterInfoReport.empty() &&
                        characterInfoReport != LastCharacterInfoReport)
                    {
                        LastCharacterInfoReport = characterInfoReport;
                        logGameServer(characterInfoReport);
                    }
                    static std::string LastSlotReport;
                    auto slotReport = Bindings.reportProfileCharacterSlots();
                    if (!slotReport.empty() && slotReport != LastSlotReport)
                    {
                        LastSlotReport = slotReport;
                        logGameServer("client-side " + slotReport);
                    }
                    const auto loadout = Bindings.captureClientLoadoutRequest();
                    const auto selection = Bindings.readClientBookingSelection();
                    // TWO SOURCES, ONE SILENCE. Returning nullopt here makes the
                    // bridge time out, and configure-session reports status=3 with a
                    // stock explanation -- "the client has no loadout to report yet,
                    // capture AFTER it has picked a class". That explanation has now
                    // been wrong twice: the capture still times out with a class
                    // picked and the player standing in the map. It cannot say which
                    // of the two reads came back empty, and they fail for completely
                    // different reasons -- the loadout needs the client character
                    // resolver (unported on OLfinal, section 16a), while the booking
                    // selection needs the client to still be holding a lobby booking,
                    // which it may well drop once the match starts.
                    // THE LOADOUT IS THE HALF THAT MATTERS. The booking selection
                    // is reported when the client is holding one and left empty when
                    // it is not -- a client at the menu has a perfectly good loadout
                    // and no booking, and refusing both because of the second is why
                    // this reported nothing for so long. configure-session takes the
                    // map and gametype from its own arguments anyway.
                    const auto haveSelection =
                        selection && selection->rotationIndex >= 0;
                    if (!loadout)
                    {
                        static std::string LastCaptureRefusal;
                        auto why = std::string("client capture empty:") +
                            (loadout ? "" : " NO_LOADOUT") +
                            (selection ? "" : " NO_BOOKING_SELECTION") +
                            (selection && selection->rotationIndex < 0
                                ? " ROTATION_INDEX_NEGATIVE" : "");
                        if (loadout)
                        {
                            why += " characterIndex=" +
                                std::to_string(loadout->characterIndex) +
                                " classMask=" +
                                std::to_string(loadout->classMask);
                        }
                        if (why != LastCaptureRefusal)
                        {
                            logGameServer(why);
                            LastCaptureRefusal = why;
                        }
                        return std::optional<
                            OlMod::DedicatedSession::ClientSessionCapture>{};
                    }
                    OlMod::DedicatedSession::BookingSelection booking{};
                    if (haveSelection)
                    {
                        booking = {
                            .playlistId = selection->playlistSlot,
                            .rotationIndex = static_cast<std::uint32_t>(
                                selection->rotationIndex),
                            .mapName = selection->mapName,
                            .gameType = selection->gameType,
                        };
                    }
                    return std::optional{
                        OlMod::DedicatedSession::ClientSessionCapture{
                            .booking = booking,
                            .loadout = *loadout,
                        }};
                });
            }
        }
        if (!OlMod::runsGameServer(role))
            return;
        markFramePhase(3);
        ensureDedicatedControlServer();
        processDedicatedControlMessages();
        markFramePhase(4);
        const auto initialStatus = Server.status();
        std::uint64_t requestSequence{};
        bool refreshRequested{};
        {
            const std::lock_guard lock(LoadoutMutex);
            requestSequence = LoadoutPrepareRequestSequence;
            refreshRequested = !PreparedLoadouts ||
                PreparedLoadouts->requestSequence !=
                    LoadoutPrepareRequestSequence;
        }
        if (role != OlMod::ProcessRole::Dedicated &&
            CodolGameServer::SV_ShouldRefreshClientLoadouts(
                initialStatus.gameStateConfigured,
                initialStatus.activeClients,
                refreshRequested) &&
            (!LastLoadoutPrepareRequestSequence ||
                *LastLoadoutPrepareRequestSequence != requestSequence ||
                !LastLoadoutPrepareAttempt ||
                nowMilliseconds - *LastLoadoutPrepareAttempt >= 1000))
        {
            LastLoadoutPrepareAttempt = nowMilliseconds;
            LastLoadoutPrepareRequestSequence = requestSequence;
            static_cast<void>(prepareClientLoadouts());
        }
        Network.NET_Frame(Server, nowMilliseconds);
        const auto status = Server.status();
        // Keep connectionless failures in the persistent server log.  The
        // dedicated process normally has no visible console, so the
        // temporary std::clog diagnostics in ServerCore are otherwise lost.
        if (role == OlMod::ProcessRole::Dedicated)
        {
            static std::uint32_t loggedConnectionlessConnected{};
            static std::uint32_t loggedConnectionlessRejected{};
            const auto diagnostics = Server.connectionlessDiagnostics();
            if (diagnostics.connected != loggedConnectionlessConnected)
            {
                loggedConnectionlessConnected = diagnostics.connected;
                logGameServer(
                    "connectionless connected peer=" +
                    std::to_string(diagnostics.lastConnectedPeer.ipv4) + ":" +
                    std::to_string(diagnostics.lastConnectedPeer.port) +
                    " slot=" +
                    std::to_string(diagnostics.lastConnectedClientSlot));
            }
            if (diagnostics.rejected != loggedConnectionlessRejected)
            {
                loggedConnectionlessRejected = diagnostics.rejected;
                logGameServer(
                    "connectionless rejected peer=" +
                    std::to_string(diagnostics.lastRejectedPeer.ipv4) + ":" +
                    std::to_string(diagnostics.lastRejectedPeer.port) +
                    " reason=" + diagnostics.lastRejectedReason);
            }
        }
        const auto mayInitializeDedicatedConfigStrings =
            role == OlMod::ProcessRole::Dedicated &&
            status.netchanPacketsReceived != 0;
        markFramePhase(5);
        static_cast<void>(configurePendingBooking(
            status.netchanPacketsReceived != 0 &&
            (status.clientsReadyForGameState != 0 ||
                mayInitializeDedicatedConfigStrings)));
        configurePendingWorldSpawn(nowMilliseconds);
        markFramePhase(6);
        std::vector<CodolGameServer::SvOutboundPacket> outbound;
        const auto serverCpuStart = role==OlMod::ProcessRole::Dedicated
            ? currentThreadCpuMicroseconds() : std::nullopt;
        const auto serverFrameTimingStart = RuntimeClock::now();
        try
        {
            outbound = Server.onComFrame(nowMilliseconds);
        }
        catch (const std::exception &error)
        {
            logGameServer(
                "server frame terminated by C++ exception: " +
                std::string(error.what()));
            throw;
        }
        const auto serverWallUs=elapsedMicroseconds(serverFrameTimingStart);
        ServerFrameTiming.record(serverWallUs);
        // Wall timers alone mislabel scheduler/I/O waits as expensive native
        // movement. Only report slow frames, at most once per second. CPU time
        // has OS accounting granularity; it is a discriminator, not a profiler.
        static std::uint64_t lastSlowFrameReport{};
        if (serverWallUs>=50000u && serverCpuStart &&
            (!lastSlowFrameReport || nowMilliseconds-lastSlowFrameReport>=1000u))
        {
            const auto cpuEnd=currentThreadCpuMicroseconds();
            if (cpuEnd && *cpuEnd>=*serverCpuStart)
            {
                lastSlowFrameReport=nowMilliseconds;
                logGameServer("FRAMESTALL wallUs="+std::to_string(serverWallUs)+
                    " threadCpuUs="+std::to_string(*cpuEnd-*serverCpuStart));
            }
        }
        markFramePhase(7);
        runDObjLocationalProbe();
        runCapsuleEntityProbe();
        drainGameplayScriptLogs();
        const auto networkSendTimingStart = RuntimeClock::now();
        Network.NET_SendPackets(outbound, nowMilliseconds);
        NetworkSendTiming.record(elapsedMicroseconds(networkSendTimingStart));
        markFramePhase(8);
        const auto finalStatus = Server.status();
        const auto networkStatus = Network.status();
        // AIM THE INSTRUMENT AT THE TRANSITION ITSELF: whenever connectedClients changes, print
        // every slot the server will still talk about, so whatever empties them shows up in the
        // census on one side or the other.
        //
        // CORRECTION. An earlier version of this comment claimed "commitSessionRoster is never
        // called from anywhere". THAT IS FALSE, and it is the whole bug. It is called from
        // SvClientSystem::configureGameState under `if (sessionGeneration)`, and has been since
        // 99d66d1 -- an UNQUALIFIED intra-class call, which a grep for the member-qualified form
        // (`.commitSessionRoster`, `Server.commitSessionRoster`) does not match. The log proves
        // the reachability without reading any code: the client dies within a second of every
        // `gamestate configuration ACCEPTED`, and on the one run that FAILED at
        // stage=server_commit_failed -- the failure that returns before this very call -- the
        // client SURVIVED for twenty more seconds. Accept kills it; failure spares it.
        if (finalStatus.connectedClients != LastCensusConnectedClients)
        {
            std::string census;
            for (std::uint32_t clientNum{};
                clientNum < CodolGameServer::MaximumGameClients; ++clientNum)
            {
                const auto ingress = Server.clientIngressStatus(clientNum);
                if (!ingress)
                    continue;
                census += (census.empty() ? "" : " | ") + std::to_string(clientNum) +
                    ":state=" + std::to_string(static_cast<unsigned>(ingress->state)) +
                    " xuid=" + std::to_string(ingress->xuid) +
                    " peer=" + std::to_string(ingress->peer.ipv4) + ":" +
                    std::to_string(ingress->peer.port) +
                    " gen=" + std::to_string(ingress->sessionGeneration) +
                    " genActive=" + std::to_string(ingress->sessionGenerationActive ? 1 : 0) +
                    " lastPacket=" + std::to_string(ingress->lastPacketTime);
            }
            logGameServer(
                "client census " + std::to_string(LastCensusConnectedClients) + " -> " +
                std::to_string(finalStatus.connectedClients) + " now=" +
                std::to_string(nowMilliseconds) + " [" +
                (census.empty() ? std::string("no slot reports anything") : census) + "]");
            LastCensusConnectedClients = finalStatus.connectedClients;
        }
        for (std::uint32_t clientNum = 0;
             clientNum < LastLoggedClientThinkStatus.size();
             ++clientNum)
        {
            const auto thinkStatus = Server.worldClientThinkStatus(clientNum);
            auto &lastStatus = LastLoggedClientThinkStatus[clientNum];
            if (!thinkStatus)
            {
                lastStatus.reset();
                continue;
            }
            if (thinkStatus->failureStage !=
                    CodolGameServer::SvClientThinkFailureStage::None &&
                (!lastStatus ||
                    lastStatus->lastAttemptedCommandTime !=
                        thinkStatus->lastAttemptedCommandTime ||
                    lastStatus->failureStage != thinkStatus->failureStage))
            {
                logGameServer(
                    "client-think rejected client=" +
                    std::to_string(clientNum) + " commandTime=" +
                    std::to_string(thinkStatus->lastAttemptedCommandTime) +
                    " committed=" +
                    std::to_string(thinkStatus->lastCommittedCommandTime) +
                    " psCmdTime=" +
                    std::to_string(thinkStatus->playerStateCommandTime) +
                    " serverTime=" +
                    std::to_string(thinkStatus->serverTime) +
                    " stage=" + std::string(
                        CodolGameServer::SV_ClientThinkFailureStageName(
                            thinkStatus->failureStage)) +
                    " failures=" +
                    std::to_string(thinkStatus->failureCount) +
                    (thinkStatus->nativeActionDiagnostics
                        ? " nativeAction={pmType=" +
                            std::to_string(
                                thinkStatus->nativeActionDiagnostics->pmType) +
                            " clientNum=" + std::to_string(
                                thinkStatus->nativeActionDiagnostics->clientNum) +
                            " viewmodel=" + std::to_string(
                                thinkStatus->nativeActionDiagnostics->viewmodelIndex) +
                            " weapon=" + std::to_string(
                                thinkStatus->nativeActionDiagnostics
                                    ->currentWeaponAssetIndex) +
                            " anim=" + std::to_string(
                                thinkStatus->nativeActionDiagnostics
                                    ->weaponAnimation[0]) + "," +
                            std::to_string(
                                thinkStatus->nativeActionDiagnostics
                                    ->weaponAnimation[1]) +
                            " state=" + std::to_string(
                                thinkStatus->nativeActionDiagnostics
                                    ->weaponState[0]) + "," +
                            std::to_string(
                                thinkStatus->nativeActionDiagnostics
                                    ->weaponState[1]) +
                            " shots=" + std::to_string(
                                thinkStatus->nativeActionDiagnostics
                                    ->weaponShotCount[0]) + "," +
                            std::to_string(
                                thinkStatus->nativeActionDiagnostics
                                    ->weaponShotCount[1]) + "}"
                        : std::string{}));
            }
            lastStatus = thinkStatus;

            const auto ingress = Server.clientIngressStatus(clientNum);
            if (ingress)
            {
                const auto ingressStateKey =
                    std::to_string(ingress->xuid) + " name=" + ingress->name +
                    " state=" + std::to_string(static_cast<unsigned>(ingress->state)) +
                    " profile=" + std::to_string(ingress->profileStatsReceivedMask) +
                    "/" + std::to_string(ingress->profileStatsRequiredMask) +
                    " profile_complete=" +
                    std::to_string(ingress->profileStatsComplete ? 1 : 0) +
                    " gamestate_stage=" +
                    std::to_string(ingress->gameStateUpdateStage) +
                    " gamestate_msg=" +
                    std::to_string(ingress->gamestateMessageNum) +
                    " session_generation=" +
                    std::to_string(ingress->sessionGeneration) +
                    " generation_active=" +
                    std::to_string(ingress->sessionGenerationActive ? 1 : 0) +
                    " gameplay=" + std::to_string(static_cast<unsigned>(ingress->gameplayState)) +
                    " loadout_seq=" + std::to_string(ingress->loadoutSequence) +
                    " pending_loadout_seq=" +
                    std::to_string(ingress->pendingLoadoutSequence) +
                    " team=" + std::to_string(static_cast<unsigned>(ingress->team)) +
                    " pending_team=" +
                    std::to_string(static_cast<unsigned>(ingress->pendingTeam));
                if (LastLoggedClientIngressState[clientNum] != ingressStateKey)
                {
                    logGameServer("client-slot " + std::to_string(clientNum) +
                        " " + ingressStateKey +
                        " msg_ack=" +
                        std::to_string(ingress->messageAcknowledge) +
                        " reliable_ack=" +
                        std::to_string(ingress->reliableAcknowledge));
                    LastLoggedClientIngressState[clientNum] = ingressStateKey;
                }
            }
            else
            {
                LastLoggedClientIngressState[clientNum].clear();
            }
            if (ingress && ingress->discardedUnsupportedUserCmds !=
                    LastLoggedUnsupportedDiscardCounts[clientNum])
            {
                const auto &discarded =
                    ingress->lastDiscardedUnsupportedUserCmd;
                logGameServer(
                    "unsupported usercmd discarded client=" +
                    std::to_string(clientNum) + " commandTime=" +
                    std::to_string(
                        discarded ? discarded->commandTime : 0) +
                    " count=" + std::to_string(
                        ingress->discardedUnsupportedUserCmds));
                LastLoggedUnsupportedDiscardCounts[clientNum] =
                    ingress->discardedUnsupportedUserCmds;
            }
            if (ingress)
            {
                const auto reject = ingress->lastPacketReject;
                const auto rejectState = reject
                    ? std::to_string(reject->sequence) + " ack=" +
                        std::to_string(reject->messageAcknowledge) +
                        " reliable_ack=" +
                        std::to_string(reject->reliableAcknowledge) +
                        " decoded=" + std::to_string(reject->decodedCommandsSize) +
                        " rejected_cmd=" + std::to_string(reject->rejectedCommandTime) +
                        " baseline_cmd=" + std::to_string(reject->rejectedCommandBaselineTime) +
                        " reason=" + reject->reason
                    : std::string{};
                if (!rejectState.empty() &&
                    rejectState != LastLoggedClientRejectState[clientNum])
                {
                    logGameServer(
                        "client-packet-reject client=" +
                        std::to_string(clientNum) + " " + rejectState);
                    LastLoggedClientRejectState[clientNum] = rejectState;
                }
                else if (rejectState.empty())
                {
                    LastLoggedClientRejectState[clientNum].clear();
                }
            }
        }
        const auto statusChanged =
            finalStatus.connectedClients != LastLoggedServerStatus.connectedClients ||
            finalStatus.activeClients != LastLoggedServerStatus.activeClients ||
            finalStatus.netchanPacketsReceived !=
                LastLoggedServerStatus.netchanPacketsReceived ||
            finalStatus.snapshotMessagesSent !=
                LastLoggedServerStatus.snapshotMessagesSent ||
            finalStatus.worldFrameRejections !=
                LastLoggedServerStatus.worldFrameRejections ||
            networkStatus.lastSocketError != LastLoggedNetworkStatus.lastSocketError;
        if (statusChanged &&
            (!LastRuntimeStatusLogMilliseconds ||
                nowMilliseconds - LastRuntimeStatusLogMilliseconds >= 5000))
        {
            const auto serverTiming = ServerFrameTiming.take();
            const auto sendTiming = NetworkSendTiming.take();
            std::array<CodolGameServer::SvTimingWindow,
                CodolGameServer::MaximumGameClients> snapshotTiming{};
            for (std::size_t index{}; index < snapshotTiming.size(); ++index)
                snapshotTiming[index] = SnapshotBuildTiming[index].take();
            const auto gameplay = Server.gameplayPresentationStatus();
            const auto frameTiming = Server.takeFrameTimingStatus();
            std::string acknowledgeProgress;
            for (std::size_t clientNum = 0;
                clientNum < LastLoggedClientIngressState.size(); ++clientNum)
            {
                const auto ingress = Server.clientIngressStatus(clientNum);
                if (!ingress)
                    continue;
                acknowledgeProgress += acknowledgeProgress.empty() ? " acks=" : ",";
                acknowledgeProgress += std::to_string(clientNum) + ":" +
                    std::to_string(ingress->messageAcknowledge) + "/" +
                    std::to_string(ingress->reliableAcknowledge);
            }
            logGameServer(
                "runtime clients=" +
                std::to_string(finalStatus.connectedClients) + " active=" +
                std::to_string(finalStatus.activeClients) + " packets=" +
                std::to_string(finalStatus.netchanPacketsReceived) +
                " dropped=" +
                std::to_string(finalStatus.netchanPacketsDropped) +
                " snapshots=" +
                std::to_string(finalStatus.snapshotMessagesSent) +
                " frameReject=" +
                std::string(CodolGameServer::
                    SV_SnapshotFrameValidationFailureName(
                        finalStatus.worldFrameValidationFailure)) +
                ":" + std::to_string(finalStatus.worldFrameRejections) +
                " socketError=" +
                std::to_string(networkStatus.lastSocketError) +
                acknowledgeProgress);
            std::string clientFlow;
            for (const auto &client : gameplay.clients)
            {
                if (client.clientNum >= snapshotTiming.size())
                    continue;
                const auto ingress = Server.clientIngressStatus(client.clientNum);
                const auto commandAge = client.lastExecutedUserCmdTime
                    ? static_cast<std::int64_t>(gameplay.serverTime) -
                        static_cast<std::int64_t>(
                            *client.lastExecutedUserCmdTime)
                    : std::int64_t{ -1 };
                const auto receivedExecutedGap =
                    client.lastReceivedUserCmdTime &&
                        client.lastExecutedUserCmdTime
                    ? static_cast<std::int64_t>(
                          *client.lastReceivedUserCmdTime) -
                        static_cast<std::int64_t>(
                            *client.lastExecutedUserCmdTime)
                    : std::int64_t{ -1 };
                const auto acknowledgeGap = ingress
                    ? ingress->outgoingSequence - ingress->messageAcknowledge
                    : std::numeric_limits<std::uint32_t>::max();
                clientFlow += clientFlow.empty() ? " clients=" : ";";
                clientFlow += std::to_string(client.clientNum) +
                    "{pending=" + std::to_string(client.pendingUserCmdCount) +
                    " cmdAge=" + std::to_string(commandAge) +
                    " recvExec=" + std::to_string(receivedExecutedGap) +
                    " ackGap=" + std::to_string(acknowledgeGap) +
                    " snapBuild=" +
                    (ingress
                            ? std::string(CodolGameServer::
                                  SV_SnapshotAssemblyFailureName(
                                      ingress->snapshotAssemblyFailure)) +
                                ":" + std::to_string(
                                    ingress->snapshotAssemblyAttempts) +
                                "/" + std::to_string(
                                    ingress->snapshotAssemblyFailures)
                            : "unavailable") +
                    " snapUs=" + formatTimingWindow(
                        snapshotTiming[client.clientNum]) + "}";
            }
            logGameServer(
                "runtime-perf tickUs=" + formatTimingWindow(serverTiming) +
                " sendUs=" + formatTimingWindow(sendTiming) + clientFlow);
            logGameServer(
                "runtime-frame fixedUs=" + formatTimingWindow(
                    frameTiming.total) +
                " prepareUs=" + formatTimingWindow(frameTiming.prepare) +
                " beginUs=" + formatTimingWindow(frameTiming.beginWorld) +
                " thinkUs=" + formatTimingWindow(frameTiming.clientThink) +
                " thinkCommands=" + std::to_string(
                    frameTiming.clientThinkCommands) +
                " modeUs=" + formatTimingWindow(frameTiming.mode) +
                " endUs=" + formatTimingWindow(frameTiming.endAndPublish));
            LastRuntimeStatusLogMilliseconds = nowMilliseconds;
            LastLoggedServerStatus = finalStatus;
            LastLoggedNetworkStatus = networkStatus;
        }
    }

    void initialize()
    {
        const std::lock_guard lock(StartupMutex);
        if (Installed)
            return;
        const auto role = OlMod::processRole();

        // A custom zone can be requested before the frame hook exists. Apply
        // the explicit unsigned-fastfile opt-in at the plugin's earliest entry
        // for both client and dedicated processes.
        if (!UnsignedFastfilePatchAttempted)
        {
            UnsignedFastfilePatchAttempted = true;
            UnsignedFastfilePatch =
                CodolGameServer::installUnsignedFastfilePatch();
            if (*UnsignedFastfilePatch !=
                CodolGameServer::UnsignedFastfilePatchResult::NotRequested)
            {
                logGameServer(
                    "unsigned fastfile patch " + std::string(
                        CodolGameServer::unsignedFastfilePatchResultName(
                            *UnsignedFastfilePatch)));
            }
        }

        // FIRST, BEFORE ANYTHING THAT DEPENDS ON THE ENGINE OR THE RENDERER.
        //
        // TenProxy asks for TCLS_SHAREDMEMEMORY<pid> during this process's own startup, and
        // publishing it used to sit in installClientInputPatches -- which runs only after the
        // engine bindings resolve AND installFrameHook succeeds. That is deep into startup and
        // rendering-adjacent, so it is a RACE against TenProxy dressed up as an ordering.
        //
        // Measured 2026-09-05: on Wine's d3d9 it won -- the client authenticated as Skeet and
        // the lobby served his profile -- and under DXVK it lost, and the same [100] came back.
        // The player then had a choice between a client that logs in and crashes at the intro
        // (d3d9) and one that survives the intro and cannot log in (DXVK). Nothing about the
        // mapping should depend on which renderer is in use.
        //
        // onStartup/onInitialized are the plugin's own entry points, so this is as early as
        // this code can run. It is idempotent -- the handle is held for the process lifetime
        // and a second call returns immediately -- and the later call site is left in place as
        // a backstop for a path that reaches the frame hook without coming through here.
        if (role != OlMod::ProcessRole::Dedicated)
        {
            const auto tclsMapping = CodolGameServer::publishTclsMapping();
            if (tclsMapping != CodolGameServer::TclsMappingResult::NotRequested)
            {
                logGameServer(std::string("tcls mapping ") +
                    CodolGameServer::tclsMappingResultName(tclsMapping) + " (early)");
            }
        }
        if (role == OlMod::ProcessRole::Client)
        {
            // A CODOL CLIENT THAT CRASHES LEAVES NOTHING. It installs its own
            // TopLevelExceptionFilter, so there is no dump and no WER event -- only
            // a ClientException posted to the lobby, whose stack starts at the
            // reporter and carries no registers. A vectored handler runs BEFORE
            // that filter, so it is the only place the faulting context can be read.
            //
            // Free until something faults, which is why this is armed here and not
            // implemented as a hook: the functions involved in section 152w's crash
            // are per-frame, and a per-frame client hook killed three clients at once.
            CodolGameServer::armNativeFaultWitness(GetModuleHandleW(nullptr));
            // The noclip key. Its own thread, and it only ever talks to the
            // dedicated over the control socket -- nothing here touches a frame.
            CodolGameServer::startClientNoclipHotkey();
            CodolGameServer::startClientBatteryHotkey();
            // AND A ONE-HERTZ READ OF THE CLIENT'S OWN characterInfo. The bridge tick
            // was the wrong place for this: it fires while the client is still at the
            // menu, where cgame is not initialised and the array pointer is null, so
            // the probe only ever reported BASE NULL and never sampled a match at all.
            //
            // Its own thread, one second apart, READ ONLY and bounds-checked, logged
            // only when the answer CHANGES -- so a healthy match prints one line and an
            // invisible player prints the moment it goes wrong. Deliberately not a hook:
            // this project's rule is never to hook a per-frame client function.
            std::thread([] {
                std::string last;
                for (;;)
                {
                    std::this_thread::sleep_for(std::chrono::seconds(1));
                    auto report = Bindings.reportClientCharacterInfo();
                    if (report.empty() || report == last)
                        continue;
                    last = std::move(report);
                    logGameServer(last);
                }
            }).detach();
            const auto instance =
                CodolGameServer::configuredClientInstance();
            if (!instance ||
                (*instance > 1 &&
                    !CodolGameServer::
                        installClientInstanceSingleInstancePatch(*instance)))
            {
                logGameServer("client instance mutex patch failed");
                return;
            }
        }
        if (role == OlMod::ProcessRole::Dedicated)
        {
            if (!DedicatedProcessPatch)
            {
                DedicatedProcessPatch =
                    CodolGameServer::installDedicatedProcessPatches();
                if (*DedicatedProcessPatch !=
                        CodolGameServer::DedicatedProcessPatchResult::Patched &&
                    *DedicatedProcessPatch !=
                        CodolGameServer::DedicatedProcessPatchResult::AlreadyPatched)
                {
                    logDedicatedProcessPatchFailure(*DedicatedProcessPatch);
                }
            }
            if (*DedicatedProcessPatch !=
                    CodolGameServer::DedicatedProcessPatchResult::Patched &&
                *DedicatedProcessPatch !=
                    CodolGameServer::DedicatedProcessPatchResult::AlreadyPatched)
            {
                return;
            }
        }
        if (!Bindings.bind())
        {
            logGameServer("engine binding failed");
            return;
        }
        if (role == OlMod::ProcessRole::Client)
        {
            const auto *const alphaWeapons =
                std::getenv("OLMOD_ALPHA_WEAPONS");
            if (alphaWeapons && std::string_view(alphaWeapons) == "1")
            {
                const auto alphaGamestatePatch =
                    CodolGameServer::installClientAlphaWeaponGamestatePatch(
                        prepareClientAlphaWeaponsForGamestate);
                logGameServer(
                    "client alpha gamestate patch " +
                    std::string(CodolGameServer::clientProcessPatchResultName(
                        alphaGamestatePatch)));
            }
        }
        if (!OlMod::runsGameServer(role))
        {
            Installed = CodolGameServer::installFrameHook(
                Bindings, onServerFrame);
            if (Installed)
                installClientInputPatches(role);
            logGameServer(std::string("client frame hook ") +
                (Installed ? "installed" : "failed"));
            return;
        }
        Server.setLoadoutProvider([](
            const std::uint64_t xuid,
            const std::string_view selectedLoadout)
            -> std::optional<CodolGameServer::SvResolvedLoadout> {
            const std::lock_guard lock(LoadoutMutex);
            return RegisteredSessionAssets.loadout(xuid, selectedLoadout);
        });
        Server.setUavWeaponProvider([] { return Bindings.resolveUavWeapon(); });
        // IW4 and MW3 both ship a 30-second ordinary UAV. The decoded CODOL
        // captures do not expose an undestroyed lifetime, so retain that
        // documented reference policy while enabling the completed DM owner.
        (void)Server.configureUavRadar(30'000);
        // A free one-time reward remains separately opt-in for live diagnostics.
        if (const auto *test = std::getenv("OLMOD_UAV_RADAR_TEST"); test && std::string_view(test) == "1")
            (void)Server.configureUavRadarTest(30'000);
        if (const auto *grant = std::getenv("OLMOD_UAV_RADAR_TEST_GRANT");
            grant && std::string_view(grant) == "1")
            Server.setUavDiagnosticGrant(true);
        Server.setRewardLoadoutProvider([](const std::uint64_t xuid) {
            const std::lock_guard lock(LoadoutMutex);
            return RegisteredSessionAssets.rewards(xuid);
        });
        Server.setPerkLoadoutProvider([](
            const std::uint64_t xuid, const std::string_view selectedLoadout) {
            const std::lock_guard lock(LoadoutMutex);
            return RegisteredSessionAssets.perks(xuid, selectedLoadout);
        });
        Server.setEquipmentLoadoutProvider([](
            const std::uint64_t xuid, const std::string_view selectedLoadout) {
            const std::lock_guard lock(LoadoutMutex);
            return RegisteredSessionAssets.resolvedEquipment(xuid, selectedLoadout);
        });
        // The podium's `|` precache burst names models the DObj build already
        // resolved -- see driveMatchEndSequence. The entity number and the
        // client number are the same value for a player entity, which is what
        // makes this a one-line lookup rather than a mapping.
        Server.setCharacterModelNamesProvider(
            [](const std::uint32_t clientNum) -> std::vector<std::string> {
                return Bindings.characterModelNames(clientNum);
            });
        Server.setScriptAnimationResolver([](const std::string_view name) {
            return Bindings.resolveScriptAnimation(name);
        });
        // THE OUTFIT MASK, HANDED OVER BY CLIENT NUMBER RATHER THAN CARRIED IN THE
        // CUSTOMIZATION. Section 184h: forty-eight bytes on SvCharacterCustomization
        // put forty-eight bytes into the unordered_map node that also holds the
        // address-keyed native playerState, and every death lost its animation
        // (durationMs=-1, T-pose) -- measured in both directions, reverting the same
        // commit restored 1816 and 2983. So the mask travels beside the customization
        // instead of inside it. Guarded by LoadoutMutex, which both providers take.
        static std::map<std::uint32_t, std::array<std::uint32_t, 12>>
            CharacterOptionMasks;
        Server.setCharacterOptionMaskProvider([](const std::uint32_t clientNum) {
            const std::lock_guard lock(LoadoutMutex);
            const auto found = CharacterOptionMasks.find(clientNum);
            return found != CharacterOptionMasks.end()
                ? found->second
                : std::array<std::uint32_t, 12>{};
        });
        Server.setCharacterCustomizationProvider([](
            const std::uint32_t clientNum,
            const std::uint64_t xuid,
            const CodolGameServer::SvCharacterFaction faction)
            -> std::optional<CodolGameServer::SvCharacterCustomization> {
            const std::lock_guard lock(LoadoutMutex);
            const auto *const presentation =
                RegisteredSessionAssets.character(xuid);
            if (!presentation)
                return std::nullopt;
            // RESOLVE THE VIEWHANDS BY NAME RATHER THAN SHIP THE PLACEHOLDER.
            // viewmodelIndex is an index into the MODEL configstrings, and the
            // client finds its own by scanning them for "viewhands_tf141"
            // (EngineBindings ~7345). The dedicated could not run the full
            // character resolver -- that scheme is absent on OLfinal, section 16a --
            // so it shipped 1, the first model slot, which is some unrelated mesh.
            // The client duly attached the gun to that model's skeleton and drew a
            // smeared object across the whole screen.
            //
            // The viewhands lookup needs NONE of the unported machinery: it is a
            // name search over configstrings this server publishes itself. Do that,
            // and only fall back to the placeholder if the search comes up empty --
            // a wrong-looking gun still beats no spawn.
            // ON, AND IT IS LOAD-BEARING. It was turned off once to rule it out by
            // measurement, and the client died on the spot:
            //     错误 1073 tag_weapon defaultvehicle
            // The profile's own viewmodelIndex is the PLACEHOLDER 1 ("was placeholder 1"
            // in this server's own log), and model configstring 1 on this map is
            // `defaultvehicle`, which has no tag_weapon -- so the client fatals trying to
            // attach the player's weapon to it. This override is not cosmetic: it is
            // covering for an unported viewmodel index, and it must stay until the real
            // one is derived.
            //
            // It also cannot be the invisible player, which is what the test was for:
            // viewmodelIndex travels in the PLAYERSTATE
            // (PlayerStateViewmodelIndexField, 10 bits) -- a player's OWN first-person
            // hands -- and CG_SetupClientCharacterInfo 0x00541800 reads none of it. Its
            // inputs are clientState +0x150, +0x154, +0x158, +0x7C and +0x4C.
            // OLMOD_VIEWHANDS_TF141=0 turns it off again; expect the fatal above.
            // TODO(CODOL): derive the character's own viewhands index and retire this.
            // viewmodelIndex travels in the PLAYERSTATE (PlayerStateViewmodelIndexField,
            // 10 bits) -- a player's OWN first-person hands -- and
            // CG_SetupClientCharacterInfo 0x00541800 reads none of it: its inputs are
            // clientState +0x150, +0x154, +0x158, +0x7C and +0x4C. So it cannot decide
            // whether another player's BODY draws. What it does do is replace every
            // character's own viewhands with tf141, which is why both players had them,
            // and that is a real wrongness worth not shipping.
            // OLMOD_VIEWHANDS_TF141=1 restores it.
            static const bool ViewhandsOverrideEnabled = [] {
                std::array<char, 8> value{};
                std::size_t size = 0;
                if (getenv_s(&size, value.data(), value.size(),
                        "OLMOD_VIEWHANDS_TF141") != 0 || size < 2)
                {
                    return true;
                }
                return value[0] != '0';
            }();
            // THE CHARACTER'S OWN HANDS, NOT tf141's. The resolver already produces
            // them: character 545 resolves to
            //     fpa_goose_ss_m_15, boo_empty_ss_s, fja_infbasea_sc_m_wht_00,
            //     han_infbasea_tf_m_00, hea_socomb_sc_m
            // and `han_` is the hands. viewmodelIndex, unlike modelIndex, really IS a
            // model configstring index -- it is ten bits, validCharacterCustomization
            // bounds it at 0x3FF, and resolveModelConfigStringIndex's 139 for
            // viewhands_tf141 is what has been putting tf141 hands on everyone.
            //
            // ORDER: the character's own hands, then tf141, and NEVER the profile's own
            // value. That last one is the placeholder 1, model configstring 1 is
            // `defaultvehicle`, and sending it kills the client outright --
            // `错误 1073 tag_weapon defaultvehicle`, measured. A wrong-but-valid pair of
            // hands beats a fatal.
            //
            // CACHE THE MISS TOO, and cache per character. resolveModelConfigStringIndex
            // SCANS UP TO 1024 CONFIGSTRINGS and this provider runs per frame per client;
            // storing only successes is what a player measured as "extremely laggy" the
            // last time this pattern was written. And do not latch on an EMPTY name list:
            // the names arrive from the DObj build a frame later than the first
            // customization.
            struct ViewhandsCacheEntry
            {
                std::uint16_t characterItemId{};
                std::uint16_t index{};
                bool resolved{};
            };
            static std::map<std::uint64_t, ViewhandsCacheEntry> ViewhandsCache;
            static std::atomic<std::uint16_t> CachedGenericViewhandsIndex{};
            auto viewmodelIndex = presentation->viewmodelIndex;
            std::optional<std::uint16_t> characterHands;
            auto &handsCache = ViewhandsCache[xuid];
            if (handsCache.characterItemId == presentation->characterItemId &&
                (handsCache.resolved || handsCache.index))
            {
                if (handsCache.resolved)
                    characterHands = handsCache.index;
            }
            else
            {
                const auto names = Bindings.characterModelNames(clientNum);
                if (!names.empty())
                {
                    handsCache.characterItemId = presentation->characterItemId;
                    handsCache.resolved = false;
                    handsCache.index = 1;   // asked, and the answer is remembered
                    for (const auto &name : names)
                    {
                        if (name.rfind("han_", 0) != 0)
                            continue;
                        // RESOLVE OR REGISTER, the same two-step the body uses. The
                        // map does not publish `han_infbasea_tf_m_00`, so resolving
                        // alone always failed and every player fell back to tf141's
                        // hands -- while the gamestate publisher had ALREADY given that
                        // exact name a band slot. Registering again returns the slot it
                        // already holds, so this simply uses it.
                        auto resolved = Bindings.resolveModelConfigStringIndex(name);
                        if (!resolved)
                            resolved = Server.registerOutfitModelConfigString(name);
                        if (resolved)
                        {
                            characterHands = *resolved;
                            handsCache.resolved = true;
                            handsCache.index = *resolved;
                            logGameServer(
                                "viewhands: the CHARACTER'S OWN hands index=" +
                                std::to_string(*resolved) + " name=" + name);
                        }
                        else
                        {
                            logGameServer(
                                "viewhands: character hands HAVE NO BAND SLOT name=" +
                                name + " -- falling back to " +
                                std::string(
                                    CodolGameServer::GenericCharacterViewhandsName));
                        }
                        break;
                    }
                }
            }
            if (characterHands)
            {
                viewmodelIndex = *characterHands;
            }
            else if (ViewhandsOverrideEnabled)
            {
                if (auto cached =
                        CachedGenericViewhandsIndex.load(std::memory_order_acquire))
                {
                    viewmodelIndex = cached;
                }
                else if (const auto resolved = Bindings.resolveModelConfigStringIndex(
                        CodolGameServer::GenericCharacterViewhandsName))
                {
                    CachedGenericViewhandsIndex.store(
                        *resolved, std::memory_order_release);
                    viewmodelIndex = *resolved;
                    logGameServer(
                        "viewhands model resolved index=" + std::to_string(*resolved) +
                        " name=" +
                        std::string(CodolGameServer::GenericCharacterViewhandsName) +
                        " (was placeholder " +
                        std::to_string(presentation->viewmodelIndex) + ")");
                }
            }
            // THE PLAYER MODEL INDEX IS NOT A MODEL CONFIGSTRING INDEX. Section 166.
            //
            // This block used to resolve the player's own body name to a MODEL BAND
            // INDEX and write it into customization.modelIndex, on the reasoning that a
            // model index must address the map's model band the way the viewhands index
            // above does. IT DOES NOT, and the override was the invisible player:
            //
            //   * the wire field is FOUR BITS (clientState index 17, +0x150), and
            //     validCharacterCustomization refuses anything outside 1..0xF. A band
            //     index is in the hundreds -- resolveModelConfigStringIndex returns 139
            //     for the viewhands right above -- so the customization this produced
            //     was INVALID.
            //   * an invalid customization is never pushed into snapshot clientInfos,
            //     and writeClientInfos then emits the REMOVE bit for a client that was
            //     in the observer's baseline. The observer CLEARS that clientInfo.
            //   * CG_SetupClientCharacterInfo 0x00541800 opens with
            //     `if (*(int *)(clientState + 0x150) <= 0) return;` and writes NO model
            //     names at all, so characterInfo+0x18 stays EMPTY and
            //     BG_UpdatePlayerDObj refuses to draw the LIVING player while letting
            //     the CORPSE through -- the flash on death, with a fallback body, which
            //     is where "a COMPLETELY DIFFERENT MODEL" came from in the first place.
            //   * and it was STICKY AND PER-PLAYER: the cache latched per character, and
            //     a body name the map's band does not publish left the override unset,
            //     so that player stayed visible. One visible, one invisible, flipping
            //     run to run with what happened to be in the band.
            //
            // What the field actually does, read off 0x00541800 and 0x0080E600: the
            // request's +0 word is NEVER READ by the resolver. Its only job is that
            // `> 0` gate. The BODY comes from characterItemId (+0x7C) through the
            // character definition table, and the retail corpus agrees the field only
            // ever carries 0, 6, 7 or 8 -- a four-value namespace, not a band index.
            //
            // So the bootstrap 6 is not a placeholder to be improved: it is a legal
            // value of the field, and the character is chosen elsewhere. Removing this
            // also takes the 1024-configstring scan back out of the per-frame provider.
            // TODO(CODOL): derive 6/7/8 per character once the selector is found; it is
            // cosmetic against the character id, not the thing that makes a body render.

            auto customization = CodolGameServer::SV_ResolveCharacterCustomization(
                presentation->selectionIds,
                presentation->female,
                presentation->color,
                viewmodelIndex,
                faction,
                presentation->characterItemId,
                presentation->recordItemIds);
            if (!customization)
                return customization;

            // THE BODY, AS A MODEL-BAND INDEX, so a player renders even when the
            // character system does not resolve. Section 168: 0x00541800 returns 0 and
            // its caller runs the fallback 0x00541BD0, which takes the base model name
            // from clientState +0x14 + 2568. We have never sent that field, so a client
            // that lost the character path had an EMPTY model name and drew nothing --
            // the invisible player, measured in both clients' own memory.
            //
            // Same two-step the outfit models use: the map's own band first, and only a
            // name the map never published gets a slot broadcast into it.
            //
            // CACHE THE MISS TOO, AND PER CHARACTER. resolveModelConfigStringIndex scans
            // up to 1024 configstrings and this provider runs per frame per client;
            // caching only successes is what a player measured as "extremely laggy".
            // And do not latch on an empty name list -- the names arrive from the DObj
            // build a frame after the first customization exists.
            struct BodyModelCacheEntry
            {
                std::uint16_t characterItemId{};
                std::uint16_t index{};
                bool asked{};
            };
            static std::map<std::uint64_t, BodyModelCacheEntry> BodyModelCache;
            auto &bodyCache = BodyModelCache[xuid];
            if (!bodyCache.asked ||
                bodyCache.characterItemId != customization->characterItemId)
            {
                // ASK THE CHARACTER RESOLVER, NOT THE DObj. characterModelNames reads
                // what the DObj build cached, and that arrives a frame or more after the
                // first customization exists -- so the first clientInfo writes went out
                // with a ZERO body index, and an observer that then never received the
                // 0 -> 418 change was left with an EMPTY model name for that slot.
                // Measured: one client held slot 0 at `model=fpa_goose_ss_m_15` and slot
                // 1 at `model=EMPTY rebuild=1` in the same line. The resolver answers
                // from the character record on the FIRST frame, so the field is right in
                // the very first write and never has to change.
                std::vector<std::string> names;
                if (auto body = Bindings.characterBodyModelName(*customization);
                    !body.empty())
                {
                    // THE BATTLECHATTER VOICE'S GENDER, from the one place it
                    // is actually stated. customization->female comes from the
                    // character definition and was measured false for a female
                    // character in a live match; the body model name says
                    // `..._sc_f` / `..._tf_m` and is right for 452 of the 456
                    // body models in the shipped zones. Pushed rather than
                    // stored on the customization because that struct is
                    // embedded in an address-keyed buffer whose size is pinned.
                    if (const auto female =
                            CodolGameServer::SV_BattleChatterFemaleFromModelName(
                                body))
                    {
                        Server.setBattleChatterVoiceFemale(clientNum, *female);
                    }
                    names.emplace_back(std::move(body));
                }
                if (names.empty())
                    names = Bindings.characterModelNames(clientNum);
                if (!names.empty())
                {
                    bodyCache.characterItemId = customization->characterItemId;
                    bodyCache.asked = true;
                    bodyCache.index = 0;
                    for (const auto &name : names)
                    {
                        if (name.rfind("fpa_", 0) != 0)
                            continue;
                        auto index = Bindings.resolveModelConfigStringIndex(name);
                        if (!index)
                            index = Server.registerOutfitModelConfigString(name);
                        if (index)
                        {
                            bodyCache.index = *index;
                            logGameServer(
                                "body model index=" + std::to_string(*index) +
                                " name=" + name +
                                " -- clientState +0x14, the model the client draws when"
                                " the character system does not resolve");
                        }
                        else
                        {
                            logGameServer(
                                "body model COULD NOT BE PUBLISHED name=" + name +
                                " -- this player has no fallback body");
                        }
                        break;
                    }
                }
            }
            customization->bodyModelConfigStringIndex = bodyCache.index;

            // THE OUTFIT, RESOLVED TO MODEL CONFIG-STRING INDEXES. The client derives
            // this character's DEFAULT models from the character item id on its own,
            // so only the extras an equipped piece adds have to travel, and they
            // travel as indexes into the map's model configstring band.
            //
            // A NAME THE BAND DOES NOT PUBLISH CANNOT BE SENT, and saying so is the
            // point of the log line below rather than silently dropping it: an
            // attachment index the client cannot resolve is a model it will look up
            // and miss, and this project has already paid once for handing the DObj
            // build something it could not dereference (section 67's sparse list).
            // Registering absent models into the band is the next step and is a
            // GAMESTATE change, not a per-spawn one.
            // ONCE PER OUTFIT, NOT ONCE PER FRAME. THIS PROVIDER IS CALLED FROM
            // ServerCore::runFrame FOR EVERY ACTIVE CLIENT, so anything expensive here
            // runs at the tick rate times the player count. characterOutfitAttachmentModels
            // resolves the character record TWICE through the native engine, and doing
            // that per frame cost a measured match its framerate AND left both players
            // unrendered -- the same lesson as never hooking a per-frame client function,
            // on the server side.
            //
            // The answer only changes when the OUTFIT changes, so it is keyed on the
            // inputs that decide it and recomputed on nothing else.
            struct OutfitCacheEntry
            {
                std::uint16_t characterItemId{};
                std::array<std::uint16_t, 12> recordItemIds{};
                std::array<std::uint16_t, 4> attachments{};
                std::array<std::uint32_t, 12> optionMask{};
                bool resolved{};
            };
            static std::map<std::uint64_t, OutfitCacheEntry> OutfitCache;
            auto &cached = OutfitCache[xuid];
            if (cached.resolved &&
                cached.characterItemId == customization->characterItemId &&
                cached.recordItemIds == customization->recordItemIds)
            {
                customization->outfitAttachmentModelIndexes = cached.attachments;
                CharacterOptionMasks[clientNum] = cached.optionMask;
                return customization;
            }
            cached.characterItemId = customization->characterItemId;
            cached.recordItemIds = customization->recordItemIds;
            cached.attachments = {};
            cached.optionMask = {};
            cached.resolved = true;

            // THE OUTFIT AS THE CLIENT READS IT: a selection mask, not a list of ids.
            //
            // Section 184. sub_80E600 -- the function CG_SetupClientCharacterInfo hands
            // netfields 21..32 to -- tests bit i of this block against option i of the
            // character definition's own list and renders optionList[i]. Sending the
            // item ids there (section 182) set whatever bits those ids spell, which is
            // precisely why pieces finally rendered and were the wrong ones.
            //
            // IT IS KEYED ON NOTHING PER-PROCESS, which is the property section 182e
            // proved was required: the character item id is already on the wire as
            // field 20, both sides reach the same per-character table through it, and
            // no decode key is involved anywhere.
            //
            // AN ID THAT IS NOT AN OPTION FOR THIS CHARACTER LEAVES ITS BIT CLEAR, so
            // the worst case here is the character's own default piece -- which is what
            // every match before section 182 rendered and what the player confirmed
            // looked right. This cannot render a WRONG piece; it can only fail to
            // render a right one, and the witness line says which.
            //
            // In the same cache as the attachments because it has the same two inputs
            // and the same reason not to run per frame.
            {
                std::string witness;
                if (Bindings.characterOptionSelectionMask(
                        customization->characterItemId,
                        customization->recordItemIds,
                        cached.optionMask,
                        &witness))
                {
                    CharacterOptionMasks[clientNum] = cached.optionMask;
                }
                else
                {
                    witness = "character option mask UNAVAILABLE character=" +
                        std::to_string(customization->characterItemId) +
                        " -- no option list, so the client renders this character's"
                        " defaults";
                }
                static std::string LastMaskReport;
                if (witness != LastMaskReport)
                {
                    LastMaskReport = witness;
                    logGameServer(witness);
                }
            }

            // OFF BY DEFAULT, AND HERE IS WHAT THE LIVE RUN MEASURED.
            //
            // Everything this side builds arrives correctly -- verified in the client's
            // own demo: `cs 2985 heg_dystopic_mask_ss_m`, `cs 2986
            // ves_teddybear_backpack_ss_m`, and a clientInfo carrying
            // attachModelIndex 418 and 417 beside characterItemId 545. And with those
            // attachments on the wire THE PLAYER DOES NOT RENDER AT ALL: both players
            // invisible, visible for a split second only as a corpse. Without them,
            // same build, same match, both render.
            //
            // So the model half is right and the TAG half is not. This sent tag index 0
            // on the reasoning that a character piece merges onto the base skeleton by
            // bone name, which is what this server does on its OWN DObj -- but that
            // path writes a stable EMPTY STRING, whereas the client resolves a tag
            // INDEX through configstrings this server never populates. Index 0 there is
            // not "no tag", it is a lookup that finds nothing, and the DObj build fails
            // for the whole player rather than for one attachment.
            //
            // AND THE REASONING ABOVE IS REFUTED BY RETAIL'S OWN WIRE. Section 181.
            //
            // The tag block is at 5896, not 12249 -- CG_SetupClientCharacterInfo
            // 0x541800 resolves each attachment as `model + 2568` and `tag + 5896`, and
            // 5896+28 is cs 5924 `tag_stowed_back`, which is the stowed weapon's tag.
            // Five independent checks agree, including
            // ServerMaterialConfigStringBase 4872 + 1024 == 5896 and 5896 + 64 ==
            // WeaponConfigStringBase 5960, 64 being exactly what six bits address.
            //
            // MEASURED ACROSS ALL 62 RETAIL DEMOS: players carry attachment tags 13, 14,
            // 21, 28, 30, 50, 51, 60, 62 and 63 in these very slots -- and ONLY index 28
            // ever has a configstring set. C-2021-7-18[21-59-51]clash sets NONE of the
            // tag block and still ships tags 50, 62 and 63. So the great majority of
            // retail's attachment tags resolve to an UNSET configstring, i.e. to an
            // EMPTY tag string, and the attachments render regardless.
            //
            // An empty tag is therefore NORMAL, not fatal -- which is also what this
            // server's own DObj has always done: it writes stable EMPTY strings into
            // characterInfo's ten attachment tags and the models build. "Index 0 is a
            // lookup that finds nothing and the DObj build fails for the whole player"
            // was reasoning, never a measurement, and the wire disagrees with it.
            //
            // So this defaults ON now. OLMOD_OUTFIT_ATTACHMENTS=0 forces it back off if
            // a run shows otherwise -- and the thing to watch is an INVISIBLE PLAYER,
            // because that is the failure the old reasoning predicted.
            // OFF AGAIN, AND THIS TIME BECAUSE THE CHANNEL IS KNOWN. Section 184i.
            //
            // These five model/tag pairs mount a model on one of the PLAYER's tags.
            // The only attachment retail was ever observed publishing in 62 demos is
            // `+0x018 = 172` with tag 28 = cs 5924 `tag_stowed_back` -- the STOWED
            // WEAPON on the player's back. They are not the outfit channel and never
            // were: an outfit piece is selected by BIT in netfields 21..32 and lands in
            // one of twelve prefix-named slots (cha/fpa/boo/fja/han/hea/ves/heg/elp/
            // knp/pat/eye), which is a different mechanism entirely.
            //
            // So section 182b's "a complete, resolvable, accepted model/tag pair
            // rendered NOTHING" was never a defect in the pair -- it was an outfit model
            // posted to the stowed-weapon channel, which correctly renders nothing.
            // Leaving it on occupies a slot retail uses for the weapon on the player's
            // back, and section 181f's "a tag meant for a sight blocks the ironsights"
            // lives in exactly this area.
            //
            // OLMOD_OUTFIT_ATTACHMENTS=1 forces it back on for a comparison run.
            static const bool OutfitAttachmentsEnabled = [] {
                const auto *const value = std::getenv("OLMOD_OUTFIT_ATTACHMENTS");
                return value && *value == '1';
            }();
            if (!OutfitAttachmentsEnabled)
                return customization;

            static std::string LastOutfitReport;
            const auto extras =
                Bindings.characterOutfitAttachmentModels(*customization);
            if (!extras.empty())
            {
                std::string resident;
                std::string missing;
                std::size_t slot = 0;
                for (const auto &name : extras)
                {
                    // The map's own band first; it costs nothing and needs no
                    // broadcast. Only a name the map never published gets a slot.
                    auto index = Bindings.resolveModelConfigStringIndex(name);
                    if (!index)
                        index = Server.registerOutfitModelConfigString(name);
                    if (!index)
                    {
                        missing += " " + name;
                        continue;
                    }
                    if (slot < customization->outfitAttachmentModelIndexes.size())
                    {
                        customization->outfitAttachmentModelIndexes[slot++] = *index;
                        resident += " " + std::to_string(*index) + ":" + name;
                    }
                }
                auto report = "outfit attachments xuid=" + std::to_string(xuid) +
                    " character=" + std::to_string(presentation->characterItemId) +
                    " extras=" + std::to_string(extras.size()) +
                    " resident=" + (resident.empty() ? " none" : resident) +
                    " NOT IN BAND=" + (missing.empty() ? " none" : missing);
                if (report != LastOutfitReport)
                {
                    LastOutfitReport = report;
                    logGameServer(report);
                }
            }
            cached.attachments = customization->outfitAttachmentModelIndexes;
            return customization;
        });
        Server.setSharedPmoveRunner([](
            CodolGameServer::SvNativePlayerState &nativePlayerState,
            const CodolGameServer::SvGameClientCommandState &commandState,
            const CodolGameServer::SvResolvedLoadout *const resolvedLoadout,
            const CodolGameServer::SvGlassState &glassState,
            const std::span<const CodolGameServer::SvCollisionEntity>
                collisionEntities,
            CodolGameServer::SvNativePmoveOutput &output) {
            if (!resolvedLoadout)
                return false;
            CodolGameServer::SvNativePmoveFailure failure{};
            const auto result = Bindings.runServerPmove(
                nativePlayerState,
                commandState.currentUserCmd,
                commandState.oldUserCmd,
                CodolGameServer::PlayerCollisionContentMask,
                true,
                glassState,
                collisionEntities,
                &failure);
            if (!result)
            {
                output.failure = failure;
                return false;
            }
            output = *result;
            return true;
        });
        Server.setWeaponMovementRunner([](
            const CodolGameServer::SvWeaponMovementFrameInput &input,
            CodolGameServer::SvWeaponMovementClientState &clientState,
            const CodolGameServer::SvResolvedLoadout *const resolvedLoadout,
            CodolGameServer::SvNativeWeaponMovementOutput &output) {
            const auto result = Bindings.runServerWeaponMovement(
                input, clientState, resolvedLoadout);
            if (!result)
                return false;
            output = *result;
            return true;
        });
        Server.setPlayerStateToEntityStateConverter([](
            CodolGameServer::SvNativePlayerState &nativePlayerState,
            CodolGameServer::SvNativeEntityState &nativeEntityState,
            CodolGameServer::SvNativeEntityStateProjection &projection) {
            return Bindings.playerStateToEntityState(
                nativePlayerState, nativeEntityState, projection);
        });
        Server.setDeathAnimationRunner([](
            CodolGameServer::SvNativePlayerState &nativePlayerState,
            const std::uint32_t randomSeed,
            const CodolGameServer::SvDeathAnimationConditions &conditions) {
            return Bindings.runServerDeathAnimation(
                nativePlayerState, randomSeed, conditions);
        });
        Server.setSpawnAnimationRunner([](
            CodolGameServer::SvNativePlayerState &nativePlayerState,
            const std::uint32_t randomSeed) {
            return Bindings.runServerSpawnAnimation(
                nativePlayerState, randomSeed);
        });
        Server.setPointTraceRunner([](
            const CodolGameServer::SvPointTraceRequest &request,
            const CodolGameServer::SvGlassState &glassState,
            const std::span<const CodolGameServer::SvCollisionEntity>
                collisionEntities) {
            return Bindings.traceServerPoint(
                request, glassState, collisionEntities);
        });
        Server.setRadiusDamageVisibilityRunner([](
            const CodolGameServer::SvRadiusDamageTraceRequest &request,
            const CodolGameServer::SvGlassState &glassState,
            const std::span<const CodolGameServer::SvCollisionEntity> collisionEntities) {
            return Bindings.traceRadiusDamageVisibility(request, glassState, collisionEntities);
        });
        Server.setCapsuleTraceRunner([](
            const std::array<float, 3> &start,
            const std::array<float, 3> &end,
            const CodolGameServer::TraceBounds &bounds,
            const std::uint32_t contentMask,
            const CodolGameServer::SvGlassState &glassState,
            const std::span<const CodolGameServer::SvCollisionEntity>
                collisionEntities,
            const CodolGameServer::SvTraceEntityFilter &filter) {
            return Bindings.traceServerCapsule(
                start,
                end,
                bounds,
                contentMask,
                glassState,
                collisionEntities,
                filter);
        });
        Server.setTriggerContactRunner([](
            const std::array<float, 3> &playerOrigin,
            const CodolGameServer::TraceBounds &playerBounds,
            const CodolGameServer::SvTriggerVolume &trigger) {
            return Bindings.contactBrushModel(
                playerOrigin,
                playerBounds,
                trigger.origin,
                trigger.angles,
                trigger.collision);
        });
        Server.setNativeEntityMirrorSynchronizer([](
            const CodolGameServer::SvNativeEntityMirrorPhase phase,
            const std::span<const CodolGameServer::SvCollisionEntity>
                collisionEntities,
            const std::span<const CodolGameServer::SvNativeEntityStateSource>
                entityStates,
            const std::uint32_t serverTime) {
            return Bindings.synchronizeNativeServerEntities(
                phase,
                collisionEntities,
                entityStates,
                serverTime);
        });
        // SECTION 190: hand the native playerState overlay the alt weapon, so
        // the mode slots at +0x3E8 / +0x3F0 stop being zero. Installed here
        // because EngineBindings owns the module base and the server library
        // must not reach for it directly.
        // SECTION 190: AND LET AN ALT WEAPON SHOOT.
        //
        // Once the server switches a player to their alt, every fire event
        // names a weapon SV_FindResolvedWeapon cannot find, and that path
        // returns Invalid and rejects the whole clientThink candidate -- the
        // player would freeze on the trigger. This resolves the alt on demand
        // instead of growing SvResolvedLoadout, which sits inside the client
        // state the address-keyed native buffer is sized against (section 184h).
        //
        // AND IT MUST NOT BECOME "ANY WEAPON MAY FIRE". The admitted set is
        // exactly the alts: the reverse of weaponDefinition +3720 over every
        // registered weapon, built once. A weapon nothing links to is still
        // refused, which is what the refusal is for.
        // THE DEFINITION BEHIND A GRANT. readWeaponSelection resolves ANY weapon
        // index into a full definition -- ammo index, clip index, clip size, max ammo
        // -- and the alt-only restriction below is a policy layer on top of it, not a
        // limit of the accessor. A grant needs the ammo fields or the weapon arrives
        // unfireable, so this is the same read with no allowlist.
        Server.setWeaponDefinitionResolver(
            [](const std::uint16_t weaponAssetIndex,
               CodolGameServer::SvResolvedWeapon &resolved) {
                if (!weaponAssetIndex)
                    return false;
                CodolGameServer::ClientWeaponSelection selection{};
                if (!Bindings.readWeaponSelection(weaponAssetIndex, selection))
                    return false;
                resolved = toResolvedWeapon(selection);
                return true;
            });
        CodolGameServer::SV_SetAltWeaponLookup(
            [](const std::uint16_t weaponAssetIndex,
               CodolGameServer::SvResolvedWeapon &resolved) {
                if (!weaponAssetIndex)
                    return false;
                static std::mutex altMutex;
                static std::unordered_map<std::uint16_t, std::uint16_t> altToHost;
                static bool built{};
                const std::lock_guard<std::mutex> guard(altMutex);
                if (!built)
                {
                    built = true;
                    for (std::uint32_t host = 1;
                         host < CodolGameServer::WeaponConfigStringCount;
                         ++host)
                    {
                        const auto alt = Bindings.altWeaponAssetIndex(host);
                        if (alt)
                            altToHost.emplace(
                                alt, static_cast<std::uint16_t>(host));
                    }
                    OlMod::RuntimeLog::write(
                        OlMod::RuntimeLog::Channel::GameServer,
                        "alt weapon table built pairs=" +
                            std::to_string(altToHost.size()));
                }
                if (!altToHost.contains(weaponAssetIndex))
                    return false;
                CodolGameServer::ClientWeaponSelection selection{};
                if (!Bindings.readWeaponSelection(weaponAssetIndex, selection))
                    return false;
                resolved = toResolvedWeapon(selection);
                return true;
            });
        // SECTION 191z: AND THE HOST -> ALT DIRECTION, WHICH IS THE ONE THE SPAWN
        // BOOTSTRAP NEEDED AND NEVER HAD.
        //
        // The lookup above answers "is this index an alt, and what is it made
        // of". `sv_client_spawn_mp.cpp` was calling it with the loadout's HOST
        // weapon, which is never a key in that map, so it returned false for
        // every weapon in every class and the alt never got a heldWeapons slot.
        // The log said so all along: `list2F4=1224,1226,0,0,0,0` -- two entries,
        // the primary and the secondary, and nothing after them.
        //
        // out.exe's finish-weapon-change routine (0x00424470) walks exactly that
        // array and stores a ZERO for any cmd.weapon it does not find, so an
        // alt outside the held list cannot become the current weapon however it
        // is requested. That is the second half of section 191y.
        CodolGameServer::SV_SetHostAltWeaponLookup(
            [](const std::uint16_t hostAssetIndex,
               CodolGameServer::SvResolvedWeapon &resolved) {
                if (!hostAssetIndex)
                    return false;
                const auto alt = Bindings.altWeaponAssetIndex(hostAssetIndex);
                if (!alt)
                    return false;
                CodolGameServer::ClientWeaponSelection selection{};
                if (!Bindings.readWeaponSelection(alt, selection))
                    return false;
                resolved = toResolvedWeapon(selection);
                return true;
            });
        // SECTION 190: and the same answer to the server world, which does the switch itself
        // on the alt-fire button's rising edge.
        //
        // OFF BY DEFAULT SINCE 2026-09-03, BECAUSE 0x100000 IS NOT THE ALT-FIRE BUTTON.
        // Section 190 read it off sub_425440's fire types and never confirmed it against a real
        // press. It is AIM DOWN SIGHTS. Measured in a live match, the player's words first:
        //
        //     "every time i right click it readys my weapon back and forth"
        //
        //     15:17:46 alt fire SWITCH client=0 from=1227 to=1228     <- one per right-click,
        //     15:17:47 alt fire SWITCH client=0 from=1227 to=1228        twenty-odd in ten seconds
        //
        // Always 1227->1228, never back, so the paired toggle does not even hold: every press
        // re-applies the switch and the client replays the weapon raise. That is a WORSE game
        // than no alt-fire at all, and it shipped enabled on the strength of a decompile.
        //
        // The rest of section 190 stands and is not reverted -- the alt weapon is registered,
        // linked, given ammo and a heldWeapons slot, and SV_LookupAltWeapon lets it shoot. Only
        // the TRIGGER was wrong. Set OLMOD_ALT_FIRE=1 to put the switch back while a real button
        // is being identified; OLMOD_ALT_FIRE_BUTTON already overrides which bit it watches, so
        // the pair is enough to find the right one without another build.
        // OFF AGAIN, AND 0x08000000 IS NOT A KEY EITHER.
        //
        // Second wrong trigger in two attempts, and the second one was mine. I
        // asked the player to press 3 in isolation, saw only 0x08000000, and
        // took it -- from TWO edges for TEN presses. A count that does not
        // match is not a detail to round off; it was the window telling me it
        // was contaminated.
        //
        // The labelled follow-up settles it: 63 edges of 0x08000000 in three
        // minutes INCLUDING a run on the idle second client that nobody was
        // touching. It is not a keypress. Most likely it is a HELD bit
        // flickering through sect.186's decode -- a delta packet's first
        // usercmd deltas against the client's last command, so a held button
        // reads as released and re-pressed and yields a rising edge per packet.
        //
        // WHAT THE SAME MEASUREMENT DID ESTABLISH: pressing 3 produces NO
        // distinct button bit at all. The only other bits seen were 0x00000001
        // (attack) and one 0x20100800 combination. So alt-fire on this build is
        // probably NOT a usercmd button, and the trigger has to be found on the
        // command channel instead. Binding a third bit off the same evidence
        // would be the same mistake twice more.
        //
        // The rest of sect.190 stands and is not reverted: the alt weapon is
        // registered, linked, given ammo and a heldWeapons slot, SV_LookupAltWeapon
        // lets it shoot, AND weapon movement now resolves it too -- which was a
        // real bug this hunt found and fixed. Only the TRIGGER is unknown.
        // ARMED. THE TRIGGER IS RIGHT AND THE SWITCH IS NOT LANDING YET.
        //
        // The action is "Weapon Attachments" on key 3 -- the HUD says so, and
        // the client has been renaming the gun to the alt on that key since
        // before any of this existed. It is not a `+` bind so it never reaches
        // a usercmd; it arrives as the reliable command `n 89`, ten presses to
        // ten commands.
        //
        // The switch then fires -- 65 times in one match, 1224->1225 -- and
        // `player-presentation` still reports weapon=1224 every time. So the
        // assignment is being undone between here and the wire, which is what
        // the player sees as "it just readies my weapon" rather than
        // transforming it. Which stage undoes it is now instrumented rather
        // than guessed (OLMOD_LOG_ALT_WEAPON=1).
        if (const auto *const altFire = std::getenv("OLMOD_ALT_FIRE");
            !(altFire && altFire[0] == '0' && !altFire[1]))
        {
            Server.setAltFireResolver([](const std::uint16_t weaponAssetIndex) {
                return Bindings.altWeaponAssetIndex(weaponAssetIndex);
            });
        }
        CodolGameServer::SV_SetAltWeaponResolver(
            [](const std::uint16_t weaponAssetIndex) {
                return Bindings.altWeaponAssetIndex(weaponAssetIndex);
            });
        Server.setClientEventsHandler([](
            CodolGameServer::SvPlayerState &playerState,
            CodolGameServer::SvGameEntity &entity,
            CodolGameServer::SvNativePlayerState &nativePlayerState,
            const CodolGameServer::SvWeaponAimState &weaponAimState,
            const float currentAimSpreadScale,
            const std::uint32_t serverTime,
            CodolGameServer::SvGlassState &glassState,
            CodolGameServer::SvGlassDamageState &glassDamageState,
            const CodolGameServer::SvGlassMapMetadata &glassMetadata,
            const std::span<const CodolGameServer::SvCollisionEntity>
                collisionEntities,
            const std::span<const CodolGameServer::SvDamageablePlayerView>
                damageablePlayers,
            const CodolGameServer::SvResolvedLoadout *const resolvedLoadout,
            const std::span<const CodolGameServer::SvNativePredictableEvent>
                events) {
            const auto uavWeapon = playerState.rewardActionType == 1 &&
                playerState.rewardActionWeapon && std::ranges::any_of(events, [&](const auto &event) {
                    return event.parameter == playerState.rewardActionWeapon;
                })
                ? Bindings.resolveUavWeapon() : std::nullopt;
            return CodolGameServer::SV_HandleClientEventsDetailed(
                playerState,
                entity,
                currentAimSpreadScale,
                resolvedLoadout,
                events,
                [&nativePlayerState, &weaponAimState, serverTime](
                    const CodolGameServer::SvResolvedWeapon &weapon) {
                    return Bindings.buildServerWeaponFireBasis(
                        nativePlayerState,
                        weaponAimState,
                        weapon,
                        static_cast<std::int32_t>(serverTime));
                },
                [serverTime,
                 &glassState,
                 &glassDamageState,
                 &glassMetadata,
                 collisionEntities,
                 damageablePlayers](
                    CodolGameServer::SvPlayerState &playerState,
                    CodolGameServer::SvGameEntity &entity,
                    const CodolGameServer::SvResolvedWeapon &weapon,
                    const CodolGameServer::SvWeaponFireBasis &basis,
                    const CodolGameServer::SvWeaponSpreadResult &spread,
                    const CodolGameServer::SvFireWeaponEvent &event) {
                    if(const auto special=Server.factorySpecialWeapon(weapon.weaponAssetIndex)) {
                        const auto launch=CodolGameServer::SV_LaunchFactorySpecial(*special,basis,
                            static_cast<std::uint16_t>(playerState.clientNum),serverTime);
                        if(!launch)return CodolGameServer::SvFireWeaponResult::Failed;
                        entity.pendingEntitySpawns.push_back(*launch);
                        return CodolGameServer::SvFireWeaponResult::Applied;
                    }
                    return executeServerBulletFire(
                        serverTime,
                        glassState,
                        glassDamageState,
                        glassMetadata,
                        collisionEntities,
                        damageablePlayers,
                        playerState,
                        entity,
                        weapon,
                        basis,
                        spread,
                        event);
                },
                [serverTime,
                 &glassState,
                 &glassDamageState,
                 &glassMetadata,
                 collisionEntities,
                 damageablePlayers](
                    CodolGameServer::SvPlayerState &,
                    CodolGameServer::SvGameEntity &entity,
                    const CodolGameServer::SvResolvedWeapon &weapon,
                    const CodolGameServer::SvWeaponFireBasis &basis) {
                    return executeServerMeleeAttack(
                        serverTime,
                        glassState,
                        glassDamageState,
                        glassMetadata,
                        collisionEntities,
                        damageablePlayers,
                        entity,
                        weapon,
                        basis);
                },
                Server.playerEquipment(playerState.clientNum, playerState.spawnGeneration),
                [&nativePlayerState,&weaponAimState,serverTime](auto &ps,auto &entity,const auto &weapon) {
                    const auto kind=Server.factorySpecialWeapon(weapon.weaponAssetIndex);
                    if(!kind)return CodolGameServer::SvFireWeaponResult::DeferredImpact;
                    const auto basis=Bindings.buildServerOffhandFireBasis(nativePlayerState,weaponAimState,weapon,
                        static_cast<std::int32_t>(serverTime));
                    if(!basis)return CodolGameServer::SvFireWeaponResult::Failed;
                    const auto parameters=Bindings.resolveGrenadeLaunchParameters(weapon.weaponAssetIndex);
                    if(!parameters)return CodolGameServer::SvFireWeaponResult::Failed;
                    const auto offhand=CodolGameServer::SV_ReadNativeOffhandState(nativePlayerState);
                    const auto launch=CodolGameServer::SV_ComputeGrenadeLaunch({
                        .parameters=*parameters,.basis=*basis,.playerVelocity=ps.velocity,
                        .angularVelocity={120,75,0},.time=serverTime,.owner=static_cast<std::uint16_t>(ps.clientNum),
                        .heldFuseMilliseconds=std::max(0,offhand.grenadeTimeLeft),
                        // Original fire/shrink demos: stationary angular trajectory
                        // throughout flight. Monkey also needs upright presentation.
                        .rotate=!(*kind>=CodolGameServer::SvFactorySpecialKind::FireTrap &&
                            *kind<=CodolGameServer::SvFactorySpecialKind::Monkey)},
                        [](const auto &v,auto &out){const auto angles=Bindings.directionToAngles(v);if(!angles)return false;out=*angles;return true;});
                    if(!launch)return CodolGameServer::SvFireWeaponResult::Failed;
                    entity.pendingEntitySpawns.push_back(*launch);
                    CodolGameServer::SV_ClearNativeGrenadeTimer(nativePlayerState);
                    ps.grenadeTimeLeft=0;
                    static unsigned offhandReports{};
                    if(offhandReports++<64)
                        logGameServer("Factory offhand released name="+weapon.weaponName+
                            " asset="+std::to_string(weapon.weaponAssetIndex)+
                            " heldFuse="+std::to_string(offhand.grenadeTimeLeft));
                    return CodolGameServer::SvFireWeaponResult::Applied;
                }, uavWeapon ? &*uavWeapon : nullptr);
        });
        Installed = CodolGameServer::installFrameHook(Bindings, onServerFrame);
        if (Installed)
            installClientInputPatches(role);
        logGameServer(std::string("game server frame hook ") +
            (Installed ? "installed" : "failed"));
    }

    bool ensureInstalled()
    {
        initialize();
        return Installed;
    }
}

extern "C" __declspec(dllexport) void __cdecl onStartup(bool)
{
    initialize();
}

extern "C" __declspec(dllexport) void __cdecl onInitialized(bool)
{
    initialize();
}

// The archived CODOL Localnetworking loader retains only modules exposing this
// entrypoint. This plugin does not proxy a hostname, but must remain loaded once
// its in-process frame hook is installed.
extern "C" __declspec(dllexport) void *__cdecl Createserver(const char *)
{
    return nullptr;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerSetEnabled(const bool enabled)
{
    if (!ensureInstalled())
        return false;
    if (enabled && !Network.start())
        return false;
    Server.setEnabled(enabled);
    if (!enabled)
    {
        Network.stop();
        const std::lock_guard lock(WorldAssetMutex);
        PendingWorldAsset.reset();
    }
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetStatus(
    std::uint32_t *enabled,
    std::uint32_t *frameNumber,
    std::uint32_t *serverTime)
{
    if (!ensureInstalled() || !enabled || !frameNumber || !serverTime)
        return false;
    const auto status = Server.status();
    *enabled = status.enabled;
    *frameNumber = status.frameNumber;
    *serverTime = status.serverTime;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetNetworkStatus(
    std::uint32_t *connectedClients)
{
    if (!ensureInstalled() || !connectedClients)
        return false;
    *connectedClients = Server.status().connectedClients;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetNetchanStatus(
    std::uint32_t *packetsReceived,
    std::uint32_t *packetsDropped,
    std::uint32_t *reliableCommandsReceived)
{
    if (!ensureInstalled() || !packetsReceived || !packetsDropped || !reliableCommandsReceived)
        return false;
    const auto status = Server.status();
    *packetsReceived = status.netchanPacketsReceived;
    *packetsDropped = status.netchanPacketsDropped;
    *reliableCommandsReceived = status.reliableCommandsReceived;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl
    CODOL_GameServerGetConnectionlessDiagnosticsV1(
        std::uint32_t *handled,
        std::uint32_t *connected,
        std::uint32_t *rejected,
        std::uint32_t *lastConnectedIpv4,
        std::uint32_t *lastConnectedPort,
        std::uint32_t *lastConnectedClientSlot,
        std::uint32_t *lastRejectedIpv4,
        std::uint32_t *lastRejectedPort,
        char *lastRejectedReason,
        const std::uint32_t lastRejectedReasonCapacity,
        std::uint32_t *lastRejectedReasonLength)
{
    if (!ensureInstalled() || !handled || !connected || !rejected ||
        !lastConnectedIpv4 || !lastConnectedPort ||
        !lastConnectedClientSlot || !lastRejectedIpv4 || !lastRejectedPort ||
        !lastRejectedReason || !lastRejectedReasonCapacity ||
        !lastRejectedReasonLength)
    {
        return false;
    }
    const auto status = Server.connectionlessDiagnostics();
    *handled = status.handled;
    *connected = status.connected;
    *rejected = status.rejected;
    *lastConnectedIpv4 = status.lastConnectedPeer.ipv4;
    *lastConnectedPort = status.lastConnectedPeer.port;
    *lastConnectedClientSlot = status.lastConnectedClientSlot;
    *lastRejectedIpv4 = status.lastRejectedPeer.ipv4;
    *lastRejectedPort = status.lastRejectedPeer.port;
    return CodolGameServer::SV_CopyStatusText(
        status.lastRejectedReason,
        { lastRejectedReason, lastRejectedReasonCapacity },
        *lastRejectedReasonLength);
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetClientIngressStatus(
    const std::uint32_t clientNum,
    std::uint32_t *state,
    std::uint32_t *lastPacketTime,
    std::uint32_t *incomingSequence,
    std::uint32_t *outgoingSequence,
    std::uint32_t *messageAcknowledge,
    std::uint32_t *reliableAcknowledge,
    std::uint32_t *lastClientReliableSequence,
    std::int32_t *deltaMessage,
    std::uint32_t *lastMoveCommandCount,
    std::uint32_t *acceptedPackets,
    std::uint32_t *duplicatePackets,
    std::uint32_t *rejectedPackets,
    std::uint32_t *decodedCommandsSize,
    std::uint8_t *decodedCommandsPrefix,
    const std::uint32_t decodedCommandsPrefixCapacity)
{
    if (!ensureInstalled() || !state || !lastPacketTime || !incomingSequence ||
        !outgoingSequence || !messageAcknowledge || !reliableAcknowledge ||
        !lastClientReliableSequence || !deltaMessage || !lastMoveCommandCount ||
        !acceptedPackets || !duplicatePackets || !rejectedPackets ||
        !decodedCommandsSize || !decodedCommandsPrefix || !decodedCommandsPrefixCapacity)
    {
        return false;
    }
    const auto status = Server.clientIngressStatus(clientNum);
    if (!status)
        return false;
    *state = static_cast<std::uint32_t>(status->state);
    *lastPacketTime = status->lastPacketTime;
    *incomingSequence = status->incomingSequence;
    *outgoingSequence = status->outgoingSequence;
    *messageAcknowledge = status->messageAcknowledge;
    *reliableAcknowledge = status->reliableAcknowledge;
    *lastClientReliableSequence = status->lastClientReliableSequence;
    *deltaMessage = status->deltaMessage;
    *lastMoveCommandCount = status->lastMoveCommandCount;
    *acceptedPackets = status->acceptedPackets;
    *duplicatePackets = status->duplicatePackets;
    *rejectedPackets = status->rejectedPackets;
    *decodedCommandsSize = status->decodedCommandsSize;
    const auto prefixSize = std::min<std::size_t>(
        status->decodedCommandsSize,
        std::min<std::size_t>(
            status->decodedCommandsPrefix.size(), decodedCommandsPrefixCapacity));
    std::copy_n(
        status->decodedCommandsPrefix.begin(), prefixSize, decodedCommandsPrefix);
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetClientGameStateStage(
    const std::uint32_t clientNum,
    std::uint32_t *stage)
{
    if (!ensureInstalled() || !stage)
        return false;
    const auto status = Server.clientIngressStatus(clientNum);
    if (!status)
        return false;
    *stage = status->gameStateUpdateStage;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetClientLoadingStatus(
    const std::uint32_t clientNum,
    std::uint32_t *profileReceived,
    std::uint32_t *profileRequired,
    std::uint32_t *profileComplete,
    std::uint32_t *gameStateStage,
    std::uint32_t *gameStateMessage,
    std::uint64_t *sessionGeneration,
    std::uint32_t *generationActive)
{
    if (!ensureInstalled() || !profileReceived || !profileRequired ||
        !profileComplete || !gameStateStage || !gameStateMessage ||
        !sessionGeneration || !generationActive)
        return false;
    const auto status = Server.clientIngressStatus(clientNum);
    if (!status)
        return false;
    *profileReceived = status->profileStatsReceivedMask;
    *profileRequired = status->profileStatsRequiredMask;
    *profileComplete = status->profileStatsComplete ? 1u : 0u;
    *gameStateStage = status->gameStateUpdateStage;
    *gameStateMessage = status->gamestateMessageNum;
    *sessionGeneration = status->sessionGeneration;
    *generationActive = status->sessionGenerationActive ? 1u : 0u;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetClientUserCmdStatus(
    const std::uint32_t clientNum,
    std::uint32_t *commandTime,
    std::uint32_t *buttons,
    std::uint32_t *angle0,
    std::uint32_t *angle1,
    std::uint32_t *angle2,
    std::uint32_t *weapon,
    std::uint32_t *offHandIndex,
    std::uint32_t *lastWeaponAltModeSwitch,
    std::int32_t *forwardMove,
    std::int32_t *rightMove)
{
    if (!ensureInstalled() || !commandTime || !buttons || !angle0 || !angle1 || !angle2 ||
        !weapon || !offHandIndex || !lastWeaponAltModeSwitch || !forwardMove || !rightMove)
    {
        return false;
    }
    const auto status = Server.clientIngressStatus(clientNum);
    if (!status || !status->lastReceivedUserCmd)
        return false;
    const auto &command = *status->lastReceivedUserCmd;
    *commandTime = command.commandTime;
    *buttons = command.buttons;
    *angle0 = command.angles[0];
    *angle1 = command.angles[1];
    *angle2 = command.angles[2];
    *weapon = command.weapon;
    *offHandIndex = command.offHandIndex;
    *lastWeaponAltModeSwitch = command.lastWeaponAltModeSwitch;
    *forwardMove = command.forwardMove;
    *rightMove = command.rightMove;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetClientRejectStatus(
    const std::uint32_t clientNum,
    std::uint32_t *sequence,
    std::uint32_t *serverId,
    std::uint32_t *messageAcknowledge,
    std::uint32_t *reliableAcknowledge,
    std::uint32_t *decodedCommandsSize,
    std::uint8_t *decodedCommandsPrefix,
    const std::uint32_t decodedCommandsPrefixCapacity,
    char *reason,
    const std::uint32_t reasonCapacity,
    std::uint32_t *reasonLength)
{
    if (!ensureInstalled() || !sequence || !serverId || !messageAcknowledge ||
        !reliableAcknowledge || !decodedCommandsSize || !decodedCommandsPrefix ||
        !decodedCommandsPrefixCapacity || !reason || !reasonCapacity || !reasonLength)
    {
        return false;
    }
    const auto status = Server.clientIngressStatus(clientNum);
    if (!status || !status->lastPacketReject)
        return false;
    const auto &reject = *status->lastPacketReject;
    *sequence = reject.sequence;
    *serverId = reject.serverId;
    *messageAcknowledge = reject.messageAcknowledge;
    *reliableAcknowledge = reject.reliableAcknowledge;
    *decodedCommandsSize = reject.decodedCommandsSize;
    const auto prefixSize = std::min<std::size_t>(
        reject.decodedCommandsSize,
        std::min<std::size_t>(
            reject.decodedCommandsPrefix.size(), decodedCommandsPrefixCapacity));
    std::copy_n(
        reject.decodedCommandsPrefix.begin(), prefixSize, decodedCommandsPrefix);
    return CodolGameServer::SV_CopyStatusText(
        reject.reason,
        { reason, reasonCapacity },
        *reasonLength);
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetClientReliableCommandStatus(
    const std::uint32_t clientNum,
    std::uint32_t *sequence,
    char *command,
    const std::uint32_t commandCapacity,
    std::uint32_t *commandLength)
{
    if (!ensureInstalled() || !sequence || !command || !commandCapacity || !commandLength)
        return false;
    const auto status = Server.clientIngressStatus(clientNum);
    if (!status)
        return false;
    return CodolGameServer::SV_CopyClientReliableCommandStatus(
        *status,
        *sequence,
        { command, commandCapacity },
        *commandLength);
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetClientMenuResponseStatus(
    const std::uint32_t clientNum,
    std::uint32_t *sequence,
    std::uint32_t *serverId,
    std::uint32_t *menuIndex,
    char *menuName,
    const std::uint32_t menuNameCapacity,
    std::uint32_t *menuNameLength,
    char *response,
    const std::uint32_t responseCapacity,
    std::uint32_t *responseLength)
{
    if (!ensureInstalled() || !sequence || !serverId || !menuIndex || !menuName ||
        !menuNameCapacity || !menuNameLength || !response || !responseCapacity ||
        !responseLength)
    {
        return false;
    }
    const auto status = Server.clientIngressStatus(clientNum);
    if (!status || !status->lastMenuResponse)
        return false;
    const auto &menuResponse = *status->lastMenuResponse;
    *sequence = menuResponse.sequence;
    *serverId = menuResponse.serverId;
    *menuIndex = menuResponse.menuIndex;
    return CodolGameServer::SV_CopyStatusText(
               menuResponse.menuName,
               { menuName, menuNameCapacity },
               *menuNameLength) &&
        CodolGameServer::SV_CopyStatusText(
               menuResponse.response,
               { response, responseCapacity },
               *responseLength);
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetClientGameplayStatus(
    const std::uint32_t clientNum,
    std::uint32_t *gameplayState,
    std::uint32_t *loadoutSequence,
    char *selectedLoadout,
    const std::uint32_t selectedLoadoutCapacity,
    std::uint32_t *selectedLoadoutLength)
{
    if (!ensureInstalled() || !gameplayState || !loadoutSequence || !selectedLoadout ||
        !selectedLoadoutCapacity || !selectedLoadoutLength)
    {
        return false;
    }
    const auto status = Server.clientIngressStatus(clientNum);
    if (!status)
        return false;
    *gameplayState = static_cast<std::uint32_t>(status->gameplayState);
    *loadoutSequence = status->loadoutSequence;
    return CodolGameServer::SV_CopyStatusText(
        status->selectedLoadout,
        { selectedLoadout, selectedLoadoutCapacity },
        *selectedLoadoutLength);
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerConfigureSession(
    const std::uint8_t *descriptor,
    const std::uint32_t descriptorSize)
{
    if (!ensureInstalled() || !descriptor || !descriptorSize)
        return false;
    return Server.configureSessionDescriptor({ descriptor, descriptorSize });
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetSessionStatus(
    std::uint32_t *configured)
{
    if (!ensureInstalled() || !configured)
        return false;
    *configured = Server.status().sessionConfigured;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl
    CODOL_GameServerGetDedicatedSessionConsumptionStatus(
        std::uint64_t *queuedRequestId,
        std::uint64_t *processedRequestId,
        std::uint32_t *stage,
        std::int32_t *failedClassIndex,
        std::uint32_t *requestedClassMask,
        std::uint32_t *resolvedClassMask,
        std::uint32_t *characterFailure,
        std::uint32_t *characterRecordIndex,
        std::uint32_t *characterItemId)
{
    if (!ensureInstalled() || !queuedRequestId || !processedRequestId || !stage ||
        !failedClassIndex || !requestedClassMask || !resolvedClassMask ||
        !characterFailure || !characterRecordIndex || !characterItemId)
    {
        return false;
    }
    const std::lock_guard lock(DedicatedControlMutex);
    const auto status = DedicatedSessionConsumption.status();
    *queuedRequestId = status.queuedRequestId;
    *processedRequestId = status.processedRequestId;
    *stage = static_cast<std::uint32_t>(status.stage);
    *failedClassIndex = status.failedClassIndex;
    *requestedClassMask = status.requestedClassMask;
    *resolvedClassMask = status.resolvedClassMask;
    *characterFailure = status.characterFailure;
    *characterRecordIndex = status.characterRecordIndex;
    *characterItemId = status.characterItemId;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetLoadoutPreparationStatus(
    std::uint32_t *attemptCount,
    std::int32_t *currentCharacter,
    std::uint32_t *resolvedClassMask,
    std::uint32_t *registeredClassMask,
    std::uint32_t *prepared,
    std::int32_t *preparedCharacter)
{
    if (!ensureInstalled() || !attemptCount || !currentCharacter ||
        !resolvedClassMask || !registeredClassMask || !prepared ||
        !preparedCharacter)
    {
        return false;
    }
    const std::lock_guard lock(LoadoutMutex);
    *attemptCount = LoadoutPreparation.attemptCount;
    *currentCharacter = LoadoutPreparation.currentCharacter;
    *resolvedClassMask = LoadoutPreparation.resolvedClassMask;
    *registeredClassMask = LoadoutPreparation.registeredClassMask;
    *prepared = PreparedLoadouts.has_value();
    *preparedCharacter = PreparedLoadouts && !PreparedLoadouts->members.empty()
        ? static_cast<std::int32_t>(
              PreparedLoadouts->members.front().characterIndex)
        : -1;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl
    CODOL_GameServerGetGameStateConfigurationStatus(
        std::uint32_t *attemptCount,
        std::uint32_t *stage,
        std::int32_t *failedClassIndex,
        std::uint32_t *registeredClassMask,
        std::uint32_t *firstDynamicWeaponAssetIndex)
{
    if (!ensureInstalled() || !attemptCount || !stage || !failedClassIndex ||
        !registeredClassMask || !firstDynamicWeaponAssetIndex)
    {
        return false;
    }
    const auto status = GameStateConfiguration.status();
    *attemptCount = status.attemptCount;
    *stage = static_cast<std::uint32_t>(status.stage);
    *failedClassIndex = status.failedClassIndex;
    *registeredClassMask = status.registeredClassMask;
    *firstDynamicWeaponAssetIndex = status.firstDynamicWeaponAssetIndex;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetLoadoutResolveFailure(
    std::uint32_t *failure)
{
    if (!ensureInstalled() || !failure)
        return false;
    *failure = static_cast<std::uint32_t>(Bindings.loadoutResolveFailure());
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl
    CODOL_GameServerGetRegisteredCharacterStatus(std::int32_t *registeredCharacter)
{
    if (!ensureInstalled() || !registeredCharacter)
        return false;
    const std::lock_guard lock(LoadoutMutex);
    const auto &members = RegisteredSessionAssets.members();
    *registeredCharacter = !members.empty()
        ? static_cast<std::int32_t>(
              members.begin()->second.
                  characterPresentation.characterIndex)
        : -1;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl
    CODOL_GameServerGetRegisteredCharacterPresentation(
        std::uint32_t *characterIndex,
        std::uint32_t *female,
        std::uint32_t *color,
        std::uint32_t *viewmodelIndex,
        std::uint16_t *selectionIds,
        const std::uint32_t selectionCapacity)
{
    if (!ensureInstalled() || !characterIndex || !female || !color ||
        !viewmodelIndex || !selectionIds ||
        selectionCapacity < CodolGameServer::ClientCharacterPresentation{}.
            selectionIds.size())
    {
        return false;
    }
    const std::lock_guard lock(LoadoutMutex);
    const auto &members = RegisteredSessionAssets.members();
    if (members.empty())
        return false;
    const auto &presentation =
        members.begin()->second.characterPresentation;
    *characterIndex = presentation.characterIndex;
    *female = presentation.female ? 1u : 0u;
    *color = presentation.color;
    *viewmodelIndex = presentation.viewmodelIndex;
    std::ranges::copy(
        presentation.selectionIds, selectionIds);
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerConfigureGameState(
    const char *mapName,
    const char *gameType,
    const std::uint32_t configStringChecksum,
    const std::uint32_t checksumFeed)
{
    if (!ensureInstalled() || !mapName || !*mapName || !gameType || !*gameType)
        return false;
    if (!Bindings.CCS_Initialized())
        return false;
    const auto nativeConfigStringChecksum = Bindings.CCS_GetChecksum();
    if (configStringChecksum && configStringChecksum != nativeConfigStringChecksum)
        return false;
    return configureGameState(
        mapName, gameType, nativeConfigStringChecksum, checksumFeed);
}

namespace
{
    bool configureBooking(
        const char *command,
        std::optional<OlMod::DedicatedSession::BookingSelection> selection,
        std::optional<OlMod::DedicatedSession::MatchRules> matchRules,
        const CodolGameServer::SvConfigStringGenerationRequirement
            generationRequirement)
    {
        if (!ensureInstalled() || !command || !*command)
            return false;

        // This gate refuses a match in five different ways and used to report all
        // of them as one bare "booking configuration failed", which costs a whole
        // restart-and-rejoin cycle to narrow down. Name the check that refused.
        const auto refuse = [&](const std::string &reason) {
            logGameServer("booking refused: " + reason);
            return false;
        };

        const auto parsed = CodolGameServer::SV_ParseBookingCommand(command);
        if (!parsed)
            return refuse("unparsable command: " + std::string(command));

        std::optional<CodolGameServer::SvResolvedBooking> booking;
        if (selection)
        {
            // Only compare what the command actually carried. CODOL's own
            // booking grammar has no playlist id at all -- it names the map and
            // the gametype instead -- so comparing a defaulted zero against the
            // capture refused every match on this build.
            if (parsed->hasPlaylistId && selection->playlistId != parsed->playlistId)
            {
                return refuse(
                    "capture/command playlist disagree: capture=" +
                    std::to_string(selection->playlistId) + " command=" +
                    std::to_string(parsed->playlistId));
            }
            if (!parsed->mapName.empty() &&
                (parsed->mapName != selection->mapName ||
                    parsed->gameType != selection->gameType))
            {
                logGameServer(
                    "booking command and capture name different matches (using the "
                    "command): command=" + parsed->gameType + " on " + parsed->mapName +
                    " capture=" + selection->gameType + " on " + selection->mapName);
            }
            // The captured rotation index is NOT the booked one, and requiring
            // them equal refused every free-for-all match. MEASURED twice: the
            // command said rotation 5 and the capture's map was mp_fav_tropical,
            // which is entry [5] of the ffa rotation; the command said 8 and the
            // map was mp_seatown, entry [8]. Both times the captured MAP tracked
            // the command exactly while the captured index did not - it read 5
            // against a command of 8.
            //
            // It survived until now because every previous test was sd on
            // playlist 26 rotation 0, and a stale or misread byte compares equal
            // to 0 for free. Free-for-all is the first rotation here that rolls a
            // non-zero index, which is what exposed it.
            //
            // The index is only ever used for this comparison - the match is
            // resolved from the captured map and gametype below - so report the
            // disagreement and carry on rather than refuse on a field that has
            // been shown not to mean what its name says.
            if (parsed->hasRotationIndex &&
                selection->rotationIndex != parsed->rotationIndex)
            {
                logGameServer(
                    "booking rotation index differs (using the captured map): "
                    "capture=" + std::to_string(selection->rotationIndex) +
                    " command=" + std::to_string(parsed->rotationIndex) +
                    " map=" + selection->mapName);
            }
            booking = CodolGameServer::SV_ResolveBooking(
                command,
                CodolGameServer::SvPlaylistEntry{
                    .mapName = parsed->mapName.empty()
                        ? selection->mapName
                        : parsed->mapName,
                    .gameType = parsed->gameType.empty()
                        ? selection->gameType
                        : parsed->gameType,
                    .weight = 1,
                });
        }
        else
        {
            const std::filesystem::path playlistPath =
                L"./Ayria/Assets/Alwaysoffline/1004/Server/mp_playlists_shipRetail_release.info";
            std::ifstream stream(playlistPath, std::ios::binary);
            if (!stream)
                return false;
            const std::string text{
                std::istreambuf_iterator<char>(stream),
                std::istreambuf_iterator<char>() };
            const auto playlists = CodolGameServer::SV_ParsePlaylistDocument(text);
            if (!playlists)
                return false;
            booking = CodolGameServer::SV_ResolveBooking(command, *playlists);
        }
        if (!booking)
        {
            return refuse(
                selection
                    ? "rotation did not resolve map=" + selection->mapName +
                        " gametype=" + selection->gameType
                    : std::string("rotation did not resolve from the publisher playlist"));
        }
        if (OlMod::processRole() == OlMod::ProcessRole::Dedicated)
        {
            // matchGameType_ is compared against gameState.gameType every frame
            // (sv_main_mp.cpp:979), and that one is the ENGINE name, so this has
            // to be translated too or the two vocabularies never meet and
            // uiGameRules is silently never produced.
            if (!matchRules)
                return refuse("no match rules reached the dedicated server");
            const auto engineGameType =
                CodolGameServer::SV_EngineGameType(booking->rotation.gameType);
            if (!Server.configureMatchRules(*matchRules, engineGameType))
            {
                return refuse(
                    "match rules invalid booked=" + booking->rotation.gameType +
                    " engine=" + std::string(engineGameType) +
                    " version=" + std::to_string(matchRules->playlistVersion) +
                    " score=" + std::to_string(matchRules->scoreLimit) +
                    " time=" + std::to_string(matchRules->timeLimitMinutes) +
                    " roundSwitch=" + std::to_string(matchRules->roundSwitch) +
                    " roundLimit=" + std::to_string(matchRules->roundLimit) +
                    " winLimit=" + std::to_string(matchRules->winLimit));
            }
        }
        logGameServer("booking accepted, taking the booking and loadout locks");
        {
            const std::lock_guard lock(BookingMutex);
            static_cast<void>(Bindings.CCS_Initialized());
            PendingBooking.assign(
                booking->rotation,
                Bindings.CCS_GetChecksum(),
                generationRequirement);
            const std::lock_guard loadoutLock(LoadoutMutex);
            ++LoadoutPrepareRequestSequence;
        }
        logGameServer("booking configured");
        return true;
    }
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerConfigureBooking(
    const char *command)
{
    std::optional<OlMod::DedicatedSession::BookingSelection> selection;
    if (const auto native = Bindings.readClientBookingSelection();
        native && native->rotationIndex >= 0)
    {
        // PINNED TO DEATHMATCH, DELIBERATELY. Section 187o.
        //
        // Section 187i taught this server to read the client's booking, and it
        // immediately started serving what the player had actually selected -- which
        // was `cha`, Charge, a TEAM mode. That is more correct than the old behaviour
        // of always serving dm, and it broke shooting: dm.lua leaves every player at
        // team None so `issameteam` is false for every pair, while cha.lua puts players
        // on real sides and gates scoring on `issameteam`. Two players on one side
        // cannot hurt each other, and "I still can't do damage" is exactly what that
        // looks like from inside the game.
        //
        // Dated precisely rather than guessed: deaths at 17:20:09 and 17:47:59 both ran
        // `booked=dm`; every cycle after the booking port ran `booked=cha` and produced
        // none, with 94 and 66 bullet-hits staged against zero kills.
        //
        // So the MAP, playlist and rotation come from the player's own booking -- that
        // is the part worth having -- and the gametype is pinned until team assignment
        // puts two players on opposing sides. The override says so out loud rather than
        // silently disagreeing with the menu.
        auto bookedGameType = native->gameType;
        // Preserve Zombie Siege's own script.  Pinning zm to dm suppresses the
        // spawner/window/barrier controller even though the Factory map still
        // appears to load.
        if (bookedGameType != "zm" && !gameTypeIsTeamless(bookedGameType))
        {
            static std::string lastPinReport;
            auto report = "booking gametype PINNED " + bookedGameType +
                " -> dm (section 187o: team modes leave both players on one side and"
                " nothing can be damaged); map=" + native->mapName + " kept";
            if (report != lastPinReport)
            {
                lastPinReport = report;
                logGameServer(report);
            }
            bookedGameType = "dm";
        }
        selection = OlMod::DedicatedSession::BookingSelection{
            .playlistId = native->playlistSlot,
            .rotationIndex = static_cast<std::uint32_t>(native->rotationIndex),
            .mapName = native->mapName,
            .gameType = bookedGameType,
        };
    }
    return configureBooking(command, std::move(selection), std::nullopt);
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetGameStateStatus(
    std::uint32_t *configured,
    std::uint32_t *messagesSent)
{
    if (!ensureInstalled() || !configured || !messagesSent)
        return false;
    const auto status = Server.status();
    *configured = status.gameStateConfigured;
    *messagesSent = status.gameStateMessagesSent;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetLoadingStatus(
    std::uint32_t *activeClients,
    std::uint32_t *updatesReceived)
{
    if (!ensureInstalled() || !activeClients || !updatesReceived)
        return false;
    const auto status = Server.status();
    *activeClients = status.activeClients;
    *updatesReceived = status.gameStateUpdatesReceived;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetSnapshotStatus(
    std::uint32_t *messagesSent)
{
    if (!ensureInstalled() || !messagesSent)
        return false;
    *messagesSent = Server.status().snapshotMessagesSent;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetSnapshotDeltaStatus(
    std::uint32_t *fullMessagesSent,
    std::uint32_t *deltaMessagesSent,
    std::uint32_t *messageAcknowledge,
    std::uint32_t *outgoingSequence)
{
    if (!ensureInstalled() || !fullMessagesSent || !deltaMessagesSent ||
        !messageAcknowledge || !outgoingSequence)
    {
        return false;
    }
    const auto status = Server.status();
    *fullMessagesSent = status.fullSnapshotMessagesSent;
    *deltaMessagesSent = status.deltaSnapshotMessagesSent;
    *messageAcknowledge = status.messageAcknowledge;
    *outgoingSequence = status.outgoingSequence;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetWorldStatus(
    std::uint32_t *spawnConfigured)
{
    if (!ensureInstalled() || !spawnConfigured)
        return false;
    *spawnConfigured = Server.status().worldSpawnConfigured;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl
    CODOL_GameServerGetEntityDamageStatusV1(
        const std::uint32_t entityNum,
        std::uint32_t *generation,
        std::uint32_t *kind,
        std::int32_t *health,
        std::uint32_t *canTakeDamage,
        std::uint32_t *cannotDie,
        std::uint32_t *stageIndex,
        std::uint32_t *modelIndex)
{
    if (!ensureInstalled() || !generation || !kind || !health ||
        !canTakeDamage || !cannotDie || !stageIndex || !modelIndex)
    {
        return false;
    }
    const auto status = Server.worldEntityDamageStatus(entityNum);
    if (!status)
        return false;
    *generation = status->generation;
    *kind = static_cast<std::uint32_t>(status->state.kind);
    *health = status->state.health;
    *canTakeDamage = status->state.canTakeDamage;
    *cannotDie = status->state.cannotDie;
    *stageIndex = status->state.stageIndex;
    *modelIndex = status->modelIndex;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetSdStatusV1(
    std::uint32_t *roundConfigured,
    std::uint32_t *roundArmed,
    std::uint32_t *roundCompleted,
    std::uint32_t *roundsPlayed,
    std::uint32_t *roundWinner,
    std::uint32_t *roundEndReason,
    std::uint32_t *bombConfigured,
    std::uint32_t *bombPhase,
    std::uint32_t *attackers,
    std::uint32_t *defenders,
    std::uint32_t *attackersAlive,
    std::uint32_t *defendersAlive,
    std::uint32_t *carrierClientNum,
    std::uint32_t *planterClientNum,
    std::uint32_t *defuserClientNum,
    std::uint32_t *plantedSiteLabel,
    std::uint32_t *phaseStartServerTime,
    std::uint32_t *plantedServerTime)
{
    if (!ensureInstalled() || !roundConfigured || !roundArmed ||
        !roundCompleted || !roundsPlayed || !roundWinner || !roundEndReason ||
        !bombConfigured || !bombPhase || !attackers || !defenders ||
        !attackersAlive || !defendersAlive || !carrierClientNum ||
        !planterClientNum || !defuserClientNum || !plantedSiteLabel ||
        !phaseStartServerTime || !plantedServerTime)
    {
        return false;
    }
    const auto status = Server.sdRuntimeStatus();
    const auto optionalClient = [](const std::optional<std::uint32_t> value) {
        return value.value_or(std::numeric_limits<std::uint32_t>::max());
    };
    *roundConfigured = status.round.configured;
    *roundArmed = status.round.armed;
    *roundCompleted = status.round.completed;
    *roundsPlayed = status.round.roundsPlayed;
    *roundWinner = static_cast<std::uint32_t>(status.round.winner);
    *roundEndReason = static_cast<std::uint32_t>(status.round.endReason);
    *bombConfigured = status.bomb.configured;
    *bombPhase = static_cast<std::uint32_t>(status.bomb.phase);
    *attackers = status.teams.attackers;
    *defenders = status.teams.defenders;
    *attackersAlive = status.teams.attackersAlive;
    *defendersAlive = status.teams.defendersAlive;
    *carrierClientNum = optionalClient(status.bomb.carrierClientNum);
    *planterClientNum = optionalClient(status.bomb.planterClientNum);
    *defuserClientNum = optionalClient(status.bomb.defuserClientNum);
    *plantedSiteLabel = status.bomb.plantedSiteLabel &&
            status.bomb.plantedSiteLabel->size() == 1
        ? static_cast<unsigned char>((*status.bomb.plantedSiteLabel)[0])
        : 0;
    *phaseStartServerTime = status.bomb.phaseStartServerTime;
    *plantedServerTime = status.bomb.plantedServerTime;
    return true;
}

// Read-only SD presentation diagnostic. This deliberately exposes the
// authoritative playerstate objective slots, not a client-side interpretation.
extern "C" __declspec(dllexport) bool __cdecl
    CODOL_GameServerGetWorldObjectiveStatusV1(
        const std::uint32_t clientNum,
        std::uint32_t *activeCount,
        std::uint32_t *state0,
        std::uint32_t *icon0,
        std::uint32_t *state1,
        std::uint32_t *icon1,
        std::uint32_t *state2,
        std::uint32_t *icon2)
{
    if (!ensureInstalled() || !activeCount || !state0 || !icon0 || !state1 ||
        !icon1 || !state2 || !icon2)
    {
        return false;
    }
    const auto state = Server.worldPlayerState(clientNum);
    if (!state)
        return false;
    const auto &objectives = state->objectives;
    *activeCount = static_cast<std::uint32_t>(std::ranges::count_if(
        objectives, [](const auto &objective) {
            return objective.state != CodolGameServer::SvObjectiveState::Empty;
        }));
    const auto write = [](const auto &objective, std::uint32_t *stateOut,
                          std::uint32_t *iconOut) {
        *stateOut = static_cast<std::uint32_t>(objective.state);
        *iconOut = objective.icon;
    };
    write(objectives[0], state0, icon0);
    write(objectives[1], state1, icon1);
    write(objectives[2], state2, icon2);
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl
    CODOL_GameServerGetWorldClientThinkStatus(
        const std::uint32_t clientNum,
        std::uint32_t *lastAttemptedCommandTime,
        std::uint32_t *lastCommittedCommandTime,
        std::uint32_t *failureStage,
        std::uint32_t *failureCount)
{
    if (!ensureInstalled() || !lastAttemptedCommandTime ||
        !lastCommittedCommandTime || !failureStage || !failureCount)
    {
        return false;
    }
    const auto status = Server.worldClientThinkStatus(clientNum);
    if (!status)
        return false;
    *lastAttemptedCommandTime = status->lastAttemptedCommandTime;
    *lastCommittedCommandTime = status->lastCommittedCommandTime;
    *failureStage = static_cast<std::uint32_t>(status->failureStage);
    *failureCount = status->failureCount;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl
    CODOL_GameServerGetWorldPredictableEventStatusV1(
        const std::uint32_t clientNum,
        std::uint32_t *commandTime,
        std::int32_t *oldSequence,
        std::int32_t *currentSequence,
        std::uint32_t *count,
        std::int32_t *events,
        std::int32_t *eventParameters,
        std::uint32_t *handlerResult)
{
    if (!ensureInstalled() || !commandTime || !oldSequence ||
        !currentSequence || !count || !events || !eventParameters ||
        !handlerResult)
    {
        return false;
    }
    const auto status = Server.worldPredictableEventStatus(clientNum);
    if (!status)
        return false;
    *commandTime = status->commandTime;
    *oldSequence = status->oldSequence;
    *currentSequence = status->currentSequence;
    *count = status->count;
    for (std::size_t index{}; index < status->events.size(); ++index)
    {
        events[index] = status->events[index].event;
        eventParameters[index] = status->events[index].parameter;
    }
    *handlerResult = static_cast<std::uint32_t>(status->handlerResult);
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl
    CODOL_GameServerGetWorldBulletExecutionStatusV1(
        const std::uint32_t clientNum,
        std::uint32_t *commandTime,
        float *start,
        float *end,
        float *fraction,
        std::uint32_t *hitType,
        std::uint32_t *hitEntityNum,
        std::uint32_t *partGroup,
        std::uint32_t *surfaceFlags,
        std::uint32_t *playerDamageStaged,
        std::uint32_t *entityDamageStaged,
        std::uint32_t *result)
{
    if (!ensureInstalled() || !commandTime || !start || !end || !fraction ||
        !hitType || !hitEntityNum || !partGroup || !surfaceFlags ||
        !playerDamageStaged || !entityDamageStaged || !result)
    {
        return false;
    }
    const auto status = Server.worldBulletExecutionStatus(clientNum);
    if (!status)
        return false;
    *commandTime = status->commandTime;
    std::ranges::copy(status->start, start);
    std::ranges::copy(status->end, end);
    *fraction = status->trace.fraction;
    *hitType = status->trace.hitType;
    *hitEntityNum = status->hitEntityNum.value_or(
        CodolGameServer::BulletNoneEntityNum);
    *partGroup = status->trace.partGroup;
    *surfaceFlags = status->trace.surfaceFlags;
    *playerDamageStaged = status->playerDamageStaged;
    *entityDamageStaged = status->entityDamageStaged;
    *result = static_cast<std::uint32_t>(status->result);
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl
    CODOL_GameServerGetWorldBulletExecutionStatusV2(
        const std::uint32_t clientNum,
        std::uint32_t *commandTime,
        float *start,
        float *end,
        float *fraction,
        std::uint32_t *hitType,
        std::uint32_t *hitEntityNum,
        std::uint32_t *modelIndex,
        std::uint32_t *partName,
        std::uint32_t *partGroup,
        std::uint32_t *surfaceFlags,
        std::uint32_t *playerDamageStaged,
        std::uint32_t *entityDamageStaged,
        std::uint32_t *result)
{
    if (!ensureInstalled() || !commandTime || !start || !end || !fraction ||
        !hitType || !hitEntityNum || !modelIndex || !partName || !partGroup ||
        !surfaceFlags || !playerDamageStaged || !entityDamageStaged || !result)
    {
        return false;
    }
    const auto status = Server.worldBulletExecutionStatus(clientNum);
    if (!status)
        return false;
    *commandTime = status->commandTime;
    std::ranges::copy(status->start, start);
    std::ranges::copy(status->end, end);
    *fraction = status->trace.fraction;
    *hitType = status->trace.hitType;
    *hitEntityNum = status->hitEntityNum.value_or(
        CodolGameServer::BulletNoneEntityNum);
    *modelIndex = status->trace.modelIndex;
    *partName = status->trace.partName;
    *partGroup = status->trace.partGroup;
    *surfaceFlags = status->trace.surfaceFlags;
    *playerDamageStaged = status->playerDamageStaged;
    *entityDamageStaged = status->entityDamageStaged;
    *result = static_cast<std::uint32_t>(status->result);
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetWorldPlayerSampleV1(
    const std::uint32_t clientNum,
    CodolWorldPlayerSampleV1 *output,
    const std::uint32_t outputSize)
{
    if (!ensureInstalled() || !output || outputSize < sizeof(*output))
        return false;
    const auto sample = Server.worldPlayerSample(clientNum);
    if (!sample)
        return false;
    *output = makeWorldPlayerSampleV1(*sample);
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetWorldPlayerSampleV2(
    const std::uint32_t clientNum,
    CodolWorldPlayerSampleV2 *output,
    const std::uint32_t outputSize)
{
    if (!ensureInstalled() || !output || outputSize < sizeof(*output))
        return false;
    const auto sample = Server.worldPlayerSample(clientNum);
    if (!sample)
        return false;
    const auto &state = sample->playerState;
    *output = {
        .base = makeWorldPlayerSampleV1(*sample, sizeof(*output), 2),
        .pmType = state.pmType,
        .viewAngles = state.viewAngles,
        .deltaAngles = state.deltaAngles,
        .ladderVector = state.ladderVector,
        .sprintButtonUpRequired = state.sprintButtonUpRequired,
        .sprintDelay = state.sprintDelay,
        .lastSprintStart = state.lastSprintStart,
        .lastSprintEnd = state.lastSprintEnd,
        .sprintStartMaxLength = state.sprintStartMaxLength,
        .mantleYaw = state.mantleYaw,
        .mantleTimer = state.mantleTimer,
        .mantleTransitionIndex = state.mantleTransitionIndex,
        .mantleFlags = state.mantleFlags,
        .weaponPositionFraction = state.weaponPositionFraction,
        .weaponAnim = { state.weaponAnim[0], state.weaponAnim[1] },
        .weaponTime = state.weaponTime,
        .weaponDelay = state.weaponDelay,
        .weaponState = { state.weaponState[0], state.weaponState[1] },
        .weaponHandFlags = {
            state.weaponHandFlags[0], state.weaponHandFlags[1] },
        .weaponShotCount = {
            state.weaponShotCount[0], state.weaponShotCount[1] },
        .legsTimer = state.legsTimer,
        .legsAnim = state.legsAnim,
        .torsoTimer = state.torsoTimer,
        .torsoAnim = state.torsoAnim,
        .proneDirection = state.proneDirection,
        .proneDirectionPitch = state.proneDirectionPitch,
        .proneTorsoPitch = state.proneTorsoPitch,
        .bobCycle = state.bobCycle,
    };
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetWorldPlayerStatus(
    const std::uint32_t clientNum,
    std::uint32_t *commandTime,
    float *origin,
    float *velocity,
    std::uint32_t *groundEntityNum,
    std::uint32_t *gravity,
    std::uint32_t *speed,
    float *moveSpeedScaleMultiplier)
{
    if (!ensureInstalled() || !commandTime || !origin || !velocity ||
        !groundEntityNum || !gravity || !speed || !moveSpeedScaleMultiplier)
    {
        return false;
    }
    const auto playerState = Server.worldPlayerState(clientNum);
    if (!playerState)
        return false;
    *commandTime = playerState->commandTime;
    std::copy(playerState->origin.begin(), playerState->origin.end(), origin);
    std::copy(playerState->velocity.begin(), playerState->velocity.end(), velocity);
    *groundEntityNum = playerState->groundEntityNum;
    *gravity = playerState->gravity;
    *speed = playerState->speed;
    *moveSpeedScaleMultiplier = playerState->moveSpeedScaleMultiplier;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetWorldPlayerPmoveStatus(
    const std::uint32_t clientNum,
    std::uint32_t *pmTime,
    std::uint32_t *pmFlags,
    std::uint32_t *jumpTime,
    float *jumpOriginZ)
{
    if (!ensureInstalled() || !pmTime || !pmFlags || !jumpTime || !jumpOriginZ)
        return false;
    const auto playerState = Server.worldPlayerState(clientNum);
    if (!playerState)
        return false;
    *pmTime = playerState->pmTime;
    *pmFlags = playerState->pmFlags;
    *jumpTime = playerState->jumpTime;
    *jumpOriginZ = playerState->jumpOriginZ;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetWorldPlayerFlagsStatus(
    const std::uint32_t clientNum,
    std::uint32_t *eFlags,
    std::uint32_t *otherFlags)
{
    if (!ensureInstalled() || !eFlags || !otherFlags)
        return false;
    const auto playerState = Server.worldPlayerState(clientNum);
    if (!playerState)
        return false;
    *eFlags = playerState->eFlags;
    *otherFlags = playerState->otherFlags;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetWorldPlayerViewHeightStatus(
    const std::uint32_t clientNum,
    float *current,
    std::int32_t *target,
    std::int32_t *lerpTarget,
    std::int32_t *lerpTime,
    std::uint32_t *lerpDown)
{
    if (!ensureInstalled() || !current || !target || !lerpTarget || !lerpTime ||
        !lerpDown)
    {
        return false;
    }
    const auto playerState = Server.worldPlayerState(clientNum);
    if (!playerState)
        return false;
    *current = playerState->viewHeightCurrent;
    *target = playerState->viewHeightTarget;
    *lerpTarget = playerState->viewHeightLerpTarget;
    *lerpTime = playerState->viewHeightLerpTime;
    *lerpDown = playerState->viewHeightLerpDown ? 1u : 0u;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetWorldPlayerHealthStatus(
    const std::uint32_t clientNum,
    std::uint32_t *health,
    std::uint32_t *maxHealth,
    std::uint32_t *damageEvent,
    std::uint32_t *damageYaw,
    std::uint32_t *damagePitch,
    std::uint32_t *damageCount)
{
    if (!ensureInstalled() || !health || !maxHealth || !damageEvent ||
        !damageYaw || !damagePitch || !damageCount)
    {
        return false;
    }
    const auto playerState = Server.worldPlayerState(clientNum);
    if (!playerState)
        return false;
    *health = playerState->health;
    *maxHealth = playerState->maxHealth;
    *damageEvent = playerState->damageEvent;
    *damageYaw = playerState->damageYaw;
    *damagePitch = playerState->damagePitch;
    *damageCount = playerState->damageCount;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetWorldEventStatus(
    std::uint32_t *sequence,
    std::uint32_t *type,
    std::uint32_t *serverTime,
    std::uint32_t *clientNum,
    std::uint32_t *spawnSequence,
    std::uint32_t *spawnGeneration)
{
    if (!ensureInstalled() || !sequence || !type || !serverTime || !clientNum ||
        !spawnSequence || !spawnGeneration)
    {
        return false;
    }
    const auto event = Server.worldLastEvent();
    if (!event)
        return false;
    *sequence = event->sequence;
    *type = static_cast<std::uint32_t>(event->type);
    *serverTime = event->serverTime;
    *clientNum = event->clientNum;
    *spawnSequence = event->spawnSequence;
    *spawnGeneration = event->spawnGeneration;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetWorldEventWeaponStatus(
    std::uint32_t *sequence,
    std::uint32_t *weaponAssetIndex,
    char *weaponName,
    const std::uint32_t weaponNameCapacity,
    std::uint32_t *weaponNameLength)
{
    if (!ensureInstalled() || !sequence || !weaponAssetIndex || !weaponName ||
        !weaponNameCapacity || !weaponNameLength)
    {
        return false;
    }
    const auto event = Server.worldLastEvent();
    if (!event || event->type != CodolGameServer::SvWorldEventType::WeaponSwitchStarted)
        return false;
    *sequence = event->sequence;
    *weaponAssetIndex = event->weaponAssetIndex;
    return CodolGameServer::SV_CopyStatusText(
        event->weaponName,
        { weaponName, weaponNameCapacity },
        *weaponNameLength);
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetWorldPlayerWeaponStatus(
    const std::uint32_t clientNum,
    std::uint32_t *currentWeaponAssetIndex,
    std::int32_t *weaponTime,
    std::int32_t *weaponDelay,
    std::uint32_t *weaponState,
    std::uint32_t *weaponAnim,
    std::uint32_t *clipAmmo,
    std::uint32_t *weaponType,
    std::uint32_t *fireType,
    std::uint32_t *definitionFireDelay,
    std::uint32_t *definitionFireTime)
{
    if (!ensureInstalled() || !currentWeaponAssetIndex || !weaponTime ||
        !weaponDelay || !weaponState || !weaponAnim || !clipAmmo ||
        !weaponType || !fireType || !definitionFireDelay || !definitionFireTime)
    {
        return false;
    }
    const auto sample = Server.worldPlayerSample(clientNum);
    if (!sample)
        return false;
    if (!sample->weapon)
        return false;

    *currentWeaponAssetIndex = sample->weapon->currentWeaponAssetIndex;
    *weaponTime = sample->weapon->weaponTime;
    *weaponDelay = sample->weapon->weaponDelay;
    *weaponState = sample->weapon->weaponState;
    *weaponAnim = sample->weapon->weaponAnim;
    *clipAmmo = sample->weapon->clipAmmo;
    *weaponType = sample->weapon->weaponType;
    *fireType = sample->weapon->fireType;
    *definitionFireDelay = sample->weapon->definitionFireDelay;
    *definitionFireTime = sample->weapon->definitionFireTime;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetWorldResolvedLoadoutStatus(
    const std::uint32_t clientNum,
    std::uint32_t *primaryWeaponAssetIndex,
    std::uint32_t *secondaryWeaponAssetIndex)
{
    if (!ensureInstalled() || !primaryWeaponAssetIndex || !secondaryWeaponAssetIndex)
        return false;
    const auto loadout = Server.worldResolvedLoadout(clientNum);
    if (!loadout)
        return false;
    *primaryWeaponAssetIndex = loadout->primary.weaponAssetIndex;
    *secondaryWeaponAssetIndex = loadout->secondary.weaponAssetIndex;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetGameStateReadinessStatus(
    std::uint32_t *clientsReady)
{
    if (!ensureInstalled() || !clientsReady)
        return false;
    *clientsReady = Server.status().clientsReadyForGameState;
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetConstantConfigStringStatus(
    std::uint32_t *initialized,
    std::uint32_t *checksum)
{
    if (!ensureInstalled() || !initialized || !checksum)
        return false;
    *initialized = Bindings.CCS_Initialized();
    *checksum = Bindings.CCS_GetChecksum();
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetTransportStatus(
    std::uint32_t *bound,
    std::uint32_t *port,
    std::uint32_t *packetsReceived,
    std::uint32_t *packetsSent,
    std::uint32_t *lastSocketError)
{
    if (!ensureInstalled() || !bound || !port || !packetsReceived || !packetsSent || !lastSocketError)
        return false;
    const auto status = Network.status();
    *bound = status.bound;
    *port = status.port;
    *packetsReceived = status.packetsReceived;
    *packetsSent = status.packetsSent;
    *lastSocketError = static_cast<std::uint32_t>(status.lastSocketError);
    return true;
}

extern "C" __declspec(dllexport) bool __cdecl CODOL_GameServerGetTransportTimingStatus(
    std::uint32_t *lastPacketReceivedTime,
    std::uint32_t *lastPacketSentTime)
{
    if (!ensureInstalled() || !lastPacketReceivedTime || !lastPacketSentTime)
        return false;
    const auto status = Network.status();
    *lastPacketReceivedTime = status.lastPacketReceivedTime;
    *lastPacketSentTime = status.lastPacketSentTime;
    return true;
}

BOOL WINAPI DllMain(const HINSTANCE module, const DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
    {
        DisableThreadLibraryCalls(module);
        initialize();
    }
    return TRUE;
}
