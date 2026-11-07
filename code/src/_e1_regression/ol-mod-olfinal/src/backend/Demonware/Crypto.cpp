#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <bcrypt.h>

#include "Crypto.hpp"

#include <algorithm>
#include <stdexcept>
#include <string_view>

namespace
{
    using ByteVector = std::vector<std::uint8_t>;

    void requireSuccess(const NTSTATUS status, const char *operation)
    {
        if (status < 0)
            throw std::runtime_error(operation);
    }

    ULONG propertyU32(BCRYPT_HANDLE handle, const wchar_t *name)
    {
        ULONG value{};
        ULONG written{};
        requireSuccess(BCryptGetProperty(
            handle,
            name,
            reinterpret_cast<PUCHAR>(&value),
            sizeof(value),
            &written,
            0), "BCryptGetProperty failed");
        return value;
    }

    ByteVector hash(
        const wchar_t *algorithm,
        const std::span<const std::uint8_t> data,
        const std::span<const std::uint8_t> key)
    {
        BCRYPT_ALG_HANDLE provider{};
        const auto flags = key.empty() ? 0UL : BCRYPT_ALG_HANDLE_HMAC_FLAG;
        requireSuccess(BCryptOpenAlgorithmProvider(&provider, algorithm, nullptr, flags),
            "BCryptOpenAlgorithmProvider failed");

        try
        {
            ByteVector object(propertyU32(provider, BCRYPT_OBJECT_LENGTH));
            ByteVector output(propertyU32(provider, BCRYPT_HASH_LENGTH));
            BCRYPT_HASH_HANDLE handle{};
            requireSuccess(BCryptCreateHash(
                provider,
                &handle,
                object.data(),
                static_cast<ULONG>(object.size()),
                key.empty() ? nullptr : const_cast<PUCHAR>(key.data()),
                static_cast<ULONG>(key.size()),
                0), "BCryptCreateHash failed");
            try
            {
                if (!data.empty())
                {
                    requireSuccess(BCryptHashData(
                        handle,
                        const_cast<PUCHAR>(data.data()),
                        static_cast<ULONG>(data.size()),
                        0), "BCryptHashData failed");
                }
                requireSuccess(BCryptFinishHash(
                    handle,
                    output.data(),
                    static_cast<ULONG>(output.size()),
                    0), "BCryptFinishHash failed");
            }
            catch (...)
            {
                BCryptDestroyHash(handle);
                throw;
            }
            BCryptDestroyHash(handle);
            BCryptCloseAlgorithmProvider(provider, 0);
            return output;
        }
        catch (...)
        {
            BCryptCloseAlgorithmProvider(provider, 0);
            throw;
        }
    }

    ByteVector aesCbc(
        const bool encrypt,
        const std::span<const std::uint8_t> input,
        const std::span<const std::uint8_t> key,
        const std::span<const std::uint8_t> iv)
    {
        if (key.size() != 16 || iv.size() != 16 || input.empty() || input.size() % 16 != 0)
            throw std::invalid_argument("AES-128-CBC requires a non-empty, block-aligned input and 16-byte key/IV");

        BCRYPT_ALG_HANDLE provider{};
        requireSuccess(BCryptOpenAlgorithmProvider(&provider, BCRYPT_AES_ALGORITHM, nullptr, 0),
            "BCryptOpenAlgorithmProvider(AES) failed");
        try
        {
            requireSuccess(BCryptSetProperty(
                provider,
                BCRYPT_CHAINING_MODE,
                reinterpret_cast<PUCHAR>(const_cast<wchar_t *>(BCRYPT_CHAIN_MODE_CBC)),
                sizeof(BCRYPT_CHAIN_MODE_CBC),
                0), "BCryptSetProperty(CBC) failed");

            ByteVector object(propertyU32(provider, BCRYPT_OBJECT_LENGTH));
            BCRYPT_KEY_HANDLE handle{};
            requireSuccess(BCryptGenerateSymmetricKey(
                provider,
                &handle,
                object.data(),
                static_cast<ULONG>(object.size()),
                const_cast<PUCHAR>(key.data()),
                static_cast<ULONG>(key.size()),
                0), "BCryptGenerateSymmetricKey failed");
            try
            {
                ByteVector mutableIv(iv.begin(), iv.end());
                ByteVector output(input.size());
                ULONG written{};
                const auto status = encrypt
                    ? BCryptEncrypt(handle, const_cast<PUCHAR>(input.data()), static_cast<ULONG>(input.size()),
                        nullptr, mutableIv.data(), static_cast<ULONG>(mutableIv.size()), output.data(),
                        static_cast<ULONG>(output.size()), &written, 0)
                    : BCryptDecrypt(handle, const_cast<PUCHAR>(input.data()), static_cast<ULONG>(input.size()),
                        nullptr, mutableIv.data(), static_cast<ULONG>(mutableIv.size()), output.data(),
                        static_cast<ULONG>(output.size()), &written, 0);
                requireSuccess(status, encrypt ? "BCryptEncrypt failed" : "BCryptDecrypt failed");
                output.resize(written);
                BCryptDestroyKey(handle);
                BCryptCloseAlgorithmProvider(provider, 0);
                return output;
            }
            catch (...)
            {
                BCryptDestroyKey(handle);
                throw;
            }
        }
        catch (...)
        {
            BCryptCloseAlgorithmProvider(provider, 0);
            throw;
        }
    }

