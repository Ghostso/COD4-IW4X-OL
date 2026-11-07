#pragma once

#include <cstddef>
#include <cstdint>
#include <functional>
#include <optional>
#include <string_view>

namespace CodolGameServer
{
    // THE PROFILE SCHEMA, READ BY NAME INSTEAD OF BY ORDINAL.
    //
    // `mp/playerdata.def` is a StructuredDataDef: a tree of structs, indexed arrays and
    // scalars, plus one flat table that converts a path's accumulated INDEX into a byte
    // offset in the 0x8000-byte profile document. The engine's own reader is sub_50F410,
    // which takes property NAMES ("characterClasses", "slots") and walks the same tree:
    //
    //     byteOffset = *(_DWORD *)(*(_DWORD *)(def + 0x38) + 4 * index)
    //
    // Everything in this file is that walk, done in-process against the def the game has
    // already loaded, so that nothing here has to be re-measured when the def changes.
    //
    // WHY IT EXISTS. EngineBindings carried eight hand-measured ordinals for this schema
    // -- characterClasses at 605 with a stride of 14, weaponClasses at 1607 with a stride
    // of 37, slots at child ordinal 5, primaryBase at 22, secondaryBase at 29 -- and every
    // one of them is a PER-BUILD constant. Six of the eight differ on 3.3.3.3 (576/10/1
    // and 1154/36), so the same code reading the same names would have read garbage there.
    // The attachment ordinals were worse: they were not measured at all but derived as
    // `weaponOrdinal - AttachmentCount`, arithmetic that the source comment itself calls
    // numerology, and that landed on the wrong weapon once already (section 187g/187m).
    // The def NAMES them -- primaryAttach at 16, secondaryAttach at 23, six wide -- and
    // asking it is both shorter and correct by construction.
    //
    // THE IN-MEMORY FORM IS THE ON-DISK FORM WITH POINTERS FIXED UP. A zone loads as one
    // contiguous image and the loader replaces each 0xFFFFFFFF "the data follows here"
    // placeholder with the address of that inline data. That is measured, not assumed: the
    // def's header word at +0x38 is 0xFFFFFFFF in the extracted file and is the offset
    // table POINTER at runtime, which is the read EngineBindings has always done. It is
    // also what lets the tests below walk an extracted def: link the placeholders and the
    // production code runs unchanged over the real schema of two different builds.
    class PlayerDataDef
    {
    public:
        // Category numbers, recovered from the data rather than assumed from another CoD
        // title, and matching Tools/olfinal/decode-profile-blob.py in the CODOL repo.
        enum Category : std::uint32_t
        {
            CategoryInt = 0,
            CategoryByte = 1,
            CategoryBool = 2,   // stores a BIT offset, not a byte one
            CategoryString = 3, // typeIndex is the maximum length
            CategoryStruct = 5,
            CategoryIndexedArray = 6,
        };

        // The record layout. Public because the test's fixture linker needs exactly the
        // same offsets the walker uses -- one description of the format, not two.
        struct Layout
        {
            static constexpr std::size_t HeaderBytes = 0x3C;

            static constexpr std::size_t Version = 0x00;
            static constexpr std::size_t FormatChecksum = 0x04;
            static constexpr std::size_t EnumCount = 0x08;
            static constexpr std::size_t Enums = 0x0C;
            static constexpr std::size_t StructCount = 0x10;
            static constexpr std::size_t Structs = 0x14;
            static constexpr std::size_t IndexedArrayCount = 0x18;
            static constexpr std::size_t IndexedArrays = 0x1C;
            static constexpr std::size_t EnumedArrayCount = 0x20;
            static constexpr std::size_t EnumedArrays = 0x24;
            static constexpr std::size_t RootCategory = 0x28;
            static constexpr std::size_t RootType = 0x2C;
            static constexpr std::size_t DocumentSize = 0x30;
            static constexpr std::size_t OffsetTableCount = 0x34;
            static constexpr std::size_t OffsetTable = 0x38;

            // {propertyCount, properties*, sizeBytes, bitOffset, indexCount}
            static constexpr std::size_t StructRecordBytes = 20;
            static constexpr std::size_t StructPropertyCount = 0;
            static constexpr std::size_t StructProperties = 4;
            static constexpr std::size_t StructIndexCount = 16;

            // {name*, category, typeIndex, offsetIndex, 0, 0}
            static constexpr std::size_t PropertyRecordBytes = 24;
            static constexpr std::size_t PropertyName = 0;
            static constexpr std::size_t PropertyCategory = 4;
            static constexpr std::size_t PropertyType = 8;
            static constexpr std::size_t PropertyOffsetIndex = 12;

