#include "MatchmakingService.hpp"

#include "ByteBuffer.hpp"
#include "../../shared/DedicatedControl.hpp"
#include "../../shared/ProcessRole.hpp"

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <optional>
#include <vector>

namespace
{
    constexpr auto BlobType = std::uint8_t{ 0x13 };
    constexpr auto FindServersQuery = std::uint32_t{ 1 };
    constexpr auto FindPlaylistLobbiesQuery = std::uint32_t{ 3 };

    const std::array<std::uint8_t, 8> &processSessionId()
    {
        static const auto value = []
        {
            LARGE_INTEGER frequency{};
            LARGE_INTEGER counter{};
            QueryPerformanceFrequency(&frequency);
            QueryPerformanceCounter(&counter);

            constexpr auto NanosecondsPerSecond = std::uint64_t{ 1'000'000'000 };
            const auto ticks = static_cast<std::uint64_t>(counter.QuadPart);
            const auto ticksPerSecond = static_cast<std::uint64_t>(frequency.QuadPart);
            const auto nanoseconds =
                NanosecondsPerSecond * (ticks / ticksPerSecond) +
                NanosecondsPerSecond * (ticks % ticksPerSecond) / ticksPerSecond;

            std::array<std::uint8_t, 8> id{};
            std::memcpy(id.data(), &nanoseconds, sizeof(nanoseconds));

            const auto seed = static_cast<unsigned int>(std::time(nullptr)) & 0xFEFEFEFEU;
            std::srand(seed);
            auto index = std::size_t{ 1 };
            do
            {
                id[index] ^= id[index - 1];
                index = static_cast<std::size_t>(std::rand() % 8 + 1);
            }
            while (index < 7);
            return id;
        }();
        return value;
    }

    std::uint64_t processSessionNumericId()
    {
        auto result = std::uint64_t{};
        const auto &bytes = processSessionId();
        std::memcpy(&result, bytes.data(), sizeof(result));
        return result;
    }

    bool readSessionProperties(
        AlwaysofflineRe::Demonware::ByteBuffer &input,
        nlohmann::json &properties)
    {
        std::vector<std::uint8_t> hostAddress;
        std::uint32_t gameType{};
        std::uint32_t maxPlayers{};
        if (!input.readBlob(hostAddress) || !input.readU32(gameType) || !input.readU32(maxPlayers))
            return false;

        std::vector<std::uint8_t> demonwareData;
        if (!input.empty() && input.remaining().front() == BlobType)
        {
            if (!input.readBlob(demonwareData))
                return false;
        }
        else
        {
            const auto remaining = input.remaining();
            demonwareData.assign(remaining.begin(), remaining.end());
        }

        properties = {
            { "Demonware.Hostaddress", std::move(hostAddress) },
            { "Session.Gametype", gameType },
            { "Players.Max", maxPlayers },
            { "Session.Demonware", std::move(demonwareData) },
        };
        return true;
    }

    std::optional<std::uint32_t> matchmakingQueryKind(
        const std::span<const std::uint8_t> payload)
    {
        AlwaysofflineRe::Demonware::ByteBuffer input(payload);
        std::uint32_t kind{};
        if (!input.readU32(kind))
            return std::nullopt;
        return kind;
    }

    bool isServerSession(const nlohmann::json &properties)
    {
        const auto role = properties.find("Session.Role");
        return role != properties.end() && role->is_string() &&
            role->get_ref<const std::string &>() == "server";
    }

    std::vector<std::uint8_t> jsonBytes(
        const nlohmann::json &properties,
        const char *key)
    {
        const auto found = properties.find(key);
        if (found == properties.end() || !found->is_array())
            return {};
        try
        {
            return found->get<std::vector<std::uint8_t>>();
        }
        catch (const nlohmann::json::exception &)
        {
            return {};
        }
    }

    std::string jsonString(
        const nlohmann::json &properties,
        const char *key)
    {
        const auto found = properties.find(key);
        if (found == properties.end() || !found->is_string())
            return {};
        return found->get<std::string>();
    }

    // The UID advertised as the room's host. DELIBERATELY NOT the player's own CODOID: the
    // client addresses its room-join message to this value, and with its own id there it
    // messages itself and discards the reply, reporting "the room is not responding".
    // Measured in the C# reference, LobbyServer/Services/MatchMaking.cs.
    constexpr std::uint64_t RoomHostUid = 1000001;

    std::uint32_t jsonU32(
        const nlohmann::json &properties,
        const char *key,
        const std::uint32_t fallback)
    {
        const auto found = properties.find(key);
        if (found == properties.end() || !found->is_number_unsigned())
            return fallback;
        const auto value = found->get<std::uint64_t>();
        return value <= UINT32_MAX ? static_cast<std::uint32_t>(value) : fallback;
    }

    std::uint64_t nextControlRequestId()
    {
        static std::atomic_uint64_t requestId{};
        return ++requestId;
    }

    bool configureLocalGameServer(const std::span<const std::uint8_t> descriptor)
    {
        if (descriptor.empty())
            return false;
        const auto module = GetModuleHandleW(L"CodolGameServer.Localnet32");
        if (!module)
            return false;
        const auto callback = reinterpret_cast<bool(__cdecl *)(const std::uint8_t *, std::uint32_t)>(
            GetProcAddress(module, "CODOL_GameServerConfigureSession"));
        if (!callback || descriptor.size() > UINT32_MAX ||
            !callback(descriptor.data(), static_cast<std::uint32_t>(descriptor.size())))
        {
            return false;
        }
        const auto setEnabled = reinterpret_cast<bool(__cdecl *)(bool)>(
            GetProcAddress(module, "CODOL_GameServerSetEnabled"));
        return setEnabled && setEnabled(true);
    }

    std::optional<AlwaysofflineRe::Demonware::GameServerEndpoint>
    localGameServerEndpoint()
    {
        const auto module = GetModuleHandleW(L"CodolGameServer.Localnet32");
        if (!module)
            return std::nullopt;
        const auto getStatus = reinterpret_cast<bool(__cdecl *)(
            std::uint32_t *, std::uint32_t *, std::uint32_t *, std::uint32_t *, std::uint32_t *)>(
                GetProcAddress(module, "CODOL_GameServerGetTransportStatus"));
        if (!getStatus)
            return std::nullopt;

        std::uint32_t bound{};
        std::uint32_t port{};
        std::uint32_t packetsReceived{};
        std::uint32_t packetsSent{};
        std::uint32_t lastSocketError{};
        if (!getStatus(
                &bound, &port, &packetsReceived, &packetsSent, &lastSocketError) ||
            !bound || !port || port > UINT16_MAX)
        {
            return std::nullopt;
        }
        return AlwaysofflineRe::Demonware::GameServerEndpoint{
            // This is the address the client actually dials: it reaches
            // properties["Demonware.Hostaddress"] through commonAddress().
            .ipv4 = OlMod::DedicatedControl::configuredHostIpv4(),
            .port = static_cast<std::uint16_t>(port),
        };
    }

    bool configureDedicatedGameServer(
        const std::span<const std::uint8_t> descriptor)
    {
        if (descriptor.empty())
            return false;
        const auto result = OlMod::DedicatedControl::submit(
            OlMod::DedicatedControl::configuredHostAddress(),
            OlMod::DedicatedControl::configuredPort(),
            {
                .type = OlMod::DedicatedControl::MessageType::ConfigureSession,
                .requestId = nextControlRequestId(),
                .payload = {
                    reinterpret_cast<const char *>(descriptor.data()),
                    descriptor.size(),
                },
            },
            1000);
        const auto status = OlMod::DedicatedControl::decodeEndpointStatus(
            result.payload);
        return result.delivered &&
            result.status == OlMod::DedicatedControl::ResponseStatus::Accepted &&
            status && status->sessionConfigured && status->enabled &&
            status->bound && status->port;
    }

    std::optional<AlwaysofflineRe::Demonware::GameServerEndpoint>
    dedicatedGameServerEndpoint()
    {
        const auto result = OlMod::DedicatedControl::submit(
            OlMod::DedicatedControl::configuredHostAddress(),
            OlMod::DedicatedControl::configuredPort(),
            {
                .type = OlMod::DedicatedControl::MessageType::QueryEndpoint,
                .requestId = nextControlRequestId(),
            },
            500);
        const auto status = OlMod::DedicatedControl::decodeEndpointStatus(
            result.payload);
        if (!result.delivered ||
            result.status != OlMod::DedicatedControl::ResponseStatus::Accepted ||
            !status || !status->sessionConfigured || !status->enabled ||
            !status->bound || !status->port)
        {
            return std::nullopt;
        }
        return AlwaysofflineRe::Demonware::GameServerEndpoint{
            // This is the address the client actually dials: it reaches
            // properties["Demonware.Hostaddress"] through commonAddress().
            .ipv4 = OlMod::DedicatedControl::configuredHostIpv4(),
            .port = status->port,
        };
    }

    bool configureGameServer(const std::span<const std::uint8_t> descriptor)
    {
        return OlMod::processRole() == OlMod::ProcessRole::Client
            ? configureDedicatedGameServer(descriptor)
            : configureLocalGameServer(descriptor);
    }

    std::optional<AlwaysofflineRe::Demonware::GameServerEndpoint>
    gameServerEndpoint()
    {
        return OlMod::processRole() == OlMod::ProcessRole::Client
            ? dedicatedGameServerEndpoint()
            : localGameServerEndpoint();
    }

    std::vector<std::uint8_t> commonAddress(
        const AlwaysofflineRe::Demonware::GameServerEndpoint endpoint)
    {
        const auto appendEndpoint = [](std::vector<std::uint8_t> &output,
                                       const std::uint32_t ipv4,
                                       const std::uint16_t port)
        {
            output.push_back(static_cast<std::uint8_t>(ipv4 >> 24));
            output.push_back(static_cast<std::uint8_t>(ipv4 >> 16));
            output.push_back(static_cast<std::uint8_t>(ipv4 >> 8));
            output.push_back(static_cast<std::uint8_t>(ipv4));
            output.push_back(static_cast<std::uint8_t>(port));
            output.push_back(static_cast<std::uint8_t>(port >> 8));
        };

        std::vector<std::uint8_t> output;
        output.reserve(37);
        appendEndpoint(output, endpoint.ipv4, endpoint.port);
        constexpr std::array<std::uint8_t, 6> EmptyEndpoint{
            0x00, 0xFF, 0x00, 0xFF, 0x00, 0x00,
        };
        for (int index = 0; index < 4; ++index)
            output.insert(output.end(), EmptyEndpoint.begin(), EmptyEndpoint.end());
        appendEndpoint(output, endpoint.ipv4, endpoint.port);
        output.push_back(1);
        return output;
    }

    void replaceWithAuthoritativeGameServerAddress(
        nlohmann::json &properties,
        const AlwaysofflineRe::Demonware::MatchmakingService::GameServerProvider &provider)
    {
        if (!provider)
            return;
        const auto endpoint = provider();
        if (endpoint && endpoint->port)
            properties["Demonware.Hostaddress"] = commonAddress(*endpoint);
    }
}

namespace AlwaysofflineRe::Demonware
{
    MatchmakingService::MatchmakingService(
        const bool startNetworking,
        GameServerProvider gameServerProvider,
        GameServerConfigurator gameServerConfigurator,
        SessionUpdatePublisher sessionUpdatePublisher,
        SessionTerminatePublisher sessionTerminatePublisher)
        : discovery_(processSessionNumericId(), startNetworking),
          gameServerProvider_(gameServerProvider ? std::move(gameServerProvider) : gameServerEndpoint),
          gameServerConfigurator_(gameServerConfigurator
              ? std::move(gameServerConfigurator)
              : configureGameServer),
          sessionUpdatePublisher_(sessionUpdatePublisher
              ? std::move(sessionUpdatePublisher)
              : [this](const nlohmann::json &properties) {
                    discovery_.broadcastUpdate(properties);
                }),
          sessionTerminatePublisher_(sessionTerminatePublisher
              ? std::move(sessionTerminatePublisher)
              : [this] { discovery_.broadcastTerminate(); })
    {
    }

