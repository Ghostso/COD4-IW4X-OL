#include "net_dtls_cod.hpp"

#include <algorithm>
#include <limits>
#include <stdexcept>

#include <openssl/crypto.h>
#include <openssl/bn.h>
#include <openssl/ec.h>
#include <openssl/evp.h>
#include <openssl/hmac.h>
#include <openssl/obj_mac.h>

namespace
{
    std::uint16_t readU16(
        const std::span<const std::uint8_t> data,
        const std::size_t offset)
    {
        return static_cast<std::uint16_t>(
            data[offset] | static_cast<std::uint16_t>(data[offset + 1]) << 8);
    }

    void appendU16(std::vector<std::uint8_t> &output, const std::uint16_t value)
    {
        output.push_back(static_cast<std::uint8_t>(value));
        output.push_back(static_cast<std::uint8_t>(value >> 8));
    }

    void appendU32(std::vector<std::uint8_t> &output, const std::uint32_t value)
    {
        output.push_back(static_cast<std::uint8_t>(value));
        output.push_back(static_cast<std::uint8_t>(value >> 8));
        output.push_back(static_cast<std::uint8_t>(value >> 16));
        output.push_back(static_cast<std::uint8_t>(value >> 24));
    }

    void appendIpv4(std::vector<std::uint8_t> &output, const std::uint32_t address)
    {
        output.push_back(static_cast<std::uint8_t>(address >> 24));
        output.push_back(static_cast<std::uint8_t>(address >> 16));
        output.push_back(static_cast<std::uint8_t>(address >> 8));
        output.push_back(static_cast<std::uint8_t>(address));
    }

    std::array<std::uint8_t, 20> sha1(const std::span<const std::uint8_t> input)
    {
        std::array<std::uint8_t, 20> output{};
        unsigned int size{};
        if (!EVP_Digest(
                input.data(),
                input.size(),
                output.data(),
                &size,
                EVP_sha1(),
                nullptr) ||
            size != output.size())
        {
            throw std::runtime_error("OpenSSL SHA-1 failed");
        }
        return output;
    }

    std::array<std::uint8_t, 20> hmacSha1(
        const std::span<const std::uint8_t> input,
        const std::span<const std::uint8_t> key)
    {
        std::array<std::uint8_t, 20> output{};
        unsigned int size{};
        if (!HMAC(
                EVP_sha1(),
                key.data(),
                static_cast<int>(key.size()),
                input.data(),
                input.size(),
                output.data(),
                &size) ||
            size != output.size())
        {
            throw std::runtime_error("OpenSSL HMAC-SHA1 failed");
        }
        return output;
    }

    std::vector<std::uint8_t> aesCtrLittleEndian(
        const std::span<const std::uint8_t> input,
        const std::span<const std::uint8_t, 16> key,
        const std::span<const std::uint8_t, 16> iv)
    {
        if (input.empty())
            return {};
        const auto blockCount = (input.size() + 15) / 16;
        std::vector<std::uint8_t> counters(blockCount * 16);
        std::array<std::uint8_t, 16> counter{};
        std::copy(iv.begin(), iv.end(), counter.begin());
        for (std::size_t block = 0; block < blockCount; ++block)
        {
            std::copy(counter.begin(), counter.end(), counters.begin() + block * 16);
            for (auto &byte : counter)
            {
                if (++byte != 0)
                    break;
            }
        }

        const auto context = EVP_CIPHER_CTX_new();
        if (!context)
            throw std::runtime_error("EVP_CIPHER_CTX_new failed");
        std::vector<std::uint8_t> stream(counters.size());
        int written{};
        int finalized{};
        const auto ok = EVP_EncryptInit_ex(context, EVP_aes_128_ecb(), nullptr, key.data(), nullptr) &&
            EVP_CIPHER_CTX_set_padding(context, 0) &&
            EVP_EncryptUpdate(
                context,
                stream.data(),
                &written,
                counters.data(),
                static_cast<int>(counters.size())) &&
            EVP_EncryptFinal_ex(context, stream.data() + written, &finalized);
        EVP_CIPHER_CTX_free(context);
        if (!ok || static_cast<std::size_t>(written + finalized) != stream.size())
            throw std::runtime_error("OpenSSL AES-128-ECB failed");

        std::vector<std::uint8_t> output(input.size());
        for (std::size_t index = 0; index < input.size(); ++index)
            output[index] = input[index] ^ stream[index];
        return output;
    }

