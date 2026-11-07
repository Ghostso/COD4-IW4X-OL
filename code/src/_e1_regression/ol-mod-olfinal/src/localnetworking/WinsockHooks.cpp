#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <WinSock2.h>
#include <Windows.h>
#include <Ws2tcpip.h>
#include <mhook-lib/mhook.h>

#include "Localnetworking.hpp"

#include <algorithm>
#include <array>
#include <cstring>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

namespace
{
    using Connect = int(WSAAPI *)(SOCKET, const sockaddr *, int);
    using Bind = int(WSAAPI *)(SOCKET, const sockaddr *, int);
    using SendTo = int(WSAAPI *)(SOCKET, const char *, int, int, const sockaddr *, int);
    using ReceiveFrom = int(WSAAPI *)(SOCKET, char *, int, int, sockaddr *, int *);
    using GetHostByName = hostent *(WSAAPI *)(const char *);
    using GetAddressInfo = INT(WSAAPI *)(PCSTR, PCSTR, const ADDRINFOA *, PADDRINFOA *);

    Connect OriginalConnect{};
    Bind OriginalBind{};
    SendTo OriginalSendTo{};
    ReceiveFrom OriginalReceiveFrom{};
    GetHostByName OriginalGetHostByName{};
    GetAddressInfo OriginalGetAddressInfo{};

    std::mutex FrontendMutex;
    std::unordered_map<std::uint32_t, std::string> ProxyAddresses;
    std::unordered_map<SOCKET, IServer::Endpoints> DatagramSockets;
    std::unordered_map<SOCKET, IServer::Address> Bindings;
    std::unordered_map<SOCKET, std::uint32_t> DatagramSendDiagnostics;
    std::unordered_map<SOCKET, std::uint32_t> TargetSendDiagnostics;
    std::unordered_map<SOCKET, std::uint32_t> ConnectDiagnostics;
    std::unordered_map<SOCKET, std::uint32_t> ReceiveDiagnostics;
    std::unordered_map<SOCKET, std::uint32_t> GameReceiveDiagnostics;
    std::unordered_map<SOCKET, std::uint32_t> HandshakeDiagnostics;

    std::string handshakePrefix(const char *buffer, const int length)
    {
        std::string text;
        const auto count = std::min(length, 16);
        for (int index = 0; index < count; ++index)
        {
            if (!text.empty())
                text += ':';
            char value[4]{};
            sprintf_s(value, "%02X", static_cast<unsigned char>(buffer[index]));
            text += value;
        }
        return text;
    }

    std::string processTag()
    {
        char instance[32]{};
        const auto size = GetEnvironmentVariableA("OLMOD_CLIENT_INSTANCE", instance,
            static_cast<DWORD>(sizeof(instance)));
        return "pid=" + std::to_string(GetCurrentProcessId()) +
            " instance=" + (size ? std::string(instance, size) : "?");
    }

    bool isDedicatedProcess()
    {
        char role[32]{};
        const auto size = GetEnvironmentVariableA("OLMOD_PROCESS_ROLE", role,
            static_cast<DWORD>(sizeof(role)));
        return size && _stricmp(role, "dedicated") == 0;
    }

    struct InstalledHook
    {
        void *trampoline{};
        void **canonicalOriginal{};
    };

    bool equalAddress(const IServer::Address &left, const IServer::Address &right)
    {
        return left.ipv4 == right.ipv4 && left.port == right.port;
    }

    std::string addressText(const sockaddr *address)
    {
        if (!address)
            return {};
        std::array<char, INET6_ADDRSTRLEN> buffer{};
        if (address->sa_family == AF_INET)
        {
            const auto *ipv4 = reinterpret_cast<const sockaddr_in *>(address);
            if (inet_ntop(AF_INET, &ipv4->sin_addr, buffer.data(), buffer.size()))
                return buffer.data();
        }
        else if (address->sa_family == AF_INET6)
        {
            const auto *ipv6 = reinterpret_cast<const sockaddr_in6 *>(address);
            if (inet_ntop(AF_INET6, &ipv6->sin6_addr, buffer.data(), buffer.size()))
                return buffer.data();
        }
        return {};
    }

