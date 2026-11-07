#pragma once

#include "sv_damage_mp.hpp"
#include "sv_weapon_fire_mp.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string_view>

namespace CodolGameServer
{
    // OLMOD(alpha-weapon-port): source-owned description of one 0.0.2.2
    // WeaponDef. It contains only fields whose alpha offsets have a named C1
    // consumer (or the explicitly bracketed penetrate field) and whose OLfinal
    // destination has independently been recovered. Pointer-bearing models,
    // materials, animations and sounds do not cross this structure.
    struct SvAlphaWeaponTuning
    {
        std::int32_t weaponType{};
        std::int32_t weaponClass{};
        std::int32_t penetrateType{};
        std::int32_t impactType{};
        std::int32_t fireType{};
        std::int32_t startAmmo{};
        std::int32_t maxAmmo{};
        std::int32_t shotCount{};
        std::int32_t damage{};
        std::int32_t minDamage{};
        std::int32_t meleeDamage{};
        std::int32_t fireDelayMilliseconds{};
        std::int32_t dropTimeMilliseconds{};
        std::int32_t raiseTimeMilliseconds{};
        std::int32_t overlayReticle{};
        std::array<float, 6> hipSpread{};
        float maxDamageRange{};
        float minDamageRange{};
        std::array<float, HitLocationCount> hitLocationMultipliers{};
        std::int32_t clipSize{};
        std::int32_t fireTimeMilliseconds{};
        bool aimDownSight{};

        bool operator==(const SvAlphaWeaponTuning &) const = default;
    };

    enum class SvAlphaWeaponLineage : std::uint8_t
    {
        MeasuredDescendant,
        CompatibilityAlias,
        ConvertedPresentation,
        MissingModelFamily,
    };

    struct SvAlphaWeaponPort
    {
        const char *alphaName{};
        const char *sourceName{};
        SvAlphaWeaponLineage lineage{};
        SvAlphaWeaponTuning tuning{};

        bool operator==(const SvAlphaWeaponPort &) const = default;
    };

    // CODREF(alpha_weapondef): OLfinal DB_SizeofXAsset<WeaponDef> 0x4834B0
    // returns 0x101C. DB_LinkXAssetEntry 0x49DA10 copies exactly that many
    // bytes through the type-28 size dispatch before publishing an entry.
    inline constexpr std::size_t OlfinalWeaponDefSize = 0x101C;

    [[nodiscard]] std::span<const SvAlphaWeaponPort>
        SV_AlphaWeaponPorts() noexcept;

    // OLfinal's shipped ordinary-weapon table ends at 1223. The client alpha
    // installer appends this catalog in declaration order before it parses the
    // first modular weapon, so these are the base indexes that may cross the
    // wire. A dedicated map reset rebuilds its private registry in a different
    // order; callers must translate the matching alpha name back to this index
    // instead of exposing that process-local slot to clients.
    inline constexpr std::uint16_t AlphaWeaponNetworkBaseIndex = 1224;
    [[nodiscard]] std::optional<std::uint16_t>
        SV_AlphaWeaponNetworkAssetIndex(std::string_view name) noexcept;

    // CODREF(OLfinal 0x76B7C0): StringTable cells cache this lowercase
    // polynomial hash beside their text pointer. Alias model tables must
    // update both halves of column zero.
    [[nodiscard]] std::uint32_t SV_StringTableHash(
        std::string_view value) noexcept;

    // Clone bytes already copied from an OLfinal WeaponDef are patched in
    // place. `persistentNameAddress` must name storage that remains alive for
    // the resulting DB entry; the retained linker copies the structure but
    // deliberately keeps its pointer-bearing members shallow.
    [[nodiscard]] bool SV_PatchAlphaWeaponDefinition(
        std::span<std::byte> definition,
        std::uint32_t persistentNameAddress,
        const SvAlphaWeaponTuning &tuning) noexcept;
}
