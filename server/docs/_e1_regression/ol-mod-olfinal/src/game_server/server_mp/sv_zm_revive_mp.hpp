#pragma once

#include <cstdint>
#include <optional>

namespace CodolGameServer
{
    // CODREF(zm_revive): CODOL 1649370 PM_CheckDuck 417D10, 417FFB..
    // 418003 forces prone for pm_type 7. BO1's last-stand types are different.
    inline constexpr std::uint8_t SvPmTypeZombieDowned = 7;
    // OLMOD(zm_revive): explicit reconstruction policy, not recovered CODOL odds/timers.
    inline constexpr std::uint32_t SvZombieReviveMilliseconds = 4000;
    inline constexpr std::uint32_t SvZombieBleedoutMilliseconds = 45000;
    inline constexpr float SvZombieReviveRadius = 72.0f;

    // CODREF(1649370 593FED,7BDCE0): bit100000 hides the viewweapon but also
    // enters a locked-entity asset consumer. It is NOT a hide-only flag.
    // TODO(CODOL): recover the complete native hide-viewmodel contract before
    // hiding a treatment helper's gun; ordinary entity flags remain untouched.

    struct SvZombieDownedState
    {
        std::uint32_t generation{}, downedAt{}, round{};
        std::uint16_t weaponAssetIndex{};
        bool bledOut{};
        bool scoreRecorded{};
        std::optional<std::uint32_t> reviver;
        std::uint32_t reviverGeneration{}, startedAt{}, lastSeen{}, duration{};

        void cancel()
        {
            reviver.reset();
            reviverGeneration = startedAt = lastSeen = duration = 0;
        }
    };
}