    void MatchmakingService::registerTasks(ServiceRegistry &registry) const
    {
        const auto registerService = [this, &registry](const std::uint8_t service, const std::string_view prefix)
        {
            registry.registerTask(service, 1, std::string(prefix) + "::createSession", [this](const auto &request)
            {
                return createSession(request);
            });
            registry.registerTask(service, 2, std::string(prefix) + "::updateSession", [this](const auto &request)
            {
                return updateSession(request);
            });
            registry.registerTask(service, 3, std::string(prefix) + "::deleteSession", [this](const auto &request)
            {
                return deleteSession(request);
            });
            registry.registerTask(service, 5, std::string(prefix) + "::findSessions", [this](const auto &request)
            {
                return findSessions(request);
            });
            registry.registerTask(service, 9, std::string(prefix) + "::submitPerformance", [this](const auto &request)
            {
                return submitPerformance(request);
            });
            registry.registerTask(service, 10, std::string(prefix) + "::getPerformanceValues", [this](const auto &request)
            {
                return getPerformanceValues(request);
            });
            registry.registerTask(service, 12, std::string(prefix) + "::updatePlayers", [this](const auto &request)
            {
                return updatePlayers(request);
            });
            registry.registerTask(service, 16, std::string(prefix) + "::findSessions", [this](const auto &request)
            {
                return findSessions(request);
            });
        };

        registerService(0x15, "Matchmaking");
        registerService(0x8A, "Matchmaking2");
    }

