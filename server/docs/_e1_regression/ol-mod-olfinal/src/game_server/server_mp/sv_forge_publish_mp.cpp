#include "sv_forge_publish_mp.hpp"

#include <cstring>
#include <algorithm>
#include <iterator>
#include <stdexcept>
#include <string>
#include <fstream>
#include <memory>

#ifdef _WIN32
#include <Windows.h>
#endif

namespace CodolGameServer
{
    namespace
    {
        // Every pointer written into an asset is four bytes, because the client is
        // x86 and the RVAs below are x86 offsets. On a 64-bit build the writes
        // would silently truncate and the engine would follow half an address, so
        // fail the build instead.
        static_assert(sizeof(void *) == 4,
            "the forge publication path targets the 32-bit client");

        constexpr std::size_t XAnimPartsSize = 88;
        constexpr std::uint32_t InlineFollows = 0xFFFFFFFFu;

        // Field offsets, read off Load_XAnimParts' own disassembly rather than
        // transferred from IW4 notes.
        constexpr std::size_t OffName = 0;
        constexpr std::size_t OffDataByteCount = 4;
        constexpr std::size_t OffDataShortCount = 6;
        constexpr std::size_t OffDataIntCount = 8;
        constexpr std::size_t OffRandomDataByteCount = 10;
        constexpr std::size_t OffRandomDataIntCount = 12;
        constexpr std::size_t OffNumframes = 14;
        constexpr std::size_t OffBoneCount = 26;
        constexpr std::size_t OffNotifyCount = 27;
        constexpr std::size_t OffRandomDataShortCount = 32;
        constexpr std::size_t OffIndexCount = 36;
        constexpr std::size_t OffNames = 48;
        constexpr std::size_t OffDataByte = 52;
        constexpr std::size_t OffDataShort = 56;
        constexpr std::size_t OffDataInt = 60;
        constexpr std::size_t OffRandomDataShort = 64;
        constexpr std::size_t OffRandomDataByte = 68;
        constexpr std::size_t OffRandomDataInt = 72;
        constexpr std::size_t OffIndices = 76;
        constexpr std::size_t OffNotify = 80;
        constexpr std::size_t OffDeltaPart = 84;

        constexpr std::size_t NotifyStride = 8;   // u16 name, u16 pad, float time

        std::uint16_t readU16(const std::byte *const d, const std::size_t o) noexcept
        {
            return static_cast<std::uint16_t>(
                std::to_integer<std::uint16_t>(d[o]) |
                (std::to_integer<std::uint16_t>(d[o + 1]) << 8));
        }
        std::uint32_t readU32(const std::byte *const d, const std::size_t o) noexcept
        {
            std::uint32_t v{};
            for (int i = 3; i >= 0; --i)
                v = (v << 8) | std::to_integer<std::uint32_t>(d[o + static_cast<std::size_t>(i)]);
            return v;
        }
        void writeU16(std::byte *const d, const std::size_t o, const std::uint16_t v) noexcept
        {
            d[o] = static_cast<std::byte>(v & 0xFF);
            d[o + 1] = static_cast<std::byte>((v >> 8) & 0xFF);
        }
        void writePointer(std::byte *const d, const std::size_t o, void *const p) noexcept
        {
            const auto v = reinterpret_cast<std::uintptr_t>(p);
            for (std::size_t i = 0; i < sizeof(std::uint32_t); ++i)
                d[o + i] = static_cast<std::byte>((v >> (8 * i)) & 0xFF);
        }
    }

    const char *SV_ForgeXAnimStatusName(const SvForgeXAnimStatus status) noexcept
    {
        switch (status)
        {
        case SvForgeXAnimStatus::Disabled: return "Disabled";
        case SvForgeXAnimStatus::InvalidBlob: return "InvalidBlob";
        case SvForgeXAnimStatus::UnresolvedString: return "UnresolvedString";
        case SvForgeXAnimStatus::MissingBinding: return "MissingBinding";
        case SvForgeXAnimStatus::WrongThread: return "WrongThread";
        case SvForgeXAnimStatus::LinkFailed: return "LinkFailed";
        case SvForgeXAnimStatus::Ready: return "Ready";
        }
        return "?";
    }

