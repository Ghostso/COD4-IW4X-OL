#include "sv_alpha_barrett_assets_mp.hpp"

#include <algorithm>
#include <fstream>
#include <limits>
#include <map>
#include <nlohmann/json.hpp>
#include <set>
#include <span>
#include <stdexcept>
#include <string_view>

namespace CodolGameServer
{
    namespace
    {
        using Json = nlohmann::json;

        constexpr std::array<std::array<std::string_view, 4>, 4> ModelRows{{
            { "barrett_mp", "0", "wea_barrett_barrett_blk",
              "wea_barrett_barrett_blk_vmgun" },
            { "barrett_mp", "1", "wea_barrett_barrett_01",
              "wea_barrett_barrett_01_vmgun" },
            { "barrett_mp", "2", "wea_barrett_barrett_02",
              "wea_barrett_barrett_02_vmgun" },
            { "barrett_mp", "3", "wea_barrett_barrett_03",
              "wea_barrett_barrett_03_vmgun" },
        }};

        constexpr std::string_view SourceZoneSha256 =
            "f39e86d5023402f62187a4f4c524f937c91dc07a98785d8a648feba024da9d9b";

        constexpr std::array<std::string_view, 17> ImageNames{
            "alpha_barrett_weapon_detail_01",
            "alpha_barrett_weapon_detail_02",
            "alpha_barrett_weapon_detail_03",
            "alpha_barrett_weapon_detail_blk",
            "detail_gray_01",
            "wea_barrett_barrett_col",
            "wea_barrett_barrett_nml",
            "weapon_m82_new_col",
            "weapon_m82_new_nml",
            "weapon_wa2000_scope_col",
            "weapon_wa2000_scope_lens_col",
            "weapon_wa2000_scope_lens_nrml",
            "weapon_wa2000_scope_nrml",
            "~wea_barrett_barrett_spc-rgb&~8223d6af",
            "~weapon_m82_new_spc-rgb&weapo~b701ea82",
            "~weapon_wa2000_scope_lens_spe~2f1c4f36",
            "~weapon_wa2000_scope_spec-rgb~0b29b7ff",
        };

        constexpr std::array<std::string_view, 17> ImageSourceNames{
            "weapon_detail_01",
            "weapon_detail_02",
            "weapon_detail_03",
            "weapon_detail_blk",
            "detail_gray_01",
            "wea_barrett_barrett_col",
            "wea_barrett_barrett_nml",
            "weapon_m82_new_col",
            "weapon_m82_new_nml",
            "weapon_wa2000_scope_col",
            "weapon_wa2000_scope_lens_col",
            "weapon_wa2000_scope_lens_nrml",
            "weapon_wa2000_scope_nrml",
            "~wea_barrett_barrett_spc-rgb&~8223d6af",
            "~weapon_m82_new_spc-rgb&weapo~b701ea82",
            "~weapon_wa2000_scope_lens_spe~2f1c4f36",
            "~weapon_wa2000_scope_spec-rgb~0b29b7ff",
        };

        constexpr std::array<std::uint8_t, 17> ImageSemantics{
            3, 3, 3, 3, 3, 2, 5, 2, 5, 2, 2, 5, 5, 8, 8, 8, 8,
        };

        constexpr std::array<std::string_view, 9> MaterialNames{
            "mc/mtl_wea_barrett_barrett_01",
            "mc/mtl_wea_barrett_barrett_02",
            "mc/mtl_wea_barrett_barrett_03",
            "mc/mtl_wea_barrett_barrett_blk",
            "mc/mtl_weapon_m82",
            "mc/mtl_weapon_m82_muzzle_tip",
            "mc/mtl_weapon_m82_trans",
            "mc/mtl_weapon_wa2000_scope",
            "mc/mtl_weapon_wa2000_scope_lens",
        };

        constexpr std::array<std::string_view, 15> RetainedMaterialNames{
            "mc/mtl_motion_tracker_screen",
            "mc/mtl_weapon_acog_2",
            "mc/mtl_weapon_acog_2_lens",
            "mc/mtl_weapon_acog_2_lens_world",
            "mc/mtl_weapon_acog_2_reticle",
            "mc/mtl_weapon_acog_2_reticle_base",
            "mc/mtl_weapon_acog_lens2",
            "mc/mtl_weapon_motion_tracker",
            "mc/mtl_weapon_suppressor_b",
            "mc/mtl_weapon_thermal_lens",
            "mc/mtl_weapon_thermal_lens_2",
            "mc/mtl_weapon_thermal_screen",
            "mc/mtl_weapon_thermal_screen_off",
            "mc/mtl_weapon_thermal_screen_scanlines",
            "mc/mtl_weapon_thermal_sight_2",
        };

