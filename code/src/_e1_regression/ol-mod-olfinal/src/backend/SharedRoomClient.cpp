#include "SharedRoomClient.hpp"

#include "SharedRoomControl.hpp"
#include "../shared/DedicatedControl.hpp"

namespace AlwaysofflineRe
{
    namespace
    {
        // Read per call rather than cached: the owner's address is
        // configuration, and a cached copy would silently outlive a change to
        // it in a process that is already running.
        std::string ownerHost()
        {
            return OlMod::DedicatedControl::configuredHostAddress();
        }
    }

    SharedRoomClient::SharedRoomClient(Reporter reporter)
        : reporter_(std::move(reporter))
    {
    }

    std::uint64_t SharedRoomClient::nextRequestId()
    {
        const auto requestId = nextRequestId_++;
        if (!nextRequestId_)
            nextRequestId_ = 1;
        return requestId;
    }

    bool SharedRoomClient::connect(
        const Demonware::AuthIdentity &identity,
        const std::uint16_t bridgePort)
    {
        std::scoped_lock lock(mutex_);
        const auto result = OlMod::DedicatedControl::submit(
            ownerHost(),
            SharedRoomControl::configuredPort(),
            {
                .type = OlMod::DedicatedControl::MessageType::RoomConnect,
                .requestId = nextRequestId(),
                .payload = SharedRoomControl::encode({
                    .userId = identity.userId,
                    .displayName = identity.username,
                    .bridgePort = bridgePort,
                }),
            });
        const auto token = SharedRoomControl::decodeToken(result.payload);
        if (!result.delivered ||
            result.status != OlMod::DedicatedControl::ResponseStatus::Accepted ||
            !token)
        {
            if (reporter_)
            {
                reporter_(
                    "shared room connect rejected user=" + std::to_string(identity.userId) +
                    " bridge=" + std::to_string(bridgePort) +
                    " delivered=" + std::to_string(result.delivered) +
                    " status=" + std::to_string(static_cast<unsigned>(result.status)) +
                    " token=" + std::to_string(token.has_value()));
            }
            return false;
        }
        connection_ = Connection{
            .userId = identity.userId,
            .token = *token,
        };
        return true;
    }

    bool SharedRoomClient::disconnect(const std::uint64_t userId)
    {
        std::scoped_lock lock(mutex_);
        if (!connection_ || connection_->userId != userId)
            return false;
        const auto result = OlMod::DedicatedControl::submit(
            ownerHost(),
            SharedRoomControl::configuredPort(),
            {
                .type = OlMod::DedicatedControl::MessageType::RoomDisconnect,
                .requestId = nextRequestId(),
                .payload = SharedRoomControl::encode(
                    SharedRoomControl::MemberRequest{
                    .userId = userId,
                    .connectionToken = connection_->token,
                }),
            });
        if (!result.delivered ||
            result.status != OlMod::DedicatedControl::ResponseStatus::Accepted)
        {
            return false;
        }
        connection_.reset();
        return true;
    }

    bool SharedRoomClient::setReady(
        const std::uint64_t userId, const bool ready)
    {
        std::scoped_lock lock(mutex_);
        if (!connection_ || connection_->userId != userId)
            return false;
        const auto result = OlMod::DedicatedControl::submit(
            ownerHost(),
            SharedRoomControl::configuredPort(),
            {
                .type = OlMod::DedicatedControl::MessageType::RoomSetReady,
                .requestId = nextRequestId(),
                .payload = SharedRoomControl::encode(
                    SharedRoomControl::ReadyRequest{
                    .userId = userId,
                    .connectionToken = connection_->token,
                    .ready = ready,
                }),
            });
        return result.delivered &&
            result.status == OlMod::DedicatedControl::ResponseStatus::Accepted;
    }

    std::optional<FrozenRoomRoster> SharedRoomClient::freeze(
        const std::uint64_t generation)
    {
        if (!generation)
            return std::nullopt;
        std::scoped_lock lock(mutex_);
        if (!connection_)
            return std::nullopt;
        const auto result = OlMod::DedicatedControl::submit(
            ownerHost(),
            SharedRoomControl::configuredPort(),
            {
                .type = OlMod::DedicatedControl::MessageType::RoomFreeze,
                .requestId = nextRequestId(),
                .payload = SharedRoomControl::encode(
                    SharedRoomControl::FreezeRequest{
                    .generation = generation,
                    .claimant = {
                        .userId = connection_->userId,
                        .connectionToken = connection_->token,
                    },
                }),
            });
        if (!result.delivered ||
            result.status != OlMod::DedicatedControl::ResponseStatus::Accepted)
        {
            return std::nullopt;
        }
        return SharedRoomControl::decodeRoster(result.payload);
    }

    std::optional<std::vector<std::uint8_t>>
        SharedRoomClient::canonicalizeSessionDescriptor(
            const std::uint64_t userId,
            const std::span<const std::uint8_t> descriptor)
    {
        std::scoped_lock lock(mutex_);
        if (!connection_ || connection_->userId != userId || descriptor.empty())
            return std::nullopt;
        const auto payload = SharedRoomControl::encode(
            SharedRoomControl::SessionDescriptorRequest{
                .userId = userId,
                .connectionToken = connection_->token,
                .descriptor = {
                    reinterpret_cast<const char *>(descriptor.data()),
                    descriptor.size(),
                },
            });
        if (payload.empty())
            return std::nullopt;
        const auto result = OlMod::DedicatedControl::submit(
            ownerHost(),
            SharedRoomControl::configuredPort(),
            {
                .type = OlMod::DedicatedControl::MessageType::
                    RoomCanonicalizeSession,
                .requestId = nextRequestId(),
                .payload = payload,
            });
        if (!result.delivered ||
            result.status != OlMod::DedicatedControl::ResponseStatus::Accepted ||
            result.payload.empty())
        {
            return std::nullopt;
        }
        return std::vector<std::uint8_t>(
            result.payload.begin(), result.payload.end());
    }
}
