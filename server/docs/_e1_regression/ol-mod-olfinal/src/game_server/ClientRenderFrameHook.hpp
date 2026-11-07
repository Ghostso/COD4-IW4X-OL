#pragma once

// THE RENDER-FRAME HOOK, and the GfxImage upload that needs it.
//
// WHY A SECOND FRAME HOOK. ol-mod already hooks Com_Frame (`FrameHook.cpp`), and
// that is the right place for game-server work. It is the WRONG place for a
// Direct3D call, and the client says so outright:
//
//     device BehaviorFlags   0x42   FPU_PRESERVE | HARDWARE_VERTEXPROCESSING
//                                   - no D3DCREATE_MULTITHREADED
//     thread 16016           Com_Frame 0x4FEA20               923 calls / 5s
//     thread 43208           sub_BE21F0 0xBE21F0              923 calls / 5s
//                            and every BeginScene, Clear and SetRenderTarget
//
// Measured 2026-09-09. The two run in exact lockstep, one render frame per
// Com_Frame, on DIFFERENT threads. Without D3DCREATE_MULTITHREADED every call on
// the device has to come from the thread that made it, so an upload driven from
// the Com_Frame callback would be calling the device off-thread.
//
// THE SITE. `sub_BE21F0` is the render backend's per-frame function; at +0x1E it
// calls `sub_BE2150`, which is what calls BeginScene:
//
//     00BE220B  50              push eax
//     00BE220C  8B D8           mov  ebx, eax
//     00BE220E  E8 3D FF FF FF  call sub_BE2150     ; <- the five bytes replaced
//     00BE2213  83 C4 04        add  esp, 4         ; CALLER cleanup, cdecl
//
// One five-byte call redirect, the same shape and the same discipline as
// `ClientAnimtreeHook`: the original bytes are verified before anything is
// written and a mismatch refuses rather than patching. The replacement runs the
// pump and then TAIL-JUMPS to sub_BE2150 with the stack untouched, so the
// original's own `retn` returns straight to the call site. That makes the hook
// convention-agnostic - it never has to know how many arguments sub_BE2150 takes.
//
// It runs BEFORE BeginScene, which is where a texture upload belongs.
//
// THE FIBER CONTEXT. `sub_BE7470` opens with `sub_67C170(1, sub_BE0900)`, a fiber
// switch rather than a thread hop. It returns immediately when the caller is
// already on context 1, and otherwise yields until `sub_BE0900` is true. Measured
// from the render frame, `sub_67C080()` - the same slot computation sub_67C170
// uses - returns 1, and `sub_BE0900` is `sub_67CCE0() || sub_67C080() == 1`, so
// the predicate is ALREADY satisfied there. The pump reads the slot anyway and
// refuses if it is not 1, because the failure mode of guessing is Error("1190").
//
// PROVEN. On 2026-09-09 this exact sequence - staged blob, sub_BE7470 from inside
// a render-frame callback, then DB_LinkXAssetEntry(10) - published seven PPSh
// images into a live client. `image+0` went from the load-def pointer to a real
// IDirect3DTexture9 whose vtable (0x6c6f1438) is byte-identical to the one every
// shipped image carries, the load def relocated to +0x2C, category went 3 -> 11
// (the +8 the staging path adds), all 52 header bytes survived the link, and the
// XAsset entry table found each name afterwards. That run was driven through
// Frida (`tools/runtime/CodolForgeImageProbe.py`) because it needed no rebuild;
// THIS code is the same sequence in the DLL and has not itself been run yet.

#include "server_mp/sv_forge_image_mp.hpp"