        constexpr std::array<std::string_view, 0> RetainedImageNames{};

        constexpr std::array<std::pair<std::string_view, std::string_view>, 15>
            AnimationNames{{
                { "alpha_barrett_idle", "viewmodel_barrett_idle" },
                { "alpha_barrett_fire", "viewmodel_barrett_fire" },
                { "alpha_barrett_reload", "viewmodel_barrett_reload" },
                { "alpha_barrett_reload_empty", "viewmodel_barrett_reload_empty" },
                { "alpha_barrett_pullout", "viewmodel_barrett_pullout" },
                { "alpha_barrett_breach", "viewmodel_barrett_breach" },
                { "alpha_barrett_putaway", "viewmodel_barrett_putaway" },
                { "alpha_barrett_pullout_quick", "viewmodel_barrett_pullout_quick" },
                { "alpha_barrett_putaway_quick", "viewmodel_barrett_putaway_quick" },
                { "alpha_barrett_sprint_in", "viewmodel_barrett_sprint_in" },
                { "alpha_barrett_sprint_loop", "viewmodel_barrett_sprint_loop" },
                { "alpha_barrett_sprint_out", "viewmodel_barrett_sprint_out" },
                { "alpha_barrett_ads_fire", "viewmodel_barrett_ads_fire" },
                { "alpha_barrett_ads_up", "viewmodel_barrett_ads_up" },
                { "alpha_barrett_ads_down", "viewmodel_barrett_ads_down" },
            }};

        constexpr std::array<std::string_view, 1> ViewmodelResources{
            "viewmodel_m8210",
        };
        constexpr std::array<std::string_view, 3> WeaponResources{
            "weapon_m82_lod010", "weapon_m82_lod110", "weapon_m82_lod210",
        };
        constexpr std::array<std::string_view, 3> ModularWorldResources{
            "wea_barrett_barrett_lod010", "wea_barrett_barrett_lod110",
            "wea_barrett_barrett_lod210",
        };
        constexpr std::array<std::string_view, 1> ModularViewResources{
            "wea_barrett_barrett_vmgun10",
        };

        struct ModelSpec
        {
            std::string_view name;
            std::string_view kind;
            std::string_view skeleton;
            std::size_t bones;
            std::size_t roots;
            std::size_t surfaces;
            std::size_t lods;
            std::span<const std::string_view> resources;
        };

        const std::array<ModelSpec, 10> ModelSpecs{{
            { "viewmodel_barrett", "weapon_view", "weapon_view",
              29, 1, 22, 1, ViewmodelResources },
            { "weapon_m82", "weapon_world", "weapon_world",
              11, 1, 38, 3, WeaponResources },
            { "wea_barrett_barrett_blk", "modular_world", "modular_world",
              15, 1, 3, 3, ModularWorldResources },
            { "wea_barrett_barrett_blk_vmgun", "modular_view", "modular_view",
              20, 1, 2, 1, ModularViewResources },
            { "wea_barrett_barrett_01", "modular_world", "modular_world",
              15, 1, 3, 3, ModularWorldResources },
            { "wea_barrett_barrett_01_vmgun", "modular_view", "modular_view",
              20, 1, 2, 1, ModularViewResources },
            { "wea_barrett_barrett_02", "modular_world", "modular_world",
              15, 1, 3, 3, ModularWorldResources },
            { "wea_barrett_barrett_02_vmgun", "modular_view", "modular_view",
              20, 1, 2, 1, ModularViewResources },
            { "wea_barrett_barrett_03", "modular_world", "modular_world",
              15, 1, 3, 3, ModularWorldResources },
            { "wea_barrett_barrett_03_vmgun", "modular_view", "modular_view",
              20, 1, 2, 1, ModularViewResources },
        }};

        const std::map<std::string_view, std::uint32_t, std::less<>>
            MaterialTechniquePointers{
                { "mc/mtl_weapon_wa2000_scope", 0x3000442Du },
                { "mc/mtl_weapon_wa2000_scope_lens", 0x3000450Du },
                { "mc/mtl_weapon_m82_trans", 0x3000450Du },
                { "mc/mtl_weapon_m82", 0x3000440Du },
                { "mc/mtl_weapon_m82_muzzle_tip", 0x3000440Du },
                { "mc/mtl_wea_barrett_barrett_blk", 0x3000440Du },
                { "mc/mtl_wea_barrett_barrett_01", 0x3000440Du },
                { "mc/mtl_wea_barrett_barrett_02", 0x3000440Du },
                { "mc/mtl_wea_barrett_barrett_03", 0x3000440Du },
            };

