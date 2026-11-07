#include "ByteBuffer.hpp"

#include <algorithm>
#include <limits>

namespace
{
    constexpr std::uint8_t TypeBool = 0x01;
    constexpr std::uint8_t TypeU8 = 0x03;
    constexpr std::uint8_t TypeU16 = 0x06;
    // SignedInteger32 in the shared Demonware type enum, one below TypeU32. The
    // matchmaking session record needs it: its query-criterion fields are SIGNED
    // and the client type-checks each value, so writing them as TypeU32 is not a
    // cosmetic difference.
    constexpr std::uint8_t TypeI32 = 0x07;
    constexpr std::uint8_t TypeU32 = 0x08;
    constexpr std::uint8_t TypeI64 = 0x09;
    constexpr std::uint8_t TypeU64 = 0x0A;
    constexpr std::uint8_t TypeString = 0x10;
    constexpr std::uint8_t TypeBlob = 0x13;
    constexpr std::uint8_t TypeArray = 0x6C;
}

namespace AlwaysofflineRe::Demonware
{
    ByteBuffer::ByteBuffer(const std::span<const std::uint8_t> data)
        : data_(data.begin(), data.end())
    {
    }

    bool ByteBuffer::require(const std::size_t size)
    {
        if (!valid_ || size > remainingSize())
        {
            valid_ = false;
            return false;
        }
        return true;
    }

    bool ByteBuffer::readType(const std::uint8_t expected)
    {
        if (!useDataTypes_)
            return true;
        if (!require(1))
            return false;
        if (data_[cursor_++] != expected)
        {
            valid_ = false;
            return false;
        }
        return true;
    }

    void ByteBuffer::writeType(const std::uint8_t type)
    {
        if (useDataTypes_)
            data_.push_back(type);
    }

    bool ByteBuffer::readRaw(const std::span<std::uint8_t> output)
    {
        if (!require(output.size()))
            return false;
        std::copy_n(data_.begin() + static_cast<std::ptrdiff_t>(cursor_), output.size(), output.begin());
        cursor_ += output.size();
        return true;
    }

    bool ByteBuffer::readU8(std::uint8_t &value)
    {
        if (!readType(TypeU8) || !require(1))
            return false;
        value = data_[cursor_++];
        return true;
    }

    bool ByteBuffer::readBool(bool &value)
    {
        if (!readType(TypeBool) || !require(1))
            return false;
        value = data_[cursor_++] != 0;
        return true;
    }

    bool ByteBuffer::readU16(std::uint16_t &value)
    {
        if (!readType(TypeU16) || !require(2))
            return false;
        value = static_cast<std::uint16_t>(data_[cursor_]) |
            static_cast<std::uint16_t>(data_[cursor_ + 1] << 8);
        cursor_ += 2;
        return true;
    }

    bool ByteBuffer::readU32(std::uint32_t &value)
    {
        if (!readType(TypeU32) || !require(4))
            return false;
        value = 0;
        for (unsigned int index = 0; index != 4; ++index)
            value |= static_cast<std::uint32_t>(data_[cursor_ + index]) << (index * 8);
        cursor_ += 4;
        return true;
    }

    bool ByteBuffer::readU64(std::uint64_t &value)
    {
        if (!readType(TypeU64) || !require(8))
            return false;
        value = 0;
        for (unsigned int index = 0; index != 8; ++index)
            value |= static_cast<std::uint64_t>(data_[cursor_ + index]) << (index * 8);
        cursor_ += 8;
        return true;
    }

    bool ByteBuffer::readI64(std::int64_t &value)
    {
        if (!readType(TypeI64) || !require(8))
            return false;
        std::uint64_t encoded{};
        for (unsigned int index = 0; index != 8; ++index)
            encoded |= static_cast<std::uint64_t>(data_[cursor_ + index]) << (index * 8);
        cursor_ += 8;
        value = static_cast<std::int64_t>(encoded);
        return true;
    }

    bool ByteBuffer::readU32Array(std::vector<std::uint32_t> &value)
    {
        if (!readType(TypeArray) || !require(9) || data_[cursor_++] != TypeU32)
        {
            valid_ = false;
            return false;
        }

        const auto readRawU32 = [this]()
        {
            std::uint32_t result{};
            for (unsigned int index = 0; index != 4; ++index)
                result |= static_cast<std::uint32_t>(data_[cursor_++]) << (index * 8);
            return result;
        };
        const auto byteSize = readRawU32();
        const auto count = readRawU32();
        if (count > (std::numeric_limits<std::uint32_t>::max)() / 4 || byteSize != count * 4 ||
            !require(byteSize))
        {
            valid_ = false;
            return false;
        }

        value.clear();
        value.reserve(count);
        for (std::uint32_t index = 0; index != count; ++index)
            value.push_back(readRawU32());
        return true;
    }

