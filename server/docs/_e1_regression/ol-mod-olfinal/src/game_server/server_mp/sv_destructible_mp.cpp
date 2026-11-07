#include "sv_destructible_mp.hpp"

#include <algorithm>
#include <array>
#include <ranges>

namespace CodolGameServer
{
    namespace
    {
        // CODREF(g_damage): health sequences and replacement model names come
        // from IW4's original _destructible.gsc. CODDIFF(g_damage): exposure is
        // restricted to exact type names observed in CODOL crash MapEnts.
        using Stage = SvDestructibleStageDefinition;

        constexpr std::array FlatscreenStages{
            Stage{ 1, {} },
            Stage{ 200, "ma_flatscreen_tv_wallmount_broken_01" },
        };
        constexpr std::array TransformerStages{
            Stage{ 75, {} }, Stage{ 75, {} }, Stage{ 150, {} },
            Stage{ 250, {} }, Stage{ 400, {} },
        };
        constexpr std::array FluorescentLightStages{ Stage{ 150, {} } };
        constexpr std::array SedanStages{
            Stage{ 250, {} }, Stage{ 200, {} }, Stage{ 100, {} },
            Stage{ 300, {} }, Stage{ 400, {} },
        };
        constexpr std::array PickupStages{
            Stage{ 300, {} }, Stage{ 200, {} }, Stage{ 100, {} },
            Stage{ 300, {} }, Stage{ 400, {} },
        };

        constexpr std::array Definitions{
            SvDestructibleDefinition{
                "toy_tv_flatscreen_wallmount_01", FlatscreenStages,
                {} },
            SvDestructibleDefinition{
                "toy_transformer_small01", TransformerStages,
                "utility_transformer_small01_dest" },
            SvDestructibleDefinition{
                "toy_light_ceiling_fluorescent_single",
                FluorescentLightStages, "me_lightfluohang_single_destroyed" },
            SvDestructibleDefinition{
                "vehicle_80s_sedan1_red", SedanStages,
                "vehicle_80s_sedan1_red_destroyed" },
            SvDestructibleDefinition{
                "vehicle_80s_sedan1_green", SedanStages,
                "vehicle_80s_sedan1_green_destroyed" },
            SvDestructibleDefinition{
                "vehicle_80s_sedan1_brn", SedanStages,
                "vehicle_80s_sedan1_brn_destroyed" },
            SvDestructibleDefinition{
                "vehicle_pickup", PickupStages, "vehicle_pickup_destroyed" },
        };
    }

    bool SV_IsDestructibleDefinitionValid(
        const SvDestructibleDefinition &definition)
    {
        // OLMOD(destructible-definition-admission): source script-data guard;
        // presentation assets are validated separately before activation.
        return !definition.type.empty() && !definition.stages.empty() &&
            std::ranges::all_of(definition.stages, [](const auto &stage) {
                return stage.health > 0;
            });
    }

    std::optional<SvDestructibleState> SV_InitializeDestructible(
        const SvDestructibleDefinition &definition)
    {
        if (!SV_IsDestructibleDefinitionValid(definition))
            return std::nullopt;
        return SvDestructibleState{
            .health = definition.stages.front().health,
        };
    }

    std::optional<SvDestructibleDamageResult> SV_ApplyDestructibleDamage(
        const SvDestructibleDefinition &definition,
        const SvDestructibleState &state,
        const std::int32_t damage)
    {
        // CODREF(g_damage): IW4 destructible_state carries overflow damage
        // through ordered states and runs every entered state action.
        if (!SV_IsDestructibleDefinitionValid(definition) || damage <= 0 ||
            state.destroyed || state.stageIndex >= definition.stages.size() ||
            state.health <= 0 ||
            state.health > definition.stages[state.stageIndex].health)
        {
            return std::nullopt;
        }

        auto result = SvDestructibleDamageResult{ .state = state };
        auto remainingDamage = static_cast<std::int64_t>(damage);
        while (remainingDamage >= result.state.health)
        {
            remainingDamage -= result.state.health;
            ++result.state.stageIndex;
            if (result.state.stageIndex == definition.stages.size())
            {
                result.state.health = 0;
                result.state.destroyed = true;
                result.enteredDestroyedState = true;
                return result;
            }
            result.state.health =
                definition.stages[result.state.stageIndex].health;
            result.enteredStages.push_back(result.state.stageIndex);
        }
        result.state.health -= static_cast<std::int32_t>(remainingDamage);
        return result;
    }

    std::optional<SvEntityDamageState> SV_InitializeDestructibleDamageState(
        const SvDestructibleDefinition &definition)
    {
        // CODDIFF(g_damage): adapts script-owned destructible state to ol-mod's
        // generation-safe generic damage owner; no CODOL gentity layout exists.
        const auto initial = SV_InitializeDestructible(definition);
        if (!initial)
            return std::nullopt;
        return SvEntityDamageState{
            .kind = SvEntityDamageKind::Destructible,
            .health = initial->health,
            .canTakeDamage = true,
            .stageIndex = static_cast<std::uint32_t>(initial->stageIndex),
        };
    }