    void MatchmakingService::setSessionDescriptorCanonicalizer(
        SessionDescriptorCanonicalizer canonicalizer)
    {
        std::scoped_lock lock(localMutex_);
        sessionDescriptorCanonicalizer_ = std::move(canonicalizer);
    }

    bool MatchmakingService::ingestLanPacket(
        const std::span<const std::uint8_t> packet,
        const std::uint32_t sourceAddress) const
    {
        return discovery_.ingestPacket(packet, sourceAddress);
    }

    ServiceResponse MatchmakingService::createSession(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        nlohmann::json properties;
        if (!readSessionProperties(input, properties))
            return ServiceResponse{ .error = 1000, .task = request.task };

        auto descriptor = jsonBytes(properties, "Session.Demonware");
        if (sessionDescriptorCanonicalizer_)
        {
            const auto canonical = sessionDescriptorCanonicalizer_(descriptor);
            if (!canonical)
                return ServiceResponse{ .error = 1000, .task = request.task };
            descriptor = *canonical;
            properties["Session.Demonware"] = descriptor;
        }
        static_cast<void>(gameServerConfigurator_(descriptor));

        // The address embedded by the client is only a local booking hint.
        // Once the dedicated endpoint is bound, advertise that authoritative
        // endpoint to every room member so their ClientLoadTimer targets the
        // same server socket.
        replaceWithAuthoritativeGameServerAddress(
            properties, gameServerProvider_);

        {
            std::scoped_lock lock(localMutex_);
            localProperties_ = properties;
        }
        sessionUpdatePublisher_(properties);

        ByteBuffer object;
        object.writeBlob(processSessionId());
        return ServiceResponse{ .task = request.task, .objects = { object.data() } };
    }

