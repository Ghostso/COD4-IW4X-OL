#include "sv_weapon_loadout_mp.hpp"

#include <algorithm>
#include <array>

namespace CodolGameServer
{
    std::optional<std::vector<NamedWeaponAttachment>>
        SV_MergeWeaponAttachments(
            const std::span<const NamedWeaponAttachment> defaults,
            const std::span<const NamedWeaponAttachment> equipped)
    {
        std::array<bool, WeaponAttachmentSlotCount> defaultSlots{};
        std::array<bool, WeaponAttachmentSlotCount> equippedSlots{};
        const auto validate = [](const NamedWeaponAttachment &attachment) {
            return attachment.slot > 0 &&
                attachment.slot < WeaponAttachmentSlotCount &&
                !attachment.name.empty();
        };

        for (const auto &attachment : defaults)
        {
            if (!validate(attachment) || defaultSlots[attachment.slot])
                return std::nullopt;
            defaultSlots[attachment.slot] = true;
        }
        for (const auto &attachment : equipped)
        {
            if (!validate(attachment) || equippedSlots[attachment.slot])
                return std::nullopt;
            equippedSlots[attachment.slot] = true;
        }

        std::vector<NamedWeaponAttachment> result;
        result.reserve(defaults.size() + equipped.size());
        for (const auto &attachment : defaults)
        {
            if (!equippedSlots[attachment.slot])
                result.push_back(attachment);
        }
        result.insert(result.end(), equipped.begin(), equipped.end());
        // ORDERED BY SLOT, BECAUSE THE STRING IS THE VARIANT KEY.
        //
        // `** <weapon> 0 0 <attachment...>` is not a set -- the engine resolves the
        // whole string to a weapon and builds its DObj from the order it reads. Retail
        // says so directly: weapon 992's default is `** 992 0 0 9321`, and the same
        // weapon with a red dot is `** 992 0 0 6206 9321` -- 6206 INSERTED BEFORE 9321,
        // not appended. Weapon 646 does the same, `14268 8738 9321` against a default
        // of `8738 9321`.
        //
        // Appending put the equipped attachment last, which built a different variant
        // and bound its model to the wrong DObj part: the client faulted at spawn with
        // `1073 tag_reticle_red_dot fja_bountyhunter_kitty_sc_f_vmchar` -- looking for
        // the sight's tag on the VIEWMODEL CHARACTER, the player's jacket, instead of
        // the weapon. Section 187.
        //
        // Sorting the merged list rather than only the equipped half, so defaults and
        // equipped share one rule and the answer does not depend on which half a
        // given attachment arrived in.
        std::stable_sort(
            result.begin(), result.end(),
            [](const NamedWeaponAttachment &left,
                const NamedWeaponAttachment &right) {
                return left.slot < right.slot;
            });
        if (result.size() > MaximumModularWeaponAttachmentCount)
            return std::nullopt;
        return result;
    }

    bool SV_ShouldRefreshClientLoadouts(
        const bool gameStateConfigured,
        const std::uint32_t activeClients,
        const bool refreshRequested)
    {
        if (gameStateConfigured && activeClients != 0)
            return false;
        return refreshRequested;
    }
}
