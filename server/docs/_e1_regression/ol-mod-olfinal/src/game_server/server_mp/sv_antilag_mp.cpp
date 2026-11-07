#include "sv_antilag_mp.hpp"

#include <algorithm>
#include <cmath>

namespace CodolGameServer
{
    namespace
    {
        const SvAntiLagPlayerPose *findPlayer(
            const std::span<const SvAntiLagPlayerPose> players,
            const std::uint32_t clientNum,
            const std::uint8_t spawnGeneration)
        {
            const auto found = std::ranges::lower_bound(
                players, clientNum, {}, &SvAntiLagPlayerPose::clientNum);
            return found != players.end() && found->clientNum == clientNum &&
                    found->spawnGeneration == spawnGeneration
                ? &*found
                : nullptr;
        }

        bool finiteOrigin(const std::array<float, 3> &origin)
        {
            return std::ranges::all_of(
                origin, [](const float value) { return std::isfinite(value); });
        }
    }

    void SvAntiLagHistory::clear()
    {
        frames_.clear();
    }

    void SvAntiLagHistory::record(
        const std::uint32_t serverTime,
        const std::span<const SvAntiLagPlayerPose> players)
    {
        std::vector<SvAntiLagPlayerPose> ordered{
            players.begin(), players.end()};
        std::erase_if(ordered, [](const SvAntiLagPlayerPose &pose) {
            return !finiteOrigin(pose.origin);
        });
        std::ranges::sort(ordered, {}, &SvAntiLagPlayerPose::clientNum);
        const auto duplicate = std::ranges::adjacent_find(
            ordered, {}, &SvAntiLagPlayerPose::clientNum);
        if (duplicate != ordered.end())
            return;

        if (!frames_.empty() && frames_.back().serverTime == serverTime)
            frames_.back().players = std::move(ordered);
        else
            frames_.push_back({serverTime, std::move(ordered)});

        constexpr std::uint32_t RetentionMilliseconds =
            SvAntiLagMaximumRewindMilliseconds + 100;
        while (!frames_.empty() &&
            serverTime - frames_.front().serverTime > RetentionMilliseconds)
        {
            frames_.pop_front();
        }
    }

    std::optional<std::array<float, 3>> SvAntiLagHistory::originAt(
        const std::uint32_t clientNum,
        const std::uint8_t spawnGeneration,
        const std::uint32_t commandTime,
        const std::uint32_t serverTime,
        const std::uint32_t frameMilliseconds,
        const std::array<float, 3> &currentOrigin) const
    {
        if (!frameMilliseconds || !finiteOrigin(currentOrigin))
            return std::nullopt;
        const auto age = serverTime - commandTime;
        if (age <= frameMilliseconds ||
            age > SvAntiLagMaximumRewindMilliseconds)
        {
            return std::nullopt;
        }

        const Frame *older{};
        const Frame *newer{};
        const SvAntiLagPlayerPose *olderPose{};
        const SvAntiLagPlayerPose *newerPose{};
        for (const auto &frame : frames_)
        {
            const auto *const pose = findPlayer(
                frame.players, clientNum, spawnGeneration);
            if (!pose)
                continue;
            if (static_cast<std::int32_t>(frame.serverTime - commandTime) <= 0)
            {
                older = &frame;
                olderPose = pose;
            }
            if (static_cast<std::int32_t>(frame.serverTime - commandTime) >= 0)
            {
                newer = &frame;
                newerPose = pose;
                break;
            }
        }
        if (!older || !olderPose)
            return std::nullopt;

        const auto *const newerOrigin = newerPose
            ? &newerPose->origin
            : &currentOrigin;
        const auto newerTime = newer ? newer->serverTime : serverTime;
        if (newerTime == older->serverTime)
            return olderPose->origin;
        if (static_cast<std::int32_t>(commandTime - older->serverTime) < 0 ||
            static_cast<std::int32_t>(newerTime - commandTime) < 0)
        {
            return std::nullopt;
        }

        const auto fraction = static_cast<float>(commandTime - older->serverTime) /
            static_cast<float>(newerTime - older->serverTime);
        std::array<float, 3> result{};
        for (std::size_t axis{}; axis < result.size(); ++axis)
        {
            result[axis] = olderPose->origin[axis] +
                ((*newerOrigin)[axis] - olderPose->origin[axis]) * fraction;
        }
        return finiteOrigin(result)
            ? std::optional{result}
            : std::nullopt;
    }
}