    std::optional<SvForgeXAnimAsset> SV_RelocateForgeXAnim(
        const std::span<const std::byte> blob,
        const std::vector<std::string> &boneNames,
        const std::vector<std::string> &notifyNames,
        const SvForgeStringResolver &resolve,
        std::string &error)
    {
        if (blob.size() < XAnimPartsSize)
        {
            error = "blob is " + std::to_string(blob.size()) +
                " bytes, shorter than the 88-byte header";
            return std::nullopt;
        }
        if (!resolve)
        {
            error = "no script-string resolver was supplied";
            return std::nullopt;
        }

        SvForgeXAnimAsset asset;
        asset.storage.assign(blob.begin(), blob.end());
        std::byte *const d = asset.storage.data();

        const auto dataByteCount = readU16(d, OffDataByteCount);
        const auto dataShortCount = readU16(d, OffDataShortCount);
        const auto dataIntCount = readU16(d, OffDataIntCount);
        const auto randomDataByteCount = readU16(d, OffRandomDataByteCount);
        const auto randomDataIntCount = readU16(d, OffRandomDataIntCount);
        const auto numframes = readU16(d, OffNumframes);
        const auto randomDataShortCount = readU32(d, OffRandomDataShortCount);
        const auto indexCount = readU32(d, OffIndexCount);
        asset.boneCount = std::to_integer<std::uint8_t>(d[OffBoneCount]);
        asset.notifyCount = std::to_integer<std::uint8_t>(d[OffNotifyCount]);

        // The emitter refuses to produce either of these, so refuse to relocate
        // one: they would mean a layout this walk does not model.
        if (numframes == 0 || numframes >= 256)
        {
            error = "numframes is " + std::to_string(numframes) + "; expected 1..255";
            return std::nullopt;
        }
        if (indexCount != 0 || readU32(d, OffIndices) != 0)
        {
            error = "indices must be absent below 256 frames";
            return std::nullopt;
        }
        if (readU32(d, OffDeltaPart) != 0)
        {
            error = "deltaPart is not NULL; relocation does not model it";
            return std::nullopt;
        }
        if (randomDataIntCount != 0 || readU32(d, OffRandomDataInt) != 0)
        {
            error = "randomDataInt is not used by any shipped animation";
            return std::nullopt;
        }
        if (asset.boneCount == 0)
        {
            error = "the asset names no bones";
            return std::nullopt;
        }
        if (boneNames.size() != asset.boneCount)
        {
            error = "given " + std::to_string(boneNames.size()) +
                " bone names for an asset with " +
                std::to_string(asset.boneCount) + " bones";
            return std::nullopt;
        }
        if (notifyNames.size() != asset.notifyCount)
        {
            error = "given " + std::to_string(notifyNames.size()) +
                " notify names for an asset with " +
                std::to_string(asset.notifyCount) + " notifies";
            return std::nullopt;
        }

        // Walk the payload in the loader's visit order, rewriting each placeholder
        // into an address inside our own storage.
        std::size_t p = XAnimPartsSize;
        const auto claim = [&](const std::size_t offset, const std::size_t bytes,
                               const char *const what) -> bool {
            const auto placeholder = readU32(d, offset);
            if (placeholder == 0)
            {
                // A NULL array must be empty; a non-empty one must be present.
                if (bytes != 0)
                {
                    error = std::string(what) + " is NULL but its count is not zero";
                    return false;
                }
                return true;
            }
            if (placeholder != InlineFollows)
            {
                error = std::string(what) + " holds an unexpected pointer placeholder";
                return false;
            }
            if (p + bytes > asset.storage.size())
            {
                error = std::string(what) + " runs past the end of the blob";
                return false;
            }
            writePointer(d, offset, d + p);
            p += bytes;
            return true;
        };

        // The asset name is a NUL-terminated string, not a counted array.
        if (readU32(d, OffName) == InlineFollows)
        {
            std::size_t e = p;
            while (e < asset.storage.size() && d[e] != std::byte{0}) ++e;
            if (e >= asset.storage.size())
            {
                error = "the asset name is not NUL-terminated";
                return std::nullopt;
            }
            asset.name.assign(reinterpret_cast<const char *>(d + p), e - p);
            writePointer(d, OffName, d + p);
            p = e + 1;
        }
        else if (readU32(d, OffName) != 0)
        {
            error = "the asset name holds an unexpected pointer placeholder";
            return std::nullopt;
        }

        const std::size_t namesAt = p;
        if (!claim(OffNames, 2u * asset.boneCount, "names")) return std::nullopt;
        const std::size_t notifyAt = p;
        if (!claim(OffNotify, NotifyStride * asset.notifyCount, "notify")) return std::nullopt;
        if (!claim(OffDataByte, dataByteCount, "dataByte")) return std::nullopt;
        if (!claim(OffDataShort, 2u * dataShortCount, "dataShort")) return std::nullopt;
        if (!claim(OffDataInt, 4u * dataIntCount, "dataInt")) return std::nullopt;
        if (!claim(OffRandomDataShort, 2u * randomDataShortCount, "randomDataShort"))
            return std::nullopt;
        if (!claim(OffRandomDataByte, randomDataByteCount, "randomDataByte"))
            return std::nullopt;

        if (p != asset.storage.size())
        {
            // The same standard the decoder holds itself to: a walk that does not
            // tile the blob has not understood it.
            error = "arrays tile " + std::to_string(p) + " of " +
                std::to_string(asset.storage.size()) + " bytes";
            return std::nullopt;
        }

        // Script strings last, so a resolver failure cannot leave a half-relocated
        // asset that still looks structurally sound.
        asset.boneStrings.reserve(asset.boneCount);
        for (std::uint8_t i = 0; i < asset.boneCount; ++i)
        {
            const auto id = resolve(boneNames[i]);
            if (id == 0)
            {
                error = "bone name '" + boneNames[i] + "' did not resolve";
                return std::nullopt;
            }
            asset.boneStrings.push_back(id);
            writeU16(d, namesAt + 2u * i, id);
        }
        asset.notifyStrings.reserve(asset.notifyCount);
        for (std::uint8_t i = 0; i < asset.notifyCount; ++i)
        {
            const auto id = resolve(notifyNames[i]);
            if (id == 0)
            {
                error = "notify name '" + notifyNames[i] + "' did not resolve";
                return std::nullopt;
            }
            asset.notifyStrings.push_back(id);
            writeU16(d, notifyAt + NotifyStride * i, id);
        }

        return asset;
    }

    SvForgeStringResolver SV_ForgeStringResolver(
        const SvForgeXAnimBindings &bindings) noexcept
    {
        if (!bindings.scriptStringGet)
            return {};
        const auto function = reinterpret_cast<
            std::int32_t(__cdecl *)(const char *, std::int32_t, std::uint32_t)>(
            bindings.scriptStringGet);
        const auto kind = bindings.scriptStringKind;
        return [function, kind](const std::string &name) -> std::uint16_t {
            if (name.empty() || name.size() > 255)
                return 0;
#ifdef _WIN32
            __try
            {
#endif
                const auto id = function(
                    name.c_str(), kind, static_cast<std::uint32_t>(name.size()));
                if (id <= 0 || id > 0xFFFF)
                    return 0;
                return static_cast<std::uint16_t>(id);
#ifdef _WIN32
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return 0;
            }
#endif
        };
    }

    SvForgeStringResolver SV_ForgeStringTableResolver(
        const std::uintptr_t moduleBase) noexcept
    {
        if (!moduleBase)
            return {};
        return [moduleBase](const std::string &name) -> std::uint16_t {
            if (name.empty() || name.size() > 15)
                return 0;
#ifdef _WIN32
            __try
            {
#endif
                const auto slot = reinterpret_cast<const std::uint8_t *const *>(
                    moduleBase + ScriptStringTablePtrRva);
                const std::uint8_t *const table = *slot;
                if (!table)
                    return 0;
                // `length` counts the NUL, so a name of n characters stores n + 1.
                const auto want = static_cast<std::uint8_t>(name.size() + 1);
                for (std::size_t i = 1; i <= ScriptStringMaxIndex; ++i)
                {
                    const std::uint8_t *const e = table + ScriptStringStride * i;
                    if (e[3] != want)
                        continue;
                    if (std::memcmp(e + 4, name.c_str(), name.size() + 1) == 0)
                        return static_cast<std::uint16_t>(i);
                }
                return 0;
#ifdef _WIN32
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return 0;
            }
#endif
        };
    }

    SvForgeXAnimStatus SV_PublishForgeXAnim(
        SvForgeXAnimAsset &asset,
        const SvForgeXAnimBindings &bindings,
        std::string &error) noexcept
    {
        if (!bindings.dbLinkXAssetEntry)
        {
            error = "DB_LinkXAssetEntry is not bound";
            return SvForgeXAnimStatus::MissingBinding;
        }
        if (asset.storage.empty() || asset.storage.size() < XAnimPartsSize)
        {
            error = "the asset was not relocated";
            return SvForgeXAnimStatus::InvalidBlob;
        }

        // DB_LinkXAssetEntry copies the 88-byte header but KEEPS every pointer
        // inside it, so the storage this asset owns has to outlive the client. A
        // caller that lets it go out of scope leaves the engine holding freed
        // memory, which is why the asset is passed by reference and never copied.
        void *header = asset.header();
        void *entry = nullptr;
#ifdef _WIN32
        __try
        {
#endif
            entry = reinterpret_cast<void *(__cdecl *)(std::uint32_t, void **)>(
                bindings.dbLinkXAssetEntry)(OlfinalXAnimAssetType, &header);
#ifdef _WIN32
        }
        __except (EXCEPTION_EXECUTE_HANDLER)
        {
            error = "DB_LinkXAssetEntry faulted";
            return SvForgeXAnimStatus::LinkFailed;
        }
#endif
        if (!entry || !header)
        {
            error = "DB_LinkXAssetEntry returned nothing";
            return SvForgeXAnimStatus::LinkFailed;
        }
        return SvForgeXAnimStatus::Ready;
    }

