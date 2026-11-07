#include "PlayerDataDef.hpp"

#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <initializer_list>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace
{
    using CodolGameServer::PlayerDataDef;

    void require(const bool condition, const std::string &message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    std::vector<std::uint8_t> readFile(const std::string &path)
    {
        std::ifstream file(path, std::ios::binary);
        require(file.good(), "fixture " + path + " does not open");
        std::vector<std::uint8_t> bytes(
            (std::istreambuf_iterator<char>(file)),
            std::istreambuf_iterator<char>());
        require(!bytes.empty(), "fixture " + path + " is empty");
        return bytes;
    }

    // THE FIXTURE LINKER.
    //
    // An extracted def is the loaded image MINUS the loader's pointer fixups: every
    // pointer field that named inline data reads back as the 0xFFFFFFFF placeholder. This
    // puts them back, so the production walker runs over the real schema of a real build
    // with no test-only reading code in the path.
    //
    // A NAME BLOCK'S LENGTH IS COUNTED, NOT GUESSED. The strings that follow a record
    // array are exactly as many as that array has 0xFFFFFFFF name fields -- a property or
    // enum entry whose name already appears earlier in the zone stores a resolved pointer
    // and emits nothing. Deciding the block's end by "is this token still printable"
    // instead is what drifted an earlier decoder by two bytes: the byte after the enum's
    // names here is 0x5C, a printable backslash. The walk is self-checking anyway --
    // it must land on the offset table exactly `offsetTableCount * 4` bytes before the end
    // of the file, and linkDef() asserts that.
    class LinkedDef
    {
    public:
        explicit LinkedDef(const std::string &path)
            : image_(readFile(path))
        {
            static constexpr std::string_view Marker = "mp/playerdata.def";
            const auto found = std::search(
                image_.begin(), image_.end(), Marker.begin(), Marker.end(),
                [](const std::uint8_t left, const char right) {
                    return left == static_cast<std::uint8_t>(right);
                });
            require(found != image_.end(), path + " holds no mp/playerdata.def");
            defAt_ = static_cast<std::size_t>(found - image_.begin()) + Marker.size() + 1;
            link(path);
        }

        [[nodiscard]] const std::uint8_t *def() const { return image_.data() + defAt_; }

        // The walker touches nothing outside the fixture. This is the test's stand-in for
        // EngineBindings' VirtualQuery probe, and it is what makes the handful of name
        // pointers that resolve outside the extracted slice a skip rather than a crash.
        [[nodiscard]] PlayerDataDef::Readable readable() const
        {
            const auto *const begin = image_.data();
            const auto *const end = image_.data() + image_.size();
            return [begin, end](const void *const address, const std::size_t length) {
                const auto *const at = static_cast<const std::uint8_t *>(address);
                return at >= begin && at <= end &&
                    length <= static_cast<std::size_t>(end - at);
            };
        }

    private:
        std::uint32_t u32(const std::size_t at) const
        {
            require(at + 4 <= image_.size(), "fixture read past its end");
            std::uint32_t value = 0;
            std::memcpy(&value, image_.data() + at, sizeof(value));
            return value;
        }

        void put(const std::size_t at, const std::size_t target)
        {
            require(at + 4 <= image_.size(), "fixture write past its end");
            require(u32(at) == 0xFFFFFFFFu, "linking a field that is not a placeholder");
            const auto address = reinterpret_cast<std::uintptr_t>(image_.data() + target);
            const auto raw = static_cast<std::uint32_t>(address);
            require(
                static_cast<std::uintptr_t>(raw) == address,
                "the fixture must live below 4 GB, as it does in a 32-bit build");
            std::memcpy(image_.data() + at, &raw, sizeof(raw));
        }

        // Skip `count` NUL-terminated strings.
        std::size_t strings(std::size_t at, const std::uint32_t count)
        {
            for (std::uint32_t entry = 0; entry < count; ++entry)
            {
                while (at < image_.size() && image_[at] != 0)
                    ++at;
                require(at < image_.size(), "a name block runs off the end of the fixture");
                ++at;
            }
            return at;
        }

        // Point every placeholder name field in a record array at the string that
        // follows, and return where the block ends.
        std::size_t linkNames(
            const std::size_t records,
            const std::uint32_t count,
            const std::size_t recordBytes,
            const std::size_t nameOffset)
        {
            auto at = records + count * recordBytes;
            for (std::uint32_t entry = 0; entry < count; ++entry)
            {
                const auto field = records + entry * recordBytes + nameOffset;
                if (u32(field) != 0xFFFFFFFFu)
                    continue;
                put(field, at);
                at = strings(at, 1);
            }
            return at;
        }

        void link(const std::string &path)
        {
            using Layout = PlayerDataDef::Layout;

            const auto enumCount = u32(defAt_ + Layout::EnumCount);
            const auto structCount = u32(defAt_ + Layout::StructCount);
            const auto indexedArrayCount = u32(defAt_ + Layout::IndexedArrayCount);
            const auto enumedArrayCount = u32(defAt_ + Layout::EnumedArrayCount);
            const auto offsetTableCount = u32(defAt_ + Layout::OffsetTableCount);

            auto at = defAt_ + Layout::HeaderBytes;

            if (enumCount)
            {
                put(defAt_ + Layout::Enums, at);
                const auto enums = at;
                at += enumCount * Layout::EnumRecordBytes;
                for (std::uint32_t entry = 0; entry < enumCount; ++entry)
                {
                    const auto entryCount = u32(enums + entry * Layout::EnumRecordBytes);
                    // An enum entry is {name*, value}; its names follow the same rule.
                    at = linkNames(at, entryCount, 8, 0);
                }
            }

            require(structCount != 0, path + " declares no structs");
            put(defAt_ + Layout::Structs, at);
            const auto structs = at;
            at += structCount * Layout::StructRecordBytes;
            for (std::uint32_t entry = 0; entry < structCount; ++entry)
            {
                const auto record = structs + entry * Layout::StructRecordBytes;
                const auto propertyCount = u32(record + Layout::StructPropertyCount);
                if (!propertyCount)
                    continue;
                put(record + Layout::StructProperties, at);
                at = linkNames(
                    at,
                    propertyCount,
                    Layout::PropertyRecordBytes,
                    Layout::PropertyName);
            }

            if (indexedArrayCount)
            {
                put(defAt_ + Layout::IndexedArrays, at);
                at += indexedArrayCount * Layout::IndexedArrayRecordBytes;
            }
            if (enumedArrayCount)
            {
                put(defAt_ + Layout::EnumedArrays, at);
                at += enumedArrayCount * Layout::EnumedArrayRecordBytes;
            }

            put(defAt_ + Layout::OffsetTable, at);
            // THE WALK'S OWN ORACLE. The offset table is last in the file, so a link that
            // mis-sized any name block lands somewhere other than exactly its own length
            // before the end. Nothing below is trustworthy if this does not hold.
            require(
                at + offsetTableCount * 4 == image_.size(),
                path + ": the linked offset table does not end at the file's end -- "
                       "a name block was mis-sized");
        }

        std::vector<std::uint8_t> image_;
        std::size_t defAt_{};
    };

    struct Expected
    {
        const char *path;
        std::uint32_t index;
        std::uint32_t count;
        std::uint32_t stride;
        std::uint32_t byteOffset;
    };

    void checkSchema(
        const PlayerDataDef &def,
        const std::string &label,
        const std::uint32_t formatChecksum,
        const std::uint32_t documentSize,
        const std::uint32_t offsetTableCount,
        const std::vector<Expected> &expected)
    {
        require(
            def.formatChecksum() == formatChecksum,
            label + ": formatChecksum is " + std::to_string(def.formatChecksum()));
        require(
            def.documentSize() == documentSize,
            label + ": documentSize is " + std::to_string(def.documentSize()));
        require(
            def.offsetTableCount() == offsetTableCount,
            label + ": offsetTableCount is " + std::to_string(def.offsetTableCount()));

        for (const auto &want : expected)
        {
            const auto resolved = def.resolve(want.path);
            require(
                resolved.has_value(),
                label + ": " + want.path + " does not resolve BY NAME");
            require(
                resolved->index == want.index,
                label + ": " + want.path + " is index " +
                    std::to_string(resolved->index) + ", expected " +
                    std::to_string(want.index));
            require(
                resolved->count == want.count,
                label + ": " + want.path + " is " + std::to_string(resolved->count) +
                    " wide, expected " + std::to_string(want.count));
            require(
                resolved->stride == want.stride,
                label + ": " + want.path + " has stride " +
                    std::to_string(resolved->stride) + ", expected " +
                    std::to_string(want.stride));
            const auto byteOffset = def.byteOffsetOf(want.path);
            require(
                byteOffset && *byteOffset == want.byteOffset,
                label + ": " + want.path + " is byte " +
                    std::to_string(byteOffset ? *byteOffset : 0) + ", expected " +
                    std::to_string(want.byteOffset));
        }
    }
}

int main()
{
    try
    {
        const std::string fixtures = "tests/game_server/Fixtures/";

        // THE GOLDENS COME FROM A FOREIGN DECODER. Every index, count, stride and byte
        // offset below was printed by Tools/olfinal/decode-profile-blob.py in the CODOL
        // repo, which walks the same defs SEQUENTIALLY in python and shares no code with
        // the pointer-following walker under test.
        const LinkedDef olfinalImage(fixtures + "mp_playerdata.def.1649370.bin");
        const auto olfinal =
            PlayerDataDef::open(olfinalImage.def(), olfinalImage.readable());
        require(olfinal.has_value(), "the OLfinal def does not open");

        const LinkedDef legacyImage(fixtures + "mp_playerdata.def.3333.bin");
        const auto legacy = PlayerDataDef::open(legacyImage.def(), legacyImage.readable());
        require(legacy.has_value(), "the 3.3.3.3 def does not open");

        checkSchema(
            *olfinal, "OLfinal 1649370", 0x4A6CC345u, 15767u, 3927u,
            {
                { "characterClasses", 605, 12, 14, 13270 },
                { "characterClasses[0].slots", 610, 9, 1, 3858 },
                { "characterClasses[3].slots", 652, 9, 1, 3930 },
                { "weaponClasses", 1607, 60, 37, 4392 },
                { "weaponClasses[0].primaryBase", 1629, 1, 0, 4466 },
                { "weaponClasses[0].secondaryBase", 1636, 1, 0, 4494 },
                { "weaponClasses[0].primaryAttach", 1623, 6, 1, 4442 },
                { "weaponClasses[0].secondaryAttach", 1630, 6, 1, 4470 },
                { "weaponClasses[2].primaryBase", 1703, 1, 0, 4694 },
                { "weaponClasses[7].primaryBase", 1888, 1, 0, 5264 },
            });

        // THE SECOND BUILD IS WHAT MAKES THIS TEST BITE. Six of the eight ordinals
        // EngineBindings used to carry differ here, so a walker that quietly returned the
        // constants it replaced would pass the block above and fail this one.
        checkSchema(
            *legacy, "3.3.3.3", 0xE32D50D6u, 14426u, 3414u,
            {
                { "characterClasses", 576, 12, 10, 13270 },
                { "characterClasses[0].slots", 577, 9, 1, 3858 },
                { "characterClasses[3].slots", 607, 9, 1, 3930 },
                { "weaponClasses", 1154, 60, 36, 4392 },
                { "weaponClasses[0].primaryBase", 1176, 1, 0, 4466 },
                { "weaponClasses[0].secondaryBase", 1183, 1, 0, 4494 },
                { "weaponClasses[0].primaryAttach", 1170, 6, 1, 4442 },
                { "weaponClasses[0].secondaryAttach", 1177, 6, 1, 4470 },
                { "weaponClasses[2].primaryBase", 1248, 1, 0, 4694 },
                { "weaponClasses[7].primaryBase", 1428, 1, 0, 5264 },
            });

        // AND THE TWO DISAGREE, EXPLICITLY. This is the assertion the eight deleted
        // constants failed: every INDEX moved between builds while every BYTE OFFSET
        // stayed put, so reading OLfinal's index 605 out of the 3.3.3.3 table would have
        // produced a perfectly plausible byte offset for an entirely different field.
        for (const auto *const path :
             { "characterClasses", "weaponClasses", "weaponClasses[0].primaryBase" })
        {
            const auto a = olfinal->resolve(path);
            const auto b = legacy->resolve(path);
            require(a && b, std::string(path) + " must resolve in both builds");
            require(
                a->index != b->index,
                std::string(path) + " has the same index in both builds; the walker is "
                                    "not reading the def it was given");
            require(
                olfinal->byteOffsetOf(path) == legacy->byteOffsetOf(path),
                std::string(path) + " must land on the same byte in both builds");
        }

        // A PATH THAT DOES NOT EXIST MUST FAIL, NOT GUESS. `secondaryAttach` was called
        // absent from this def for a whole section and read by arithmetic instead; a
        // resolver that answers for a name the def does not carry would have made that
        // mistake unfindable.
        for (const auto *const path :
             { "", "notAProperty", "characterClasses.slots", "characterClasses[12].slots",
               "weaponClasses[60].primaryBase", "weaponClasses[0].primaryBase.slots",
               "weaponClasses[0].primaryBase[0]", "weaponClasses[0].notAProperty" })
        {
            require(
                !olfinal->resolve(path).has_value(),
                std::string("\"") + path + "\" must not resolve");
        }

        // A STORED PROFILE SAYS WHICH DEF WROTE IT, AND THAT IS NOT DECORATION.
        //
        // The document's header is {contentHash, version, formatChecksum}, and the two
        // fixtures below prove it discriminates: a profile the OLfinal client saved
        // declares 0x4A6CC345, while the .pubinfo seeds shipped in the LobbyServer's
        // Resources declare 0xE32D50D6 -- they are 3.3.3.3-era documents. BOTH decode
        // "successfully" under either def, because the byte offsets of these particular
        // fields agree across the two builds; only the checksum tells them apart. I
        // decoded the seed with the OLfinal def while writing this file and got entirely
        // plausible numbers for exactly that reason.
        //
        // THE STORED DOCUMENT SITS FOUR BYTES LATER THAN THE CLIENT'S LIVE BUFFER, and
        // the header says why: the live buffer starts at `version`, and the stored copy
        // prepends the content hash. The shift was measured long before the header was
        // understood -- at shift 0 these fields read as a profile with no weapons.
        constexpr std::size_t StoredDocumentShift = 4;
        constexpr std::size_t DocumentVersionOffset = 4;
        constexpr std::size_t DocumentFormatChecksumOffset = 8;
        const auto documentU32 = [](const std::vector<std::uint8_t> &blob,
                                    const std::size_t at) {
            require(at + 4 <= blob.size(), "a document read runs off the end");
            std::uint32_t value = 0;
            std::memcpy(&value, blob.data() + at, sizeof(value));
            return value;
        };

        const auto document = readFile(fixtures + "profile-69420.olfinal.document.bin");
        const auto seed = readFile(fixtures + "profile-seed.3333.document.bin");
        require(
            document.size() == 0x8000 && seed.size() == 0x8000,
            "a stored profile document is not 0x8000 bytes");
        require(
            documentU32(document, DocumentVersionOffset) == olfinal->version() &&
                documentU32(seed, DocumentVersionOffset) == legacy->version(),
            "both documents should declare the def version their build ships (233)");
        require(
            documentU32(document, DocumentFormatChecksumOffset) ==
                olfinal->formatChecksum(),
            "the live save must declare the OLfinal def's formatChecksum");
        require(
            documentU32(seed, DocumentFormatChecksumOffset) == legacy->formatChecksum(),
            "the shipped .pubinfo seeds are 3.3.3.3 documents, and must say so");
        require(
            olfinal->formatChecksum() != legacy->formatChecksum(),
            "the two defs must be distinguishable by checksum at all");

        // END TO END, ON A PROFILE THE CLIENT ACTUALLY SAVED. Resolving by name and then
        // converting through the def's own table has to land on the weapons account 69420
        // is holding. These are not merely the python decoder's numbers: 545, 569, 11857
        // and 10028 are four values the RUNNING PLUGIN printed for this same profile,
        // recorded before this walker existed. A decode that disagrees with the engine
        // about a value the engine published is wrong however tidy its table walk looks.
        const auto stored = [&](const std::string_view path) {
            const auto byteOffset = olfinal->byteOffsetOf(path);
            require(
                byteOffset.has_value(),
                std::string(path) + " does not resolve against the OLfinal def");
            return documentU32(document, *byteOffset + StoredDocumentShift);
        };
        struct Saved { const char *path; std::uint32_t value; };
        for (const auto &[path, value] : std::initializer_list<Saved>{
                 { "characterClasses[0].slots[0]", 545 },
                 { "characterClasses[1].slots[0]", 569 },
                 { "weaponClasses[0].primaryBase", 11857 },
                 { "weaponClasses[0].secondaryBase", 10028 },
                 { "weaponClasses[1].primaryBase", 12820 },
                 { "weaponClasses[1].secondaryBase", 10049 },
                 { "weaponClasses[2].primaryBase", 10007 },
                 { "weaponClasses[4].primaryBase", 10001 },
                 // AND THE ATTACHMENT ARRAY THE SOURCE SAID DID NOT EXIST. This class
                 // carries nothing on its primary and one item on its SECONDARY, which
                 // is the array EngineBindings' comment declared absent from this def.
                 { "weaponClasses[0].primaryAttach[0]", 0 },
                 { "weaponClasses[0].secondaryAttach[0]", 25703 },
                 { "weaponClasses[0].secondaryAttach[1]", 0 },
             })
        {
            const auto got = stored(path);
            require(
                got == value,
                std::string("69420's ") + path + " reads " + std::to_string(got) +
                    ", expected " + std::to_string(value));
        }

        // A def that is not this schema must be refused rather than half-read.
        const std::vector<std::uint8_t> rubbish(PlayerDataDef::Layout::HeaderBytes, 0);
        require(
            !PlayerDataDef::open(
                 rubbish.data(),
                 [&](const void *const address, const std::size_t length) {
                     const auto *const at = static_cast<const std::uint8_t *>(address);
                     const auto *const end = rubbish.data() + rubbish.size();
                     return at >= rubbish.data() && at <= end &&
                         length <= static_cast<std::size_t>(end - at);
                 })
                 .has_value(),
            "an all-zero header must not open as a def");
        require(
            !PlayerDataDef::open(nullptr, olfinalImage.readable()).has_value(),
            "a null def must not open");

        std::cout << "PlayerDataDef tests passed\n";
        return EXIT_SUCCESS;
    }
    catch (const std::exception &error)
    {
        std::cerr << "PlayerDataDef tests failed: " << error.what() << '\n';
        return EXIT_FAILURE;
    }
}
