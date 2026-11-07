#include "DedicatedSession.hpp"

#include "CodolPlaylist.hpp"

#include <algorithm>
#include <limits>
#include <utility>

namespace
{
    constexpr std::uint32_t PayloadMagic = 0x53444C4F; // OLDS
    constexpr std::uint16_t LoadoutPayloadKind = 1;
    constexpr std::uint16_t SessionStartPayloadKind = 2;
    constexpr std::uint16_t ClientSessionCapturePayloadKind = 3;

    class Writer
    {
    public:
        void u8(const std::uint8_t value) { data_.push_back(value); }

        void u16(const std::uint16_t value)
        {
            data_.push_back(static_cast<std::uint8_t>(value));
            data_.push_back(static_cast<std::uint8_t>(value >> 8));
        }

        void u32(const std::uint32_t value)
        {
            for (std::uint32_t shift = 0; shift < 32; shift += 8)
                data_.push_back(static_cast<std::uint8_t>(value >> shift));
        }

        void u64(const std::uint64_t value)
        {
            for (std::uint32_t shift = 0; shift < 64; shift += 8)
                data_.push_back(static_cast<std::uint8_t>(value >> shift));
        }

        void text(const std::string &value)
        {
            data_.insert(data_.end(), value.begin(), value.end());
        }

        [[nodiscard]] std::vector<std::uint8_t> take() { return std::move(data_); }

    private:
        std::vector<std::uint8_t> data_;
    };

    class Reader
    {
    public:
        explicit Reader(const std::span<const std::uint8_t> data) : data_(data) {}

        bool u8(std::uint8_t &value)
        {
            if (offset_ == data_.size())
                return false;
            value = data_[offset_++];
            return true;
        }

        bool u16(std::uint16_t &value)
        {
            if (data_.size() - offset_ < 2)
                return false;
            value = static_cast<std::uint16_t>(data_[offset_]) |
                static_cast<std::uint16_t>(data_[offset_ + 1] << 8);
            offset_ += 2;
            return true;
        }

        bool u32(std::uint32_t &value)
        {
            if (data_.size() - offset_ < 4)
                return false;
            value = 0;
            for (std::uint32_t shift = 0; shift < 32; shift += 8)
                value |= static_cast<std::uint32_t>(data_[offset_++]) << shift;
            return true;
        }

        bool u64(std::uint64_t &value)
        {
            if (data_.size() - offset_ < 8)
                return false;
            value = 0;
            for (std::uint32_t shift = 0; shift < 64; shift += 8)
                value |= static_cast<std::uint64_t>(data_[offset_++]) << shift;
            return true;
        }

        bool text(const std::size_t size, std::string &value)
        {
            if (size > data_.size() - offset_)
                return false;
            value.assign(
                reinterpret_cast<const char *>(data_.data() + offset_), size);
            offset_ += size;
            return true;
        }

        [[nodiscard]] bool empty() const { return offset_ == data_.size(); }

    private:
        std::span<const std::uint8_t> data_;
        std::size_t offset_{};
    };

    bool validItemId(const std::uint32_t itemId)
    {
        return itemId <= (std::numeric_limits<std::uint16_t>::max)();
    }

    bool validUsername(const std::string &username)
    {
        return !username.empty() &&
            username.size() <= OlMod::DedicatedSession::MaximumUsernameSize &&
            std::ranges::all_of(username, [](const unsigned char value) {
                return value >= 0x20 && value <= 0x7E;
            });
    }

    bool validName(const std::string &value, const std::size_t maximumSize)
    {
        return !value.empty() && value.size() <= maximumSize &&
            std::ranges::all_of(value, [](const unsigned char character) {
                return character == '_' || character >= '0' && character <= '9' ||
                    character >= 'A' && character <= 'Z' ||
                    character >= 'a' && character <= 'z';
            });
    }

    void writeBookingBody(
        Writer &writer,
        const OlMod::DedicatedSession::BookingSelection &selection)
    {
        writer.u32(selection.playlistId);
        writer.u32(selection.rotationIndex);
        writer.u16(static_cast<std::uint16_t>(selection.mapName.size()));
        writer.u16(static_cast<std::uint16_t>(selection.gameType.size()));
        writer.text(selection.mapName);
        writer.text(selection.gameType);
    }

    bool readBookingBody(
        Reader &reader,
        OlMod::DedicatedSession::BookingSelection &selection)
    {
        std::uint16_t mapNameSize{};
        std::uint16_t gameTypeSize{};
        return reader.u32(selection.playlistId) &&
            reader.u32(selection.rotationIndex) &&
            reader.u16(mapNameSize) && reader.u16(gameTypeSize) &&
            mapNameSize <= OlMod::DedicatedSession::MaximumMapNameSize &&
            gameTypeSize <= OlMod::DedicatedSession::MaximumGameTypeSize &&
            reader.text(mapNameSize, selection.mapName) &&
            reader.text(gameTypeSize, selection.gameType);
    }

