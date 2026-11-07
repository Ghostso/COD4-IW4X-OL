#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include "platformwrapper/PlatformConfig.hpp"
#include "platformwrapper/Tencent.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

namespace
{
    int Failures{};

    void check(const bool condition, const std::string &message)
    {
        if (condition)
            return;
        ++Failures;
        std::cerr << "FAIL: " << message << '\n';
    }
}

int main()
{
    using namespace OlMod::Platformwrapper;

    const auto paths = runtimePathsFromModule(
        LR"(E:\Games\CODOL\Ayria\Plugins\Platformwrapper.Ayria32)");
    check(paths.ayriaRoot == LR"(E:\Games\CODOL\Ayria)", "Ayria root follows module location");
    check(paths.gameRoot == LR"(E:\Games\CODOL)", "game root follows module location");
    check(
        paths.config == paths.assets / L"Platform.json",
        "canonical config belongs to Platformwrapper assets");

    check(
        platformIdString(0x01100001DEADC0DEull) == "01100001DEADC0DE",
        "platform ID uses archived uppercase hexadecimal format");
    PlatformConfig defaults;
    check(
        authenticationDescriptor(defaults) == "auth3.qq.com:3074;lsg.qq.com:3074;1004",
        "authentication descriptor preserves CODOL wire format");

    const auto fixtureRoot = std::filesystem::temp_directory_path() / L"ol-mod-platformwrapper-tests";
    const auto fixturePaths = runtimePathsFromModule(
        fixtureRoot / L"Ayria" / L"Plugins" / L"Platformwrapper.Ayria32");
    std::filesystem::remove_all(fixtureRoot);
    std::filesystem::create_directories(fixturePaths.assets);
    {
        std::ofstream legacy(fixturePaths.assets / L"UserID.txt", std::ios::binary);
        legacy << "DEADC0DE\r\n";
    }
    auto legacy = loadPlatformConfig(fixturePaths);
    check(
        legacy.platformUserId == 0x01100001DEADC0DEull,
        "legacy low account ID expands to a full platform ID");
    {
        std::ofstream canonical(fixturePaths.config, std::ios::binary);
        canonical << R"({
  "schemaVersion": 1,
  "titleId": 1004,
  "gameVersion": 43,
  "zoneId": 7,
  "serverId": 2,
  "platformUserId": "0110000100001234",
  "authEndpoint": "auth.test:3074",
  "lobbyEndpoint": "lsg.test:3074"
})";
    }
    const auto canonical = loadPlatformConfig(fixturePaths);
    check(canonical.platformUserId == 0x0110000100001234ull, "canonical config overrides legacy ID");
    check(canonical.gameVersion == 43 && canonical.zoneId == 7 && canonical.serverId == 2,
        "canonical numeric Tencent tags load");
    check(authenticationDescriptor(canonical) == "auth.test:3074;lsg.test:3074;1004",
        "canonical endpoints feed Tencent tag 8");
    _putenv_s("OLMOD_PLATFORM_USER_ID", "0110000100005678");
    const auto processOverride = loadPlatformConfig(fixturePaths);
    _putenv_s("OLMOD_PLATFORM_USER_ID", "");
    check(
        processOverride.platformUserId == 0x0110000100005678ull,
        "process platform ID override isolates local client identities");
    std::filesystem::remove_all(fixtureRoot);

    TencentInterface interface(defaults);
    std::uint32_t size{};
    check(interface.getBytestring(22, nullptr, &size) == TRUE && size == 16,
        "Tencent platform ID size query");
    std::uint8_t platformId[16]{};
    auto capacity = static_cast<std::uint32_t>(sizeof(platformId));
    check(interface.getBytestring(22, platformId, &capacity) == TRUE,
        "Tencent platform ID read");
    check(std::string(reinterpret_cast<char *>(platformId), sizeof(platformId)) == "01100001DEADC0DE",
        "Tencent tag 22 carries configured platform ID");
    std::uint32_t dword{};
    check(interface.getDWORD(1, &dword) == TRUE && dword == 42,
        "Tencent game-version tag");
    check(interface.Initialize() == TRUE, "Tencent shared-memory initialization");
    check(interface.Uninitialize() == TRUE, "Tencent shared-memory cleanup");

    std::wstring executable(32768, L'\0');
    const auto executableSize = GetModuleFileNameW(
        nullptr, executable.data(), static_cast<DWORD>(executable.size()));
    check(executableSize != 0 && executableSize < executable.size(), "resolve test executable");
    executable.resize(executableSize);
    const auto rebuiltModule = std::filesystem::path(executable).parent_path() /
        L"PlatformwrapperRe.Ayria32";
    std::ifstream pe(rebuiltModule, std::ios::binary);
    IMAGE_DOS_HEADER dos{};
    IMAGE_FILE_HEADER fileHeader{};
    if (pe.read(reinterpret_cast<char *>(&dos), sizeof(dos)) && dos.e_magic == IMAGE_DOS_SIGNATURE)
    {
        pe.seekg(dos.e_lfanew + sizeof(DWORD));
        pe.read(reinterpret_cast<char *>(&fileHeader), sizeof(fileHeader));
    }
    check(fileHeader.Machine == IMAGE_FILE_MACHINE_I386, "rebuilt Platformwrapper is PE32/x86");
    const auto rebuilt = LoadLibraryW(rebuiltModule.c_str());
    check(rebuilt != nullptr, "load rebuilt Platformwrapper DLL");
    if (rebuilt)
    {
        const char *exports[]{
            "onStartup",
            "onInitialized",
            "onMessage",
            "Invoke",
            "CreateObj",
            "InitCrossContextByOpenID",
        };
        for (const auto *name : exports)
            check(GetProcAddress(rebuilt, name) != nullptr, std::string("export ") + name);
        FreeLibrary(rebuilt);
    }

    if (Failures)
        return 1;
    std::cout << "Platformwrapper tests passed.\n";
    return 0;
}
