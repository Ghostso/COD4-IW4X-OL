#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <WinSock2.h>
#include <Windows.h>

#include "Localnetworking.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <deque>
#include <fstream>
#include <mutex>
#include <thread>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace
{
    HMODULE ModuleHandle{};

    bool setNonblocking(const SOCKET socket)
    {
        u_long enabled = 1;
        return ioctlsocket(socket, FIONBIO, &enabled) == 0;
    }

    void closeSocket(SOCKET &socket)
    {
        if (socket == INVALID_SOCKET)
            return;
        closesocket(socket);
        socket = INVALID_SOCKET;
    }

    SOCKET createListener(const std::uint16_t port)
    {
        auto socket = ::socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (socket == INVALID_SOCKET)
            return INVALID_SOCKET;

        sockaddr_in address{};
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        address.sin_port = htons(port);
        if (::bind(socket, reinterpret_cast<const sockaddr *>(&address), sizeof(address)) != 0 ||
            listen(socket, 16) != 0)
        {
            closeSocket(socket);
            return INVALID_SOCKET;
        }
        setNonblocking(socket);
        return socket;
    }

    std::string winsockError(const std::string_view operation)
    {
        return std::string(operation) + " failed with Winsock error " +
            std::to_string(WSAGetLastError()) + '.';
    }
}

namespace OlMod::Localnetworking
{
    struct Bridge::State
    {
        struct Connection
        {
            IServer *server{};
            bool packet{};
            IServer::Endpoints endpoints{};
            std::deque<std::vector<char>> outbound;
            std::size_t outboundOffset{};
        };

        struct ConnectionView
        {
            SOCKET socket{INVALID_SOCKET};
            IServer *server{};
            bool packet{};
            IServer::Endpoints endpoints{};
        };

        std::mutex mutex;
        std::mutex logMutex;
        std::atomic_bool running{};
        bool started{};
        RuntimePaths paths;
        std::filesystem::path logPath;
        std::uint16_t port{};
        SOCKET streamListener{INVALID_SOCKET};
        SOCKET datagramListener{INVALID_SOCKET};
        std::vector<HMODULE> plugins;
        std::unordered_map<std::string, IServer *> resolvedHosts;
        std::unordered_set<std::string> rejectedHosts;
        std::unordered_map<std::uint16_t, std::string> pendingStreamPorts;
        std::unordered_map<SOCKET, Connection> connections;

