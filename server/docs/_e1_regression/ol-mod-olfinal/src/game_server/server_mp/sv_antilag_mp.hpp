#pragma once

#include <array>
#include <cstdint>
#include <deque>
#include <optional>
#include <span>
#include <vector>

namespace CodolGameServer
{
    inline constexpr std::uint32_t SvAntiLagMaximumRewindMilliseconds = 400;

    struct SvAntiLagPlayerPose
    {
        std::uint32_t clientNum{};
        std::uint8_t spawnGeneration{};
        std::array<float, 3> origin{};

        bool operator==(const SvAntiLagPlayerPose &) const = default;
    };

    class SvAntiLagHistory
    {
    public:
        void clear();
        void record(
            std::uint32_t serverTime,
            std::span<const SvAntiLagPlayerPose> players);

        [[nodiscard]] std::optional<std::array<float, 3>> originAt(
            std::uint32_t clientNum,
            std::uint8_t spawnGeneration,
            std::uint32_t commandTime,
            std::uint32_t serverTime,
            std::uint32_t frameMilliseconds,
            const std::array<float, 3> &currentOrigin) const;

        [[nodiscard]] std::size_t frameCount() const { return frames_.size(); }

    private:
        struct Frame
        {
            std::uint32_t serverTime{};
            std::vector<SvAntiLagPlayerPose> players;
        };

        std::deque<Frame> frames_;
    };
}