            // {arraySize, elementCategory, elementTypeIndex, elementSizeBytes}
            static constexpr std::size_t IndexedArrayRecordBytes = 16;
            static constexpr std::size_t IndexedArraySize = 0;
            static constexpr std::size_t IndexedArrayElementCategory = 4;
            static constexpr std::size_t IndexedArrayElementType = 8;

            static constexpr std::size_t EnumedArrayRecordBytes = 16;
            static constexpr std::size_t EnumRecordBytes = 12;
        };

        // A property name longer than this is not a name; it is a wild pointer landing in
        // readable memory. Bounds the string compare so a bad def cannot walk off a page.
        static constexpr std::size_t MaxNameLength = 128;

        // Nothing here dereferences an address this has not approved. In the plugin that
        // is EngineBindings' VirtualQuery probe; in the tests it is a bounds check against
        // the fixture buffer.
        using Readable = std::function<bool(const void *, std::size_t)>;

        // What a named path addresses.
        struct Resolved
        {
            std::uint32_t index{};    // table index of the element the path names
            std::uint32_t category{}; // Category of that element
            std::uint32_t count{ 1 }; // array length, when the path stops on an array
            std::uint32_t stride{};   // indices between elements of that array
        };

        // `def` is the loaded def buffer: *(DB_FindXAssetHeader(39, "mp/playerdata.def") + 8).
        // Returns nothing when the header does not read, so a caller that gets a value has
        // already had its pointers checked.
        [[nodiscard]] static std::optional<PlayerDataDef> open(
            const void *def,
            Readable readable);

        [[nodiscard]] std::uint32_t version() const { return version_; }
        [[nodiscard]] std::uint32_t formatChecksum() const { return formatChecksum_; }

        // The profile document's size in bytes -- the bound a byte offset must fall inside.
        [[nodiscard]] std::uint32_t documentSize() const { return documentSize_; }
        [[nodiscard]] std::uint32_t offsetTableCount() const { return offsetTableCount_; }

        // sub_50F410's last step: index -> byte offset in the document.
        [[nodiscard]] std::optional<std::uint32_t> byteOffset(std::uint32_t index) const;

        // "characterClasses", "characterClasses[3].slots", "weaponClasses[7].primaryBase".
        // A trailing array with no subscript resolves to its element 0 and reports the
        // array's length and stride, which is how the caller learns that `slots` is nine
        // wide and `weaponClasses` is sixty long WITHOUT being told.
        [[nodiscard]] std::optional<Resolved> resolve(std::string_view path) const;

        // resolve() and then byteOffset(), for the common case.
        [[nodiscard]] std::optional<std::uint32_t> byteOffsetOf(std::string_view path) const;

    private:
        PlayerDataDef() = default;

        [[nodiscard]] bool readU32(const std::uint8_t *at, std::uint32_t &value) const;
        [[nodiscard]] const std::uint8_t *pointerAt(
            const std::uint8_t *record,
            std::size_t offset) const;
        [[nodiscard]] bool nameEquals(const std::uint8_t *name, std::string_view want) const;

        struct Property
        {
            std::uint32_t category{};
            std::uint32_t typeIndex{};
            std::uint32_t offsetIndex{};
        };

        [[nodiscard]] std::optional<Property> findProperty(
            std::uint32_t structIndex,
            std::string_view name) const;

        struct Array
        {
            std::uint32_t size{};
            std::uint32_t elementCategory{};
            std::uint32_t elementType{};
        };

        [[nodiscard]] std::optional<Array> indexedArray(std::uint32_t typeIndex) const;

        // How many table indices one value of this type occupies. Recursion is bounded
        // because an array of arrays of ... cannot nest deeper than the def has types.
        [[nodiscard]] std::optional<std::uint32_t> elementSpan(
            std::uint32_t category,
            std::uint32_t typeIndex,
            std::uint32_t depth = 0) const;

        Readable readable_{};
        const std::uint8_t *def_{};
        const std::uint8_t *structs_{};
        const std::uint8_t *indexedArrays_{};
        const std::uint8_t *offsetTable_{};
        std::uint32_t version_{};
        std::uint32_t formatChecksum_{};
        std::uint32_t structCount_{};
        std::uint32_t indexedArrayCount_{};
        std::uint32_t rootCategory_{};
        std::uint32_t rootType_{};
        std::uint32_t documentSize_{};
        std::uint32_t offsetTableCount_{};
    };
}
