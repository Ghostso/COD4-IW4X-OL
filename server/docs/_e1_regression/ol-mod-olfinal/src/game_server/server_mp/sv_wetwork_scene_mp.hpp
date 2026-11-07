#pragma once

#include "sv_const_baselines_mp.hpp"

#include <span>

namespace CodolGameServer
{
    // Wetwork layers mission-owned movers over mp_cargoship's const scene.
    // The const fastfile ends at entity 823; the retail admission snapshot
    // carries another 180 full-state movers. Their layout is the same subset
    // already represented by SvConstBaselineEntry, but they are transmitted
    // states rather than client-side delta baselines.
    using SvWetworkSceneEntry = SvConstBaselineEntry;

    [[nodiscard]] std::span<const SvWetworkSceneEntry>
        SV_WetworkInitialScene();
}
