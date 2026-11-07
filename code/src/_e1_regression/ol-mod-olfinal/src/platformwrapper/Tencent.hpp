#pragma once

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "PlatformConfig.hpp"

#include <cstddef>
#include <cstdint>
#include <string>
#include <unordered_map>

namespace OlMod::Platformwrapper
{
    class TencentInterface
    {
    public:
        explicit TencentInterface(PlatformConfig config);

        virtual BOOL getLogininfo(void *loginInfo);
        virtual BOOL Initialize();
        virtual BOOL Restart();
        virtual BOOL Uninitialize();
        virtual BOOL setEventhandler(void *eventHandler);
        virtual void ReleaseTENIO();
        virtual BOOL Notifyshutdown();
        virtual void *Closehandle();
        virtual BOOL getInteger(std::uint32_t tag, std::int32_t *buffer);
        virtual BOOL getDWORD(std::uint32_t tag, std::uint32_t *buffer);
        virtual BOOL getBytestring(std::uint32_t tag, std::uint8_t *buffer, std::uint32_t *size);
        virtual BOOL getWidestring(std::uint32_t tag, wchar_t *buffer, std::uint32_t *size);
        virtual BOOL getBytestring_(
            std::uint32_t tag,
            std::uint8_t *buffer,
            std::uint32_t *size,
            std::uint32_t serverId);
        virtual BOOL getWidestring_(
            std::uint32_t tag,
            wchar_t *buffer,
            std::uint32_t *size,
            std::uint32_t serverId);
        virtual BOOL getDWORD_(
            std::uint32_t tag,
            std::uint32_t *buffer,
            std::uint32_t serverId);

    private:
        void notify(std::uint32_t tag, bool serverScoped) const;

        PlatformConfig config_;
        std::unordered_map<std::uint32_t, std::wstring> wideStrings_;
        std::unordered_map<std::uint32_t, std::string> byteStrings_;
        std::unordered_map<std::uint32_t, std::int32_t> integers_;
        std::unordered_map<std::uint32_t, std::uint32_t> dwords_;
        HANDLE sharedMapping_{};
        void *sharedView_{};
    };

    class TensafeInterface000
    {
    public:
        struct InitInfo
        {
            std::uint32_t uin;
            std::uint32_t gameVersion;
            std::size_t sink;
        };

        struct EncryptedPackage
        {
            std::uint32_t command;
            std::uint8_t *gamePackage;
            std::uint32_t gameLength;
            std::uint8_t *encryptedPackage;
            std::uint32_t encryptedLength;
        };

        virtual std::size_t setInitinfo(InitInfo *info);
        virtual std::size_t onLogin();
        virtual std::size_t Encrypt(EncryptedPackage *packet);
        virtual std::size_t isCheatpacket(std::uint32_t command);
        virtual std::size_t Decrypt(EncryptedPackage *packet);
        virtual std::size_t Release();

    private:
        // Present in the archived CODOL DLL before the 2019 source fields.
        // It shifts userId to +0x08 and the 64-bit sink to +0x18.
        std::uint32_t unknown0_{};
        std::uint32_t userId_{};
        std::uint32_t uin_{};
        std::uint32_t gameVersion_{};
        std::uint64_t sink_{};
        std::int64_t startupTime_{};
        std::uint32_t configNeedsReload_{};
        char outgoingPacket_[512]{};
        char incomingPacket_[512]{};
        std::uint32_t unknown_{};
        std::uint32_t sequenceId_{};
        std::uint32_t packetsReceived_{};
        std::uint32_t unknown2_{};
        std::uint32_t encryptedPacketsReceived_{};
        std::uint32_t unknown3_{};
        std::uint32_t clientSent_{};
        std::uint32_t clientReceived_{};
        char configData_[1030]{};
    };

    static_assert(sizeof(TensafeInterface000) == 0x858);

    void setRuntimePaths(RuntimePaths paths);
    [[nodiscard]] const PlatformConfig &activeConfig();
}

extern "C"
{
    __declspec(dllexport) void __cdecl Invoke(std::uint32_t gameId, void **interfacePointer);
    __declspec(dllexport) void *__cdecl CreateObj(int type);
    __declspec(dllexport) int __cdecl InitCrossContextByOpenID(void *context);
}
