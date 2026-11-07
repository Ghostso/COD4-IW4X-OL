#include "sv_grenade_launch_mp.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>

namespace CodolGameServer
{
    namespace
    {
        bool finite(const std::array<float,3> &v)
        {
            return std::ranges::all_of(v, [](float x) { return std::isfinite(x); });
        }

        bool valid(const SvGrenadeLaunchParameters &p)
        {
            return p.weapon && p.weapon <= 0x7FF && p.speed > 0 &&
                p.speedUp >= 0 && p.fuseMilliseconds >= 0;
        }
    }

    std::optional<SvGrenadeLaunchParameters> SV_ReadGrenadeLaunchParameters(
        const std::uint16_t weapon, const std::span<const std::uint8_t> definition)
    {
        // CODREF(1649370): 429E10 type/offhand, 4297D0 fuse, 42A0C0 cooking;
        // 445910 timedDetonation gate matches IW4 CG_AddHudGrenade 821A3768.
        // Speed +2616/+2620 is verified by all eleven absolute DM Semtex launches
        // (checkpoint44): pre-inheritance delay and truncated velocity agree.
        if (definition.size() < 3838) return std::nullopt;
        const auto read = [&](std::size_t offset) {
            std::int32_t value{};
            std::memcpy(&value, definition.data() + offset, sizeof(value));
            return value;
        };
        if (read(1416) != 1 || read(1436) <= 0 ||
            definition[3811] > 1 || definition[3837] > 1) return std::nullopt;
        const SvGrenadeLaunchParameters result{weapon,read(2616),read(2620),
            read(2284),definition[3811] != 0,definition[3837] != 0};
        return valid(result) ? std::optional{result} : std::nullopt;
    }

    std::optional<SvMissileSpawnRequest> SV_ComputeGrenadeLaunch(
        const SvGrenadeLaunchRequest &r, const SvDirectionToAngles &toAngles)
    {
        if (!valid(r.parameters) || !SV_IsWeaponFireBasisValid(r.basis) ||
            r.basis.weaponAssetIndex != r.parameters.weapon || r.basis.weaponType != 1 ||
            r.owner >= EntityNumWorld || r.heldFuseMilliseconds < 0 || !toAngles ||
            !finite(r.playerVelocity) || !finite(r.angularVelocity)) return std::nullopt;

        // CODREF(IW4 8233E610/823138F0/82313C80, Ghosts 14016BEA0/140135CB0):
        // toss first, direction angles before quantization, visibility delay
        // before velocity inheritance. This ordering is visible in CODOL's demo.
        std::array<float,3> toss{};
        for (std::size_t i{}; i < 3; ++i)
            toss[i] = r.basis.forward[i] * static_cast<float>(r.parameters.speed);
        toss[2] += static_cast<float>(r.parameters.speedUp);
        const auto fitsNativeInteger = [](float x) {
            return std::isfinite(x) && x >= -2147483648.0f && x < 2147483648.0f;
        };
        if (!std::ranges::all_of(toss,fitsNativeInteger) ||
            !std::ranges::all_of(r.angularVelocity,fitsNativeInteger)) return std::nullopt;
        const float speed = std::sqrt(toss[0]*toss[0] + toss[1]*toss[1] + toss[2]*toss[2]);
        if (!std::isfinite(speed) || speed <= 0) return std::nullopt;
        const float delayValue = 85.0f - speed * 35.0f / 600.0f;
        const auto delay = static_cast<std::uint32_t>(std::clamp(delayValue,20.0f,50.0f));

        // A player's non-timed grenade receives the reference cleanup deadline,
        // not a detonation promise. The think owner must distinguish the two.
        // PM already decremented a cooked fuse; do not subtract hold time again.
        const std::uint32_t fuse = r.parameters.timedDetonation
            ? static_cast<std::uint32_t>(r.heldFuseMilliseconds
                ? r.heldFuseMilliseconds : r.parameters.fuseMilliseconds)
            : 30000u;
        const auto lifetime = std::min(fuse,60000u);
        constexpr auto maxTime = static_cast<std::uint32_t>(std::numeric_limits<std::int32_t>::max());
        if (r.time > maxTime - std::max(lifetime,delay)) return std::nullopt;

        SvMissileSpawnRequest result;
        auto &m = result.initial;
        m.weapon = r.parameters.weapon;
        m.owner = r.owner;
        m.ground = EntityNumNone;
        m.position = {5,static_cast<std::int32_t>(r.time),0,r.basis.muzzleTrace,{}};
        m.angles.base.fill(std::numeric_limits<float>::quiet_NaN());
        if (!toAngles(toss,m.angles.base) || !finite(m.angles.base)) return std::nullopt;
        // Retained vectoangles 764C10 produces unsigned pitch/yaw and zero roll.
        // Tiny negative native angles may round to 360 when wrapped to float.
        if (m.angles.base[0] < 0 || m.angles.base[0] > 360 ||
            m.angles.base[1] < 0 || m.angles.base[1] > 360 || m.angles.base[2] != 0)
            return std::nullopt;
        if (r.rotate)
        {
            m.angles.type = 2; // CODOL linear; BO1's ordinal 3 is different.
            m.angles.time = static_cast<std::int32_t>(r.time);
            m.angles.base[0] -= 120.0f;
            if (m.angles.base[0] < 0) m.angles.base[0] += 360.0f;
            for (std::size_t i{}; i < 3; ++i)
                m.angles.delta[i] = std::trunc(r.angularVelocity[i]);
        }

        std::array<float,3> direction{};
        for (std::size_t i{}; i < 3; ++i) direction[i] = toss[i] / speed;
        const float inherited = r.playerVelocity[0]*direction[0] +
            r.playerVelocity[1]*direction[1] + r.playerVelocity[2]*direction[2];
        for (std::size_t i{}; i < 3; ++i)
            m.position.delta[i] = std::trunc(toss[i]) + inherited * direction[i];
        if (!finite(m.position.delta) || !finite(m.angles.delta)) return std::nullopt;
        m.launchTime = r.time + delay;
        result.fuseDeadline = r.time + lifetime;
        // Preserve InitGrenadeTimer's zero-nextthink fallback at clock zero.
        if (!result.fuseDeadline) result.fuseDeadline = 30000;
        return result;
    }
}
