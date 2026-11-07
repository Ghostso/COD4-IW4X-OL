#pragma once

#include "IServer.hpp"
#include "Demonware/AckOnlyServices.hpp"
#include "Demonware/Auth3TlsTransport.hpp"
#include "Demonware/ContentUnlock2Service.hpp"
#include "Demonware/Friends2Service.hpp"
#include "Demonware/InstantMessageService.hpp"
#include "Demonware/LobbyProtocol.hpp"
#include "Demonware/MatchmakingService.hpp"
#include "Demonware/MarketplaceService.hpp"
#include "Demonware/Profiles2Service.hpp"
#include "Demonware/Storage2Service.hpp"
#include "Demonware/TencentService.hpp"
#include "Demonware/TitleUtilitiesService.hpp"
#include "Demonware/Unknown0BService.hpp"
#include "DedicatedBookingDispatcher.hpp"
#include "SharedRoomClient.hpp"

#include <cstdint>
#include <deque>
#include <memory>
#include <mutex>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace AlwaysofflineRe
{
    enum class ServerKind
    {
        none,
        stun,
        auth3,
        legacyAuth,
        content,
        lobby,
    };

    [[nodiscard]] ServerKind classifyHostname(std::string_view hostname);
    [[nodiscard]] const char *serverKindName(ServerKind kind);
    void log(std::string_view message);

    class StunServer final : public IDatagramServer
    {
    public:
        bool onPacketread(void *data, std::uint32_t *size) override;
        bool onPacketwrite(const void *data, std::uint32_t size, const Endpoints *endpoints) override;

    private:
        std::mutex mutex_;
        std::deque<std::vector<std::uint8_t>> responses_;
    };

    // These classes preserve the recovered protocol boundaries while their
    // protocol implementations are reconstructed. They deliberately emit no
    // response instead of hiding missing behavior behind an empty success.
    class PendingStreamServer final : public IStreamServer
    {
    public:
        PendingStreamServer(ServerKind kind, std::string hostname);

        void onConnect() override;
        void onDisconnect() override;
        bool onStreamread(void *data, std::uint32_t *size) override;
        bool onStreamwrite(const void *data, std::uint32_t size) override;

    private:
        ServerKind kind_;
        std::string hostname_;
    };

    class LobbyServer final : public IStreamServer
    {
    public:
        LobbyServer(std::string hostname, Demonware::AuthSession &session);

        void onConnect() override;
        void onDisconnect() override;
        bool onStreamread(void *data, std::uint32_t *size) override;
        bool onStreamwrite(const void *data, std::uint32_t size) override;

        [[nodiscard]] Demonware::ServiceRegistry &registry() { return registry_; }

    private:
        void submitBooking(std::string_view command);

        std::mutex mutex_;
        std::string hostname_;
        Demonware::AuthSession &session_;
        Demonware::ServiceRegistry registry_;
        Demonware::LobbyProtocol protocol_;
        Demonware::ContentUnlock2Service contentUnlock2_;
        Demonware::Friends2Service friends2_;
        Demonware::MatchmakingService matchmaking_;
        Demonware::InstantMessageService instantMessage_;
        Demonware::MarketplaceService marketplace_;
        Demonware::Profiles2Service profiles2_;
        Demonware::Storage2Service storage2_;
        Demonware::TencentService tencent_;
        Demonware::TitleUtilitiesService titleUtilities_;
        SharedRoomClient sharedRoomClient_;
        DedicatedBookingDispatcher bookingDispatcher_;
        Demonware::Unknown0BService unknown0B_;
        Demonware::AckOnlyServices ackOnly_;
    };

    class Auth3Server final : public IStreamServer
    {
    public:
        Auth3Server(
            std::string hostname,
            Demonware::AuthSession &session,
            Demonware::PlayerIdentityStore &identityStore);

        void onConnect() override;
        void onDisconnect() override;
        bool onStreamread(void *data, std::uint32_t *size) override;
        bool onStreamwrite(const void *data, std::uint32_t size) override;

    private:
        std::mutex mutex_;
        std::string hostname_;
        Demonware::Auth3TlsTransport transport_;
    };

    class ServerFactory
    {
    public:
        ServerFactory();
        IServer *create(std::string_view hostname);

    private:
        std::mutex mutex_;
        Demonware::PlayerIdentityStore playerIdentities_;
        Demonware::AuthSession authSession_;
        StunServer stun_;
        std::unique_ptr<PendingStreamServer> legacyAuth_;
        std::unique_ptr<LobbyServer> lobby_;
        std::unordered_map<std::string, std::unique_ptr<Auth3Server>> auth3Hosts_;
        std::unordered_map<std::string, std::unique_ptr<PendingStreamServer>> perHost_;
    };
}
