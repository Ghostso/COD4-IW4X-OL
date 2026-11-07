#include "Auth3Protocol.hpp"

#include <algorithm>
#include <array>
#include <charconv>
#include <chrono>
#include <cstring>
#include <limits>
#include <span>
#include <stdexcept>
#include <vector>

#pragma warning(push, 0)
#include <nlohmann/json.hpp>
#include <openssl/evp.h>
#pragma warning(pop)

namespace
{
    using ByteVector = std::vector<std::uint8_t>;
    using Json = nlohmann::json;

    constexpr std::array<std::uint8_t, 8> CodolTicketIv{
        0xA6, 0x80, 0x22, 0xCC, 0x34, 0xAC, 0xE6, 0x97,
    };

    std::string valueString(const Json &object, const char *name, const std::string_view fallback = {})
    {
        const auto iterator = object.find(name);
        if (iterator == object.end() || iterator->is_null())
            return std::string(fallback);
        if (iterator->is_string())
            return iterator->get<std::string>();
        if (iterator->is_number_integer() || iterator->is_number_unsigned())
            return iterator->dump();
        return std::string(fallback);
    }

    std::uint32_t parseU32(const std::string_view value, const int base, const std::uint32_t fallback)
    {
        std::uint32_t result{};
        const auto parsed = std::from_chars(value.data(), value.data() + value.size(), result, base);
        return parsed.ec == std::errc{} && parsed.ptr == value.data() + value.size() ? result : fallback;
    }

    void writeU32(ByteVector &output, const std::size_t offset, const std::uint32_t value)
    {
        for (unsigned int index = 0; index != 4; ++index)
            output[offset + index] = static_cast<std::uint8_t>(value >> (index * 8));
    }

    void writeU64(ByteVector &output, const std::size_t offset, const std::uint64_t value)
    {
        for (unsigned int index = 0; index != 8; ++index)
            output[offset + index] = static_cast<std::uint8_t>(value >> (index * 8));
    }

    std::uint64_t readU64(const std::span<const std::uint8_t> input, const std::size_t offset)
    {
        std::uint64_t value{};
        for (unsigned int index = 0; index != 8; ++index)
            value |= static_cast<std::uint64_t>(input[offset + index]) << (index * 8);
        return value;
    }

    class BitReader
    {
    public:
        BitReader(const std::span<const std::uint8_t> data, const std::size_t bitCount)
            : data_(data), bitCount_(std::min(bitCount, data.size() * 8))
        {
        }

        bool read(const unsigned int count, std::uint32_t &value)
        {
            if (count > 32 || position_ + count > bitCount_)
                return false;
            value = 0;
            for (unsigned int index = 0; index != count; ++index)
            {
                const auto bit = (data_[(position_ + index) / 8] >> ((position_ + index) % 8)) & 1;
                value |= static_cast<std::uint32_t>(bit) << index;
            }
            position_ += count;
            return true;
        }

        bool readBytes(const std::span<std::uint8_t> output)
        {
            for (auto &byte : output)
            {
                std::uint32_t value{};
                if (!read(8, value))
                    return false;
                byte = static_cast<std::uint8_t>(value);
            }
            return true;
        }

    private:
        std::span<const std::uint8_t> data_;
        std::size_t bitCount_{};
        std::size_t position_{};
    };

    std::string base64Encode(const std::span<const std::uint8_t> input)
    {
        std::string output(4 * ((input.size() + 2) / 3), '\0');
        const auto size = EVP_EncodeBlock(
            reinterpret_cast<unsigned char *>(output.data()),
            input.data(),
            static_cast<int>(input.size()));
        if (size < 0)
            throw std::runtime_error("base64 encoding failed");
        output.resize(static_cast<std::size_t>(size));
        return output;
    }

    ByteVector base64Decode(std::string value)
    {
        std::replace(value.begin(), value.end(), '-', '+');
        std::replace(value.begin(), value.end(), '_', '/');
        while (value.size() % 4 != 0)
            value.push_back('=');
        if (value.empty() || value.size() > static_cast<std::size_t>(std::numeric_limits<int>::max()))
            return {};

        ByteVector output((value.size() / 4) * 3);
        const auto size = EVP_DecodeBlock(
            output.data(),
            reinterpret_cast<const unsigned char *>(value.data()),
            static_cast<int>(value.size()));
        if (size < 0)
            return {};
        auto actual = static_cast<std::size_t>(size);
        if (!value.empty() && value.back() == '=') --actual;
        if (value.size() > 1 && value[value.size() - 2] == '=') --actual;
        output.resize(actual);
        return output;
    }

