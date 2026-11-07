// Independent, offline verification of the transport lifecycle contract:
// loopback binding, start() idempotency, stop() state cleanup and rebinding.
//
// No game process and no injection are involved. Every case binds a real UDP
// socket on the loopback interface and an ephemeral port, so the production
// game port is never occupied or disturbed.

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <WinSock2.h>
#include <Windows.h>

#include "server_mp/sv_network_mp.hpp"
#include "win32/win_net.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

namespace
{
    using CodolGameServer::AnyIpv4Address;
    using CodolGameServer::NetPacketResult;
    using CodolGameServer::NetUdpSocket;
    using CodolGameServer::PeerAddress;
    using CodolGameServer::SocketAlreadyBoundError;
    using CodolGameServer::SvOutboundPacket;
    using CodolGameServer::SvUdpTransport;

    // INADDR_ANY is zero, and PeerAddress::ipv4 is host byte order.
    static_assert(AnyIpv4Address == 0, "INADDR_ANY must be zero in host byte order");

    constexpr std::uint32_t LoopbackIpv4 = 0x7F000001u;

    // --- P1 seam: redirect this module's closesocket import ------------------
    //
    // SIMULATED FAILURE. This rewrites the closesocket entry in THIS test
    // executable's own import address table for the duration of one call, so the
    // production close() failure branch runs against a controlled OS response.
    // It is NOT a genuine Windows closesocket failure, and no result from it may
    // be reported as one. win_net.cpp is the only closesocket caller in the tree,
    // so the window affects exactly that call.
    using CloseSocketFunction = int(WSAAPI *)(SOCKET);

    int InjectedCloseError = 0;

    int WSAAPI failingCloseSocket(SOCKET)
    {
        WSASetLastError(InjectedCloseError);
        return SOCKET_ERROR;
    }

    CloseSocketFunction *findCloseSocketIatSlot()
    {
        // Locate the slot by ADDRESS, not by import name: the loader fills every
        // IAT entry with the resolved function address, so the closesocket slot
        // is the ws2_32 entry whose value equals GetProcAddress's result. This
        // does not depend on the lookup-name table layout.
        const auto ws2 = GetModuleHandleW(L"ws2_32.dll");
        if (!ws2)
            return nullptr;
        const auto real = reinterpret_cast<CloseSocketFunction>(
            GetProcAddress(ws2, "closesocket"));
        if (!real)
            return nullptr;
        auto *const base = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
        if (!base)
            return nullptr;
        const auto *const dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(base);
        if (dos->e_magic != IMAGE_DOS_SIGNATURE)
            return nullptr;
        const auto *const nt =
            reinterpret_cast<const IMAGE_NT_HEADERS *>(base + dos->e_lfanew);
        if (nt->Signature != IMAGE_NT_SIGNATURE)
            return nullptr;
        const auto &imports =
            nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
        if (!imports.VirtualAddress || !imports.Size)
            return nullptr;
        for (auto *descriptor = reinterpret_cast<const IMAGE_IMPORT_DESCRIPTOR *>(
                 base + imports.VirtualAddress);
             descriptor->Name;
             ++descriptor)
        {
            const auto *const moduleName =
                reinterpret_cast<const char *>(base + descriptor->Name);
            if (_stricmp(moduleName, "ws2_32.dll") != 0)
                continue;
            auto *const iat = reinterpret_cast<IMAGE_THUNK_DATA *>(
                base + descriptor->FirstThunk);
            for (std::size_t index = 0; iat[index].u1.Function; ++index)
            {
                if (reinterpret_cast<CloseSocketFunction>(iat[index].u1.Function) == real)
                {
                    return reinterpret_cast<CloseSocketFunction *>(
                        &iat[index].u1.Function);
                }
            }
        }
        return nullptr;
    }