#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace CodolGameServer
{
    enum class RenderFrameHookResult
    {
        Installed,
        AlreadyInstalled,
        Disabled,
        UnsupportedHost,
        UnexpectedBytes,
        ProtectionFailed,
    };

    [[nodiscard]] const char *renderFrameHookResultName(RenderFrameHookResult result) noexcept;

    // DEFAULT OFF, set CODOL_IMAGE_UPLOAD_HOOK=1 to enable. A patch that rewrites
    // the client's own render loop opts in explicitly rather than shipping on.
    [[nodiscard]] RenderFrameHookResult installClientRenderFrameHook();

    enum class ForgeImageUploadStatus : std::uint32_t
    {
        Queued,
        WrongFiberSlot,   // the render frame was not on slot 1 after all
        RendererClosed,   // the dvar sub_BE7470 gates on reads zero
        UploadFaulted,
        NoTexture,        // sub_BE7470 returned but image+0 is still null
        LinkFaulted,
        LinkRefused,
        Published,
    };

    [[nodiscard]] const char *forgeImageUploadStatusName(ForgeImageUploadStatus s) noexcept;

    struct ForgeImageUploadRecord
    {
        std::string name;
        ForgeImageUploadStatus status = ForgeImageUploadStatus::Queued;
        std::uint32_t fiberSlot = 0;
        std::uintptr_t texture = 0;
        std::uintptr_t published = 0;
        std::string detail;
    };

    // Hands an image to the render thread. The image is MOVED and kept alive for
    // the life of the process: the engine copies the 52-byte header but keeps the
    // pointers inside it, so the storage can never be released.
    //
    // Returns false when the hook is not installed - queueing against a hook that
    // will never run is a silent hang, not a deferral.
    [[nodiscard]] bool queueForgeImageUpload(
        std::unique_ptr<SvForgeGfxImage> image, bool link);

    [[nodiscard]] std::size_t forgeImageUploadPending() noexcept;
    [[nodiscard]] std::vector<ForgeImageUploadRecord> forgeImageUploadReport();

    // Builds every *.iwi in a directory and queues it. Gated on the directory
    // existing, which is how this path is exercised without a bundle: set
    // CODOL_FORGE_IMAGE_DIR and the images publish on the next few render frames.
    //
    // The semantic is taken from the name's suffix - _c colour 2, _n normal 5,
    // _s specular 8 - which is what the shipped MaterialTextureDefs carry, and
    // what the PPSh's own materials expect of these six names.
    struct ForgeImageDirectoryReport
    {
        std::size_t found = 0;
        std::size_t queued = 0;
        std::vector<std::pair<std::string, std::string>> failures;   // file, why
    };

    [[nodiscard]] ForgeImageDirectoryReport queueForgeImageDirectory(
        const std::string &directory);

    // ------------------------------------------------------------------
    // The whole chain, from inside the client.
    //
    // WHY THIS EXISTS. Publishing from an injected thread works and was proven
    // asset type by asset type, but it does not SURVIVE: a zone transition removes
    // Material, GfxImage and XAnimParts entries and rewrites XModels as the
    // missing-model default, and a name that already exists cannot be re-pointed
    // by linking. Every run from outside therefore races the next map load.
    //
    // Publishing from in here does not have that problem, because it can happen
    // AFTER the zone the client is about to run - the render-frame hook is the
    // first thing that runs every frame, and by the time it does, the map's own
    // assets are already loaded.
    //
    // ORDER MATTERS and is enforced by phase: images have to exist before a
    // material can bind them, and materials before a model can name them. The
    // pump does one image per frame, then the materials, then the models.

    struct ForgeChainRequest
    {
        std::string bundlePath;    // <staging>/bundle.json
        // A shipped Material to clone. Its slot set has to cover the port's:
        // `mc/mtl_t6_wpn_pda` carries colorMap, normalMap and specularMap, which
        // is what the PPSh's two weapon materials need.
        std::string cloneSource;
        // Empty means "every model in the bundle", and the materials and images
        // those models transitively name.
        std::vector<std::string> models;
    };

    enum class ForgeChainPhase : std::uint32_t
    {
        Idle,
        Images,
        Materials,
        Models,
        Done,
        Failed,
    };

    [[nodiscard]] const char *forgeChainPhaseName(ForgeChainPhase phase) noexcept;

    struct ForgeChainStep
    {
        std::string what;     // "image t4_ppsh41_base_c", "material ...", "model ..."
        bool ok = false;
        std::string detail;
    };

    // Reads the bundle, stages every image the requested models need, and queues
    // the three phases. Returns false and sets `error` if the bundle cannot be
    // read or the request names nothing publishable - nothing is queued in that
    // case, so a bad request cannot leave a half-published client.
    [[nodiscard]] bool queueForgeChain(const ForgeChainRequest &request, std::string &error);

    [[nodiscard]] ForgeChainPhase forgeChainPhase() noexcept;
    [[nodiscard]] std::vector<ForgeChainStep> forgeChainSteps();

    // RVAs against image base 0x400000.
    inline constexpr std::size_t RenderFrameCallSiteRva = 0x7E220E;  // 0x00BE220E
    inline constexpr std::size_t RenderFrameTargetRva = 0x7E2150;    // 0x00BE2150
    inline constexpr std::size_t ImageUploadRva = 0x7E7470;          // 0x00BE7470
    inline constexpr std::size_t FiberSlotRva = 0x27C080;            // 0x0067C080
    // sub_BE7470 does nothing at all unless *(dvar + 12) is non-zero.
    inline constexpr std::size_t LoadForRendererDvarRva = 0xA899CC;  // 0x00E899CC
}