    ByteVector makeTicket(const AlwaysofflineRe::Demonware::AuthIdentity &identity)
    {
        ByteVector ticket(128);
        writeU32(ticket, 0, 0xEFBDADDE);
        ticket[4] = 0;
        writeU32(ticket, 5, identity.titleId);
        const auto now = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
        writeU32(ticket, 9, static_cast<std::uint32_t>(now));
        writeU32(ticket, 13, 0x7FFFFFFF);
        writeU64(ticket, 17, 0);
        writeU64(ticket, 25, identity.userId);
        const auto usernameSize = std::min<std::size_t>(17, identity.username.size());
        std::copy_n(identity.username.begin(), usernameSize, ticket.begin() + 33);
        std::copy(identity.sessionKey.begin(), identity.sessionKey.end(), ticket.begin() + 97);
        ticket[121] = '3';
        ticket[122] = 'U';
        ticket[123] = '"';
        return ticket;
    }

    ByteVector encryptTicket(
        const std::span<const std::uint8_t> ticket,
        const std::span<const std::uint8_t> sessionKey)
    {
        EVP_CIPHER_CTX *context = EVP_CIPHER_CTX_new();
        if (!context)
            throw std::runtime_error("EVP_CIPHER_CTX_new failed");
        ByteVector output(ticket.size() + EVP_MAX_BLOCK_LENGTH);
        int first{};
        int final{};
        const auto initialized = EVP_EncryptInit_ex(
            context,
            EVP_des_ede3_cbc(),
            nullptr,
            sessionKey.data(),
            CodolTicketIv.data());
        const auto padding = EVP_CIPHER_CTX_set_padding(context, 0);
        const auto updated = EVP_EncryptUpdate(
            context,
            output.data(),
            &first,
            ticket.data(),
            static_cast<int>(ticket.size()));
        const auto finished = EVP_EncryptFinal_ex(context, output.data() + first, &final);
        EVP_CIPHER_CTX_free(context);
        if (initialized != 1 || padding != 1 || updated != 1 || finished != 1)
            throw std::runtime_error("3DES ticket encryption failed");
        output.resize(static_cast<std::size_t>(first + final));
        return output;
    }

    Json extraData(const Json &request)
    {
        const auto parsed = Json::parse(valueString(request, "extra_data"), nullptr, false);
        return parsed.is_object() ? parsed : Json::object();
    }

    void consumeTask28CodoRequest(const Json &extra, AlwaysofflineRe::Demonware::AuthIdentity &identity)
    {
        const auto encoded = valueString(extra, "codo_request");
        const auto decoded = base64Decode(encoded);
        if (decoded.size() < 56)
            return;

        identity.userId = readU64(decoded, 6);
        const auto name = std::span(decoded).subspan(14, 16);
        const auto terminator = std::find(name.begin(), name.end(), std::uint8_t{});
        identity.username.assign(
            reinterpret_cast<const char *>(name.data()),
            static_cast<std::size_t>(std::distance(name.begin(), terminator)));
        std::copy_n(decoded.begin() + 32, identity.sessionKey.size(), identity.sessionKey.begin());
    }

    void consumeTask32CodoRequest(const Json &extra, AlwaysofflineRe::Demonware::AuthIdentity &identity)
    {
        const auto decoded = base64Decode(valueString(extra, "codo_request"));
        const auto bitCount = parseU32(
            valueString(extra, "codo_request_size_bits"),
            10,
            static_cast<std::uint32_t>(decoded.size() * 8));
        BitReader bits(decoded, bitCount);
        std::uint32_t typed{};
        if (!bits.read(1, typed))
            return;

        std::uint32_t length{};
        if (typed != 0)
        {
            std::uint32_t type{};
            if (!bits.read(5, type) || type == 20 || type != 6)
                return;
        }
        if (!bits.read(16, length) || length > decoded.size())
            return;

        ByteVector value(length);
        if (!bits.readBytes(value))
            return;
        identity.sessionKey.fill(0);
        std::copy_n(value.begin(), std::min(value.size(), identity.sessionKey.size()), identity.sessionKey.begin());
    }
}

