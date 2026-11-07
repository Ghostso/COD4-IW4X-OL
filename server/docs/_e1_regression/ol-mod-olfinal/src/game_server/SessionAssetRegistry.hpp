#pragma once

#include "EngineBindings.hpp"
#include "server_mp/sv_snapshot_mp.hpp"

#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <string_view>

namespace CodolGameServer
{
    struct RegisteredSessionAssets
    {
        ClientCharacterPresentation characterPresentation;
        std::map<std::string, SvResolvedLoadout> loadouts;
        std::map<std::string, SvResolvedPerks> perks;
        // Retained per member/class for the offhand grant owner. Capturing this
        // request does not claim that projectile simulation is implemented.
        std::map<std::string, OlMod::DedicatedSession::EquipmentRequest> equipment;
        std::map<std::string, SvResolvedEquipment> offhands;
        // Shared class-0 selection; nullopt means resolution failed, while an
        // engaged empty selection means the player equipped no rewards.
        std::optional<SvResolvedRewards> rewards;

        bool operator==(const RegisteredSessionAssets &) const = default;
    };

    class SessionAssetRegistry
    {
    public:
        using Members = std::map<std::uint64_t, RegisteredSessionAssets>;

        [[nodiscard]] bool replace(Members members)
        {
            if (members.empty() ||
                members.contains(0) && members.size() != 1)
            {
                return false;
            }
            for (const auto &[xuid, assets] : members)
            {
                static_cast<void>(xuid);
                if (assets.loadouts.empty())
                    return false;
            }
            members_ = std::move(members);
            return true;
        }

        // REFRESH ONE MEMBER IN PLACE. This is the live loadout update (§157c):
        // it replaces one player's classes/character without the full replace()
        // that a SessionStart does, so the other members and the running match
        // are untouched. The next spawn resolves the new loadout. Refuses an
        // empty member so a bad update cannot blank a player's loadout.
        [[nodiscard]] bool updateMember(
            const std::uint64_t xuid, RegisteredSessionAssets assets)
        {
            if (!xuid || assets.loadouts.empty())
                return false;
            const auto member = members_.find(xuid);
            if (member != members_.end())
                member->second = std::move(assets);
            else
                members_.emplace(xuid, std::move(assets));
            return true;
        }

        [[nodiscard]] std::optional<SvResolvedLoadout> loadout(
            const std::uint64_t xuid,
            const std::string_view selectedLoadout) const
        {
            const auto member = findMember(xuid);
            if (member == members_.end())
                return std::nullopt;
            const auto loadout = member->second.loadouts.find(
                std::string(selectedLoadout));
            return loadout == member->second.loadouts.end()
                ? std::nullopt
                : std::optional{ loadout->second };
        }

        [[nodiscard]] std::optional<SvResolvedPerks> perks(
            const std::uint64_t xuid, const std::string_view selectedLoadout) const
        {
            const auto member = findMember(xuid);
            if (member == members_.end())
                return std::nullopt;
            const auto found = member->second.perks.find(std::string(selectedLoadout));
            return found == member->second.perks.end()
                ? std::nullopt : std::optional{ found->second };
        }

        [[nodiscard]] std::optional<OlMod::DedicatedSession::EquipmentRequest> equipment(
            const std::uint64_t xuid, const std::string_view selectedLoadout) const
        {
            const auto member = findMember(xuid);
            if (member == members_.end())
                return std::nullopt;
            const auto found = member->second.equipment.find(std::string(selectedLoadout));
            return found == member->second.equipment.end()
                ? std::nullopt : std::optional{ found->second };
        }

        [[nodiscard]] std::optional<SvResolvedEquipment> resolvedEquipment(
            const std::uint64_t xuid, const std::string_view selectedLoadout) const
        {
            const auto member = findMember(xuid);
            if (member == members_.end()) return std::nullopt;
            const auto found = member->second.offhands.find(std::string(selectedLoadout));
            return found == member->second.offhands.end()
                ? std::nullopt : std::optional{found->second};
        }

        [[nodiscard]] std::optional<SvResolvedRewards> rewards(
            const std::uint64_t xuid) const
        {
            const auto member = findMember(xuid);
            return member == members_.end() ? std::nullopt : member->second.rewards;
        }

        [[nodiscard]] const ClientCharacterPresentation *character(
            const std::uint64_t xuid) const
        {
            const auto member = findMember(xuid);
            return member == members_.end()
                ? nullptr
                : &member->second.characterPresentation;
        }

        [[nodiscard]] const Members &members() const { return members_; }

    private:
        [[nodiscard]] Members::const_iterator findMember(
            const std::uint64_t xuid) const
        {
            auto member = members_.find(xuid);
            if (member == members_.end() && members_.size() == 1 &&
                members_.begin()->first == 0)
            {
                member = members_.begin();
            }
            return member;
        }

        Members members_;
    };
}
