#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <WinSock2.h>
#include <WS2tcpip.h>

#include "Servers.hpp"
#include "../shared/ProcessRole.hpp"
#include "Demonware/Auth3ClientPatches.hpp"
#include "../shared/DedicatedControl.hpp"
#include "../shared/RuntimeLog.hpp"

#include "Demonware/CodolStartupTasks.hpp"

#include <algorithm>
#include <array>
#include <cstring>
#include <iomanip>
#include <sstream>
#include <utility>

namespace
{
    std::string lowercase(std::string_view value)
    {
        std::string result(value);
        std::transform(result.begin(), result.end(), result.begin(), [](const unsigned char character)
        {
            return static_cast<char>(std::tolower(character));
        });
        return result;
    }

    bool contains(const std::string &value, const std::string_view needle)
    {
        return value.find(needle) != std::string::npos;
    }

    std::string hexPreview(const void *data, const std::uint32_t size)
    {
        const auto *bytes = static_cast<const std::uint8_t *>(data);
        const auto count = std::min<std::uint32_t>(size, 64);
        std::ostringstream stream;
        stream << std::hex << std::setfill('0');
        for (std::uint32_t index = 0; index != count; ++index)
            stream << std::setw(2) << static_cast<unsigned int>(bytes[index]);
        if (count != size)
            stream << "...";
        return stream.str();
    }

    void appendU16(std::vector<std::uint8_t> &output, const std::uint16_t value)
    {
        output.push_back(static_cast<std::uint8_t>(value >> 8));
        output.push_back(static_cast<std::uint8_t>(value));
    }

    void appendU32(std::vector<std::uint8_t> &output, const std::uint32_t value)
    {
        output.push_back(static_cast<std::uint8_t>(value >> 24));
        output.push_back(static_cast<std::uint8_t>(value >> 16));
        output.push_back(static_cast<std::uint8_t>(value >> 8));
        output.push_back(static_cast<std::uint8_t>(value));
    }

    void appendLeU16(std::vector<std::uint8_t> &output, const std::uint16_t value)
    {
        output.push_back(static_cast<std::uint8_t>(value));
        output.push_back(static_cast<std::uint8_t>(value >> 8));
    }

    std::string endpointText(const IServer::Address &endpoint)
    {
        IN_ADDR address{};
        address.S_un.S_addr = endpoint.ipv4;
        std::array<char, INET_ADDRSTRLEN> buffer{};
        if (!InetNtopA(AF_INET, &address, buffer.data(), static_cast<DWORD>(buffer.size())))
            return "<invalid>:" + std::to_string(ntohs(endpoint.port));
        return std::string(buffer.data()) + ':' + std::to_string(ntohs(endpoint.port));
    }

}

