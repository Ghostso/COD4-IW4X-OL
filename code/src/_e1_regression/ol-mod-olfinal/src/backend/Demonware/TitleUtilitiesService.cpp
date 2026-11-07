#include "TitleUtilitiesService.hpp"

#include "ByteBuffer.hpp"

#include <ctime>
#include <string>
#include <string_view>

#include <openssl/evp.h>

namespace
{
    std::string base64(const std::string_view input)
    {
        std::string output(4 * ((input.size() + 2) / 3), '\0');
        const auto size = EVP_EncodeBlock(
            reinterpret_cast<unsigned char *>(output.data()),
            reinterpret_cast<const unsigned char *>(input.data()),
            static_cast<int>(input.size()));
        if (size < 0)
            return {};
        output.resize(static_cast<std::size_t>(size));
        return output;
    }
}

namespace AlwaysofflineRe::Demonware
{
    TitleUtilitiesService::TitleUtilitiesService(AuthSession &session)
        : session_(session)
    {
    }

    void TitleUtilitiesService::registerTasks(ServiceRegistry &registry) const
    {
        registry.registerTask(0x0C, 6, "TitleUtilities2::getServerTime", [this](const auto &request)
        {
            return getServerTime(request);
        });
        registry.registerTask(0x0C, 9, "TitleUtilities2::task9", [this](const auto &request)
        {
            return task9(request);
        });
    }

    ServiceResponse TitleUtilitiesService::getServerTime(const ServiceRequest &request) const
    {
        ByteBuffer object;
        object.writeU32(static_cast<std::uint32_t>(std::time(nullptr)));
        return ServiceResponse{ .task = request.task, .objects = { object.data() } };
    }

    ServiceResponse TitleUtilitiesService::task9(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint64_t userId{};
        if (!input.readU64(userId) || !input.valid())
            return ServiceResponse{ .error = 1000, .task = request.task };

        ByteBuffer object;
        object.writeU64(userId);
        object.writeString(base64(session_.snapshot().username));
        return ServiceResponse{ .task = request.task, .objects = { object.data() } };
    }
}
