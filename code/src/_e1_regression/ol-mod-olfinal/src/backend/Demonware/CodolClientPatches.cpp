#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "CodolClientPatches.hpp"
#include "Servers.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <cstddef>
#include <cstring>
#include <cwchar>
#include <string>
#include <string_view>

namespace
{
    // THIS FILE IS STILL 3.3.3.3-ONLY, DELIBERATELY, AND IT GATES ITSELF.
    //
    // These two constants are a SEPARATE copy of the host gate from
    // EngineBindings::ExpectedTimestamp/ExpectedImageSize, which now name
    // out.exe (1649370). That divergence is intentional rather than an
    // oversight: every RVA below is a 3.3.3.3 address, so the honest gate for
    // this patch set is the build those addresses describe. On an OLfinal host
    // the check fails, nothing is written, and backend/Appmain.cpp logs
    // "Refused to apply CODOL startup patches to an unknown executable image."
    // once -- which is accurate, not a fault to chase.
    //
    // WHAT IT COSTS ON OLfinal: the client-side profile completion, profile
    // reload, public-profile request and inventory refresh hooks do not
    // install. The Demonware SERVER side is unaffected and build-independent.
    //
    // TODO(CODOL): port the eight RVAs below to 1649370 if the OLfinal client
    // turns out to need these hooks. They were NOT ported with the rest of the
    // flip because none of their owning functions is in the 3.3.3.3 -> OLfinal
    // pair set, so each needs its own identification -- and because whether
    // OLfinal needs them at all is unknown until a client runs without them.
    // Exit condition is a live client reaching its loadout with these absent;
    // if it does, delete this note instead of porting.
    // Tools/olfinal/import-signature.py is the method that worked for the four
    // constants in game_server/ClientProcessPatches.cpp, which had the same
    // problem: anchor on the Win32 imports the function calls, since an import
    // is named in the file and therefore survives an unrelated build.
    constexpr DWORD CodolTimestamp = 0x57611E31;
    constexpr std::size_t CodolImageSize = 0x0C72A000;
    constexpr std::size_t MaximumPatchSize = 8;
    constexpr std::size_t ProfileCompletionRva = 0x2D83E0;
    constexpr std::size_t ProfileStartOperationRva = 0x2D84D0;
    constexpr std::size_t ProfileManagerFrameRva = 0x2D9FE0;
    constexpr std::size_t PublicProfileRequestCallRva = 0x2D866A;
    constexpr std::size_t GetPublicProfilesRva = 0x65A890;
    constexpr std::size_t InventoryRequestRva = 0x0A6B10;
    constexpr std::size_t InventoryFinalizeRva = 0x0A6CC0;
    constexpr std::size_t CurrentCharacterCacheRva = 0x8D7E3C;
    constexpr std::size_t ProfileCompletionPrologueSize = 6;
    constexpr std::size_t ProfileManagerFramePrologueSize = 6;
    constexpr std::size_t InventoryFinalizePrologueSize = 6;

    constexpr std::array<std::uint8_t, ProfileCompletionPrologueSize>
        ProfileCompletionPrefix{ 0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8 };
    constexpr std::array<std::uint8_t, ProfileManagerFramePrologueSize>
        ProfileManagerFramePrefix{ 0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x14 };
    constexpr std::array<std::uint8_t, 6>
        InventoryRequestPrefix{ 0x55, 0x8B, 0xEC, 0x51, 0x80, 0x3D };
    constexpr std::array<std::uint8_t, InventoryFinalizePrologueSize>
        InventoryFinalizePrefix{ 0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8 };
    constexpr std::array<std::uint8_t, 5>
        PublicProfileRequestCall{ 0xE8, 0x21, 0x22, 0x38, 0x00 };

