#include "Friends2Service.hpp"

#include "ByteBuffer.hpp"

#include <array>
#include <string>
#include <string_view>

#include <openssl/evp.h>

namespace
{
    constexpr auto CodolPresence = []
    {
        std::array<std::uint8_t, 136> value{};
        value[28] = 0x6D;
        value[29] = 0x75;
        value[32] = 0x6B;
        value[33] = 0x75;
        value[36] = 0x6C;
        value[37] = 0x75;
        value[44] = 0x10;
        value[120] = 0x04;
        value[121] = 0x04;
        return value;
    }();

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
    Friends2Service::Friends2Service(AuthSession &session)
        : session_(session)
    {
    }

    void Friends2Service::registerTasks(ServiceRegistry &registry) const
    {
        registry.registerTask(0x09, 0x1A, "Friends2::getFriends", [this](const auto &request)
        {
            return getFriends(request);
        });
    }

    ServiceResponse Friends2Service::getFriends(const ServiceRequest &request) const
    {
        ByteBuffer input(request.payload);
        std::uint32_t limit{};
        if (!input.readU32(limit))
            return ServiceResponse{ .error = 1000, .task = request.task };

        std::uint32_t offset{};
        if (!input.empty() && input.remaining().front() == 0x08 && !input.readU32(offset))
            return ServiceResponse{ .error = 1000, .task = request.task };

        ServiceResponse response{ .task = request.task };
        if (limit == 0 || offset != 0)
            return response;

        const auto identity = session_.snapshot();
        ByteBuffer object;
        object.writeU64(identity.userId);
        object.writeString(base64(identity.username));
        object.writeU8(0);
        object.writeBool(true);
        object.writeBlob(CodolPresence);
        response.objects.push_back(object.data());
        return response;
    }
}
