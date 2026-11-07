#include "Unknown0BService.hpp"

#include "ByteBuffer.hpp"

#include <array>
#include <utility>

#include <nlohmann/json.hpp>

namespace AlwaysofflineRe::Demonware
{
    Unknown0BService::Unknown0BService(
        AuthSession &session,
        PushSink pushSink,
        LanDiscovery *messageBus,
        BookingSink bookingSink,
        RoomEventSink roomEventSink)
        : session_(session),
          pushSink_(std::move(pushSink)),
          messageBus_(messageBus),
          bookingSink_(std::move(bookingSink)),
          roomEventSink_(std::move(roomEventSink))
    {
    }

    void Unknown0BService::registerTasks(ServiceRegistry &registry) const
    {
        for (const auto task : { std::uint8_t{ 1 }, std::uint8_t{ 9 }, std::uint8_t{ 11 } })
        {
            registry.registerTask(0x0B, task, "Unknown0B::consumeUserPair", [this](const auto &request)
            {
                return consumeUserPair(request);
            });
        }
        registry.registerTask(0x0B, 2, "Unknown0B::task2", [this](const auto &request)
        {
            return task2(request);
        });
        registry.registerTask(0x0B, 4, "Unknown0B::setRoomData", [this](const auto &request)
        {
            return task4(request);
        });
        registry.registerTask(0x0B, 5, "Unknown0B::publishChannelMessage", [this](const auto &request)
        {
            return task5(request);
        });
        registry.registerTask(0x0B, 10, "Unknown0B::task10", [this](const auto &request)
        {
            return task10(request);
        });
        registry.registerTask(0x0B, 13, "Unknown0B::createRoom", [this](const auto &request)
        {
            return task13(request);
        });
    }

    ServiceResponse Unknown0BService::consumeUserPair(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint64_t firstUserId{};
        std::uint64_t secondUserId{};
        if (!input.readU64(firstUserId) || !input.readU64(secondUserId) ||
            !input.empty() || !input.valid())
        {
            return ServiceResponse{ .error = 1000, .task = request.task };
        }
        return ServiceResponse{ .task = request.task };
    }

    ServiceResponse Unknown0BService::task2(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint64_t userId{};
        if (!input.readU64(userId) || userId != session_.snapshot().userId)
            return ServiceResponse{ .error = 1000, .task = request.task };
        if (roomEventSink_ && !roomEventSink_(RoomEvent::Leave))
            return ServiceResponse{ .error = 1000, .task = request.task };
        return ServiceResponse{ .task = request.task };
    }

    /// Task 4 -- every room message the client sends, as `(u64 roomId, blob batch, u32)`.
    /// NOT a heartbeat: FUN_007e82f0, at the end of FUN_00632e80's drain block, builds this
    /// task via FUN_00b8ec00 = FUN_00b78bc0(buf, 0x0B, 4), so the packed batch of queued room
    /// messages -- 准备 among them -- arrives HERE, inside the blob. Unlike task 13 it binds no
    /// result buffer (FUN_00b8ec00 never calls FUN_00b83cb0), so a bare acknowledgement is
    /// correct for this one.
    ServiceResponse Unknown0BService::task4(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint64_t channelId{};
        std::vector<std::uint8_t> message;
        std::uint32_t type{};
        if (!input.readU64(channelId) || !input.readBlob(message) || !input.readU32(type))
            return ServiceResponse{ .error = 1000, .task = request.task };

        // TODO(CODOL): capture the corresponding unready payload before
        // generalizing this exact ready-state message into a field parser.
        constexpr std::array<std::uint8_t, 16> CapturedReadyMessage{
            0x0C, 0x00, 0x00, 0x00, 0x02, 0x02, 0x00, 0x00,
            0x00, 0x08, 0x00, 0x00, 0x00, 0x80, 0x08, 0x00,
        };
        if (roomEventSink_ &&
            std::ranges::equal(message, CapturedReadyMessage) &&
            !roomEventSink_(RoomEvent::Ready))
        {
            return ServiceResponse{ .error = 1000, .task = request.task };
        }

        const auto identity = session_.snapshot();
        const nlohmann::json event{
            { "Sendername", identity.username },
            { "SenderID", identity.userId },
            { "ChannelID", channelId },
            { "Recipient", 0 },
            { "Message", message },
            { "Whisper", false },
            { "Type", type },
        };
        if (pushSink_)
        {
            if (auto push = decodeChannelPush(event.dump(), identity.userId))
                pushSink_(std::move(*push), 2);
        }
        if (messageBus_)
            messageBus_->broadcast("Demonware::Channelmessage", event.dump());
        return ServiceResponse{ .task = request.task };
    }