    class ScopedCloseSocketFailure
    {
    public:
        explicit ScopedCloseSocketFailure(const int injectedError)
        {
            InjectedCloseError = injectedError;
            slot_ = findCloseSocketIatSlot();
            if (!slot_)
                return;
            DWORD oldProtection{};
            if (!VirtualProtect(
                    slot_, sizeof(*slot_), PAGE_EXECUTE_READWRITE, &oldProtection))
            {
                slot_ = nullptr;
                return;
            }
            original_ = *slot_;
            *slot_ = &failingCloseSocket;
            VirtualProtect(slot_, sizeof(*slot_), oldProtection, &oldProtection);
        }

        ~ScopedCloseSocketFailure() { restore(); }

        ScopedCloseSocketFailure(const ScopedCloseSocketFailure &) = delete;
        ScopedCloseSocketFailure &operator=(const ScopedCloseSocketFailure &) = delete;

        [[nodiscard]] bool active() const { return slot_ != nullptr; }

        void restore()
        {
            if (!slot_)
                return;
            DWORD oldProtection{};
            if (VirtualProtect(
                    slot_, sizeof(*slot_), PAGE_EXECUTE_READWRITE, &oldProtection))
            {
                *slot_ = original_;
                VirtualProtect(slot_, sizeof(*slot_), oldProtection, &oldProtection);
            }
            slot_ = nullptr;
        }

    private:
        CloseSocketFunction *slot_{};
        CloseSocketFunction original_{};
    };

    // --- A6: read the game-server channel log ---------------------------------
    //
    // RuntimeLog::logPath() places the channel file next to the executable, and
    // RuntimeLog::write() appends it with a direct WriteFile (nothing is buffered
    // in user space), so the bytes are on disk by the time stop() returns.
    std::filesystem::path gameServerLogPath()
    {
        std::array<wchar_t, 32768> modulePath{};
        const auto length = GetModuleFileNameW(
            nullptr, modulePath.data(), static_cast<DWORD>(modulePath.size()));
        if (!length || length >= modulePath.size())
            return {};
        return std::filesystem::path(modulePath.data()).parent_path() /
            L"Ayria" / L"Logs" / L"CodolGameServer.log";
    }

    std::uintmax_t logFileSizeOrZero(const std::filesystem::path &path)
    {
        std::error_code error;
        const auto size = std::filesystem::file_size(path, error);
        return error ? 0 : size;
    }

    std::string readAppendedBytes(
        const std::filesystem::path &path,
        const std::uintmax_t offset)
    {
        std::ifstream input(path, std::ios::binary);
        if (!input)
            return {};
        input.seekg(static_cast<std::streamoff>(offset), std::ios::beg);
        return std::string(
            std::istreambuf_iterator<char>(input),
            std::istreambuf_iterator<char>());
    }

    int Checks{};
    int Failures{};

    void require(const bool condition, const char *const message)
    {
        ++Checks;
        if (condition)
        {
            std::cout << "  ok   " << message << '\n';
            return;
        }
        ++Failures;
        std::cout << "  FAIL " << message << '\n';
    }

    std::uint16_t differentPort(const std::uint16_t port)
    {
        return static_cast<std::uint16_t>(port == 65535 ? port - 1 : port + 1);
    }

    void testLoopbackEphemeralBinding()
    {
        std::cout << "[1/8] loopback ephemeral bind\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "start(0, 127.0.0.1) succeeds");
        const auto status = transport.status();
        require(status.bound, "bound is set");
        require(status.port != 0, "an ephemeral port was assigned");
        transport.stop();
    }