namespace AlwaysofflineRe
{
    ServerKind classifyHostname(const std::string_view hostname)
    {
        const auto value = lowercase(hostname);

        // OLMOD(claim-lobby): the OLfinal bring-up stack points the client at
        // `lobby.codol.localhost`, which the hosts file resolves to 127.0.0.1 and the C# LobbyServer
        // answers. That is why this backend's matchmaking and room services -- 21/1..21/16 and
        // 11/1..11/13, all registered -- never see a request: the gate below requires
        // demonware.net or qq.com, so Createserver refuses the name and Localnetworking lets the
        // connection through to the real socket instead of routing it in-process.
        //
        // It matters because ConfigureSession is sent from MatchmakingService. With the lobby
        // served elsewhere nothing ever tells the game server to host, and QueryEndpoint on a live
        // client reports sessionConfigured=false, bound=false, port=0 -- which is exactly what a
        // two-client match is blocked on, and no amount of address work reaches it.
        //
        // Deliberately ONLY the lobby host. `auth.codol.localhost` would match "auth." and be
        // claimed as legacyAuth, taking login away from the C# AuthServer, which currently works
        // and whose OLfinal login chain is delicate -- see the 725 trap in AuthEndpoints.cs.
        // Off by default so this cannot change an existing stack by accident; the runtime driver
        // sets it for the processes it launches.
        if (contains(value, "lobby.codol.localhost"))
        {
            std::array<char, 8> claim{};
            const auto size = GetEnvironmentVariableA(
                "OLMOD_CLAIM_LOBBY", claim.data(), static_cast<DWORD>(claim.size()));
            const auto enabled = size == 1 && claim[0] == '1';
            return enabled ? ServerKind::lobby : ServerKind::none;
        }

        if (!contains(value, "demonware.net") && !contains(value, "qq.com"))
            return ServerKind::none;

        // The original build only recognized "stun.". CODOL 3.3.3.3 uses
        // stun1-/stun2- hostnames, so the source replacement accepts both.
        if (contains(value, "stun.") || contains(value, "stun1-") || contains(value, "stun2-"))
            return ServerKind::stun;
        if (contains(value, "umbrella.") || contains(value, "auth3.") || contains(value, "uno."))
        {
            // OLMOD_EXTERNAL_AUTH3: HAND AUTH3 BACK TO A REAL SERVER.
            //
            // Handoff section 191i. Claiming this name is what forces the whole opaque path:
            // the connection never reaches a socket, an in-process TLS server answers it with a
            // certificate it MINTS AT RUNTIME AND SIGNS ITSELF, and the only way a client accepts
            // that is if three of its validation sites are patched out first. On 2026-09-03 that
            // chain cost a remote player his evening -- the patches were gated on a 3.3.3.3
            // filename, OLfinal runs out.exe, so they never applied and his client correctly said
            // `tlsv1 alert unknown ca`.
            //
            // Refusing the claim lets Localnetworking pass the connect through to the real socket,
            // where the hosts file sends it to the C# AuthServer. That server already implements
            // this protocol PROPERLY -- Tiger, 3DES, the real codoId/worldId parse, and it knows
            // about the 725 trap -- and it now serves a certificate signed by
            // rootca.codol.localhost, which both machines already trust. No interception, no
            // self-signed leaf, no patches.
            //
            // OFF BY DEFAULT, and deliberately so: it needs the hosts entries and the rebuilt
            // AuthServer to be in place, and a half-applied version of this change is a client
            // that dials a name nothing answers. The pair is what makes it work, so the switch
            // is what turns the pair on.
            std::array<char, 8> external{};
            const auto size = GetEnvironmentVariableA(
                "OLMOD_EXTERNAL_AUTH3", external.data(), static_cast<DWORD>(external.size()));
            if (size == 1 && external[0] == '1')
                return ServerKind::none;
            return ServerKind::auth3;
        }
        if (contains(value, "auth."))
            return ServerKind::legacyAuth;
        if (contains(value, "cs."))
            return ServerKind::content;
        if (contains(value, "lsg.") || contains(value, "lobby."))
        {
            // The same switch covers lsg./lobby., because auth and the lobby are ONE TRUST
            // DOMAIN -- section 23b measured that directly: an LSG server that cannot validate
            // the ticket the other half issued completes the key exchange and then drops the
            // session, which reaches the screen as `[100] cannot connect to the lobby service`.
            // Moving one without the other reproduces exactly that.
            std::array<char, 8> external{};
            const auto size = GetEnvironmentVariableA(
                "OLMOD_EXTERNAL_AUTH3", external.data(), static_cast<DWORD>(external.size()));
            if (size == 1 && external[0] == '1')
                return ServerKind::none;
            return ServerKind::lobby;
        }
        return ServerKind::none;
    }

    const char *serverKindName(const ServerKind kind)
    {
        switch (kind)
        {
            case ServerKind::stun: return "STUN";
            case ServerKind::auth3: return "Auth3/UNO HTTP";
            case ServerKind::legacyAuth: return "legacy Auth";
            case ServerKind::content: return "content server";
            case ServerKind::lobby: return "LSG/lobby";
            default: return "unclaimed";
        }
    }

