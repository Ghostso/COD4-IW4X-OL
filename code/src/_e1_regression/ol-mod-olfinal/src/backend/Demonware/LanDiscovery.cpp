#include "LanDiscovery.hpp"

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <WinSock2.h>
#include <WS2tcpip.h>
#include <Windows.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <limits>
#include <optional>
#include <ranges>
#include <string>
#include <thread>

#pragma warning(push, 0)
#include <openssl/evp.h>
#pragma warning(pop)

namespace
{
    constexpr auto DiscoveryPort = std::uint16_t{ 0x4321 };

    bool isLegacyBase64(const std::string_view input)
    {
        if (input.empty())
            return false;
        return std::ranges::all_of(input, [](const unsigned char value)
        {
            return (value >= 'A' && value <= 'Z') ||
                (value >= 'a' && value <= 'z') ||
                (value >= '/' && value <= '9') || value == '=' || value == '+';
        });
    }

    std::string base64Encode(const std::string_view input)
    {
        if (input.empty())
            return {};
        if (input.size() > static_cast<std::size_t>((std::numeric_limits<int>::max)()))
            return {};
        std::string output(((input.size() + 2) / 3) * 4, '\0');
        const auto size = EVP_EncodeBlock(
            reinterpret_cast<unsigned char *>(output.data()),
            reinterpret_cast<const unsigned char *>(input.data()),
            static_cast<int>(input.size()));
        if (size < 0)
            return {};
        output.resize(static_cast<std::size_t>(size));
        return output;
    }

    std::optional<std::string> base64Decode(const std::string_view input)
    {
        if (input.empty())
            return std::string{};
        if (input.size() % 4 != 0 ||
            input.size() > static_cast<std::size_t>((std::numeric_limits<int>::max)()))
            return std::nullopt;
        std::string output(input.size() / 4 * 3, '\0');
        const auto size = EVP_DecodeBlock(
            reinterpret_cast<unsigned char *>(output.data()),
            reinterpret_cast<const unsigned char *>(input.data()),
            static_cast<int>(input.size()));
        if (size < 0)
            return std::nullopt;
        auto padding = std::size_t{};
        if (!input.empty() && input.back() == '=')
            ++padding;
        if (input.size() >= 2 && input[input.size() - 2] == '=')
            ++padding;
        output.resize(static_cast<std::size_t>(size) - padding);
        return output;
    }
}

namespace AlwaysofflineRe::Demonware
{
    class LanDiscovery::State
    {
    public:
        explicit State(LanDiscovery &owner)
            : owner_(owner)
        {
            WSADATA winsock{};
            if (WSAStartup(MAKEWORD(2, 2), &winsock) != 0)
                return;
            winsockStarted_ = true;

            socket_ = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
            if (socket_ == INVALID_SOCKET)
                return;

            const auto enabled = TRUE;
            setsockopt(socket_, SOL_SOCKET, SO_BROADCAST,
                reinterpret_cast<const char *>(&enabled), sizeof(enabled));
            setsockopt(socket_, SOL_SOCKET, SO_REUSEADDR,
                reinterpret_cast<const char *>(&enabled), sizeof(enabled));
            auto nonblocking = u_long{ 1 };
            ioctlsocket(socket_, FIONBIO, &nonblocking);

            SOCKADDR_IN address{};
            address.sin_family = AF_INET;
            address.sin_port = htons(DiscoveryPort);
            address.sin_addr.s_addr = htonl(INADDR_ANY);
            if (bind(socket_, reinterpret_cast<const SOCKADDR *>(&address), sizeof(address)) == SOCKET_ERROR)
            {
                closesocket(socket_);
                socket_ = INVALID_SOCKET;
                return;
            }

            worker_ = std::thread([this] { receive(); });
        }

        ~State()
        {
            stopping_.store(true);
            if (socket_ != INVALID_SOCKET)
                closesocket(socket_);
            if (worker_.joinable())
                worker_.join();
            socket_ = INVALID_SOCKET;
            if (winsockStarted_)
                WSACleanup();
        }

        void broadcast(const std::span<const std::uint8_t> packet) const
        {
            if (socket_ == INVALID_SOCKET || packet.empty() ||
                packet.size() > static_cast<std::size_t>((std::numeric_limits<int>::max)()))
                return;
            SOCKADDR_IN destination{};
            destination.sin_family = AF_INET;
            destination.sin_port = htons(DiscoveryPort);
            destination.sin_addr.s_addr = htonl(INADDR_BROADCAST);
            sendto(
                socket_,
                reinterpret_cast<const char *>(packet.data()),
                static_cast<int>(packet.size()),
                0,
                reinterpret_cast<const SOCKADDR *>(&destination),
                sizeof(destination));
        }