    ServiceResponse MatchmakingService::updateSession(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::vector<std::uint8_t> ignoredSessionId;
        nlohmann::json properties;
        if (!input.readBlob(ignoredSessionId) || !readSessionProperties(input, properties))
            return ServiceResponse{ .error = 1000, .task = request.task };

        auto descriptor = jsonBytes(properties, "Session.Demonware");
        if (sessionDescriptorCanonicalizer_)
        {
            const auto canonical = sessionDescriptorCanonicalizer_(descriptor);
            if (!canonical)
                return ServiceResponse{ .error = 1000, .task = request.task };
            descriptor = *canonical;
            properties["Session.Demonware"] = descriptor;
        }
        static_cast<void>(gameServerConfigurator_(descriptor));

        replaceWithAuthoritativeGameServerAddress(
            properties, gameServerProvider_);

        {
            std::scoped_lock lock(localMutex_);
            localProperties_ = properties;
        }
        sessionUpdatePublisher_(properties);
        return ServiceResponse{ .task = request.task };
    }

    ServiceResponse MatchmakingService::deleteSession(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::vector<std::uint8_t> ignoredSessionId;
        if (!input.readBlob(ignoredSessionId))
            return ServiceResponse{ .error = 1000, .task = request.task };

        {
            std::scoped_lock lock(localMutex_);
            localProperties_.clear();
        }
        sessionTerminatePublisher_();
        return ServiceResponse{ .task = request.task };
    }

