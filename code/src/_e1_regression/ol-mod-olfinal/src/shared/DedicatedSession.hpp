#pragma once

#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace OlMod::DedicatedSession
{
    // Kept in lockstep with configure-session.py and ClientSessionCapture.
    // Version 8 adds the current perk/equipment/reward loadout fields; accepting
    // only version 5 rejects every live booking before world initialization.
    constexpr std::uint16_t SchemaVersion = 8;
    constexpr std::size_t RewardSlotCount = 3;
    constexpr std::size_t CharacterItemCount = 12;
    constexpr std::size_t LoadoutClassCount = 5;
    constexpr std::size_t WeaponsPerClass = 2;
    constexpr std::size_t AttachmentCount = 6;
    constexpr std::size_t PerkSlotCount = 6;
    constexpr std::size_t MaximumUsernameSize = 16;
    constexpr std::size_t MaximumBookingCommandSize = 1024;
    constexpr std::size_t MaximumMapNameSize = 64;
    constexpr std::size_t MaximumGameTypeSize = 32;
    constexpr std::size_t MaximumSessionMembers = 18;

    struct WeaponRequest
    {
        std::uint32_t itemId{};
        std::array<std::uint32_t, AttachmentCount> attachmentItemIds{};

        bool operator==(const WeaponRequest &) const = default;
    };

    // Source-owned transport of the named lethal/tactical profile fields.
    // Raw item integers use catalog ID + 1, with 0/1 empty. Double-ammo flags
    // are booleans from the profile, not a guessed native ammo count.
    struct EquipmentRequest
    {
        std::array<std::uint32_t, 2> itemIds{}; // lethal, tactical
        std::uint8_t doubleAmmoMask{}; // bit 0 lethal, bit 1 tactical

        bool operator==(const EquipmentRequest &) const = default;
    };

    struct ClassRequest
    {
        std::array<WeaponRequest, WeaponsPerClass> weapons{};
        // Decoded profile integers: catalog ID + 1; 0 and 1 are empty.
        std::array<std::uint32_t, PerkSlotCount> perkItemIds{};
        EquipmentRequest equipment;

        bool operator==(const ClassRequest &) const = default;
    };

    struct LoadoutRequest
    {
        std::uint32_t characterIndex{};
        std::uint8_t classMask{};
        std::array<std::uint32_t, CharacterItemCount> characterItemIds{};
        std::array<ClassRequest, LoadoutClassCount> classes{};
        // Raw profile item IDs, shared across weapon classes (native class 0).
        std::array<std::uint32_t, RewardSlotCount> rewardItemIds{};

        bool operator==(const LoadoutRequest &) const = default;
    };

    struct BookingSelection
    {
        std::uint32_t playlistId{};
        std::uint32_t rotationIndex{};
        std::string mapName;
        std::string gameType;

        bool operator==(const BookingSelection &) const = default;
    };

    struct MatchRules
    {
        std::uint32_t playlistVersion{};
        std::uint32_t scoreLimit{};
        std::uint32_t timeLimitMinutes{};
        std::uint32_t roundSwitch{};
        std::uint32_t roundLimit{};
        std::uint32_t winLimit{};

        bool operator==(const MatchRules &) const = default;
    };

    struct ClientSessionCapture
    {
        BookingSelection booking;
        LoadoutRequest loadout;

        bool operator==(const ClientSessionCapture &) const = default;
    };

    struct SessionMember
    {
        std::uint64_t userId{};
        std::string username;
        LoadoutRequest loadout;

        bool operator==(const SessionMember &) const = default;
    };

    struct SessionStart
    {
        std::string bookingCommand;
        BookingSelection booking;
        MatchRules matchRules;
        std::vector<SessionMember> members;

        bool operator==(const SessionStart &) const = default;
    };

    [[nodiscard]] bool valid(const LoadoutRequest &request);
    [[nodiscard]] bool valid(const BookingSelection &selection);
    [[nodiscard]] bool valid(const MatchRules &rules, std::string_view gameType);
    [[nodiscard]] bool valid(const ClientSessionCapture &capture);
    [[nodiscard]] bool valid(const SessionStart &request);
    [[nodiscard]] std::vector<std::uint8_t> encode(const LoadoutRequest &request);
    [[nodiscard]] std::vector<std::uint8_t> encode(
        const ClientSessionCapture &capture);
    [[nodiscard]] std::vector<std::uint8_t> encode(const SessionStart &request);
    [[nodiscard]] std::optional<LoadoutRequest> decodeLoadout(
        std::span<const std::uint8_t> payload);
    [[nodiscard]] std::optional<ClientSessionCapture> decodeClientSessionCapture(
        std::span<const std::uint8_t> payload);
    [[nodiscard]] std::optional<SessionStart> decodeSessionStart(
        std::span<const std::uint8_t> payload);
}