    SvForgeXAnimPublishReport SV_PublishForgeBundleXAnims(
        const std::vector<SvForgeAnimationRef> &animations,
        const std::filesystem::path &bundleRoot,
        const std::uintptr_t moduleBase,
        const bool enable) noexcept
    {
        SvForgeXAnimPublishReport report;
        // The gate is checked before anything else so a caller cannot reach the
        // engine by accident, and so a disabled call is genuinely free.
        if (!enable || !moduleBase)
            return report;
        report.ran = true;

        SvForgeXAnimBindings bindings;
        bindings.dbLinkXAssetEntry =
            reinterpret_cast<void *>(moduleBase + DBLinkXAssetEntryRva);
        bindings.scriptStringGet =
            reinterpret_cast<void *>(moduleBase + ScriptStringGetRva);
        const auto resolve = SV_ForgeStringResolver(bindings);
        if (!resolve)
        {
            report.failures.emplace_back(
                "*", "the script-string resolver could not be bound");
            return report;
        }

        // Published assets are never released: DB_LinkXAssetEntry copies the
        // 88-byte header but keeps the pointers inside it, so the engine holds
        // references into this storage for the life of the process. unique_ptr so
        // that growing the list can never move an asset that has been published.
        static std::vector<std::unique_ptr<SvForgeXAnimAsset>> published;

        for (const auto &anim : animations)
        {
            ++report.attempted;
            const auto path = bundleRoot / anim.asset;
            std::error_code ec;
            const auto size = std::filesystem::file_size(path, ec);
            if (ec || size < 88)
            {
                report.failures.emplace_back(
                    anim.name, "blob missing or shorter than its header");
                continue;
            }
            std::vector<std::byte> bytes(static_cast<std::size_t>(size));
            {
                std::ifstream stream(path, std::ios::binary);
                stream.read(reinterpret_cast<char *>(bytes.data()),
                    static_cast<std::streamsize>(bytes.size()));
                if (stream.gcount() != static_cast<std::streamsize>(bytes.size()))
                {
                    report.failures.emplace_back(anim.name, "blob did not read back whole");
                    continue;
                }
            }

            std::string error;
            auto relocated = SV_RelocateForgeXAnim(
                bytes, anim.bones, anim.notifies, resolve, error);
            if (!relocated)
            {
                report.failures.emplace_back(anim.name, "relocate: " + error);
                continue;
            }

            auto owned = std::make_unique<SvForgeXAnimAsset>(std::move(*relocated));
            const auto status = SV_PublishForgeXAnim(*owned, bindings, error);
            if (status != SvForgeXAnimStatus::Ready)
            {
                report.failures.emplace_back(
                    anim.name,
                    std::string(SV_ForgeXAnimStatusName(status)) + ": " + error);
                continue;
            }
            published.push_back(std::move(owned));
            ++report.published;
        }
        return report;
    }

    namespace
    {
        constexpr std::size_t XModelSize = 360;
        constexpr std::size_t OffXmNumBones = 4;
        constexpr std::size_t OffXmNumRootBones = 5;
        constexpr std::size_t OffXmNumsurfs = 6;
        constexpr std::size_t OffXmBoneNames = 44;
        constexpr std::size_t OffXmParentList = 48;
        constexpr std::size_t OffXmQuats = 52;
        constexpr std::size_t OffXmTrans = 56;
        constexpr std::size_t OffXmPartClassification = 60;
        constexpr std::size_t OffXmBaseMat = 64;
        constexpr std::size_t OffXmMaterials = 68;
        constexpr std::size_t OffXmLodInfo = 72;
        constexpr std::size_t LodInfoStride = 56;
        constexpr std::size_t OffLodNumsurfs = 4;
        constexpr std::size_t OffLodModelSurfs = 8;
        constexpr std::size_t OffLodName = 12;
        constexpr std::size_t OffLodSurfs = 48;
        constexpr std::size_t OffXmCollSurfs = 300;
        constexpr std::size_t OffXmNumCollSurfs = 304;
        constexpr std::size_t OffXmBoneInfo = 312;
        constexpr std::size_t OffXmPhysPreset = 352;
        constexpr std::size_t OffXmPhysCollmap = 356;
        constexpr std::uint32_t StreamedModelSurfs = 0xFFFFFFFEu;

        std::size_t alignUp(const std::size_t v, const std::size_t a) noexcept
        {
            return (v + a - 1) & ~(a - 1);
        }
        void writeU32(std::byte *const d, const std::size_t o, const std::uint32_t v) noexcept
        {
            for (std::size_t i = 0; i < 4; ++i)
                d[o + i] = static_cast<std::byte>((v >> (8 * i)) & 0xFF);
        }
    }