    constexpr std::size_t RemoteTaskProfileOffset = 56;
    constexpr std::size_t TaskRemoteTaskOffset = 40;
    constexpr std::size_t RemoteTaskErrorOffset = 56;
    constexpr std::size_t ProfileKindOffset = 108;
    constexpr std::size_t ProfileOperationOffset = 116;
    constexpr std::size_t ProfileDeferredOperationOffset = 120;
    constexpr std::size_t ProfileDownloadAttemptOffset = 37132;
    constexpr std::uint32_t PublicProfileKind = 1;
    constexpr std::uint32_t PrivateProfileKind = 2;
    constexpr std::uint32_t DownloadOperation = 1;
    constexpr std::uint32_t MissingProfileError = 800;

    using ProfileCompletion = int(__cdecl *)(std::uintptr_t task, char succeeded);
    using ProfileStartOperation = bool(__thiscall *)(void *profile, std::uint32_t operation);
    using GetPublicProfiles = std::uintptr_t(__thiscall *)(
        void *profiles,
        std::uintptr_t result,
        std::uintptr_t userIds,
        std::uintptr_t profile,
        std::uint32_t count);
    using InventoryRequest = bool(__cdecl *)();
    using InventoryFinalize = char(__cdecl *)(char succeeded, std::uint32_t resultCount);

    enum class RuntimeRequestState : std::uint32_t
    {
        idle = 1,
        queued = 2,
        inFlight = 3,
        succeeded = 4,
        failed = 5,
    };

    struct RuntimeRequest
    {
        std::atomic_uint32_t generation{};
        std::atomic<RuntimeRequestState> state{ RuntimeRequestState::idle };
        std::atomic_uint32_t errorCode{};
    };

    enum class StartupInventoryState : std::uint8_t
    {
        notStarted,
        inFlight,
        ready,
    };

    ProfileCompletion OriginalProfileCompletion{};
    ProfileStartOperation StartProfileOperation{};
    void *OriginalProfileManagerFrame{};
    GetPublicProfiles OriginalGetPublicProfiles{};
    InventoryRequest RequestInventory{};
    InventoryFinalize OriginalFinalizeInventory{};
    volatile LONG *CurrentCharacterCache{};
    std::atomic<StartupInventoryState> InventoryState{ StartupInventoryState::notStarted };
    std::atomic_bool InventoryDeferralLogged{};
    std::array<RuntimeRequest, 3> ProfileReloads{};
    RuntimeRequest InventoryRefresh{};
    std::atomic_bool ProfileManagerHookInstalled{};

    bool isProfileKind(const std::uint32_t kind)
    {
        return kind == PublicProfileKind || kind == PrivateProfileKind;
    }

    void finishRuntimeRequest(
        RuntimeRequest &request,
        const bool succeeded,
        const std::uint32_t errorCode)
    {
        if (request.state.load() != RuntimeRequestState::inFlight)
            return;
        request.errorCode = errorCode;
        request.state = succeeded ? RuntimeRequestState::succeeded : RuntimeRequestState::failed;
    }

    struct PatchSite
    {
        std::size_t rva;
        std::size_t size;
        std::array<std::uint8_t, MaximumPatchSize> original;
        std::array<std::uint8_t, MaximumPatchSize> patched;
    };

