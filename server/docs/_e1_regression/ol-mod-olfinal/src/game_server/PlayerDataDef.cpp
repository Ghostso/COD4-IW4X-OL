#include "PlayerDataDef.hpp"

#include <algorithm>
#include <charconv>
#include <cstring>
#include <system_error>
#include <utility>

namespace CodolGameServer
{
    namespace
    {
        // A def with a cycle in its type graph would otherwise recurse forever. Nothing
        // real nests anywhere near this deep -- the deepest path in either shipped def is
        // an array of structs holding an array of scalars.
        constexpr std::uint32_t MaxTypeDepth = 8;

        // Every pointer field in the def is one 32-bit word, because the client and this
        // plugin are both x86. A 64-bit build would silently truncate every address
        // pointerAt() reconstructs, so it fails here instead.
        static_assert(
            sizeof(void *) == sizeof(std::uint32_t),
            "the StructuredDataDef pointer fields are 32-bit; this is an x86 image");
    }

    std::optional<PlayerDataDef> PlayerDataDef::open(
        const void *const def,
        Readable readable)
    {
        if (!def || !readable)
            return std::nullopt;
        if (!readable(def, Layout::HeaderBytes))
            return std::nullopt;

        PlayerDataDef parsed;
        parsed.readable_ = std::move(readable);
        parsed.def_ = static_cast<const std::uint8_t *>(def);

        const auto header = [&](const std::size_t offset, std::uint32_t &value) {
            return parsed.readU32(parsed.def_ + offset, value);
        };
        if (!header(Layout::Version, parsed.version_) ||
            !header(Layout::FormatChecksum, parsed.formatChecksum_) ||
            !header(Layout::StructCount, parsed.structCount_) ||
            !header(Layout::IndexedArrayCount, parsed.indexedArrayCount_) ||
            !header(Layout::RootCategory, parsed.rootCategory_) ||
            !header(Layout::RootType, parsed.rootType_) ||
            !header(Layout::DocumentSize, parsed.documentSize_) ||
            !header(Layout::OffsetTableCount, parsed.offsetTableCount_))
        {
            return std::nullopt;
        }

        parsed.structs_ = parsed.pointerAt(parsed.def_, Layout::Structs);
        parsed.indexedArrays_ = parsed.pointerAt(parsed.def_, Layout::IndexedArrays);
        parsed.offsetTable_ = parsed.pointerAt(parsed.def_, Layout::OffsetTable);

        // A def with no structs, no offset table or a root that is not a struct is not
        // this schema. Refuse it here rather than resolving nonsense from it.
        if (!parsed.structs_ || !parsed.offsetTable_ || !parsed.structCount_ ||
            !parsed.offsetTableCount_ || parsed.rootCategory_ != CategoryStruct ||
            parsed.rootType_ >= parsed.structCount_)
        {
            return std::nullopt;
        }
        // indexedArrays_ may legitimately be null only when the def declares none; every
        // shipped def declares some, and a null one with a non-zero count is corrupt.
        if (parsed.indexedArrayCount_ && !parsed.indexedArrays_)
            return std::nullopt;

        return parsed;
    }

    bool PlayerDataDef::readU32(const std::uint8_t *const at, std::uint32_t &value) const
    {
        if (!at || !readable_(at, sizeof(std::uint32_t)))
            return false;
        std::memcpy(&value, at, sizeof(value));
        return true;
    }

    const std::uint8_t *PlayerDataDef::pointerAt(
        const std::uint8_t *const record,
        const std::size_t offset) const
    {
        // A pointer field is 32-bit in this 32-bit image, and the placeholder an unlinked
        // def carries is 0xFFFFFFFF. Both are rejected the same way: by asking whether the
        // address it names is readable.
        std::uint32_t raw = 0;
        if (!readU32(record + offset, raw) || !raw || raw == 0xFFFFFFFFu)
            return nullptr;
        const auto *const address = reinterpret_cast<const std::uint8_t *>(
            static_cast<std::uintptr_t>(raw));
        return readable_(address, 1) ? address : nullptr;
    }

