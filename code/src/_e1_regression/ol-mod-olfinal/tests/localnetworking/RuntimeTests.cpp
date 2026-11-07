#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#define _WINSOCK_DEPRECATED_NO_WARNINGS
#include <WinSock2.h>
#include <Windows.h>
#include <Ws2tcpip.h>

#include "localnetworking/Localnetworking.hpp"

#include <cstring>
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

    SOCKET connectFixtureStream(
        OlMod::Localnetworking::Bridge &bridge,
        const DWORD receiveTimeout)
    {
        auto client = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (client == INVALID_SOCKET)
            return INVALID_SOCKET;
        setsockopt(
            client,
            SOL_SOCKET,
            SO_RCVTIMEO,
            reinterpret_cast<const char *>(&receiveTimeout),
            sizeof(receiveTimeout));

        sockaddr_in local{};
        local.sin_family = AF_INET;
        local.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        if (bind(client, reinterpret_cast<const sockaddr *>(&local), sizeof(local)) != 0)
        {
            closesocket(client);
            return INVALID_SOCKET;
        }
        int localSize = sizeof(local);
        if (getsockname(client, reinterpret_cast<sockaddr *>(&local), &localSize) != 0)
        {
            closesocket(client);
            return INVALID_SOCKET;
        }
        bridge.associatePort("fixture.local", local.sin_port);

        sockaddr_in backend{};
        backend.sin_family = AF_INET;
        backend.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        backend.sin_port = htons(bridge.backendPort());
        if (connect(client, reinterpret_cast<const sockaddr *>(&backend), sizeof(backend)) != 0)
        {
            closesocket(client);
            return INVALID_SOCKET;
        }
        return client;
    }
}

