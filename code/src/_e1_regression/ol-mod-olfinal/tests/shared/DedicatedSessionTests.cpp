#include "shared/DedicatedSession.hpp"

#include <stdexcept>

namespace
{
    void require(const bool condition, const char *const message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }

    OlMod::DedicatedSession::LoadoutRequest fixtureLoadout()
    {
        using namespace OlMod::DedicatedSession;
        LoadoutRequest request{
            .characterIndex = 3,
            .classMask = 0x03,
            .characterItemIds = { 545, 789, 792 },
        };
        request.classes[0].weapons[0] = {
            .itemId = 10053,
            .attachmentItemIds = { 20379, 20782 },
        };
        request.classes[0].weapons[1] = {
            .itemId = 10145,
            .attachmentItemIds = { 25684 },
        };
        request.classes[1].weapons[0] = { .itemId = 10001 };
        request.classes[1].weapons[1] = { .itemId = 10049 };
        request.classes[0].perkItemIds = { 60041, 60044, 1, 1, 1, 1 };
        request.classes[1].perkItemIds = { 1, 60042, 1, 1, 1, 1 };
        request.classes[0].equipment = { .itemIds = {60001, 60006}, .doubleAmmoMask = 1 };
        request.classes[1].equipment = { .itemIds = {1, 60005}, .doubleAmmoMask = 2 };
        request.rewardItemIds = { 60077, 60081, 60084 };
        return request;
    }
}

