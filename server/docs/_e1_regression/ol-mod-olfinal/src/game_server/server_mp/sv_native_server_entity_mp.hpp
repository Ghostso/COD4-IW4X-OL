#pragma once

#include "sv_collision_mp.hpp"
#include "sv_native_entitystate_mp.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>

namespace CodolGameServer
{
    struct SvCharacterCustomization;

    enum class SvNativeEntityMirrorPhase : std::uint8_t
    {
        Collision,
        IncrementalCollision,
        Presentation,
    };

    struct SvNativeServerEntity
    {
        static constexpr std::size_t Size = 0x2C8;
        static constexpr std::uint32_t Capacity = 2046;

        // OLMOD(native-gentity-byte-image): this is either a build template or
        // an opaque backup of one native slot. Copies intentionally preserve
        // raw bytes; address-bound entityState origins are relocated only when
        // publishing from SvNativeEntityState to their destination slot.
        alignas(std::uint32_t) std::array<std::byte, Size> bytes{};

        bool operator==(const SvNativeServerEntity &) const = default;
    };

    static_assert(sizeof(SvNativeServerEntity) == SvNativeServerEntity::Size);

    struct SvNativeEntityStateSource
    {
        std::uint32_t entityNum{};
        const SvNativeEntityState *state{};
        const SvCharacterCustomization *customization{};
        // CODREF(client_spawn): which LIFE this presentation belongs to.
        // characterInfo's animation lerp frames are initialised once per
        // character selection, and a respawn changes neither the selection nor
        // the model context, so without this the death pose survives into the
        // next life and the server skeleton stays collapsed at roughly waist
        // height - hittable low, never in the head, on every life after the
        // first. playerState +0x1F8 spawnGeneration is CODOL's own per-life
        // counter and SV_ClientSpawn already increments it.
        std::uint8_t spawnGeneration{};

        bool operator==(const SvNativeEntityStateSource &) const = default;
    };

    [[nodiscard]] std::optional<SvNativeServerEntity>
        SV_BuildNativeServerEntity(
            const SvCollisionEntity &entity,
            const SvNativeEntityState *entityState = nullptr);
    void SV_CopyNativeServerEntityToSlot(
        SvNativeServerEntity &destination,
        const SvNativeServerEntity &source,
        const SvNativeEntityState *entityState = nullptr);
    void SV_CopyNativeEntityStateToServerEntity(
        SvNativeServerEntity &destination,
        const SvNativeEntityState &source);
    [[nodiscard]] bool SV_ValidateNativeServerEntityLinkResult(
        const SvNativeServerEntity &entity,
        const SvCollisionEntity &source);
    [[nodiscard]] bool SV_IsNativeServerEntityAvailableBaseline(
        const SvNativeServerEntity &entity);
    [[nodiscard]] bool SV_IsNativeServerEntityLinked(
        const SvNativeServerEntity &entity);
    void SV_ClearNativeServerEntityLinkedFlag(SvNativeServerEntity &entity);
}
