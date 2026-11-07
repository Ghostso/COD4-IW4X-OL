#include "LobbyProtocol.hpp"

#include <algorithm>
#include <array>
#include <optional>
#include <span>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string>

namespace
{
    constexpr std::size_t MaxFrameSize = 1024 * 1024;

    // Demonware bit order: LSB-first within each byte, same as the reader in
    // Auth3Protocol.cpp.
    class AuthInfoBitReader
    {
    public:
        explicit AuthInfoBitReader(const std::span<const std::uint8_t> data)
            : data_(data)
        {
        }

        bool skip(const std::size_t count)
        {
            if (position_ + count > data_.size() * 8)
                return false;
            position_ += count;
            return true;
        }

        bool readBytes(const std::span<std::uint8_t> output)
        {
            if (position_ + output.size() * 8 > data_.size() * 8)
                return false;
            for (auto &byte : output)
            {
                std::uint32_t value{};
                for (unsigned index = 0; index != 8; ++index)
                {
                    const auto bit =
                        (data_[(position_ + index) / 8] >> ((position_ + index) % 8)) & 1;
                    value |= static_cast<std::uint32_t>(bit) << index;
                }
                position_ += 8;
                byte = static_cast<std::uint8_t>(value);
            }
            return true;
        }

    private:
        std::span<const std::uint8_t> data_;
        std::size_t position_{};
    };

    // THE SESSION KEY IS IN THE CLIENT'S OWN AUTH FRAME. It is not minted here and it is
    // not looked up: the auth server issues a 128-byte server ticket whose first 24 bytes
    // are the key, and the client forwards that ticket verbatim. The C# reference
    // implementation this is ported from does exactly one line for it --
    // `var sessionKey = authInfoData[..24];` at LobbyServer/Client.cs:339 -- and its own
    // comment says the ticket is "minted and the client forwarded verbatim".
    //
    // Deriving the keys from this backend's AuthSession instead was the whole [100] bug:
    // with OLMOD_CLAIM_LOBBY=1 this backend owns the lobby while the C# AuthServer owns
    // auth, so that AuthSession is empty, deriveSessionKeys produced the wrong
    // decrypt/HMAC pair, and the client's first encrypted 0x86 threw in
    // processServiceMessage and dropped the connection. Two clients also get DIFFERENT
    // keys, so no single shared value could ever have worked.
    //
    // LAYOUT, from Shared/BitBuffer.cs. The buffer is constructed with
    // dataHasTypeCheckedBit=false, which prepends one bit and starts reading at bit 1, so
    // offsets are relative to authInfo's own bit 0 and TypeChecked starts FALSE:
    //
    //     serviceId   8 bits        untagged (TypeChecked false at construction)
    //     unknown     1 bit         untagged (the caller sets TypeChecked=false for it)
    //     titleId     5 + 32 bits   tagged   (TypeChecked set true first)
    //     ivSeed      5 + 32 bits   tagged
    //     authInfoData            1024 bits
    //
    // The tag is 5 bits because BitBufferDataType::MaxType is 0x20. That puts the data at
    // bit 83, which is NOT byte-aligned -- which is exactly why this needs a bit reader
    // and cannot be a byte offset eyeballed off a captured frame.
    constexpr std::size_t AuthInfoBytes = 139;
    constexpr std::size_t AuthInfoDataBytes = 128;
    constexpr std::size_t TypeTagBits = 5;

    std::optional<std::array<std::uint8_t, 24>> sessionKeyFromClientAuth(
        const std::span<const std::uint8_t> frame)
    {
        // frame is [u32 size][0xAB][0x82][authInfo][clientVerify]; the caller has already
        // checked the two type bytes.
        constexpr std::size_t AuthInfoOffset = 6;
        if (frame.size() < AuthInfoOffset + AuthInfoBytes)
            return std::nullopt;

        AuthInfoBitReader reader(frame.subspan(AuthInfoOffset, AuthInfoBytes));
        if (!reader.skip(8) ||                      // serviceId
            !reader.skip(1) ||                      // unknown bool
            !reader.skip(TypeTagBits + 32) ||       // titleId
            !reader.skip(TypeTagBits + 32))         // ivSeed
        {
            return std::nullopt;
        }

        std::array<std::uint8_t, AuthInfoDataBytes> data{};
        if (!reader.readBytes(data))
            return std::nullopt;

        std::array<std::uint8_t, 24> key{};
        std::copy_n(data.begin(), key.size(), key.begin());
        return key;
    }

