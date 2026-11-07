#pragma once

#include "ByteBuffer.hpp"

#include <cstdint>
#include <atomic>
#include <functional>
#include <map>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace AlwaysofflineRe::Demonware
{
    inline constexpr std::uint64_t OriginalTransactionPrefix = 0x797265766E6F4300ULL;

    struct ServiceRequest
    {
        std::uint8_t service{};
        std::uint8_t protocolVersion{};
        std::uint8_t task{};
        std::vector<std::uint8_t> payload;
    };

    struct ServiceResponse
    {
        std::uint8_t envelopeType{ 1 };
        std::uint64_t transaction{};
        std::uint32_t error{};
        std::uint8_t task{};
        std::vector<std::vector<std::uint8_t>> objects;

        [[nodiscard]] std::vector<std::uint8_t> serialize() const;
    };

    [[nodiscard]] std::optional<ServiceRequest> parseServiceRequest(std::span<const std::uint8_t> decoded);

    class ServiceRegistry
    {
    public:
        using Handler = std::function<ServiceResponse(const ServiceRequest &)>;

        void registerTask(std::uint8_t service, std::uint8_t task, std::string name, Handler handler);
        [[nodiscard]] std::optional<ServiceResponse> dispatch(const ServiceRequest &request) const;

        /// The reply an unregistered task gets: error 0, zero results, and a transaction id
        /// from the same counter a handled task would have drawn.
        ///
        /// This is not a courtesy. The C# OLfinal lobby server answers EVERY task this way
        /// (Client.cs, `if (!handled) SendTaskReply(taskId)`), and that server is the one that
        /// has actually driven an OLfinal client to the menu. Staying silent instead is not a
        /// smaller version of the same behaviour -- it is a different one, and the client
        /// responds to it by retrying: 27 requests for service 4 task 13 in a single measured
        /// session, against 12 for a task that is answered.
        [[nodiscard]] ServiceResponse acknowledgeUnhandled(const ServiceRequest &request) const;

        [[nodiscard]] std::string taskName(std::uint8_t service, std::uint8_t task) const;

    private:
        struct Entry
        {
            std::string name;
            Handler handler;
        };
        void stampTransaction(ServiceResponse &response) const;

        std::map<std::pair<std::uint8_t, std::uint8_t>, Entry> tasks_;
        mutable std::atomic<std::uint32_t> nextTransaction_{};
    };
}
