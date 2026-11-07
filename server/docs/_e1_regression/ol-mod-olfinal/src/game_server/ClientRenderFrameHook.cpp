#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "ClientRenderFrameHook.hpp"

#include "server_mp/sv_forge_bundle_mp.hpp"
#include "server_mp/sv_forge_publish_mp.hpp"
#include <algorithm>
#include <array>
#include <cctype>
#include <atomic>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <utility>
#include <vector>

namespace CodolGameServer
{
    namespace
    {
        // sub_BE2150, __cdecl, one stack argument, caller cleans.
        using RenderBeginFn = void(__cdecl *)(void *);
        // sub_BE7470, __cdecl (void **loadDefSlot, GfxImage *). Load_GfxImage passes
        // the image for BOTH, because the load-def pointer arrives at image+0.
        using ImageUploadFn = void(__cdecl *)(void *, void *);
        using FiberSlotFn = std::uint32_t(__cdecl *)();
        using LinkFn = void *(__cdecl *)(std::uint32_t, void **);

        constexpr std::array<std::uint8_t, 5> OriginalCall{ 0xE8, 0x3D, 0xFF, 0xFF, 0xFF };

        // CODREF(material): Load_Material out.exe 0x488250 reads 104 bytes;
        // +81 textureCount, +92 MaterialTextureDef *, 12 bytes each.
        constexpr std::size_t MaterialHeaderBytes = 104;
        constexpr std::size_t OffMtlTextureCount = 81;
        constexpr std::size_t OffMtlTextureTable = 92;
        constexpr std::size_t TextureDefBytes = 12;

        std::atomic<bool> Installed{ false };
        void *RenderBegin{};

        ImageUploadFn Upload{};
        FiberSlotFn FiberSlot{};
        LinkFn Link{};
        const std::uint32_t **LoadForRendererDvar{};

        struct Job
        {
            std::unique_ptr<SvForgeGfxImage> image;
            bool link = false;
        };

        std::mutex QueueMutex;
        std::vector<Job> Pending;
        // Published assets are never released: the engine keeps the pointers.
        std::vector<std::unique_ptr<SvForgeGfxImage>> Retained;
        std::vector<ForgeImageUploadRecord> Records;
        // Read without the lock every frame, so the idle cost is one relaxed load.
        std::atomic<std::size_t> PendingCount{ 0 };

        [[nodiscard]] bool rendererAcceptsUploads() noexcept
        {
            if (LoadForRendererDvar == nullptr)
                return false;
            const std::uint32_t *const dvar = *LoadForRendererDvar;
            if (dvar == nullptr)
                return false;
            // sub_BE7470: `mov ecx, dword_E899CC / cmp dword ptr [ecx+0Ch], 0 / jz`.
            return dvar[3] != 0;
        }

        // The two engine calls, each isolated in a function with NO object that
        // needs unwinding. MSVC refuses __try in a function that has one, and
        // `record.detail = "..."` alone is enough to create one.
        [[nodiscard]] bool guardedUpload(void *const header) noexcept
        {
            __try
            {
                Upload(header, header);
                return true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return false;
            }
        }

        [[nodiscard]] bool guardedLink(void **const slot, void **const entryOut) noexcept
        {
            __try
            {
                *entryOut = Link(OlfinalGfxImageAssetType, slot);
                return true;
            }
            __except (EXCEPTION_EXECUTE_HANDLER)
            {
                return false;
            }
        }

