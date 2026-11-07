#pragma once

#include <array>
#include <cstdint>
#include <memory>
#include <optional>
#include <span>
#include <string>
#include <vector>

#include "net_types.hpp"

namespace CodolGameServer
{
    class DtlsSessionConfig
    {
    public:
        static constexpr std::size_t SecurityKeySize = 16;

        bool configureFromDemonwareDescriptor(std::span<const std::uint8_t> descriptor);
        void reset();

        [[nodiscard]] bool configured() const;
        [[nodiscard]] const std::array<std::uint8_t, SecurityKeySize> &securityKey() const;

    private:
        std::array<std::uint8_t, SecurityKeySize> securityKey_{};
        bool configured_{};
    };

    struct DtlsSessionKeys
    {
        std::array<std::uint8_t, 20> digest{};

        static DtlsSessionKeys derive(std::span<const std::uint8_t> sharedMaterial);
        [[nodiscard]] std::array<std::uint8_t, 16> aesKey() const;
        [[nodiscard]] std::array<std::uint8_t, 24> hmacKey() const;
        [[nodiscard]] std::array<std::uint8_t, 16> iv(
            std::uint16_t sequenceNumber,
            std::uint16_t verificationTag) const;
    };

    struct DtlsDataPacket
    {
        static constexpr std::uint8_t PacketType = 0x06;
        static constexpr std::uint8_t Version = 0x02;
        static constexpr std::size_t HeaderSize = 16;

        std::uint16_t verificationTag{};
        std::uint16_t sequenceNumber{};
        std::array<std::uint8_t, 8> authenticator{};
        std::uint16_t encryptedSize{};
        std::vector<std::uint8_t> payload;

        static DtlsDataPacket parse(std::span<const std::uint8_t> packet);
        static std::vector<std::uint8_t> build(
            std::span<const std::uint8_t> plaintext,
            std::uint16_t verificationTag,
            std::uint16_t sequenceNumber,
            const DtlsSessionKeys &keys);

        [[nodiscard]] bool verify(const DtlsSessionKeys &keys) const;
        [[nodiscard]] std::vector<std::uint8_t> decrypt(const DtlsSessionKeys &keys) const;

    private:
        [[nodiscard]] std::vector<std::uint8_t> authenticatedBytes() const;
    };

    struct DtlsInitPacket
    {
        std::uint16_t verificationTag{};
        std::uint16_t counter{};
        std::uint16_t initTag{};
        std::array<std::uint8_t, 8> securityId{};

        static DtlsInitPacket parse(std::span<const std::uint8_t> packet);
    };

    struct DtlsCookieEchoPacket
    {
        std::uint16_t verificationTag{};
        std::uint16_t counter{};
        std::uint16_t clientTag{};
        // 67, not 37. A bdCommonAddr on the wire is 67 bytes; the 37 here was the short form, and
        // it makes every field after it 30 bytes early and the whole packet 30 bytes short. The C#
        // GameServer hit exactly this and was corrected the same way -- at the old offsets the
        // security id came out of the 00FF00FF0000 sentinel run and the ECC parse started
        // mid-sentinel, giving "expected DER SEQUENCE".
        std::array<std::uint8_t, 67> commonAddress{};
        std::array<std::uint8_t, 8> securityId{};
        std::array<std::uint8_t, 100> publicKey{};

        static DtlsCookieEchoPacket parse(std::span<const std::uint8_t> packet);
    };

    class DtlsKeyPair
    {
    public:
        DtlsKeyPair();
        explicit DtlsKeyPair(std::span<const std::uint8_t> privateScalar);
        ~DtlsKeyPair();
        DtlsKeyPair(DtlsKeyPair &&) noexcept;
        DtlsKeyPair &operator=(DtlsKeyPair &&) noexcept;
        DtlsKeyPair(const DtlsKeyPair &) = delete;
        DtlsKeyPair &operator=(const DtlsKeyPair &) = delete;

        [[nodiscard]] std::array<std::uint8_t, 100> publicKey() const;
        [[nodiscard]] std::array<std::uint8_t, 44> sharedMaterial(
            std::span<const std::uint8_t, 100> peerPublicKey,
            std::span<const std::uint8_t, 16> securityKey) const;

