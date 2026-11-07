#pragma once

#include "AuthSession.hpp"
#include "LanDiscovery.hpp"
#include "ServiceRegistry.hpp"

#include <functional>
#include <optional>

namespace AlwaysofflineRe::Demonware
{
    /// Lobby service 11 -- the ROOM service, and the one that gates the 准备 (Ready) button.
    ///
    /// The class keeps the name Unknown0B because that is what dest1yo's Alwaysoffline.Localnet32
    /// calls it and every annotation in tools/reverse/annotations maps to those names
    /// (Unknown0B_dispatch at 0x10051C90, Unknown0B_task13 at 0x10051B75). Renaming here would
    /// break that correspondence for no gain. What follows is the understanding the C# OLfinal
    /// lobby server recovered for the same service, which is the part worth carrying over.
    ///
    /// THE CHAIN (full derivation in CODOL-main re/ROOM-START.md sect.38-39):
    ///
    ///   Pressing 准备 reaches dwRoomImp vtable+0x84 (FUN_0062c690), which SENDS NOTHING -- it
    ///   appends to the room's outbound priority queue at dwRoomImp+0x3A0D4. The per-frame pump
    ///   FUN_00632e80 drains those queues only inside `if (vtable+0x5c)`, and that predicate
    ///   (FUN_0062FED0) requires the client to BE IN A ROOM:
    ///
    ///       (room != 0 && room[1] != 0) || roomID64 != 0
    ///
    ///   Entering the room screen allocates one of two static 0x25D0-byte records at 0x0E374640,
    ///   stores it at dwRoomImp+0x1C, and then asks US to create the room -- FUN_007e7ee0 ->
    ///   FUN_00b8e670 -> FUN_00b78bc0(buffer, 0x0B, 0x0D): service 11, task 13. If that task
    ///   fails, the client tears the record straight back down (FUN_006340d0 -> FUN_00633ee0)
    ///   and the queued ready message never leaves.
    ///
    /// SO TASK 13'S REPLY MUST CARRY EXACTLY ONE RESULT. A zero-result acknowledgement is a
    /// failure as far as the client is concerned, and it is the failure that looks most like
    /// success in a log. The tell is on the wire one request later: the client's next 11/4
    /// echoes the room id back as `0A 0000000000000000` -- a tag-10 u64 of ZERO -- because it
    /// never received one. Check that field before believing the room came up.
    ///
    /// THE RESULT'S SHAPE is FUN_00b96e30's read order, the deserialiser FUN_00b8e670 binds to
    /// room+8. It fails the whole parse if any field is missing or mistyped:
    ///
    ///     reader        tag        object   room record
    ///     FUN_00b769c0  10 UInt64  +0x08    +0x10   ROOM ID -- FUN_007e7a20 looks rooms up by it
    ///     FUN_00b76200   8 UInt32  +0x10    +0x18   member count (FUN_007e7b00 walks
    ///                                               room+0x40 + i*0x60 with it)
    ///     FUN_00b76200   8 UInt32  +0x14    +0x1C
    ///     FUN_00b769c0  10 UInt64  +0x18    +0x20   second id, sent on by FUN_00634350
    ///     FUN_00b76870   1 Bool    +0x20    +0x28
    ///     FUN_00b76870   1 Bool    +0x21    +0x29
    ///     FUN_00b76200   8 UInt32  +0x24    +0x2C
    ///
    /// TWO SOURCES DISAGREE ON THREE OF THOSE VALUES, and the disagreement is deliberately left
    /// standing rather than resolved by preference. dest1yo's shipped DLL -- which this code
    /// ports and which drives a real client -- sends member count 0, third field 18, last field
    /// 1, and uses the user id as the room id. The C# OLfinal server sends 1, 0, 0 with a fixed
    /// room id of 69421, reasoning that room+0x18 is the member count and one member is us.
    /// Both reach a lobby, so neither is refuted, and the values below stay as the shipped DLL
    /// had them.
    ///
    /// TODO(CODOL): settle it by measurement -- put a client in a room and read room+0x18 and
    /// room+0x2C out of the live record at 0x0E374640. Done when the member list is observed
    /// to be right (or wrong) for a known member count, not argued from the reply.
    class Unknown0BService
    {
    public:
        using PushSink = std::function<void(std::vector<std::uint8_t>, std::uint8_t)>;
        using BookingSink = std::function<void(std::string_view)>;
        enum class RoomEvent
        {
            Enter,
            Leave,
            Ready,
        };
        using RoomEventSink = std::function<bool(RoomEvent)>;

        explicit Unknown0BService(
            AuthSession &session,
            PushSink pushSink = {},
            LanDiscovery *messageBus = nullptr,
            BookingSink bookingSink = {},
            RoomEventSink roomEventSink = {});

        void registerTasks(ServiceRegistry &registry) const;
        [[nodiscard]] static std::optional<std::vector<std::uint8_t>> decodeChannelPush(
            std::string_view eventJson,
            std::uint64_t localUserId);

    private:
        [[nodiscard]] ServiceResponse consumeUserPair(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse task2(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse task4(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse task5(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse task10(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse task13(const ServiceRequest &request) const;

        AuthSession &session_;
        PushSink pushSink_;
        LanDiscovery *messageBus_{};
        BookingSink bookingSink_;
        RoomEventSink roomEventSink_;
    };
}
