#pragma once

#include <cstddef>
#include <cstdint>
#include <functional>
#include <optional>
#include <span>
#include <string_view>
#include <vector>

#include "sv_damage_mp.hpp"

namespace CodolGameServer
{
    struct SvDestructibleStageDefinition
    {
        // CODREF(g_damage): IW4 _destructible.gsc defines ordered per-part
        // health states and carries overflow damage into the next state.
        std::int32_t health{};
        std::string_view replacementModel;

        bool operator==(const SvDestructibleStageDefinition &) const = default;
    };

    struct SvDestructibleDefinition
    {
        // CODDIFF(g_damage): only exact CODOL MapEnt type names with an IW4
        // definition are admitted; this is script data, not native layout.
        std::string_view type;
        std::span<const SvDestructibleStageDefinition> stages;
        std::string_view destroyedModel;

        bool operator==(const SvDestructibleDefinition &) const = default;
    };

    struct SvDestructibleState
    {
        // OLMOD(destructible-stage-owner): explicit state avoids inferring an
        // ambiguous stage from repeated health values.
        std::size_t stageIndex{};
        std::int32_t health{};
        bool destroyed{};

        bool operator==(const SvDestructibleState &) const = default;
    };

    struct SvDestructibleDamageResult
    {
        SvDestructibleState state;
        std::vector<std::size_t> enteredStages;
        bool enteredDestroyedState{};

        bool operator==(const SvDestructibleDamageResult &) const = default;
    };

    struct SvResolvedDestructiblePresentation
    {
        // OLMOD(destructible-presentation-plan): asset indexes and event plans
        // are resolved before owner registration and committed transactionally.
        std::vector<std::optional<std::uint16_t>> stageModelIndexes;
        std::optional<std::uint16_t> destroyedModelIndex;
        // Empty means no recovered presentation side effects. Otherwise the
        // outer vector is aligned one-to-one with definition.stages.
        std::vector<std::vector<SvEntityDamagePresentationEvent>> stageEvents;
        std::vector<SvEntityDamagePresentationEvent> destroyedEvents;

        bool operator==(const SvResolvedDestructiblePresentation &) const = default;
    };

    [[nodiscard]] bool SV_IsDestructibleDefinitionValid(
        const SvDestructibleDefinition &definition);
    [[nodiscard]] std::optional<SvDestructibleState>
    SV_InitializeDestructible(const SvDestructibleDefinition &definition);
    [[nodiscard]] std::optional<SvDestructibleDamageResult>
    SV_ApplyDestructibleDamage(
        const SvDestructibleDefinition &definition,
        const SvDestructibleState &state,
        std::int32_t damage);
    [[nodiscard]] std::optional<SvEntityDamageState>
    SV_InitializeDestructibleDamageState(
        const SvDestructibleDefinition &definition);
    [[nodiscard]] bool SV_IsResolvedDestructiblePresentationValid(
        const SvDestructibleDefinition &definition,
        const SvResolvedDestructiblePresentation &presentation);
    using SvDestructibleModelResolver = std::function<
        std::optional<std::uint16_t>(std::string_view)>;
    [[nodiscard]] std::optional<SvResolvedDestructiblePresentation>
    SV_ResolveDestructiblePresentation(
        const SvDestructibleDefinition &definition,
        const SvDestructibleModelResolver &resolveModel);
    [[nodiscard]] std::optional<SvEntityDamageMutation>
    SV_ApplyDestructibleEntityDamage(
        const SvDestructibleDefinition &definition,
        const SvResolvedDestructiblePresentation &presentation,
        const SvEntityDamagePayload &payload,
        const SvEntityDamageState &state,
        std::uint16_t currentModelIndex);

    // CODDIFF(g_damage): conservative IW4-derived subset. Only exact CODOL MapEnt type names
    // whose state-health sequence is present in the original IW4 scripts are
    // exposed here. CODOL-specific variants remain unsupported until their
    // own definitions are recovered.
    // TODO(CODOL): do not add tropical/ratnest02/tubetvsound/ceiling-fan
    // variants until their title-local state tables and presentation are found.
    [[nodiscard]] const SvDestructibleDefinition *
    SV_FindIw4DestructibleDefinition(std::string_view type);
}