    std::pair<std::span<const std::uint8_t>, std::size_t> readTlv(
        const std::span<const std::uint8_t> data,
        const std::size_t offset,
        const std::uint8_t expectedTag)
    {
        if (offset + 2 > data.size() || data[offset] != expectedTag || data[offset + 1] & 0x80)
            throw std::invalid_argument("invalid CODOL DTLS public-key TLV");
        const auto size = static_cast<std::size_t>(data[offset + 1]);
        const auto start = offset + 2;
        if (start + size > data.size())
            throw std::invalid_argument("truncated CODOL DTLS public-key TLV");
        return { data.subspan(start, size), start + size };
    }

    std::vector<std::uint8_t> encodeInteger(const BIGNUM *value)
    {
        std::array<std::uint8_t, 28> raw{};
        if (BN_bn2binpad(value, raw.data(), static_cast<int>(raw.size())) !=
            static_cast<int>(raw.size()))
            throw std::runtime_error("P-224 coordinate export failed");
        std::vector<std::uint8_t> encoded{ 0x02 };
        const auto leadingZero = (raw.front() & 0x80) != 0;
        encoded.push_back(static_cast<std::uint8_t>(raw.size() + leadingZero));
        if (leadingZero)
            encoded.push_back(0);
        encoded.insert(encoded.end(), raw.begin(), raw.end());
        return encoded;
    }
}

namespace CodolGameServer
{
    bool DtlsSessionConfig::configureFromDemonwareDescriptor(
        const std::span<const std::uint8_t> descriptor)
    {
        // Captured CODOL descriptors encode SecurityKey as a typed 16-byte blob.
        constexpr std::array<std::uint8_t, 6> marker{ 0x13, 0x08, 0x10, 0, 0, 0 };
        const auto found = std::search(descriptor.begin(), descriptor.end(), marker.begin(), marker.end());
        if (found == descriptor.end() ||
            static_cast<std::size_t>(descriptor.end() - found) < marker.size() + SecurityKeySize)
        {
            return false;
        }

        std::copy_n(found + marker.size(), SecurityKeySize, securityKey_.begin());
        configured_ = true;
        return true;
    }

    void DtlsSessionConfig::reset()
    {
        securityKey_.fill(0);
        configured_ = false;
    }

    bool DtlsSessionConfig::configured() const
    {
        return configured_;
    }

    const std::array<std::uint8_t, DtlsSessionConfig::SecurityKeySize> &
        DtlsSessionConfig::securityKey() const
    {
        return securityKey_;
    }

    DtlsSessionKeys DtlsSessionKeys::derive(
        const std::span<const std::uint8_t> sharedMaterial)
    {
        if (sharedMaterial.size() != 44)
            throw std::invalid_argument("CODOL DTLS shared material must be 44 bytes");
        return { .digest = sha1(sharedMaterial) };
    }

    std::array<std::uint8_t, 16> DtlsSessionKeys::aesKey() const
    {
        std::array<std::uint8_t, 16> result{};
        std::copy_n(digest.begin(), result.size(), result.begin());
        return result;
    }

    std::array<std::uint8_t, 24> DtlsSessionKeys::hmacKey() const
    {
        std::array<std::uint8_t, 24> result{};
        std::copy(digest.begin(), digest.end(), result.begin());
        return result;
    }

