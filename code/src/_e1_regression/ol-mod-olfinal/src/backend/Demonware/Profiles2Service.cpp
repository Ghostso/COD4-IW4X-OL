#include "Profiles2Service.hpp"

#include "ByteBuffer.hpp"

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>

#include <algorithm>
#include <array>
#include <charconv>
#include <fstream>
#include <iterator>
#include <utility>

namespace
{
    std::string userIdDirectory(const std::uint64_t userId)
    {
        std::array<char, 16> buffer{};
        const auto result = std::to_chars(buffer.data(), buffer.data() + buffer.size(), userId, 16);
        if (result.ec != std::errc{})
            return {};
        std::string value(buffer.data(), result.ptr);
        std::transform(value.begin(), value.end(), value.begin(), [](const unsigned char character)
        {
            return character >= 'a' && character <= 'f'
                ? static_cast<char>(character - 'a' + 'A')
                : static_cast<char>(character);
        });
        return value;
    }
}

namespace AlwaysofflineRe::Demonware
{
    Profiles2Service::Profiles2Service(AuthSession &session, std::filesystem::path assetRoot)
        : session_(session), assetRoot_(std::move(assetRoot))
    {
    }

    void Profiles2Service::registerTasks(ServiceRegistry &registry) const
    {
        registry.registerTask(0x08, 1, "Profiles2::getPublicInfos", [this](const auto &request)
        {
            return getPublicInfos(request);
        });
        registry.registerTask(0x08, 2, "Profiles2::getPrivateInfo", [this](const auto &request)
        {
            return getPrivateInfo(request);
        });
        registry.registerTask(0x08, 3, "Profiles2::setPublicInfo", [this](const auto &request)
        {
            return setPublicInfo(request);
        });
        registry.registerTask(0x08, 4, "Profiles2::setPrivateInfo", [this](const auto &request)
        {
            return setPrivateInfo(request);
        });
        registry.registerTask(0x08, 5, "Profiles2::deleteProfile", [this](const auto &request)
        {
            return deleteProfile(request);
        });
        registry.registerTask(0x08, 6, "Profiles2::setPrivateInfoByUserID", [this](const auto &request)
        {
            return setPrivateInfoByUserId(request);
        });
        registry.registerTask(0x08, 7, "Profiles2::getPrivateInfoByUserID", [this](const auto &request)
        {
            return getPrivateInfoByUserId(request);
        });
        registry.registerTask(0x08, 8, "Profiles2::setPublicInfoByUserID", [this](const auto &request)
        {
            return setPublicInfoByUserId(request);
        });
    }

    ServiceResponse Profiles2Service::getPublicInfos(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        ServiceResponse response{ .task = request.task };
        const auto identity = session_.snapshot();
        while (!input.empty() && input.remaining().front() == 0x0A)
        {
            std::uint64_t userId{};
            if (!input.readU64(userId))
                return ServiceResponse{ .error = 800, .task = request.task };
            if (userId != identity.userId)
                continue;

            const auto profile = loadProfile(userId, "Publicprofile");
            if (!profile)
                return ServiceResponse{ .error = 800, .task = request.task };

            ByteBuffer object;
            object.writeU64(userId);
            object.writeRaw(*profile);
            response.objects.push_back(object.data());
        }
        return response;
    }

    ServiceResponse Profiles2Service::getPrivateInfo(const ServiceRequest &request) const
    {
        // CODREF: the current out.exe startup path treats both error 800 and a
        // non-empty task-2 private profile as fatal.  The captured live contract
        // is an empty successful reply; task 7 remains the explicit by-user read.
        return ServiceResponse{ .task = request.task };
    }

    ServiceResponse Profiles2Service::setPublicInfo(const ServiceRequest &request) const
    {
        const auto profile = stripOptionalUserId(request.payload);
        if (!profile || profile->empty() ||
            !saveProfile(session_.snapshot().userId, "Publicprofile", *profile))
            return ServiceResponse{ .error = 1000, .task = request.task };
        return ServiceResponse{ .task = request.task };
    }

    ServiceResponse Profiles2Service::setPublicInfoByUserId(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint64_t userId{};
        if (!input.readU64(userId) || input.empty() || !input.valid() ||
            !saveProfile(userId, "Publicprofile", input.remaining()))
            return ServiceResponse{ .error = 1000, .task = request.task };
        return ServiceResponse{ .task = request.task };
    }

