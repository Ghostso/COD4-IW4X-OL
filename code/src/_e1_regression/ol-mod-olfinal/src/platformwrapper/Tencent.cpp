#include "Tencent.hpp"

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <mutex>

namespace
{
    std::mutex ConfigMutex;
    OlMod::Platformwrapper::RuntimePaths Paths;
    OlMod::Platformwrapper::PlatformConfig Config;

    void notifyBootstrapperInitialized()
    {
        HMODULE bootstrapper = GetModuleHandleW(L"Localbootstrap.dll");
        if (!bootstrapper)
            bootstrapper = GetModuleHandleW(L"Bootstrapper32.dll");
        if (!bootstrapper)
            bootstrapper = GetModuleHandleW(L"Bootstrapper32d.dll");
        if (!bootstrapper)
            return;
        const auto callback = reinterpret_cast<void(__cdecl *)()>(
            GetProcAddress(bootstrapper, "onInitializationdone"));
        if (callback)
            callback();
    }
}

namespace OlMod::Platformwrapper
{
    TencentInterface::TencentInterface(PlatformConfig config)
        : config_(std::move(config)),
          wideStrings_{{14, L"Appname"}, {15, L"Windowname"}, {16, L"PASS:-q"}},
          byteStrings_{
              {3, "7"},
              {4, "Gamesig"},
              {5, "Loginkey"},
              {7, "Appticket"},
              {8, authenticationDescriptor(config_)},
              {22, platformIdString(config_.platformUserId)},
              {24, "Tencentticket"},
              {25, "OpenIDKey"},
              {26, "7"},
              {27, "Jumpsig"},
          },
          dwords_{
              {1, config_.gameVersion},
              {5, config_.zoneId},
              {7, 38},
              {18, config_.serverId},
          }
    {
    }

    void TencentInterface::notify(const std::uint32_t tag, const bool serverScoped) const
    {
        auto window = FindWindowW(L"static", nullptr);
        while (window)
        {
            PostMessageW(window, 0xBD2u, 1u | (tag << 16u), serverScoped ? 1 : 0);
            window = FindWindowExW(nullptr, window, L"static", nullptr);
        }
    }

    BOOL TencentInterface::getLogininfo(void *)
    {
        notify(0x65, false);
        return TRUE;
    }

    BOOL TencentInterface::Initialize()
    {
        if (sharedView_)
            return TRUE;
        const auto name = "TCLS_SHAREDMEMEMORY" + std::to_string(GetCurrentProcessId());
        sharedMapping_ = CreateFileMappingA(
            INVALID_HANDLE_VALUE, nullptr, PAGE_READWRITE, 0, 4096, name.c_str());
        if (!sharedMapping_)
            return FALSE;
        sharedView_ = MapViewOfFile(sharedMapping_, FILE_MAP_ALL_ACCESS, 0, 0, 4096);
        if (!sharedView_)
        {
            CloseHandle(sharedMapping_);
            sharedMapping_ = nullptr;
            return FALSE;
        }
        *static_cast<DWORD *>(sharedView_) = 64;
        notify(0x64, false);
        return TRUE;
    }

    BOOL TencentInterface::Restart() { return TRUE; }

    BOOL TencentInterface::Uninitialize()
    {
        if (sharedView_)
        {
            UnmapViewOfFile(sharedView_);
            sharedView_ = nullptr;
        }
        if (sharedMapping_)
        {
            CloseHandle(sharedMapping_);
            sharedMapping_ = nullptr;
        }
        return TRUE;
    }

    BOOL TencentInterface::setEventhandler(void *) { return TRUE; }
    void TencentInterface::ReleaseTENIO() {}
    BOOL TencentInterface::Notifyshutdown() { return TRUE; }
    void *TencentInterface::Closehandle() { return this; }

    BOOL TencentInterface::getInteger(const std::uint32_t tag, std::int32_t *buffer)
    {
        const auto iterator = integers_.find(tag);
        if (iterator != integers_.end() && buffer)
            *buffer = iterator->second;
        notify(tag, false);
        return iterator != integers_.end();
    }