    std::array<std::uint8_t, 16> DtlsSessionKeys::iv(
        const std::uint16_t sequenceNumber,
        const std::uint16_t verificationTag) const
    {
        std::vector<std::uint8_t> seed;
        seed.reserve(6);
        appendU32(seed, sequenceNumber);
        appendU16(seed, verificationTag);
        const auto digestValue = sha1(seed);
        std::array<std::uint8_t, 16> result{};
        std::copy_n(digestValue.begin(), result.size(), result.begin());
        return result;
    }

    DtlsDataPacket DtlsDataPacket::parse(const std::span<const std::uint8_t> packet)
    {
        if (packet.size() < HeaderSize || packet[0] != PacketType || packet[1] != Version)
            throw std::invalid_argument("not a supported CODOL DTLS data packet");
        DtlsDataPacket result;
        result.verificationTag = readU16(packet, 2);
        result.sequenceNumber = readU16(packet, 4);
        std::copy_n(packet.begin() + 6, result.authenticator.size(), result.authenticator.begin());
        result.encryptedSize = readU16(packet, 14);
        result.payload.assign(packet.begin() + HeaderSize, packet.end());
        if (result.encryptedSize > result.payload.size())
            throw std::invalid_argument("CODOL DTLS encrypted prefix exceeds payload size");
        return result;
    }

    std::vector<std::uint8_t> DtlsDataPacket::authenticatedBytes() const
    {
        std::vector<std::uint8_t> output{ PacketType, Version };
        output.reserve(8 + payload.size());
        appendU16(output, verificationTag);
        appendU16(output, sequenceNumber);
        appendU16(output, encryptedSize);
        output.insert(output.end(), payload.begin(), payload.end());
        return output;
    }

    bool DtlsDataPacket::verify(const DtlsSessionKeys &keys) const
    {
        const auto expected = hmacSha1(authenticatedBytes(), keys.hmacKey());
        return CRYPTO_memcmp(expected.data(), authenticator.data(), authenticator.size()) == 0;
    }

    std::vector<std::uint8_t> DtlsDataPacket::decrypt(const DtlsSessionKeys &keys) const
    {
        if (!verify(keys))
            throw std::invalid_argument("CODOL DTLS authenticator mismatch");
        const auto key = keys.aesKey();
        const auto ivValue = keys.iv(sequenceNumber, verificationTag);
        auto output = aesCtrLittleEndian(
            std::span(payload).first(encryptedSize),
            key,
            ivValue);
        output.insert(output.end(), payload.begin() + encryptedSize, payload.end());
        return output;
    }

    std::vector<std::uint8_t> DtlsDataPacket::build(
        const std::span<const std::uint8_t> plaintext,
        const std::uint16_t verificationTag,
        const std::uint16_t sequenceNumber,
        const DtlsSessionKeys &keys)
    {
        if (plaintext.size() > std::numeric_limits<std::uint16_t>::max())
            throw std::invalid_argument("CODOL DTLS payload exceeds uint16 size");
        const auto key = keys.aesKey();
        const auto ivValue = keys.iv(sequenceNumber, verificationTag);
        DtlsDataPacket candidate{
            .verificationTag = verificationTag,
            .sequenceNumber = sequenceNumber,
            .encryptedSize = static_cast<std::uint16_t>(plaintext.size()),
            .payload = aesCtrLittleEndian(plaintext, key, ivValue),
        };
        const auto signature = hmacSha1(candidate.authenticatedBytes(), keys.hmacKey());
        std::copy_n(signature.begin(), candidate.authenticator.size(), candidate.authenticator.begin());

        std::vector<std::uint8_t> output{ PacketType, Version };
        output.reserve(HeaderSize + candidate.payload.size());
        appendU16(output, verificationTag);
        appendU16(output, sequenceNumber);
        output.insert(output.end(), candidate.authenticator.begin(), candidate.authenticator.end());
        appendU16(output, candidate.encryptedSize);
        output.insert(output.end(), candidate.payload.begin(), candidate.payload.end());
        return output;
    }