    IServer::Address socketAddress(const SOCKET socket)
    {
        sockaddr_in address{};
        int size = sizeof(address);
        if (getsockname(socket, reinterpret_cast<sockaddr *>(&address), &size) != 0)
            return {};
        return IServer::Address{address.sin_addr.s_addr, address.sin_port};
    }

    std::uint16_t ensureSocketPort(const SOCKET socket)
    {
        auto current = socketAddress(socket);
        if (current.port)
            return current.port;

        sockaddr_in local{};
        local.sin_family = AF_INET;
        local.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        if (OriginalBind(
                socket,
                reinterpret_cast<const sockaddr *>(&local),
                sizeof(local)) != 0)
        {
            return 0;
        }
        return socketAddress(socket).port;
    }

    std::string hostnameForAddress(const sockaddr *address)
    {
        if (!address || address->sa_family != AF_INET)
            return addressText(address);
        const auto ipv4 = reinterpret_cast<const sockaddr_in *>(address)->sin_addr.s_addr;
        std::lock_guard lock(FrontendMutex);
        if (const auto found = ProxyAddresses.find(ipv4); found != ProxyAddresses.end())
            return found->second;
        return addressText(address);
    }

    int WSAAPI connectHook(
        const SOCKET socket,
        const sockaddr *name,
        const int nameLength)
    {
        if (isDedicatedProcess())
            return OriginalConnect(socket, name, nameLength);
        if (name && name->sa_family == AF_INET)
        {
            std::lock_guard lock(FrontendMutex);
            auto &count = ConnectDiagnostics[socket];
            if (count++ < 8)
            {
                const auto *target = reinterpret_cast<const sockaddr_in *>(name);
                OlMod::Localnetworking::Bridge::instance().log(
                    "connect-target " + processTag() +
                    " target=" + addressText(name) +
                    " port=" + std::to_string(ntohs(target->sin_port)) +
                    " localPort=" + std::to_string(ntohs(socketAddress(socket).port)));
            }
        }
        const auto hostname = hostnameForAddress(name);
        const auto proxied = OlMod::Localnetworking::Bridge::instance().claimsHost(hostname);
        sockaddr_in local{};
        if (proxied)
        {
            const auto port = ensureSocketPort(socket);
            if (!port)
                return SOCKET_ERROR;
            OlMod::Localnetworking::Bridge::instance().associatePort(hostname, port);
            local.sin_family = AF_INET;
            local.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
            local.sin_port = htons(
                OlMod::Localnetworking::Bridge::instance().backendPort());
            name = reinterpret_cast<const sockaddr *>(&local);
            OlMod::Localnetworking::Bridge::instance().log(
                "connect " + processTag() + " host=" + hostname +
                " localPort=" + std::to_string(ntohs(port)));
        }

        const auto result = OriginalConnect(
            socket,
            name,
            proxied ? static_cast<int>(sizeof(local)) : nameLength);
        const auto error = WSAGetLastError();
        if (proxied && result == SOCKET_ERROR)
            return 0;
        WSASetLastError(error);
        return result;
    }

    bool shouldRedirectBind(const sockaddr_in &address)
    {
        const auto host = ntohl(address.sin_addr.s_addr);
        return (host & 0xFF000000u) == 0x0A000000u ||
            (host & 0xFFFF0000u) == 0xC0A80000u;
    }

    int WSAAPI bindHook(
        const SOCKET socket,
        const sockaddr *name,
        const int nameLength)
    {
        if (isDedicatedProcess())
            return OriginalBind(socket, name, nameLength);
        sockaddr_in local{};
        if (name && name->sa_family == AF_INET)
        {
            local = *reinterpret_cast<const sockaddr_in *>(name);
            if (shouldRedirectBind(local))
            {
                local.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
                name = reinterpret_cast<const sockaddr *>(&local);
            }
        }

        const auto result = OriginalBind(socket, name, nameLength);
        if (result == 0)
        {
            std::lock_guard lock(FrontendMutex);
            Bindings[socket] = socketAddress(socket);
        }
        return result;
    }