    // These are the only seven differences between the archived original and
    // the stable patched executable. IDA confirms that the final five suppress
    // error reporting without manufacturing a successful DW state transition.
    constexpr std::array<PatchSite, 7> PatchSites{
        // Only the branch bytes are stable in memory; the following PUSH
        // immediate is rebased by the PE loader under ASLR.
        PatchSite{0x2422C1, 2,
            {0x75, 0x27, 0x68, 0xDC, 0x6E, 0xC7, 0x00, 0x68},
            {0xEB, 0x27, 0x68, 0xDC, 0x6E, 0xC7, 0x00, 0x68}},
        PatchSite{0x24283D, 8,
            {0x0F, 0x85, 0x11, 0xFD, 0xFF, 0xFF, 0x68, 0x2C},
            {0xE9, 0x12, 0xFD, 0xFF, 0xFF, 0xFF, 0x68, 0x2C}},
        PatchSite{0x2D2AD1, 4,
            {0x75, 0x12, 0x68, 0x88},
            {0xEB, 0x12, 0x68, 0x88}},
        PatchSite{0x2D2B07, 4,
            {0x75, 0x12, 0x68, 0xA8},
            {0xEB, 0x12, 0x68, 0xA8}},
        PatchSite{0x2D2B42, 4,
            {0x75, 0x12, 0x68, 0xD8},
            {0xEB, 0x12, 0x68, 0xD8}},
        PatchSite{0x2D2B8D, 4,
            {0x75, 0x4B, 0x68, 0xFC},
            {0xEB, 0x4B, 0x68, 0xFC}},
        PatchSite{0x2D2C18, 4,
            {0x7D, 0x0F, 0x68, 0x3C},
            {0xEB, 0x0F, 0x68, 0x3C}},
    };

    enum class SiteState
    {
        original,
        patched,
        invalid,
    };

    bool requestStartupInventory(const std::string_view successMessage)
    {
        auto expected = StartupInventoryState::notStarted;
        if (!InventoryState.compare_exchange_strong(
                expected, StartupInventoryState::inFlight))
        {
            return true;
        }
        if (!RequestInventory || !RequestInventory())
        {
            InventoryState = StartupInventoryState::notStarted;
            return false;
        }

        AlwaysofflineRe::log(successMessage);
        return true;
    }

    char __cdecl inventoryFinalizeHook(
        const char succeeded,
        const std::uint32_t resultCount)
    {
        const auto result = OriginalFinalizeInventory(succeeded, resultCount);
        if (InventoryState.load() == StartupInventoryState::inFlight)
        {
            if (succeeded)
            {
                InventoryState = StartupInventoryState::ready;
                finishRuntimeRequest(InventoryRefresh, true, 0);
                AlwaysofflineRe::log(
                    "CODOL Marketplace native inventory completion finalized " +
                    std::to_string(resultCount) +
                    " objects; public profile download is released.");
            }
            else
            {
                InventoryState = StartupInventoryState::notStarted;
                finishRuntimeRequest(InventoryRefresh, false, 1);
                AlwaysofflineRe::log(
                    "CODOL Marketplace native inventory completion failed; "
                    "public profile download remains deferred.");
            }
        }
        return result;
    }

    std::uintptr_t __fastcall getPublicProfilesHook(
        void *profiles,
        void *,
        const std::uintptr_t result,
        const std::uintptr_t userIds,
        const std::uintptr_t profile,
        const std::uint32_t count)
    {
        if (InventoryState.load() != StartupInventoryState::ready)
        {
            if (!requestStartupInventory(
                    "Requested CODOL Marketplace inventory task 203 before public profile download.") &&
                !InventoryDeferralLogged.exchange(true))
            {
                AlwaysofflineRe::log(
                    "CODOL Marketplace was not ready; public profile download is deferred.");
            }

            if (result)
                *reinterpret_cast<std::uintptr_t *>(result) = 0;
            if (profile)
            {
                auto &attempts = *reinterpret_cast<std::uint32_t *>(
                    profile + ProfileDownloadAttemptOffset);
                if (attempts)
                    --attempts;
                InterlockedExchange(reinterpret_cast<volatile LONG *>(
                    profile + ProfileDeferredOperationOffset), 1);
            }
            return result;
        }
        return OriginalGetPublicProfiles(profiles, result, userIds, profile, count);
    }