    bool PlayerDataDef::nameEquals(
        const std::uint8_t *const name,
        const std::string_view want) const
    {
        if (!name || want.empty() || want.size() >= MaxNameLength)
            return false;
        // The NUL is part of the comparison: without it "primaryBase" would match
        // "primaryBaseSomething", and this def does carry names that share a prefix
        // (primaryAttach / primaryBase, lethal / lethalDoubleAmmo).
        if (!readable_(name, want.size() + 1))
            return false;
        return std::memcmp(name, want.data(), want.size()) == 0 &&
            name[want.size()] == '\0';
    }

    std::optional<PlayerDataDef::Property> PlayerDataDef::findProperty(
        const std::uint32_t structIndex,
        const std::string_view name) const
    {
        if (structIndex >= structCount_)
            return std::nullopt;
        const auto *const record = structs_ + structIndex * Layout::StructRecordBytes;
        std::uint32_t propertyCount = 0;
        if (!readU32(record + Layout::StructPropertyCount, propertyCount))
            return std::nullopt;
        const auto *const properties = pointerAt(record, Layout::StructProperties);
        if (!properties || !propertyCount)
            return std::nullopt;
        if (!readable_(properties, propertyCount * Layout::PropertyRecordBytes))
            return std::nullopt;

        for (std::uint32_t position = 0; position < propertyCount; ++position)
        {
            const auto *const property =
                properties + position * Layout::PropertyRecordBytes;
            // A property whose name pointer does not read is skipped, not fatal: the
            // extracted defs carry a handful of names that resolve outside the slice, and
            // none of them is a name this server asks for.
            if (!nameEquals(pointerAt(property, Layout::PropertyName), name))
                continue;
            Property found;
            if (!readU32(property + Layout::PropertyCategory, found.category) ||
                !readU32(property + Layout::PropertyType, found.typeIndex) ||
                !readU32(property + Layout::PropertyOffsetIndex, found.offsetIndex))
            {
                return std::nullopt;
            }
            return found;
        }
        return std::nullopt;
    }

    std::optional<PlayerDataDef::Array> PlayerDataDef::indexedArray(
        const std::uint32_t typeIndex) const
    {
        if (typeIndex >= indexedArrayCount_)
            return std::nullopt;
        const auto *const record =
            indexedArrays_ + typeIndex * Layout::IndexedArrayRecordBytes;
        Array array;
        if (!readU32(record + Layout::IndexedArraySize, array.size) ||
            !readU32(record + Layout::IndexedArrayElementCategory, array.elementCategory) ||
            !readU32(record + Layout::IndexedArrayElementType, array.elementType))
        {
            return std::nullopt;
        }
        return array;
    }

    std::optional<std::uint32_t> PlayerDataDef::elementSpan(
        const std::uint32_t category,
        const std::uint32_t typeIndex,
        const std::uint32_t depth) const
    {
        if (depth > MaxTypeDepth)
            return std::nullopt;
        if (category == CategoryStruct)
        {
            if (typeIndex >= structCount_)
                return std::nullopt;
            std::uint32_t indexCount = 0;
            if (!readU32(
                    structs_ + typeIndex * Layout::StructRecordBytes +
                        Layout::StructIndexCount,
                    indexCount))
            {
                return std::nullopt;
            }
            return indexCount;
        }
        if (category == CategoryIndexedArray)
        {
            const auto array = indexedArray(typeIndex);
            if (!array)
                return std::nullopt;
            const auto inner =
                elementSpan(array->elementCategory, array->elementType, depth + 1);
            if (!inner)
                return std::nullopt;
            // The product cannot exceed the offset table, which is what it indexes.
            const auto total = static_cast<std::uint64_t>(array->size) * *inner;
            if (total > offsetTableCount_)
                return std::nullopt;
            return static_cast<std::uint32_t>(total);
        }
        // Everything else -- int, byte, bool, string, enum -- is one index.
        return 1u;
    }

