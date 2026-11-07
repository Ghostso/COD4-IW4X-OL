#pragma once

#include <cstdint>
#include <map>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace AlwaysofflineRe
{
    struct SharedRoomMember
    {
        std::uint64_t userId{};
        std::string displayName;
        std::uint16_t bridgePort{};
        // Host order, and ZERO MEANS "the owner's own machine" -- an owner that
        // never learned an address behaves exactly as it did when a member was
        // a port alone.
        std::uint32_t bridgeIpv4{};
        std::uint64_t connectionToken{};
        bool ready{};

        bool operator==(const SharedRoomMember &) const = default;
    };

    struct FrozenRoomRoster
    {
        std::uint64_t generation{};
        std::uint64_t ownerUserId{};
        std::vector<SharedRoomMember> members;

        bool operator==(const FrozenRoomRoster &) const = default;
    };

    class SharedRoomSessionOwner
    {
    public:
        explicit SharedRoomSessionOwner(std::size_t capacity = 18);

        [[nodiscard]] std::optional<std::uint64_t> connect(
            std::uint64_t userId,
            std::string displayName,
            std::uint16_t bridgePort,
            std::uint32_t bridgeIpv4 = 0);
        [[nodiscard]] bool disconnect(
            std::uint64_t userId,
            std::uint64_t connectionToken);
        [[nodiscard]] bool setReady(
            std::uint64_t userId,
            std::uint64_t connectionToken,
            bool ready);
        [[nodiscard]] std::optional<FrozenRoomRoster> freeze(
            std::uint64_t generation,
            std::uint64_t claimantUserId = 0,
            std::uint64_t claimantToken = 0) const;
        [[nodiscard]] std::optional<std::string> canonicalizeSessionDescriptor(
            std::uint64_t userId,
            std::uint64_t connectionToken,
            std::string descriptor);
        [[nodiscard]] std::vector<SharedRoomMember> members() const;

    private:
        [[nodiscard]] static bool validDisplayName(std::string_view value);

        std::size_t capacity_;
        std::uint64_t nextConnectionToken_{1};
        std::map<std::uint64_t, SharedRoomMember> members_;
        mutable std::map<std::uint64_t, FrozenRoomRoster> frozenRosters_;
        mutable std::optional<std::uint64_t> allocationOwnerUserId_;
        std::optional<std::string> canonicalSessionDescriptor_;
        mutable std::mutex mutex_;
    };
}
