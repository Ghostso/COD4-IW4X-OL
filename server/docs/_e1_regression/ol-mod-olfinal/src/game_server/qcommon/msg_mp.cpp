#include "msg_mp.hpp"

#include <array>

namespace CodolGameServer
{
    void MsgWriter::MSG_WriteByte(const std::uint8_t value)
    {
        MSG_WriteData(std::span(&value, 1));
    }

    void MsgWriter::MSG_WriteShort(const std::uint16_t value)
    {
        const std::array bytes{
            static_cast<std::uint8_t>(value),
            static_cast<std::uint8_t>(value >> 8),
        };
        MSG_WriteData(bytes);
    }

    void MsgWriter::MSG_WriteLong(const std::uint32_t value)
    {
        const std::array bytes{
            static_cast<std::uint8_t>(value),
            static_cast<std::uint8_t>(value >> 8),
            static_cast<std::uint8_t>(value >> 16),
            static_cast<std::uint8_t>(value >> 24),
        };
        MSG_WriteData(bytes);
    }
}