    bool installInventoryFinalizeHook(std::uint8_t *module, const std::span<std::uint8_t> image)
    {
        if (InventoryFinalizeRva > image.size() ||
            InventoryFinalizePrefix.size() > image.size() - InventoryFinalizeRva ||
            InventoryFinalizePrologueSize > image.size() - InventoryFinalizeRva)
        {
            return false;
        }

        auto *target = module + InventoryFinalizeRva;
        if (!std::equal(InventoryFinalizePrefix.begin(), InventoryFinalizePrefix.end(), target))
            return false;

        auto *trampoline = static_cast<std::uint8_t *>(VirtualAlloc(
            nullptr,
            InventoryFinalizePrologueSize + 5,
            MEM_COMMIT | MEM_RESERVE,
            PAGE_EXECUTE_READWRITE));
        if (!trampoline)
            return false;

        std::copy_n(target, InventoryFinalizePrologueSize, trampoline);
        trampoline[InventoryFinalizePrologueSize] = 0xE9;
        *reinterpret_cast<std::int32_t *>(trampoline + InventoryFinalizePrologueSize + 1) =
            static_cast<std::int32_t>((target + InventoryFinalizePrologueSize) -
                (trampoline + InventoryFinalizePrologueSize + 5));

        DWORD oldProtection{};
        if (!VirtualProtect(
                target,
                InventoryFinalizePrologueSize,
                PAGE_EXECUTE_READWRITE,
                &oldProtection))
        {
            VirtualFree(trampoline, 0, MEM_RELEASE);
            return false;
        }

        OriginalFinalizeInventory = reinterpret_cast<InventoryFinalize>(trampoline);
        target[0] = 0xE9;
        *reinterpret_cast<std::int32_t *>(target + 1) = static_cast<std::int32_t>(
            reinterpret_cast<std::uint8_t *>(&inventoryFinalizeHook) - (target + 5));
        std::fill(target + 5, target + InventoryFinalizePrologueSize, std::uint8_t{ 0x90 });
        FlushInstructionCache(GetCurrentProcess(), target, InventoryFinalizePrologueSize);
        VirtualProtect(target, InventoryFinalizePrologueSize, oldProtection, &oldProtection);
        return true;
    }

    int __cdecl profileCompletionHook(const std::uintptr_t task, const char succeeded)
    {
        std::uint32_t profileKind{};
        std::uint32_t operation{};
        std::uint32_t errorCode{};
        if (task)
        {
            const auto profile = *reinterpret_cast<const std::uintptr_t *>(task + RemoteTaskProfileOffset);
            if (profile)
            {
                profileKind = *reinterpret_cast<const std::uint32_t *>(profile + ProfileKindOffset);
                operation = *reinterpret_cast<const std::uint32_t *>(profile + ProfileOperationOffset);
            }
            const auto remoteTask =
                *reinterpret_cast<const std::uintptr_t *>(task + TaskRemoteTaskOffset);
            if (remoteTask)
                errorCode = *reinterpret_cast<const std::uint32_t *>(remoteTask + RemoteTaskErrorOffset);
        }

        const auto result = OriginalProfileCompletion(task, succeeded);
        if (CurrentCharacterCache &&
            AlwaysofflineRe::Demonware::shouldInvalidateCodolCurrentCharacterCache(
                profileKind, operation, succeeded != 0, errorCode))
        {
            InterlockedExchange(CurrentCharacterCache, -1);
        }
        if (isProfileKind(profileKind) && operation == DownloadOperation)
            finishRuntimeRequest(ProfileReloads[profileKind], succeeded != 0 && errorCode == 0, errorCode);
        if (!AlwaysofflineRe::Demonware::shouldRequestCodolInventory(
                profileKind, operation, succeeded != 0, errorCode) ||
            InventoryState.load() != StartupInventoryState::notStarted)
        {
            return result;
        }

        if (errorCode == MissingProfileError)
        {
            if (!requestStartupInventory(
                    "CODOL public profile was absent; requested Marketplace inventory task 203."))
            {
                AlwaysofflineRe::log(
                    "CODOL public profile was absent, but Marketplace inventory was not ready.");
            }
        }
        else
        {
            if (!requestStartupInventory(
                    "CODOL public profile completed; requested Marketplace inventory task 203."))
            {
                AlwaysofflineRe::log(
                    "CODOL public profile completed, but Marketplace inventory was not ready.");
            }
        }
        return result;
    }

