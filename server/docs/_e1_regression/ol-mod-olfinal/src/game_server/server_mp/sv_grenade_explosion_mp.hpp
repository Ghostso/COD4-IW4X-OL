#pragma once

#include <array>
#include <cstdint>
#include <optional>

namespace CodolGameServer
{
    struct SvEntityState;

    // CODREF(out.exe CG_EntityEvent 536467..5365AC): event98 is the grenade
    // explosion consumer. Retail DM's twelve Semtex effects are ET_GENERAL,
    // flags16, scale1, eventSequence1, event[0]={98,5}; all other words zero
    // except number, origin, weapon and surfType. Foreign flags32 are wrong here.
    struct SvGrenadeExplosionEvent
    {
        std::array<float, 3> origin{};
        std::uint16_t weapon{};
        std::uint8_t direction{};
        std::uint8_t surfaceType{};
        bool operator==(const SvGrenadeExplosionEvent &) const = default;
    };

    [[nodiscard]] std::optional<SvEntityState> SV_ProjectGrenadeExplosionEntity(
        const SvGrenadeExplosionEvent &event, std::uint32_t entityNum);
    [[nodiscard]] bool SV_IsGrenadeExplosionEntityValid(const SvEntityState &entity);
}