    private:
        struct Impl;
        std::unique_ptr<Impl> impl_;
    };

    [[nodiscard]] std::vector<std::uint8_t> NET_DtlsNatIntroReply(
        std::span<const std::uint8_t> packet);
    [[nodiscard]] std::vector<std::uint8_t> NET_DtlsInitAck(
        std::span<const std::uint8_t> packet,
        PeerAddress peer,
        std::uint16_t serverTag,
        std::uint32_t timestamp);
    [[nodiscard]] std::vector<std::uint8_t> NET_DtlsCookieAck(
        std::span<const std::uint8_t> packet,
        std::span<const std::uint8_t, 100> serverPublicKey);

    enum class DtlsPeerState : std::uint8_t
    {
        Empty,
        CookieIssued,
        Established,
    };

    enum class DtlsPacketResultKind : std::uint8_t
    {
        Ignored,
        Reply,
        AuthenticatedData,
        Rejected,
    };

    struct DtlsPacketResult
    {
        DtlsPacketResultKind kind{ DtlsPacketResultKind::Ignored };
        std::vector<std::uint8_t> reply;
        std::vector<std::uint8_t> plaintext;
        std::string reason;
    };

    class DtlsPeerSystem
    {
    public:
        explicit DtlsPeerSystem(
            std::size_t maxPeers = 18,
            std::uint32_t sessionLifetimeMilliseconds = 120'000);

        DtlsPacketResult NET_DtlsPacket(
            PeerAddress peer,
            std::span<const std::uint8_t> packet,
            std::span<const std::uint8_t, DtlsSessionConfig::SecurityKeySize> securityKey,
            std::uint32_t nowMilliseconds,
            std::uint32_t entropy);
        [[nodiscard]] std::vector<std::uint8_t> NET_DtlsBuildData(
            PeerAddress peer,
            std::span<const std::uint8_t> plaintext);
        void rememberSecurityKey(
            std::span<const std::uint8_t, DtlsSessionConfig::SecurityKeySize> securityKey);
        void reset();

        [[nodiscard]] DtlsPeerState peerState(PeerAddress peer) const;
        [[nodiscard]] std::size_t sessionCount() const;

    private:
        struct PeerSession
        {
            bool valid{};
            PeerAddress peer{};
            DtlsPeerState state{ DtlsPeerState::Empty };
            std::uint32_t lastActivityTime{};
            std::uint16_t serverTag{};
            std::uint16_t clientTag{};
            std::array<std::uint8_t, 8> securityId{};
            // The Demonware descriptor may be refreshed while multiple peers
            // are completing DTLS. Keep the key selected at INIT per peer;
            // using the mutable global descriptor during COOKIE_ECHO races
            // the two clients onto different key material.
            std::array<std::uint8_t, DtlsSessionConfig::SecurityKeySize> securityKey{};
            std::array<std::uint8_t, DtlsSessionConfig::SecurityKeySize> previousSecurityKey{};
            bool hasPreviousSecurityKey{};
            std::optional<DtlsKeyPair> keyPair;
            std::optional<DtlsSessionKeys> keys;
            std::optional<DtlsSessionKeys> previousKeys;
            bool usingPreviousKeys{};
            std::uint16_t lastClientSequence{};
            std::uint16_t nextServerSequence{ 1 };
            bool clientSequenceReceived{};
        };

        void expireSessions(std::uint32_t nowMilliseconds);
        PeerSession *findSession(PeerAddress peer);
        [[nodiscard]] const PeerSession *findSession(PeerAddress peer) const;
        PeerSession *allocateSession(PeerAddress peer);

        std::vector<PeerSession> sessions_;
        std::uint32_t sessionLifetimeMilliseconds_;
        std::array<std::uint8_t, DtlsSessionConfig::SecurityKeySize> lastSecurityKey_{};
        std::array<std::uint8_t, DtlsSessionConfig::SecurityKeySize> previousSecurityKey_{};
        bool hasLastSecurityKey_{};
        bool hasPreviousSecurityKey_{};
    };
}