    ServiceResponse Unknown0BService::task5(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint64_t channelId{};
        std::uint64_t recipient{};
        std::vector<std::uint8_t> message;
        std::uint32_t type{};
        if (!input.readU64(channelId) || !input.readU64(recipient) ||
            !input.readBlob(message) || !input.readU32(type) ||
            !input.empty() || !input.valid())
        {
            return ServiceResponse{ .error = 1000, .task = request.task };
        }

        auto command = std::string_view(
            reinterpret_cast<const char *>(message.data()), message.size());
        if (!command.empty() && command.back() == '\0')
            command.remove_suffix(1);
        if (bookingSink_ && command.starts_with("mmstart "))
            bookingSink_(command);

        const auto identity = session_.snapshot();
        const nlohmann::json event{
            { "Sendername", identity.username },
            { "SenderID", identity.userId },
            { "ChannelID", channelId },
            { "Recipient", recipient },
            { "Message", message },
            { "Whisper", true },
            { "Type", type },
        };
        if (pushSink_)
        {
            if (auto push = decodeChannelPush(event.dump(), identity.userId))
                pushSink_(std::move(*push), 2);
        }
        if (messageBus_)
            messageBus_->broadcast("Demonware::Channelmessage", event.dump());
        return ServiceResponse{ .task = request.task };
    }

    std::optional<std::vector<std::uint8_t>> Unknown0BService::decodeChannelPush(
        const std::string_view eventJson,
        const std::uint64_t localUserId)
    {
        const auto event = nlohmann::json::parse(eventJson, nullptr, false);
        if (!event.is_object())
            return std::nullopt;

        const auto senderName = event.find("Sendername");
        const auto senderId = event.find("SenderID");
        const auto channelId = event.find("ChannelID");
        const auto recipient = event.find("Recipient");
        const auto message = event.find("Message");
        const auto whisper = event.find("Whisper");
        const auto type = event.find("Type");
        if (senderName == event.end() || !senderName->is_string() ||
            senderId == event.end() || !senderId->is_number_unsigned() ||
            channelId == event.end() || !channelId->is_number_unsigned() ||
            recipient == event.end() || !recipient->is_number_unsigned() ||
            message == event.end() || !message->is_array() ||
            whisper == event.end() || !whisper->is_boolean() ||
            type == event.end() || !type->is_number_unsigned())
        {
            return std::nullopt;
        }

        const auto isWhisper = whisper->get<bool>();
        if (isWhisper && recipient->get<std::uint64_t>() != localUserId)
            return std::nullopt;

        std::vector<std::uint8_t> messageBytes;
        messageBytes.reserve(message->size());
        for (const auto &value : *message)
        {
            if (!value.is_number_unsigned() || value.get<std::uint64_t>() > UINT8_MAX)
                return std::nullopt;
            messageBytes.push_back(static_cast<std::uint8_t>(value.get<std::uint64_t>()));
        }

        const auto messageType = type->get<std::uint64_t>();
        if (messageType > UINT32_MAX)
            return std::nullopt;
        ByteBuffer push;
        push.writeU32(isWhisper ? 7 : 8);
        push.writeU64(senderId->get<std::uint64_t>());
        push.writeString(senderName->get<std::string>());
        push.writeU64(channelId->get<std::uint64_t>());
        push.writeBlob(messageBytes);
        push.writeU32(static_cast<std::uint32_t>(messageType));
        return push.data();
    }

    ServiceResponse Unknown0BService::task10(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint64_t firstUserId{};
        std::uint64_t secondUserId{};
        std::uint32_t value{};
        bool enabled{};
        if (!input.readU64(firstUserId) || !input.readU64(secondUserId) ||
            !input.readU32(value) || !input.readBool(enabled) ||
            !input.empty() || !input.valid())
        {
            return ServiceResponse{ .error = 1000, .task = request.task };
        }
        return ServiceResponse{ .task = request.task };
    }

    /// Task 13 -- CREATE ROOM. The request carries no arguments at all; its whole frame is
    /// `04000000 86 0B 03 0D`, so everything the client needs comes back in the reply.
    ///
    /// The one result below is not optional -- see the class comment. The field order and types
    /// are FUN_00b96e30's, and the values are dest1yo's shipped ones; three of them are disputed
    /// and the TODO for settling that is on the class.
    ServiceResponse Unknown0BService::task13(const ServiceRequest &request) const
    {
        const auto emptyArgument = request.payload.empty() ||
            (request.payload.size() == 1 && request.payload.front() == 0);
        if (!emptyArgument ||
            (roomEventSink_ && !roomEventSink_(RoomEvent::Enter)))
        {
            return ServiceResponse{ .error = 1000, .task = request.task };
        }
        const auto userId = session_.snapshot().userId;
        ByteBuffer object;
        object.writeU64(static_cast<std::uint32_t>(userId));   // room+0x10  room id, must be non-zero
        object.writeU32(0);                                    // room+0x18  member count (disputed: C# sends 1)
        object.writeU32(18);                                   // room+0x1C  (disputed: C# sends 0)
        object.writeU64(userId);                               // room+0x20  second id, resent by FUN_00634350
        object.writeBool(false);                               // room+0x28
        object.writeBool(false);                               // room+0x29
        object.writeU32(1);                                    // room+0x2C  (disputed: C# sends 0)
        return ServiceResponse{ .task = request.task, .objects = { object.data() } };
    }
}