        [[nodiscard]] ForgeImageUploadStatus uploadOne(Job &job, ForgeImageUploadRecord &record)
        {
            auto *const header = static_cast<std::uint8_t *>(job.image->header());
            void *const loadDef = job.image->storage.data() + job.image->loadDefOffset;

            const std::uint32_t slot = FiberSlot ? FiberSlot() : 0xFFFFFFFFu;
            record.fiberSlot = slot;
            if (slot != 1)
            {
                // sub_67C170 reaches Error("1190") when the slot is wrong, and an
                // error dialog is a worse outcome than not uploading.
                record.detail = "fiber slot " + std::to_string(slot) + ", expected 1";
                return ForgeImageUploadStatus::WrongFiberSlot;
            }
            if (!rendererAcceptsUploads())
            {
                record.detail = "the dvar sub_BE7470 gates on reads zero";
                return ForgeImageUploadStatus::RendererClosed;
            }

            // The load def arrives at +0; sub_BE7470 relocates it to +0x2C and
            // leaves the texture in +0.
            std::memcpy(header + OlfinalGfxImageLoadDefSlot, &loadDef, sizeof(loadDef));

            if (!guardedUpload(header))
            {
                record.detail = "sub_BE7470 faulted";
                return ForgeImageUploadStatus::UploadFaulted;
            }

            void *texture{};
            std::memcpy(&texture, header + OlfinalGfxImageLoadDefSlot, sizeof(texture));
            record.texture = reinterpret_cast<std::uintptr_t>(texture);
            if (texture == nullptr)
            {
                // sub_BE6F40 writes 0 back when CreateTexture fails, which is the
                // only signal it gives.
                record.detail = "CreateTexture produced nothing";
                return ForgeImageUploadStatus::NoTexture;
            }

            if (!job.link)
                return ForgeImageUploadStatus::Published;
            if (Link == nullptr)
            {
                record.detail = "DB_LinkXAssetEntry was not resolved";
                return ForgeImageUploadStatus::LinkRefused;
            }

            void *slotValue = header;
            void *entry{};
            if (!guardedLink(&slotValue, &entry))
            {
                record.detail = "DB_LinkXAssetEntry faulted";
                return ForgeImageUploadStatus::LinkFaulted;
            }
            record.published = reinterpret_cast<std::uintptr_t>(slotValue);
            if (entry == nullptr || slotValue == nullptr)
            {
                record.detail = "DB_LinkXAssetEntry returned nothing";
                return ForgeImageUploadStatus::LinkRefused;
            }
            return ForgeImageUploadStatus::Published;
        }

        // ------------------------------------------------------------------
        // The chain: images, then materials, then models.

        struct ChainState
        {
            bool active = false;
            ForgeChainPhase phase = ForgeChainPhase::Idle;
            std::filesystem::path root;
            std::string cloneSource;
            SvForgeBundle bundle;
            std::vector<std::string> models;        // wanted, resolved
            std::vector<std::string> materials;     // wanted, in dependency order
            std::vector<ForgeChainStep> steps;
            // Published assets are never released: the engine keeps the pointers
            // inside the headers it copied.
            std::vector<std::unique_ptr<SvForgeMaterialAsset>> retainedMaterials;
            std::vector<std::unique_ptr<SvForgeXModelAsset>> retainedModels;
        };

        ChainState Chain;
        std::mutex ChainMutex;

        void note(const std::string &what, const bool ok, const std::string &detail)
        {
            Chain.steps.push_back(ForgeChainStep{ what, ok, detail });
        }

        [[nodiscard]] std::uint8_t semanticFor(const std::string &sampler) noexcept
        {
            if (sampler == "normalMap")
                return 5;
            if (sampler == "specularMap")
                return 8;
            return 2;   // colorMap, and anything a port has no measurement for
        }

        [[nodiscard]] std::uintptr_t hostBase() noexcept
        {
            return reinterpret_cast<std::uintptr_t>(GetModuleHandleW(nullptr));
        }

        [[nodiscard]] SvForgeXAnimBindings chainBindings() noexcept
        {
            SvForgeXAnimBindings b;
            b.dbLinkXAssetEntry =
                reinterpret_cast<void *>(hostBase() + DBLinkXAssetEntryRva);
            return b;
        }