    DtlsInitPacket DtlsInitPacket::parse(const std::span<const std::uint8_t> packet)
    {
        if (packet.size() != 16 || packet[0] != 0x01 || packet[1] != 0x02)
            throw std::invalid_argument("not a supported CODOL DTLS init packet");
        DtlsInitPacket result{
            .verificationTag = readU16(packet, 2),
            .counter = readU16(packet, 4),
            .initTag = readU16(packet, 6),
        };
        std::copy_n(packet.begin() + 8, result.securityId.size(), result.securityId.begin());
        return result;
    }

    DtlsCookieEchoPacket DtlsCookieEchoPacket::parse(
        const std::span<const std::uint8_t> packet)
    {
        // THE PACKET SIZE FOLLOWS THE ADDRESS THE LOBBY ADVERTISED. A bdCommonAddr is 67 bytes on
        // the wire, but an older session record carried the 37-byte short form, and the client
        // echoes back whatever it was given -- so both 219 and 189 are real and the offsets after
        // the address move with it. Deriving them from the size keeps the captured 189-byte
        // fixture parsing while a live out.exe client's 219-byte echo also works.
        //
        // Getting this wrong is not a clean failure: at the short offsets the security id comes out
        // of the 00FF00FF0000 sentinel run and the ECC parse starts mid-sentinel, which surfaces as
        // "expected DER SEQUENCE" rather than as a length problem.
        constexpr std::size_t LongAddressSize = 67;
        constexpr std::size_t ShortAddressSize = 37;
        constexpr std::size_t AddressOffset = 44;
        constexpr std::size_t SecurityIdSize = 8;
        constexpr std::size_t PublicKeySize = 100;
        const auto addressSize =
            packet.size() == AddressOffset + LongAddressSize + SecurityIdSize + PublicKeySize
                ? LongAddressSize
                : ShortAddressSize;
        if (packet.size() != AddressOffset + addressSize + SecurityIdSize + PublicKeySize ||
            packet[0] != 0x03 || packet[1] != 0x02 ||
            packet[6] != 0x02 || packet[7] != 0x02)
        {
            throw std::invalid_argument("not a supported CODOL DTLS cookie echo packet");
        }
        DtlsCookieEchoPacket result{
            .verificationTag = readU16(packet, 2),
            .counter = readU16(packet, 4),
            .clientTag = readU16(packet, 8),
        };
        const auto securityIdOffset = AddressOffset + addressSize;
        std::copy_n(packet.begin() + AddressOffset, addressSize, result.commonAddress.begin());
        std::copy_n(packet.begin() + securityIdOffset, result.securityId.size(),
            result.securityId.begin());
        std::copy_n(packet.begin() + securityIdOffset + SecurityIdSize, result.publicKey.size(),
            result.publicKey.begin());
        return result;
    }

    struct DtlsKeyPair::Impl
    {
        EC_KEY *key{};

        ~Impl()
        {
            EC_KEY_free(key);
        }
    };

    DtlsKeyPair::DtlsKeyPair()
        : impl_(std::make_unique<Impl>())
    {
        impl_->key = EC_KEY_new_by_curve_name(NID_secp224r1);
        if (!impl_->key || EC_KEY_generate_key(impl_->key) != 1)
            throw std::runtime_error("CODOL P-224 key generation failed");
    }

    DtlsKeyPair::DtlsKeyPair(const std::span<const std::uint8_t> privateScalar)
        : impl_(std::make_unique<Impl>())
    {
        if (privateScalar.empty() || privateScalar.size() > 28)
            throw std::invalid_argument("CODOL P-224 private scalar must contain 1 to 28 bytes");
        impl_->key = EC_KEY_new_by_curve_name(NID_secp224r1);
        const auto scalar = BN_bin2bn(
            privateScalar.data(), static_cast<int>(privateScalar.size()), nullptr);
        const auto group = impl_->key ? EC_KEY_get0_group(impl_->key) : nullptr;
        const auto point = group ? EC_POINT_new(group) : nullptr;
        const auto context = BN_CTX_new();
        const auto ok = impl_->key && scalar && point && context && !BN_is_zero(scalar) &&
            EC_KEY_set_private_key(impl_->key, scalar) == 1 &&
            EC_POINT_mul(group, point, scalar, nullptr, nullptr, context) == 1 &&
            EC_KEY_set_public_key(impl_->key, point) == 1 &&
            EC_KEY_check_key(impl_->key) == 1;
        BN_CTX_free(context);
        EC_POINT_free(point);
        BN_free(scalar);
        if (!ok)
            throw std::runtime_error("CODOL P-224 private key import failed");
    }