    ServiceResponse Profiles2Service::setPrivateInfo(const ServiceRequest &request) const
    {
        const auto profile = stripOptionalUserId(request.payload);
        if (!profile || profile->empty() ||
            !saveProfile(session_.snapshot().userId, "Privateprofile", *profile))
            return ServiceResponse{ .error = 1000, .task = request.task };
        return ServiceResponse{ .task = request.task };
    }

    ServiceResponse Profiles2Service::setPrivateInfoByUserId(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint64_t userId{};
        if (!input.readU64(userId) || input.empty() || !input.valid() ||
            !saveProfile(userId, "Privateprofile", input.remaining()))
            return ServiceResponse{ .error = 1000, .task = request.task };
        return ServiceResponse{ .task = request.task };
    }

    ServiceResponse Profiles2Service::getPrivateInfoByUserId(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint64_t userId{};
        if (!input.readU64(userId) || !input.empty() || !input.valid())
            return ServiceResponse{ .error = 800, .task = request.task };

        const auto profile = loadProfile(userId, "Privateprofile");
        if (!profile || profile->empty())
            return ServiceResponse{ .error = 800, .task = request.task };

        ByteBuffer object;
        object.writeU64(userId);
        object.writeRaw(*profile);
        ServiceResponse response{ .task = request.task };
        response.objects.push_back(object.data());
        return response;
    }

    ServiceResponse Profiles2Service::deleteProfile(const ServiceRequest &request) const
    {
        const auto userId = session_.snapshot().userId;
        std::error_code error;
        std::filesystem::remove(profilePath(userId, "Publicprofile"), error);
        error.clear();
        std::filesystem::remove(profilePath(userId, "Privateprofile"), error);
        return ServiceResponse{ .task = request.task };
    }

    std::filesystem::path Profiles2Service::profilePath(
        const std::uint64_t userId, const std::string_view filename) const
    {
        const auto identity = session_.snapshot();
        return assetRoot_ / std::to_string(identity.titleId) / userIdDirectory(userId) / filename;
    }

    std::optional<std::vector<std::uint8_t>> Profiles2Service::loadProfile(
        const std::uint64_t userId, const std::string_view filename) const
    {
        const auto path = profilePath(userId, filename);
        std::error_code error;
        if (!std::filesystem::is_regular_file(path, error) || error)
            return std::nullopt;

        std::ifstream stream(path, std::ios::binary);
        if (!stream)
            return std::nullopt;
        return std::vector<std::uint8_t>(
            std::istreambuf_iterator<char>(stream),
            std::istreambuf_iterator<char>());
    }

    bool Profiles2Service::saveProfile(
        const std::uint64_t userId, const std::string_view filename,
        const std::span<const std::uint8_t> profile) const
    {
        const auto path = profilePath(userId, filename);

        std::error_code error;
        std::filesystem::create_directories(path.parent_path(), error);
        if (error)
            return false;
        auto temporary = path;
        temporary += L".writing";
        {
            std::ofstream stream(temporary, std::ios::binary | std::ios::trunc);
            if (!stream)
                return false;
            stream.write(reinterpret_cast<const char *>(profile.data()),
                static_cast<std::streamsize>(profile.size()));
            if (!stream)
            {
                stream.close();
                std::filesystem::remove(temporary, error);
                return false;
            }
        }
        if (!MoveFileExW(temporary.c_str(), path.c_str(),
            MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH))
        {
            std::filesystem::remove(temporary, error);
            return false;
        }
        return true;
    }

    std::optional<std::vector<std::uint8_t>> Profiles2Service::stripOptionalUserId(
        const std::span<const std::uint8_t> payload)
    {
        if (payload.empty() || payload.front() != 0x0A)
            return std::vector<std::uint8_t>(payload.begin(), payload.end());

        ByteBuffer input(payload);
        std::uint64_t ignoredUserId{};
        if (!input.readU64(ignoredUserId))
            return std::nullopt;
        const auto remaining = input.remaining();
        return std::vector<std::uint8_t>(remaining.begin(), remaining.end());
    }
}