    private:
        void receive()
        {
            std::array<std::uint8_t, 4096> buffer{};
            while (!stopping_.load())
            {
                FD_SET readSet{};
                FD_SET(socket_, &readSet);
                timeval timeout{};
                timeout.tv_usec = 200'000;
                const auto selected = select(0, &readSet, nullptr, nullptr, &timeout);
                if (selected <= 0 || stopping_.load())
                    continue;

                SOCKADDR_IN source{};
                auto sourceSize = static_cast<int>(sizeof(source));
                const auto size = recvfrom(
                    socket_,
                    reinterpret_cast<char *>(buffer.data()),
                    static_cast<int>(buffer.size()),
                    0,
                    reinterpret_cast<SOCKADDR *>(&source),
                    &sourceSize);
                if (size > 0)
                {
                    static_cast<void>(owner_.ingestPacket(
                        std::span(buffer).first(static_cast<std::size_t>(size)),
                        source.sin_addr.s_addr));
                }
            }
        }

        LanDiscovery &owner_;
        SOCKET socket_{ INVALID_SOCKET };
        bool winsockStarted_{};
        std::atomic_bool stopping_{};
        std::thread worker_;
    };

    LanDiscovery::LanDiscovery(const std::uint64_t localId, const bool startNetworking)
        : localId_(localId)
    {
        if (startNetworking)
            state_ = std::make_unique<State>(*this);
    }

    LanDiscovery::~LanDiscovery() = default;

    std::vector<std::uint8_t> LanDiscovery::encodePacket(
        const std::string_view event,
        const std::uint64_t origin,
        const std::string_view payload)
    {
        const nlohmann::json message{
            { "Payload", isLegacyBase64(payload) ? std::string(payload) : base64Encode(payload) },
            { "Origin", origin },
            { "Event", event },
        };
        const auto encoded = base64Encode(message.dump());
        std::vector<std::uint8_t> packet{ 'M', 'E', 'E', 'P' };
        packet.insert(packet.end(), encoded.begin(), encoded.end());
        return packet;
    }

    void LanDiscovery::broadcastUpdate(const nlohmann::json &properties)
    {
        broadcast("Matchmaking::Update", properties.dump());
    }

    void LanDiscovery::broadcastTerminate()
    {
        broadcast("Matchmaking::Terminate", {});
    }

    void LanDiscovery::broadcast(const std::string_view event, const std::string_view payload)
    {
        if (!state_)
            return;
        const auto packet = encodePacket(event, localId_, payload);
        state_->broadcast(packet);
    }

    void LanDiscovery::subscribe(std::string event, EventHandler handler)
    {
        std::scoped_lock lock(handlersMutex_);
        handlers_.insert_or_assign(std::move(event), std::move(handler));
    }

    bool LanDiscovery::ingestPacket(
        const std::span<const std::uint8_t> packet,
        const std::uint32_t sourceAddress)
    {
        constexpr std::array<std::uint8_t, 4> Signature{ 'M', 'E', 'E', 'P' };
        if (packet.size() <= Signature.size() ||
            !std::ranges::equal(packet.first(Signature.size()), Signature))
            return false;

        try
        {
            const std::string encoded(packet.begin() + Signature.size(), packet.end());
            const auto decoded = base64Decode(encoded);
            if (!decoded)
                return false;
            const auto message = nlohmann::json::parse(*decoded);
            const auto origin = message.value("Origin", std::uint64_t{});
            const auto event = message.value("Event", std::string{});
            const auto payload = message.value("Payload", std::string{});
            if (!origin || origin == localId_)
                return false;

            EventHandler handler;
            {
                std::scoped_lock lock(handlersMutex_);
                const auto found = handlers_.find(event);
                if (found != handlers_.end())
                    handler = found->second;
            }
            const auto isMatchmaking = event == "Matchmaking::Update" ||
                event == "Matchmaking::Terminate";
            if (!isMatchmaking && !handler)
                return false;

            const auto decodedPayload = base64Decode(payload);
            if (!decodedPayload)
                return false;

            {
                std::scoped_lock lock(sessionsMutex_);
                const auto [node, inserted] = nodeAddresses_.try_emplace(origin, sourceAddress);
                if (!inserted && node->second != sourceAddress)
                    return false;

                const auto existing = std::ranges::find_if(sessions_, [origin](const RemoteSession &session)
                {
                    return session.id == origin;
                });
                if (event == "Matchmaking::Terminate")
                {
                    if (existing != sessions_.end())
                        sessions_.erase(existing);
                    return true;
                }
                if (event == "Matchmaking::Update")
                {
                    auto properties = nlohmann::json::parse(*decodedPayload);
                    if (!properties.is_object())
                        return false;
                    const auto now = std::chrono::steady_clock::now();
                    if (existing == sessions_.end())
                        sessions_.push_back(RemoteSession{ sourceAddress, origin, std::move(properties), now });
                    else
                    {
                        existing->properties = std::move(properties);
                        existing->updatedAt = now;
                    }
                    return true;
                }
            }

            handler(origin, *decodedPayload);
            return true;
        }
        catch (const nlohmann::json::exception &)
        {
            return false;
        }
    }

    std::vector<LanDiscovery::RemoteSession> LanDiscovery::activeSessions() const
    {
        constexpr auto Lifetime = std::chrono::seconds(30);
        const auto now = std::chrono::steady_clock::now();
        std::scoped_lock lock(sessionsMutex_);
        std::erase_if(sessions_, [now](const RemoteSession &session)
        {
            return now - session.updatedAt >= Lifetime;
        });
        return sessions_;
    }
}
