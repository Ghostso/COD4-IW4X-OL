#include "sv_forge_image_mp.hpp"

#include <algorithm>
#include <cstring>

namespace CodolGameServer
{
    namespace
    {
        constexpr std::uint32_t FourCcDxt1 = 0x31545844;   // "DXT1"
        constexpr std::uint32_t FourCcDxt3 = 0x33545844;   // "DXT3"
        constexpr std::uint32_t FourCcDxt5 = 0x35545844;   // "DXT5"

        [[nodiscard]] std::uint16_t readU16(std::span<const std::byte> d, std::size_t at) noexcept
        {
            return static_cast<std::uint16_t>(
                static_cast<std::uint16_t>(std::to_integer<std::uint8_t>(d[at])) |
                static_cast<std::uint16_t>(std::to_integer<std::uint8_t>(d[at + 1])) << 8);
        }

        [[nodiscard]] std::uint32_t readU32(std::span<const std::byte> d, std::size_t at) noexcept
        {
            std::uint32_t v = 0;
            for (std::size_t i = 0; i < 4; ++i)
                v |= static_cast<std::uint32_t>(std::to_integer<std::uint8_t>(d[at + i])) << (8 * i);
            return v;
        }

        void writeU16(std::vector<std::byte> &d, std::size_t at, std::uint16_t v) noexcept
        {
            d[at] = static_cast<std::byte>(v & 0xFF);
            d[at + 1] = static_cast<std::byte>((v >> 8) & 0xFF);
        }

        void writeU32(std::vector<std::byte> &d, std::size_t at, std::uint32_t v) noexcept
        {
            for (std::size_t i = 0; i < 4; ++i)
                d[at + i] = static_cast<std::byte>((v >> (8 * i)) & 0xFF);
        }

        // Bytes for one level of an IWI, using the FILE's bytes-per-pixel rather
        // than the D3DFORMAT's. They agree for every format this path accepts,
        // and the one where they do not - X8R8G8B8, 3 on disk against 4 in D3D -
        // is refused by SV_ForgeIwiFormatToD3D before it gets here.
        [[nodiscard]] std::uint32_t iwiLevelBytes(
            std::uint8_t iwiFormat, std::uint32_t w, std::uint32_t h) noexcept
        {
            w = std::max<std::uint32_t>(1, w);
            h = std::max<std::uint32_t>(1, h);
            const std::uint32_t blocks = ((w + 3) / 4) * ((h + 3) / 4);
            switch (iwiFormat)
            {
            case 11: return blocks * 8;    // DXT1
            case 12: return blocks * 16;   // DXT3
            case 13: return blocks * 16;   // DXT5
            case 1:  return w * h * 4;     // A8R8G8B8
            case 3:  return w * h * 2;     // A8L8
            case 4:  return w * h;         // L8
            case 5:  return w * h;         // A8
            default: return 0;
            }
        }

        [[nodiscard]] std::uint32_t fullLevelCount(
            std::uint32_t w, std::uint32_t h, std::uint32_t d) noexcept
        {
            std::uint32_t n = 1;
            for (std::uint32_t i = 1; i < w || i < h || i < d; i *= 2)
                ++n;
            return n;
        }
    }

    std::uint32_t SV_ForgeImageLevelBytes(
        const std::uint32_t f,
        const std::uint32_t w,
        const std::uint32_t h,
        const std::uint32_t d) noexcept
    {
        // sub_BE8690 out.exe 0xBE8690, branch for branch.
        if (f > 80)
        {
            if (f > FourCcDxt1)
            {
                if (f == FourCcDxt3 || f == FourCcDxt5)
                    return 16 * d * ((h + 3) >> 2) * ((w + 3) >> 2);
            }
            else
            {
                if (f == FourCcDxt1)
                    return 8 * d * ((h + 3) >> 2) * ((w + 3) >> 2);
                if (f == 112 || f == 114)
                    return 4 * d * h * w;
            }
            return 0;
        }
        if (f == 80)
            return 2 * d * h * w;
        switch (f)
        {
        case 21:
        case 22:
        case 75:
            return 4 * d * h * w;
        case 28:
        case 50:
            return d * h * w;
        case 51:
            return 2 * d * h * w;
        default:
            return 0;
        }
    }

