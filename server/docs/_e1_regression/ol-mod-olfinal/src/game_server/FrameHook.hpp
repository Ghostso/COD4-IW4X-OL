#pragma once

#include "EngineBindings.hpp"

#include <cstdint>

namespace CodolGameServer
{
    using FrameCallback = void (*)(std::uint32_t nowMilliseconds);

    bool installFrameHook(const EngineBindings &bindings, FrameCallback callback);
}
