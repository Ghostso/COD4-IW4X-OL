#pragma once

#include "Demonware/AuthSession.hpp"
#include "Demonware/MarketplaceService.hpp"
#include "SharedRoomSessionOwner.hpp"
#include "../shared/DedicatedControl.hpp"
#include "../shared/DedicatedSession.hpp"

#include <cstdint>
#include <functional>
#include <memory>
#include <span>
#include <string>
#include <string_view>

namespace AlwaysofflineRe
{
    [[nodiscard]] std::optional<OlMod::DedicatedSession::MatchRules>
        resolveMatchRules(
            std::string_view playlistText,
            const OlMod::DedicatedSession::BookingSelection &selection);

    class DedicatedBookingDispatcher
    {
    public:
        using Diagnostic = std::function<void(std::string_view)>;
        using EntitlementCheck = std::function<bool(
            std::uint64_t, std::span<const std::uint32_t>)>;
        using RosterProvider = std::function<std::optional<FrozenRoomRoster>(
            std::uint64_t)>;
        using MatchRulesProvider = std::function<
            std::optional<OlMod::DedicatedSession::MatchRules>(
                const OlMod::DedicatedSession::BookingSelection &)>;
        // (bridgeIpv4, bridgePort, message, timeoutMilliseconds). The address
        // leads because it is the half that used to be missing: a member was
        // addressed by port alone, which only ever worked on one machine.
        using ControlSubmit = std::function<OlMod::DedicatedControl::SubmitResult(
            std::uint32_t,
            std::uint16_t,
            const OlMod::DedicatedControl::Message &,
            std::uint32_t)>;

        DedicatedBookingDispatcher(
            Demonware::AuthSession &session,
            Demonware::MarketplaceService &marketplace,
            Diagnostic diagnostic);
        DedicatedBookingDispatcher(
            Demonware::AuthSession &session,
            Demonware::MarketplaceService &marketplace,
            RosterProvider rosterProvider,
            Diagnostic diagnostic);
        DedicatedBookingDispatcher(
            Demonware::AuthSession &session,
            EntitlementCheck entitlementCheck,
            RosterProvider rosterProvider,
            MatchRulesProvider matchRulesProvider,
            ControlSubmit controlSubmit,
            Diagnostic diagnostic);
        ~DedicatedBookingDispatcher();
        DedicatedBookingDispatcher(const DedicatedBookingDispatcher &) = delete;
        DedicatedBookingDispatcher &operator=(const DedicatedBookingDispatcher &) = delete;

        [[nodiscard]] bool submit(std::string command);

    private:
        struct State;
        std::unique_ptr<State> state_;
    };
}