    std::uint32_t SV_ForgeImageLevelCount(
        const std::uint32_t flags,
        const std::uint32_t w,
        const std::uint32_t h,
        const std::uint32_t d) noexcept
    {
        // sub_BE8C30 out.exe 0xBE8C30. Its first parameter is a `char`, so only
        // the low byte reaches the test.
        if (((flags & 0xFFu) & OlfinalGfxImageFlagSingleMip) != 0)
            return 1;
        return fullLevelCount(w, h, d);
    }

    std::uint64_t SV_ForgeImagePayloadBytes(
        const std::uint32_t d3dFormat,
        const std::uint32_t flags,
        const std::uint32_t width,
        const std::uint32_t height,
        const std::uint32_t depth,
        const bool cubemap) noexcept
    {
        const std::uint32_t d = std::max<std::uint32_t>(1, depth);
        const std::uint32_t levels = SV_ForgeImageLevelCount(flags, width, height, d);
        const int faces = cubemap ? 6 : 1;
        std::uint64_t total = 0;
        for (int face = 0; face < faces; ++face)
        {
            for (std::uint32_t j = 0; j < levels; ++j)
            {
                const std::uint32_t bytes = SV_ForgeImageLevelBytes(
                    d3dFormat,
                    std::max<std::uint32_t>(1, width >> j),
                    std::max<std::uint32_t>(1, height >> j),
                    std::max<std::uint32_t>(1, d >> j));
                if (bytes == 0)
                    return 0;
                total += bytes;
            }
        }
        return total;
    }

    std::uint32_t SV_ForgeIwiFormatToD3D(const std::uint8_t iwiFormat) noexcept
    {
        switch (iwiFormat)
        {
        case 1:  return 21;            // A8R8G8B8
        case 3:  return 51;            // A8L8
        case 4:  return 50;            // L8
        case 5:  return 28;            // A8
        case 11: return FourCcDxt1;
        case 12: return FourCcDxt3;
        case 13: return FourCcDxt5;
        // 2 X8R8G8B8 is deliberately absent: the file packs three bytes per pixel
        // and D3DFMT_X8R8G8B8 is four, so copying it straight through would shear
        // the image. Expanding it is possible and is simply not done here.
        // 6..10 are the stream-coded variants, which are not plain pixels at all.
        default: return 0;
        }
    }