        std::uint32_t readU32(
            const std::span<const std::byte> bytes,
            const std::size_t offset)
        {
            if (offset + 4 > bytes.size())
                throw std::runtime_error("metadata u32 is out of range");
            return static_cast<std::uint32_t>(bytes[offset]) |
                static_cast<std::uint32_t>(bytes[offset + 1]) << 8 |
                static_cast<std::uint32_t>(bytes[offset + 2]) << 16 |
                static_cast<std::uint32_t>(bytes[offset + 3]) << 24;
        }

        std::uint16_t readU16(
            const std::span<const std::byte> bytes,
            const std::size_t offset)
        {
            if (offset + 2 > bytes.size())
                throw std::runtime_error("metadata u16 is out of range");
            return static_cast<std::uint16_t>(bytes[offset]) |
                static_cast<std::uint16_t>(bytes[offset + 1]) << 8;
        }

        void writeU32(
            const std::span<std::byte> bytes,
            const std::size_t offset,
            const std::uint32_t value)
        {
            if (offset + 4 > bytes.size())
                throw std::runtime_error("metadata u32 write is out of range");
            for (std::size_t index{}; index < 4; ++index)
            {
                bytes[offset + index] = static_cast<std::byte>(
                    value >> (index * 8));
            }
        }

        std::uint8_t nibble(const char character)
        {
            if (character >= '0' && character <= '9')
                return static_cast<std::uint8_t>(character - '0');
            if (character >= 'a' && character <= 'f')
                return static_cast<std::uint8_t>(character - 'a' + 10);
            if (character >= 'A' && character <= 'F')
                return static_cast<std::uint8_t>(character - 'A' + 10);
            throw std::runtime_error("metadata contains non-hexadecimal data");
        }

        std::uint32_t hexU32(const Json &value, const std::string_view field)
        {
            if (!value.is_string())
                throw std::runtime_error(std::string(field) + " is not text");
            const auto text = value.get<std::string>();
            if (text.size() != 10 || text[0] != '0' || text[1] != 'x')
                throw std::runtime_error(std::string(field) + " is not 0xXXXXXXXX");
            std::uint32_t result{};
            for (std::size_t index = 2; index < text.size(); ++index)
                result = result << 4 | nibble(text[index]);
            return result;
        }

        std::vector<std::byte> decodeHex(
            const Json &value,
            const std::string_view field,
            const std::optional<std::size_t> exactSize = std::nullopt)
        {
            if (!value.is_string())
                throw std::runtime_error(std::string(field) + " is not text");
            const auto text = value.get<std::string>();
            if (text.size() & 1)
                throw std::runtime_error(std::string(field) + " has odd hex length");
            if (exactSize && text.size() != *exactSize * 2)
                throw std::runtime_error(std::string(field) + " has the wrong size");
            std::vector<std::byte> result(text.size() / 2);
            for (std::size_t index{}; index < result.size(); ++index)
            {
                result[index] = static_cast<std::byte>(
                    nibble(text[index * 2]) << 4 |
                    nibble(text[index * 2 + 1]));
            }
            return result;
        }

        template <std::size_t Size>
        std::array<std::byte, Size> decodeArray(
            const Json &value, const std::string_view field)
        {
            const auto bytes = decodeHex(value, field, Size);
            std::array<std::byte, Size> result{};
            std::ranges::copy(bytes, result.begin());
            return result;
        }

        std::string textField(const Json &object, const char *const name)
        {
            if (!object.contains(name) || !object.at(name).is_string())
                throw std::runtime_error(std::string("missing text field ") + name);
            const auto value = object.at(name).get<std::string>();
            if (value.empty() || value.find('\0') != std::string::npos)
                throw std::runtime_error(std::string("invalid text field ") + name);
            return value;
        }

        template <std::size_t Size>
        bool exactStrings(
            const std::vector<std::string> &actual,
            const std::array<std::string_view, Size> &expected)
        {
            return actual.size() == expected.size() &&
                std::ranges::equal(actual, expected);
        }

