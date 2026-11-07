#pragma once

#include <cstdint>

namespace CodolGameServer
{
    // Transport identity used by the plugin. This is not CODOL's in-memory netadr_t layout.
    struct PeerAddress
    {
        std::uint32_t ipv4{};
        std::uint16_t port{};

        bool operator==(const PeerAddress &) const = default;
    };
}