    std::optional<SvForgeXModelAsset> SV_BuildForgeXModel(
        const SvForgeModelRef &model,
        const SvForgeStringResolver &resolveString,
        const SvForgeMaterialResolver &resolveMaterial,
        std::string &error)
    {
        if (model.header.size() != XModelSize)
        {
            error = "header is " + std::to_string(model.header.size()) +
                " bytes, expected " + std::to_string(XModelSize);
            return std::nullopt;
        }
        if (!resolveString || !resolveMaterial)
        {
            error = "a resolver was not supplied";
            return std::nullopt;
        }

        const auto bones = std::to_integer<std::uint8_t>(model.header[OffXmNumBones]);
        const auto roots = std::to_integer<std::uint8_t>(model.header[OffXmNumRootBones]);
        const auto surfs = std::to_integer<std::uint8_t>(model.header[OffXmNumsurfs]);
        if (bones == 0 || roots == 0 || roots > bones)
        {
            error = "implausible bone counts: " + std::to_string(bones) + " bones, " +
                std::to_string(roots) + " root";
            return std::nullopt;
        }
        const std::size_t nonRoot = static_cast<std::size_t>(bones) - roots;

        // Every one of these is a length the loader derives from the header's own
        // scalars, so a disagreement means the engine would read past an array.
        const auto expect = [&](const char *what, const std::size_t got,
                                const std::size_t want) {
            if (got == want) return true;
            error = std::string(what) + " is " + std::to_string(got) +
                " bytes, expected " + std::to_string(want);
            return false;
        };
        if (model.boneNames.size() != bones)
        {
            error = "boneNames holds " + std::to_string(model.boneNames.size()) +
                " names for " + std::to_string(bones) + " bones";
            return std::nullopt;
        }
        if (!expect("parentList", model.parentList.size(), nonRoot) ||
            !expect("quats", model.quaternions.size(), 8 * nonRoot) ||
            !expect("trans", model.translations.size(), 12 * nonRoot) ||
            !expect("partClassification", model.partClassification.size(), bones) ||
            !expect("baseMat", model.baseMatrices.size(), 32u * bones))
        {
            return std::nullopt;
        }
        if (model.materials.size() != surfs)
        {
            error = "the header says " + std::to_string(surfs) + " surfaces but " +
                std::to_string(model.materials.size()) + " materials were given";
            return std::nullopt;
        }
        if (model.resource.empty())
        {
            error = "no loose resource name for lodInfo[0]";
            return std::nullopt;
        }

        const std::byte *const h = model.header.data();
        const auto lod0Surfs = static_cast<std::uint16_t>(
            std::to_integer<std::uint16_t>(h[OffXmLodInfo + OffLodNumsurfs]) |
            (std::to_integer<std::uint16_t>(h[OffXmLodInfo + OffLodNumsurfs + 1]) << 8));
        if (lod0Surfs != surfs)
        {
            error = "lodInfo[0].numsurfs is " + std::to_string(lod0Surfs) +
                " but the model has " + std::to_string(surfs) + " surfaces";
            return std::nullopt;
        }
        std::uint32_t lod0Streamed{};
        for (int i = 3; i >= 0; --i)
        {
            lod0Streamed = (lod0Streamed << 8) | std::to_integer<std::uint32_t>(
                h[OffXmLodInfo + OffLodModelSurfs + static_cast<std::size_t>(i)]);
        }
        if (lod0Streamed != StreamedModelSurfs)
        {
            error = "lodInfo[0].modelSurfs is not the streamed sentinel 0xFFFFFFFE";
            return std::nullopt;
        }

        // Lay the payload out once, so nothing can move after a pointer is taken.
        std::size_t p = XModelSize;
        const std::size_t nameAt = p;              p += model.name.size() + 1;
        p = alignUp(p, 2);
        const std::size_t boneNamesAt = p;         p += 2u * bones;
        const std::size_t parentListAt = p;        p += nonRoot;
        p = alignUp(p, 4);
        const std::size_t quatsAt = p;             p += model.quaternions.size();
        const std::size_t transAt = p;             p += model.translations.size();
        const std::size_t partClassAt = p;         p += bones;
        p = alignUp(p, 4);
        const std::size_t baseMatAt = p;           p += model.baseMatrices.size();
        const std::size_t materialsAt = p;         p += 4u * surfs;
        const std::size_t lodNameAt = p;           p += model.resource.size() + 1;

        SvForgeXModelAsset asset;
        asset.storage.assign(p, std::byte{0});
        std::byte *const d = asset.storage.data();
        std::copy(model.header.begin(), model.header.end(), asset.storage.begin());

        const auto put = [&](const std::size_t at, const std::vector<std::byte> &src) {
            std::copy(src.begin(), src.end(), asset.storage.begin() +
                static_cast<std::ptrdiff_t>(at));
        };
        std::memcpy(d + nameAt, model.name.data(), model.name.size());
        std::memcpy(d + lodNameAt, model.resource.data(), model.resource.size());
        put(parentListAt, model.parentList);
        put(quatsAt, model.quaternions);
        put(transAt, model.translations);
        put(partClassAt, model.partClassification);
        put(baseMatAt, model.baseMatrices);

        // Bone names become script strings, the same interning the animation path
        // uses; index 0 is the null string, so it is never a valid answer.
        asset.boneStrings.reserve(bones);
        for (std::uint8_t i = 0; i < bones; ++i)
        {
            const auto id = resolveString(model.boneNames[i]);
            if (id == 0)
            {
                error = "bone name '" + model.boneNames[i] + "' did not resolve";
                return std::nullopt;
            }
            asset.boneStrings.push_back(id);
            writeU16(d, boneNamesAt + 2u * i, id);
        }
        // Materials are engine-owned assets, looked up rather than authored. A
        // surface with no material is not drawable, so a miss is fatal.
        for (std::uint8_t i = 0; i < surfs; ++i)
        {
            void *const material = resolveMaterial(model.materials[i]);
            if (!material)
            {
                error = "material '" + model.materials[i] + "' did not resolve";
                return std::nullopt;
            }
            writePointer(d, materialsAt + 4u * i, material);
        }

        writePointer(d, 0, d + nameAt);
        writePointer(d, OffXmBoneNames, d + boneNamesAt);
        writePointer(d, OffXmParentList, nonRoot ? d + parentListAt : nullptr);
        writePointer(d, OffXmQuats, nonRoot ? d + quatsAt : nullptr);
        writePointer(d, OffXmTrans, nonRoot ? d + transAt : nullptr);
        writePointer(d, OffXmPartClassification, d + partClassAt);
        writePointer(d, OffXmBaseMat, d + baseMatAt);
        writePointer(d, OffXmMaterials, surfs ? d + materialsAt : nullptr);
        writePointer(d, OffXmLodInfo + OffLodName, d + lodNameAt);
        writePointer(d, OffXmLodInfo + OffLodSurfs, nullptr);

        // Everything this path does not author is explicitly NULL rather than left
        // to whatever the emitted header happened to carry.
        writePointer(d, OffXmCollSurfs, nullptr);
        writeU32(d, OffXmNumCollSurfs, 0);
        writePointer(d, OffXmBoneInfo, nullptr);
        writePointer(d, OffXmPhysPreset, nullptr);
        writePointer(d, OffXmPhysCollmap, nullptr);
        for (std::size_t lod = 1; lod < 4; ++lod)
        {
            const std::size_t at = OffXmLodInfo + lod * LodInfoStride;
            writeU32(d, at + OffLodModelSurfs, 0);
            writePointer(d, at + OffLodName, nullptr);
            writePointer(d, at + OffLodSurfs, nullptr);
        }

        asset.name = model.name;
        asset.numBones = bones;
        asset.numRootBones = roots;
        asset.numsurfs = surfs;
        return asset;
    }

    std::uint32_t SV_ForgeXAssetHash(
        const std::uint32_t type, const std::string &name) noexcept
    {
        // sub_49C870 out.exe 0x49C870, seeded with the asset type.
        std::uint32_t h = type;
        for (const char raw : name)
        {
            int c = static_cast<unsigned char>(raw);
            if (c >= 'A' && c <= 'Z')
                c += 32;
            // The hash folds a backslash to a forward slash. The COMPARE does not.
            if (c == '\\')
                c = '/';
            h = 31u * h + static_cast<std::uint32_t>(c);
        }
        return h % XAssetHashBuckets;
    }

