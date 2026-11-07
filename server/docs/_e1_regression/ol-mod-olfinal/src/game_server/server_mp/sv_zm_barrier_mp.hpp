#pragma once

#include "sv_entity_mp.hpp"
#include <array>
#include <cstdint>
#include <cmath>
#include <optional>

namespace CodolGameServer
{
    // Factory demos: three simultaneous l/m/r occupants, six independently
    // selectable boards. No assumption that a lane always removes the same pair.
    // Times come from this build's named board/end XAnim notifies at map load.
    struct SvZmTearClip
    {
        std::uint16_t animation{};
        std::uint32_t boardMilliseconds{};
        std::uint32_t endMilliseconds{};
        bool operator==(const SvZmTearClip &) const = default;
        [[nodiscard]] bool valid() const noexcept
        {
            return animation > 0 && animation < 4096 && boardMilliseconds > 0 &&
                endMilliseconds >= boardMilliseconds;
        }
    };

    using SvZmTearClips = std::array<std::array<SvZmTearClip,6>,3>;

    [[nodiscard]] inline SvZmTearClip SV_ZmTearClipFromMarkers(
        std::uint16_t animation, float boardSeconds, float endSeconds) noexcept
    {
        if (!std::isfinite(boardSeconds) || !std::isfinite(endSeconds) ||
            boardSeconds <= 0.0f || endSeconds < boardSeconds || endSeconds > 60.0f)
            return {};
        const SvZmTearClip clip{animation,
            // Preserve native float clock precision. Promoting 1.7f to double
            // before scaling produced 1700.000047 -> 1701 and delayed release
            // a whole server tick despite the marker being exactly 1700 ms.
            static_cast<std::uint32_t>(std::ceil(boardSeconds*1000.0f)),
            static_cast<std::uint32_t>(std::ceil(endSeconds*1000.0f))};
        return clip.valid() ? clip : SvZmTearClip{};
    }

    struct SvZmTearLease
    {
        SvEntityHandle actor{};
        std::uint8_t lane{};
        std::uint8_t board{}; // zero based; MapEnts boardIndex minus one
        std::uint64_t serial{};
        std::uint32_t started{};
        SvZmTearClip clip{};
        bool operator==(const SvZmTearLease &) const = default;
    };

    // Per-window ownership only. The world commits the brush trajectory before
    // acknowledgeRelease; a failed native mutation leaves the release pending.
    // This class neither deletes brushes nor invents flight/landing coordinates.
    class SvZmBarrierController
    {
    public:
        [[nodiscard]] std::optional<SvZmTearLease> acquire(
            SvEntityHandle actor, std::uint8_t lane, std::uint8_t board,
            SvZmTearClip clip, std::uint32_t now)
        {
            if (lane >= lanes_.size() || board >= released_.size() || !clip.valid() ||
                actor.entityNum >= EntityNumWorld || lanes_[lane] || released_[board])
                return std::nullopt;
            for (const auto &lease : lanes_)
                if (lease && (lease->actor == actor || lease->board == board))
                    return std::nullopt;
            SvZmTearLease lease{actor,lane,board,++serial_,now,clip};
            lanes_[lane] = lease;
            return lease;
        }

        [[nodiscard]] bool releaseDue(const SvZmTearLease &lease,
            std::uint32_t now) const noexcept
        {
            return owns(lease) && !released_[lease.board] &&
                elapsed(lease,now) >= lease.clip.boardMilliseconds;
        }

        [[nodiscard]] bool acknowledgeRelease(const SvZmTearLease &lease,
            std::uint32_t now) noexcept
        {
            if (!releaseDue(lease,now)) return false;
            released_[lease.board] = true;
            return true;
        }

        template<class CommitMotion>
        [[nodiscard]] bool commitRelease(const SvZmTearLease &lease,
            std::uint32_t now, CommitMotion &&commitMotion)
        {
            if (!releaseDue(lease,now)) return false;
            // The caller owns the native brush transaction and its rollback.
            // No release state changes on a failed/throwing transaction.
            if (!commitMotion()) return false;
            return acknowledgeRelease(lease,now);
        }

        [[nodiscard]] bool finish(const SvZmTearLease &lease,
            std::uint32_t now) noexcept
        {
            if (!owns(lease) || !released_[lease.board] ||
                elapsed(lease,now) < lease.clip.endMilliseconds) return false;
            lanes_[lease.lane].reset();
            return true;
        }

        void cancel(SvEntityHandle actor) noexcept
        {
            for (auto &lease : lanes_)
                if (lease && lease->actor == actor) lease.reset();
            // Released boards remain released: killing a tearing actor does not
            // restore a brush that has already begun its flight.
        }

        [[nodiscard]] const std::array<std::optional<SvZmTearLease>,3> &lanes() const
            noexcept { return lanes_; }
        [[nodiscard]] bool released(std::uint8_t board) const noexcept
            { return board < released_.size() && released_[board]; }

        // A repaired board becomes tearable again only after its return motion has
        // committed. Refuse an in-flight lease so repair cannot steal a board from
        // the actor currently tearing it.
        [[nodiscard]] bool restore(std::uint8_t board) noexcept
        {
            if (board >= released_.size() || !released_[board])
                return false;
            for (const auto &lease : lanes_)
                if (lease && lease->board == board)
                    return false;
            released_[board] = false;
            return true;
        }

    private:
        [[nodiscard]] bool owns(const SvZmTearLease &lease) const noexcept
        {
            return lease.lane < lanes_.size() && lanes_[lease.lane] &&
                *lanes_[lease.lane] == lease;
        }
        [[nodiscard]] static std::uint32_t elapsed(const SvZmTearLease &lease,
            std::uint32_t now) noexcept
        {
            // A clock reset cannot turn an old lease into an immediate release.
            return now >= lease.started ? now-lease.started : 0;
        }
        std::array<std::optional<SvZmTearLease>,3> lanes_{};
        std::array<bool,6> released_{};
        std::uint64_t serial_{};
    };
}
