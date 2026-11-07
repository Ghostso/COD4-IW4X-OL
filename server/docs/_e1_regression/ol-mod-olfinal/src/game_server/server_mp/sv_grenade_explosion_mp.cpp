#include "sv_grenade_explosion_mp.hpp"
#include "sv_snapshot_mp.hpp"

#include <algorithm>
#include <cmath>

namespace CodolGameServer
{
    std::optional<SvEntityState> SV_ProjectGrenadeExplosionEntity(
        const SvGrenadeExplosionEvent &event, const std::uint32_t entityNum)
    {
        if (entityNum < FirstDynamicServerEntityNum || entityNum >= EntityNumWorld ||
            !event.weapon || event.weapon > MaximumWeaponAssetIndex ||
            event.direction >= 162 || event.surfaceType > 31 ||
            !std::ranges::all_of(event.origin, [](float v) {
                return std::isfinite(v) && v == std::trunc(v);
            }))
            return std::nullopt;
        auto entity = wireZeroBaseline();
        entity.number = entityNum;
        entity.eType = 0;
        entity.eFlags = 16;
        entity.origin = event.origin;
        entity.weaponAssetIndex = event.weapon;
        entity.impactSurfaceType = event.surfaceType;
        entity.modelScale = 1.0f;
        entity.eventSequence = 1;
        entity.events[0] = {98, event.direction};
        return entity;
    }

    bool SV_IsGrenadeExplosionEntityValid(const SvEntityState &entity)
    {
        if (entity.events[0].parameter >= 162)
            return false;
        const auto expected = SV_ProjectGrenadeExplosionEntity({entity.origin,
            entity.weaponAssetIndex, static_cast<std::uint8_t>(entity.events[0].parameter),
            entity.impactSurfaceType}, entity.number);
        return expected && *expected == entity;
    }
}