        // One material: read the clone out of the client, rebind its slots by
        // nameHash, publish. The clone's own memory is only READ.
        bool publishOneMaterial(const SvForgeMaterial &material, std::string &error)
        {
            const auto table = SV_ForgeXAssetTableFor(hostBase());
            void *const clone = SV_ForgeFindXAsset(table, OlfinalMaterialAssetType,
                                                   Chain.cloneSource);
            if (clone == nullptr)
            {
                error = "the clone '" + Chain.cloneSource + "' is not in this client";
                return false;
            }
            const auto *const cloneBytes = static_cast<const std::byte *>(clone);
            const auto slotCount =
                std::to_integer<std::uint8_t>(cloneBytes[OffMtlTextureCount]);
            const std::byte *cloneTable{};
            std::memcpy(&cloneTable, cloneBytes + OffMtlTextureTable, sizeof(cloneTable));
            if (slotCount == 0 || cloneTable == nullptr)
            {
                error = "the clone has no texture table";
                return false;
            }

            std::vector<SvForgeMaterialSlot> slots;
            slots.reserve(material.textures.size());
            for (const auto &t : material.textures)
                slots.push_back(SvForgeMaterialSlot{ t.semantic, t.image });

            const auto resolveImage = SV_ForgeImageTableResolver(hostBase());
            if (!resolveImage)
            {
                error = "no image resolver";
                return false;
            }
            auto built = SV_BuildForgeMaterial(
                material.name,
                std::span<const std::byte>{ cloneBytes, MaterialHeaderBytes },
                std::span<const std::byte>{ cloneTable,
                                            TextureDefBytes * static_cast<std::size_t>(slotCount) },
                slots, resolveImage, error);
            if (!built)
                return false;

            auto owned = std::make_unique<SvForgeMaterialAsset>(std::move(*built));
            const auto status = SV_PublishForgeMaterial(*owned, chainBindings(), error);
            if (status != SvForgeXAnimStatus::Ready)
            {
                error = std::string(SV_ForgeXAnimStatusName(status)) + ": " + error;
                return false;
            }
            Chain.retainedMaterials.push_back(std::move(owned));
            return true;
        }

        bool publishOneModel(const SvForgeModel &model, std::string &error)
        {
            const auto skeleton = Chain.bundle.skeletons.find(model.skeletonKey);
            if (skeleton == Chain.bundle.skeletons.end())
            {
                error = "no skeleton '" + model.skeletonKey + "'";
                return false;
            }
            SvForgeModelRef ref;
            ref.name = model.name;
            // The bundle carries the 360 bytes as a fixed array; the ref wants
            // a vector, and the size check belongs to SV_BuildForgeXModel.
            ref.header.assign(model.header.begin(), model.header.end());
            ref.boneNames = skeleton->second.boneNames;
            ref.parentList = skeleton->second.parentList;
            ref.quaternions = skeleton->second.quaternions;
            ref.translations = skeleton->second.translations;
            ref.partClassification = skeleton->second.partClassification;
            ref.baseMatrices = skeleton->second.baseMatrices;
            ref.materials = model.materials;
            if (!model.resources.empty())
                ref.resource = model.resources.front();

            const auto resolveString = SV_ForgeStringTableResolver(hostBase());
            const auto resolveMaterial = SV_ForgeMaterialTableResolver(hostBase());
            if (!resolveString || !resolveMaterial)
            {
                error = "no string or material resolver";
                return false;
            }
            auto built = SV_BuildForgeXModel(ref, resolveString, resolveMaterial, error);
            if (!built)
                return false;

            auto owned = std::make_unique<SvForgeXModelAsset>(std::move(*built));
            const auto status = SV_PublishForgeXModel(*owned, chainBindings(), error);
            if (status != SvForgeXAnimStatus::Ready)
            {
                error = std::string(SV_ForgeXAnimStatusName(status)) + ": " + error;
                return false;
            }
            Chain.retainedModels.push_back(std::move(owned));
            return true;
        }