    int WSAAPI sendToHook(
        const SOCKET socket,
        const char *buffer,
        const int length,
        const int flags,
        const sockaddr *to,
        const int toLength)
    {
        if (isDedicatedProcess())
            return OriginalSendTo(socket, buffer, length, flags, to, toLength);
        if (!to || to->sa_family != AF_INET)
            return OriginalSendTo(socket, buffer, length, flags, to, toLength);

        const auto *target = reinterpret_cast<const sockaddr_in *>(to);
        {
            std::lock_guard lock(FrontendMutex);
            auto &count = TargetSendDiagnostics[socket];
            if (count++ < 8)
            {
                OlMod::Localnetworking::Bridge::instance().log(
                    "sendto-target " + processTag() +
                    " target=" + addressText(to) +
                    " port=" + std::to_string(ntohs(target->sin_port)) +
                    " bytes=" + std::to_string(length) +
                    " clientPort=" + std::to_string(ntohs(socketAddress(socket).port)));
            }
        }
        std::string hostname;
        {
            std::lock_guard lock(FrontendMutex);
            const auto proxy = ProxyAddresses.find(target->sin_addr.s_addr);
            if (proxy != ProxyAddresses.end())
                hostname = proxy->second;
        }
        if (hostname.empty())
        {
            // The game-server endpoint is returned as a literal loopback
            // address, so it does not pass synthetic-host resolution. The
            // recovered bdCommonAddr stores ports little-endian; logging
            // every loopback port here lets us distinguish a client-side
            // byte-order decode failure (for example 28960 -> 8305)
            // without changing the send path.
            if (ntohl(target->sin_addr.s_addr) == 0x7F000001u)
            {
                static std::unordered_map<SOCKET, std::uint32_t> directCounts;
                const auto result = OriginalSendTo(socket, buffer, length, flags, to, toLength);
                const auto error = result == SOCKET_ERROR ? WSAGetLastError() : 0;
                bool emit{};
                {
                    std::lock_guard countLock(FrontendMutex);
                    emit = directCounts[socket]++ < 3;
                }
                if (emit)
                    OlMod::Localnetworking::Bridge::instance().log(
                        "sendto-direct " + processTag() +
                        " target=" + addressText(to) +
                        " bytes=" + std::to_string(length) +
                        " clientPort=" + std::to_string(ntohs(socketAddress(socket).port)) +
                        " serverPort=" + std::to_string(ntohs(target->sin_port)) +
                        " result=" + std::to_string(result) +
                        " error=" + std::to_string(error));
                if (length > 1 && (static_cast<unsigned char>(buffer[0]) == 0x03 ||
                    static_cast<unsigned char>(buffer[0]) == 0x01))
                {
                    std::lock_guard countLock(FrontendMutex);
                    if (HandshakeDiagnostics[socket]++ < 8)
                        OlMod::Localnetworking::Bridge::instance().log(
                            "dtls-send " + processTag() +
                            " type=" + std::to_string(static_cast<unsigned char>(buffer[0])) +
                            " bytes=" + std::to_string(length) +
                            " prefix=" + handshakePrefix(buffer, length));
                }
                WSASetLastError(error);
                return result;
            }
            return OriginalSendTo(socket, buffer, length, flags, to, toLength);
        }

        const IServer::Address serverAddress{
            target->sin_addr.s_addr,
            target->sin_port,
        };
        auto clientAddress = socketAddress(socket);
        SOCKET bridgeSocket = INVALID_SOCKET;
        {
            std::lock_guard lock(FrontendMutex);
            for (auto &[candidate, endpoints] : DatagramSockets)
            {
                // A dedicated endpoint is shared by all game clients.  The
                // local UDP endpoint is therefore part of the route key;
                // matching only the server address merges clients into one
                // bridge and silently drops the second connection.
                if (!equalAddress(serverAddress, endpoints.server) ||
                    !equalAddress(clientAddress, endpoints.client))
                    continue;
                bridgeSocket = candidate;
                break;
            }
        }

        if (bridgeSocket == INVALID_SOCKET)
        {
            bridgeSocket = OlMod::Localnetworking::Bridge::instance().createDatagramSocket(
                clientAddress,
                serverAddress,
                hostname);
            if (bridgeSocket == INVALID_SOCKET)
                return SOCKET_ERROR;
            std::lock_guard lock(FrontendMutex);
            DatagramSockets.emplace(
                bridgeSocket,
                IServer::Endpoints{clientAddress, serverAddress});
            OlMod::Localnetworking::Bridge::instance().log(
                "datagram-route-created " + processTag() + " host=" + hostname +
                " clientPort=" + std::to_string(ntohs(clientAddress.port)) +
                " serverPort=" + std::to_string(ntohs(serverAddress.port)));
        }
        bool emitDiagnostic{};
        {
            std::lock_guard lock(FrontendMutex);
            emitDiagnostic = DatagramSendDiagnostics[socket]++ < 3;
        }
        if (emitDiagnostic)
            OlMod::Localnetworking::Bridge::instance().log(
                "sendto " + processTag() + " host=" + hostname +
                " bytes=" + std::to_string(length) +
                " clientPort=" + std::to_string(ntohs(clientAddress.port)) +
                " serverPort=" + std::to_string(ntohs(serverAddress.port)));
        // TODO(localnet-framing): The archived bridge maps UDP writes directly
        // onto TCP. Add framing only after CODOL burst traces define the
        // compatibility boundary.
        return send(bridgeSocket, buffer, length, 0);
    }