    bool ByteBuffer::readString(std::string &value)
    {
        if (!readType(TypeString))
            return false;
        const auto begin = data_.begin() + static_cast<std::ptrdiff_t>(cursor_);
        const auto terminator = std::find(begin, data_.end(), std::uint8_t{});
        if (terminator == data_.end())
        {
            valid_ = false;
            return false;
        }
        value.assign(begin, terminator);
        cursor_ = static_cast<std::size_t>(std::distance(data_.begin(), terminator)) + 1;
        return true;
    }

    bool ByteBuffer::readBlob(std::vector<std::uint8_t> &value)
    {
        if (!readType(TypeBlob))
            return false;
        std::uint32_t size{};
        if (!readU32(size) || !require(size))
            return false;
        value.assign(
            data_.begin() + static_cast<std::ptrdiff_t>(cursor_),
            data_.begin() + static_cast<std::ptrdiff_t>(cursor_ + size));
        cursor_ += size;
        return true;
    }

    void ByteBuffer::writeRaw(const std::span<const std::uint8_t> value)
    {
        data_.insert(data_.end(), value.begin(), value.end());
    }

    void ByteBuffer::writeU8(const std::uint8_t value)
    {
        writeType(TypeU8);
        data_.push_back(value);
    }

    void ByteBuffer::writeBool(const bool value)
    {
        writeType(TypeBool);
        data_.push_back(value ? 1 : 0);
    }

    void ByteBuffer::writeU16(const std::uint16_t value)
    {
        writeType(TypeU16);
        data_.push_back(static_cast<std::uint8_t>(value));
        data_.push_back(static_cast<std::uint8_t>(value >> 8));
    }

    void ByteBuffer::writeU32(const std::uint32_t value)
    {
        writeType(TypeU32);
        for (unsigned int index = 0; index != 4; ++index)
            data_.push_back(static_cast<std::uint8_t>(value >> (index * 8)));
    }

    void ByteBuffer::writeI32(const std::int32_t value)
    {
        writeType(TypeI32);
        const auto bits = static_cast<std::uint32_t>(value);
        for (unsigned int index = 0; index != 4; ++index)
            data_.push_back(static_cast<std::uint8_t>(bits >> (index * 8)));
    }

    void ByteBuffer::writeU64(const std::uint64_t value)
    {
        writeType(TypeU64);
        for (unsigned int index = 0; index != 8; ++index)
            data_.push_back(static_cast<std::uint8_t>(value >> (index * 8)));
    }

    void ByteBuffer::writeI64(const std::int64_t value)
    {
        writeType(TypeI64);
        const auto encoded = static_cast<std::uint64_t>(value);
        for (unsigned int index = 0; index != 8; ++index)
            data_.push_back(static_cast<std::uint8_t>(encoded >> (index * 8)));
    }

    void ByteBuffer::writeU32Array(const std::span<const std::uint32_t> value)
    {
        if (value.size() > (std::numeric_limits<std::uint32_t>::max)() / 4)
        {
            valid_ = false;
            return;
        }
        writeType(TypeArray);
        data_.push_back(TypeU32);
        const auto writeRawU32 = [this](const std::uint32_t item)
        {
            for (unsigned int index = 0; index != 4; ++index)
                data_.push_back(static_cast<std::uint8_t>(item >> (index * 8)));
        };
        writeRawU32(static_cast<std::uint32_t>(value.size() * 4));
        writeRawU32(static_cast<std::uint32_t>(value.size()));
        for (const auto item : value)
            writeRawU32(item);
    }

    void ByteBuffer::writeString(const std::string_view value)
    {
        writeType(TypeString);
        data_.insert(data_.end(), value.begin(), value.end());
        data_.push_back(0);
    }

    void ByteBuffer::writeBlob(const std::span<const std::uint8_t> value)
    {
        if (value.size() > std::numeric_limits<std::uint32_t>::max())
        {
            valid_ = false;
            return;
        }
        writeType(TypeBlob);
        writeU32(static_cast<std::uint32_t>(value.size()));
        writeRaw(value);
    }

    std::span<const std::uint8_t> ByteBuffer::remaining() const
    {
        return std::span(data_).subspan(cursor_);
    }
}