        // Runs on the render thread, after the image queue has drained.
        void pumpChain()
        {
            std::unique_lock lock(ChainMutex, std::try_to_lock);
            if (!lock.owns_lock() || !Chain.active)
                return;
            if (Chain.phase == ForgeChainPhase::Images)
            {
                if (PendingCount.load(std::memory_order_relaxed) != 0)
                    return;
                Chain.phase = ForgeChainPhase::Materials;
                return;   // one step per frame, so a stall is visible in the phase
            }
            if (Chain.phase == ForgeChainPhase::Materials)
            {
                if (Chain.materials.empty())
                {
                    Chain.phase = ForgeChainPhase::Models;
                    return;
                }
                const auto name = Chain.materials.front();
                Chain.materials.erase(Chain.materials.begin());
                const auto it = std::find_if(
                    Chain.bundle.materials.begin(), Chain.bundle.materials.end(),
                    [&name](const SvForgeMaterial &m) { return m.name == name; });
                std::string error;
                const bool ok = it != Chain.bundle.materials.end() &&
                    publishOneMaterial(*it, error);
                note("material " + name, ok, ok ? std::string{} : error);
                return;
            }
            if (Chain.phase == ForgeChainPhase::Models)
            {
                if (Chain.models.empty())
                {
                    Chain.phase = ForgeChainPhase::Done;
                    Chain.active = false;
                    return;
                }
                const auto name = Chain.models.front();
                Chain.models.erase(Chain.models.begin());
                const auto it = std::find_if(
                    Chain.bundle.models.begin(), Chain.bundle.models.end(),
                    [&name](const SvForgeModel &m) { return m.name == name; });
                std::string error;
                const bool ok = it != Chain.bundle.models.end() &&
                    publishOneModel(*it, error);
                note("model " + name, ok, ok ? std::string{} : error);
                return;
            }
        }

        // Runs on the render thread, once per frame, before BeginScene.
        void __cdecl pumpImageUploads()
        {
            if (PendingCount.load(std::memory_order_relaxed) == 0)
            {
                // The images are done; the materials and models can go now.
                pumpChain();
                return;
            }

            Job job;
            {
                // try_lock: a queueing thread must never be able to stall a frame.
                std::unique_lock lock(QueueMutex, std::try_to_lock);
                if (!lock.owns_lock() || Pending.empty())
                    return;
                job = std::move(Pending.front());
                Pending.erase(Pending.begin());
                PendingCount.store(Pending.size(), std::memory_order_relaxed);
            }
            if (!job.image)
                return;

            // ONE PER FRAME. A 512x512 DXT5 chain is 349,552 bytes through
            // LockRect and UpdateTexture; six of those in one frame is a hitch.
            ForgeImageUploadRecord record;
            record.name = job.image->name;
            record.status = uploadOne(job, record);

            {
                const std::lock_guard lock(QueueMutex);
                Records.push_back(record);
                Retained.push_back(std::move(job.image));
            }
        }

        __declspec(naked) void renderFrameHook()
        {
            // Transparent by construction: run the pump, then tail-jump to the
            // original with the stack exactly as the call site left it, so its own
            // `retn` returns to 0x00BE2213 and the caller's `add esp, 4` still
            // balances. Nothing here needs to know sub_BE2150's signature.
            __asm
            {
                pushad
                pushfd
                call pumpImageUploads
                popfd
                popad
                jmp dword ptr [RenderBegin]
            }
        }

        [[nodiscard]] std::uint8_t *hostModule(std::uint32_t &imageSize) noexcept
        {
            auto *const module = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
            if (module == nullptr)
                return nullptr;
            const auto *const dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(module);
            if (dos->e_magic != IMAGE_DOS_SIGNATURE)
                return nullptr;
            const auto *const nt =
                reinterpret_cast<const IMAGE_NT_HEADERS *>(module + dos->e_lfanew);
            if (nt->Signature != IMAGE_NT_SIGNATURE)
                return nullptr;
            imageSize = nt->OptionalHeader.SizeOfImage;
            return module;
        }

        [[nodiscard]] std::uint8_t semanticForName(const std::string &name) noexcept
        {
            if (name.size() >= 2)
            {
                const auto tail = name.substr(name.size() - 2);
                if (tail == "_n")
                    return 5;
                if (tail == "_s")
                    return 8;
                if (tail == "_c")
                    return 2;
            }
            // The CoD4 pipeline mangles combined maps into `~<name>_s-...~<hash>`,
            // so the suffix is gone but the role is still readable.
            if (name.find("_s-") != std::string::npos)
                return 8;
            if (name.find("_n-") != std::string::npos)
                return 5;
            return 2;
        }
    }

