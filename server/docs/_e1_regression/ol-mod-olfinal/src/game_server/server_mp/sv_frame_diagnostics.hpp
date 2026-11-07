#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <iterator>

namespace CodolGameServer
{
    struct SvTimingWindow
    {
        std::uint64_t count{};
        std::uint64_t totalMicroseconds{};
        std::uint64_t lastMicroseconds{};
        std::uint64_t maximumMicroseconds{};
        // <=1, <=2, <=5, <=10, <=20, <=50 and >50 milliseconds.
        std::array<std::uint64_t, 7> buckets{};

        [[nodiscard]] std::uint64_t averageMicroseconds() const
        {
            return count ? totalMicroseconds / count : 0;
        }

        bool operator==(const SvTimingWindow &) const = default;
    };

    class SvTimingAccumulator
    {
    public:
        void record(const std::uint64_t microseconds)
        {
            ++window_.count;
            window_.totalMicroseconds += microseconds;
            window_.lastMicroseconds = microseconds;
            window_.maximumMicroseconds = std::max(
                window_.maximumMicroseconds, microseconds);
            constexpr std::array<std::uint64_t, 6> thresholds{
                1'000, 2'000, 5'000, 10'000, 20'000, 50'000,
            };
            const auto bucket = std::ranges::find_if(
                thresholds,
                [microseconds](const auto threshold) {
                    return microseconds <= threshold;
                });
            ++window_.buckets[static_cast<std::size_t>(
                std::distance(thresholds.begin(), bucket))];
        }

        [[nodiscard]] SvTimingWindow take()
        {
            const auto result = window_;
            window_ = {};
            return result;
        }

    private:
        SvTimingWindow window_;
    };
}
