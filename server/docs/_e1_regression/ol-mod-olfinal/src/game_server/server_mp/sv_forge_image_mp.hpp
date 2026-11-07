#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace CodolGameServer
{
    // OLMOD(forge-image): GfxImage (asset type 10), the one asset type that
    // CANNOT be published by linking alone.
    //
    // The other four are pure data: DB_LinkXAssetEntry copies the header, inserts
    // it in the hash, and the asset is live. An image is not, because the field
    // the renderer samples is a GPU resource that does not exist until something
    // creates it:
    //
    //   sub_487380 (Load_GfxImage) reads 52 bytes with the load-def pointer at +0
    //   sub_4872A0 fixes that pointer up and calls sub_BE7470(image, image)
    //   sub_BE7470 RELOCATES the load def from +0 to +0x2C, clears +0, creates an
    //              IDirect3DTexture9, copies every mip level into it, and stores
    //              the texture back into +0.
    //
    // So a linked-but-not-uploaded image carries a load definition in a field the
    // renderer dereferences as a texture. It would not fail to draw; it would
    // follow a bogus vtable.
    //
    // MEASURED on a live client 2026-09-09: the device's BehaviorFlags are 0x42
    // (FPU_PRESERVE | HARDWARE_VERTEXPROCESSING) - NO D3DCREATE_MULTITHREADED -
    // and its calls come from a thread that is not the one running Com_Frame.
    // That is why the upload rides `ClientRenderFrameHook` rather than the frame
    // hook ol-mod already had.
    //
    // THIS FILE IS THE PURE HALF: parsing an .iwi and laying out the header, the
    // load definition and the mip payload. It makes no engine call and is fully
    // unit-tested. The engine call lives in ClientRenderFrameHook.

    // ------------------------------------------------------------------
    // The engine's own size arithmetic, reproduced exactly.

    // sub_BE8690(format, w, h, d) - bytes for ONE mip level. Returns 0 for a
    // format the client cannot size, which is always fatal.
    [[nodiscard]] std::uint32_t SV_ForgeImageLevelBytes(
        std::uint32_t d3dFormat,
        std::uint32_t width,
        std::uint32_t height,
        std::uint32_t depth) noexcept;

    // sub_BE8C30(flags, w, h, d) - how many levels sub_BE7470 will WALK. Only the
    // low byte of `flags` is read, and only bit 1: set means one level, clear
    // means the full chain counted by doubling until it covers every dimension.
    [[nodiscard]] std::uint32_t SV_ForgeImageLevelCount(
        std::uint32_t flags,
        std::uint32_t width,
        std::uint32_t height,
        std::uint32_t depth) noexcept;

    // The whole payload: faces outer, levels inner, each dimension clamped at 1.
    // `sub_BE7470` advances one cursor across all of it without resetting between
    // faces, so this IS the byte count it will read.
    [[nodiscard]] std::uint64_t SV_ForgeImagePayloadBytes(
        std::uint32_t d3dFormat,
        std::uint32_t flags,
        std::uint32_t width,
        std::uint32_t height,
        std::uint32_t depth,
        bool cubemap) noexcept;

    // ------------------------------------------------------------------
    // The .iwi side.

    // IWI pixel format -> D3DFORMAT. Returns 0 for anything this path refuses.
    //
    // Note X8R8G8B8: the file stores three bytes per pixel and D3DFMT_X8R8G8B8 is
    // four, so it is NOT a straight copy and is refused rather than silently
    // producing a sheared image. None of the PPSh's eleven images use it.
    [[nodiscard]] std::uint32_t SV_ForgeIwiFormatToD3D(std::uint8_t iwiFormat) noexcept;

    struct SvForgeImageSource
    {
        std::uint8_t version = 0;
        std::uint8_t iwiFormat = 0;
        std::uint32_t d3dFormat = 0;
        std::uint16_t width = 0;
        std::uint16_t height = 0;
        std::uint16_t depth = 0;
        bool cubemap = false;
        std::uint32_t storedLevels = 0;      // levels actually present in the file
        std::uint32_t fullLevels = 0;        // levels a complete chain would have
        std::size_t headerSize = 0;
        std::size_t payloadOffset = 0;
        std::size_t payloadBytes = 0;
        // v6 stores the chain largest-first, which is the order sub_BE7470 walks.
        // v8/v9 store it smallest-first and have to be reversed.
        bool storedSmallestFirst = false;
    };

    // Pure. Accepts only when the level count whose running total equals the
    // payload EXACTLY exists - prefix sums are strictly increasing, so at most one
    // count can match, which decides rather than guesses.
    [[nodiscard]] std::optional<SvForgeImageSource> SV_ParseForgeIwi(
        std::span<const std::byte> file,
        std::string &error);

    // ------------------------------------------------------------------
    // The asset.

    // A built GfxImage. Storage holds the 52-byte header, the name, the 16-byte
    // load definition and the mip payload contiguously; the header's pointers
    // point INTO it, so it must outlive the client and must never be moved.
    struct SvForgeGfxImage
    {
        std::vector<std::byte> storage;
        std::string name;
        std::uint32_t d3dFormat = 0;
        std::uint32_t flags = 0;
        std::uint16_t width = 0;
        std::uint16_t height = 0;
        std::uint32_t levels = 0;
        std::size_t loadDefOffset = 0;
        std::size_t payloadOffset = 0;
        std::size_t payloadBytes = 0;

        [[nodiscard]] void *header() noexcept
        {
            return storage.empty() ? nullptr : storage.data();
        }
        [[nodiscard]] const void *header() const noexcept
        {
            return storage.empty() ? nullptr : storage.data();
        }
    };

    struct SvForgeImageRequest
    {
        std::string name;
        std::uint8_t semantic = 2;   // 2 colour, 5 normal, 8 specular - the values
                                     // the shipped MaterialTextureDefs carry
        std::uint8_t category = 3;   // shipped textures load as 3 and the upload
                                     // adds 8, which is why they read back as 11
    };

    // Pure. Builds header + load def + payload from a parsed .iwi and its bytes.
    //
    // REFUSES a partial mip chain. `sub_BE8C30` can only answer "one level" or
    // "the full chain", so a file storing some other number of levels would make
    // the engine walk past the payload. Every PPSh image is one or the other.
    [[nodiscard]] std::optional<SvForgeGfxImage> SV_BuildForgeGfxImage(
        std::span<const std::byte> file,
        const SvForgeImageSource &source,
        const SvForgeImageRequest &request,
        std::string &error);

    // Convenience: parse and build in one step.
    [[nodiscard]] std::optional<SvForgeGfxImage> SV_BuildForgeGfxImageFromIwi(
        std::span<const std::byte> file,
        const SvForgeImageRequest &request,
        std::string &error);

    // Re-walks a built image the way sub_BE7470 will, and requires the payload to
    // be consumed EXACTLY. The same standard the XAnim path holds itself to.
    [[nodiscard]] bool SV_VerifyForgeGfxImage(
        const SvForgeGfxImage &image,
        std::string &error);

    // Offsets inside the 52-byte header, so the hook and the tests agree.
    inline constexpr std::size_t OlfinalGfxImageSize = 52;
    inline constexpr std::size_t OlfinalGfxImageLoadDefSlot = 0;     // read by sub_BE7470
    inline constexpr std::size_t OlfinalGfxImageMapType = 4;
    inline constexpr std::size_t OlfinalGfxImageSemantic = 5;
    inline constexpr std::size_t OlfinalGfxImageCategory = 6;
    inline constexpr std::size_t OlfinalGfxImageCardMemory = 16;
    inline constexpr std::size_t OlfinalGfxImageWidth = 32;
    inline constexpr std::size_t OlfinalGfxImageHeight = 34;
    inline constexpr std::size_t OlfinalGfxImageDepth = 36;
    inline constexpr std::size_t OlfinalGfxImageNoPixels = 38;
    inline constexpr std::size_t OlfinalGfxImageStateByte = 40;
    inline constexpr std::size_t OlfinalGfxImageLoadDefAfter = 44;   // written by sub_BE7470
    inline constexpr std::size_t OlfinalGfxImageName = 48;
    inline constexpr std::size_t OlfinalGfxImageLoadDefSize = 16;

    // OlfinalGfxImageAssetType (10) is declared by sv_forge_publish_mp.hpp,
    // alongside the other four asset type numbers.
    inline constexpr std::uint8_t OlfinalGfxImageMapType2D = 3;
    inline constexpr std::uint8_t OlfinalGfxImageMapType3D = 4;
    inline constexpr std::uint8_t OlfinalGfxImageMapTypeCube = 5;

    // The one flag bit sub_BE7470's arithmetic reads. Everything else is left
    // clear on purpose: bits 24..27 select D3DUSAGE and D3DPOOL, and a port wants
    // the ordinary path a shipped texture takes.
    inline constexpr std::uint32_t OlfinalGfxImageFlagSingleMip = 0x2;
}
