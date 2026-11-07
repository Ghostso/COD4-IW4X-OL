#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace AlwaysofflineRe::Demonware
{
    class ByteBuffer
    {
    public:
        ByteBuffer() = default;
        explicit ByteBuffer(std::span<const std::uint8_t> data);

        [[nodiscard]] bool readU8(std::uint8_t &value);
        [[nodiscard]] bool readBool(bool &value);
        [[nodiscard]] bool readU16(std::uint16_t &value);
        [[nodiscard]] bool readU32(std::uint32_t &value);
        [[nodiscard]] bool readU64(std::uint64_t &value);
        [[nodiscard]] bool readI64(std::int64_t &value);
        [[nodiscard]] bool readU32Array(std::vector<std::uint32_t> &value);
        [[nodiscard]] bool readString(std::string &value);
        [[nodiscard]] bool readBlob(std::vector<std::uint8_t> &value);
        [[nodiscard]] bool readRaw(std::span<std::uint8_t> output);

        void writeU8(std::uint8_t value);
        void writeBool(bool value);
        void writeU16(std::uint16_t value);
        void writeU32(std::uint32_t value);
        void writeI32(std::int32_t value);
        void writeU64(std::uint64_t value);
        void writeI64(std::int64_t value);
        void writeU32Array(std::span<const std::uint32_t> value);
        void writeString(std::string_view value);
        void writeBlob(std::span<const std::uint8_t> value);
        void writeRaw(std::span<const std::uint8_t> value);

        void useDataTypes(bool enabled) { useDataTypes_ = enabled; }
        [[nodiscard]] bool valid() const { return valid_; }
        [[nodiscard]] bool empty() const { return cursor_ == data_.size(); }
        [[nodiscard]] std::size_t remainingSize() const { return data_.size() - cursor_; }
        [[nodiscard]] std::span<const std::uint8_t> remaining() const;
        [[nodiscard]] const std::vector<std::uint8_t> &data() const { return data_; }

    private:
        [[nodiscard]] bool readType(std::uint8_t expected);
        void writeType(std::uint8_t type);
        [[nodiscard]] bool require(std::size_t size);

        std::vector<std::uint8_t> data_;
        std::size_t cursor_{};
        bool useDataTypes_{ true };
        bool valid_{ true };
    };
}