namespace AlwaysofflineRe::Demonware
{
    Auth3Protocol::Auth3Protocol(
        AuthSession &session,
        PlayerIdentityStore *identityStore)
        : session_(session), identityStore_(identityStore)
    {
    }

    Auth3Result Auth3Protocol::authenticate(const std::string_view requestJson)
    {
        const auto request = Json::parse(requestJson, nullptr, false);
        if (!request.is_object())
            throw std::runtime_error("invalid Auth3 JSON request");

        auto identity = session_.snapshot();
        const auto configuredUsername = identity.username;
        identity.titleId = parseU32(valueString(request, "title_id"), 10, identity.titleId);
        const auto authTask = parseU32(valueString(request, "auth_task"), 10, 0);
        const auto ivSeed = parseU32(valueString(request, "iv_seed"), 10, 0);
        const auto requestIdentity = parseU32(valueString(request, "identity"), 16, 0);
        const auto extra = extraData(request);
        if (authTask == 28)
            consumeTask28CodoRequest(extra, identity);
        else if (authTask == 32)
            consumeTask32CodoRequest(extra, identity);
        identity.username = identityStore_
            ? identityStore_->resolveDisplayName(identity.titleId, identity.userId)
            : configuredUsername;
        session_.update(identity);

        auto ticket = makeTicket(identity);
        if (authTask == 28)
            ticket = encryptTicket(ticket, identity.sessionKey);
        if (ticket.size() != 128)
            throw std::runtime_error("Auth3 ticket must be exactly 128 bytes");

        const auto ticket64 = base64Encode(ticket);
        const std::string registerData = "Shippo fuute, mofu-mofu!";
        const std::string codoId = "Hedgehogscience0";
        constexpr std::string_view extendedData =
            "eyJfX3YiOjEsImFsZyI6IlJTQS1PQUVQIiwiZW5jIjoiQTEyOENCQy1IUzI1NiIsImtpZCI6InVtYl8xIn0=.AAA"
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=.AAAAAA"
            "AAAAAAAAAAAAAAAA==.W0VuY3J5cHRlZCBkYXRhLi4gbXVjaCBzZWNyZXQuLl0=.AAAAAAAAAAAAAAAAAAAAAA";
        Json extraData{
            { "encrypted_register_codoid_data", base64Encode(std::span(
                reinterpret_cast<const std::uint8_t *>(registerData.data()), registerData.size())) },
            { "encrypted_codoid", base64Encode(std::span(
                reinterpret_cast<const std::uint8_t *>(codoId.data()), codoId.size())) },
            { "extended_data", extendedData },
            { "time_to_live", 9999 },
            { "username", base64Encode(std::span(
                reinterpret_cast<const std::uint8_t *>(identity.username.data()), identity.username.size())) },
        };
        Json response{
            { "client_ticket", ticket64 },
            { "server_ticket", ticket64 },
            { "code", "700" },
            { "extra_data", extraData.dump() },
            { "auth_task", std::to_string(authTask + 1) },
            { "identity", [&]
                {
                    std::array<char, 9> buffer{};
                    const auto converted = std::to_chars(buffer.data(), buffer.data() + buffer.size(), requestIdentity, 16);
                    return std::string(buffer.data(), converted.ptr);
                }() },
            { "iv_seed", std::to_string(ivSeed) },
        };

        return Auth3Result{
            .titleId = identity.titleId,
            .authTask = authTask,
            .ivSeed = ivSeed,
            .userId = identity.userId,
            .username = identity.username,
            .json = response.dump(),
        };
    }

    std::string Auth3Protocol::httpResponse(const std::string_view json)
    {
        std::string response = "HTTP/1.1 200 OK\r\n";
        response += "Connection: keep-alive\r\n";
        response += "Content-Type: application/json\r\n";
        response += "Content-Length: " + std::to_string(json.size()) + "\r\n\r\n";
        response.append(json);
        return response;
    }
}