    std::size_t SV_ForgeXAssetNameOffsetForThunk(const std::uint32_t thunkRva) noexcept
    {
        switch (thunkRva)
        {
        case XAssetNameThunkAt0Rva: return 0;
        case XAssetNameThunkAt16Rva: return 16;
        case XAssetNameThunkAt48Rva: return 48;
        default: return XAssetNameOffsetUnknown;
        }
    }

    bool SV_ForgeXAssetNamesEqual(const char *const stored, const std::string &wanted) noexcept
    {
        if (!stored)
            return false;
        // sub_49CA70's own comparison: byte for byte, lowering only A-Z, and no
        // slash folding. A name with no terminator inside the cap fails closed.
        for (std::size_t i = 0; i < XAssetMaxNameLength; ++i)
        {
            int a = static_cast<unsigned char>(stored[i]);
            int b = i < wanted.size() ? static_cast<unsigned char>(wanted[i]) : 0;
            if (a != b)
            {
                if (a >= 'A' && a <= 'Z')
                    a += 32;
                if (b >= 'A' && b <= 'Z')
                    b += 32;
                if (a != b)
                    return false;
            }
            if (a == 0)
                return i == wanted.size();
        }
        return false;
    }

    SvForgeXAssetTable SV_ForgeXAssetTableFor(const std::uintptr_t moduleBase) noexcept
    {
        if (!moduleBase)
            return {};
        SvForgeXAssetTable table;
        table.moduleBase = moduleBase;
        table.hashHeads =
            reinterpret_cast<const std::uint32_t *>(moduleBase + XAssetHashHeadsRva);
        table.entries =
            reinterpret_cast<const std::uint8_t *>(moduleBase + XAssetEntriesRva);
        table.nameThunks =
            reinterpret_cast<const std::uintptr_t *>(moduleBase + XAssetNameThunksRva);
        return table;
    }

    void *SV_ForgeFindXAsset(
        const SvForgeXAssetTable &table,
        const std::uint32_t type,
        const std::string &name) noexcept
    {
        if (!table.valid() || name.empty() || name.size() >= XAssetMaxNameLength)
            return nullptr;
#ifdef _WIN32
        __try
        {
#endif
            // The accessor is read from the engine's own dispatch table, so a type
            // whose name lives somewhere this code has not read is REFUSED rather
            // than read at a guessed offset.
            const std::uintptr_t thunk = table.nameThunks[type];
            const auto thunkRva = static_cast<std::uint32_t>(thunk - table.moduleBase);
            const std::size_t nameOffset = SV_ForgeXAssetNameOffsetForThunk(thunkRva);
            if (nameOffset == XAssetNameOffsetUnknown)
                return nullptr;

            const std::uint32_t bucket = SV_ForgeXAssetHash(type, name);
            if (bucket >= table.buckets)
                return nullptr;

            std::uint32_t index = table.hashHeads[bucket];
            for (std::uint32_t step = 0; index != 0 && step < XAssetMaxChainSteps; ++step)
            {
                const std::uint8_t *const entry =
                    table.entries + XAssetEntryStride * index;
                std::uint32_t entryType{};
                std::uint8_t *header{};
                std::uint32_t next{};
                std::memcpy(&entryType, entry + XAssetEntryTypeOffset, sizeof(entryType));
                std::memcpy(&header, entry + XAssetEntryHeaderOffset, sizeof(header));
                std::memcpy(&next, entry + XAssetEntryNextOffset, sizeof(next));

                if (entryType == type && header)
                {
                    const char *stored{};
                    std::memcpy(&stored, header + nameOffset, sizeof(stored));
                    if (SV_ForgeXAssetNamesEqual(stored, name))
                        return header;
                }
                index = next;
            }
            return nullptr;
#ifdef _WIN32
        }
        __except (EXCEPTION_EXECUTE_HANDLER)
        {
            return nullptr;
        }
#endif
    }

    SvForgeMaterialResolver SV_ForgeMaterialTableResolver(
        const std::uintptr_t moduleBase) noexcept
    {
        const auto table = SV_ForgeXAssetTableFor(moduleBase);
        if (!table.valid())
            return {};
        return [table](const std::string &name) -> void * {
            return SV_ForgeFindXAsset(table, OlfinalMaterialAssetType, name);
        };
    }

    SvForgeImageResolver SV_ForgeImageTableResolver(
        const std::uintptr_t moduleBase) noexcept
    {
        const auto table = SV_ForgeXAssetTableFor(moduleBase);
        if (!table.valid())
            return {};
        return [table](const std::string &name) -> void * {
            return SV_ForgeFindXAsset(table, OlfinalGfxImageAssetType, name);
        };
    }

    SvForgeMaterialResolver SV_ForgeMaterialResolver(
        const std::uintptr_t moduleBase) noexcept
    {
        if (!moduleBase)
            return {};
        const auto find = reinterpret_cast<void *(__cdecl *)(
            std::uint32_t, const char *, bool)>(moduleBase + DBFindXAssetHeaderRva);
        return [find](const std::string &name) -> void * {
            if (name.empty())
                return nullptr;
#ifdef _WIN32
            __try
            {
#endif
                // createDefault false: a missing material must read as missing, not
                // as the default one, or every surface would silently draw wrong.
                return find(OlfinalMaterialAssetType, name.c_str(), false);
#ifdef _WIN32
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return nullptr;
            }
#endif
        };
    }

    SvForgeXAnimStatus SV_PublishForgeXModel(
        SvForgeXModelAsset &asset,
        const SvForgeXAnimBindings &bindings,
        std::string &error) noexcept
    {
        if (!bindings.dbLinkXAssetEntry)
        {
            error = "DB_LinkXAssetEntry is not bound";
            return SvForgeXAnimStatus::MissingBinding;
        }
        if (asset.storage.size() < XModelSize)
        {
            error = "the asset was not built";
            return SvForgeXAnimStatus::InvalidBlob;
        }
        void *header = asset.header();
        void *entry = nullptr;
#ifdef _WIN32
        __try
        {
#endif
            entry = reinterpret_cast<void *(__cdecl *)(std::uint32_t, void **)>(
                bindings.dbLinkXAssetEntry)(OlfinalXModelAssetType, &header);
#ifdef _WIN32
        }
        __except (EXCEPTION_EXECUTE_HANDLER)
        {
            error = "DB_LinkXAssetEntry faulted";
            return SvForgeXAnimStatus::LinkFailed;
        }
#endif
        if (!entry || !header)
        {
            error = "DB_LinkXAssetEntry returned nothing";
            return SvForgeXAnimStatus::LinkFailed;
        }
        return SvForgeXAnimStatus::Ready;
    }