        const ModelSpec &modelSpec(const std::string_view name)
        {
            const auto iterator = std::ranges::find(
                ModelSpecs, name, &ModelSpec::name);
            if (iterator == ModelSpecs.end())
                throw std::runtime_error(std::string(name) + " is an unknown Barrett model");
            return *iterator;
        }

        SvAlphaBarrettSkeleton parseSkeleton(
            const Json &source, const std::size_t boneCount,
            const std::size_t rootCount)
        {
            SvAlphaBarrettSkeleton skeleton;
            skeleton.boneNames = source.at("bone_names").get<std::vector<std::string>>();
            const auto childCount = boneCount - rootCount;
            if (skeleton.boneNames.size() != boneCount ||
                std::ranges::any_of(skeleton.boneNames,
                    [](const std::string &name) { return name.empty(); }))
            {
                throw std::runtime_error("Barrett skeleton has invalid bone names");
            }
            skeleton.parentList = decodeHex(
                source.at("parent_list_hex"), "parent_list_hex", childCount);
            skeleton.quaternions = decodeHex(
                source.at("quats_hex"), "quats_hex", childCount * 8);
            skeleton.translations = decodeHex(
                source.at("translations_hex"), "translations_hex", childCount * 12);
            skeleton.partClassification = decodeHex(
                source.at("part_classification_hex"),
                "part_classification_hex", boneCount);
            skeleton.baseMatrices = decodeHex(
                source.at("base_matrices_hex"),
                "base_matrices_hex", boneCount * 32);
            // bone_name_indices_hex is retained as provenance but never used:
            // script-string indices are process-local and must be interned by name.
            static_cast<void>(decodeHex(source.at("bone_name_indices_hex"),
                "bone_name_indices_hex", boneCount * 2));
            return skeleton;
        }

        void validateModelHeader(
            const SvAlphaBarrettModel &model,
            const std::size_t boneCount,
            const std::size_t rootCount,
            const std::size_t surfaceCount,
            const std::size_t lodCount)
        {
            const auto bytes = std::span{ model.header };
            if (static_cast<std::uint8_t>(bytes[4]) != boneCount ||
                static_cast<std::uint8_t>(bytes[5]) != rootCount ||
                static_cast<std::uint8_t>(bytes[6]) != surfaceCount ||
                static_cast<std::uint8_t>(bytes[297]) != lodCount)
            {
                throw std::runtime_error(model.name + " has invalid XModel counts");
            }
            for (const auto offset : {
                     0u, 44u, 48u, 52u, 56u, 60u, 64u, 68u,
                     300u, 312u, 352u, 356u })
            {
                if (readU32(bytes, offset))
                    throw std::runtime_error(model.name + " has a live header pointer");
            }
            for (std::size_t lod{}; lod < 4; ++lod)
            {
                const auto start = 72 + lod * 56;
                for (const auto relative : { 8u, 12u, 48u })
                {
                    if (readU32(bytes, start + relative))
                        throw std::runtime_error(model.name + " has a live LOD pointer");
                }
            }
        }

