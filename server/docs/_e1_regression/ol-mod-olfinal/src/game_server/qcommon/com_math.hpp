#pragma once

#include <cmath>
#include <cstdint>

namespace CodolGameServer
{
    constexpr float ShortAngleScale = 360.0f / 65536.0f;
    constexpr float AngleShortScale = 65536.0f / 360.0f;

    [[nodiscard]] inline float BG_ShortToAngle(const std::uint16_t value)
    {
        return static_cast<float>(value) * ShortAngleScale;
    }

    [[nodiscard]] inline std::uint16_t BG_AngleToShort(const float value)
    {
        return static_cast<std::uint16_t>(
            static_cast<std::int32_t>(value * AngleShortScale));
    }

    [[nodiscard]] inline float BG_NormalizeAngle360(const float value)
    {
        const auto wrapped = std::fmod(value, 360.0f);
        return wrapped < 0.0f ? wrapped + 360.0f : wrapped;
    }
}