    void writeMatchRulesBody(
        Writer &writer,
        const OlMod::DedicatedSession::MatchRules &rules)
    {
        writer.u32(rules.playlistVersion);
        writer.u32(rules.scoreLimit);
        writer.u32(rules.timeLimitMinutes);
        writer.u32(rules.roundSwitch);
        writer.u32(rules.roundLimit);
        writer.u32(rules.winLimit);
    }

    bool readMatchRulesBody(
        Reader &reader,
        OlMod::DedicatedSession::MatchRules &rules)
    {
        return reader.u32(rules.playlistVersion) &&
            reader.u32(rules.scoreLimit) &&
            reader.u32(rules.timeLimitMinutes) &&
            reader.u32(rules.roundSwitch) &&
            reader.u32(rules.roundLimit) &&
            reader.u32(rules.winLimit);
    }

    void writeHeader(Writer &writer, const std::uint16_t kind)
    {
        writer.u32(PayloadMagic);
        writer.u16(OlMod::DedicatedSession::SchemaVersion);
        writer.u16(kind);
    }

    bool readHeader(Reader &reader, const std::uint16_t expectedKind,
        std::uint16_t &version)
    {
        std::uint32_t magic{};
        std::uint16_t kind{};
        return reader.u32(magic) && reader.u16(version) && reader.u16(kind) &&
            magic == PayloadMagic &&
            (version >= 5 && version <= OlMod::DedicatedSession::SchemaVersion) &&
            kind == expectedKind;
    }

    void writeLoadoutBody(
        Writer &writer,
        const OlMod::DedicatedSession::LoadoutRequest &request)
    {
        writer.u32(request.characterIndex);
        writer.u8(request.classMask);
        writer.u8(0);
        writer.u16(0);
        for (const auto itemId : request.characterItemIds)
            writer.u32(itemId);
        for (const auto &loadoutClass : request.classes)
        {
            for (const auto &weapon : loadoutClass.weapons)
            {
                writer.u32(weapon.itemId);
                for (const auto attachmentItemId : weapon.attachmentItemIds)
                    writer.u32(attachmentItemId);
            }
            for (const auto perkItemId : loadoutClass.perkItemIds)
                writer.u32(perkItemId);
            for (const auto itemId : loadoutClass.equipment.itemIds)
                writer.u32(itemId);
            writer.u8(loadoutClass.equipment.doubleAmmoMask);
            writer.u8(0);
            writer.u16(0);
        }
        for (const auto itemId : request.rewardItemIds)
            writer.u32(itemId);
    }

    bool readLoadoutBody(
        Reader &reader,
        OlMod::DedicatedSession::LoadoutRequest &request,
        const std::uint16_t version)
    {
        std::uint8_t reserved8{};
        std::uint16_t reserved16{};
        if (!reader.u32(request.characterIndex) ||
            !reader.u8(request.classMask) ||
            !reader.u8(reserved8) ||
            !reader.u16(reserved16) || reserved8 || reserved16)
        {
            return false;
        }
        for (auto &itemId : request.characterItemIds)
        {
            if (!reader.u32(itemId))
                return false;
        }
        for (auto &loadoutClass : request.classes)
        {
            for (auto &weapon : loadoutClass.weapons)
            {
                if (!reader.u32(weapon.itemId))
                    return false;
                for (auto &attachmentItemId : weapon.attachmentItemIds)
                {
                    if (!reader.u32(attachmentItemId))
                        return false;
                }
            }
            if (version >= 6)
            {
                for (auto &perkItemId : loadoutClass.perkItemIds)
                {
                    if (!reader.u32(perkItemId))
                        return false;
                }
            }
            if (version >= 7)
            {
                for (auto &itemId : loadoutClass.equipment.itemIds)
                    if (!reader.u32(itemId))
                        return false;
                if (!reader.u8(loadoutClass.equipment.doubleAmmoMask) ||
                    !reader.u8(reserved8) || !reader.u16(reserved16) ||
                    reserved8 || reserved16)
                    return false;
            }
        }
        if (version >= 8)
            for (auto &itemId : request.rewardItemIds)
                if (!reader.u32(itemId))
                    return false;
        return true;
    }
}