    namespace
    {
        // CODREF(alpha_weapondef): every enum value below is read off a port in
        // SV_AlphaWeaponPorts(), each of which was decoded from a shipped weapon
        // rather than inferred. The Uzi (weaponClass 3, penetrateType 1, fireType
        // 0) is the SMG witness and the one this mapping leans on hardest.
        //
        // Values with no witness are deliberately absent: an unmapped string is
        // rejected rather than defaulted, because a wrong weaponClass is a
        // gameplay change that would look like a port bug for weeks.
        struct EnumEntry { const char *text; std::int32_t value; };

        constexpr EnumEntry WeaponTypes[]{ {"bullet", 0} };
        constexpr EnumEntry WeaponClasses[]{
            {"rifle", 0}, {"assault", 0},     // Fal, Tavor, Masada
            {"sniper", 1},                    // Barrett
            {"smg", 3},                       // Uzi
            {"pistol", 5},                    // Colt Anaconda
        };
        constexpr EnumEntry PenetrateTypes[]{
            {"small", 1}, {"medium", 2}, {"large", 3},
        };
        constexpr EnumEntry ImpactTypes[]{
            {"bullet_small", 0}, {"bullet_large", 0},
        };
        constexpr EnumEntry FireTypes[]{
            {"full auto", 0}, {"single shot", 1},
        };

        // CoD4's hit-location keys, in the order the first six entries of
        // SvAlphaWeaponTuning::hitLocationMultipliers carry them. Both the
        // Standard set (1.0 then 1.4, 1.4, 1.0, 1.0, 1.0) and the Barrett's
        // (1.0 then 1.5 x5) agree that index 0 is `none` and 1..5 are the head and
        // torso group. Beyond index 5 the order has NO witness, so the remaining
        // entries keep their Standard values and CoD4's `locGun` is not mapped.
        constexpr const char *HitLocationKeys[]{
            "locNone", "locHelmet", "locHead", "locNeck",
            "locTorsoUpper", "locTorsoLower",
        };
        constexpr std::array<float, HitLocationCount> StandardHitLocations{
            1.0f, 1.4f, 1.4f, 1.0f, 1.0f, 1.0f, 1.0f,
            1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f,
            1.0f, 1.0f, 1.0f, 1.0f, 0.0f, 0.0f, 1.0f,
        };

        std::string lowercase(std::string s)
        {
            for (auto &c : s)
                c = static_cast<char>(
                    c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
            return s;
        }

        template <std::size_t N>
        bool mapEnum(const EnumEntry (&table)[N], const std::string &text,
            std::int32_t &out, std::string &error, const char *what)
        {
            const auto key = lowercase(text);
            for (const auto &e : table)
            {
                if (key == e.text)
                {
                    out = e.value;
                    return true;
                }
            }
            error = std::string(what) + " '" + text + "' has no measured OLfinal value";
            return false;
        }
    }

    std::optional<SvAlphaWeaponTuning> SV_ForgeWeaponTuning(
        const std::map<std::string, std::string> &keys, std::string &error)
    {
        const auto find = [&keys](const char *k) -> const std::string * {
            const auto it = keys.find(k);
            return it == keys.end() ? nullptr : &it->second;
        };
        const auto number = [&](const char *k, double &out) {
            const auto *const v = find(k);
            if (!v || v->empty())
            {
                error = std::string("weaponfile key '") + k + "' is missing";
                return false;
            }
            try
            {
                std::size_t used{};
                out = std::stod(*v, &used);
                if (used != v->size())
                    throw std::invalid_argument("trailing");
            }
            catch (const std::exception &)
            {
                error = std::string("weaponfile key '") + k + "' is not a number: " + *v;
                return false;
            }
            return true;
        };
        // CoD4 stores durations in SECONDS; the target stores milliseconds.
        const auto milliseconds = [&](const char *k, std::int32_t &out) {
            double v{};
            if (!number(k, v)) return false;
            if (v < 0.0 || v > 60.0)
            {
                error = std::string("weaponfile key '") + k +
                    "' is " + std::to_string(v) + " seconds, which is out of range";
                return false;
            }
            out = static_cast<std::int32_t>(v * 1000.0 + 0.5);
            return true;
        };
        const auto integer = [&](const char *k, std::int32_t &out,
                                 const double lo, const double hi) {
            double v{};
            if (!number(k, v)) return false;
            if (v < lo || v > hi)
            {
                error = std::string("weaponfile key '") + k + "' is " +
                    std::to_string(v) + ", outside " + std::to_string(lo) +
                    ".." + std::to_string(hi);
                return false;
            }
            out = static_cast<std::int32_t>(v);
            return true;
        };
        const auto real = [&](const char *k, float &out,
                              const double lo, const double hi) {
            double v{};
            if (!number(k, v)) return false;
            if (v < lo || v > hi)
            {
                error = std::string("weaponfile key '") + k + "' is " +
                    std::to_string(v) + ", outside " + std::to_string(lo) +
                    ".." + std::to_string(hi);
                return false;
            }
            out = static_cast<float>(v);
            return true;
        };
        const auto text = [&](const char *k, const char **out) {
            const auto *const v = find(k);
            if (!v || v->empty())
            {
                error = std::string("weaponfile key '") + k + "' is missing";
                return false;
            }
            *out = v->c_str();
            return true;
        };

        SvAlphaWeaponTuning t{};
        const std::string *raw{};
        const auto mapKey = [&](const char *k, auto &table, std::int32_t &out) {
            raw = find(k);
            if (!raw || raw->empty())
            {
                error = std::string("weaponfile key '") + k + "' is missing";
                return false;
            }
            return mapEnum(table, *raw, out, error, k);
        };
        (void)text;

        if (!mapKey("weaponType", WeaponTypes, t.weaponType) ||
            !mapKey("weaponClass", WeaponClasses, t.weaponClass) ||
            !mapKey("penetrateType", PenetrateTypes, t.penetrateType) ||
            !mapKey("impactType", ImpactTypes, t.impactType) ||
            !mapKey("fireType", FireTypes, t.fireType))
        {
            return std::nullopt;
        }

        if (!integer("startAmmo", t.startAmmo, 0, 4000) ||
            !integer("maxAmmo", t.maxAmmo, 1, 4000) ||
            !integer("clipSize", t.clipSize, 1, 4000) ||
            !integer("shotCount", t.shotCount, 1, 64) ||
            !integer("damage", t.damage, 0, 10000) ||
            !integer("minDamage", t.minDamage, 0, 10000) ||
            !integer("meleeDamage", t.meleeDamage, 0, 10000) ||
            !milliseconds("fireTime", t.fireTimeMilliseconds) ||
            !milliseconds("fireDelay", t.fireDelayMilliseconds) ||
            !milliseconds("dropTime", t.dropTimeMilliseconds) ||
            !milliseconds("raiseTime", t.raiseTimeMilliseconds) ||
            !real("maxDamageRange", t.maxDamageRange, 0.0, 100000.0) ||
            !real("minDamageRange", t.minDamageRange, 0.0, 100000.0))
        {
            return std::nullopt;
        }
        if (t.minDamage > t.damage)
        {
            error = "minDamage exceeds damage";
            return std::nullopt;
        }
        if (t.maxDamageRange > t.minDamageRange)
        {
            error = "maxDamageRange exceeds minDamageRange";
            return std::nullopt;
        }
        if (t.startAmmo > t.maxAmmo)
        {
            error = "startAmmo exceeds maxAmmo";
            return std::nullopt;
        }
        if (t.fireTimeMilliseconds <= 0)
        {
            error = "fireTime rounds to zero milliseconds";
            return std::nullopt;
        }

        // The order is {standMin, duckedMin, proneMin, max, duckedMax, proneMax}.
        // The Uzi's shipped values are {2.0, 1.75, 1.5, 5.0, 4.5, 4.0} and the
        // PPSh's CoD4 keys carry exactly those six numbers in exactly that order,
        // which is what fixes the mapping and says the units already agree.
        static constexpr const char *SpreadKeys[]{
            "hipSpreadStandMin", "hipSpreadDuckedMin", "hipSpreadProneMin",
            "hipSpreadMax", "hipSpreadDuckedMax", "hipSpreadProneMax",
        };
        for (std::size_t i = 0; i < t.hipSpread.size(); ++i)
        {
            if (!real(SpreadKeys[i], t.hipSpread[i], 0.0, 1000.0))
                return std::nullopt;
        }
        if (t.hipSpread[0] > t.hipSpread[3])
        {
            error = "hipSpreadStandMin exceeds hipSpreadMax";
            return std::nullopt;
        }

        t.hitLocationMultipliers = StandardHitLocations;
        for (std::size_t i = 0; i < std::size(HitLocationKeys); ++i)
        {
            if (find(HitLocationKeys[i]) &&
                !real(HitLocationKeys[i], t.hitLocationMultipliers[i], 0.0, 100.0))
            {
                return std::nullopt;
            }
        }

        const auto *const ads = find("aimDownSight");
        t.aimDownSight = ads && (*ads == "1" || lowercase(*ads) == "true");

        // overlayReticle has no CoD4 counterpart worth mapping: the source key is
        // a shader name, the target an index. Left at the clone's value.
        t.overlayReticle = 0;
        return t;
    }

