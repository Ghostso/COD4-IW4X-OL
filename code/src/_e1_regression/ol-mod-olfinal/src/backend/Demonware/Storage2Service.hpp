#pragma once

#include "AuthSession.hpp"
#include "ServiceRegistry.hpp"

#include <filesystem>
#include <optional>
#include <string>
#include <vector>

namespace AlwaysofflineRe::Demonware
{
    class Storage2Service
    {
    public:
        explicit Storage2Service(
            AuthSession &session,
            std::filesystem::path assetRoot = L"./Ayria/Assets/Alwaysoffline");

        void registerTasks(ServiceRegistry &registry);

    private:
        struct PublisherFile
        {
            std::string name;
            std::filesystem::path path;
            std::uint32_t modifiedTime{};
            std::vector<std::uint8_t> data;
        };

        [[nodiscard]] ServiceResponse listAllPublisherFiles(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse getPublisherFile(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse getFile(const ServiceRequest &request) const;
        [[nodiscard]] ServiceResponse uploadFile(const ServiceRequest &request) const;
        [[nodiscard]] std::filesystem::path serverDirectory() const;
        [[nodiscard]] std::optional<std::vector<std::uint8_t>> loadUserFile(
            std::uint64_t owner,
            const std::string &name) const;
        [[nodiscard]] bool saveUserFile(
            std::uint64_t owner,
            const std::string &name,
            std::span<const std::uint8_t> data) const;
        [[nodiscard]] std::optional<PublisherFile> loadPublisherFile(std::string name) const;
        [[nodiscard]] std::vector<PublisherFile> listPublisherFiles() const;
        void encodePublisherFile(
            const std::string &name,
            std::vector<std::uint8_t> &payload) const;

        AuthSession &session_;
        std::filesystem::path assetRoot_;
    };
}