namespace OlMod::DedicatedSession
{
    bool valid(const LoadoutRequest &request)
    {
        if (request.characterIndex >= CharacterItemCount ||
            request.classMask & ~((1u << LoadoutClassCount) - 1u) ||
            !request.characterItemIds.front())
        {
            return false;
        }
        if (!std::ranges::all_of(request.characterItemIds, validItemId))
            return false;
        if (!std::ranges::all_of(request.rewardItemIds, validItemId))
            return false;

        for (std::size_t classIndex = 0; classIndex < request.classes.size(); ++classIndex)
        {
            const auto present = (request.classMask & (1u << classIndex)) != 0;
            const auto &equipment = request.classes[classIndex].equipment;
            if (equipment.doubleAmmoMask > 3 ||
                !std::ranges::all_of(equipment.itemIds, validItemId) ||
                (!present && (equipment.doubleAmmoMask ||
                    std::ranges::any_of(equipment.itemIds,
                        [](const auto itemId) { return itemId != 0; }))))
                return false;
            const auto &perks = request.classes[classIndex].perkItemIds;
            if (!std::ranges::all_of(perks, validItemId) ||
                (!present && std::ranges::any_of(perks,
                    [](const auto itemId) { return itemId != 0; })))
                return false;
            for (const auto &weapon : request.classes[classIndex].weapons)
            {
                if (present != (weapon.itemId != 0) || !validItemId(weapon.itemId) ||
                    !std::ranges::all_of(weapon.attachmentItemIds, validItemId))
                {
                    return false;
                }
                if (!present && std::ranges::any_of(
                        weapon.attachmentItemIds, [](const auto itemId) { return itemId != 0; }))
                {
                    return false;
                }
            }
        }
        return request.classMask != 0;
    }

    bool valid(const BookingSelection &selection)
    {
        return selection.playlistId <= (std::numeric_limits<std::uint8_t>::max)() &&
            selection.rotationIndex <= static_cast<std::uint32_t>(
                (std::numeric_limits<std::int8_t>::max)()) &&
            validName(selection.mapName, MaximumMapNameSize) &&
            validName(selection.gameType, MaximumGameTypeSize);
    }

    bool valid(const ClientSessionCapture &capture)
    {
        // A CAPTURE WITH NO BOOKING IS STILL A CAPTURE, and the two halves are
        // gathered from completely different places. The loadout comes out of the
        // stored profile and is there whenever the client is logged in; the booking
        // selection only exists while the client is HOLDING a lobby booking, which
        // it is not at the menu and may drop again once a match starts.
        //
        // Requiring both meant a client sitting in the menu with five perfectly
        // readable classes reported nothing at all -- measured as
        //     client capture empty: NO_BOOKING_SELECTION characterIndex=4 classMask=31
        // where classMask 31 is all five classes read successfully.
        //
        // An entirely empty booking means "this client is not holding one". Anything
        // else is validated exactly as before, and valid(BookingSelection) itself is
        // untouched so SessionStart still requires a real map and gametype.
        const auto &booking = capture.booking;
        const auto noBooking = booking.mapName.empty() && booking.gameType.empty() &&
            !booking.playlistId && !booking.rotationIndex;
        return (noBooking || valid(booking)) && valid(capture.loadout);
    }

    bool valid(const MatchRules &rules, const std::string_view rawGameType)
    {
        // Callers on the backend side hold the token the client booked; callers on
        // the game-server side hold the engine gametype. Normalise rather than
        // pick one, because the failure of getting it wrong is silent - an
        // unrecognised name falls through to the accept-anything tail below.
        const auto gameType = OlMod::CodolPlaylist::bookingToken(rawGameType);
        constexpr std::uint32_t MaximumScoreLimit = 1'000'000;
        constexpr std::uint32_t MaximumTimeLimitMinutes = 24 * 60;
        constexpr std::uint32_t MaximumRoundLimit = 1'000;
        if (rules.scoreLimit > MaximumScoreLimit ||
            rules.timeLimitMinutes > MaximumTimeLimitMinutes ||
            rules.roundSwitch > MaximumRoundLimit ||
            rules.roundLimit > MaximumRoundLimit ||
            rules.winLimit > MaximumRoundLimit)
        {
            return false;
        }
        if (gameType == "cha")
        {
            return rules.playlistVersion && rules.scoreLimit &&
                rules.timeLimitMinutes && !rules.roundSwitch &&
                !rules.roundLimit && !rules.winLimit;
        }
        if (gameType == "sd")
        {
            return rules.playlistVersion && rules.roundSwitch &&
                rules.roundLimit && rules.winLimit &&
                rules.roundSwitch <= rules.roundLimit &&
                rules.winLimit <= rules.roundLimit &&
                !rules.scoreLimit;
        }
        // Free-for-all books as ffa and runs as the gametype dm. It is scored and
        // timed like cha but has no rounds; without this it would fall through to
        // the accept-anything tail below and a zero score limit - a match that can
        // never end - would look valid.
        if (gameType == "ffa")
        {
            return rules.playlistVersion && rules.scoreLimit &&
                rules.timeLimitMinutes && !rules.roundSwitch &&
                !rules.roundLimit && !rules.winLimit;
        }
        return true;
    }

