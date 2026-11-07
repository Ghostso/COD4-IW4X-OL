#include "shared/LocalnetServer.hpp"

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <deque>
#include <mutex>
#include <string>

namespace
{
    class FixtureServer final : public IServer
    {
    public:
        bool onStreamread(void *data, std::uint32_t *size) override
        {
            std::lock_guard lock(mutex_);
            return popResponse(streamResponses_, data, size);
        }

        bool onStreamwrite(const void *data, const std::uint32_t size) override
        {
            if (!data)
                return false;
            const std::string request(static_cast<const char *>(data), size);
            std::lock_guard lock(mutex_);
            streamResponses_.push_back(request == "ping" ? "pong" : "unexpected");
            return true;
        }

        bool onPacketread(void *data, std::uint32_t *size) override
        {
            std::lock_guard lock(mutex_);
            return popResponse(packetResponses_, data, size);
        }

        bool onPacketwrite(
            const void *data,
            const std::uint32_t size,
            const Endpoints *endpoints) override
        {
            if (!data || !endpoints)
                return false;
            const std::string request(static_cast<const char *>(data), size);
            std::lock_guard lock(mutex_);
            packetResponses_.push_back(request == "ping" ? "pong" : "unexpected");
            return true;
        }

    private:
        static bool popResponse(
            std::deque<std::string> &responses,
            void *data,
            std::uint32_t *size)
        {
            if (!data || !size || responses.empty())
                return false;
            const auto response = std::move(responses.front());
            responses.pop_front();
            const auto copied = std::min<std::size_t>(*size, response.size());
            std::memcpy(data, response.data(), copied);
            *size = static_cast<std::uint32_t>(copied);
            return true;
        }

        std::mutex mutex_;
        std::deque<std::string> streamResponses_;
        std::deque<std::string> packetResponses_;
    };

    FixtureServer Server;
}

extern "C" __declspec(dllexport) IServer *__cdecl Createserver(const char *hostname)
{
    return hostname && std::strcmp(hostname, "fixture.local") == 0 ? &Server : nullptr;
}