    std::optional<SvForgeImageSource> SV_ParseForgeIwi(
        const std::span<const std::byte> file,
        std::string &error)
    {
        if (file.size() < 16)
        {
            error = "too short to be an IWi";
            return std::nullopt;
        }
        if (std::to_integer<char>(file[0]) != 'I' ||
            std::to_integer<char>(file[1]) != 'W' ||
            std::to_integer<char>(file[2]) != 'i')
        {
            error = "not an IWi file";
            return std::nullopt;
        }

        SvForgeImageSource src;
        src.version = std::to_integer<std::uint8_t>(file[3]);
        if (src.version == 6)
        {
            // IW3: format +4, flags +5, dims +6/+8/+10, sizes +12. Largest first.
            src.headerSize = 28;
            src.iwiFormat = std::to_integer<std::uint8_t>(file[4]);
            src.cubemap = false;
            src.width = readU16(file, 6);
            src.height = readU16(file, 8);
            src.depth = readU16(file, 10);
            src.storedSmallestFirst = false;
        }
        else if (src.version == 8 || src.version == 9)
        {
            // IW5 / CODOL: flags u32 +4, format +8, dims +10/+12/+14. Smallest first.
            src.headerSize = 32;
            if (file.size() < src.headerSize)
            {
                error = "truncated IWi header";
                return std::nullopt;
            }
            const std::uint32_t flags = readU32(file, 4);
            src.iwiFormat = std::to_integer<std::uint8_t>(file[8]);
            src.cubemap = (flags & 0x10000u) != 0;
            src.width = readU16(file, 10);
            src.height = readU16(file, 12);
            src.depth = readU16(file, 14);
            src.storedSmallestFirst = true;
        }
        else
        {
            error = "unsupported IWi version " + std::to_string(src.version);
            return std::nullopt;
        }

        if (src.width == 0 || src.height == 0)
        {
            error = "zero dimensions";
            return std::nullopt;
        }
        if (file.size() <= src.headerSize)
        {
            error = "no payload";
            return std::nullopt;
        }

        src.d3dFormat = SV_ForgeIwiFormatToD3D(src.iwiFormat);
        if (src.d3dFormat == 0)
        {
            error = "IWi format " + std::to_string(src.iwiFormat) +
                    " has no plain D3DFORMAT this path will copy";
            return std::nullopt;
        }

        src.payloadOffset = src.headerSize;
        src.payloadBytes = file.size() - src.headerSize;

        const std::uint32_t depth = std::max<std::uint32_t>(1, src.depth);
        src.fullLevels = fullLevelCount(src.width, src.height, depth);
        const int faces = src.cubemap ? 6 : 1;

        // The stored level count is a property of the FILE, not of the dimensions.
        // Take the count whose running total equals the payload exactly; prefix
        // sums strictly increase, so at most one can match.
        std::uint64_t total = 0;
        for (std::uint32_t i = 0; i < src.fullLevels; ++i)
        {
            const std::uint32_t bytes = iwiLevelBytes(
                src.iwiFormat,
                std::max<std::uint32_t>(1, static_cast<std::uint32_t>(src.width) >> i),
                std::max<std::uint32_t>(1, static_cast<std::uint32_t>(src.height) >> i));
            if (bytes == 0)
            {
                error = "cannot size IWi format " + std::to_string(src.iwiFormat);
                return std::nullopt;
            }
            total += static_cast<std::uint64_t>(bytes) * static_cast<std::uint64_t>(faces);
            if (total == src.payloadBytes)
            {
                src.storedLevels = i + 1;
                break;
            }
            if (total > src.payloadBytes)
                break;
        }
        if (src.storedLevels == 0)
        {
            error = "no mip count from 1.." + std::to_string(src.fullLevels) +
                    " fills the payload of " + std::to_string(src.payloadBytes) + " bytes";
            return std::nullopt;
        }
        return src;
    }

