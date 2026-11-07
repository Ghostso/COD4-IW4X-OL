#include "sv_splash_mp.hpp"

namespace CodolGameServer
{
    std::string SV_BuildSplashCommand(
        const std::uint32_t slot,
        const std::uint32_t row,
        const std::int32_t points)
    {
        // Three arguments, in the order sub_C1C860 reads them: it takes argv(3)
        // as the points and argv(2) as the row, and clamps the slot itself.
        return "w " + std::to_string(slot) + " " + std::to_string(row) + " " +
            std::to_string(points);
    }
}