    constexpr std::array<std::uint8_t, 24> DefaultSessionKey{
        'S', 'h', 'i', 'p', 'p', 'o', ' ', 'f', 'u', 'u', 't', 'e', ',', ' ', 'm', 'o',
        'f', 'u', '-', 'm', 'o', 'f', 'u', '!'
    };
    constexpr std::array<std::uint8_t, 26> ServerHeaderAck{
        0x16, 0x00, 0x00, 0x00, 0xAB, 0x81, 0xD2, 0x00, 0x00, 0x00,
        0x70, 0xE2, 0xFD, 0xC0, 0xB6, 0x6A, 0x34, 0x92,
        0x71, 0x79, 0xFC, 0xB0, 0x85, 0x93, 0x16, 0x51,
    };

    std::uint32_t readU32(const std::span<const std::uint8_t> data, const std::size_t offset)
    {
        if (offset + 4 > data.size())
            throw std::runtime_error("truncated uint32");
        return static_cast<std::uint32_t>(data[offset]) |
            (static_cast<std::uint32_t>(data[offset + 1]) << 8) |
            (static_cast<std::uint32_t>(data[offset + 2]) << 16) |
            (static_cast<std::uint32_t>(data[offset + 3]) << 24);
    }

    void appendU32(std::vector<std::uint8_t> &output, const std::uint32_t value)
    {
        for (unsigned int index = 0; index != 4; ++index)
            output.push_back(static_cast<std::uint8_t>(value >> (index * 8)));
    }

    bool constantTimeEqual(
        const std::span<const std::uint8_t> left,
        const std::span<const std::uint8_t> right)
    {
        if (left.size() != right.size())
            return false;
        std::uint8_t difference{};
        for (std::size_t index = 0; index != left.size(); ++index)
            difference |= left[index] ^ right[index];
        return difference == 0;
    }

    std::string hexString(const std::span<const std::uint8_t> data)
    {
        constexpr std::string_view Digits = "0123456789ABCDEF";
        std::string result(data.size() * 2, '0');
        for (std::size_t index = 0; index != data.size(); ++index)
        {
            result[index * 2] = Digits[data[index] >> 4];
            result[index * 2 + 1] = Digits[data[index] & 0x0F];
        }
        return result;
    }
}

namespace AlwaysofflineRe::Demonware
{
    std::vector<std::uint8_t> encodeEncryptedLobbyMessage(
        const std::span<const std::uint8_t> payload,
        const std::span<const std::uint8_t> aesKey,
        const std::span<const std::uint8_t> hmacKey,
        const std::uint32_t sequence,
        const std::span<const std::uint8_t> iv,
        const std::uint8_t messageType)
    {
        if (payload.size() > std::numeric_limits<std::uint32_t>::max())
            throw std::invalid_argument("lobby payload is too large");

        std::vector<std::uint8_t> plaintext;
        plaintext.reserve(payload.size() + 20);
        appendU32(plaintext, 0);
        plaintext.push_back(messageType);
        plaintext.insert(plaintext.end(), payload.begin(), payload.end());
        plaintext.resize((plaintext.size() + 15) & ~std::size_t(15));
        const auto encodedSize = messageType == 0x86
            ? static_cast<std::uint32_t>(payload.size())
            : static_cast<std::uint32_t>(plaintext.size() - 4);
        for (unsigned int index = 0; index != 4; ++index)
            plaintext[index] = static_cast<std::uint8_t>(encodedSize >> (index * 8));

        const auto ciphertext = aesCbcEncrypt(plaintext, aesKey, iv);
        std::vector<std::uint8_t> frame;
        frame.reserve(34 + ciphertext.size());
        appendU32(frame, static_cast<std::uint32_t>(30 + ciphertext.size()));
        frame.push_back(0xAB);
        frame.push_back(0x85);
        appendU32(frame, sequence);
        frame.insert(frame.end(), iv.begin(), iv.end());
        frame.insert(frame.end(), ciphertext.begin(), ciphertext.end());
        const auto signature = hmacSha1(frame, hmacKey);
        frame.insert(frame.end(), signature.begin(), signature.begin() + 8);
        return frame;
    }