    BOOL TencentInterface::getDWORD(const std::uint32_t tag, std::uint32_t *buffer)
    {
        return getDWORD_(tag, buffer, 0);
    }

    BOOL TencentInterface::getBytestring(
        const std::uint32_t tag, std::uint8_t *buffer, std::uint32_t *size)
    {
        return getBytestring_(tag, buffer, size, 0);
    }

    BOOL TencentInterface::getWidestring(
        const std::uint32_t tag, wchar_t *buffer, std::uint32_t *size)
    {
        return getWidestring_(tag, buffer, size, 0);
    }

    BOOL TencentInterface::getBytestring_(
        const std::uint32_t tag,
        std::uint8_t *buffer,
        std::uint32_t *size,
        const std::uint32_t serverId)
    {
        if (!size)
            return FALSE;
        const auto iterator = byteStrings_.find(tag);
        if (iterator == byteStrings_.end())
            return FALSE;
        const auto available = *size;
        *size = static_cast<std::uint32_t>(iterator->second.size());
        if (buffer && available)
            std::memcpy(buffer, iterator->second.data(), std::min<std::size_t>(available, iterator->second.size()));
        notify(tag, serverId != 0);
        return TRUE;
    }

    BOOL TencentInterface::getWidestring_(
        const std::uint32_t tag,
        wchar_t *buffer,
        std::uint32_t *size,
        const std::uint32_t serverId)
    {
        if (!size)
            return FALSE;
        const auto iterator = wideStrings_.find(tag);
        if (iterator == wideStrings_.end())
            return FALSE;
        const auto availableCharacters = *size / sizeof(wchar_t);
        *size = static_cast<std::uint32_t>(iterator->second.size() * sizeof(wchar_t));
        if (buffer && availableCharacters)
            std::wmemcpy(buffer, iterator->second.data(), std::min<std::size_t>(availableCharacters, iterator->second.size()));
        notify(tag, serverId != 0);
        return TRUE;
    }

    BOOL TencentInterface::getDWORD_(
        const std::uint32_t tag, std::uint32_t *buffer, const std::uint32_t serverId)
    {
        const auto iterator = dwords_.find(tag);
        if (iterator != dwords_.end() && buffer)
            *buffer = iterator->second;
        notify(tag, serverId != 0);
        return iterator != dwords_.end();
    }

    std::size_t TensafeInterface000::setInitinfo(InitInfo *info)
    {
        if (!info)
            return 0;
        uin_ = info->uin;
        gameVersion_ = info->gameVersion;
        sink_ = info->sink;
        return 1;
    }

    std::size_t TensafeInterface000::onLogin()
    {
        startupTime_ = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
        std::srand(static_cast<unsigned int>(startupTime_));
        userId_ = static_cast<std::uint32_t>(std::rand());
        return 1;
    }

    std::size_t TensafeInterface000::Encrypt(EncryptedPackage *packet)
    {
        return packet ? 1 : 2;
    }

    std::size_t TensafeInterface000::isCheatpacket(std::uint32_t) { return 0; }
    std::size_t TensafeInterface000::Decrypt(EncryptedPackage *) { return 1; }
    std::size_t TensafeInterface000::Release() { return 1; }

    void setRuntimePaths(RuntimePaths paths)
    {
        std::lock_guard lock(ConfigMutex);
        Paths = std::move(paths);
        Config = loadPlatformConfig(Paths);
    }

    const PlatformConfig &activeConfig()
    {
        return Config;
    }
}

extern "C" __declspec(dllexport) void __cdecl Invoke(
    std::uint32_t, void **interfacePointer)
{
    if (!interfacePointer)
        return;
    *interfacePointer = new OlMod::Platformwrapper::TencentInterface(
        OlMod::Platformwrapper::activeConfig());
    notifyBootstrapperInitialized();
}

extern "C" __declspec(dllexport) void *__cdecl CreateObj(const int type)
{
    return type == 0 ? static_cast<void *>(new OlMod::Platformwrapper::TensafeInterface000()) : nullptr;
}

extern "C" __declspec(dllexport) int __cdecl InitCrossContextByOpenID(void *)
{
    return 0;
}