    DtlsKeyPair::~DtlsKeyPair() = default;
    DtlsKeyPair::DtlsKeyPair(DtlsKeyPair &&) noexcept = default;
    DtlsKeyPair &DtlsKeyPair::operator=(DtlsKeyPair &&) noexcept = default;

    std::array<std::uint8_t, 100> DtlsKeyPair::publicKey() const
    {
        const auto group = EC_KEY_get0_group(impl_->key);
        const auto point = EC_KEY_get0_public_key(impl_->key);
        const auto x = BN_new();
        const auto y = BN_new();
        const auto context = BN_CTX_new();
        if (!group || !point || !x || !y || !context ||
            EC_POINT_get_affine_coordinates(group, point, x, y, context) != 1)
        {
            BN_CTX_free(context);
            BN_free(y);
            BN_free(x);
            throw std::runtime_error("CODOL P-224 public key export failed");
        }
        const auto encodedX = encodeInteger(x);
        const auto encodedY = encodeInteger(y);
        BN_CTX_free(context);
        BN_free(y);
        BN_free(x);

        std::vector<std::uint8_t> content{ 0x03, 0x02, 0x07, 0x00, 0x02, 0x01, 0x1C };
        content.insert(content.end(), encodedX.begin(), encodedX.end());
        content.insert(content.end(), encodedY.begin(), encodedY.end());
        if (content.size() > 98)
            throw std::runtime_error("CODOL P-224 public key exceeds 100-byte field");
        std::array<std::uint8_t, 100> output{};
        output[0] = 0x30;
        output[1] = static_cast<std::uint8_t>(content.size());
        std::copy(content.begin(), content.end(), output.begin() + 2);
        return output;
    }

    std::array<std::uint8_t, 44> DtlsKeyPair::sharedMaterial(
        const std::span<const std::uint8_t, 100> peerPublicKey,
        const std::span<const std::uint8_t, 16> securityKey) const
    {
        const auto [sequence, ignored] = readTlv(peerPublicKey, 0, 0x30);
        (void)ignored;
        auto [format, offset] = readTlv(sequence, 0, 0x03);
        if (format.size() != 2 || format[0] != 0x07 || format[1] != 0x00)
            throw std::invalid_argument("CODOL DTLS public key has an unknown format");
        auto [keySize, next] = readTlv(sequence, offset, 0x02);
        offset = next;
        if (keySize.size() != 1 || keySize[0] != 28)
            throw std::invalid_argument("CODOL DTLS public key is not P-224");
        auto [xBytes, afterX] = readTlv(sequence, offset, 0x02);
        auto [yBytes, afterY] = readTlv(sequence, afterX, 0x02);
        if (afterY != sequence.size() || xBytes.empty() || yBytes.empty())
            throw std::invalid_argument("CODOL DTLS public key coordinates are invalid");

        const auto group = EC_KEY_get0_group(impl_->key);
        const auto point = group ? EC_POINT_new(group) : nullptr;
        const auto x = BN_bin2bn(xBytes.data(), static_cast<int>(xBytes.size()), nullptr);
        const auto y = BN_bin2bn(yBytes.data(), static_cast<int>(yBytes.size()), nullptr);
        const auto context = BN_CTX_new();
        const auto valid = group && point && x && y && context &&
            EC_POINT_set_affine_coordinates(group, point, x, y, context) == 1 &&
            EC_POINT_is_on_curve(group, point, context) == 1;
        BN_CTX_free(context);
        BN_free(y);
        BN_free(x);
        if (!valid)
        {
            EC_POINT_free(point);
            throw std::invalid_argument("CODOL DTLS peer key is not on P-224");
        }

        std::array<std::uint8_t, 44> output{};
        const auto size = ECDH_compute_key(output.data(), 28, point, impl_->key, nullptr);
        EC_POINT_free(point);
        if (size != 28)
            throw std::runtime_error("CODOL P-224 ECDH failed");
        std::copy(securityKey.begin(), securityKey.end(), output.begin() + 28);
        return output;
    }

