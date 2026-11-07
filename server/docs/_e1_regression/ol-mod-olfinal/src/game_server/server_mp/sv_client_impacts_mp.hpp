#pragma once

#include "sv_collision_mp.hpp"
#include "sv_entity_mp.hpp"

#include <array>
#include <cstdint>
#include <optional>
#include <span>

namespace CodolGameServer
{
    // OLMOD(client-impacts-source-plan): typed candidate data, not a recovered
    // CODOL pmove_t, gentity_s, script VM, or entityHandler_t layout.
    struct SvClientImpactBatch
    {
        std::uint32_t sourceEntityNum{};
        std::uint32_t inputTouchCount{};
        std::uint32_t impactCount{};
        std::array<std::uint32_t, 32> targetEntityNums{};
        std::uint32_t unresolvedEntityCount{};

        bool operator==(const SvClientImpactBatch &) const = default;
    };

    // CODREF(client_impacts): BO1/Ghosts call target then source, while BO2
    // calls source then target. CODOL retains the 32-touch pmove input layout
    // but not the server callback owner, so the order remains explicit.
    // TODO(CODOL): Remove this policy choice once CODOL server callback-order
    // evidence or an equivalent authoritative script contract is recovered.
    enum class SvClientImpactCallbackOrder : std::uint8_t
    {
        TargetThenSource,
        SourceThenTarget,
    };

    // OLMOD(client-impacts-callback-plan): normalized post-commit handler call;
    // this is not CODOL entityHandler_t, gentity_s, or script VM storage.
    struct SvClientImpactCallback
    {
        std::uint32_t receiverEntityNum{};
        std::uint32_t otherEntityNum{};
        std::uint32_t contact{};

        bool operator==(const SvClientImpactCallback &) const = default;
    };

    // OLMOD(client-impacts-callback-plan): fixed-capacity transactional output
    // for two callbacks per retained touch. Concrete handler bodies are owned
    // by the post-commit dispatcher, not by this source schema.
    struct SvClientImpactCallbackBatch
    {
        std::uint32_t callbackCount{};
        std::array<SvClientImpactCallback, 64> callbacks{};

        bool operator==(const SvClientImpactCallbackBatch &) const = default;
    };

    // OLMOD(client-impacts-script-plan): typed bilateral touch notification;
    // it deliberately does not claim native script value/entity-ref layout.
    struct SvClientImpactScriptNotification
    {
        std::uint32_t receiverEntityNum{};
        std::uint32_t otherEntityNum{};

        bool operator==(const SvClientImpactScriptNotification &) const = default;
    };

    // OLMOD(client-impacts-script-plan): fixed-capacity post-commit script
    // output. Production script lifetime and notify semantics remain external.
    struct SvClientImpactScriptNotificationBatch
    {
        std::uint32_t notificationCount{};
        std::array<SvClientImpactScriptNotification, 64> notifications{};

        bool operator==(
            const SvClientImpactScriptNotificationBatch &) const = default;
    };

    // OLMOD(client-impacts-source-plan): builds the generation-safe source
    // candidate from CODOL's bounded native touch list. Script notifications,
    // entity touch callbacks, and glass effects remain separate side effects.
    [[nodiscard]] std::optional<SvClientImpactBatch>
        SV_BuildClientImpactBatch(
            std::uint32_t sourceEntityNum,
            std::span<const std::uint32_t> touchEntityNums,
            std::span<const SvCollisionEntity> linkedEntities);

    [[nodiscard]] std::optional<SvClientImpactCallbackBatch>
        SV_BuildClientImpactCallbackBatch(
            const SvClientImpactBatch &impactBatch,
            SvClientImpactCallbackOrder callbackOrder);

    [[nodiscard]] std::optional<SvClientImpactScriptNotificationBatch>
        SV_BuildClientImpactScriptNotificationBatch(
            const SvClientImpactBatch &impactBatch);
}