    namespace
    {
        constexpr std::size_t MaterialSize = 104;
        constexpr std::size_t OffMtlName = 16;
        constexpr std::size_t OffMtlTextureCount = 81;
        constexpr std::size_t OffMtlTextureTable = 92;
        constexpr std::size_t TextureDefStride = 12;
        constexpr std::size_t OffTexNameHash = 0;
        constexpr std::size_t OffTexNameStart = 4;
        constexpr std::size_t OffTexNameEnd = 5;
        constexpr std::size_t OffTexImage = 8;

        // Measured across 2,849 shipped materials. nameStart/nameEnd are the first
        // and last characters of the sampler name and the hash covers that same
        // name, so a slot's hash is identical in every material carrying it.
        struct SamplerSlot { const char *name; std::uint32_t hash; };
        constexpr SamplerSlot SamplerSlots[]{
            {"colormap", 0xA0AB1041u},
            {"normalmap", 0x59D30D0Fu},
            {"specularmap", 0x34ECCCB3u},
            {"detailmap", 0xEB529B4Du},
        };
    }

    std::uint32_t SV_ForgeSamplerHash(const std::string &semantic) noexcept
    {
        std::string key;
        for (const char c : semantic)
            key.push_back(static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c));
        for (const auto &s : SamplerSlots)
            if (key == s.name) return s.hash;
        return 0;
    }

    std::optional<SvForgeMaterialAsset> SV_BuildForgeMaterial(
        const std::string &name,
        const std::span<const std::byte> cloneHeader,
        const std::span<const std::byte> cloneTable,
        const std::vector<SvForgeMaterialSlot> &slots,
        const SvForgeImageResolver &resolveImage,
        std::string &error)
    {
        if (cloneHeader.size() != MaterialSize)
        {
            error = "clone header is " + std::to_string(cloneHeader.size()) +
                " bytes, expected " + std::to_string(MaterialSize);
            return std::nullopt;
        }
        if (!resolveImage)
        {
            error = "no image resolver was supplied";
            return std::nullopt;
        }
        if (name.empty())
        {
            error = "the material has no name";
            return std::nullopt;
        }
        if (slots.empty())
        {
            error = "the material names no texture slots";
            return std::nullopt;
        }

        const auto textureCount =
            std::to_integer<std::uint8_t>(cloneHeader[OffMtlTextureCount]);
        if (textureCount == 0 || textureCount > 16)
        {
            error = "the clone has " + std::to_string(textureCount) + " texture slots";
            return std::nullopt;
        }
        if (cloneTable.size() != TextureDefStride * textureCount)
        {
            error = "clone texture table is " + std::to_string(cloneTable.size()) +
                " bytes for " + std::to_string(textureCount) + " slots";
            return std::nullopt;
        }

        // Lay the asset out: header, name, then our own copy of the texture table.
        // Everything else - techniqueSet, constants, state bits - keeps pointing at
        // the clone's engine-owned memory, which is the point of cloning.
        const std::size_t nameAt = MaterialSize;
        const std::size_t tableAt = alignUp(nameAt + name.size() + 1, 4);
        const std::size_t total = tableAt + cloneTable.size();

        SvForgeMaterialAsset asset;
        asset.storage.assign(total, std::byte{0});
        std::byte *const d = asset.storage.data();
        std::copy(cloneHeader.begin(), cloneHeader.end(), asset.storage.begin());
        std::memcpy(d + nameAt, name.data(), name.size());
        std::copy(cloneTable.begin(), cloneTable.end(),
            asset.storage.begin() + static_cast<std::ptrdiff_t>(tableAt));

        std::vector<bool> filled(textureCount, false);
        for (const auto &slot : slots)
        {
            const auto hash = SV_ForgeSamplerHash(slot.semantic);
            if (hash == 0)
            {
                error = "sampler slot '" + slot.semantic +
                    "' has no measured nameHash";
                return std::nullopt;
            }
            if (slot.image.empty())
            {
                error = "slot '" + slot.semantic + "' names no image";
                return std::nullopt;
            }

            // Match by nameHash rather than by position: writing an image into the
            // wrong slot draws a normal map as diffuse instead of failing.
            std::size_t at = textureCount;
            for (std::size_t i = 0; i < textureCount; ++i)
            {
                if (readU32(d, tableAt + TextureDefStride * i + OffTexNameHash) == hash)
                {
                    at = i;
                    break;
                }
            }
            if (at == textureCount)
            {
                error = "the clone has no '" + slot.semantic + "' slot to replace";
                return std::nullopt;
            }
            if (filled[at])
            {
                error = "slot '" + slot.semantic + "' was given twice";
                return std::nullopt;
            }

            void *const image = resolveImage(slot.image);
            if (!image)
            {
                error = "image '" + slot.image + "' did not resolve";
                return std::nullopt;
            }
            writePointer(d, tableAt + TextureDefStride * at + OffTexImage, image);
            filled[at] = true;
        }

        writePointer(d, OffMtlName, d + nameAt);
        writePointer(d, OffMtlTextureTable, d + tableAt);

        asset.name = name;
        asset.textureCount = textureCount;
        return asset;
    }