    bool SV_IsResolvedDestructiblePresentationValid(
        const SvDestructibleDefinition &definition,
        const SvResolvedDestructiblePresentation &presentation)
    {
        // OLMOD(destructible-presentation-plan): fail closed if any declared
        // model is absent or event arrays lose their one-to-one stage mapping.
        if (!SV_IsDestructibleDefinitionValid(definition) ||
            presentation.stageModelIndexes.size() != definition.stages.size() ||
            (!presentation.stageEvents.empty() &&
                presentation.stageEvents.size() != definition.stages.size()))
        {
            return false;
        }
        for (std::size_t index{}; index < definition.stages.size(); ++index)
        {
            const auto hasName = !definition.stages[index].replacementModel.empty();
            const auto modelIndex = presentation.stageModelIndexes[index];
            if (hasName != modelIndex.has_value() ||
                (modelIndex && !*modelIndex))
            {
                return false;
            }
        }
        const auto hasDestroyedModel = !definition.destroyedModel.empty();
        return hasDestroyedModel ==
                presentation.destroyedModelIndex.has_value() &&
            (!presentation.destroyedModelIndex ||
                *presentation.destroyedModelIndex != 0);
    }

    std::optional<SvResolvedDestructiblePresentation>
        SV_ResolveDestructiblePresentation(
            const SvDestructibleDefinition &definition,
            const SvDestructibleModelResolver &resolveModel)
    {
        if (!SV_IsDestructibleDefinitionValid(definition) || !resolveModel)
            return std::nullopt;

        SvResolvedDestructiblePresentation presentation;
        presentation.stageModelIndexes.reserve(definition.stages.size());
        for (const auto &stage : definition.stages)
        {
            if (stage.replacementModel.empty())
            {
                presentation.stageModelIndexes.push_back(std::nullopt);
                continue;
            }
            const auto modelIndex = resolveModel(stage.replacementModel);
            if (!modelIndex || !*modelIndex)
                return std::nullopt;
            presentation.stageModelIndexes.push_back(*modelIndex);
        }
        if (!definition.destroyedModel.empty())
        {
            presentation.destroyedModelIndex =
                resolveModel(definition.destroyedModel);
            if (!presentation.destroyedModelIndex ||
                !*presentation.destroyedModelIndex)
            {
                return std::nullopt;
            }
        }
        if (!SV_IsResolvedDestructiblePresentationValid(
                definition, presentation))
        {
            return std::nullopt;
        }
        return presentation;
    }

    std::optional<SvEntityDamageMutation> SV_ApplyDestructibleEntityDamage(
        const SvDestructibleDefinition &definition,
        const SvResolvedDestructiblePresentation &presentation,
        const SvEntityDamagePayload &payload,
        const SvEntityDamageState &state,
        const std::uint16_t currentModelIndex)
    {
        // CODDIFF(g_damage): pure handler adapter used by the outer command
        // transaction. Model/event publication and native relink happen later.
        if (!SV_IsResolvedDestructiblePresentationValid(
                definition, presentation) ||
            state.kind != SvEntityDamageKind::Destructible ||
            !state.canTakeDamage || state.cannotDie || !currentModelIndex ||
            state.stageIndex >= definition.stages.size() ||
            payload.damage <= 0)
        {
            return std::nullopt;
        }
        const auto result = SV_ApplyDestructibleDamage(
            definition,
            SvDestructibleState{
                .stageIndex = state.stageIndex,
                .health = state.health,
            },
            payload.damage);
        if (!result)
            return std::nullopt;

        auto next = state;
        next.health = result->state.health;
        next.stageIndex = static_cast<std::uint32_t>(result->state.stageIndex);
        next.canTakeDamage = !result->state.destroyed;

        std::optional<std::uint16_t> modelIndex;
        if (result->enteredDestroyedState)
        {
            modelIndex = presentation.destroyedModelIndex;
        }
        else
        {
            for (const auto enteredStage : result->enteredStages)
            {
                if (presentation.stageModelIndexes[enteredStage])
                    modelIndex = presentation.stageModelIndexes[enteredStage];
            }
        }
        auto mutation = SvEntityDamageMutation{
            .state = next,
            .modelIndex = modelIndex,
        };
        if (!presentation.stageEvents.empty())
        {
            for (const auto enteredStage : result->enteredStages)
            {
                mutation.presentationEvents.insert(
                    mutation.presentationEvents.end(),
                    presentation.stageEvents[enteredStage].begin(),
                    presentation.stageEvents[enteredStage].end());
            }
        }
        if (result->enteredDestroyedState)
        {
            mutation.presentationEvents.insert(
                mutation.presentationEvents.end(),
                presentation.destroyedEvents.begin(),
                presentation.destroyedEvents.end());
        }
        // TODO(CODOL): stage collision, part/tag mutation, animation, explosion
        // radius damage and specialized vehicle behavior are not represented by
        // this model/event-only plan and must not be inferred from type names.
        return mutation;
    }

    const SvDestructibleDefinition *SV_FindIw4DestructibleDefinition(
        const std::string_view type)
    {
        const auto definition = std::ranges::find(
            Definitions, type, &SvDestructibleDefinition::type);
        return definition != Definitions.end() ? &*definition : nullptr;
    }
}
