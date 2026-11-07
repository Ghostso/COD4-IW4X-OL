#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "Auth3ClientPatches.hpp"
#include "Servers.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstring>
#include <cwchar>
#include <mutex>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>

namespace
{
    constexpr std::array<int, 11> CertificateCall{
        0x68, -1, -1, -1, -1, 0x0F, 0x95, 0xC2, 0x52, 0x50, 0xE8,
    };
    constexpr std::array<int, 10> CertificateBranch{
        0x74, -1, 0x83, 0xBE, 0x78, 0x02, 0x00, 0x00, 0x00, 0x74,
    };
    constexpr std::array<int, 18> AuthenticationBranch{
        0x8B, 0x86, -1, -1, -1, -1, 0x83, -1, -1, 0x85, 0xC0, 0x0F,
        0x84, -1, -1, -1, -1, 0x68,
    };

    // ABSENT AND AMBIGUOUS ARE NOT THE SAME ANSWER, and the old findUnique() returned
    // std::nullopt for both. That single word is why this file could be wrong for a fortnight:
    // "no sites" reads as "not the game, carry on" and "two sites" reads as "the game, but do
    // not touch it", and only one of those is safe to treat as success.
    enum class SiteSearch
    {
        located,    // all three, exactly once each -- safe to patch
        absent,     // none of the three appear; this image does not contain the code
        ambiguous,  // present but not uniquely, or only partly present -- NOT safe to patch
        unusable,   // not a mappable i386 image, or its pages would not unprotect
    };

    struct SiteLookup
    {
        SiteSearch result{ SiteSearch::absent };
        std::array<std::size_t, 3> sites{};
    };

    // Counting stops at two: nothing downstream can act on a third.
    template<std::size_t Size>
    std::pair<std::size_t, std::size_t> countMatches(
        const std::span<const std::uint8_t> image,
        const std::array<int, Size> &pattern)
    {
        std::size_t count{};
        std::size_t first{};
        if (image.size() < Size)
            return { 0, 0 };
        for (std::size_t offset = 0; offset <= image.size() - Size; ++offset)
        {
            bool match = true;
            for (std::size_t index = 0; index != Size; ++index)
            {
                if (pattern[index] >= 0 && image[offset + index] != pattern[index])
                {
                    match = false;
                    break;
                }
            }
            if (!match)
                continue;
            if (!count)
                first = offset;
            if (++count > 1)
                break;
        }
        return { count, first };
    }

    SiteLookup locate(const std::span<const std::uint8_t> image)
    {
        const auto call = countMatches(image, CertificateCall);
        const auto certificate = countMatches(image, CertificateBranch);
        const auto authentication = countMatches(image, AuthenticationBranch);
        if (call.first == 1 && certificate.first == 1 && authentication.first == 1)
        {
            return SiteLookup{ SiteSearch::located,
                { call.second, certificate.second, authentication.second } };
        }
        if (!call.first && !certificate.first && !authentication.first)
            return SiteLookup{ SiteSearch::absent, {} };
        return SiteLookup{ SiteSearch::ambiguous, {} };
    }

    void patch(const std::span<std::uint8_t> image, const std::array<std::size_t, 3> &sites)
    {
        std::memset(image.data() + sites[0] + 10, 0x90, 5);
        image[sites[1]] = 0x71;
        image[sites[2] + 12] = 0x81;
    }

    // WHY THERE IS NO PROCESS-NAME GATE HERE ANY MORE -- handoff §§191g.
    //
    // This used to refuse any image not named codoMP_client_shipRetail.exe, copied from the
    // sibling gate in CodolClientPatches.cpp. There it is CORRECT and documented: every RVA in
    // that file is a 3.3.3.3 address, so the build IS the precondition. Here it was never the
    // precondition -- the three sites below are found by BYTE SIGNATURE, and they locate
    // uniquely in OLfinal's out.exe (1649370) at the same 0x1430 spacing they have in 3.3.3.3.
    // See Tools/olfinal/check-auth3-patches.py, which measures that offline against either.
    //
    // The cost of the borrowed gate was a remote player's login. installAuth3ClientPatches()
    // returned TRUE WITHOUT PATCHING on out.exe, ServerFactory::create read that as success,
    // and the client validated the self-signed certificate Auth3TlsTransport mints at runtime
    // for real -- `tlsv1 alert unknown ca`, then a 40 second stall and a hang up. It never
    // showed on this machine because this machine's client does not take the Auth3 path.
    //
    // The honest precondition is the one install() already enforces: an i386 image in which
    // all three signatures locate, and locate UNIQUELY. A name is a lossy view of that.
    std::string imageName()
    {
        std::array<char, MAX_PATH> path{};
        const auto size = GetModuleFileNameA(nullptr, path.data(), static_cast<DWORD>(path.size()));
        if (!size || size >= path.size())
            return "<unnamed image>";
        const std::string_view value(path.data(), size);
        const auto separator = value.find_last_of("\\/");
        return std::string(separator == std::string_view::npos ? value : value.substr(separator + 1));
    }

