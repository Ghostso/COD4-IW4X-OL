#include "sv_battlechatter_mp.hpp"

namespace CodolGameServer
{
    std::optional<bool> SV_BattleChatterFemaleFromModelName(
        const std::string_view bodyModelName)
    {
        std::optional<bool> female;
        std::size_t start{};
        while (start <= bodyModelName.size())
        {
            const auto end = bodyModelName.find('_', start);
            const auto component = bodyModelName.substr(
                start,
                end == std::string_view::npos ? std::string_view::npos
                                              : end - start);
            // The LAST one wins: `fpa_cowprestigea_sc_m_00_hrt` has the gender
            // before two variant tokens, and a name whose subject happens to
            // contain a lone letter earlier must not outrank the real one.
            if (component == "m")
                female = false;
            else if (component == "f")
                female = true;
            if (end == std::string_view::npos)
                break;
            start = end + 1;
        }
        return female;
    }

    float SV_BattleChatterDistanceSquared(
        const std::array<float, 3> &left, const std::array<float, 3> &right)
    {
        const auto dx = left[0] - right[0];
        const auto dy = left[1] - right[1];
        const auto dz = left[2] - right[2];
        return dx * dx + dy * dy + dz * dz;
    }

    bool SV_BattleChatterSuppressed(
        const std::uint32_t clientNum,
        const std::array<float, 3> &origin,
        const std::span<const SvBattleChatterSpeaker> speakers,
        const std::uint32_t currentServerTime)
    {
        constexpr auto radiusSquared =
            SvBattleChatterSuppressionRadius * SvBattleChatterSuppressionRadius;
        for (const auto &speaker : speakers)
        {
            // An expired hold is not a speaker. The caller may keep stale
            // entries; deciding here rather than requiring a swept list keeps
            // the two from disagreeing about who currently holds the floor.
            if (currentServerTime >= speaker.untilServerTime)
                continue;
            // CODREF: isSpeakerInRange returns true for the player themselves
            // BEFORE any distance test, so a player cannot talk over their own
            // line however far they have run in the meantime.
            if (speaker.clientNum == clientNum)
                return true;
            if (SV_BattleChatterDistanceSquared(speaker.origin, origin) <
                radiusSquared)
            {
                return true;
            }
        }
        return false;
    }

    std::vector<std::uint32_t> SV_BattleChatterAudience(
        const std::uint32_t speakerClientNum,
        const std::array<float, 3> &speakerOrigin,
        const SvTeam speakerTeam,
        const std::span<const SvBattleChatterListener> listeners,
        const SvBattleChatterAudience audience)
    {
        constexpr auto radiusSquared =
            SvBattleChatterAudibleRadius * SvBattleChatterAudibleRadius;
        std::vector<std::uint32_t> receivers;
        for (const auto &listener : listeners)
        {
            if (!listener.alive)
                continue;
            // CODREF: playSoundToTeam( alias, team, self ) -- the third
            // argument is the EXCLUDED entity. You never hear your own
            // battlechatter, in any mode. This holds on both audience settings
            // because it is not the part that is in question.
            if (listener.clientNum == speakerClientNum &&
                audience != SvBattleChatterAudience::EveryoneIncludingSpeaker)
            {
                continue;
            }
            // THE ONE PREDICATE. Everything else in this feature is identical
            // between the two settings; see the header for why it is a knob at
            // all and why delivery is per-client rather than a world entity.
            if (audience == SvBattleChatterAudience::Team)
            {
                if (speakerTeam == SvTeam::None ||
                    speakerTeam == SvTeam::Spectator ||
                    listener.team != speakerTeam)
                {
                    continue;
                }
            }
            // Stands in for the attenuation a positional sound would have done
            // for us. `maxdist` is the alias record's own 1400.
            if (SV_BattleChatterDistanceSquared(speakerOrigin, listener.origin) >
                radiusSquared)
            {
                continue;
            }
            receivers.push_back(listener.clientNum);
        }
        return receivers;
    }
}