        SvAlphaBarrettAnimation parseAnimation(
            const Json &source, const std::size_t index)
        {
            if (index >= AnimationNames.size())
                throw std::runtime_error("too many Barrett animations");
            SvAlphaBarrettAnimation animation;
            animation.name = textField(source, "name");
            animation.sourceName = textField(source, "source_name");
            if (animation.name != AnimationNames[index].first ||
                animation.sourceName != AnimationNames[index].second)
            {
                throw std::runtime_error("Barrett animation closure differs");
            }
            animation.header = decodeArray<88>(
                source.at("alpha_header_hex"), "alpha_header_hex");
            for (const auto offset : {
                     0u, 48u, 52u, 56u, 60u, 64u, 68u, 72u, 76u, 80u, 84u })
            {
                if (readU32(animation.header, offset))
                    throw std::runtime_error(
                        animation.name + " has a live header pointer");
            }
            const auto &presence = source.at("pointer_presence");
            if (!presence.is_array() || presence.size() != 10)
                throw std::runtime_error("invalid XAnim pointer presence");
            for (std::size_t pointer{}; pointer < 10; ++pointer)
            {
                if (!presence[pointer].is_boolean())
                    throw std::runtime_error("invalid XAnim pointer presence");
                animation.pointerPresence[pointer] =
                    presence[pointer].get<bool>();
            }
            if (animation.pointerPresence[9])
                throw std::runtime_error(animation.name + " has a delta part");

            animation.boneNames =
                source.at("bone_names").get<std::vector<std::string>>();
            animation.notifyNames =
                source.at("notify_names").get<std::vector<std::string>>();
            animation.notify = decodeHex(source.at("notify_hex"), "notify_hex");
            animation.dataByte = decodeHex(
                source.at("data_byte_hex"), "data_byte_hex");
            animation.dataShort = decodeHex(
                source.at("data_short_hex"), "data_short_hex");
            animation.dataInt = decodeHex(
                source.at("data_int_hex"), "data_int_hex");
            animation.randomDataShort = decodeHex(
                source.at("random_data_short_hex"), "random_data_short_hex");
            animation.randomDataByte = decodeHex(
                source.at("random_data_byte_hex"), "random_data_byte_hex");
            animation.randomDataInt = decodeHex(
                source.at("random_data_int_hex"), "random_data_int_hex");
            animation.indices = decodeHex(
                source.at("indices_hex"), "indices_hex");

            const auto bytes = std::span{ animation.header };
            const auto boneCount = static_cast<std::uint8_t>(bytes[26]);
            const auto notifyCount = static_cast<std::uint8_t>(bytes[27]);
            const auto frames = readU16(bytes, 14);
            const auto expectedIndexBytes = readU32(bytes, 36) *
                (frames >= 256 ? 2u : 1u);
            if (static_cast<std::uint8_t>(bytes[28]) != 1 ||
                static_cast<std::uint8_t>(bytes[29]) != 0 ||
                animation.boneNames.size() != boneCount ||
                animation.notifyNames.size() != notifyCount ||
                animation.notify.size() != notifyCount * 8u ||
                animation.dataByte.size() != readU16(bytes, 4) ||
                animation.dataShort.size() != readU16(bytes, 6) * 2u ||
                animation.dataInt.size() != readU16(bytes, 8) * 4u ||
                animation.randomDataByte.size() != readU16(bytes, 10) ||
                animation.randomDataInt.size() != readU16(bytes, 12) * 4u ||
                animation.randomDataShort.size() != readU32(bytes, 32) * 2u ||
                animation.indices.size() != expectedIndexBytes)
            {
                throw std::runtime_error(
                    animation.name + " has inconsistent XAnim streams");
            }
            std::size_t rotations{};
            std::size_t translations{};
            for (std::size_t part{}; part < 5; ++part)
                rotations += static_cast<std::uint8_t>(bytes[17 + part]);
            for (std::size_t part = 5; part < 9; ++part)
                translations += static_cast<std::uint8_t>(bytes[17 + part]);
            if (rotations != boneCount || translations != boneCount ||
                std::ranges::any_of(animation.boneNames,
                    [](const std::string &value) { return value.empty(); }) ||
                std::ranges::any_of(animation.notifyNames,
                    [](const std::string &value) { return value.empty(); }))
            {
                throw std::runtime_error(
                    animation.name + " has invalid XAnim script strings");
            }
            for (std::size_t offset{}; offset < animation.notify.size();
                 offset += 8)
            {
                if (readU16(animation.notify, offset))
                    throw std::runtime_error(
                        animation.name + " retains alpha notify indices");
            }
            const std::array<std::size_t, 9> streamSizes{
                animation.boneNames.size() * 2u,
                animation.dataByte.size(), animation.dataShort.size(),
                animation.dataInt.size(), animation.randomDataShort.size(),
                animation.randomDataByte.size(), animation.randomDataInt.size(),
                animation.indices.size(), animation.notify.size(),
            };
            for (std::size_t pointer{}; pointer < streamSizes.size(); ++pointer)
            {
                if (streamSizes[pointer] && !animation.pointerPresence[pointer])
                    throw std::runtime_error(
                        animation.name + " omits a non-empty XAnim pointer");
            }
            return animation;
        }
    }

    std::span<const std::array<std::string_view, 4>>
        SV_AlphaBarrettModelTable() noexcept
    {
        return ModelRows;
    }

