#include "InstantMessageService.hpp"

#include "ByteBuffer.hpp"

#include <utility>

#include <nlohmann/json.hpp>

namespace AlwaysofflineRe::Demonware
{
    InstantMessageService::InstantMessageService(
        AuthSession &session,
        PushSink pushSink,
        LanDiscovery *messageBus,
        BookingSink bookingSink)
        : session_(session),
          pushSink_(std::move(pushSink)),
          messageBus_(messageBus),
          bookingSink_(std::move(bookingSink))
    {
    }

    void InstantMessageService::registerTasks(ServiceRegistry &registry) const
    {
        registry.registerTask(0x06, 5, "Messaging::readQueuedMessages", [this](const auto &request)
        {
            return task5(request);
        });
        registry.registerTask(0x06, 14, "Messaging::sendGlobalInstantMessage", [this](const auto &request)
        {
            return task14(request);
        });
        registry.registerTask(0x06, 18, "Messaging::sendInstantMessage", [this](const auto &request)
        {
            return task18(request);
        });
    }

    ServiceResponse InstantMessageService::task5(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        [[maybe_unused]] std::uint32_t offset{};
        [[maybe_unused]] std::uint32_t maximumResults{};
        [[maybe_unused]] bool consume{};
        if (!input.readU32(offset) || !input.readU32(maximumResults) ||
            !input.readBool(consume) || !input.empty() || !input.valid())
        {
            return ServiceResponse{ .error = 1000, .task = request.task };
        }

        // The archived ring has no insertion xrefs. Both pagination modes are
        // therefore observably empty in this build.
        return ServiceResponse{ .task = request.task };
    }

    ServiceResponse InstantMessageService::task14(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint64_t recipient{};
        std::vector<std::uint8_t> message;
        if (!input.readU64(recipient) || !input.readBlob(message))
            return ServiceResponse{ .error = 1000, .task = request.task };
        const auto trailing = input.remaining();
        if (!input.valid() || (!trailing.empty() &&
            (trailing.size() != 1 || trailing.front() != 0)))
        {
            return ServiceResponse{ .error = 1000, .task = request.task };
        }

        const auto localUserId = session_.snapshot().userId;
        if (recipient != 0 && recipient != localUserId)
            publish(recipient, message, true, true);
        else if (auto response = decodeLocalCommand(message))
            publish(localUserId, *response, true, false);
        return ServiceResponse{ .task = request.task };
    }

    ServiceResponse InstantMessageService::task18(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::vector<std::uint8_t> message;
        if (!input.readBlob(message))
            return ServiceResponse{ .error = 1000, .task = request.task };

        while (!input.empty() && input.valid())
        {
            std::uint64_t recipient{};
            if (!input.readU64(recipient))
                return ServiceResponse{ .error = 1000, .task = request.task };
            publish(recipient, message, false, true);
        }
        if (!input.valid())
            return ServiceResponse{ .error = 1000, .task = request.task };
        return ServiceResponse{ .task = request.task };
    }

    void InstantMessageService::publish(
        const std::uint64_t recipient,
        const std::span<const std::uint8_t> message,
        const bool invokeLocalReceiver,
        const bool broadcastEvent) const
    {
        const auto identity = session_.snapshot();
        const std::vector<std::uint8_t> messageBytes(message.begin(), message.end());
        const nlohmann::json event{
            { "Sendername", identity.username },
            { "Recipient", recipient },
            { "SenderID", identity.userId },
            { "Message", messageBytes },
        };
        if (invokeLocalReceiver && pushSink_)
        {
            if (auto push = decodeInstantPush(event.dump(), identity.userId))
                pushSink_(std::move(*push), 2);
        }
        if (broadcastEvent && messageBus_)
            messageBus_->broadcast("Demonware::Instantmessage", event.dump());
    }

    std::optional<std::vector<std::uint8_t>> InstantMessageService::decodeLocalCommand(
        const std::span<const std::uint8_t> message) const
    {
        ByteBuffer input(message);
        input.useDataTypes(false);
        std::vector<std::uint8_t> commandBytes;
        if (!input.readBlob(commandBytes) || !input.empty() || !input.valid())
            return std::nullopt;

        const std::string command(commandBytes.begin(), commandBytes.end());
        if (bookingSink_ && command.starts_with("mmstart "))
            bookingSink_(command);

        const auto separator = command.find(' ');
        const auto token = std::string_view(command).substr(0, separator);
        std::uint32_t hash = 0x811C9DC5;
        for (const auto character : token)
            hash = (hash ^ static_cast<std::uint8_t>(character)) * 0x01000193;
        if (hash != 0xDEC30B2A)
            return std::nullopt;

        constexpr std::string_view Accepted = "mmbook accepted";
        ByteBuffer response;
        response.useDataTypes(false);
        response.writeBlob(std::span(
            reinterpret_cast<const std::uint8_t *>(Accepted.data()), Accepted.size()));
        return response.data();
    }

    std::optional<std::vector<std::uint8_t>> InstantMessageService::decodeInstantPush(
        const std::string_view eventJson,
        const std::uint64_t localUserId)
    {
        const auto event = nlohmann::json::parse(eventJson, nullptr, false);
        if (!event.is_object())
            return std::nullopt;

        const auto senderName = event.find("Sendername");
        const auto recipient = event.find("Recipient");
        const auto senderId = event.find("SenderID");
        const auto message = event.find("Message");
        if (senderName == event.end() || !senderName->is_string() ||
            recipient == event.end() || !recipient->is_number_unsigned() ||
            senderId == event.end() || !senderId->is_number_unsigned() ||
            message == event.end() || !message->is_array() ||
            recipient->get<std::uint64_t>() != localUserId)
        {
            return std::nullopt;
        }

        std::vector<std::uint8_t> messageBytes;
        messageBytes.reserve(message->size());
        for (const auto &value : *message)
        {
            if (!value.is_number_unsigned() || value.get<std::uint64_t>() > UINT8_MAX)
                return std::nullopt;
            messageBytes.push_back(static_cast<std::uint8_t>(value.get<std::uint64_t>()));
        }

        ByteBuffer push;
        push.writeU32(21);
        push.writeU64(senderId->get<std::uint64_t>());
        push.writeString(senderName->get<std::string>());
        push.writeBlob(messageBytes);
        return push.data();
    }
}