        void poll()
        {
            std::array<char, 8192> buffer{};
            while (running.load())
            {
                fd_set readable{};
                fd_set writable{};
                FD_ZERO(&readable);
                FD_ZERO(&writable);
                std::vector<ConnectionView> snapshot;
                {
                    std::lock_guard lock(mutex);
                    FD_SET(streamListener, &readable);
                    snapshot.reserve(connections.size());
                    for (const auto &[socket, connection] : connections)
                    {
                        if (readable.fd_count >= FD_SETSIZE)
                            break;
                        FD_SET(socket, &readable);
                        if (!connection.outbound.empty())
                            FD_SET(socket, &writable);
                        snapshot.push_back(ConnectionView{
                            socket,
                            connection.server,
                            connection.packet,
                            connection.endpoints,
                        });
                    }
                }

                timeval timeout{};
                timeout.tv_usec = 10000;
                const auto selected = select(0, &readable, &writable, nullptr, &timeout);
                if (selected == SOCKET_ERROR)
                    continue;

                if (selected > 0 && FD_ISSET(streamListener, &readable))
                {
                    sockaddr_in peer{};
                    int peerSize = sizeof(peer);
                    auto accepted = accept(
                        streamListener,
                        reinterpret_cast<sockaddr *>(&peer),
                        &peerSize);
                    if (accepted != INVALID_SOCKET)
                    {
                        setNonblocking(accepted);
                        IServer *server{};
                        {
                            std::lock_guard lock(mutex);
                            const auto pending = pendingStreamPorts.find(peer.sin_port);
                            if (pending != pendingStreamPorts.end())
                            {
                                const auto resolved = resolvedHosts.find(pending->second);
                                if (resolved != resolvedHosts.end())
                                    server = resolved->second;
                                pendingStreamPorts.erase(pending);
                            }
                            if (server)
                                connections.emplace(accepted, Connection{server});
                        }
                        if (server)
                            server->onConnect();
                        else
                            closeSocket(accepted);
                    }
                }

                if (selected > 0)
                {
                    for (const auto &connection : snapshot)
                    {
                        if (!FD_ISSET(connection.socket, &readable))
                            continue;
                        const auto size = recv(
                            connection.socket,
                            buffer.data(),
                            static_cast<int>(buffer.size()),
                            0);
                        if (size > 0)
                        {
                            if (connection.packet)
                            {
                                connection.server->onPacketwrite(
                                    buffer.data(),
                                    static_cast<std::uint32_t>(size),
                                    &connection.endpoints);
                            }
                            else
                            {
                                connection.server->onStreamwrite(
                                    buffer.data(),
                                    static_cast<std::uint32_t>(size));
                            }
                            continue;
                        }

                        if (size == SOCKET_ERROR && WSAGetLastError() == WSAEWOULDBLOCK)
                            continue;
                        {
                            std::lock_guard lock(mutex);
                            connections.erase(connection.socket);
                        }
                        auto closed = connection.socket;
                        closeSocket(closed);
                        connection.server->onDisconnect();
                    }
                }

                if (selected > 0)
                {
                    for (const auto &view : snapshot)
                    {
                        if (!FD_ISSET(view.socket, &writable))
                            continue;

                        IServer *disconnected{};
                        {
                            std::lock_guard lock(mutex);
                            const auto found = connections.find(view.socket);
                            if (found == connections.end())
                                continue;
                            auto &connection = found->second;
                            while (!connection.outbound.empty())
                            {
                                const auto &front = connection.outbound.front();
                                const auto remaining = front.size() - connection.outboundOffset;
                                const auto sent = send(
                                    view.socket,
                                    front.data() + connection.outboundOffset,
                                    static_cast<int>(remaining),
                                    0);
                                if (sent > 0)
                                {
                                    connection.outboundOffset += static_cast<std::size_t>(sent);
                                    if (connection.outboundOffset == front.size())
                                    {
                                        connection.outbound.pop_front();
                                        connection.outboundOffset = 0;
                                    }
                                    continue;
                                }
                                if (sent == SOCKET_ERROR && WSAGetLastError() == WSAEWOULDBLOCK)
                                    break;
                                disconnected = connection.server;
                                connections.erase(found);
                                break;
                            }
                        }
                        if (disconnected)
                        {
                            auto closed = view.socket;
                            closeSocket(closed);
                            disconnected->onDisconnect();
                        }
                    }
                }

                {
                    std::lock_guard lock(mutex);
                    snapshot.clear();
                    snapshot.reserve(connections.size());
                    for (const auto &[socket, connection] : connections)
                    {
                        snapshot.push_back(ConnectionView{
                            socket,
                            connection.server,
                            connection.packet,
                            connection.endpoints,
                        });
                    }
                }

                std::vector<std::pair<IServer *, bool>> polled;
                for (const auto &connection : snapshot)
                {
                    const auto route = std::pair{connection.server, connection.packet};
                    if (std::find(polled.begin(), polled.end(), route) != polled.end())
                        continue;
                    polled.push_back(route);

                    std::uint32_t size = static_cast<std::uint32_t>(buffer.size());
                    const auto ready = connection.packet
                        ? connection.server->onPacketread(buffer.data(), &size)
                        : connection.server->onStreamread(buffer.data(), &size);
                    if (!ready || size == 0 || size > buffer.size())
                        continue;

                    std::lock_guard lock(mutex);
                    for (auto &[_, target] : connections)
                    {
                        if (target.server == connection.server && target.packet == connection.packet)
                            target.outbound.emplace_back(buffer.begin(), buffer.begin() + size);
                    }
                }
            }
        }
    };

    std::uint32_t fnv1a32(const std::string_view value)
    {
        std::uint32_t hash = 0x811C9DC5u;
        for (const auto character : value)
        {
            hash ^= static_cast<std::uint8_t>(character);
            hash *= 0x01000193u;
        }
        return hash;
    }

    std::uint32_t syntheticIpv4(const std::string_view hostname)
    {
        return htonl(0xF0000000u | (fnv1a32(hostname) >> 8));
    }

    Bridge &Bridge::instance()
    {
        static auto *state = new State();
        static Bridge bridge;
        bridge.state_ = state;
        return bridge;
    }

    bool Bridge::start(const RuntimePaths &paths, const std::uint16_t firstPort)
    {
        std::lock_guard lock(state_->mutex);
        if (state_->started)
            return true;

        state_->paths = paths;
        state_->logPath = paths.logs / L"Localnetworking.log";
        std::error_code error;
        std::filesystem::remove(state_->logPath, error);

        WSADATA winsock{};
        if (WSAStartup(MAKEWORD(2, 2), &winsock) != 0)
        {
            log("WSAStartup failed.");
            return false;
        }

        state_->datagramListener = createListener(0);
        if (state_->datagramListener == INVALID_SOCKET)
        {
            log(winsockError("Creating the datagram bridge listener"));
            return false;
        }

        for (std::uint16_t offset = 0; offset != 64; ++offset)
        {
            state_->streamListener = createListener(
                static_cast<std::uint16_t>(firstPort + offset));
            if (state_->streamListener != INVALID_SOCKET)
            {
                state_->port = static_cast<std::uint16_t>(firstPort + offset);
                break;
            }
        }
        if (state_->streamListener == INVALID_SOCKET)
        {
            closeSocket(state_->datagramListener);
            log("No Localnetworking backend port was available in the configured range.");
            return false;
        }

        for (const auto &entry : std::filesystem::directory_iterator(paths.plugins, error))
        {
            if (error || !entry.is_regular_file(error) ||
                !isLocalnetPluginFilename(entry.path().filename().wstring()))
            {
                continue;
            }
            if (const auto module = LoadLibraryW(entry.path().c_str()))
            {
                state_->plugins.push_back(module);
                log("Loaded Localnet32 plugin " + entry.path().filename().string() + '.');
            }
        }

        state_->started = true;
        state_->running = true;
        log("Localnetworking backend listening on 127.0.0.1:" +
            std::to_string(state_->port) + '.');
        std::thread([state = state_] { state->poll(); }).detach();
        return true;
    }