    void testRepeatedStartKeepsBinding()
    {
        std::cout << "[2/8] repeated start(0) is idempotent\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "first start(0) succeeds");
        const auto first = transport.status();
        require(first.port != 0, "the first bind assigned an ephemeral port");

        // E-1: drive the real send path so the counter under test is non-zero.
        // A datagram addressed to the transport's own loopback port is a legal
        // local send; it needs no peer, no client and no public network.
        const std::array<SvOutboundPacket, 1> outbound{ {
            SvOutboundPacket{
                .peer = { LoopbackIpv4, first.port },
                .data = { 0x01, 0x02, 0x03, 0x04 } },
        } };
        transport.NET_SendPackets(outbound, 1000);
        const auto beforeRestart = transport.status();
        require(beforeRestart.packetsSent > 0, "the send path makes packetsSent non-zero");
        require(beforeRestart.packetsReceived == 0, "the send path leaves packetsReceived alone");

        require(transport.start(0, LoopbackIpv4), "second start(0) succeeds");
        const auto second = transport.status();
        require(second.port == first.port, "the bound port is unchanged");
        require(
            second.packetsSent == beforeRestart.packetsSent,
            "the non-zero send counter survives the repeated start");
        require(second.packetsReceived == 0, "the repeated start does not fabricate a receive count");

        // The repeated start must not have invalidated the socket: it still sends.
        transport.NET_SendPackets(outbound, 1001);
        const auto afterSecondSend = transport.status();
        require(
            afterSecondSend.packetsSent == beforeRestart.packetsSent + 1,
            "the socket still sends after the repeated start");
        require(afterSecondSend.bound, "the transport is still bound after the repeated start");
        std::cout << "       packetsSent=" << beforeRestart.packetsSent
                  << " after repeated start=" << second.packetsSent
                  << " after second send=" << afterSecondSend.packetsSent << '\n';
        transport.stop();
    }

    void testDifferentPortDoesNotDisturbBinding()
    {
        std::cout << "[3/8] a different explicit port cannot steal a live binding\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "start(0) succeeds");
        const auto bound = transport.status();
        require(!transport.start(differentPort(bound.port), LoopbackIpv4), "start(other) fails");
        const auto conflict = transport.status();
        require(conflict.bound, "the transport is still bound");
        require(conflict.port == bound.port, "the bound port is untouched");
        require(
            conflict.lastSocketError == SocketAlreadyBoundError,
            "the conflict is reported as SocketAlreadyBoundError");
        transport.stop();
    }

    void testStopClearsState()
    {
        std::cout << "[4/8] stop() clears the state\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "start(0) succeeds");
        transport.stop();
        const auto stopped = transport.status();
        require(!stopped.bound, "bound is cleared");
        require(stopped.port == 0, "port is cleared");
        require(
            stopped.packetsReceived == 0 && stopped.packetsSent == 0,
            "the counters are zeroed");
        require(
            stopped.lastPacketReceivedTime == 0 && stopped.lastPacketSentTime == 0,
            "the timestamps are zeroed");
    }

    void testRepeatedStop()
    {
        std::cout << "[5/8] repeated stop() is idempotent\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "start(0) succeeds");
        transport.stop();
        transport.stop();
        const auto stopped = transport.status();
        require(!stopped.bound && stopped.port == 0, "the second stop() leaves a clean state");
    }

    void testRebindAfterStop()
    {
        std::cout << "[6/8] rebinding after stop()\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "start(0) succeeds");
        transport.stop();
        require(transport.start(0, LoopbackIpv4), "start(0) after stop() succeeds");
        const auto rebound = transport.status();
        require(rebound.bound && rebound.port != 0, "the transport is bound again");
        require(
            rebound.packetsReceived == 0 && rebound.packetsSent == 0,
            "the counters restart at zero");
        require(rebound.lastSocketError == 0, "a successful start() clears the sticky error");
        transport.stop();
    }

    void testStickyErrorAcrossStop()
    {
        std::cout << "[7/8] stop() retains the sticky socket error\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "start(0) succeeds");
        const auto bound = transport.status();
        require(!transport.start(differentPort(bound.port), LoopbackIpv4), "start(other) fails");
        transport.stop();
        const auto stopped = transport.status();
        require(!stopped.bound && stopped.port == 0, "stop() cleared the binding");
        require(
            stopped.lastSocketError == SocketAlreadyBoundError,
            "the sticky error survives stop()");
    }

