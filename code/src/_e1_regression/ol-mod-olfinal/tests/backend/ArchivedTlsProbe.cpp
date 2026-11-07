#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <WinSock2.h>
#include <WS2tcpip.h>
#include <Windows.h>

#include "IServer.hpp"
#include "Demonware/LobbyProtocol.hpp"

#include <algorithm>
#include <array>
#include <cstring>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#pragma warning(push, 0)
#include <openssl/bio.h>
#include <openssl/err.h>
#include <openssl/pem.h>
#include <openssl/ssl.h>
#include <openssl/x509.h>
#pragma warning(pop)

namespace
{
    using CreateServer = IServer *(__cdecl *)(const char *);

    void require(const bool condition, const char *message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    bool transferClientOutput(SSL *client, IServer *server)
    {
        bool moved = false;
        std::array<std::uint8_t, 4096> buffer{};
        while (true)
        {
            const auto count = BIO_read(SSL_get_wbio(client), buffer.data(), static_cast<int>(buffer.size()));
            if (count <= 0)
                return moved;
            require(server->onStreamwrite(buffer.data(), static_cast<std::uint32_t>(count)),
                "archived server rejected TLS input");
            moved = true;
        }
    }

    bool transferServerOutput(IServer *server, SSL *client)
    {
        bool moved = false;
        std::array<std::uint8_t, 4096> buffer{};
        while (true)
        {
            auto size = static_cast<std::uint32_t>(buffer.size());
            if (!server->onStreamread(buffer.data(), &size))
                return moved;
            require(size <= buffer.size(), "archived server returned oversized TLS output");
            require(BIO_write(SSL_get_rbio(client), buffer.data(), static_cast<int>(size)) ==
                static_cast<int>(size), "could not feed archived TLS output to client");
            moved = true;
        }
    }

    std::string nameText(X509_NAME *name)
    {
        BIO *memory = BIO_new(BIO_s_mem());
        require(memory != nullptr, "BIO_new failed");
        X509_NAME_print_ex(memory, name, 0, XN_FLAG_RFC2253);
        char *data{};
        const auto size = BIO_get_mem_data(memory, &data);
        std::string result(data, static_cast<std::size_t>(size));
        BIO_free(memory);
        return result;
    }

    std::vector<std::uint8_t> drainServer(IServer *server)
    {
        std::vector<std::uint8_t> output;
        std::array<std::uint8_t, 4096> buffer{};
        for (unsigned int attempt = 0; attempt != 100; ++attempt)
        {
            auto size = static_cast<std::uint32_t>(buffer.size());
            if (!server->onStreamread(buffer.data(), &size) || size == 0)
                return output;
            require(size <= buffer.size(), "server returned oversized stream output");
            output.insert(output.end(), buffer.begin(), buffer.begin() + size);
        }
        throw std::runtime_error("server stream output did not drain");
    }

    std::vector<std::uint8_t> waitForServerOutput(IServer *server, const unsigned int timeoutMs)
    {
        for (unsigned int elapsed = 0; elapsed < timeoutMs; elapsed += 10)
        {
            Sleep(10);
            auto output = drainServer(server);
            if (!output.empty())
                return output;
        }
        return {};
    }

    std::vector<std::span<const std::uint8_t>> splitLobbyFrames(
        const std::span<const std::uint8_t> stream)
    {
        std::vector<std::span<const std::uint8_t>> frames;
        std::size_t offset{};
        while (offset < stream.size())
        {
            require(stream.size() - offset >= 4, "truncated lobby frame length");
            const auto payloadSize = static_cast<std::uint32_t>(stream[offset]) |
                (static_cast<std::uint32_t>(stream[offset + 1]) << 8) |
                (static_cast<std::uint32_t>(stream[offset + 2]) << 16) |
                (static_cast<std::uint32_t>(stream[offset + 3]) << 24);
            const auto frameSize = static_cast<std::size_t>(payloadSize) + 4;
            require(frameSize <= stream.size() - offset, "truncated lobby frame payload");
            frames.emplace_back(stream.subspan(offset, frameSize));
            offset += frameSize;
        }
        return frames;
    }

    std::vector<std::uint8_t> drainPacketServer(IServer *server)
    {
        std::vector<std::uint8_t> output;
        std::array<std::uint8_t, 4096> buffer{};
        for (unsigned int attempt = 0; attempt != 100; ++attempt)
        {
            auto size = static_cast<std::uint32_t>(buffer.size());
            if (!server->onPacketread(buffer.data(), &size) || size == 0)
                return output;
            require(size <= buffer.size(), "server returned oversized packet output");
            output.insert(output.end(), buffer.begin(), buffer.begin() + size);
        }
        throw std::runtime_error("server packet output did not drain");
    }

    void printHex(const std::span<const std::uint8_t> data)
    {
        for (const auto value : data)
            std::cout << std::hex << std::uppercase << std::setfill('0') << std::setw(2)
                      << static_cast<unsigned int>(value);
        std::cout << std::dec << '\n';
    }

    std::span<const std::uint8_t> archivedString(
        const std::uint8_t *image,
        const std::size_t offset)
    {
        const auto object = image + offset;
        const auto size = *reinterpret_cast<const std::uint32_t *>(object + 16);
        const auto capacity = *reinterpret_cast<const std::uint32_t *>(object + 20);
        const auto data = capacity < 16
            ? object
            : reinterpret_cast<const std::uint8_t *>(
                *reinterpret_cast<const std::uintptr_t *>(object));
        return {data, size};
    }

    std::vector<std::uint8_t> fromHex(const std::string_view value)
    {
        require(value.size() % 2 == 0, "hex fixture has an odd length");
        const auto digit = [](const char character) -> std::uint8_t
        {
            if (character >= '0' && character <= '9')
                return static_cast<std::uint8_t>(character - '0');
            if (character >= 'a' && character <= 'f')
                return static_cast<std::uint8_t>(character - 'a' + 10);
            if (character >= 'A' && character <= 'F')
                return static_cast<std::uint8_t>(character - 'A' + 10);
            throw std::runtime_error("invalid hex fixture");
        };

        std::vector<std::uint8_t> output(value.size() / 2);
        for (std::size_t index = 0; index != output.size(); ++index)
            output[index] = static_cast<std::uint8_t>((digit(value[index * 2]) << 4) | digit(value[index * 2 + 1]));
        return output;
    }

    std::string asciiFromWide(const std::wstring_view value)
    {
        std::string output;
        output.reserve(value.size());
        for (const auto character : value)
        {
            require(character <= 0x7F, "hex argument must contain ASCII characters only");
            output.push_back(static_cast<char>(character));
        }
        return output;
    }

    struct LsgFixture
    {
        std::array<std::uint8_t, 24> sessionKey{};
        std::vector<std::uint8_t> clientHeader;
        std::vector<std::uint8_t> clientAuth;
    };

    LsgFixture defaultLsgFixture()
    {
        LsgFixture fixture;
        constexpr std::string_view SessionKey = "Tencentticket";
        std::copy(SessionKey.begin(), SessionKey.end(), fixture.sessionKey.begin());
        fixture.clientHeader = fromHex(
            "c8000000c8000000d2000000d200000000000800e3823f2caf646fba");
        fixture.clientAuth = fromHex(
            "95000000ab820711fb000000dab69b9df36eed7d07601f0000e0663b53fbffffff"
            "0300000000000000f0066ef50e0080080862bb0bcb9b7b3333634b732b030000"
            "0000000000000000000000000000000000000000000000000000000000000000"
            "000000000000000000000000000000000000a02a731b2b73a3a34b1b5b2ba303"
            "0000000000000000000098a9120100000000db73bf2e280e");
        return fixture;
    }

    LsgFixture loadLsgFixture(const std::filesystem::path &path)
    {
        std::ifstream input(path);
        require(input.good(), "could not open LSG fixture");
        LsgFixture fixture;
        bool foundSessionKey{};
        bool foundHeader{};
        bool foundAuth{};
        std::string line;
        while (std::getline(input, line))
        {
            if (!line.empty() && line.back() == '\r')
                line.pop_back();
            const auto separator = line.find('=');
            if (separator == std::string::npos)
                continue;
            const auto name = std::string_view(line).substr(0, separator);
            const auto value = std::string_view(line).substr(separator + 1);
            if (name == "session_key")
            {
                const auto bytes = fromHex(value);
                require(bytes.size() == fixture.sessionKey.size(), "LSG fixture session key must be 24 bytes");
                std::copy(bytes.begin(), bytes.end(), fixture.sessionKey.begin());
                foundSessionKey = true;
            }
            else if (name == "client_header")
            {
                fixture.clientHeader = fromHex(value);
                foundHeader = true;
            }
            else if (name == "client_auth")
            {
                fixture.clientAuth = fromHex(value);
                foundAuth = true;
            }
        }
        require(foundSessionKey && foundHeader && foundAuth, "LSG fixture is missing a required field");
        return fixture;
    }
}

int wmain(const int argc, wchar_t **argv)
{
    std::cout.setf(std::ios::unitbuf);
    if (argc < 2)
    {
        std::wcerr << L"Usage: AlwaysofflineRe.ArchivedTlsProbe <plugin> "
                     L"[--certificate FILE] [--lsg-fixture FILE] "
                     L"[--lsg-request HEX]... [--lan-packet HEX]\n";
        return 2;
    }

    std::optional<std::filesystem::path> certificatePath;
    std::optional<std::filesystem::path> fixturePath;
    std::optional<std::vector<std::uint8_t>> lanPacket;
    std::vector<std::vector<std::uint8_t>> lsgRequests;
    for (int index = 2; index < argc; index += 2)
    {
        if (index + 1 >= argc)
        {
            std::wcerr << L"Missing value for " << argv[index] << L'\n';
            return 2;
        }
        const std::wstring_view option = argv[index];
        if (option == L"--certificate")
            certificatePath = argv[index + 1];
        else if (option == L"--lsg-fixture")
            fixturePath = argv[index + 1];
        else if (option == L"--lsg-request")
        {
            const std::wstring_view wideValue = argv[index + 1];
            lsgRequests.push_back(fromHex(asciiFromWide(wideValue)));
        }
        else if (option == L"--lan-packet")
        {
            lanPacket = fromHex(asciiFromWide(argv[index + 1]));
        }
        else
        {
            std::wcerr << L"Unknown option: " << option << L'\n';
            return 2;
        }
    }

    try
    {
        const auto module = LoadLibraryW(argv[1]);
        require(module != nullptr, "LoadLibraryW failed");
        const auto createServer = reinterpret_cast<CreateServer>(GetProcAddress(module, "Createserver"));
        require(createServer != nullptr, "Createserver export was not found");

        auto *stun = createServer("stun.qq.com");
        require(stun != nullptr, "archived plugin did not claim stun.qq.com");
        IServer::Endpoints endpoints{};
        endpoints.client.ipv4 = inet_addr("10.1.2.3");
        endpoints.client.port = htons(3074);
        endpoints.server.ipv4 = inet_addr("203.0.113.9");
        endpoints.server.port = htons(3075);
        constexpr std::array<std::uint8_t, 4> NatRequest{ 0x14, 0x02, 0x00, 0x00 };
        require(stun->onPacketwrite(NatRequest.data(), static_cast<std::uint32_t>(NatRequest.size()), &endpoints),
            "archived STUN server rejected type-20 request");
        const auto natResponse = drainPacketServer(stun);
        require(!natResponse.empty(), "archived STUN server did not answer type-20 request");
        std::cout << "STUN type-20 response: ";
        printHex(natResponse);

        constexpr std::array<std::uint8_t, 3> AddressRequest{ 0x1E, 0x03, 0x00 };
        require(stun->onPacketwrite(
            AddressRequest.data(), static_cast<std::uint32_t>(AddressRequest.size()), &endpoints),
            "archived STUN server rejected type-30 request");
        const auto addressResponse = drainPacketServer(stun);
        require(!addressResponse.empty(), "archived STUN server did not answer type-30 request");
        std::cout << "STUN type-30 response: ";
        printHex(addressResponse);

        auto *sameStun = createServer("stun.qq.com");
        require(sameStun != nullptr, "archived plugin did not reclaim stun.qq.com");
        std::cout << "STUN instance reused: " << (sameStun == stun ? "yes" : "no") << '\n';

        auto secondEndpoints = endpoints;
        secondEndpoints.client.port = htons(4000);
        secondEndpoints.server.ipv4 = inet_addr("198.51.100.42");
        secondEndpoints.server.port = htons(4001);
        require(stun->onPacketwrite(NatRequest.data(), static_cast<std::uint32_t>(NatRequest.size()), &endpoints),
            "archived STUN server rejected first burst request");
        require(stun->onPacketwrite(
            NatRequest.data(), static_cast<std::uint32_t>(NatRequest.size()), &secondEndpoints),
            "archived STUN server rejected second burst request");
        const auto burstResponse = drainPacketServer(stun);
        std::cout << "STUN two-write response (" << burstResponse.size() << " bytes): ";
        printHex(burstResponse);

        auto *server = createServer("auth3.qq.com");
        require(server != nullptr, "archived plugin did not claim auth3.qq.com");
        server->onConnect();

        SSL_CTX *context = SSL_CTX_new(TLS_client_method());
        require(context != nullptr, "SSL_CTX_new failed");
        SSL_CTX_set_verify(context, SSL_VERIFY_NONE, nullptr);
        SSL_CTX_set_security_level(context, 0);
        require(SSL_CTX_set_min_proto_version(context, TLS1_VERSION) == 1, "could not enable TLS 1.0");
        require(SSL_CTX_set_max_proto_version(context, TLS1_VERSION) == 1, "could not force TLS 1.0");
        require(SSL_CTX_set_cipher_list(context, "ALL:@SECLEVEL=0") == 1, "could not enable legacy ciphers");

        SSL *client = SSL_new(context);
        require(client != nullptr, "SSL_new failed");
        BIO *read = BIO_new(BIO_s_mem());
        BIO *write = BIO_new(BIO_s_mem());
        require(read && write, "BIO_new failed");
        BIO_set_nbio(read, 1);
        BIO_set_nbio(write, 1);
        SSL_set_bio(client, read, write);
        SSL_set_connect_state(client);

        for (unsigned int attempt = 0; attempt != 100 && !SSL_is_init_finished(client); ++attempt)
        {
            static_cast<void>(SSL_do_handshake(client));
            static_cast<void>(transferClientOutput(client, server));
            static_cast<void>(transferServerOutput(server, client));
        }
        require(SSL_is_init_finished(client), "archived TLS handshake did not complete");

        X509 *certificate = SSL_get1_peer_certificate(client);
        require(certificate != nullptr, "archived server did not provide a certificate");
        std::cout << "Version: " << X509_get_version(certificate) + 1 << '\n';
        std::cout << "Signature: " << OBJ_nid2ln(X509_get_signature_nid(certificate)) << '\n';
        std::cout << "Subject: " << nameText(X509_get_subject_name(certificate)) << '\n';
        std::cout << "Issuer: " << nameText(X509_get_issuer_name(certificate)) << '\n';
        std::array<unsigned char, EVP_MAX_MD_SIZE> digest{};
        unsigned int digestSize{};
        require(X509_digest(certificate, EVP_sha256(), digest.data(), &digestSize) == 1,
            "certificate digest failed");
        std::cout << "SHA256: ";
        for (unsigned int index = 0; index != digestSize; ++index)
            std::cout << std::hex << std::uppercase << std::setfill('0') << std::setw(2)
                      << static_cast<unsigned int>(digest[index]);
        std::cout << '\n';

        constexpr std::string_view body =
            R"({"identity":"1020304","title_id":"1004","auth_task":"28","iv_seed":"2295540364","extra_data":"{\"token\":\"\"}","codo_request":"AAAAAAAA3sCt3gEAEAFBbHdheXNvZmZsaW5lAAAAAAABAgMEBQYHCAkKCwwNDg8QERITFBUWFxg=","machine_id":"","version":"1","codo_request_size_bits":"448","extended_data":false})";
        std::string request = "POST /auth/ HTTP/1.1\r\nHost: auth3.qq.com\r\nContent-Type: application/json\r\n";
        request += "Content-Length: " + std::to_string(body.size()) + "\r\n\r\n";
        request.append(body);
        require(SSL_write(client, request.data(), static_cast<int>(request.size())) ==
            static_cast<int>(request.size()), "could not write Auth3 request");
        static_cast<void>(transferClientOutput(client, server));
        static_cast<void>(transferServerOutput(server, client));
        std::string response;
        std::array<char, 4096> plaintext{};
        for (unsigned int attempt = 0; attempt != 20; ++attempt)
        {
            const auto readSize = SSL_read(client, plaintext.data(), static_cast<int>(plaintext.size()));
            if (readSize > 0)
                response.append(plaintext.data(), static_cast<std::size_t>(readSize));
            static_cast<void>(transferClientOutput(client, server));
            static_cast<void>(transferServerOutput(server, client));
        }
        require(!response.empty(), "archived server did not return an Auth3 response");
        std::cout << "Response:\n" << response << '\n';

        const auto image = reinterpret_cast<const std::uint8_t *>(module);
        const auto dos = reinterpret_cast<const IMAGE_DOS_HEADER *>(image);
        const auto nt = reinterpret_cast<const IMAGE_NT_HEADERS *>(image + dos->e_lfanew);
        if (dos->e_magic == IMAGE_DOS_SIGNATURE && nt->Signature == IMAGE_NT_SIGNATURE &&
            nt->OptionalHeader.SizeOfImage >= 0x1A04E8)
        {
            std::cout << "Archived title: " << *reinterpret_cast<const std::uint32_t *>(image + 0x1A0470)
                      << '\n';
            std::cout << "Archived user: " << *reinterpret_cast<const std::uint64_t *>(image + 0x1A0480)
                      << '\n';
            std::cout << "Archived session key: ";
            for (std::size_t index = 0; index != 24; ++index)
                std::cout << std::hex << std::uppercase << std::setfill('0') << std::setw(2)
                          << static_cast<unsigned int>(image[0x1A04D0 + index]);
            std::cout << std::dec << '\n';
        }

        auto *lobby = createServer("lsg.qq.com");
        require(lobby != nullptr, "plugin did not claim lsg.qq.com");
        lobby->onConnect();
        const auto fixture = fixturePath ? loadLsgFixture(*fixturePath) : defaultLsgFixture();
        const auto &header = fixture.clientHeader;
        require(header.size() == 28, "LSG fixture client header must be 28 bytes");
        require(lobby->onStreamwrite(header.data(), static_cast<std::uint32_t>(header.size())),
            "lobby rejected client header");
        const auto headerAck = drainServer(lobby);
        require(!headerAck.empty(), "lobby did not return a header ACK");
        std::cout << "LSG header ACK: ";
        printHex(headerAck);

        const auto &capturedSessionKey = fixture.sessionKey;
        require(nt->OptionalHeader.SizeOfImage >= 0x1A04E8, "archived image does not expose the session key");
        std::memcpy(const_cast<std::uint8_t *>(image) + 0x1A04D0,
            capturedSessionKey.data(), capturedSessionKey.size());
        const auto &auth = fixture.clientAuth;
        require(auth.size() >= 4, "LSG fixture client auth is truncated");
        require(auth.size() == 4 + *reinterpret_cast<const std::uint32_t *>(auth.data()),
            "captured client auth contains trailing stream bytes");
        require(lobby->onStreamwrite(auth.data(), static_cast<std::uint32_t>(auth.size())),
            "lobby rejected client auth");
        const auto authDone = drainServer(lobby);
        require(!authDone.empty(), "lobby did not return auth-done");
        std::cout << "LSG auth done: ";
        printHex(authDone);

        for (const auto [name, offset] : {
                 std::pair{"client transcript", std::size_t{0x1A0518}},
                 std::pair{"server transcript", std::size_t{0x1A0530}},
                 std::pair{"auth transcript", std::size_t{0x1A0548}},
             })
        {
            const auto value = archivedString(image, offset);
            std::cout << "Archived " << name << " (" << value.size() << " bytes): ";
            printHex(value);
        }

        std::array<std::uint8_t, 20> archivedHmac{};
        std::array<std::uint8_t, 16> archivedEncrypt{};
        std::array<std::uint8_t, 16> archivedDecrypt{};
        if (nt->OptionalHeader.SizeOfImage >= 0x1A64D8)
        {
            std::memcpy(archivedHmac.data(), image + 0x1A04BC, archivedHmac.size());
            std::memcpy(archivedEncrypt.data(), image + 0x1A04E8, archivedEncrypt.size());
            std::memcpy(archivedDecrypt.data(), image + 0x1A0500, archivedDecrypt.size());
            std::cout << "Archived LSG HMAC key: ";
            printHex(archivedHmac);
            std::cout << "Archived LSG encrypt key: ";
            printHex(archivedEncrypt);
            std::cout << "Archived LSG decrypt key: ";
            printHex(archivedDecrypt);
            std::cout << "Archived LSG outgoing sequence: "
                      << *reinterpret_cast<const std::uint32_t *>(image + 0x1A64D4) << '\n';

        }

        std::vector<std::uint8_t> transcript(header.begin() + 8, header.end());
        transcript.insert(transcript.end(), headerAck.begin(), headerAck.end());
        transcript.insert(transcript.end(), auth.begin(), auth.end() - 8);
        const auto keys = AlwaysofflineRe::Demonware::deriveSessionKeys(capturedSessionKey, transcript);
        try
        {
            std::vector<std::uint8_t> expectedAuthDone{ 0x0A, 0x00, 0x00, 0x00, 0xAB, 0x83 };
            expectedAuthDone.insert(expectedAuthDone.end(), keys.responseId.begin(), keys.responseId.end());
            require(authDone == expectedAuthDone, "archived plaintext AB83 does not match derived response ID");
            require(std::equal(keys.responseHmac.begin(), keys.responseHmac.end(), archivedHmac.begin()),
                "archived response HMAC key does not match reconstructed KDF");
            require(std::equal(keys.encrypt.begin(), keys.encrypt.end(), archivedEncrypt.begin()),
                "archived encrypt key does not match reconstructed KDF");
            require(std::equal(keys.decrypt.begin(), keys.decrypt.end(), archivedDecrypt.begin()),
                "archived decrypt key does not match reconstructed KDF");
            std::cout << "Archived plaintext AB83 and all reconstructed LSG keys match.\n";

            if (lanPacket)
            {
                WSADATA winsock{};
                require(WSAStartup(MAKEWORD(2, 2), &winsock) == 0, "WSAStartup failed");
                const auto socketHandle = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
                require(socketHandle != INVALID_SOCKET, "could not create LAN probe socket");
                SOCKADDR_IN destination{};
                destination.sin_family = AF_INET;
                destination.sin_port = htons(0x4321);
                destination.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
                require(sendto(
                    socketHandle,
                    reinterpret_cast<const char *>(lanPacket->data()),
                    static_cast<int>(lanPacket->size()),
                    0,
                    reinterpret_cast<const SOCKADDR *>(&destination),
                    sizeof(destination)) == static_cast<int>(lanPacket->size()),
                    "could not send synthetic LAN packet");
                closesocket(socketHandle);
                WSACleanup();
                Sleep(1200);
                std::cout << "Synthetic LAN packet sent: " << lanPacket->size() << " bytes\n";
            }

            if (lsgRequests.empty())
                lsgRequests.push_back({ 0x47, 0x03, 0x09 });
            const std::array<std::uint8_t, 16> zeroIv{};
            std::uint32_t sequence = 1;
            for (const auto &requestBytes : lsgRequests)
            {
                require(requestBytes.size() >= 3, "LSG service request must include service, protocol, and task");
                const auto requestFrame = AlwaysofflineRe::Demonware::encodeEncryptedLobbyMessage(
                    requestBytes, keys.decrypt, keys.requestHmac, sequence, zeroIv);
                require(lobby->onStreamwrite(
                    requestFrame.data(), static_cast<std::uint32_t>(requestFrame.size())),
                    "lobby rejected an encrypted service request");
                const auto responseFrame = drainServer(lobby);
                require(!responseFrame.empty(), "lobby did not return an encrypted service response");
                const auto responseFrames = splitLobbyFrames(responseFrame);
                require(!responseFrames.empty(), "lobby response stream did not contain a frame");
                const auto decoded = AlwaysofflineRe::Demonware::decodeEncryptedLobbyMessage(
                    responseFrames.front(), keys.encrypt, keys.responseHmac);
                require(decoded.sequence == sequence, "archived service response sequence mismatch");
                std::cout << "LSG task " << std::hex << std::uppercase << std::setfill('0')
                          << std::setw(2) << static_cast<unsigned int>(requestBytes[0]) << '/'
                          << std::setw(2) << static_cast<unsigned int>(requestBytes[2]) << std::dec
                          << " sequence: " << decoded.sequence << '\n';
                std::cout << "LSG task message type: "
                          << static_cast<unsigned int>(decoded.messageType) << '\n';
                std::cout << "LSG task payload: ";
                printHex(decoded.payload);

                for (std::size_t index = 1; index != responseFrames.size(); ++index)
                {
                    const auto asynchronous = AlwaysofflineRe::Demonware::decodeEncryptedLobbyMessage(
                        responseFrames[index], keys.encrypt, keys.responseHmac);
                    std::cout << "LSG bundled asynchronous sequence: " << asynchronous.sequence << '\n';
                    std::cout << "LSG bundled asynchronous message type: "
                              << static_cast<unsigned int>(asynchronous.messageType) << '\n';
                    std::cout << "LSG bundled asynchronous payload: ";
                    printHex(asynchronous.payload);
                }

                const auto asynchronousStream = waitForServerOutput(lobby, 500);
                for (const auto asynchronousFrame : splitLobbyFrames(asynchronousStream))
                {
                    const auto asynchronous = AlwaysofflineRe::Demonware::decodeEncryptedLobbyMessage(
                        asynchronousFrame, keys.encrypt, keys.responseHmac);
                    std::cout << "LSG asynchronous sequence: " << asynchronous.sequence << '\n';
                    std::cout << "LSG asynchronous message type: "
                              << static_cast<unsigned int>(asynchronous.messageType) << '\n';
                    std::cout << "LSG asynchronous payload: ";
                    printHex(asynchronous.payload);
                }
                ++sequence;
            }
        }
        catch (const std::exception &error)
        {
            std::cout << "LSG deep probe stopped: " << error.what() << '\n';
        }
        lobby->onDisconnect();

        if (certificatePath)
        {
            BIO *output = BIO_new_file(certificatePath->string().c_str(), "wb");
            require(output != nullptr, "could not create certificate output");
            require(PEM_write_bio_X509(output, certificate) == 1, "PEM_write_bio_X509 failed");
            BIO_free(output);
            std::wcout << L"Certificate: " << *certificatePath << L'\n';
        }

        X509_free(certificate);
        SSL_free(client);
        SSL_CTX_free(context);
        server->onDisconnect();
        FreeLibrary(module);
        return 0;
    }
    catch (const std::exception &error)
    {
        std::cerr << "Probe failed: " << error.what();
        if (const auto code = ERR_get_error())
            std::cerr << ": " << ERR_error_string(code, nullptr);
        std::cerr << '\n';
        return 1;
    }
}