    // The tail of one bdMatchMakingInfo, written FIELD BY FIELD.
    //
    // This replaced `writeRaw(properties["Session.Demonware"])`, which pasted one opaque
    // captured descriptor into the record. That descriptor put 37 where the client requires
    // 67, and the consequence is not a wrong label on screen -- it is a hard crash. MEASURED
    // 2026-08-30 with tools/runtime/CodolLobbyObjectProbe.py:
    //
    //     typeGate: gateField=37, gateExpected=67, gatePasses=False, written=0
    //
    // sub_B95C50 leaves its out-pointer at 0 unless *(MatchMakingInfo + 70) == 67, and
    // sub_8071F0 then reads *(0 + 0x10) -- the 0x10 access violation in every crash dump from
    // QuickMatch, the zombies lobby and the dev panel alike. sub_7C44F0 copies that field
    // verbatim (a1[70] = a2[70]) out of the 568-byte wire record, so the value is ours.
    //
    // Ported from the C# reference LobbyServer/Services/MatchMaking.cs BuildSessionRecord(),
    // which renders in this client. Both sides use the same Demonware type tags -- U32 0x08,
    // I32 0x07, U64 0x0A, String 0x10, Blob 0x13 -- so this is a faithful transcription, not a
    // reinterpretation. The constants carry that file's measured notes:
    //
    //   room id   MUST be a NON-ZERO DECIMAL STRING. MatchController.as rejects a join when
    //             _strtoui64(room.id) equals the `last_kick_room_id` dvar, which is unset and
    //             so parses to 0; a non-numeric id also parses to 0, and 0 == 0 reported every
    //             join as a kick.
    //   host uid  MUST NOT be the player's own CODOID, or the client addresses the room join
    //             to itself and discards its own reply.
    //
    // The seven values marked "query criterion" are what the client filters on. They are
    // carried across exactly; nothing here is guessed, and where ol-mod has no source of its
    // own for a field the reference's measured constant is used rather than an invention.
    void MatchmakingService::writeSessionRecordTail(
        ByteBuffer &object,
        const LanDiscovery::RemoteSession &session) const
    {
        // Room id as a decimal string, derived from the session so two rooms differ, and
        // forced non-zero for the kick check above.
        const auto roomId = static_cast<std::uint64_t>(session.id & 0x7FFFFFFFULL) | 1ULL;
        object.writeString(std::to_string(roomId));
        object.writeU64(RoomHostUid);

        const auto mapName = jsonString(session.properties, "Session.Map");
        object.writeString(mapName.empty() ? std::string{ "mp_crash_tropical" } : mapName);

        object.writeI32(-695030357);   // query criterion, 0xD692ADAB
        for (int index = 0; index != 6; ++index)
            object.writeI32(0);

        // The 16-byte security key. GameServer needs the matching half, so it comes from the
        // session descriptor rather than being minted here.
        const auto securityKey = jsonBytes(session.properties, "Session.SecurityKey");
        std::array<std::uint8_t, 16> key{};
        std::copy_n(securityKey.begin(),
            (std::min)(securityKey.size(), key.size()), key.begin());
        object.writeBlob(key);

        object.writeI32(19);           // query criterion
        object.writeI32(0);
        object.writeI32(0);
        object.writeI32(8);            // query criterion
        object.writeI32(-1);
        object.writeI32(796);          // mp_playlists_shipRetail_release.info version 796
        object.writeI32(30);           // query criterion
        object.writeI32(0);
        object.writeI32(7);
        object.writeI32(0);

        object.writeI32(0x0C0DE001);   // room id, non-zero on purpose
        object.writeU64(RoomHostUid);  // demonwareID / room id

        object.writeI32(0);
        object.writeI32(0);
        object.writeI32(0);
        object.writeI32(1);
        object.writeI32(0);
    }