    bool valid(const SessionStart &request)
    {
        if (request.members.empty() ||
            request.members.size() > MaximumSessionMembers ||
            request.bookingCommand.empty() ||
            request.bookingCommand.size() > MaximumBookingCommandSize ||
            request.bookingCommand.find('\0') != std::string::npos ||
            !valid(request.booking) ||
            !valid(request.matchRules, request.booking.gameType))
        {
            return false;
        }
        std::vector<std::uint64_t> userIds;
        userIds.reserve(request.members.size());
        for (const auto &member : request.members)
        {
            if (!member.userId || !validUsername(member.username) ||
                !valid(member.loadout) ||
                std::ranges::find(userIds, member.userId) != userIds.end())
            {
                return false;
            }
            userIds.push_back(member.userId);
        }
        return true;
    }

    std::vector<std::uint8_t> encode(const LoadoutRequest &request)
    {
        if (!valid(request))
            return {};
        Writer writer;
        writeHeader(writer, LoadoutPayloadKind);
        writeLoadoutBody(writer, request);
        return writer.take();
    }

    std::vector<std::uint8_t> encode(const SessionStart &request)
    {
        if (!valid(request))
            return {};
        Writer writer;
        writeHeader(writer, SessionStartPayloadKind);
        writer.u16(static_cast<std::uint16_t>(request.members.size()));
        writer.u16(static_cast<std::uint16_t>(request.bookingCommand.size()));
        writeBookingBody(writer, request.booking);
        writeMatchRulesBody(writer, request.matchRules);
        writer.text(request.bookingCommand);
        for (const auto &member : request.members)
        {
            writer.u64(member.userId);
            writer.u16(static_cast<std::uint16_t>(member.username.size()));
            writer.u16(0);
            writeLoadoutBody(writer, member.loadout);
            writer.text(member.username);
        }
        return writer.take();
    }

    std::vector<std::uint8_t> encode(const ClientSessionCapture &capture)
    {
        if (!valid(capture))
            return {};
        Writer writer;
        writeHeader(writer, ClientSessionCapturePayloadKind);
        writeBookingBody(writer, capture.booking);
        writeLoadoutBody(writer, capture.loadout);
        return writer.take();
    }

    std::optional<LoadoutRequest> decodeLoadout(
        const std::span<const std::uint8_t> payload)
    {
        Reader reader(payload);
        LoadoutRequest request;
        std::uint16_t version{};
        if (!readHeader(reader, LoadoutPayloadKind, version) ||
            !readLoadoutBody(reader, request, version) || !reader.empty() || !valid(request))
        {
            return std::nullopt;
        }
        return request;
    }

    std::optional<SessionStart> decodeSessionStart(
        const std::span<const std::uint8_t> payload)
    {
        Reader reader(payload);
        SessionStart request;
        std::uint16_t version{};
        std::uint16_t memberCount{};
        std::uint16_t bookingCommandSize{};
        if (!readHeader(reader, SessionStartPayloadKind, version) ||
            !reader.u16(memberCount) ||
            !reader.u16(bookingCommandSize) ||
            !memberCount || memberCount > MaximumSessionMembers ||
            bookingCommandSize > MaximumBookingCommandSize ||
            !readBookingBody(reader, request.booking) ||
            !readMatchRulesBody(reader, request.matchRules) ||
            !reader.text(bookingCommandSize, request.bookingCommand))
        {
            return std::nullopt;
        }
        request.members.reserve(memberCount);
        for (std::uint16_t index = 0; index < memberCount; ++index)
        {
            SessionMember member;
            std::uint16_t usernameSize{};
            std::uint16_t reserved{};
            if (!reader.u64(member.userId) ||
                !reader.u16(usernameSize) || !reader.u16(reserved) || reserved ||
                usernameSize > MaximumUsernameSize ||
                !readLoadoutBody(reader, member.loadout, version) ||
                !reader.text(usernameSize, member.username))
            {
                return std::nullopt;
            }
            request.members.push_back(std::move(member));
        }
        if (!reader.empty() || !valid(request))
            return std::nullopt;
        return request;
    }

    std::optional<ClientSessionCapture> decodeClientSessionCapture(
        const std::span<const std::uint8_t> payload)
    {
        Reader reader(payload);
        ClientSessionCapture capture;
        std::uint16_t version{};
        if (!readHeader(reader, ClientSessionCapturePayloadKind, version) ||
            !readBookingBody(reader, capture.booking) ||
            !readLoadoutBody(reader, capture.loadout, version) ||
            !reader.empty() || !valid(capture))
        {
            return std::nullopt;
        }
        return capture;
    }
}