    const char *renderFrameHookResultName(const RenderFrameHookResult result) noexcept
    {
        switch (result)
        {
        case RenderFrameHookResult::Installed: return "Installed";
        case RenderFrameHookResult::AlreadyInstalled: return "AlreadyInstalled";
        case RenderFrameHookResult::Disabled: return "Disabled";
        case RenderFrameHookResult::UnsupportedHost: return "UnsupportedHost";
        case RenderFrameHookResult::UnexpectedBytes: return "UnexpectedBytes";
        case RenderFrameHookResult::ProtectionFailed: return "ProtectionFailed";
        }
        return "Unknown";
    }

    const char *forgeImageUploadStatusName(const ForgeImageUploadStatus s) noexcept
    {
        switch (s)
        {
        case ForgeImageUploadStatus::Queued: return "Queued";
        case ForgeImageUploadStatus::WrongFiberSlot: return "WrongFiberSlot";
        case ForgeImageUploadStatus::RendererClosed: return "RendererClosed";
        case ForgeImageUploadStatus::UploadFaulted: return "UploadFaulted";
        case ForgeImageUploadStatus::NoTexture: return "NoTexture";
        case ForgeImageUploadStatus::LinkFaulted: return "LinkFaulted";
        case ForgeImageUploadStatus::LinkRefused: return "LinkRefused";
        case ForgeImageUploadStatus::Published: return "Published";
        }
        return "Unknown";
    }

    RenderFrameHookResult installClientRenderFrameHook()
    {
        if (Installed.load())
            return RenderFrameHookResult::AlreadyInstalled;

        std::array<char, 8> value{};
        const auto size =
            GetEnvironmentVariableA("CODOL_IMAGE_UPLOAD_HOOK", value.data(), value.size());
        const auto enabled = size && value[0] != '0' && value[0] != 'n' &&
            value[0] != 'N' && value[0] != 'f' && value[0] != 'F';
        if (!enabled)
            return RenderFrameHookResult::Disabled;

        std::uint32_t imageSize = 0;
        auto *const module = hostModule(imageSize);
        if (module == nullptr)
            return RenderFrameHookResult::UnsupportedHost;
        if (RenderFrameCallSiteRva + OriginalCall.size() > imageSize ||
            RenderFrameTargetRva >= imageSize ||
            ImageUploadRva >= imageSize ||
            FiberSlotRva >= imageSize ||
            LoadForRendererDvarRva >= imageSize ||
            DBLinkXAssetEntryRva >= imageSize)
        {
            return RenderFrameHookResult::UnsupportedHost;
        }

        auto *const site = module + RenderFrameCallSiteRva;
        // VERIFY BEFORE WRITING. A build whose bytes differ is a build these
        // offsets were not derived from.
        if (!std::equal(OriginalCall.begin(), OriginalCall.end(), site))
            return RenderFrameHookResult::UnexpectedBytes;

        RenderBegin = module + RenderFrameTargetRva;
        Upload = reinterpret_cast<ImageUploadFn>(module + ImageUploadRva);
        FiberSlot = reinterpret_cast<FiberSlotFn>(module + FiberSlotRva);
        Link = reinterpret_cast<LinkFn>(module + DBLinkXAssetEntryRva);
        LoadForRendererDvar =
            reinterpret_cast<const std::uint32_t **>(module + LoadForRendererDvarRva);

        const auto target = reinterpret_cast<std::uintptr_t>(&renderFrameHook);
        const auto next = reinterpret_cast<std::uintptr_t>(site) + OriginalCall.size();
        const auto relative = static_cast<std::int32_t>(target - next);

        std::array<std::uint8_t, 5> replacement{ 0xE8 };
        std::memcpy(replacement.data() + 1, &relative, sizeof(relative));

        DWORD oldProtection{};
        if (!VirtualProtect(site, replacement.size(), PAGE_EXECUTE_READWRITE, &oldProtection))
            return RenderFrameHookResult::ProtectionFailed;
        std::copy(replacement.begin(), replacement.end(), site);
        FlushInstructionCache(GetCurrentProcess(), site, replacement.size());
        DWORD ignored{};
        VirtualProtect(site, replacement.size(), oldProtection, &ignored);

        Installed.store(true);
        return RenderFrameHookResult::Installed;
    }

