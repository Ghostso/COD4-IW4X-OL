#pragma once

#include "sv_snapshot_mp.hpp"

#include <cstdint>
#include <optional>
#include <span>
#include <unordered_map>
#include <vector>

namespace CodolGameServer
{
    inline constexpr std::uint32_t UserCmdButtonActivate = 0x00000008;

    enum class SvUseTeamRelation : std::uint8_t
    {
        Any,
        Friendly,
        Enemy,
    };

    struct SvUseObjectDefinition
    {
        std::uint32_t objectId{};
        SvTeam ownerTeam{ SvTeam::None };
        SvUseTeamRelation allowedRelation{ SvUseTeamRelation::Any };
        std::uint32_t useDurationMilliseconds{};
        bool requiresKeyObject{};

        bool operator==(const SvUseObjectDefinition &) const = default;
    };

    struct SvUseObjectCandidate
    {
        std::uint32_t objectId{};
        bool insideTrigger{};
        bool hasKeyObject{};

        bool operator==(const SvUseObjectCandidate &) const = default;
    };

    struct SvUseObjectClientCommand
    {
        std::uint32_t clientNum{};
        SvTeam team{ SvTeam::None };
        std::uint32_t commandTime{};
        std::uint32_t buttons{};
        bool playing{};
        bool alive{};
        std::span<const SvUseObjectCandidate> candidates;
    };

    enum class SvUseObjectEventType : std::uint8_t
    {
        Begin,
        Cancel,
        Complete,
    };

    struct SvUseObjectEvent
    {
        SvUseObjectEventType type{ SvUseObjectEventType::Begin };
        std::uint32_t objectId{};
        std::uint32_t clientNum{};
        std::uint32_t commandTime{};
        std::uint32_t elapsedMilliseconds{};

        bool operator==(const SvUseObjectEvent &) const = default;
    };

    struct SvUseObjectProgress
    {
        std::uint32_t objectId{};
        std::uint32_t clientNum{};
        std::uint32_t startCommandTime{};
        std::uint32_t lastCommandTime{};

        bool operator==(const SvUseObjectProgress &) const = default;
    };

    class SvUseObjectSystem
    {
    public:
        void reset();
        [[nodiscard]] bool configure(
            std::span<const SvUseObjectDefinition> definitions);
        [[nodiscard]] std::vector<SvUseObjectEvent> processCommittedCommand(
            const SvUseObjectClientCommand &command);
        [[nodiscard]] std::optional<SvUseObjectEvent> cancelClient(
            std::uint32_t clientNum,
            std::uint32_t commandTime);
        [[nodiscard]] std::optional<SvUseObjectProgress> progressForClient(
            std::uint32_t clientNum) const;
        [[nodiscard]] std::optional<std::uint32_t> claimantForObject(
            std::uint32_t objectId) const;

    private:
        [[nodiscard]] const SvUseObjectDefinition *eligibleDefinition(
            const SvUseObjectClientCommand &command) const;
        [[nodiscard]] std::optional<SvUseObjectEvent> cancelProgress(
            std::uint32_t clientNum,
            std::uint32_t commandTime);

        std::vector<SvUseObjectDefinition> definitions_;
        std::unordered_map<std::uint32_t, SvUseObjectProgress> clientProgress_;
        std::unordered_map<std::uint32_t, std::uint32_t> objectClaimants_;
        std::unordered_map<std::uint32_t, std::uint32_t> lastCommandTimes_;
    };
}