    void __cdecl processRuntimeRequests(void *manager)
    {
        if (!manager)
            return;

        if (InventoryRefresh.state.load() == RuntimeRequestState::queued)
        {
            InventoryState = StartupInventoryState::notStarted;
            if (requestStartupInventory("Editor requested CODOL Marketplace inventory refresh."))
                InventoryRefresh.state = RuntimeRequestState::inFlight;
        }

        constexpr std::size_t FirstProfileOffset = 0x10;
        constexpr std::size_t ProfileStride = 0x9128;
        auto *base = static_cast<std::uint8_t *>(manager);
        for (std::size_t index = 0; index != 2; ++index)
        {
            auto *profile = base + FirstProfileOffset + index * ProfileStride;
            const auto kind = *reinterpret_cast<const std::uint32_t *>(profile + ProfileKindOffset);
            if (!isProfileKind(kind) ||
                ProfileReloads[kind].state.load() != RuntimeRequestState::queued ||
                *reinterpret_cast<const std::uint32_t *>(profile + ProfileOperationOffset) != 0)
            {
                continue;
            }
            if (StartProfileOperation && StartProfileOperation(profile, DownloadOperation))
            {
                ProfileReloads[kind].state = RuntimeRequestState::inFlight;
                AlwaysofflineRe::log(std::string("Editor started CODOL ") +
                    (kind == PublicProfileKind ? "Publicprofile" : "Privateprofile") +
                    " reload.");
            }
        }
    }

    __declspec(naked) void profileManagerFrameHook()
    {
        __asm
        {
            pushfd
            pushad
            push eax
            call processRuntimeRequests
            add esp, 4
            popad
            popfd
            jmp dword ptr [OriginalProfileManagerFrame]
        }
    }

    bool installProfileManagerFrameHook(std::uint8_t *module, const std::span<std::uint8_t> image)
    {
        if (ProfileManagerFrameRva > image.size() ||
            ProfileManagerFramePrologueSize > image.size() - ProfileManagerFrameRva ||
            ProfileStartOperationRva >= image.size())
        {
            return false;
        }

        auto *target = module + ProfileManagerFrameRva;
        if (!std::equal(ProfileManagerFramePrefix.begin(), ProfileManagerFramePrefix.end(), target))
            return false;

        auto *trampoline = static_cast<std::uint8_t *>(VirtualAlloc(
            nullptr,
            ProfileManagerFramePrologueSize + 5,
            MEM_COMMIT | MEM_RESERVE,
            PAGE_EXECUTE_READWRITE));
        if (!trampoline)
            return false;

        std::copy_n(target, ProfileManagerFramePrologueSize, trampoline);
        trampoline[ProfileManagerFramePrologueSize] = 0xE9;
        *reinterpret_cast<std::int32_t *>(trampoline + ProfileManagerFramePrologueSize + 1) =
            static_cast<std::int32_t>((target + ProfileManagerFramePrologueSize) -
                (trampoline + ProfileManagerFramePrologueSize + 5));

        DWORD oldProtection{};
        if (!VirtualProtect(target, ProfileManagerFramePrologueSize, PAGE_EXECUTE_READWRITE, &oldProtection))
        {
            VirtualFree(trampoline, 0, MEM_RELEASE);
            return false;
        }

        OriginalProfileManagerFrame = trampoline;
        StartProfileOperation = reinterpret_cast<ProfileStartOperation>(module + ProfileStartOperationRva);
        target[0] = 0xE9;
        *reinterpret_cast<std::int32_t *>(target + 1) = static_cast<std::int32_t>(
            reinterpret_cast<std::uint8_t *>(&profileManagerFrameHook) - (target + 5));
        std::fill(target + 5, target + ProfileManagerFramePrologueSize, std::uint8_t{ 0x90 });
        FlushInstructionCache(GetCurrentProcess(), target, ProfileManagerFramePrologueSize);
        VirtualProtect(target, ProfileManagerFramePrologueSize, oldProtection, &oldProtection);
        ProfileManagerHookInstalled = true;
        return true;
    }