    ByteVector expandKey(
        const std::span<const std::uint8_t> secret,
        const std::string_view label,
        const std::size_t size)
    {
        ByteVector output;
        ByteVector previous;
        std::uint8_t counter = 1;
        while (output.size() < size)
        {
            ByteVector input;
            input.reserve(previous.size() + label.size() + 1);
            input.insert(input.end(), previous.begin(), previous.end());
            input.insert(input.end(), label.begin(), label.end());
            input.push_back(counter++);
            previous = AlwaysofflineRe::Demonware::hmacSha1(input, secret);
            output.insert(output.end(), previous.begin(), previous.end());
        }
        output.resize(size);
        return output;
    }
}

namespace AlwaysofflineRe::Demonware
{
    std::vector<std::uint8_t> sha1(const std::span<const std::uint8_t> data)
    {
        return hash(BCRYPT_SHA1_ALGORITHM, data, {});
    }

    std::vector<std::uint8_t> md5(const std::span<const std::uint8_t> data)
    {
        return hash(BCRYPT_MD5_ALGORITHM, data, {});
    }

    std::vector<std::uint8_t> hmacSha1(
        const std::span<const std::uint8_t> data,
        const std::span<const std::uint8_t> key)
    {
        if (key.empty())
            throw std::invalid_argument("HMAC-SHA1 requires a key");
        return hash(BCRYPT_SHA1_ALGORITHM, data, key);
    }

    SessionKeys deriveSessionKeys(
        const std::span<const std::uint8_t> sessionKey,
        const std::span<const std::uint8_t> handshakeTranscript)
    {
        if (sessionKey.size() != 24)
            throw std::invalid_argument("DW session key must be 24 bytes");

        const auto transcriptHash = sha1(handshakeTranscript);
        const auto secret = hmacSha1(sessionKey, transcriptHash);
        const auto challenge = expandKey(secret, "CLIENTCHAL", 16);
        const auto data = expandKey(secret, "BDDATA", 72);

        SessionKeys result;
        std::copy_n(challenge.begin() + 8, result.responseId.size(), result.responseId.begin());
        std::copy_n(data.begin(), result.requestHmac.size(), result.requestHmac.begin());
        std::copy_n(data.begin() + 20, result.responseHmac.size(), result.responseHmac.begin());
        std::copy_n(data.begin() + 40, result.decrypt.size(), result.decrypt.begin());
        std::copy_n(data.begin() + 56, result.encrypt.size(), result.encrypt.begin());
        return result;
    }

    std::vector<std::uint8_t> aesCbcEncrypt(
        const std::span<const std::uint8_t> plaintext,
        const std::span<const std::uint8_t> key,
        const std::span<const std::uint8_t> iv)
    {
        return aesCbc(true, plaintext, key, iv);
    }

    std::vector<std::uint8_t> aesCbcDecrypt(
        const std::span<const std::uint8_t> ciphertext,
        const std::span<const std::uint8_t> key,
        const std::span<const std::uint8_t> iv)
    {
        return aesCbc(false, ciphertext, key, iv);
    }

    void fillRandom(const std::span<std::uint8_t> output)
    {
        if (!output.empty())
        {
            requireSuccess(BCryptGenRandom(
                nullptr,
                output.data(),
                static_cast<ULONG>(output.size()),
                BCRYPT_USE_SYSTEM_PREFERRED_RNG), "BCryptGenRandom failed");
        }
    }
}