    int WSAAPI receiveFromHook(
        const SOCKET socket,
        char *buffer,
        const int length,
        const int flags,
        sockaddr *from,
        int *fromLength)
    {
        if (isDedicatedProcess())
            return OriginalReceiveFrom(socket, buffer, length, flags, from, fromLength);
        std::vector<std::pair<SOCKET, IServer::Endpoints>> routes;
        IServer::Address binding{};
        {
            std::lock_guard lock(FrontendMutex);
            routes.assign(DatagramSockets.begin(), DatagramSockets.end());
            if (const auto found = Bindings.find(socket); found != Bindings.end())
                binding = found->second;
            else
                binding = socketAddress(socket);
        }

        fd_set readable{};
        FD_ZERO(&readable);
        for (const auto &[candidate, _] : routes)
        {
            if (readable.fd_count >= FD_SETSIZE)
                break;
            FD_SET(candidate, &readable);
        }
        timeval timeout{};
        timeout.tv_usec = 1;
        if (readable.fd_count && select(0, &readable, nullptr, nullptr, &timeout) > 0)
        {
            for (const auto &[candidate, endpoints] : routes)
            {
                if (!FD_ISSET(candidate, &readable) ||
                    binding.port != endpoints.client.port ||
                    (binding.ipv4 && binding.ipv4 != endpoints.client.ipv4))
                {
                    continue;
                }
                if (from && fromLength && *fromLength >= static_cast<int>(sizeof(sockaddr_in)))
                {
                    sockaddr_in source{};
                    source.sin_family = AF_INET;
                    source.sin_addr.s_addr = endpoints.server.ipv4;
                    source.sin_port = endpoints.server.port;
                    std::memcpy(from, &source, sizeof(source));
                    *fromLength = sizeof(source);
                }
                const auto result = recv(candidate, buffer, length, 0);
                const auto error = result == SOCKET_ERROR ? WSAGetLastError() : 0;
                bool emit{};
                {
                    std::lock_guard lock(FrontendMutex);
                    emit = ReceiveDiagnostics[socket]++ < 8;
                }
                if (emit)
                {
                    const auto packetType = result > 0
                        ? static_cast<unsigned int>(static_cast<unsigned char>(buffer[0]))
                        : 0u;
                    OlMod::Localnetworking::Bridge::instance().log(
                        "recvfrom-route " + processTag() +
                        " source=" + std::to_string(ntohl(endpoints.server.ipv4)) +
                        " serverPort=" + std::to_string(ntohs(endpoints.server.port)) +
                        " clientPort=" + std::to_string(ntohs(binding.port)) +
                        " bytes=" + std::to_string(result) +
                        " type=" + std::to_string(packetType) +
                        " error=" + std::to_string(error));
                }
                WSASetLastError(error);
                return result;
            }
        }
        const auto result = OriginalReceiveFrom(socket, buffer, length, flags, from, fromLength);
        const auto error = result == SOCKET_ERROR ? WSAGetLastError() : 0;
        if (result > 0 && from && from->sa_family == AF_INET)
        {
            const auto *source = reinterpret_cast<const sockaddr_in *>(from);
            const auto packetType = static_cast<unsigned int>(
                static_cast<unsigned char>(buffer[0]));
            const auto loopbackGamePacket =
                ntohl(source->sin_addr.s_addr) == 0x7F000001u &&
                (packetType == 0x0C || packetType == 0x0D ||
                 packetType == 0x01 || packetType == 0x02 ||
                 packetType == 0x03 || packetType == 0x04 ||
                 packetType == 0x06);
            bool emit{};
            {
                std::lock_guard lock(FrontendMutex);
                emit = loopbackGamePacket
                    ? GameReceiveDiagnostics[socket]++ < 16
                    : ReceiveDiagnostics[socket]++ < 8;
            }
            if (emit)
            {
                OlMod::Localnetworking::Bridge::instance().log(
                    std::string(loopbackGamePacket
                        ? "recvfrom-game "
                        : "recvfrom-direct ") + processTag() +
                    " source=" + addressText(from) +
                    " serverPort=" + std::to_string(ntohs(source->sin_port)) +
                    " clientPort=" + std::to_string(ntohs(socketAddress(socket).port)) +
                    " bytes=" + std::to_string(result) +
                    " type=" + std::to_string(packetType));
            if (packetType == 0x02 || packetType == 0x04)
            {
                std::lock_guard countLock(FrontendMutex);
                if (HandshakeDiagnostics[socket]++ < 8)
                    OlMod::Localnetworking::Bridge::instance().log(
                        "dtls-recv " + processTag() +
                        " type=" + std::to_string(packetType) +
                        " bytes=" + std::to_string(result) +
                        " prefix=" + handshakePrefix(buffer, result));
            }
            }
        }
        WSASetLastError(error);
        return result;
    }