    bool installPublicProfileRequestHook(std::uint8_t *module, const std::span<std::uint8_t> image)
    {
        if (PublicProfileRequestCallRva > image.size() ||
            PublicProfileRequestCall.size() > image.size() - PublicProfileRequestCallRva ||
            GetPublicProfilesRva >= image.size())
        {
            return false;
        }

        auto *call = module + PublicProfileRequestCallRva;
        if (!std::equal(PublicProfileRequestCall.begin(), PublicProfileRequestCall.end(), call))
            return false;

        DWORD oldProtection{};
        if (!VirtualProtect(call, PublicProfileRequestCall.size(), PAGE_EXECUTE_READWRITE, &oldProtection))
            return false;

        OriginalGetPublicProfiles = reinterpret_cast<GetPublicProfiles>(module + GetPublicProfilesRva);
        call[0] = 0xE8;
        *reinterpret_cast<std::int32_t *>(call + 1) = static_cast<std::int32_t>(
            reinterpret_cast<std::uint8_t *>(&getPublicProfilesHook) - (call + 5));
        FlushInstructionCache(GetCurrentProcess(), call, PublicProfileRequestCall.size());
        VirtualProtect(call, PublicProfileRequestCall.size(), oldProtection, &oldProtection);
        return true;
    }

    bool installProfileCompletionHook(std::uint8_t *module, const std::span<std::uint8_t> image)
    {
        if (ProfileCompletionRva > image.size() ||
            ProfileCompletionPrologueSize > image.size() - ProfileCompletionRva ||
            InventoryRequestRva > image.size() ||
            InventoryRequestPrefix.size() > image.size() - InventoryRequestRva ||
            CurrentCharacterCacheRva > image.size() ||
            sizeof(LONG) > image.size() - CurrentCharacterCacheRva)
        {
            return false;
        }

        auto *target = module + ProfileCompletionRva;
        if (!std::equal(ProfileCompletionPrefix.begin(), ProfileCompletionPrefix.end(), target) ||
            !std::equal(
                InventoryRequestPrefix.begin(), InventoryRequestPrefix.end(),
                module + InventoryRequestRva))
        {
            return false;
        }

        auto *trampoline = static_cast<std::uint8_t *>(VirtualAlloc(
            nullptr,
            ProfileCompletionPrologueSize + 5,
            MEM_COMMIT | MEM_RESERVE,
            PAGE_EXECUTE_READWRITE));
        if (!trampoline)
            return false;

        std::copy_n(target, ProfileCompletionPrologueSize, trampoline);
        trampoline[ProfileCompletionPrologueSize] = 0xE9;
        *reinterpret_cast<std::int32_t *>(trampoline + ProfileCompletionPrologueSize + 1) =
            static_cast<std::int32_t>((target + ProfileCompletionPrologueSize) -
                (trampoline + ProfileCompletionPrologueSize + 5));

        DWORD oldProtection{};
        if (!VirtualProtect(target, ProfileCompletionPrologueSize, PAGE_EXECUTE_READWRITE, &oldProtection))
        {
            VirtualFree(trampoline, 0, MEM_RELEASE);
            return false;
        }

        OriginalProfileCompletion = reinterpret_cast<ProfileCompletion>(trampoline);
        RequestInventory = reinterpret_cast<InventoryRequest>(module + InventoryRequestRva);
        CurrentCharacterCache = reinterpret_cast<volatile LONG *>(
            module + CurrentCharacterCacheRva);
        target[0] = 0xE9;
        *reinterpret_cast<std::int32_t *>(target + 1) = static_cast<std::int32_t>(
            reinterpret_cast<std::uint8_t *>(&profileCompletionHook) - (target + 5));
        std::fill(target + 5, target + ProfileCompletionPrologueSize, std::uint8_t{ 0x90 });
        FlushInstructionCache(GetCurrentProcess(), target, ProfileCompletionPrologueSize);
        VirtualProtect(target, ProfileCompletionPrologueSize, oldProtection, &oldProtection);
        return true;
    }