    void log(const std::string_view message)
    {
        OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::Backend, message);
    }

    bool StunServer::onPacketread(void *data, std::uint32_t *size)
    {
        if (!data || !size)
            return false;

        std::string preview;
        std::size_t remaining{};
        {
            std::scoped_lock lock(mutex_);
            if (responses_.empty() || *size < responses_.front().size())
                return false;

            const auto &response = responses_.front();
            std::memcpy(data, response.data(), response.size());
            *size = static_cast<std::uint32_t>(response.size());
            preview = hexPreview(response.data(), static_cast<std::uint32_t>(response.size()));
            responses_.pop_front();
            remaining = responses_.size();
        }
        log("STUN dequeued response=" + preview + " remaining=" + std::to_string(remaining) + '.');
        return true;
    }

    bool StunServer::onPacketwrite(
        const void *data,
        const std::uint32_t size,
        const Endpoints *endpoints)
    {
        if (!data || !endpoints || size == 0)
            return false;

        const auto *request = static_cast<const std::uint8_t *>(data);
        if (request[0] == 0x14 || request[0] == 0x1E)
        {
            std::vector<std::uint8_t> response;
            response.reserve(request[0] == 0x14 ? 15 : 9);
            response.push_back(static_cast<std::uint8_t>(request[0] + 1));
            appendLeU16(response, AF_INET);
            response.insert(response.end(), { 0xF0, 0x00, 0x00, 0x01 });
            appendLeU16(response, ntohs(endpoints->client.port));
            if (request[0] == 0x14)
            {
                const auto *address = reinterpret_cast<const std::uint8_t *>(&endpoints->server.ipv4);
                response.insert(response.end(), address, address + sizeof(endpoints->server.ipv4));
                appendLeU16(response, ntohs(endpoints->server.port));
            }

            const auto preview = hexPreview(response.data(), static_cast<std::uint32_t>(response.size()));
            std::size_t depth{};
            {
                std::scoped_lock lock(mutex_);
                responses_.push_back(std::move(response));
                depth = responses_.size();
            }
            log("Handled DW STUN type " + std::to_string(request[0]) +
                " request client=" + endpointText(endpoints->client) +
                " server=" + endpointText(endpoints->server) +
                " response=" + preview + " queued=" + std::to_string(depth) + '.');
            return true;
        }

        if (size < 20 || request[0] != 0 || request[1] != 1)
            return true;

        std::vector<std::uint8_t> response;
        response.reserve(32);
        appendU16(response, 0x0101);
        appendU16(response, 12);
        response.insert(response.end(), request + 4, request + 20);
        appendU16(response, 0x0001);
        appendU16(response, 8);
        response.push_back(0);
        response.push_back(1);
        appendU16(response, ntohs(endpoints->client.port));
        appendU32(response, ntohl(endpoints->client.ipv4));

        const auto preview = hexPreview(response.data(), static_cast<std::uint32_t>(response.size()));
        std::size_t depth{};
        {
            std::scoped_lock lock(mutex_);
            responses_.push_back(std::move(response));
            depth = responses_.size();
        }
        log("Handled STUN binding request client=" + endpointText(endpoints->client) +
            " server=" + endpointText(endpoints->server) +
            " response=" + preview + " queued=" + std::to_string(depth) + '.');
        return true;
    }

    PendingStreamServer::PendingStreamServer(const ServerKind kind, std::string hostname)
        : kind_(kind), hostname_(std::move(hostname))
    {
    }

    void PendingStreamServer::onConnect()
    {
        log(std::string("Connected to pending ") + serverKindName(kind_) + " server for " + hostname_ + '.');
    }

    void PendingStreamServer::onDisconnect()
    {
        log(std::string("Disconnected from pending ") + serverKindName(kind_) + " server for " + hostname_ + '.');
    }

    bool PendingStreamServer::onStreamread(void *, std::uint32_t *)
    {
        return false;
    }

    bool PendingStreamServer::onStreamwrite(const void *data, const std::uint32_t size)
    {
        log(std::string("Pending ") + serverKindName(kind_) + " input for " + hostname_ +
            ": " + std::to_string(size) + " bytes, " + hexPreview(data, size));
        return true;
    }

    LobbyServer::LobbyServer(std::string hostname, Demonware::AuthSession &session)
        : hostname_(std::move(hostname)),
          session_(session),
          protocol_(registry_, [](const std::string_view message) { log(message); }),
          friends2_(session_),
          matchmaking_(),
          instantMessage_(session_, [this](auto payload, const std::uint8_t messageType)
          {
              protocol_.queuePush(std::move(payload), messageType);
          }, &matchmaking_.messageBus(), [this](const std::string_view command) {
              submitBooking(command);
          }),
          marketplace_(session_),
          profiles2_(session_),
          storage2_(session_),
          tencent_(session_),
          titleUtilities_(session_),
          sharedRoomClient_([](const std::string_view message) { log(message); }),
          bookingDispatcher_(
              session_, marketplace_,
              OlMod::processRole() == OlMod::ProcessRole::Client
                  ? DedicatedBookingDispatcher::RosterProvider{
                      [this](const std::uint64_t generation) {
                          return sharedRoomClient_.freeze(generation);
                      }}
                  : DedicatedBookingDispatcher::RosterProvider{},
              [](const std::string_view message) { log(message); }),
          unknown0B_(session_, [this](auto payload, const std::uint8_t messageType)
          {
              protocol_.queuePush(std::move(payload), messageType);
          }, &matchmaking_.messageBus(), [this](const std::string_view command) {
              submitBooking(command);
          }, [this](const Demonware::Unknown0BService::RoomEvent event) {
              const auto eventName = event == Demonware::Unknown0BService::RoomEvent::Enter
                  ? "enter"
                  : event == Demonware::Unknown0BService::RoomEvent::Leave
                      ? "leave" : "ready";
              log("shared room event=" + std::string(eventName) +
                  " role=" + std::to_string(static_cast<int>(OlMod::processRole())));
              if (OlMod::processRole() != OlMod::ProcessRole::Client)
                  return true;
              const auto identity = session_.snapshot();
              bool accepted{};
              if (event == Demonware::Unknown0BService::RoomEvent::Enter)
              {
                  accepted = sharedRoomClient_.connect(
                      identity,
                      OlMod::DedicatedControl::configuredClientBridgePort());
              }
              else if (event == Demonware::Unknown0BService::RoomEvent::Leave)
                  accepted = sharedRoomClient_.disconnect(identity.userId);
              else
                  accepted = sharedRoomClient_.setReady(identity.userId, true);
              log("shared room event=" + std::string(eventName) +
                  " user=" + std::to_string(identity.userId) +
                  " accepted=" + std::to_string(accepted));
              return accepted;
          })
    {
        if (OlMod::processRole() == OlMod::ProcessRole::Client)
        {
            matchmaking_.setSessionDescriptorCanonicalizer(
                [this](const std::span<const std::uint8_t> descriptor) {
                    return sharedRoomClient_.canonicalizeSessionDescriptor(
                        session_.snapshot().userId, descriptor);
                });
        }
        Demonware::registerCodolStartupTasks(registry_);
        contentUnlock2_.registerTasks(registry_);
        friends2_.registerTasks(registry_);
        instantMessage_.registerTasks(registry_);
        matchmaking_.registerTasks(registry_);
        marketplace_.registerTasks(registry_);
        profiles2_.registerTasks(registry_);
        storage2_.registerTasks(registry_);
        tencent_.registerTasks(registry_);
        titleUtilities_.registerTasks(registry_);
        unknown0B_.registerTasks(registry_);
        ackOnly_.registerTasks(registry_);
        matchmaking_.messageBus().subscribe(
            "Demonware::Instantmessage",
            [this](const std::uint64_t, const std::string_view payload)
            {
                const auto identity = session_.snapshot();
                if (auto push = Demonware::InstantMessageService::decodeInstantPush(payload, identity.userId))
                    protocol_.queuePush(std::move(*push), 2);
            });
        matchmaking_.messageBus().subscribe(
            "Demonware::Channelmessage",
            [this](const std::uint64_t, const std::string_view payload)
            {
                const auto identity = session_.snapshot();
                if (auto push = Demonware::Unknown0BService::decodeChannelPush(payload, identity.userId))
                    protocol_.queuePush(std::move(*push), 2);
            });
    }

    void LobbyServer::submitBooking(const std::string_view command)
    {
        log("CODOL_GAME_BOOKING command=" + std::string(command));
        if (OlMod::processRole() == OlMod::ProcessRole::Client)
        {
            const auto userId = session_.snapshot().userId;
            if (!sharedRoomClient_.setReady(userId, true))
            {
                log("CODOL_GAME_SESSION booking_ready_rejected user=" +
                    std::to_string(userId));
                return;
            }
        }
        static_cast<void>(bookingDispatcher_.submit(std::string(command)));
    }

    void LobbyServer::onConnect()
    {
        std::scoped_lock lock(mutex_);
        protocol_.reset();
        log("Connected to LSG/lobby server for " + hostname_ + '.');
    }

    void LobbyServer::onDisconnect()
    {
        std::scoped_lock lock(mutex_);
        protocol_.reset();
        log("Disconnected from LSG/lobby server for " + hostname_ + '.');
    }

    bool LobbyServer::onStreamread(void *data, std::uint32_t *size)
    {
        if (!data || !size)
            return false;
        std::scoped_lock lock(mutex_);
        const auto output = protocol_.takeOutput(*size);
        if (output.empty())
            return false;
        std::memcpy(data, output.data(), output.size());
        *size = static_cast<std::uint32_t>(output.size());
        return true;
    }

    bool LobbyServer::onStreamwrite(const void *data, const std::uint32_t size)
    {
        if (!data || !size)
            return false;
        std::scoped_lock lock(mutex_);
        protocol_.setSessionKey(session_.snapshot().sessionKey);
        protocol_.receive(std::span(static_cast<const std::uint8_t *>(data), size));
        return true;
    }

    Auth3Server::Auth3Server(
        std::string hostname,
        Demonware::AuthSession &session,
        Demonware::PlayerIdentityStore &identityStore)
        : hostname_(std::move(hostname)),
          transport_(session, hostname_,
              [](const std::string_view message) { log(message); },
              &identityStore)
    {
    }

    void Auth3Server::onConnect()
    {
        std::scoped_lock lock(mutex_);
        try
        {
            transport_.reset();
            log("Connected to Auth3 TLS server for " + hostname_ + '.');
        }
        catch (const std::exception &error)
        {
            log(std::string("Auth3 TLS connect failed: ") + error.what());
        }
    }

    void Auth3Server::onDisconnect()
    {
        std::scoped_lock lock(mutex_);
        try
        {
            transport_.reset();
            log("Disconnected from Auth3 TLS server for " + hostname_ + '.');
        }
        catch (const std::exception &error)
        {
            log(std::string("Auth3 TLS disconnect reset failed: ") + error.what());
        }
    }

    bool Auth3Server::onStreamread(void *data, std::uint32_t *size)
    {
        if (!data || !size)
            return false;
        std::scoped_lock lock(mutex_);
        const auto output = transport_.takeOutput(*size);
        if (output.empty())
            return false;
        std::memcpy(data, output.data(), output.size());
        *size = static_cast<std::uint32_t>(output.size());
        return true;
    }

    bool Auth3Server::onStreamwrite(const void *data, const std::uint32_t size)
    {
        if (!data || !size)
            return false;
        std::scoped_lock lock(mutex_);
        try
        {
            transport_.receive(std::span(static_cast<const std::uint8_t *>(data), size));
        }
        catch (const std::exception &error)
        {
            log(std::string("Auth3 TLS input failed: ") + error.what());
            try
            {
                transport_.reset();
            }
            catch (const std::exception &resetError)
            {
                log(std::string("Auth3 TLS recovery failed: ") + resetError.what());
            }
        }
        return true;
    }

    ServerFactory::ServerFactory() = default;

    IServer *ServerFactory::create(const std::string_view hostname)
    {
        const auto kind = classifyHostname(hostname);
        if (kind == ServerKind::none)
            return nullptr;
        if (kind == ServerKind::stun)
            return &stun_;

        std::scoped_lock lock(mutex_);
        if (kind == ServerKind::legacyAuth)
        {
            if (!legacyAuth_)
                legacyAuth_ = std::make_unique<PendingStreamServer>(kind, std::string(hostname));
            return legacyAuth_.get();
        }
        if (kind == ServerKind::lobby)
        {
            if (!lobby_)
                lobby_ = std::make_unique<LobbyServer>(std::string(hostname), authSession_);
            return lobby_.get();
        }

        const auto key = lowercase(hostname);
        if (kind == ServerKind::auth3)
        {
            // Installed HERE rather than for every claimed name: these three patches blind the
            // client's certificate and authentication checks, and Auth3 is the only path that
            // needs them. Claiming STUN used to drag them in too, which is a lot of blast radius
            // for a UDP echo. Still early enough -- the client cannot validate anything until it
            // talks to the server this branch is about to return.
            if (!Demonware::installAuth3ClientPatches())
            {
                log("Could not install the three recovered CODOL Auth3 client patches.");
                return nullptr;
            }
            auto [iterator, inserted] = auth3Hosts_.try_emplace(key);
            if (inserted)
                iterator->second = std::make_unique<Auth3Server>(
                    std::string(hostname), authSession_, playerIdentities_);
            return iterator->second.get();
        }

        auto [iterator, inserted] = perHost_.try_emplace(key);
        if (inserted)
            iterator->second = std::make_unique<PendingStreamServer>(kind, std::string(hostname));
        return iterator->second.get();
    }
}