    hostent *WSAAPI getHostByNameHook(const char *hostname)
    {
        if (!hostname ||
            !OlMod::Localnetworking::Bridge::instance().claimsHost(hostname))
        {
            return OriginalGetHostByName(hostname);
        }

        auto *result = OriginalGetHostByName("localhost");
        if (!result || !result->h_addr_list || !result->h_addr_list[0])
            return result;
        thread_local std::string stableHostname;
        stableHostname = hostname;
        const auto address = OlMod::Localnetworking::syntheticIpv4(hostname);
        result->h_name = stableHostname.data();
        result->h_addrtype = AF_INET;
        result->h_length = sizeof(address);
        result->h_addr_list[1] = nullptr;
        if (result->h_aliases)
            result->h_aliases[0] = nullptr;
        std::memcpy(result->h_addr_list[0], &address, sizeof(address));
        {
            std::lock_guard lock(FrontendMutex);
            ProxyAddresses[address] = hostname;
        }
        return result;
    }

    INT WSAAPI getAddressInfoHook(
        const PCSTR nodeName,
        const PCSTR serviceName,
        const ADDRINFOA *hints,
        PADDRINFOA *result)
    {
        if (!nodeName ||
            !OlMod::Localnetworking::Bridge::instance().claimsHost(nodeName))
        {
            return OriginalGetAddressInfo(nodeName, serviceName, hints, result);
        }

        addrinfo proxyHints{};
        if (hints)
            proxyHints = *hints;
        proxyHints.ai_family = AF_INET;
        const auto code = OriginalGetAddressInfo("localhost", serviceName, &proxyHints, result);
        if (code != 0 || !result)
            return code;
        const auto address = OlMod::Localnetworking::syntheticIpv4(nodeName);
        for (auto *entry = *result; entry; entry = entry->ai_next)
        {
            if (entry->ai_family == AF_INET && entry->ai_addr)
                reinterpret_cast<sockaddr_in *>(entry->ai_addr)->sin_addr.s_addr = address;
        }
        {
            std::lock_guard lock(FrontendMutex);
            ProxyAddresses[address] = nodeName;
        }
        return code;
    }

