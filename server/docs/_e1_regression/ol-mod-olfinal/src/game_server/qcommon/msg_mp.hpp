#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>

namespace CodolGameServer
{
    struct msg_t
    {
        std::int32_t overflowed{};
        std::int32_t readOnly{};
        std::uint8_t *data{};
        std::uint8_t *splitData{};
        std::int32_t maxsize{};
        std::int32_t cursize{};
        std::int32_t splitSize{};
        std::int32_t readcount{};
        std::int32_t bit{};
        std::int32_t lastEntityRef{};
        std::int32_t flush{};
        std::int32_t targetLocalNetID{};
    };

    static_assert(sizeof(void *) != 4 || sizeof(msg_t) == 0x30);
    static_assert(sizeof(void *) != 4 || offsetof(msg_t, data) == 0x08);
    static_assert(sizeof(void *) != 4 || offsetof(msg_t, cursize) == 0x14);
    static_assert(sizeof(void *) != 4 || offsetof(msg_t, readcount) == 0x1C);
    static_assert(sizeof(void *) != 4 || offsetof(msg_t, bit) == 0x20);

    class MsgWriter
    {
    public:
        virtual ~MsgWriter() = default;

        virtual void MSG_WriteData(std::span<const std::uint8_t> value) = 0;
        virtual void MSG_WriteBits(std::int32_t value, std::uint32_t bits) = 0;
        virtual void MSG_WriteString(std::string_view value) = 0;
        [[nodiscard]] virtual bool overflowed() const = 0;

        void MSG_WriteByte(std::uint8_t value);
        void MSG_WriteShort(std::uint16_t value);
        void MSG_WriteLong(std::uint32_t value);
    };
}