    std::vector<std::uint8_t> NET_DtlsNatIntroReply(
        const std::span<const std::uint8_t> packet)
    {
        if (packet.size() != 29 || packet[0] != 0x0D || readU16(packet, 1) < 2)
            return {};
        auto output = std::vector(packet.begin(), packet.end());
        output[0] = 0x0C;
        return output;
    }

    std::vector<std::uint8_t> NET_DtlsInitAck(
        const std::span<const std::uint8_t> packet,
        const PeerAddress peer,
        const std::uint16_t serverTag,
        const std::uint32_t timestamp)
    {
        if (!serverTag)
            throw std::invalid_argument("CODOL DTLS server tag must be non-zero");
        const auto init = DtlsInitPacket::parse(packet);
        std::vector<std::uint8_t> output{ 0x02, 0x02 };
        appendU16(output, init.initTag);
        appendU16(output, 0);
        appendU32(output, timestamp);
        appendU32(output, 0);
        appendU16(output, serverTag);
        appendU16(output, serverTag);
        appendU16(output, init.initTag);
        appendU16(output, 0);
        appendU16(output, 0);
        appendIpv4(output, peer.ipv4);
        appendU16(output, peer.port);
        output.insert(output.end(), init.securityId.begin(), init.securityId.end());
        return output;
    }

    std::vector<std::uint8_t> NET_DtlsCookieAck(
        const std::span<const std::uint8_t> packet,
        const std::span<const std::uint8_t, 100> serverPublicKey)
    {
        const auto echo = DtlsCookieEchoPacket::parse(packet);
        std::vector<std::uint8_t> output{ 0x04, 0x02 };
        appendU16(output, echo.clientTag);
        appendU16(output, 0);
        output.insert(output.end(), serverPublicKey.begin(), serverPublicKey.end());
        output.insert(output.end(), echo.securityId.begin(), echo.securityId.end());
        return output;
    }

    DtlsPeerSystem::DtlsPeerSystem(
        const std::size_t maxPeers,
        const std::uint32_t sessionLifetimeMilliseconds)
        : sessions_(maxPeers),
          sessionLifetimeMilliseconds_(sessionLifetimeMilliseconds)
    {
        if (!maxPeers)
            throw std::invalid_argument("DTLS transport must have at least one peer slot");
        if (!sessionLifetimeMilliseconds_)
            throw std::invalid_argument("DTLS session lifetime must be non-zero");
    }