    bool hookExport(
        const char *name,
        void *target,
        void **original,
        std::vector<InstalledHook> &installedHooks)
    {
        std::array<void *, 2> addresses{};
        const std::array<const char *, 2> modules{"ws2_32.dll", "wsock32.dll"};
        for (std::size_t index = 0; index != modules.size(); ++index)
        {
            const auto module = LoadLibraryA(modules[index]);
            addresses[index] = module ? reinterpret_cast<void *>(GetProcAddress(module, name)) : nullptr;
        }

        bool installed{};
        bool complete = true;
        for (std::size_t index = 0; index != addresses.size(); ++index)
        {
            if (!addresses[index] ||
                (index != 0 && addresses[index] == addresses[0]))
            {
                continue;
            }
            auto *trampoline = addresses[index];
            if (!Mhook_SetHook(&trampoline, target))
            {
                complete = false;
                continue;
            }
            const auto canonical = !*original || index == 0;
            installedHooks.push_back(InstalledHook{
                trampoline,
                canonical ? original : nullptr,
            });
            if (canonical)
                *original = trampoline;
            installed = true;
        }
        return installed && complete && *original;
    }
}

namespace OlMod::Localnetworking
{
    bool installWinsockHooks()
    {
        static std::mutex installMutex;
        static bool installed{};
        static bool rollbackFailed{};
        std::lock_guard lock(installMutex);
        if (installed)
            return true;
        if (rollbackFailed)
            return false;

        std::vector<InstalledHook> installedHooks;
        const auto install = [&](const char *name, void *target, void **original)
        {
            return hookExport(name, target, original, installedHooks);
        };
        const auto success =
            install("bind", reinterpret_cast<void *>(&bindHook),
                reinterpret_cast<void **>(&OriginalBind)) &&
            install("connect", reinterpret_cast<void *>(&connectHook),
                reinterpret_cast<void **>(&OriginalConnect)) &&
            install("recvfrom", reinterpret_cast<void *>(&receiveFromHook),
                reinterpret_cast<void **>(&OriginalReceiveFrom)) &&
            install("sendto", reinterpret_cast<void *>(&sendToHook),
                reinterpret_cast<void **>(&OriginalSendTo)) &&
            install("gethostbyname", reinterpret_cast<void *>(&getHostByNameHook),
                reinterpret_cast<void **>(&OriginalGetHostByName)) &&
            install("getaddrinfo", reinterpret_cast<void *>(&getAddressInfoHook),
                reinterpret_cast<void **>(&OriginalGetAddressInfo));
        if (success)
        {
            installed = true;
            return true;
        }

        bool rollbackComplete = true;
        for (auto iterator = installedHooks.rbegin(); iterator != installedHooks.rend(); ++iterator)
        {
            auto restored = iterator->trampoline;
            if (!Mhook_Unhook(&restored))
            {
                rollbackComplete = false;
                continue;
            }
            if (iterator->canonicalOriginal)
                *iterator->canonicalOriginal = restored;
        }
        rollbackFailed = !rollbackComplete;
        if (rollbackComplete)
        {
            OriginalConnect = nullptr;
            OriginalBind = nullptr;
            OriginalSendTo = nullptr;
            OriginalReceiveFrom = nullptr;
            OriginalGetHostByName = nullptr;
            OriginalGetAddressInfo = nullptr;
        }
        return false;
    }
}