    bool queueForgeImageUpload(std::unique_ptr<SvForgeGfxImage> image, const bool link)
    {
        if (!Installed.load() || !image)
            return false;
        const std::lock_guard lock(QueueMutex);
        Pending.push_back(Job{ std::move(image), link });
        PendingCount.store(Pending.size(), std::memory_order_relaxed);
        return true;
    }

    std::size_t forgeImageUploadPending() noexcept
    {
        return PendingCount.load(std::memory_order_relaxed);
    }

    std::vector<ForgeImageUploadRecord> forgeImageUploadReport()
    {
        const std::lock_guard lock(QueueMutex);
        return Records;
    }

    const char *forgeChainPhaseName(const ForgeChainPhase phase) noexcept
    {
        switch (phase)
        {
        case ForgeChainPhase::Idle: return "Idle";
        case ForgeChainPhase::Images: return "Images";
        case ForgeChainPhase::Materials: return "Materials";
        case ForgeChainPhase::Models: return "Models";
        case ForgeChainPhase::Done: return "Done";
        case ForgeChainPhase::Failed: return "Failed";
        }
        return "Unknown";
    }

    bool queueForgeChain(const ForgeChainRequest &request, std::string &error)
    {
        if (!Installed.load())
        {
            error = "the render-frame hook is not installed";
            return false;
        }
        auto bundle = SV_LoadForgeBundle(request.bundlePath, error);
        if (!bundle)
            return false;
        if (request.cloneSource.empty())
        {
            error = "no clone source; a Material is cloned, never authored";
            return false;
        }

        const std::filesystem::path bundleFile{ request.bundlePath };
        const auto root = bundleFile.parent_path();

        // Which models, and then the materials and images they transitively name.
        // Resolving it this way means a request for one model publishes exactly
        // what that model needs and nothing else.
        std::vector<std::string> models;
        for (const auto &m : bundle->models)
        {
            if (request.models.empty() ||
                std::find(request.models.begin(), request.models.end(), m.name) !=
                    request.models.end())
            {
                models.push_back(m.name);
            }
        }
        if (models.empty())
        {
            error = "the request names no model in the bundle";
            return false;
        }

        std::vector<std::string> materials;
        std::vector<std::string> images;
        for (const auto &modelName : models)
        {
            const auto model = std::find_if(
                bundle->models.begin(), bundle->models.end(),
                [&modelName](const SvForgeModel &m) { return m.name == modelName; });
            if (model == bundle->models.end())
                continue;
            for (const auto &materialName : model->materials)
            {
                if (std::find(materials.begin(), materials.end(), materialName) !=
                    materials.end())
                {
                    continue;
                }
                const auto material = std::find_if(
                    bundle->materials.begin(), bundle->materials.end(),
                    [&materialName](const SvForgeMaterial &m) { return m.name == materialName; });
                if (material == bundle->materials.end())
                {
                    error = "model '" + modelName + "' names material '" +
                        materialName + "', which the bundle does not carry";
                    return false;
                }
                materials.push_back(materialName);
                for (const auto &texture : material->textures)
                {
                    if (std::find(images.begin(), images.end(), texture.image) == images.end())
                        images.push_back(texture.image);
                }
            }
        }

        // Build every image BEFORE queueing anything, so a bad one refuses the
        // whole request rather than leaving the client half published.
        std::vector<std::unique_ptr<SvForgeGfxImage>> built;
        for (const auto &imageName : images)
        {
            const auto file = root / "main" / "images" / (imageName + ".iwi");
            std::ifstream in(file, std::ios::binary);
            if (!in)
            {
                error = "cannot open " + file.string();
                return false;
            }
            in.seekg(0, std::ios::end);
            const auto length = in.tellg();
            in.seekg(0, std::ios::beg);
            std::vector<std::byte> bytes(
                length > 0 ? static_cast<std::size_t>(length) : 0u);
            if (!bytes.empty())
            {
                in.read(reinterpret_cast<char *>(bytes.data()),
                        static_cast<std::streamsize>(bytes.size()));
            }
            if (bytes.empty() || !in)
            {
                error = "cannot read " + file.string();
                return false;
            }

            SvForgeImageRequest imageRequest;
            imageRequest.name = imageName;
            imageRequest.semantic = 2;
            for (const auto &materialName : materials)
            {
                const auto material = std::find_if(
                    bundle->materials.begin(), bundle->materials.end(),
                    [&materialName](const SvForgeMaterial &m) { return m.name == materialName; });
                if (material == bundle->materials.end())
                    continue;
                for (const auto &texture : material->textures)
                {
                    if (texture.image == imageName)
                        imageRequest.semantic = semanticFor(texture.semantic);
                }
            }
            auto image = SV_BuildForgeGfxImageFromIwi(bytes, imageRequest, error);
            if (!image)
            {
                error = imageName + ": " + error;
                return false;
            }
            built.push_back(std::make_unique<SvForgeGfxImage>(std::move(*image)));
        }

        {
            const std::lock_guard lock(ChainMutex);
            Chain.root = root;
            Chain.cloneSource = request.cloneSource;
            Chain.bundle = std::move(*bundle);
            Chain.models = std::move(models);
            Chain.materials = std::move(materials);
            Chain.steps.clear();
            Chain.phase = ForgeChainPhase::Images;
            Chain.active = true;
        }
        for (auto &image : built)
        {
            const auto name = image->name;
            if (!queueForgeImageUpload(std::move(image), /*link=*/true))
            {
                error = "the render-frame hook refused image " + name;
                return false;
            }
        }
        return true;
    }