    DtlsPacketResult DtlsPeerSystem::NET_DtlsPacket(
        const PeerAddress peer,
        const std::span<const std::uint8_t> packet,
        const std::span<const std::uint8_t, DtlsSessionConfig::SecurityKeySize> securityKey,
        const std::uint32_t nowMilliseconds,
        const std::uint32_t entropy)
    {
        if (packet.empty())
            return {};

        // CODOL may refresh ConfigureSession per native client. Keep the two
        // most recent descriptor keys so peers whose INIT raced that refresh
        // can still authenticate their first data packet.
        rememberSecurityKey(securityKey);

        expireSessions(nowMilliseconds);
        try
        {
            if (packet[0] == 0x0D)
            {
                auto reply = NET_DtlsNatIntroReply(packet);
                if (reply.empty())
                    return { .kind = DtlsPacketResultKind::Rejected, .reason = "invalid NAT intro" };
                return { .kind = DtlsPacketResultKind::Reply, .reply = std::move(reply) };
            }

            if (packet[0] == 0x01)
            {
                const auto init = DtlsInitPacket::parse(packet);
                auto *session = allocateSession(peer);
                if (!session)
                {
                    return {
                        .kind = DtlsPacketResultKind::Rejected,
                        .reason = "DTLS peer slots are full",
                    };
                }

                *session = {};
                session->valid = true;
                session->peer = peer;
                session->state = DtlsPeerState::CookieIssued;
                session->lastActivityTime = nowMilliseconds;
                session->clientTag = init.initTag;
                session->securityId = init.securityId;
                std::copy(securityKey.begin(), securityKey.end(), session->securityKey.begin());
                if (hasPreviousSecurityKey_ &&
                    !std::equal(previousSecurityKey_.begin(), previousSecurityKey_.end(),
                                session->securityKey.begin()))
                {
                    session->previousSecurityKey = previousSecurityKey_;
                    session->hasPreviousSecurityKey = true;
                }
                session->serverTag = static_cast<std::uint16_t>(entropy ^ (entropy >> 16));
                if (!session->serverTag)
                    session->serverTag = 1;
                session->keyPair.emplace();
                return {
                    .kind = DtlsPacketResultKind::Reply,
                    .reply = NET_DtlsInitAck(
                        packet, peer, session->serverTag, nowMilliseconds),
                };
            }

            if (packet[0] == 0x03)
            {
                auto *session = findSession(peer);
                if (!session || session->state != DtlsPeerState::CookieIssued ||
                    !session->keyPair)
                {
                    return {
                        .kind = DtlsPacketResultKind::Rejected,
                        .reason = "DTLS cookie echo has no pending INIT",
                    };
                }

                const auto echo = DtlsCookieEchoPacket::parse(packet);
                if (echo.verificationTag != session->serverTag ||
                    echo.clientTag != session->clientTag ||
                    echo.securityId != session->securityId)
                {
                    return {
                        .kind = DtlsPacketResultKind::Rejected,
                        .reason = "DTLS cookie echo does not match its INIT",
                    };
                }

                const auto sharedMaterial = session->keyPair->sharedMaterial(
                    echo.publicKey, session->securityKey);
                session->keys = DtlsSessionKeys::derive(sharedMaterial);
                if (session->hasPreviousSecurityKey)
                {
                    const auto previousMaterial = session->keyPair->sharedMaterial(
                        echo.publicKey, session->previousSecurityKey);
                    session->previousKeys = DtlsSessionKeys::derive(previousMaterial);
                }
                session->state = DtlsPeerState::Established;
                session->lastActivityTime = nowMilliseconds;
                session->nextServerSequence = 1;
                session->clientSequenceReceived = false;
                return {
                    .kind = DtlsPacketResultKind::Reply,
                    .reply = NET_DtlsCookieAck(packet, session->keyPair->publicKey()),
                };
            }

            if (packet[0] == DtlsDataPacket::PacketType)
            {
                auto *session = findSession(peer);
                if (!session || session->state != DtlsPeerState::Established || !session->keys)
                {
                    return {
                        .kind = DtlsPacketResultKind::Rejected,
                        .reason = "DTLS data arrived before key agreement",
                    };
                }

                const auto data = DtlsDataPacket::parse(packet);
                if (data.verificationTag != session->serverTag)
                {
                    return {
                        .kind = DtlsPacketResultKind::Rejected,
                        .reason = "DTLS data authentication failed",
                    };
                }
                if (!data.verify(*session->keys))
                {
                    if (!session->previousKeys || !data.verify(*session->previousKeys))
                    {
                        return {
                            .kind = DtlsPacketResultKind::Rejected,
                            .reason = "DTLS data authentication failed",
                        };
                    }
                    session->keys = std::move(session->previousKeys);
                    session->previousKeys.reset();
                    session->usingPreviousKeys = true;
                }
                if (session->clientSequenceReceived)
                {
                    const auto delta = static_cast<std::uint16_t>(
                        data.sequenceNumber - session->lastClientSequence);
                    if (!delta || delta >= 0x8000)
                    {
                        return {
                            .kind = DtlsPacketResultKind::Rejected,
                            .reason = "DTLS data sequence was replayed or stale",
                        };
                    }
                }

                session->clientSequenceReceived = true;
                session->lastClientSequence = data.sequenceNumber;
                session->lastActivityTime = nowMilliseconds;
                return {
                    .kind = DtlsPacketResultKind::AuthenticatedData,
                    .plaintext = data.decrypt(*session->keys),
                };
            }
        }
        catch (const std::exception &error)
        {
            return { .kind = DtlsPacketResultKind::Rejected, .reason = error.what() };
        }

        return {};
    }