    bool SV_BuildOlfinalAlphaBarrettImage(
        const SvAlphaBarrettImage &source,
        const std::uint32_t loadDefAddress,
        const std::uint32_t nameAddress,
        std::array<std::byte, AlphaBarrettOlfinalGfxImageSize> &header,
        std::array<std::byte, 16> &loadDef) noexcept
    {
        if (!loadDefAddress || !nameAddress ||
            readU32(source.alphaHeader, 0) ||
            readU32(source.alphaHeader, 28) ||
            !readU16(source.alphaHeader, 20) ||
            !readU16(source.alphaHeader, 22) ||
            !readU16(source.alphaHeader, 24) ||
            readU32(source.alphaLoadDef, 12))
        {
            return false;
        }

        header.fill(std::byte{});
        loadDef = source.alphaLoadDef;
        std::copy_n(source.alphaHeader.begin() + 4, 8, header.begin() + 4);
        std::copy_n(source.alphaHeader.begin() + 20, 7, header.begin() + 32);
        header[40] = source.alphaHeader[27];
        writeU32(header, 0, loadDefAddress);
        writeU32(header, 48, nameAddress);
        return true;
    }

    bool SV_OlfinalAlphaBarrettMaterialLayoutCompatible(
        const SvAlphaBarrettMaterial &source,
        const std::span<const std::byte, AlphaBarrettOlfinalMaterialSize> finalTemplate)
        noexcept
    {
        return std::equal(
                   source.alphaHeader.begin() + 16,
                   source.alphaHeader.begin() + 22,
                   finalTemplate.begin() + 20) &&
            source.alphaHeader[4] == finalTemplate[26] &&
            std::equal(
                source.alphaHeader.begin() + 5,
                source.alphaHeader.begin() + 8,
                finalTemplate.begin() + 28) &&
            std::equal(
                source.alphaHeader.begin() + 24,
                source.alphaHeader.begin() + 72,
                finalTemplate.begin() + 32) &&
            std::equal(
                source.alphaHeader.begin() + 72,
                source.alphaHeader.begin() + 79,
                finalTemplate.begin() + 81);
    }

    bool SV_BuildOlfinalAlphaBarrettMaterial(
        const SvAlphaBarrettMaterial &source,
        const std::span<const std::byte, AlphaBarrettOlfinalMaterialSize> finalTemplate,
        const std::uint32_t nameAddress,
        const std::uint32_t textureTableAddress,
        const std::uint32_t constantTableAddress,
        const std::uint32_t stateBitsTableAddress,
        std::array<std::byte, AlphaBarrettOlfinalMaterialSize> &header) noexcept
    {
        if (!nameAddress ||
            (source.textures.empty() != (textureTableAddress == 0)) ||
            (source.constants.empty() != (constantTableAddress == 0)) ||
            (source.stateBits.empty() != (stateBitsTableAddress == 0)) ||
            source.textures.size() > std::numeric_limits<std::uint8_t>::max() ||
            source.constants.size() % 32 || source.stateBits.size() % 8 ||
            source.textures.size() !=
                static_cast<std::uint8_t>(source.alphaHeader[72]) ||
            source.constants.size() / 32 !=
                static_cast<std::uint8_t>(source.alphaHeader[73]) ||
            source.stateBits.size() / 8 !=
                static_cast<std::uint8_t>(source.alphaHeader[74]) ||
            !SV_OlfinalAlphaBarrettMaterialLayoutCompatible(
                source, finalTemplate))
        {
            return false;
        }

        std::ranges::copy(finalTemplate, header.begin());
        writeU32(header, 16, nameAddress);
        writeU32(header, 92, textureTableAddress);
        writeU32(header, 96, constantTableAddress);
        writeU32(header, 100, stateBitsTableAddress);
        return true;
    }