    SiteState inspectSite(const std::span<const std::uint8_t> image, const PatchSite &site)
    {
        if (site.rva > image.size() || site.size > image.size() - site.rva)
            return SiteState::invalid;
        const auto bytes = image.subspan(site.rva, site.size);
        if (std::equal(bytes.begin(), bytes.end(), site.original.begin()))
            return SiteState::original;
        if (std::equal(bytes.begin(), bytes.end(), site.patched.begin()))
            return SiteState::patched;
        return SiteState::invalid;
    }

    bool inspectAll(
        const std::span<const std::uint8_t> image,
        std::array<SiteState, PatchSites.size()> &states)
    {
        for (std::size_t index = 0; index != PatchSites.size(); ++index)
        {
            states[index] = inspectSite(image, PatchSites[index]);
            if (states[index] == SiteState::invalid)
                return false;
        }
        return true;
    }

    void applyPatches(
        const std::span<std::uint8_t> image,
        const std::array<SiteState, PatchSites.size()> &states)
    {
        for (std::size_t index = 0; index != PatchSites.size(); ++index)
        {
            if (states[index] != SiteState::original)
                continue;
            const auto &site = PatchSites[index];
            std::copy_n(site.patched.begin(), site.size, image.begin() + site.rva);
        }
    }

    bool isCodolHost()
    {
        std::array<wchar_t, 32768> path{};
        const auto size = GetModuleFileNameW(nullptr, path.data(), static_cast<DWORD>(path.size()));
        if (!size || size >= path.size())
            return false;
        const std::wstring_view value(path.data(), size);
        const auto separator = value.find_last_of(L"\\/");
        const auto name = separator == std::wstring_view::npos ? value : value.substr(separator + 1);
        return _wcsicmp(std::wstring(name).c_str(), L"codoMP_client_shipRetail.exe") == 0;
    }

    bool install()
    {
        auto *module = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
        if (!module)
            return false;
        const auto *dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(module);
        if (dos->e_magic != IMAGE_DOS_SIGNATURE)
            return false;
        const auto *nt = reinterpret_cast<const IMAGE_NT_HEADERS *>(module + dos->e_lfanew);
        if (nt->Signature != IMAGE_NT_SIGNATURE ||
            nt->FileHeader.Machine != IMAGE_FILE_MACHINE_I386 ||
            nt->FileHeader.TimeDateStamp != CodolTimestamp ||
            nt->OptionalHeader.SizeOfImage != CodolImageSize)
        {
            return false;
        }

        std::span<std::uint8_t> image(module, nt->OptionalHeader.SizeOfImage);
        std::array<SiteState, PatchSites.size()> states{};
        if (!inspectAll(image, states))
            return false;

        struct ProtectedRange
        {
            void *address{};
            std::size_t size{};
            DWORD previous{};
        };
        std::array<ProtectedRange, PatchSites.size()> ranges{};
        std::size_t protectedCount{};
        for (std::size_t index = 0; index != PatchSites.size(); ++index)
        {
            if (states[index] != SiteState::original)
                continue;
            const auto &site = PatchSites[index];
            auto &range = ranges[protectedCount];
            range = ProtectedRange{module + site.rva, site.size};
            if (!VirtualProtect(range.address, range.size, PAGE_EXECUTE_READWRITE, &range.previous))
            {
                while (protectedCount)
                {
                    auto &previous = ranges[--protectedCount];
                    DWORD ignored{};
                    VirtualProtect(previous.address, previous.size, previous.previous, &ignored);
                }
                return false;
            }
            ++protectedCount;
        }

        applyPatches(image, states);
        FlushInstructionCache(GetCurrentProcess(), module, image.size());
        while (protectedCount)
        {
            auto &range = ranges[--protectedCount];
            DWORD ignored{};
            VirtualProtect(range.address, range.size, range.previous, &ignored);
        }
        return installProfileCompletionHook(module, image) &&
            installInventoryFinalizeHook(module, image) &&
            installPublicProfileRequestHook(module, image) &&
            installProfileManagerFrameHook(module, image);
    }
}