    std::vector<std::uint8_t> DtlsPeerSystem::NET_DtlsBuildData(
        const PeerAddress peer,
        const std::span<const std::uint8_t> plaintext)
    {
        auto *session = findSession(peer);
        if (!session || session->state != DtlsPeerState::Established || !session->keys)
            return {};
        const auto sequence = session->nextServerSequence++;
        return DtlsDataPacket::build(
            plaintext, session->clientTag, sequence, *session->keys);
    }

    void DtlsPeerSystem::rememberSecurityKey(
        const std::span<const std::uint8_t, DtlsSessionConfig::SecurityKeySize> securityKey)
    {
        if (hasLastSecurityKey_ &&
            std::equal(securityKey.begin(), securityKey.end(), lastSecurityKey_.begin()))
            return;
        if (hasLastSecurityKey_)
        {
            previousSecurityKey_ = lastSecurityKey_;
            hasPreviousSecurityKey_ = true;
        }
        std::copy(securityKey.begin(), securityKey.end(), lastSecurityKey_.begin());
        hasLastSecurityKey_ = true;
    }

    void DtlsPeerSystem::reset()
    {
        for (auto &session : sessions_)
            session = {};
    }

    DtlsPeerState DtlsPeerSystem::peerState(const PeerAddress peer) const
    {
        const auto *session = findSession(peer);
        return session ? session->state : DtlsPeerState::Empty;
    }

    std::size_t DtlsPeerSystem::sessionCount() const
    {
        return static_cast<std::size_t>(std::count_if(
            sessions_.begin(), sessions_.end(), [](const auto &session) {
                return session.valid;
            }));
    }

    void DtlsPeerSystem::expireSessions(const std::uint32_t nowMilliseconds)
    {
        for (auto &session : sessions_)
        {
            if (session.valid &&
                nowMilliseconds - session.lastActivityTime > sessionLifetimeMilliseconds_)
            {
                session = {};
            }
        }
    }

    DtlsPeerSystem::PeerSession *DtlsPeerSystem::findSession(const PeerAddress peer)
    {
        const auto found = std::find_if(
            sessions_.begin(), sessions_.end(), [peer](const auto &session) {
                return session.valid && session.peer == peer;
            });
        return found == sessions_.end() ? nullptr : &*found;
    }

    const DtlsPeerSystem::PeerSession *DtlsPeerSystem::findSession(
        const PeerAddress peer) const
    {
        const auto found = std::find_if(
            sessions_.begin(), sessions_.end(), [peer](const auto &session) {
                return session.valid && session.peer == peer;
            });
        return found == sessions_.end() ? nullptr : &*found;
    }

    DtlsPeerSystem::PeerSession *DtlsPeerSystem::allocateSession(const PeerAddress peer)
    {
        if (auto *existing = findSession(peer))
            return existing;
        const auto freeSlot = std::find_if(
            sessions_.begin(), sessions_.end(), [](const auto &session) {
                return !session.valid;
            });
        return freeSlot == sessions_.end() ? nullptr : &*freeSlot;
    }
}
