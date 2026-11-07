#include "sv_missile_mp.hpp"
#include "sv_snapshot_mp.hpp"
#include "sv_entity_mp.hpp"
#include <algorithm>
#include <bit>
#include <cmath>

namespace CodolGameServer
{
    std::optional<SvEntityState> SV_ProjectMissileEntity(const SvMissileNetworkState &m)
    {
        if (m.number < FirstDynamicServerEntityNum || m.number >= EntityNumWorld ||
            !m.weapon || m.weapon > 0x7FF || m.owner > EntityNumNone ||
            m.ground > EntityNumNone || m.eFlags > 0x3FFFFFFF || m.surfaceType > 31 ||
            !std::isfinite(m.scale) || m.scale <= 0 ||
            !std::ranges::all_of(m.events, SV_IsEntityEventValid) ||
            !SV_IsTrajectoryValid(m.position, m.position.time) ||
            !SV_IsTrajectoryValid(m.angles, m.angles.time)) return std::nullopt;
        SvEntityState e;
        e.scriptMoverField00E4 = 0;
        e.number = m.number;
        e.eType = SvEntityTypeMissile;
        e.weaponAssetIndex = m.weapon;
        // CODOL's ET_MISSILE owner is +84; ground is +8C. The per-type writer
        // maps these semantic members rather than borrowing another table.
        e.otherEntityNum = m.owner;
        e.groundEntityNum = m.ground;
        e.eFlags = m.eFlags;
        e.origin = m.position.base;
        e.positionTrajectoryDelta = m.position.delta;
        e.positionTrajectoryType = static_cast<std::uint8_t>(m.position.type);
        e.positionTrajectoryTime = std::bit_cast<std::uint32_t>(m.position.time);
        e.positionTrajectoryDuration = static_cast<std::uint32_t>(m.position.duration);
        e.angles = m.angles.base;
        e.angleTrajectoryDelta = m.angles.delta;
        e.angleTrajectoryType = static_cast<std::uint8_t>(m.angles.type);
        e.angleTrajectoryTime = std::bit_cast<std::uint32_t>(m.angles.time);
        e.angleTrajectoryDuration = static_cast<std::uint32_t>(m.angles.duration);
        e.modelScale = m.scale;
        e.lerpData0058 = m.launchTime;
        e.impactSurfaceType = m.surfaceType;
        e.eventSequence = m.eventSequence;
        e.events = m.events;
        return e;
    }

    bool SV_IsMissileEntityValid(const SvEntityState &e)
    {
        if (e.eType != SvEntityTypeMissile) return false;
        const SvMissileNetworkState m{
            e.number, e.weaponAssetIndex, e.otherEntityNum,
            static_cast<std::uint16_t>(e.groundEntityNum), e.eFlags,
            {e.positionTrajectoryType, std::bit_cast<std::int32_t>(e.positionTrajectoryTime),
                std::bit_cast<std::int32_t>(e.positionTrajectoryDuration),
                e.origin, e.positionTrajectoryDelta},
            {e.angleTrajectoryType, std::bit_cast<std::int32_t>(e.angleTrajectoryTime),
                std::bit_cast<std::int32_t>(e.angleTrajectoryDuration),
                e.angles, e.angleTrajectoryDelta},
            e.modelScale, e.lerpData0058, e.impactSurfaceType, e.eventSequence, e.events};
        const auto projected = SV_ProjectMissileEntity(m);
        // Equality also rejects truncation and stale fields owned by other types.
        return projected && *projected == e;
    }
}