    std::optional<SvForgeCod4Material> SV_ParseForgeCod4Material(
        const std::span<const std::byte> file,
        std::string &error)
    {
        if (file.size() < Cod4MtlHeaderSize)
        {
            error = "the material is " + std::to_string(file.size()) +
                " bytes, too short for a header";
            return std::nullopt;
        }

        const auto u32At = [&file](const std::size_t at) {
            std::uint32_t v = 0;
            for (std::size_t i = 0; i < 4; ++i)
                v |= static_cast<std::uint32_t>(
                    std::to_integer<std::uint8_t>(file[at + i])) << (8 * i);
            return v;
        };
        // Every string has to terminate inside the file. A CoD4 material is a
        // rebased struct dump, so an offset that leaves it means this is not one.
        const auto stringAt =
            [&file](const std::uint32_t at, std::string &out) -> bool {
                if (at == 0 || at >= file.size())
                    return false;
                for (std::size_t i = at; i < file.size(); ++i)
                {
                    if (file[i] == std::byte{0})
                    {
                        out.assign(
                            reinterpret_cast<const char *>(file.data()) + at, i - at);
                        return !out.empty();
                    }
                }
                return false;
            };

        SvForgeCod4Material parsed;
        if (!stringAt(u32At(OffCod4MtlName), parsed.name))
        {
            error = "the material's name offset does not resolve inside the file";
            return std::nullopt;
        }
        // The technique set is read but NOT used: a clone keeps its own, which is
        // the whole point of cloning. It is carried so a caller can report what the
        // source asked for.
        (void)stringAt(u32At(OffCod4MtlTechniqueSet), parsed.techniqueSet);

        const auto textureCount =
            std::to_integer<std::uint8_t>(file[OffCod4MtlTextureCount]);
        if (textureCount == 0 || textureCount > 16)
        {
            error = "the material declares " + std::to_string(textureCount) +
                " texture slots";
            return std::nullopt;
        }

        const std::uint32_t tableAt = u32At(OffCod4MtlTextureTable);
        const std::uint64_t tableEnd = static_cast<std::uint64_t>(tableAt) +
            static_cast<std::uint64_t>(Cod4TextureDefStride) * textureCount;
        if (tableAt < Cod4MtlHeaderSize || tableEnd > file.size())
        {
            error = "the texture table at " + std::to_string(tableAt) + " for " +
                std::to_string(textureCount) + " slots does not lie inside the file";
            return std::nullopt;
        }

        for (std::size_t i = 0; i < textureCount; ++i)
        {
            const std::size_t entry = tableAt + Cod4TextureDefStride * i;
            SvForgeMaterialSlot slot;
            if (!stringAt(u32At(entry + 0), slot.semantic))
            {
                error = "slot " + std::to_string(i) + " has no sampler name";
                return std::nullopt;
            }
            if (!stringAt(u32At(entry + 8), slot.image))
            {
                error = "slot '" + slot.semantic + "' names no image";
                return std::nullopt;
            }
            // A sampler with no measured nameHash cannot be matched against a
            // clone's slots, and matching by position is the mistake this whole
            // path exists to avoid. Refuse rather than bind it somewhere.
            if (SV_ForgeSamplerHash(slot.semantic) == 0)
            {
                error = "sampler '" + slot.semantic +
                    "' has no measured nameHash, so it cannot be matched by hash";
                return std::nullopt;
            }
            for (const auto &seen : parsed.slots)
            {
                if (seen.semantic == slot.semantic)
                {
                    error = "the material names '" + slot.semantic + "' twice";
                    return std::nullopt;
                }
            }
            parsed.semantics.push_back(
                std::to_integer<std::uint8_t>(file[entry + 5]));
            parsed.slots.push_back(std::move(slot));
        }
        return parsed;
    }

    SvForgeImageResolver SV_ForgeImageResolver(const std::uintptr_t moduleBase) noexcept
    {
        if (!moduleBase)
            return {};
        const auto find = reinterpret_cast<void *(__cdecl *)(
            std::uint32_t, const char *, bool)>(moduleBase + DBFindXAssetHeaderRva);
        return [find](const std::string &name) -> void * {
            if (name.empty())
                return nullptr;
#ifdef _WIN32
            __try
            {
#endif
                // createDefault false, for the same reason as materials: a missing
                // image must read as missing rather than as the default checker.
                return find(OlfinalGfxImageAssetType, name.c_str(), false);
#ifdef _WIN32
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return nullptr;
            }
#endif
        };
    }

    SvForgeXAnimStatus SV_PublishForgeMaterial(
        SvForgeMaterialAsset &asset,
        const SvForgeXAnimBindings &bindings,
        std::string &error) noexcept
    {
        if (!bindings.dbLinkXAssetEntry)
        {
            error = "DB_LinkXAssetEntry is not bound";
            return SvForgeXAnimStatus::MissingBinding;
        }
        if (asset.storage.size() < MaterialSize)
        {
            error = "the asset was not built";
            return SvForgeXAnimStatus::InvalidBlob;
        }
        void *header = asset.header();
        void *entry = nullptr;
#ifdef _WIN32
        __try
        {
#endif
            entry = reinterpret_cast<void *(__cdecl *)(std::uint32_t, void **)>(
                bindings.dbLinkXAssetEntry)(OlfinalMaterialAssetType, &header);
#ifdef _WIN32
        }
        __except (EXCEPTION_EXECUTE_HANDLER)
        {
            error = "DB_LinkXAssetEntry faulted";
            return SvForgeXAnimStatus::LinkFailed;
        }
#endif
        if (!entry || !header)
        {
            error = "DB_LinkXAssetEntry returned nothing";
            return SvForgeXAnimStatus::LinkFailed;
        }
        return SvForgeXAnimStatus::Ready;
    }
}