namespace AlwaysofflineRe::Demonware
{
    bool patchCodolStartupBuffer(const std::span<std::uint8_t> image)
    {
        std::array<SiteState, PatchSites.size()> states{};
        if (!inspectAll(image, states))
            return false;
        applyPatches(image, states);
        return true;
    }

    bool shouldRequestCodolInventory(
        const std::uint32_t profileKind,
        const std::uint32_t operation,
        const bool succeeded,
        const std::uint32_t errorCode)
    {
        return profileKind == PublicProfileKind &&
            operation == DownloadOperation &&
            (succeeded || errorCode == MissingProfileError);
    }

    bool shouldInvalidateCodolCurrentCharacterCache(
        const std::uint32_t profileKind,
        const std::uint32_t operation,
        const bool succeeded,
        const std::uint32_t errorCode)
    {
        return profileKind == PublicProfileKind &&
            operation == DownloadOperation &&
            succeeded &&
            errorCode == 0;
    }

    bool installCodolStartupPatches()
    {
        if (!isCodolHost())
            return true;
        return install();
    }

    std::uint32_t requestCodolProfileReload(const std::uint32_t profileKind)
    {
        if (!ProfileManagerHookInstalled.load() || !isProfileKind(profileKind))
            return 0;
        auto &request = ProfileReloads[profileKind];
        if (request.state.load() == RuntimeRequestState::queued ||
            request.state.load() == RuntimeRequestState::inFlight)
        {
            return request.generation.load();
        }
        request.errorCode = 0;
        const auto generation = request.generation.fetch_add(1) + 1;
        request.state = RuntimeRequestState::queued;
        return generation;
    }

    bool getCodolProfileReloadStatus(
        const std::uint32_t profileKind,
        std::uint32_t &generation,
        std::uint32_t &state,
        std::uint32_t &errorCode)
    {
        if (!ProfileManagerHookInstalled.load() || !isProfileKind(profileKind))
            return false;
        const auto &request = ProfileReloads[profileKind];
        generation = request.generation.load();
        state = static_cast<std::uint32_t>(request.state.load());
        errorCode = request.errorCode.load();
        return true;
    }

    std::uint32_t requestCodolInventoryRefresh()
    {
        if (!ProfileManagerHookInstalled.load())
            return 0;
        if (InventoryRefresh.state.load() == RuntimeRequestState::queued ||
            InventoryRefresh.state.load() == RuntimeRequestState::inFlight)
        {
            return InventoryRefresh.generation.load();
        }
        InventoryRefresh.errorCode = 0;
        const auto generation = InventoryRefresh.generation.fetch_add(1) + 1;
        InventoryRefresh.state = RuntimeRequestState::queued;
        return generation;
    }

    bool getCodolInventoryRefreshStatus(
        std::uint32_t &generation,
        std::uint32_t &state,
        std::uint32_t &errorCode)
    {
        if (!ProfileManagerHookInstalled.load())
            return false;
        generation = InventoryRefresh.generation.load();
        state = static_cast<std::uint32_t>(InventoryRefresh.state.load());
        errorCode = InventoryRefresh.errorCode.load();
        return true;
    }
}