    void testOccupiedPortFails()
    {
        std::cout << "[8/8] an occupied loopback port fails to start\n";
        NetUdpSocket holder;
        require(holder.NET_IPSocket(0, LoopbackIpv4), "the holder binds an ephemeral port");
        const auto heldPort = holder.port();
        require(heldPort != 0, "the holder has a non-zero port");
        SvUdpTransport blocked;
        require(!blocked.start(heldPort, LoopbackIpv4), "binding the occupied port fails");
        const auto failed = blocked.status();
        require(!failed.bound, "a failed start leaves the transport unbound");
        require(failed.port == 0, "a failed start leaves the port at zero");
        require(failed.lastSocketError != 0, "a failed start records a socket error");
        blocked.stop();
    }

    void testDefaultAddressStaysInaddrAny()
    {
        std::cout << "[extra] the default address stays INADDR_ANY\n";
        // A default-bound socket must accept traffic addressed to loopback; a
        // narrower default (one interface) would not.
        NetUdpSocket receiver;
        require(receiver.NET_IPSocket(0), "the default address binds");
        const auto receiverPort = receiver.port();
        require(receiverPort != 0, "the default address binds an ephemeral port");

        NetUdpSocket sender;
        require(sender.NET_IPSocket(0, LoopbackIpv4), "the loopback sender binds");
        const std::array<std::uint8_t, 4> payload{ 0xDE, 0xAD, 0xBE, 0xEF };
        require(
            sender.NET_SendPacket({ LoopbackIpv4, receiverPort }, payload),
            "a loopback datagram is sent to the default-bound port");

        PeerAddress from{};
        std::array<std::uint8_t, 32> buffer{};
        std::size_t size{};
        auto received = NetPacketResult::Empty;
        for (int attempt = 0; attempt < 200; ++attempt)
        {
            received = receiver.NET_GetPacket(from, buffer, size);
            if (received != NetPacketResult::Empty)
                break;
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
        require(received == NetPacketResult::Received, "the default-bound socket receives it");
        require(size == payload.size(), "the payload length matches");
        require(
            std::equal(payload.begin(), payload.end(), buffer.begin()),
            "the payload bytes match");

        // The transport's own default overload must bind as well.
        SvUdpTransport defaultBound;
        require(defaultBound.start(0), "SvUdpTransport::start(0) uses the default address");
        const auto status = defaultBound.status();
        require(status.bound && status.port != 0, "the default overload reports a bound port");
        defaultBound.stop();
    }

    // A-1: an already-bound socket must not report success for a request whose
    // address the live binding does not satisfy.
    void testAddressMustMatchLiveBinding()
    {
        std::cout << "[A-1] the requested address must match the live binding\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "start(0, 127.0.0.1) succeeds");
        const auto bound = transport.status();
        require(bound.port != 0, "an ephemeral port was assigned");

        const std::array<SvOutboundPacket, 1> outbound{ {
            SvOutboundPacket{
                .peer = { LoopbackIpv4, bound.port },
                .data = { 0x11, 0x22, 0x33, 0x44 } },
        } };
        transport.NET_SendPackets(outbound, 2000);
        const auto before = transport.status();
        require(before.packetsSent > 0, "the send path makes packetsSent non-zero");

        // Same port, same address: the historical idempotent success.
        require(
            transport.start(bound.port, LoopbackIpv4),
            "same port and same address succeeds");
        const auto same = transport.status();
        require(same.port == before.port, "the same-address repeat keeps the port");
        require(same.packetsSent == before.packetsSent, "the same-address repeat keeps the counter");

        // Same port, different address: refused, with the live binding intact.
        require(
            !transport.start(bound.port, AnyIpv4Address),
            "same port with a different address fails");
        const auto conflict = transport.status();
        require(conflict.bound, "the transport is still bound");
        require(conflict.port == before.port, "the bound port is untouched");
        require(conflict.packetsSent == before.packetsSent, "the counter is untouched");
        require(
            conflict.lastSocketError == SocketAlreadyBoundError,
            "the address conflict reports SocketAlreadyBoundError");

        // Port 0 keeps the existing idempotent contract even with another address.
        require(
            transport.start(0, AnyIpv4Address),
            "start(0) with another address stays idempotent");
        const auto afterZero = transport.status();
        require(afterZero.port == before.port, "start(0) keeps the port");
        require(afterZero.packetsSent == before.packetsSent, "start(0) keeps the counter");

        // The socket must still work after the refused requests.
        transport.NET_SendPackets(outbound, 2001);
        require(
            transport.status().packetsSent == before.packetsSent + 1,
            "the socket still sends after the refused requests");
        transport.stop();

        // The reverse direction: bound to INADDR_ANY, a specific address is a mismatch.
        SvUdpTransport anyBound;
        require(anyBound.start(0, AnyIpv4Address), "start(0, INADDR_ANY) succeeds");
        const auto anyPort = anyBound.status().port;
        require(anyPort != 0, "INADDR_ANY assigned an ephemeral port");
        require(
            !anyBound.start(anyPort, LoopbackIpv4),
            "a specific address against an INADDR_ANY binding fails");
        require(
            anyBound.status().lastSocketError == SocketAlreadyBoundError,
            "the reverse conflict is reported");
        require(
            anyBound.start(anyPort, AnyIpv4Address),
            "the exact INADDR_ANY repeat succeeds");
        anyBound.stop();
    }

    // C-3: the socket-initialisation failure paths must be diagnosable from the
    // log alone.
    void testInitializationFailureLogging()
    {
        std::cout << "[C-3] a bind failure logs operation, address, port and error\n";
        NetUdpSocket holder;
        require(holder.NET_IPSocket(0, LoopbackIpv4), "the holder binds an ephemeral port");
        const auto heldPort = holder.port();
        require(heldPort != 0, "the holder has a non-zero port");

        std::ostringstream captured;
        auto *const originalClog = std::clog.rdbuf();
        std::clog.rdbuf(captured.rdbuf());
        SvUdpTransport blocked;
        const auto bound = blocked.start(heldPort, LoopbackIpv4);
        std::clog.rdbuf(originalClog);

        require(!bound, "binding the occupied port fails");
        const auto text = captured.str();
        require(text.find("udp init failed") != std::string::npos, "the failure is logged");
        require(text.find("op=bind") != std::string::npos, "the failing operation is named");
        require(
            text.find("requested=127.0.0.1:") != std::string::npos,
            "the requested address is logged as a dotted quad");
        require(
            text.find(":" + std::to_string(heldPort)) != std::string::npos,
            "the requested port is logged");
        require(
            text.find("actual=unavailable") != std::string::npos,
            "the unconfirmed actual binding is marked unavailable");
        const auto errorPosition = text.find("error=");
        require(errorPosition != std::string::npos, "the raw error code is logged");
        if (errorPosition != std::string::npos)
        {
            const auto loggedError = std::stoi(text.substr(errorPosition + 6));
            require(loggedError != 0, "the logged error is a real Winsock code");
            require(
                loggedError == blocked.status().lastSocketError,
                "the logged error matches the reported status");
        }
        blocked.stop();

        // The success path keeps its original log.
        std::ostringstream successCaptured;
        auto *const restore = std::clog.rdbuf();
        std::clog.rdbuf(successCaptured.rdbuf());
        NetUdpSocket fresh;
        const auto freshBound = fresh.NET_IPSocket(0, LoopbackIpv4);
        std::clog.rdbuf(restore);
        require(freshBound, "a fresh loopback bind succeeds");
        const auto successText = successCaptured.str();
        require(successText.find("udp bound") != std::string::npos, "the success log is unchanged");
        require(
            successText.find("address=127.0.0.1") != std::string::npos,
            "the success log names the address");
    }

    // B-1: stop() must report whether the socket was actually released. The
    // close-failure branch cannot be provoked offline, so only the success and
    // idempotent paths are asserted here.
    void testStopReturnValue()
    {
        std::cout << "[B-1] stop() reports the release result\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "start(0) succeeds");
        require(transport.stop(), "a normal stop returns true");
        const auto stopped = transport.status();
        require(!stopped.bound && stopped.port == 0, "the stopped transport is unbound");
        require(
            stopped.packetsReceived == 0 && stopped.packetsSent == 0,
            "the stopped transport has zeroed counters");
        require(transport.stop(), "a repeated stop on a stopped transport returns true");

        require(transport.start(0, LoopbackIpv4), "the transport rebinds after stop");
        require(transport.status().bound, "the rebind is reported as bound");
        require(transport.stop(), "the second normal stop returns true");
        require(!transport.status().bound, "the second stop clears the binding again");
    }

    // P1: a controlled closesocket failure must leave the binding and the handle
    // intact, and the next stop must complete the cleanup. The failure is
    // simulated through this module's import table; it is not a genuine Windows
    // closesocket failure.
    void testStopCloseFailureKeepsBinding()
    {
        std::cout << "[simulated-close-failure] a failed release keeps the socket\n";
        SvUdpTransport transport;
        require(transport.start(0, LoopbackIpv4), "start(0) succeeds");
        const auto bound = transport.status();
        require(bound.port != 0, "an ephemeral port was assigned");

        const std::array<SvOutboundPacket, 1> outbound{ {
            SvOutboundPacket{
                .peer = { LoopbackIpv4, bound.port },
                .data = { 0x51, 0x52, 0x53, 0x54 } },
        } };
        transport.NET_SendPackets(outbound, 3000);
        const auto before = transport.status();
        require(before.packetsSent > 0, "the send path makes packetsSent non-zero");

        // A6: remember where the log ends so only this call's bytes are checked.
        const auto logPath = gameServerLogPath();
        std::error_code logError;
        const auto logExistedBefore = std::filesystem::exists(logPath, logError);
        const auto logSizeBefore = logFileSizeOrZero(logPath);
        std::cout << "       game-server log existed-before="
                  << (logExistedBefore ? "true" : "false")
                  << " bytes-before=" << logSizeBefore << '\n';

        bool released = true;
        {
            ScopedCloseSocketFailure failure(WSAENOTSOCK);
            require(failure.active(), "the closesocket import can be redirected for the test");
            released = transport.stop();
        }
        require(!released, "a failed close makes stop return false");

        const auto appended = readAppendedBytes(logPath, logSizeBefore);
        require(
            appended.find(
                std::string("udp transport stop failed op=close error=") +
                std::to_string(WSAENOTSOCK)) != std::string::npos,
            "the failed stop appends the close-failure log line");

        const auto failed = transport.status();
        require(failed.bound, "the binding is retained after the failed stop");
        require(failed.port == before.port, "the port is retained after the failed stop");
        require(
            failed.packetsSent == before.packetsSent,
            "the send counter is retained after the failed stop");
        require(
            failed.lastSocketError == WSAENOTSOCK,
            "the injected close error is reported through the status");

        // The failed close must have left the handle usable.
        transport.NET_SendPackets(outbound, 3001);
        require(
            transport.status().packetsSent == before.packetsSent + 1,
            "the socket still sends after the failed stop");

        // The retry uses the real closesocket and must complete the cleanup.
        require(transport.stop(), "the retry stop returns true");
        const auto recovered = transport.status();
        require(!recovered.bound && recovered.port == 0, "the retry clears the binding");
        require(recovered.packetsSent == 0, "the retry zeroes the send counter");
    }
}

int main()
{
    std::cout << "=== ol_transport_lifecycle_tests ===\n";
    testLoopbackEphemeralBinding();
    testRepeatedStartKeepsBinding();
    testDifferentPortDoesNotDisturbBinding();
    testStopClearsState();
    testRepeatedStop();
    testRebindAfterStop();
    testStickyErrorAcrossStop();
    testOccupiedPortFails();
    testDefaultAddressStaysInaddrAny();
    testAddressMustMatchLiveBinding();
    testInitializationFailureLogging();
    testStopReturnValue();
    testStopCloseFailureKeepsBinding();
    std::cout << "checks=" << Checks << " failures=" << Failures << '\n';
    return Failures == 0 ? 0 : 1;
}
