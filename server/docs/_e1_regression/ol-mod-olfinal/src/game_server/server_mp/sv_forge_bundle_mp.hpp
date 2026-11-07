#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace CodolGameServer
{
    // OLMOD(forge-bundle): the publishable description CodolForge writes beside
    // a staging run (`bundle.json`). It is the CoD4 counterpart to the alpha
    // Barrett bundle: same key vocabulary, but generic over whatever the source
    // folder held rather than pinned to one weapon's closure.
    //
    // Mesh bytes and IWI bytes never enter this object. They go to the loose
    // overlay as `main/models/<resource>` and `main/images/<image>.iwi`; this
    // carries only what has to become a ZONE asset through the retained
    // DB_LinkXAssetEntry - the XModel, its skeleton, and the materials.
    //
    // CODREF(xmodel): OLfinal Load_XModel 0x489B20 reads 360 bytes.
    //   +4 u8 numBones (TOTAL)  +5 u8 numRootBones  +6 u8 numsurfs
    //   +44 boneNames  +48 parentList  +52 quats  +56 trans
    //   +60 partClassification  +64 baseMat (DObjAnimMat, 32 bytes)
    //   +72 XModelLodInfo[4], 56 bytes each; lodInfo[0].name is the loose
    //       resource name and lodInfo[0].numsurfs must equal its surface count.
    // parentList / quats / trans cover the NON-ROOT bones only; boneNames,
    // partClassification and baseMat cover all of them.
    struct SvForgeSkeleton
    {
        std::vector<std::string> boneNames;
        std::vector<std::byte> parentList;
        std::vector<std::byte> quaternions;
        std::vector<std::byte> translations;
        std::vector<std::byte> partClassification;
        std::vector<std::byte> baseMatrices;

        [[nodiscard]] std::size_t boneCount() const noexcept
        {
            return boneNames.size();
        }
        [[nodiscard]] std::size_t rootBoneCount() const noexcept
        {
            return boneNames.size() - parentList.size();
        }
    };

    struct SvForgeTexture
    {
        std::string semantic;
        std::string image;
    };

    // CODREF(material): OLfinal Load_Material 0x488250 reads 104 bytes, with
    // textureCount at +81 and a 12-byte MaterialTextureDef table at +92. The
    // first eight bytes of each entry - nameHash, nameStart, nameEnd,
    // samplerState, semantic - are produced by the asset pipeline and appear
    // nowhere in the client, so they must be COPIED from `cloneSource` rather
    // than recomputed. Only MaterialTextureDef.image is replaced.
    struct SvForgeMaterial
    {
        std::string name;
        std::string cloneSource;
        std::vector<SvForgeTexture> textures;
    };

    struct SvForgeModel
    {
        std::string name;
        std::string skeletonKey;
        std::array<std::byte, 360> header{};
        std::vector<std::string> resources;
        std::vector<std::string> materials;
    };

    // CODREF(xanim): OLfinal Load_XAnimParts 0x485B40 reads 88 bytes. The emitted
    // asset is complete EXCEPT its `names` array (+48) and its notify names, which
    // are u16 SCRIPT STRING indices - the client interns them per zone through
    // `sub_74BD10(str, kind 4, len)` at out.exe 0x74BD10, so their values cannot be
    // known outside a running client. CodolForge therefore emits zeros there and
    // ships the real strings as text; the publisher resolves and patches them.
    //
    // `bones` is in the asset's own ROTATION part-type order, which is also the
    // order `names` must be patched in, and the index a translation record's
    // bone-index byte carries.
    struct SvForgeAnimation
    {
        std::string name;
        std::string asset;                     // path to the .xanimparts blob
        std::uint16_t numframes = 0;
        bool looping = false;
        std::vector<std::string> bones;
        std::vector<std::string> notifies;
    };

    // The CoD4 weaponfile's raw keys. Mapping them onto OLfinal's enums and
    // millisecond units is SV_ForgeWeaponTuning's job, not the loader's - this
    // only carries them, and only checks that a clone source was named.
    struct SvForgeWeapon
    {
        std::string name;
        std::string cloneSource;
        std::map<std::string, std::string, std::less<>> keys;
    };

    struct SvForgeBundle
    {
        std::map<std::string, SvForgeSkeleton, std::less<>> skeletons;
        std::vector<SvForgeMaterial> materials;
        std::vector<SvForgeModel> models;
        std::vector<std::string> images;
        std::vector<SvForgeAnimation> animations;
        std::vector<SvForgeWeapon> weapons;
    };

    inline constexpr std::size_t OlfinalXModelSize = 360;
    inline constexpr std::size_t OlfinalXAnimPartsSize = 88;
    inline constexpr std::size_t OlfinalMaterialSize = 104;
    inline constexpr std::size_t OlfinalDObjAnimMatSize = 32;

    // Parses and CROSS-CHECKS. A bundle is rejected outright unless every one of
    // these holds, because a half-valid asset closure is worse than none:
    //   * format is "codolforge-bundle-1";
    //   * every model header is exactly 360 bytes;
    //   * header numBones / numRootBones / numsurfs agree with the named
    //     skeleton and the model's material count;
    //   * skeleton array lengths agree with the bone and root counts;
    //   * every material a model names exists in the bundle;
    //   * every image a material names is listed in `images`;
    //   * every model names at least one loose resource;
    //   * every animation has a name, an asset, 1..255 frames, and 1..255 bones
    //     whose names are non-empty and DISTINCT - they are slots, so a repeat
    //     would silently make one bone unaddressable. 256 frames or more is
    //     rejected outright: that is the u16 index path, which the emitter does
    //     not produce;
    //   * every weapon has a name, a clone source, and at least one key - a
    //     WeaponDef is published by CLONING a shipped one, so a port with no
    //     source to clone from cannot be built at all.
    [[nodiscard]] std::optional<SvForgeBundle> SV_LoadForgeBundle(
        const std::filesystem::path &path,
        std::string &error) noexcept;
}