    // The name is used for exactly one judgement, and it is not "may I patch this". It is
    // "should I be alarmed that there was nothing here to patch": in a test binary or a tool
    // that happens to load this plugin, absent signatures are the expected, healthy answer.
    // In an image we ship the game as, absent signatures mean they MOVED WITH THE BUILD, and
    // that must be loud -- the failure it causes is a remote player who cannot log in.
    bool isKnownClientImage(const std::string &name)
    {
        return _stricmp(name.c_str(), "out.exe") == 0 ||
            _stricmp(name.c_str(), "codoMP_client_shipRetail.exe") == 0;
    }

    SiteSearch install(std::array<std::size_t, 3> &sites)
    {
        const auto module = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
        if (!module)
            return SiteSearch::unusable;
        const auto dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(module);
        if (dos->e_magic != IMAGE_DOS_SIGNATURE)
            return SiteSearch::unusable;
        const auto nt = reinterpret_cast<const IMAGE_NT_HEADERS *>(module + dos->e_lfanew);
        if (nt->Signature != IMAGE_NT_SIGNATURE || nt->FileHeader.Machine != IMAGE_FILE_MACHINE_I386)
            return SiteSearch::unusable;
        const auto size = static_cast<std::size_t>(nt->OptionalHeader.SizeOfImage);
        std::span<std::uint8_t> image(module, size);
        const auto found = locate(image);
        if (found.result != SiteSearch::located)
            return found.result;
        sites = found.sites;

        struct ProtectedRange
        {
            void *address{};
            std::size_t size{};
            DWORD previous{};
        };
        std::array<ProtectedRange, 3> ranges{
            ProtectedRange{module + sites[0] + 10, 5},
            ProtectedRange{module + sites[1], 1},
            ProtectedRange{module + sites[2] + 12, 1},
        };
        std::size_t protectedCount{};
        for (auto &range : ranges)
        {
            if (!VirtualProtect(range.address, range.size, PAGE_EXECUTE_READWRITE, &range.previous))
            {
                while (protectedCount)
                {
                    auto &previous = ranges[--protectedCount];
                    DWORD ignored{};
                    VirtualProtect(previous.address, previous.size, previous.previous, &ignored);
                }
                return SiteSearch::unusable;
            }
            ++protectedCount;
        }

        patch(image, sites);
        FlushInstructionCache(GetCurrentProcess(), module, size);
        while (protectedCount)
        {
            auto &range = ranges[--protectedCount];
            DWORD ignored{};
            VirtualProtect(range.address, range.size, range.previous, &ignored);
        }
        return SiteSearch::located;
    }
}

namespace AlwaysofflineRe::Demonware
{
    bool patchAuth3ValidationBuffer(const std::span<std::uint8_t> image)
    {
        const auto found = locate(image);
        if (found.result != SiteSearch::located)
            return false;
        patch(image, found.sites);
        return true;
    }

    bool installAuth3ClientPatches()
    {
        static std::once_flag once;
        static bool result{};
        std::call_once(once, [] {
            std::array<std::size_t, 3> sites{};
            const auto outcome = install(sites);
            const auto name = imageName();
            std::ostringstream message;
            switch (outcome)
            {
                case SiteSearch::located:
                    result = true;
                    // One line, once, and it dates three per-build constants. The offsets
                    // differ between clients; the 0x1430 SPACING between them does not, which
                    // is how out.exe's sites were corroborated against 3.3.3.3's offline
                    // before this ever ran.
                    message << "Applied the three Auth3 client patches to " << name << " at +0x"
                            << std::hex << std::uppercase << sites[0] << ", +0x" << sites[1]
                            << ", +0x" << sites[2] << '.';
                    break;

                case SiteSearch::absent:
                    if (!isKnownClientImage(name))
                    {
                        // Not a client. Nothing to patch, nothing wrong, nothing to say.
                        result = true;
                        return;
                    }
                    message << "The three Auth3 client patch signatures are ABSENT from " << name
                            << ", which IS a known CODOL client image -- they have moved with "
                               "the build. Re-derive them with Tools/olfinal/check-auth3-patches"
                               ".py; until then Auth3 cannot serve a client that needs it.";
                    break;

                case SiteSearch::ambiguous:
                    message << "The Auth3 client patch signatures do not resolve to one site "
                               "each in " << name << ". Refusing to patch a guess.";
                    break;

                case SiteSearch::unusable:
                    message << "Could not map " << name
                            << " as a patchable i386 image for the Auth3 client patches.";
                    break;
            }
            AlwaysofflineRe::log(message.str());
        });
        return result;
    }
}