    std::optional<SvForgeGfxImage> SV_BuildForgeGfxImage(
        const std::span<const std::byte> file,
        const SvForgeImageSource &source,
        const SvForgeImageRequest &request,
        std::string &error)
    {
        if (request.name.empty())
        {
            error = "image has no name";
            return std::nullopt;
        }
        if (source.payloadOffset + source.payloadBytes > file.size())
        {
            error = "payload runs past the file";
            return std::nullopt;
        }
        if (source.cubemap)
        {
            // Nothing in this port needs one, and a cube face order that has never
            // been checked is exactly the kind of thing that produces a plausible
            // wrong answer.
            error = "cubemaps are not supported by this path";
            return std::nullopt;
        }

        // sub_BE8C30 can only answer "one level" or "the full chain", so those are
        // the only two shapes that can be handed to sub_BE7470 without it walking
        // past the payload.
        std::uint32_t flags = 0;
        if (source.storedLevels == 1)
        {
            flags = OlfinalGfxImageFlagSingleMip;
        }
        else if (source.storedLevels != source.fullLevels)
        {
            error = "IWi stores " + std::to_string(source.storedLevels) + " of " +
                    std::to_string(source.fullLevels) +
                    " levels; the engine can only walk one or all";
            return std::nullopt;
        }

        const std::uint32_t depth = std::max<std::uint32_t>(1, source.depth);
        const std::uint64_t needed = SV_ForgeImagePayloadBytes(
            source.d3dFormat, flags, source.width, source.height, depth, source.cubemap);
        if (needed == 0)
        {
            error = "the client cannot size D3DFORMAT " + std::to_string(source.d3dFormat);
            return std::nullopt;
        }
        if (needed != source.payloadBytes)
        {
            error = "the engine would read " + std::to_string(needed) +
                    " bytes but the file holds " + std::to_string(source.payloadBytes);
            return std::nullopt;
        }

        SvForgeGfxImage image;
        image.name = request.name;
        image.d3dFormat = source.d3dFormat;
        image.flags = flags;
        image.width = source.width;
        image.height = source.height;
        image.levels = source.storedLevels;
        image.payloadBytes = source.payloadBytes;

        // header | name | pad | load def | payload
        std::size_t cursor = OlfinalGfxImageSize;
        const std::size_t nameAt = cursor;
        cursor += request.name.size() + 1;
        cursor = (cursor + 3) & ~std::size_t{ 3 };
        image.loadDefOffset = cursor;
        cursor += OlfinalGfxImageLoadDefSize;
        image.payloadOffset = cursor;
        cursor += source.payloadBytes;

        image.storage.assign(cursor, std::byte{ 0 });

        std::memcpy(image.storage.data() + nameAt, request.name.data(), request.name.size());

        image.storage[OlfinalGfxImageMapType] = static_cast<std::byte>(OlfinalGfxImageMapType2D);
        image.storage[OlfinalGfxImageSemantic] = static_cast<std::byte>(request.semantic);
        image.storage[OlfinalGfxImageCategory] = static_cast<std::byte>(request.category);
        writeU16(image.storage, OlfinalGfxImageWidth, source.width);
        writeU16(image.storage, OlfinalGfxImageHeight, source.height);
        writeU16(image.storage, OlfinalGfxImageDepth, static_cast<std::uint16_t>(depth));
        // +38 "no pixels" and +40 the byte sub_4999E0 reads. sub_4999E0 returns
        // true - and sub_BE7470 then does nothing at all - when (b & 1) is set and
        // (b & 2) is not, so zero is the value that lets the upload proceed.
        image.storage[OlfinalGfxImageNoPixels] = std::byte{ 0 };
        image.storage[OlfinalGfxImageStateByte] = std::byte{ 0 };
        // cardMemory is accounting for the picmip dvar, not correctness; the upload
        // path never reads it. The honest value is what the payload actually costs.
        for (std::size_t i = 0; i < 4; ++i)
        {
            writeU32(image.storage, OlfinalGfxImageCardMemory + 4 * i,
                     static_cast<std::uint32_t>(source.payloadBytes));
        }

        // The load definition. +0 is the `Levels` argument CreateTexture receives:
        // shipped images pass 0 for a full chain and 1 for a single level.
        auto &s = image.storage;
        s[image.loadDefOffset] =
            static_cast<std::byte>(source.storedLevels == 1 ? 1 : 0);
        writeU32(s, image.loadDefOffset + 4, flags);
        writeU32(s, image.loadDefOffset + 8, source.d3dFormat);
        writeU32(s, image.loadDefOffset + 12, static_cast<std::uint32_t>(source.payloadBytes));

        // The payload, in the order sub_BE7470 walks it: largest level first.
        const std::byte *const from = file.data() + source.payloadOffset;
        std::byte *const to = s.data() + image.payloadOffset;
        if (!source.storedSmallestFirst)
        {
            std::memcpy(to, from, source.payloadBytes);
        }
        else
        {
            // v8/v9 store smallest-first. Walk the file backwards a level at a
            // time and lay the levels down largest-first.
            std::size_t readAt = source.payloadBytes;
            std::size_t writeAt = 0;
            for (std::uint32_t i = 0; i < source.storedLevels; ++i)
            {
                const std::uint32_t bytes = iwiLevelBytes(
                    source.iwiFormat,
                    std::max<std::uint32_t>(1, static_cast<std::uint32_t>(source.width) >> i),
                    std::max<std::uint32_t>(1, static_cast<std::uint32_t>(source.height) >> i));
                if (bytes > readAt)
                {
                    error = "reversing the mip chain ran off the start of the payload";
                    return std::nullopt;
                }
                readAt -= bytes;
                std::memcpy(to + writeAt, from + readAt, bytes);
                writeAt += bytes;
            }
            if (readAt != 0 || writeAt != source.payloadBytes)
            {
                error = "reversing the mip chain did not consume the payload exactly";
                return std::nullopt;
            }
        }

        std::string verifyError;
        if (!SV_VerifyForgeGfxImage(image, verifyError))
        {
            error = "built image failed its own check: " + verifyError;
            return std::nullopt;
        }
        return image;
    }

