#pragma once

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <string>

namespace OlMod
{
    enum class ProcessRole
    {
        Combined,
        Client,
        Dedicated,
    };

    inline ProcessRole processRole()
    {
        char *configured{};
        std::size_t configuredSize{};
        if (_dupenv_s(
                &configured,
                &configuredSize,
                "OLMOD_PROCESS_ROLE") != 0 ||
            !configured)
        {
            return ProcessRole::Combined;
        }

        std::string role(configured);
        std::free(configured);
        std::ranges::transform(role, role.begin(), [](const unsigned char character) {
            return static_cast<char>(std::tolower(character));
        });
        if (role == "client")
            return ProcessRole::Client;
        if (role == "dedicated")
            return ProcessRole::Dedicated;
        return ProcessRole::Combined;
    }

    inline bool runsBackend(const ProcessRole role)
    {
        return role != ProcessRole::Dedicated;
    }

    inline bool runsGameServer(const ProcessRole role)
    {
        return role != ProcessRole::Client;
    }
}