    bool Bridge::claimsHost(const std::string_view hostname)
    {
        if (hostname.empty())
            return false;
        const std::string key(hostname);
        std::lock_guard lock(state_->mutex);
        if (state_->resolvedHosts.contains(key))
            return true;
        if (state_->rejectedHosts.contains(key))
            return false;

        using CreateServer = IServer *(__cdecl *)(const char *);
        for (const auto module : state_->plugins)
        {
            const auto callback = reinterpret_cast<CreateServer>(
                GetProcAddress(module, "Createserver"));
            if (!callback)
                continue;
            if (auto *server = callback(key.c_str()))
            {
                state_->resolvedHosts.emplace(key, server);
                return true;
            }
        }
        state_->rejectedHosts.emplace(key);
        return false;
    }

    void Bridge::associatePort(
        const std::string_view hostname,
        const std::uint16_t networkPort)
    {
        std::lock_guard lock(state_->mutex);
        state_->pendingStreamPorts[networkPort] = std::string(hostname);
    }

    SOCKET Bridge::createDatagramSocket(
        const IServer::Address &clientAddress,
        const IServer::Address &serverAddress,
        const std::string_view hostname)
    {
        IServer *server{};
        sockaddr_in listener{};
        int listenerSize = sizeof(listener);
        {
            std::lock_guard lock(state_->mutex);
            const auto resolved = state_->resolvedHosts.find(std::string(hostname));
            if (resolved == state_->resolvedHosts.end())
                return INVALID_SOCKET;
            server = resolved->second;
            if (getsockname(
                    state_->datagramListener,
                    reinterpret_cast<sockaddr *>(&listener),
                    &listenerSize) != 0)
            {
                return INVALID_SOCKET;
            }
        }

        auto client = ::socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (client == INVALID_SOCKET)
            return INVALID_SOCKET;
        setNonblocking(client);

        sockaddr_in local{};
        local.sin_family = AF_INET;
        local.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        if (::bind(client, reinterpret_cast<const sockaddr *>(&local), sizeof(local)) != 0)
        {
            closeSocket(client);
            return INVALID_SOCKET;
        }

        const auto connected = connect(
            client,
            reinterpret_cast<const sockaddr *>(&listener),
            sizeof(listener));
        if (connected == SOCKET_ERROR)
        {
            const auto code = WSAGetLastError();
            if (code != WSAEWOULDBLOCK && code != WSAEINPROGRESS && code != WSAEINVAL)
            {
                closeSocket(client);
                return INVALID_SOCKET;
            }
        }

        fd_set readable{};
        FD_ZERO(&readable);
        FD_SET(state_->datagramListener, &readable);
        timeval timeout{};
        timeout.tv_sec = 1;
        if (select(0, &readable, nullptr, nullptr, &timeout) <= 0)
        {
            closeSocket(client);
            return INVALID_SOCKET;
        }

        sockaddr_in peer{};
        int peerSize = sizeof(peer);
        auto accepted = accept(
            state_->datagramListener,
            reinterpret_cast<sockaddr *>(&peer),
            &peerSize);
        if (accepted == INVALID_SOCKET)
        {
            closeSocket(client);
            return INVALID_SOCKET;
        }
        setNonblocking(accepted);

        {
            std::lock_guard lock(state_->mutex);
            state_->connections.emplace(
                accepted,
                State::Connection{
                    server,
                    true,
                    IServer::Endpoints{clientAddress, serverAddress},
                });
        }
        return client;
    }

    std::uint16_t Bridge::backendPort() const
    {
        std::lock_guard lock(state_->mutex);
        return state_->port;
    }

    void Bridge::log(const std::string_view message)
    {
        std::lock_guard lock(state_->logMutex);
        if (state_->logPath.empty())
            return;
        std::ofstream stream(state_->logPath, std::ios::app);
        if (stream)
            stream << message << '\n';
    }

    void setModuleHandle(const HMODULE module)
    {
        ModuleHandle = module;
    }

    std::optional<RuntimePaths> currentRuntimePaths()
    {
        if (!ModuleHandle)
            return std::nullopt;
        std::wstring path(32768, L'\0');
        const auto size = GetModuleFileNameW(
            ModuleHandle,
            path.data(),
            static_cast<DWORD>(path.size()));
        if (!size || size >= path.size())
            return std::nullopt;
        path.resize(size);
        return runtimePathsFromModule(path);
    }
}