    DecodedLobbyMessage decodeEncryptedLobbyMessage(
        const std::span<const std::uint8_t> frame,
        const std::span<const std::uint8_t> aesKey,
        const std::span<const std::uint8_t> hmacKey)
    {
        if (frame.size() < 50 || readU32(frame, 0) + 4 != frame.size() || frame[4] != 0xAB || frame[5] != 0x85)
            throw std::runtime_error("invalid encrypted lobby frame");

        const auto signedSize = frame.size() - 8;
        const auto signature = hmacSha1(frame.first(signedSize), hmacKey);
        if (!constantTimeEqual(frame.last(8), std::span(signature).first(8)))
            throw std::runtime_error("lobby frame HMAC mismatch");

        const auto ciphertext = frame.subspan(26, frame.size() - 34);
        if (ciphertext.empty() || ciphertext.size() % 16 != 0)
            throw std::runtime_error("invalid lobby ciphertext length");
        const auto plaintext = aesCbcDecrypt(ciphertext, aesKey, frame.subspan(10, 16));
        const auto encodedSize = readU32(plaintext, 0);
        if (plaintext.size() < 5 || encodedSize > plaintext.size() - 4 ||
            (plaintext[4] != 0x86 && encodedSize == 0))
            throw std::runtime_error("invalid decrypted lobby payload");
        const auto messageType = plaintext[4];
        const auto payloadSize = messageType == 0x86 ? encodedSize : encodedSize - 1;

        return DecodedLobbyMessage{
            .sequence = readU32(frame, 6),
            .messageType = messageType,
            .payload = std::vector<std::uint8_t>(plaintext.begin() + 5, plaintext.begin() + 5 + payloadSize),
        };
    }

    LobbyProtocol::LobbyProtocol(ServiceRegistry &registry, Diagnostic diagnostic)
        : registry_(registry), diagnostic_(std::move(diagnostic))
    {
        sessionKey_ = DefaultSessionKey;
    }

    void LobbyProtocol::reset()
    {
        phase_ = LobbyPhase::clientHeader;
        keys_ = {};
        transcript_.clear();
        input_.clear();
        output_.clear();
        outgoingSequence_ = 0;
        std::scoped_lock lock(pushMutex_);
        queuedPushes_.clear();
    }

    void LobbyProtocol::setSessionKey(const std::span<const std::uint8_t> sessionKey)
    {
        if (sessionKey.size() != sessionKey_.size())
            throw std::invalid_argument("DW session key must be 24 bytes");
        std::copy(sessionKey.begin(), sessionKey.end(), sessionKey_.begin());
    }

    void LobbyProtocol::receive(const std::span<const std::uint8_t> data)
    {
        input_.insert(input_.end(), data.begin(), data.end());
        while (input_.size() >= 4)
        {
            const auto payloadSize = readU32(input_, 0);
            if (payloadSize > MaxFrameSize)
            {
                input_.clear();
                report("Rejected oversized LSG frame.");
                return;
            }
            // DW3's 0xC8 client header is a fixed 28-byte record. Its first
            // dword is a generation marker, unlike normal length-prefixed frames.
            const auto frameSize = phase_ == LobbyPhase::clientHeader && payloadSize == 0xC8
                ? std::size_t{ 28 }
                : static_cast<std::size_t>(payloadSize) + 4;
            if (input_.size() < frameSize)
                return;

            const std::vector<std::uint8_t> frame(input_.begin(), input_.begin() + frameSize);
            input_.erase(input_.begin(), input_.begin() + frameSize);
            try
            {
                processFrame(frame);
            }
            catch (const std::exception &error)
            {
                report(std::string("Rejected LSG frame: ") + error.what());
            }
        }
    }

    std::vector<std::uint8_t> LobbyProtocol::takeOutput(const std::size_t limit)
    {
        flushQueuedPushes();
        const auto size = std::min(limit, output_.size());
        std::vector<std::uint8_t> result(output_.begin(), output_.begin() + size);
        output_.erase(output_.begin(), output_.begin() + size);
        return result;
    }

    void LobbyProtocol::queuePush(std::vector<std::uint8_t> payload, const std::uint8_t messageType)
    {
        std::scoped_lock lock(pushMutex_);
        queuedPushes_.push_back(DecodedLobbyMessage{
            .messageType = messageType,
            .payload = std::move(payload),
        });
    }

    void LobbyProtocol::processFrame(const std::span<const std::uint8_t> frame)
    {
        if (readU32(frame, 0) == 0)
        {
            constexpr std::array<std::uint8_t, 4> Zero{};
            emit(Zero);
            return;
        }

        switch (phase_)
        {
            case LobbyPhase::clientHeader: processClientHeader(frame); break;
            case LobbyPhase::clientAuth: processClientAuth(frame); break;
            case LobbyPhase::established: processServiceMessage(frame); break;
        }
    }

    void LobbyProtocol::processClientHeader(const std::span<const std::uint8_t> frame)
    {
        if (frame.size() != 28 || readU32(frame, 0) != 0xC8 || readU32(frame, 4) != 0xC8)
            throw std::runtime_error("expected 0xC8 client header ACK");

        transcript_.insert(transcript_.end(), frame.begin() + 8, frame.end());
        transcript_.insert(transcript_.end(), ServerHeaderAck.begin(), ServerHeaderAck.end());
        emit(ServerHeaderAck);
        phase_ = LobbyPhase::clientAuth;
        report("LSG_CAPTURE client_header=" + hexString(frame));
        report("Accepted LSG client header ACK.");
    }

