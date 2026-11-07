#include "SharedRoomSessionOwner.hpp"

#include <algorithm>
#include <iterator>
#include <utility>

namespace AlwaysofflineRe
{
    SharedRoomSessionOwner::SharedRoomSessionOwner(const std::size_t capacity)
        : capacity_(capacity)
    {
    }

    bool SharedRoomSessionOwner::validDisplayName(const std::string_view value)
    {
        return !value.empty() && value.size() <= 16 &&
            std::ranges::all_of(value, [](const unsigned char character) {
                return character >= 0x20 && character <= 0x7E;
            });
    }

    std::optional<std::uint64_t> SharedRoomSessionOwner::connect(
        const std::uint64_t userId,
        std::string displayName,
        const std::uint16_t bridgePort,
        const std::uint32_t bridgeIpv4)
    {
        const std::lock_guard lock(mutex_);
        // TWO MEMBERS COLLIDE ONLY WHEN THEY SHARE A PORT ON THE SAME MACHINE.
        // Keying on the port alone was right while everyone was on the owner's
        // box and is exactly wrong once they are not: two friends both running
        // the DEFAULT bridge port 28962 on their own PCs are not a duplicate,
        // and the second of them used to be refused here.
        if (!userId || !bridgePort || !validDisplayName(displayName) ||
            (!members_.contains(userId) && members_.size() >= capacity_) ||
            std::ranges::any_of(members_, [&](const auto &entry) {
                return entry.first != userId &&
                    entry.second.bridgePort == bridgePort &&
                    entry.second.bridgeIpv4 == bridgeIpv4;
            }))
        {
            return std::nullopt;
        }
        canonicalSessionDescriptor_.reset();
        auto connectionToken = nextConnectionToken_++;
        if (!nextConnectionToken_)
            nextConnectionToken_ = 1;
        members_.insert_or_assign(userId, SharedRoomMember{
            .userId = userId,
            .displayName = std::move(displayName),
            .bridgePort = bridgePort,
            .bridgeIpv4 = bridgeIpv4,
            .connectionToken = connectionToken,
        });
        return connectionToken;
    }

    bool SharedRoomSessionOwner::disconnect(
        const std::uint64_t userId,
        const std::uint64_t connectionToken)
    {
        const std::lock_guard lock(mutex_);
        const auto member = members_.find(userId);
        if (member == members_.end() ||
            member->second.connectionToken != connectionToken)
        {
            return false;
        }
        members_.erase(member);
        canonicalSessionDescriptor_.reset();
        return true;
    }

    bool SharedRoomSessionOwner::setReady(
        const std::uint64_t userId,
        const std::uint64_t connectionToken,
        const bool ready)
    {
        const std::lock_guard lock(mutex_);
        const auto member = members_.find(userId);
        if (member == members_.end() ||
            member->second.connectionToken != connectionToken)
        {
            return false;
        }
        member->second.ready = ready;
        return true;
    }

    std::optional<FrozenRoomRoster> SharedRoomSessionOwner::freeze(
        const std::uint64_t generation,
        const std::uint64_t claimantUserId,
        const std::uint64_t claimantToken) const
    {
        const std::lock_guard lock(mutex_);
        if (const auto frozen = frozenRosters_.find(generation);
            frozen != frozenRosters_.end())
        {
            return frozen->second;
        }
        if (!generation || members_.empty() ||
            std::ranges::any_of(members_, [](const auto &entry) {
                return !entry.second.ready;
            }))
        {
            return std::nullopt;
        }
        std::uint64_t ownerUserId = claimantUserId;
        if (claimantUserId || claimantToken)
        {
            const auto claimant = members_.find(claimantUserId);
            if (claimant == members_.end() ||
                claimant->second.connectionToken != claimantToken)
            {
                return std::nullopt;
            }
            if (!allocationOwnerUserId_)
                allocationOwnerUserId_ = claimantUserId;
            ownerUserId = *allocationOwnerUserId_;
        }
        else if (!members_.empty())
        {
            // Compatibility for isolated tests and the legacy one-client path.
            ownerUserId = members_.begin()->first;
        }
        FrozenRoomRoster roster{
            .generation = generation,
            .ownerUserId = ownerUserId,
        };
        roster.members.reserve(members_.size());
        std::ranges::transform(
            members_,
            std::back_inserter(roster.members),
            [](const auto &entry) { return entry.second; });
        frozenRosters_.emplace(generation, roster);
        return roster;
    }

    std::vector<SharedRoomMember> SharedRoomSessionOwner::members() const
    {
        const std::lock_guard lock(mutex_);
        std::vector<SharedRoomMember> result;
        result.reserve(members_.size());
        std::ranges::transform(
            members_,
            std::back_inserter(result),
            [](const auto &entry) { return entry.second; });
        return result;
    }

    std::optional<std::string>
        SharedRoomSessionOwner::canonicalizeSessionDescriptor(
            const std::uint64_t userId,
            const std::uint64_t connectionToken,
            std::string descriptor)
    {
        const std::lock_guard lock(mutex_);
        const auto member = members_.find(userId);
        if (member == members_.end() ||
            member->second.connectionToken != connectionToken ||
            descriptor.empty())
        {
            return std::nullopt;
        }
        if (!canonicalSessionDescriptor_)
            canonicalSessionDescriptor_ = std::move(descriptor);
        return canonicalSessionDescriptor_;
    }
}