    std::optional<SvForgeGfxImage> SV_BuildForgeGfxImageFromIwi(
        const std::span<const std::byte> file,
        const SvForgeImageRequest &request,
        std::string &error)
    {
        const auto source = SV_ParseForgeIwi(file, error);
        if (!source)
            return std::nullopt;
        return SV_BuildForgeGfxImage(file, *source, request, error);
    }

    bool SV_VerifyForgeGfxImage(const SvForgeGfxImage &image, std::string &error)
    {
        if (image.storage.size() < OlfinalGfxImageSize)
        {
            error = "storage is smaller than the header";
            return false;
        }
        if (image.loadDefOffset + OlfinalGfxImageLoadDefSize > image.storage.size())
        {
            error = "the load definition runs past the storage";
            return false;
        }
        if (image.payloadOffset + image.payloadBytes != image.storage.size())
        {
            error = "the payload does not end at the end of the storage";
            return false;
        }
        if (image.payloadOffset != image.loadDefOffset + OlfinalGfxImageLoadDefSize)
        {
            error = "the payload does not immediately follow the load definition";
            return false;
        }

        const std::span<const std::byte> s{ image.storage };
        const std::uint32_t flags = readU32(s, image.loadDefOffset + 4);
        const std::uint32_t format = readU32(s, image.loadDefOffset + 8);
        const std::uint32_t declared = readU32(s, image.loadDefOffset + 12);
        if (declared != image.payloadBytes)
        {
            error = "resourceSize disagrees with the payload";
            return false;
        }

        const std::uint16_t w = readU16(s, OlfinalGfxImageWidth);
        const std::uint16_t h = readU16(s, OlfinalGfxImageHeight);
        const std::uint16_t d = readU16(s, OlfinalGfxImageDepth);
        if (d == 0)
        {
            error = "depth is zero";
            return false;
        }

        // Walk it exactly as sub_BE7470 does, and require the cursor to land on
        // the last byte of the payload.
        const std::uint32_t levels = SV_ForgeImageLevelCount(flags, w, h, d);
        std::uint64_t cursor = 0;
        for (std::uint32_t j = 0; j < levels; ++j)
        {
            const std::uint32_t bytes = SV_ForgeImageLevelBytes(
                format,
                std::max<std::uint32_t>(1, static_cast<std::uint32_t>(w) >> j),
                std::max<std::uint32_t>(1, static_cast<std::uint32_t>(h) >> j),
                std::max<std::uint32_t>(1, static_cast<std::uint32_t>(d) >> j));
            if (bytes == 0)
            {
                error = "a level of D3DFORMAT " + std::to_string(format) + " has no size";
                return false;
            }
            cursor += bytes;
            if (cursor > image.payloadBytes)
            {
                error = "the walk runs past the payload at level " + std::to_string(j);
                return false;
            }
        }
        if (cursor != image.payloadBytes)
        {
            error = "the walk consumed " + std::to_string(cursor) + " of " +
                    std::to_string(image.payloadBytes) + " bytes";
            return false;
        }
        if (levels != image.levels)
        {
            error = "the engine would walk " + std::to_string(levels) +
                    " levels but the file holds " + std::to_string(image.levels);
            return false;
        }

        // The name has to be a NUL-terminated copy inside the storage, because the
        // header's +48 will point at it for the life of the client.
        const std::size_t nameAt = OlfinalGfxImageSize;
        if (nameAt + image.name.size() + 1 > image.storage.size())
        {
            error = "the name runs past the storage";
            return false;
        }
        if (std::memcmp(image.storage.data() + nameAt, image.name.data(), image.name.size()) != 0 ||
            image.storage[nameAt + image.name.size()] != std::byte{ 0 })
        {
            error = "the embedded name does not match";
            return false;
        }
        return true;
    }
}
