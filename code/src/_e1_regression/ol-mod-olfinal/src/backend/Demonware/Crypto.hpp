#pragma once

#include <array>
#include <cstdint>
#include <span>
#include <vector>

namespace AlwaysofflineRe::Demonware
{
    struct SessionKeys
    {
        std::array<std::uint8_t, 8> responseId{};
        std::array<std::uint8_t, 20> requestHmac{};
        std::array<std::uint8_t, 20> responseHmac{};
        std::array<std::uint8_t, 16> decrypt{};
        std::array<std::uint8_t, 16> encrypt{};
    };

    [[nodiscard]] std::vector<std::uint8_t> sha1(std::span<const std::uint8_t> data);
    [[nodiscard]] std::vector<std::uint8_t> md5(std::span<const std::uint8_t> data);
    [[nodiscard]] std::vector<std::uint8_t> hmacSha1(
        std::span<const std::uint8_t> data,
        std::span<const std::uint8_t> key);
    [[nodiscard]] SessionKeys deriveSessionKeys(
        std::span<const std::uint8_t> sessionKey,
        std::span<const std::uint8_t> handshakeTranscript);
    [[nodiscard]] std::vector<std::uint8_t> aesCbcEncrypt(
        std::span<const std::uint8_t> plaintext,
        std::span<const std::uint8_t> key,
        std::span<const std::uint8_t> iv);
    [[nodiscard]] std::vector<std::uint8_t> aesCbcDecrypt(
        std::span<const std::uint8_t> ciphertext,
        std::span<const std::uint8_t> key,
        std::span<const std::uint8_t> iv);
    void fillRandom(std::span<std::uint8_t> output);
}