void runDedicatedSessionTests()
{
    using namespace OlMod::DedicatedSession;
    const auto loadout = fixtureLoadout();
    require(valid(loadout), "item-ID loadout fixture is valid");
    const auto encodedLoadout = encode(loadout);
    const auto decodedLoadout = decodeLoadout(encodedLoadout);
    require(decodedLoadout && *decodedLoadout == loadout,
        "loadout descriptor roundtrips without asset indexes");
    // Version 6 preserves perks but has no equipment fields.
    auto version7 = encodedLoadout;
    version7.resize(version7.size() - RewardSlotCount * sizeof(std::uint32_t));
    version7[4] = 7;
    auto expectedVersion7 = loadout;
    expectedVersion7.rewardItemIds = {};
    require(decodeLoadout(version7) == expectedVersion7,
        "version 7 captures have no invented equipped rewards");
    auto truncatedRewards = encodedLoadout;
    truncatedRewards.pop_back();
    require(!decodeLoadout(truncatedRewards), "truncated reward slots are rejected");
    auto version6 = version7;
    for (std::size_t index = LoadoutClassCount; index-- > 0;)
    {
        const auto start = 8 + 56 + index * 92 + 80;
        version6.erase(version6.begin() + start, version6.begin() + start + 12);
    }
    version6[4] = 6;
    auto expectedVersion6 = expectedVersion7;
    for (auto &loadoutClass : expectedVersion6.classes)
        loadoutClass.equipment = {};
    require(decodeLoadout(version6) == expectedVersion6,
        "version 6 preserves perks without inventing equipment");
    auto badEquipmentReserved = encodedLoadout;
    badEquipmentReserved[8 + 56 + 80 + 9] = 1;
    require(!decodeLoadout(badEquipmentReserved), "equipment reserved bytes reject skew");
    auto truncatedEquipment = encodedLoadout;
    truncatedEquipment.resize(8 + 56 + 80 + 11);
    require(!decodeLoadout(truncatedEquipment), "truncated equipment is rejected");
    // Version 5 had the same 56-byte prefix and 56-byte weapon blocks,
    // without the six perk items following each class.
    auto legacy = version6;
    for (std::size_t index = LoadoutClassCount; index-- > 0;)
    {
        const auto start = 8 + 56 + index * 80 + 56;
        legacy.erase(legacy.begin() + start, legacy.begin() + start + 24);
    }
    legacy[4] = 5;
    auto expectedLegacy = expectedVersion6;
    for (auto &loadoutClass : expectedLegacy.classes)
        loadoutClass.perkItemIds = {};
    require(decodeLoadout(legacy) == expectedLegacy,
        "version 5 captures decode with no invented perks");
    auto truncatedPerks = encodedLoadout;
    truncatedPerks.resize(8 + 56 + 56 + 23);
    require(!decodeLoadout(truncatedPerks), "truncated perk slots are rejected");

    const ClientSessionCapture capture{
        .booking = {
            .playlistId = 26,
            .rotationIndex = 0,
            .mapName = "mp_crash_tropical",
            .gameType = "sd",
        },
        .loadout = loadout,
    };
    const auto encodedCapture = encode(capture);
    const auto decodedCapture = decodeClientSessionCapture(encodedCapture);
    require(decodedCapture && *decodedCapture == capture,
        "client capture roundtrips native booking selection and item IDs");

    SessionStart session{
        .bookingCommand = "mmstart 26 0",
        .booking = capture.booking,
        .matchRules = {
            .playlistVersion = 796,
            .roundSwitch = 1,
            .roundLimit = 7,
            .winLimit = 4,
        },
        .members = {
            {
                .userId = 0x1100001DEADC0DEULL,
                .username = "Alwaysoffline",
                .loadout = loadout,
            },
            {
                .userId = 0x1100001DEADC0DFULL,
                .username = "SecondPlayer",
                .loadout = loadout,
            },
        },
    };
    session.members[1].loadout.rewardItemIds = { 60078, 60079, 60082 };
    const auto encodedSession = encode(session);
    const auto decodedSession = decodeSessionStart(encodedSession);
    require(decodedSession && *decodedSession == session,
        "session start roundtrips identity, booking, and requested item IDs");

    auto invalid = loadout;
    invalid.rewardItemIds[0] = 65536;
    require(!valid(invalid), "reward item IDs obey the catalog range");
    invalid = loadout;
    invalid.classes[2].equipment.itemIds[0] = 60001;
    require(!valid(invalid), "absent classes cannot carry equipment");
    invalid = loadout;
    invalid.classes[0].equipment.itemIds[0] = 65536;
    require(!valid(invalid), "equipment IDs obey the catalog range");
    invalid = loadout;
    invalid.classes[0].equipment.doubleAmmoMask = 4;
    require(!valid(invalid), "unknown equipment flags are rejected");
    invalid = loadout;
    invalid.classes[2].perkItemIds[0] = 60041;
    require(!valid(invalid), "absent classes cannot carry perks");
    invalid = loadout;
    invalid.classes[0].perkItemIds[0] = 65536;
    require(!valid(invalid), "perk item IDs obey the item catalog range");
    invalid = loadout;
    invalid.classMask = 0;
    require(!valid(invalid) && encode(invalid).empty(),
        "descriptor rejects an empty approved class mask");
    invalid = loadout;
    invalid.classes[2].weapons[0].itemId = 10001;
    require(!valid(invalid), "descriptor rejects items outside the approved class mask");
    invalid = loadout;
    invalid.classes[0].weapons[0].itemId = 0x10000;
    require(!valid(invalid), "descriptor rejects item IDs outside CODOL's 16-bit catalog");

    session.members[0].username = "bad\nname";
    require(!valid(session), "session rejects non-printable usernames");
    session.members[0].username = "Alwaysoffline";
    session.members[1].userId = session.members[0].userId;
    require(!valid(session), "session rejects duplicate member identities");
    session.members[1].userId = 0x1100001DEADC0DFULL;
    session.booking.mapName = "../mp_crash_tropical";
    require(!valid(session), "session rejects an invalid captured map name");
    session.booking = capture.booking;
    session.booking.gameType = "cha";
    require(!valid(session), "CHA session rejects absent authoritative match rules");
    session.matchRules = {
        .playlistVersion = 796,
        .scoreLimit = 100,
        .timeLimitMinutes = 20,
    };
    require(valid(session), "CHA session accepts bounded authoritative match rules");
    session.booking = capture.booking;
    session.matchRules = {
        .playlistVersion = 796,
        .roundSwitch = 1,
        .roundLimit = 7,
        .winLimit = 4,
    };
    require(valid(session), "SD session accepts bounded authoritative round rules");
    session.matchRules.winLimit = 8;
    require(!valid(session), "SD session rejects a win limit above its round limit");
    auto malformed = encodedSession;
    malformed.front() ^= 0xFF;
    require(!decodeSessionStart(malformed), "session rejects an invalid payload magic");
    malformed = encodedSession;
    malformed.push_back(0);
    require(!decodeSessionStart(malformed), "session rejects trailing bytes");
    malformed = encodedSession;
    malformed.pop_back();
    require(!decodeSessionStart(malformed), "session rejects truncated strings");
}