int main()
{
    using namespace OlMod::Localnetworking;

    const auto paths = runtimePathsFromModule(
        LR"(E:\Games\CODOL\OLModRuntime\Plugins\Localnetworking.Ayria32)");
    check(
        paths.root == std::filesystem::path(LR"(E:\Games\CODOL\OLModRuntime)"),
        "runtime root follows the module location");
    check(paths.plugins == paths.root / L"Plugins", "plugin directory is module-relative");
    check(paths.logs == paths.root / L"Logs", "log directory is module-relative");
    check(paths.assets == paths.root / L"Assets", "asset directory is module-relative");

    check(isLocalnetPluginFilename(L"Alwaysoffline.Localnet32"), "canonical Localnet32 name");
    check(isLocalnetPluginFilename(L"BACKEND.LOCALNET32"), "case-insensitive Localnet32 name");
    check(!isLocalnetPluginFilename(L"Backend.Localnet64"), "reject Localnet64 plugin");
    check(!isLocalnetPluginFilename(L"Backend.Localnet32.bak"), "reject backup suffix");

    check(fnv1a32("auth3.qq.com") == 0x9C2BA8FFu, "archived FNV-1a mapping");
    check(
        ntohl(syntheticIpv4("auth3.qq.com")) == 0xF09C2BA8u,
        "synthetic address uses the archived 240/8 mapping");
    check(
        syntheticIpv4("auth3.qq.com") != syntheticIpv4("lsg.qq.com"),
        "different hosts receive different synthetic addresses");

    std::wstring executable(32768, L'\0');
    const auto executableSize = GetModuleFileNameW(
        nullptr,
        executable.data(),
        static_cast<DWORD>(executable.size()));
    check(executableSize != 0 && executableSize < executable.size(), "resolve test executable");
    executable.resize(executableSize);
    const auto binaryDirectory = std::filesystem::path(executable).parent_path();
    const auto rebuiltModule = binaryDirectory / L"LocalnetworkingRe.Ayria32";
    std::ifstream pe(rebuiltModule, std::ios::binary);
    IMAGE_DOS_HEADER dos{};
    IMAGE_FILE_HEADER fileHeader{};
    if (pe.read(reinterpret_cast<char *>(&dos), sizeof(dos)) && dos.e_magic == IMAGE_DOS_SIGNATURE)
    {
        pe.seekg(dos.e_lfanew + sizeof(DWORD));
        pe.read(reinterpret_cast<char *>(&fileHeader), sizeof(fileHeader));
    }
    check(fileHeader.Machine == IMAGE_FILE_MACHINE_I386, "rebuilt Localnetworking is PE32/x86");
    const auto rebuilt = LoadLibraryW(rebuiltModule.c_str());
    check(rebuilt != nullptr, "load rebuilt Localnetworking DLL");
    if (rebuilt)
    {
        check(GetProcAddress(rebuilt, "onStartup") != nullptr, "export onStartup");
        check(GetProcAddress(rebuilt, "onInitialized") != nullptr, "export onInitialized");
        check(GetProcAddress(rebuilt, "onMessage") != nullptr, "export onMessage");
        FreeLibrary(rebuilt);
    }

    const auto fixtureModule = std::filesystem::path(executable).parent_path() /
        L"localnetworking_fixture" / L"Plugins" / L"Localnetworking.Ayria32";
    const auto fixturePaths = runtimePathsFromModule(fixtureModule);
    check(
        std::filesystem::exists(fixturePaths.plugins / L"Fixture.Localnet32"),
        "fixture Localnet32 plugin was built");

    auto &bridge = Bridge::instance();
    check(bridge.start(fixturePaths, 48400), "start fixture Localnetworking bridge");
    check(bridge.claimsHost("fixture.local"), "fixture plugin claims its hostname");
    check(!bridge.claimsHost("not-owned.local"), "unclaimed hostname remains external");

    DWORD receiveTimeout = 2000;
    auto client = connectFixtureStream(bridge, receiveTimeout);
    check(client != INVALID_SOCKET, "connect fixture stream through backend");
    check(send(client, "ping", 4, 0) == 4, "send fixture request");

    char response[16]{};
    const auto received = recv(client, response, sizeof(response), 0);
    check(received == 4 && std::string(response, 4) == "pong", "receive fixture response");
    closesocket(client);

    auto fanoutClientA = connectFixtureStream(bridge, receiveTimeout);
    auto fanoutClientB = connectFixtureStream(bridge, receiveTimeout);
    check(
        fanoutClientA != INVALID_SOCKET && fanoutClientB != INVALID_SOCKET,
        "connect two streams to one server instance");
    check(send(fanoutClientA, "ping", 4, 0) == 4, "send fan-out fixture request");
    std::memset(response, 0, sizeof(response));
    const auto fanoutA = recv(fanoutClientA, response, sizeof(response), 0);
    check(fanoutA == 4 && std::string(response, 4) == "pong", "fan-out response reaches sender");
    std::memset(response, 0, sizeof(response));
    const auto fanoutB = recv(fanoutClientB, response, sizeof(response), 0);
    check(fanoutB == 4 && std::string(response, 4) == "pong", "fan-out response reaches peer");
    closesocket(fanoutClientA);
    closesocket(fanoutClientB);

    check(installWinsockHooks(), "install archived Winsock hook surface");
    auto *host = gethostbyname("fixture.local");
    check(host && host->h_addr_list && host->h_addr_list[0], "hook gethostbyname");
    std::uint32_t proxyAddress{};
    if (host && host->h_addr_list && host->h_addr_list[0])
        std::memcpy(&proxyAddress, host->h_addr_list[0], sizeof(proxyAddress));
    check(proxyAddress == syntheticIpv4("fixture.local"), "gethostbyname synthetic address");

    addrinfo hints{};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    addrinfo *addresses{};
    check(
        getaddrinfo("fixture.local", "3074", &hints, &addresses) == 0 && addresses,
        "hook getaddrinfo");
    for (auto *entry = addresses; entry; entry = entry->ai_next)
    {
        check(
            entry->ai_family == AF_INET && entry->ai_addr &&
                reinterpret_cast<sockaddr_in *>(entry->ai_addr)->sin_addr.s_addr == proxyAddress,
            "every getaddrinfo result uses the IPv4 synthetic address");
    }
    if (addresses)
        freeaddrinfo(addresses);

    auto hookedStream = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    setsockopt(
        hookedStream,
        SOL_SOCKET,
        SO_RCVTIMEO,
        reinterpret_cast<const char *>(&receiveTimeout),
        sizeof(receiveTimeout));
    sockaddr_in proxyTarget{};
    proxyTarget.sin_family = AF_INET;
    proxyTarget.sin_addr.s_addr = proxyAddress;
    proxyTarget.sin_port = htons(3074);
    check(
        connect(
            hookedStream,
            reinterpret_cast<const sockaddr *>(&proxyTarget),
            sizeof(proxyTarget)) == 0,
        "hook connect redirects synthetic address");
    check(send(hookedStream, "ping", 4, 0) == 4, "send through hooked stream");
    std::memset(response, 0, sizeof(response));
    const auto hookedStreamReceived = recv(hookedStream, response, sizeof(response), 0);
    check(
        hookedStreamReceived == 4 && std::string(response, 4) == "pong",
        "receive through hooked stream");
    closesocket(hookedStream);

    auto datagram = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    u_long nonblocking = 1;
    check(
        ioctlsocket(datagram, FIONBIO, &nonblocking) == 0,
        "configure fixture datagram as nonblocking");
    sockaddr_in privateBinding{};
    privateBinding.sin_family = AF_INET;
    privateBinding.sin_addr.s_addr = htonl(0x0A010203u);
    check(
        bind(
            datagram,
            reinterpret_cast<const sockaddr *>(&privateBinding),
            sizeof(privateBinding)) == 0,
        "hook bind redirects private address");
    sockaddr_in effectiveBinding{};
    int effectiveBindingSize = sizeof(effectiveBinding);
    check(
        getsockname(
            datagram,
            reinterpret_cast<sockaddr *>(&effectiveBinding),
            &effectiveBindingSize) == 0 &&
            effectiveBinding.sin_addr.s_addr == htonl(INADDR_LOOPBACK),
        "private bind resolves to loopback");
    check(
        sendto(
            datagram,
            "ping",
            4,
            0,
            reinterpret_cast<const sockaddr *>(&proxyTarget),
            sizeof(proxyTarget)) == 4,
        "hook sendto creates datagram bridge");
    sockaddr_in packetSource{};
    int packetSourceSize = sizeof(packetSource);
    std::memset(response, 0, sizeof(response));
    int packetReceived = SOCKET_ERROR;
    for (int attempt = 0; attempt != 200 && packetReceived == SOCKET_ERROR; ++attempt)
    {
        packetReceived = recvfrom(
            datagram,
            response,
            sizeof(response),
            0,
            reinterpret_cast<sockaddr *>(&packetSource),
            &packetSourceSize);
        if (packetReceived == SOCKET_ERROR)
            Sleep(5);
    }
    check(
        packetReceived == 4 && std::string(response, 4) == "pong",
        "hook recvfrom reads datagram bridge response");
    check(
        packetSource.sin_addr.s_addr == proxyAddress &&
            packetSource.sin_port == proxyTarget.sin_port,
        "recvfrom restores synthetic server endpoint");
    closesocket(datagram);

    auto literalReceiver = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    sockaddr_in literalAddress{};
    literalAddress.sin_family = AF_INET;
    literalAddress.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    check(
        bind(
            literalReceiver,
            reinterpret_cast<const sockaddr *>(&literalAddress),
            sizeof(literalAddress)) == 0,
        "bind literal loopback receiver");
    int literalAddressSize = sizeof(literalAddress);
    check(
        getsockname(
            literalReceiver,
            reinterpret_cast<sockaddr *>(&literalAddress),
            &literalAddressSize) == 0,
        "resolve literal loopback receiver port");
    auto literalSender = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    check(
        sendto(
            literalSender,
            "literal",
            7,
            0,
            reinterpret_cast<const sockaddr *>(&literalAddress),
            sizeof(literalAddress)) == 7,
        "hook sendto preserves literal loopback UDP");
    setsockopt(
        literalReceiver,
        SOL_SOCKET,
        SO_RCVTIMEO,
        reinterpret_cast<const char *>(&receiveTimeout),
        sizeof(receiveTimeout));
    std::memset(response, 0, sizeof(response));
    check(
        recv(literalReceiver, response, sizeof(response), 0) == 7 &&
            std::string(response, 7) == "literal",
        "literal loopback UDP reaches its native socket");
    closesocket(literalSender);
    closesocket(literalReceiver);

    if (Failures)
        return 1;
    std::cout << "Localnetworking runtime tests passed.\n";
    return 0;
}