    ServiceResponse MatchmakingService::findSessions(const ServiceRequest &request) const
    {
        ServiceResponse response{ .task = request.task };
        auto sessions = discovery_.activeSessions();
        const auto queryKind = matchmakingQueryKind(request.payload);
        if (queryKind == FindServersQuery)
        {
            std::erase_if(sessions, [](const auto &session)
            {
                return !isServerSession(session.properties);
            });
            std::vector<std::uint8_t> descriptor;
            {
                std::scoped_lock lock(localMutex_);
                descriptor = jsonBytes(localProperties_, "Session.Demonware");
            }
            if (!descriptor.empty())
                static_cast<void>(gameServerConfigurator_(descriptor));
            const auto endpoint = gameServerProvider_();
            if (endpoint)
            {
                if (!descriptor.empty())
                {
                    sessions.insert(sessions.begin(), LanDiscovery::RemoteSession{
                        .id = processSessionNumericId() ^ 0x53525652564F4443ULL,
                        .properties = {
                            { "Demonware.Hostaddress", commonAddress(*endpoint) },
                            { "Session.Gametype", std::uint32_t{ 0 } },
                            { "Players.Max", std::uint32_t{ 18 } },
                            { "Players.Current", std::uint32_t{ 0 } },
                            { "Session.Demonware", descriptor },
                            { "Session.Role", "server" },
                        },
                    });
                }
            }
        }
        else
        {
            if (queryKind == FindPlaylistLobbiesQuery)
            {
                std::erase_if(sessions, [](const auto &session)
                {
                    return isServerSession(session.properties);
                });
            }
            std::scoped_lock lock(localMutex_);
            if (!localProperties_.empty())
            {
                sessions.insert(sessions.begin(), LanDiscovery::RemoteSession{
                    .id = processSessionNumericId(),
                    .properties = localProperties_,
                });
            }
        }
        response.objects.reserve(sessions.size());
        for (const auto &session : sessions)
        {
            ByteBuffer object;
            object.writeBlob(jsonBytes(session.properties, "Demonware.Hostaddress"));
            const auto sessionId = std::span(
                reinterpret_cast<const std::uint8_t *>(&session.id),
                sizeof(session.id));
            object.writeBlob(sessionId);
            object.writeU32(jsonU32(session.properties, "Session.Gametype", 0));
            object.writeU32(jsonU32(session.properties, "Players.Max", 18));
            object.writeU32(jsonU32(session.properties, "Players.Current", 1));
            writeSessionRecordTail(object, session);
            response.objects.push_back(object.data());
        }
        return response;
    }

    ServiceResponse MatchmakingService::submitPerformance(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint32_t context{};
        if (!input.readU32(context))
            return ServiceResponse{ .error = 1000, .task = request.task };

        std::vector<std::pair<std::uint64_t, std::int64_t>> values;
        while (!input.empty())
        {
            std::uint64_t userId{};
            std::int64_t performance{};
            if (!input.readU64(userId) || !input.readI64(performance))
                return ServiceResponse{ .error = 1000, .task = request.task };
            values.emplace_back(userId, performance);
        }

        std::scoped_lock lock(performanceMutex_);
        for (const auto &[userId, performance] : values)
            performanceValues_[userId][context] = performance;
        return ServiceResponse{ .task = request.task };
    }

    ServiceResponse MatchmakingService::getPerformanceValues(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint32_t context{};
        if (!input.readU32(context))
            return ServiceResponse{ .error = 1000, .task = request.task };

        std::vector<std::uint64_t> userIds;
        while (!input.empty())
        {
            std::uint64_t userId{};
            if (!input.readU64(userId))
                return ServiceResponse{ .error = 1000, .task = request.task };
            userIds.push_back(userId);
        }

        ServiceResponse response{ .task = request.task };
        std::scoped_lock lock(performanceMutex_);
        for (const auto userId : userIds)
        {
            const auto user = performanceValues_.find(userId);
            if (user == performanceValues_.end())
                continue;
            const auto value = user->second.find(context);
            if (value == user->second.end())
                continue;

            ByteBuffer object;
            object.writeU64(userId);
            object.writeI64(value->second);
            response.objects.push_back(object.data());
        }
        return response;
    }

    ServiceResponse MatchmakingService::updatePlayers(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::vector<std::uint8_t> ignoredSessionId;
        std::uint32_t currentPlayers{};
        if (!input.readBlob(ignoredSessionId) || !input.readU32(currentPlayers))
            return ServiceResponse{ .error = 1000, .task = request.task };

        nlohmann::json properties;
        {
            std::scoped_lock lock(localMutex_);
            localProperties_["Players.Current"] = currentPlayers;
            properties = localProperties_;
        }
        sessionUpdatePublisher_(properties);
        return ServiceResponse{ .task = request.task };
    }
}