    std::optional<SvAlphaBarrettBundle> SV_LoadAlphaBarrettBundle(
        const std::filesystem::path &path, std::string &error) noexcept
    {
        error.clear();
        try
        {
            std::ifstream stream(path, std::ios::binary);
            if (!stream)
                throw std::runtime_error("cannot open alpha Barrett metadata");
            const auto root = Json::parse(stream, nullptr, true, true);
            if (textField(root, "format") != "olfinal-alpha-barrett-metadata-v4")
                throw std::runtime_error("unsupported alpha Barrett metadata format");
            if (textField(root, "source_zone") != "ui_viewer_mp.zone" ||
                textField(root, "source_zone_sha256") != SourceZoneSha256)
            {
                throw std::runtime_error("alpha Barrett metadata provenance differs");
            }

            SvAlphaBarrettBundle bundle;
            const auto &table = root.at("model_table");
            if (!table.is_array() || table.size() != ModelRows.size())
                throw std::runtime_error("Barrett model table is not 4x4");
            for (std::size_t row{}; row < ModelRows.size(); ++row)
            {
                if (!table[row].is_array() || table[row].size() != 4)
                    throw std::runtime_error("Barrett model table is not 4x4");
                for (std::size_t column{}; column < 4; ++column)
                {
                    bundle.modelTable[row][column] =
                        table[row][column].get<std::string>();
                    if (bundle.modelTable[row][column] != ModelRows[row][column])
                        throw std::runtime_error("Barrett model table content differs");
                }
            }

            bundle.images = root.at("images").get<std::vector<std::string>>();
            bundle.retainedImages =
                root.at("retained_images").get<std::vector<std::string>>();
            if (!exactStrings(bundle.images, ImageNames) ||
                !exactStrings(bundle.retainedImages, RetainedImageNames))
            {
                throw std::runtime_error("Barrett image closure differs");
            }

            const auto &imageMetadata = root.at("image_metadata");
            if (!imageMetadata.is_array() ||
                imageMetadata.size() != ImageNames.size())
            {
                throw std::runtime_error("Barrett image metadata closure differs");
            }
            for (std::size_t index{}; index < ImageNames.size(); ++index)
            {
                const auto &source = imageMetadata[index];
                SvAlphaBarrettImage image;
                image.name = textField(source, "name");
                image.sourceName = textField(source, "source_name");
                image.alphaHeader = decodeArray<32>(
                    source.at("alpha_header_hex"), "alpha_header_hex");
                image.alphaLoadDef = decodeArray<16>(
                    source.at("alpha_load_def_hex"), "alpha_load_def_hex");
                if (image.name != ImageNames[index] ||
                    image.name != bundle.images[index] ||
                    image.sourceName != ImageSourceNames[index] ||
                    readU32(image.alphaHeader, 0) ||
                    readU32(image.alphaHeader, 28) ||
                    static_cast<std::uint8_t>(image.alphaHeader[4]) != 3 ||
                    static_cast<std::uint8_t>(image.alphaHeader[5]) !=
                        ImageSemantics[index] ||
                    static_cast<std::uint8_t>(image.alphaHeader[6]) != 3 ||
                    !readU16(image.alphaHeader, 20) ||
                    !readU16(image.alphaHeader, 22) ||
                    !readU16(image.alphaHeader, 24) ||
                    readU32(image.alphaLoadDef, 0) ||
                    readU32(image.alphaLoadDef, 4) ||
                    (readU32(image.alphaLoadDef, 8) != 0x31545844u &&
                        readU32(image.alphaLoadDef, 8) != 0x35545844u) ||
                    readU32(image.alphaLoadDef, 12))
                {
                    throw std::runtime_error(
                        image.name + " has invalid GfxImage metadata");
                }
                bundle.imageMetadata.push_back(std::move(image));
            }

            const auto &skeletons = root.at("skeletons");
            if (!skeletons.is_object() || skeletons.size() != 4)
                throw std::runtime_error("Barrett skeleton closure differs");
            for (const auto &[key, bones] : {
                     std::pair{ "weapon_view", 29u },
                     std::pair{ "weapon_world", 11u },
                     std::pair{ "modular_view", 20u },
                     std::pair{ "modular_world", 15u },
                 })
            {
                bundle.skeletons.emplace(
                    key, parseSkeleton(skeletons.at(key), bones, 1));
            }

            bundle.retainedMaterials =
                root.at("retained_materials").get<std::vector<std::string>>();
            if (!exactStrings(bundle.retainedMaterials, RetainedMaterialNames))
                throw std::runtime_error("retained Barrett material closure differs");

            std::set<std::string, std::less<>> materialNames;
            for (const auto &source : root.at("materials"))
            {
                SvAlphaBarrettMaterial material;
                material.name = textField(source, "name");
                material.cloneSource = textField(source, "clone_source");
                material.alphaTechniquePointer = hexU32(
                    source.at("alpha_technique_pointer"),
                    "alpha_technique_pointer");
                material.alphaHeader = decodeArray<96>(
                    source.at("alpha_header_hex"), "alpha_header_hex");
                for (const auto offset : { 0u, 80u, 84u, 88u, 92u })
                {
                    if (readU32(material.alphaHeader, offset))
                        throw std::runtime_error(material.name + " has a live pointer");
                }
                for (const auto &textureSource : source.at("textures"))
                {
                    material.textures.push_back({
                        decodeArray<8>(textureSource.at("slot_header_hex"),
                            "slot_header_hex"),
                        textField(textureSource, "image"),
                    });
                }
                material.constants = decodeHex(
                    source.at("constants_hex"), "constants_hex");
                material.stateBits = decodeHex(
                    source.at("state_bits_hex"), "state_bits_hex");
                const auto technique = MaterialTechniquePointers.find(material.name);
                const auto expectedCloneSource =
                    material.name == "mc/mtl_weapon_wa2000_scope_lens" ||
                        material.name == "mc/mtl_weapon_m82_trans"
                    ? "mc/mtl_weapon_acog_2_alpha"
                    : material.name == "mc/mtl_weapon_wa2000_scope"
                    ? "mc/mtl_wea_javelin_javelin_lens"
                    : "mc/mtl_weapon_m16";
                if (material.cloneSource != expectedCloneSource ||
                    technique == MaterialTechniquePointers.end() ||
                    material.alphaTechniquePointer != technique->second ||
                    material.textures.size() !=
                        static_cast<std::uint8_t>(material.alphaHeader[72]) ||
                    material.constants.size() !=
                        static_cast<std::uint8_t>(material.alphaHeader[73]) * 32u ||
                    material.stateBits.size() !=
                        static_cast<std::uint8_t>(material.alphaHeader[74]) * 8u ||
                    !materialNames.insert(material.name).second)
                {
                    throw std::runtime_error(material.name + " has invalid tables");
                }
                for (const auto &texture : material.textures)
                {
                    if (!std::ranges::contains(bundle.images, texture.image) &&
                        !std::ranges::contains(bundle.retainedImages, texture.image))
                    {
                        throw std::runtime_error(
                            material.name + " names an unclosed texture image");
                    }
                }
                bundle.materials.push_back(std::move(material));
            }
            const std::set<std::string, std::less<>> expectedMaterialNames(
                MaterialNames.begin(), MaterialNames.end());
            if (materialNames != expectedMaterialNames)
                throw std::runtime_error("constructed Barrett material closure differs");

            std::set<std::string, std::less<>> availableMaterials =
                expectedMaterialNames;
            availableMaterials.insert(
                bundle.retainedMaterials.begin(), bundle.retainedMaterials.end());

            std::set<std::string> modelNames;
            for (const auto &source : root.at("models"))
            {
                SvAlphaBarrettModel model;
                model.name = textField(source, "name");
                model.kind = textField(source, "kind");
                model.skeletonKey = textField(source, "skeleton_key");
                model.materials =
                    source.at("materials").get<std::vector<std::string>>();
                model.header = decodeArray<360>(
                    source.at("header_hex"), "header_hex");
                model.resources = source.at("resources").get<std::vector<std::string>>();
                model.boneInfo = decodeHex(source.at("bone_info_hex"), "bone_info_hex");
                const auto &spec = modelSpec(model.name);
                if (model.kind != spec.kind ||
                    model.skeletonKey != spec.skeleton ||
                    model.materials.size() != spec.surfaces ||
                    std::ranges::any_of(model.materials,
                        [&availableMaterials](const std::string &name) {
                            return !availableMaterials.contains(name);
                        }) ||
                    model.resources.size() != spec.resources.size() ||
                    !std::ranges::equal(model.resources, spec.resources) ||
                    model.boneInfo.size() != spec.bones * 28u ||
                    !modelNames.insert(model.name).second)
                {
                    throw std::runtime_error(model.name + " has invalid model metadata");
                }
                validateModelHeader(
                    model, spec.bones, spec.roots, spec.surfaces, spec.lods);
                bundle.models.push_back(std::move(model));
            }
            if (bundle.models.size() != ModelSpecs.size())
                throw std::runtime_error("Barrett model closure differs");
            for (const auto &spec : ModelSpecs)
            {
                if (!modelNames.contains(std::string(spec.name)))
                    throw std::runtime_error("Barrett metadata omits a required model");
            }
            for (const auto &row : ModelRows)
            {
                for (const auto column : { 2u, 3u })
                {
                    if (!modelNames.contains(std::string(row[column])))
                        throw std::runtime_error("Barrett model table names a missing model");
                }
            }

            const auto &animations = root.at("animations");
            if (!animations.is_array() ||
                animations.size() != AnimationNames.size())
            {
                throw std::runtime_error("Barrett animation closure differs");
            }
            bundle.animations.reserve(animations.size());
            for (std::size_t index{}; index < animations.size(); ++index)
                bundle.animations.push_back(parseAnimation(animations[index], index));
            return bundle;
        }
        catch (const std::exception &exception)
        {
            error = exception.what();
            return std::nullopt;
        }
    }
}
