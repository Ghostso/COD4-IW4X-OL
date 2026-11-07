#pragma once

#include "SharedRoomSessionOwner.hpp"
#include "../shared/DedicatedControl.hpp"

#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <string_view>

namespace AlwaysofflineRe::SharedRoomControl
{
    constexpr std::uint16_t DefaultPort = 28970;

    struct ConnectRequest
    {
        std::uint64_t userId{};
        std::string displayName;
        std::uint16_t bridgePort{};

        bool operator==(const ConnectRequest &) const = default;
    };

    struct MemberRequest
    {
        std::uint64_t userId{};
        std::uint64_t connectionToken{};

        bool operator==(const MemberRequest &) const = default;
    };

    struct ReadyRequest
    {
        std::uint64_t userId{};
        std::uint64_t connectionToken{};
        bool ready{};

        bool operator==(const ReadyRequest &) const = default;
    };

    struct SessionDescriptorRequest
    {
        std::uint64_t userId{};
        std::uint64_t connectionToken{};
        std::string descriptor;

        bool operator==(const SessionDescriptorRequest &) const = default;
    };

    struct FreezeRequest
    {
        std::uint64_t generation{};
        MemberRequest claimant;

        bool operator==(const FreezeRequest &) const = default;
    };

    [[nodiscard]] std::string encode(const ConnectRequest &request);
    [[nodiscard]] std::optional<ConnectRequest> decodeConnect(
        std::string_view payload);
    [[nodiscard]] std::string encode(const MemberRequest &request);
    [[nodiscard]] std::optional<MemberRequest> decodeMember(
        std::string_view payload);
    [[nodiscard]] std::string encode(const ReadyRequest &request);
    [[nodiscard]] std::optional<ReadyRequest> decodeReady(
        std::string_view payload);
    [[nodiscard]] std::string encode(const SessionDescriptorRequest &request);
    [[nodiscard]] std::optional<SessionDescriptorRequest>
        decodeSessionDescriptor(std::string_view payload);
    [[nodiscard]] std::string encode(const FreezeRequest &request);
    [[nodiscard]] std::optional<FreezeRequest> decodeFreeze(
        std::string_view payload);
    [[nodiscard]] std::string encodeToken(std::uint64_t token);
    [[nodiscard]] std::optional<std::uint64_t> decodeToken(
        std::string_view payload);
    [[nodiscard]] std::string encodeRoster(const FrozenRoomRoster &roster);
    [[nodiscard]] std::optional<FrozenRoomRoster> decodeRoster(
        std::string_view payload);
    [[nodiscard]] std::uint16_t configuredPort();

    class Handler
    {
    public:
        explicit Handler(SharedRoomSessionOwner &owner) : owner_(owner) {}
        [[nodiscard]] OlMod::DedicatedControl::Response operator()(
            const OlMod::DedicatedControl::Message &message);

    private:
        SharedRoomSessionOwner &owner_;
    };
}
