#pragma once

#include "AuthSession.hpp"
#include "ServiceRegistry.hpp"

#include <filesystem>
#include <optional>
#include <span>
#include <string_view>
#include <vector>

namespace AlwaysofflineRe::Demonware
{
    class Profiles2Service
    {
    public:
        explicit Profiles2Service(
            AuthSession &session,
            std::filesystem::path assetRoot = "./Ayria/Assets/Alwaysoffline");

        void registerTasks(ServiceRegistry &registry) const;

    private:
        [[nodiscard]] ServiceResponse getPublicInfos(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse getPrivateInfo(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse getPrivateInfoByUserId(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse setPublicInfo(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse setPublicInfoByUserId(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse setPrivateInfo(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse setPrivateInfoByUserId(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse deleteProfile(const ServiceRequest &request) const;
        [[nodiscard]] std::filesystem::path profilePath(
            std::uint64_t userId, std::string_view filename) const;
        [[nodiscard]] std::optional<std::vector<std::uint8_t>> loadProfile(
            std::uint64_t userId, std::string_view filename) const;
        [[nodiscard]] bool saveProfile(
            std::uint64_t userId, std::string_view filename,
            std::span<const std::uint8_t> profile) const;
        [[nodiscard]] static std::optional<std::vector<std::uint8_t>> stripOptionalUserId(
            std::span<const std::uint8_t> payload);

        AuthSession &session_;
        std::filesystem::path assetRoot_;
    };
}