    ForgeChainPhase forgeChainPhase() noexcept
    {
        const std::lock_guard lock(ChainMutex);
        return Chain.phase;
    }

    std::vector<ForgeChainStep> forgeChainSteps()
    {
        const std::lock_guard lock(ChainMutex);
        return Chain.steps;
    }

    ForgeImageDirectoryReport queueForgeImageDirectory(const std::string &directory)
    {
        ForgeImageDirectoryReport report;
        std::error_code ec;
        const std::filesystem::path root{ directory };
        if (!std::filesystem::is_directory(root, ec))
        {
            report.failures.emplace_back(directory, "not a directory");
            return report;
        }

        std::vector<std::filesystem::path> files;
        for (const auto &entry : std::filesystem::directory_iterator(root, ec))
        {
            if (!entry.is_regular_file(ec))
                continue;
            auto ext = entry.path().extension().string();
            std::transform(ext.begin(), ext.end(), ext.begin(),
                           [](const unsigned char c) { return static_cast<char>(std::tolower(c)); });
            if (ext == ".iwi")
                files.push_back(entry.path());
        }
        std::sort(files.begin(), files.end());
        report.found = files.size();

        for (const auto &file : files)
        {
            const auto label = file.filename().string();
            std::ifstream in(file, std::ios::binary);
            if (!in)
            {
                report.failures.emplace_back(label, "cannot open");
                continue;
            }
            in.seekg(0, std::ios::end);
            const auto length = in.tellg();
            in.seekg(0, std::ios::beg);
            std::vector<std::byte> bytes(
                length > 0 ? static_cast<std::size_t>(length) : 0u);
            if (!bytes.empty())
                in.read(reinterpret_cast<char *>(bytes.data()),
                        static_cast<std::streamsize>(bytes.size()));
            if (bytes.empty() || !in)
            {
                report.failures.emplace_back(label, "empty");
                continue;
            }

            SvForgeImageRequest request;
            request.name = file.stem().string();
            request.semantic = semanticForName(request.name);
            std::string error;
            auto built = SV_BuildForgeGfxImageFromIwi(bytes, request, error);
            if (!built)
            {
                report.failures.emplace_back(label, error);
                continue;
            }
            auto owned = std::make_unique<SvForgeGfxImage>(std::move(*built));
            if (!queueForgeImageUpload(std::move(owned), /*link=*/true))
            {
                report.failures.emplace_back(label, "the render-frame hook is not installed");
                continue;
            }
            ++report.queued;
        }
        return report;
    }
}