    void LobbyProtocol::processClientAuth(const std::span<const std::uint8_t> frame)
    {
        if (frame.size() < 14 || frame[4] != 0xAB || frame[5] != 0x82)
            throw std::runtime_error("expected 0xAB82 client auth");
        transcript_.insert(transcript_.end(), frame.begin(), frame.end() - 8);
        // The client's own ticket wins. sessionKey_ stays the fallback so a stack that
        // really does mint the key here is unaffected.
        const auto forwarded = sessionKeyFromClientAuth(frame);
        if (forwarded)
        {
            sessionKey_ = *forwarded;
            report("LSG session key taken from the client ticket.");
        }
        else
        {
            report("LSG client ticket unreadable; falling back to the AuthSession key.");
        }
        keys_ = deriveSessionKeys(sessionKey_, transcript_);
        report("LSG_CAPTURE session_key=" + hexString(sessionKey_));
        report("LSG_CAPTURE client_auth=" + hexString(frame));
        report("LSG_CAPTURE transcript_sha1=" + hexString(sha1(transcript_)));
        report("LSG_CAPTURE response_id=" + hexString(keys_.responseId));
        report("LSG_CAPTURE request_hmac=" + hexString(keys_.requestHmac));
        report("LSG_CAPTURE response_hmac=" + hexString(keys_.responseHmac));
        report("LSG_CAPTURE decrypt_key=" + hexString(keys_.decrypt));
        report("LSG_CAPTURE encrypt_key=" + hexString(keys_.encrypt));

        std::vector<std::uint8_t> response;
        appendU32(response, 10);
        response.push_back(0xAB);
        response.push_back(0x83);
        response.insert(response.end(), keys_.responseId.begin(), keys_.responseId.end());
        emit(response);
        phase_ = LobbyPhase::established;
        report("Completed LSG key exchange.");
    }

    void LobbyProtocol::processServiceMessage(const std::span<const std::uint8_t> frame)
    {
        const auto decoded = decodeEncryptedLobbyMessage(frame, keys_.decrypt, keys_.requestHmac);
        if (decoded.messageType != 0x86)
            throw std::runtime_error("expected 0x86 service request");
        const auto request = parseServiceRequest(decoded.payload);
        if (!request)
            throw std::runtime_error("invalid protocol-3 service request");
        report("LSG_REQUEST sequence=" + std::to_string(decoded.sequence) +
            " service=" + std::to_string(request->service) +
            " task=" + std::to_string(request->task) +
            " payload=" + hexString(request->payload));

        // An unregistered task still gets an answer. See ServiceRegistry::acknowledgeUnhandled
        // for why silence is the wrong default; the log line stays so the coverage gap is
        // still visible, which is the only thing the old early return was buying.
        auto response = registry_.dispatch(*request);
        if (!response)
        {
            report("LSG_UNHANDLED service=" + std::to_string(request->service) +
                " task=" + std::to_string(request->task) +
                " -- acknowledging with an empty reply.");
            response = registry_.acknowledgeUnhandled(*request);
        }

        const auto payload = response->serialize();
        report("LSG_RESPONSE service=" + std::to_string(request->service) +
            " task=" + std::to_string(request->task) +
            " envelope=" + std::to_string(response->envelopeType) +
            " payload=" + hexString(payload));
        std::array<std::uint8_t, 16> iv{};
        fillRandom(iv);
        const auto encoded = encodeEncryptedLobbyMessage(
            payload,
            keys_.encrypt,
            keys_.responseHmac,
            ++outgoingSequence_,
            iv,
            response->envelopeType);
        emit(encoded);
    }

    void LobbyProtocol::flushQueuedPushes()
    {
        if (phase_ != LobbyPhase::established)
            return;

        std::deque<DecodedLobbyMessage> pushes;
        {
            std::scoped_lock lock(pushMutex_);
            pushes.swap(queuedPushes_);
        }
        for (const auto &push : pushes)
        {
            std::array<std::uint8_t, 16> iv{};
            fillRandom(iv);
            const auto encoded = encodeEncryptedLobbyMessage(
                push.payload,
                keys_.encrypt,
                keys_.responseHmac,
                ++outgoingSequence_,
                iv,
                push.messageType);
            emit(encoded);
            report("LSG_PUSH type=" + std::to_string(push.messageType) +
                " payload=" + hexString(push.payload));
        }
    }

    void LobbyProtocol::emit(const std::span<const std::uint8_t> data)
    {
        output_.insert(output_.end(), data.begin(), data.end());
    }

    void LobbyProtocol::report(const std::string_view message) const
    {
        if (diagnostic_)
            diagnostic_(message);
    }
}