    std::optional<std::uint32_t> PlayerDataDef::byteOffset(const std::uint32_t index) const
    {
        if (index >= offsetTableCount_)
            return std::nullopt;
        std::uint32_t offset = 0;
        if (!readU32(offsetTable_ + index * sizeof(std::uint32_t), offset))
            return std::nullopt;
        return offset;
    }

    std::optional<PlayerDataDef::Resolved> PlayerDataDef::resolve(
        const std::string_view path) const
    {
        if (path.empty())
            return std::nullopt;

        std::uint32_t index = 0;
        std::uint32_t structIndex = rootType_;
        Resolved resolved;
        bool inStruct = true;

        std::size_t at = 0;
        while (at <= path.size())
        {
            const auto stop = path.find('.', at);
            const auto step =
                path.substr(at, stop == std::string_view::npos ? stop : stop - at);
            if (step.empty() || !inStruct)
                return std::nullopt;

            const auto bracket = step.find('[');
            const auto name = step.substr(0, bracket);
            const auto property = findProperty(structIndex, name);
            if (!property)
                return std::nullopt;

            auto category = property->category;
            auto typeIndex = property->typeIndex;
            // An offsetIndex is a table index; one past the table is a corrupt record.
            if (property->offsetIndex >= offsetTableCount_ ||
                index > offsetTableCount_ - property->offsetIndex)
            {
                return std::nullopt;
            }
            index += property->offsetIndex;

            // Every subscript peels one array level and moves the index by that level's
            // element span -- exactly the way a byte offset would accumulate, which is
            // what makes the def's single conversion at the end correct.
            auto cursor = bracket;
            while (cursor != std::string_view::npos && cursor < step.size())
            {
                if (step[cursor] != '[')
                    return std::nullopt;
                const auto close = step.find(']', cursor);
                if (close == std::string_view::npos)
                    return std::nullopt;
                const auto digits = step.substr(cursor + 1, close - cursor - 1);
                std::uint32_t subscript = 0;
                const auto *const first = digits.data();
                const auto parse =
                    std::from_chars(first, first + digits.size(), subscript);
                if (parse.ec != std::errc{} || parse.ptr != first + digits.size())
                    return std::nullopt;

                if (category != CategoryIndexedArray)
                    return std::nullopt;
                const auto array = indexedArray(typeIndex);
                if (!array || subscript >= array->size)
                    return std::nullopt;
                category = array->elementCategory;
                typeIndex = array->elementType;
                const auto span = elementSpan(category, typeIndex);
                if (!span)
                    return std::nullopt;
                const auto moved = static_cast<std::uint64_t>(subscript) * *span;
                if (moved > offsetTableCount_ || index > offsetTableCount_ - moved)
                    return std::nullopt;
                index += static_cast<std::uint32_t>(moved);

                cursor = close + 1;
            }

            resolved.category = category;
            resolved.count = 1;
            resolved.stride = 0;
            if (category == CategoryIndexedArray)
            {
                // A path that stops on an array names its element 0 and reports the shape,
                // so a caller asking for "characterClasses" learns that it is twelve
                // elements fourteen indices apart without carrying either number.
                const auto array = indexedArray(typeIndex);
                if (!array)
                    return std::nullopt;
                const auto span = elementSpan(array->elementCategory, array->elementType);
                if (!span)
                    return std::nullopt;
                resolved.count = array->size;
                resolved.stride = *span;
                resolved.category = array->elementCategory;
                inStruct = false;
            }
            else if (category == CategoryStruct)
            {
                structIndex = typeIndex;
                inStruct = true;
            }
            else
            {
                inStruct = false;
            }

            if (stop == std::string_view::npos)
                break;
            at = stop + 1;
        }

        resolved.index = index;
        return resolved;
    }

    std::optional<std::uint32_t> PlayerDataDef::byteOffsetOf(
        const std::string_view path) const
    {
        const auto resolved = resolve(path);
        return resolved ? byteOffset(resolved->index) : std::nullopt;
    }
}
