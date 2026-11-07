#!/usr/bin/env python3
r"""Read out.exe's character-item tables from a live CLIENT. READ ONLY, calls nothing.

WHAT THIS ANSWERS. Section 48c's slot mapping, both halves of it.

    sub_619E90 tail   decodes record[0] on its own and calls sub_619AD0(record, id)
    sub_619AD0 pass 1 for every OCCUPIED record entry: flags[entry] = 1, then
                      sub_810270(id) -> mark flags[category] = 1 for every category it claims
    sub_619AD0 pass 2 for every EMPTY entry whose flag is still 0: look up a DEFAULT and
                      write it in with sub_810B20

`flags` is TWELVE dwords at ebp-0x34 (memset 0x2C from ebp-0x30, plus [ebp-0x34] cleared on
its own), so a "category" is a RECORD ENTRY INDEX in 0..11 -- the same twelve
`CharacterRecordToSelectionName` maps onto eleven names.

--dump    reads sub_810270's table: which EXTRA entries an item claims.
--resolve reads the chain pass 2 uses, which is where the defaults live:

    id16    = itemId & 0xFFFF
    lookup  = (uint16)(bucketOffsets[id16 / 1000] + id16 % 1000)   < lookupCount
    defIdx  = (uint16)lookupTable[lookup]                          nonzero, < definitionCount
    def     = definitions + defIdx * 40                            CharacterItemDefinitionSize
    def[+5] == 2                                                   "this is a character"
    record  = characterRecords + (uint16)def[+2] * 0x34            < characterRecordCount
    default[slot] = (uint16)record[0xC + slot * 2]                 TWELVE of them

**The last line is the piece section 48 was missing.** A character carries a default item per
record slot, and pass 2 writes those into every entry the profile left empty -- which is why a
profile with only slot 0 set is not a broken profile. It is the normal case.

WHY THIS IS LIVE AND NOT OFFLINE. Every COUNT is in the image and reads straight out of the
dump (lookupCount 23213, definitionCount 21741, characterRecordCount 54, and bucketOffsets
itself). All three POINTERS are heap -- 0x5C3A1584, 0x5C4EFF08, 0x5C89BE98 -- and the dump's
own region map stops at 0xFC8E000. sub_810270's table is heap too. Reading the CSVs those are
built from instead needs the zone's block-pointer model: a StringTable cell string that is not
0xFFFFFFFF is a (block << 28) | offset reference, and no constant delta maps them onto the
file -- checked across 645 pointers and 33 deltas, best 26 of 200.

READ ONLY, ON PURPOSE. sub_810270 would lazily build its table if it were missing and calling
it is one line -- section 65o is the reason not to. A native call from a Frida thread in this
process put a fault in the frame thread and killed the client, and `__try` is not a safety net
here because CODOL's own crash handler takes the fault first. If a table is not built, this
says so and stops.

NEVER RUN THIS AGAINST THE DEDICATED PROCESS. It refuses by itself: the dedicated is the
out.exe listening on the control port; the client is the one on the bridge port.

    python tools/runtime/CodolCharacterCategoryDump.py --pid <client> --dump
    python tools/runtime/CodolCharacterCategoryDump.py --pid <client> --resolve
"""

import argparse
import json
import re
import subprocess
import sys

import frida

IMAGE_BASE = 0x400000
IMAGE_NAME = "out.exe"

# VA -> RVA computed in python, never by hand (the handoff's rule, and the reason for it).
TABLE_POINTER_RVA = 0x84ABB5C - IMAGE_BASE   # 0x080ABB5C
RECORD_COUNT_RVA = 0x8269C5C - IMAGE_BASE    # 0x07E69C5C
RECORD_SIZE = 0x8C
MAX_CATEGORIES = (RECORD_SIZE - 8) // 4      # 33

# Read off sub_619AD0's second loop at 0x619B60, instruction by instruction.
BUCKET_OFFSETS_VA = 0x779584C
LOOKUP_COUNT_VA = 0x7795848
LOOKUP_POINTER_VA = 0x7795844
DEFINITION_COUNT_VA = 0x7795840
DEFINITIONS_POINTER_VA = 0x779583C
CHARACTER_RECORD_COUNT_VA = 0x7798900
CHARACTER_RECORDS_POINTER_VA = 0x77988FC
DEFINITION_SIZE = 40
CHARACTER_RECORD_SIZE = 0x34
CHARACTER_RECORD_DEFAULTS_OFFSET = 0xC
CHARACTER_RECORD_SLOTS = 12
CHARACTER_DEFINITION_TYPE = 2
BUCKET_SIZE = 1000

DEDICATED_CONTROL_PORT = 28961
CLIENT_BRIDGE_PORT = 28962

# The twelve this account owns, from Tools/olfinal/decode-profile-blob.py --characters.
CHARACTER_ITEM_IDS = [545, 569, 592, 649, 686, 789, 792, 1945, 1978, 2056, 2105, 2127]

DUMP_SCRIPT = """
const image = Process.getModuleByName(%(image)s);
const table = image.base.add(%(tableRva)d).readPointer();
const count = image.base.add(%(countRva)d).readS32();
if (table.isNull() || count <= 0 || count > 100000) {
    send({ type: 'not_built', table: table.toString(), count: count });
} else {
    const records = [];
    for (let i = 0; i < count; i += 1) {
        const at = table.add(i * %(recordSize)d);
        const categoryCount = at.add(4).readS32();
        const categories = [];
        const bounded = Math.max(0, Math.min(categoryCount, %(maxCategories)d));
        for (let k = 0; k < bounded; k += 1) categories.push(at.add(8 + 4 * k).readS32());
        records.push({ item: at.readS32(), count: categoryCount, categories: categories,
                       truncated: categoryCount > %(maxCategories)d });
    }
    send({ type: 'table', table: table.toString(), count: count, records: records });
}
"""

RESOLVE_SCRIPT = """
const image = Process.getModuleByName(%(image)s);
function g32(va) { return image.base.add(va - %(imageBase)d).readU32(); }
function g16(va) { return image.base.add(va - %(imageBase)d).readU16(); }
const lookupCount = g32(%(lookupCountVa)d);
const lookupPointer = ptr(g32(%(lookupPointerVa)d));
const definitionCount = g32(%(definitionCountVa)d);
const definitions = ptr(g32(%(definitionsPointerVa)d));
const recordCount = g32(%(recordCountVa)d);
const records = ptr(g32(%(recordsPointerVa)d));

function slotDefaults(record) {
    const out = [];
    for (let s = 0; s < %(slots)d; s += 1)
        out.push(record.add(%(defaultsOffset)d + s * 2).readU16());
    return out;
}

function nameOf(itemId) {
    if (!itemId) return null;
    const id = itemId & 0xFFFF;
    const index = (g16(%(bucketOffsetsVa)d + Math.floor(id / %(bucketSize)d) * 2)
                   + (id %% %(bucketSize)d)) & 0xFFFF;
    if (index >= lookupCount) return null;
    const defIndex = lookupPointer.add(index * 2).readU16();
    if (defIndex === 0 || defIndex >= definitionCount) return null;
    try {
        return definitions.add(defIndex * %(definitionSize)d).add(8).readPointer().readCString();
    } catch (e) { return null; }
}

function resolve(itemId) {
    const id = itemId & 0xFFFF;
    const bucket = Math.floor(id / %(bucketSize)d);
    const step = { item: itemId, bucket: bucket };
    const index = (g16(%(bucketOffsetsVa)d + bucket * 2) + (id %% %(bucketSize)d)) & 0xFFFF;
    step.lookupIndex = index;
    if (index >= lookupCount) { step.fail = 'lookupIndex >= lookupCount'; return step; }
    const defIndex = lookupPointer.add(index * 2).readU16();
    step.definitionIndex = defIndex;
    if (defIndex === 0) { step.fail = 'definitionIndex is 0'; return step; }
    if (defIndex >= definitionCount) { step.fail = 'defIndex >= definitionCount'; return step; }
    const definition = definitions.add(defIndex * %(definitionSize)d);
    step.type = definition.add(5).readU8();
    try { step.name = definition.add(8).readPointer().readCString(); }
    catch (e) { step.name = null; }
    if (step.type !== %(characterType)d) {
        step.fail = 'definition type is not a character';
        return step;
    }
    const recordIndex = definition.add(2).readU16();
    step.recordIndex = recordIndex;
    if (recordIndex >= recordCount) { step.fail = 'recordIndex >= recordCount'; return step; }
    const record = records.add(recordIndex * %(recordSizeChar)d);
    step.head = [record.readU16(), record.add(2).readU16(), record.add(4).readU16(),
                 record.add(6).readU16(), record.add(8).readU16(), record.add(10).readU16()];
    step.defaults = slotDefaults(record);
    step.names = step.defaults.map(nameOf);
    return step;
}

const all = [];
for (let i = 0; i < recordCount; i += 1) {
    const record = records.add(i * %(recordSizeChar)d);
    const defaults = slotDefaults(record);
    all.push({ index: i, head: [record.readU16(), record.add(2).readU16()],
               defaults: defaults, names: defaults.map(nameOf) });
}
send({ type: 'resolved', lookupCount: lookupCount, definitionCount: definitionCount,
       recordCount: recordCount, resolved: %(wanted)s.map(resolve), characters: all });
"""


def listening_pids():
    """Which pid owns which port, so the dedicated cannot be picked by mistake."""
    owners = {}
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True,
                             text=True, timeout=30).stdout
    except Exception:
        return owners
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[3].upper() != "LISTENING":
            continue
        match = re.search(r":(\d+)$", parts[1])
        if match:
            owners.setdefault(int(match.group(1)), set()).add(int(parts[4]))
    return owners


def run(pid, source):
    payloads = []
    session = frida.get_local_device().attach(pid)
    script = session.create_script(source)
    script.on("message", lambda message, data: payloads.append(
        message.get("payload", message)))
    try:
        script.load()
    finally:
        script.unload()
        session.detach()
    if not payloads:
        raise SystemExit("the script produced nothing")
    return payloads[0]


def dump_mode(args):
    result = run(args.pid, DUMP_SCRIPT % {
        "image": json.dumps(IMAGE_NAME),
        "tableRva": TABLE_POINTER_RVA,
        "countRva": RECORD_COUNT_RVA,
        "recordSize": RECORD_SIZE,
        "maxCategories": MAX_CATEGORIES,
    })
    if result.get("type") == "not_built":
        print("THE TABLE IS NOT BUILT: pointer %s, count %s. sub_80F800 is lazy, on the "
              "first sub_810270, and nothing here calls it."
              % (result.get("table"), result.get("count")))
        return 2
    records = result["records"]
    print("table at %s, %d records of 0x%X bytes"
          % (result["table"], result["count"], RECORD_SIZE))
    byItem = {r["item"]: r for r in records}
    print("THE TWELVE CHARACTER ITEMS THIS ACCOUNT OWNS:")
    for itemId in CHARACTER_ITEM_IDS:
        record = byItem.get(itemId)
        if record:
            print("  %-6d count=%d categories=%s"
                  % (itemId, record["count"], record["categories"]))
        else:
            print("  %-6d NOT IN THE TABLE -- claims no extra entry, which is what a base "
                  "character does" % itemId)
    keys = sorted(r["item"] for r in records)
    print("key range %d..%d, %d distinct of %d"
          % (keys[0], keys[-1], len(set(keys)), len(keys)))
    print("distinct category counts: %s" % sorted({r["count"] for r in records}))
    seen = sorted({c for r in records for c in r["categories"]})
    print("every category index seen: %s   (record entries, 0..11)" % seen)
    if args.out:
        json.dump(result, open(args.out, "w", encoding="utf-8"), indent=1)
        print("full JSON -> %s" % args.out)
    return 0


def resolve_mode(args):
    result = run(args.pid, RESOLVE_SCRIPT % {
        "image": json.dumps(IMAGE_NAME),
        "imageBase": IMAGE_BASE,
        "bucketOffsetsVa": BUCKET_OFFSETS_VA,
        "lookupCountVa": LOOKUP_COUNT_VA,
        "lookupPointerVa": LOOKUP_POINTER_VA,
        "definitionCountVa": DEFINITION_COUNT_VA,
        "definitionsPointerVa": DEFINITIONS_POINTER_VA,
        "recordCountVa": CHARACTER_RECORD_COUNT_VA,
        "recordsPointerVa": CHARACTER_RECORDS_POINTER_VA,
        "definitionSize": DEFINITION_SIZE,
        "recordSizeChar": CHARACTER_RECORD_SIZE,
        "defaultsOffset": CHARACTER_RECORD_DEFAULTS_OFFSET,
        "slots": CHARACTER_RECORD_SLOTS,
        "characterType": CHARACTER_DEFINITION_TYPE,
        "bucketSize": BUCKET_SIZE,
        "wanted": json.dumps(CHARACTER_ITEM_IDS),
    })
    if result.get("type") != "resolved":
        raise SystemExit("resolve produced %r" % (result,))
    print("lookupCount=%d definitionCount=%d characterRecordCount=%d"
          % (result["lookupCount"], result["definitionCount"], result["recordCount"]))
    print("")
    print("THE TWELVE CHARACTERS THIS ACCOUNT OWNS, RESOLVED:")
    for step in result["resolved"]:
        if step.get("fail"):
            print("  item %-6d bucket=%-2d lookupIndex=%-6s defIndex=%-6s type=%-4s FAIL %s"
                  % (step["item"], step["bucket"], step.get("lookupIndex"),
                     step.get("definitionIndex"), step.get("type"), step["fail"]))
            continue
        print("  item %-6d def=%-6d rec=%-3d name=%s"
              % (step["item"], step["definitionIndex"], step["recordIndex"],
                 step.get("name")))
        for slot, (value, name) in enumerate(zip(step["defaults"], step["names"])):
            if value:
                print("        slot %2d -> %-6d %s" % (slot, value, name))
    print("")
    print("ALL %d CHARACTER RECORDS, twelve per-slot defaults each:" % result["recordCount"])
    for character in result["characters"]:
        filled = ["%d:%s" % (s, n) for s, (v, n)
                  in enumerate(zip(character["defaults"], character["names"])) if v]
        print("  [%2d] %s" % (character["index"], "  ".join(filled)))
    if args.out:
        json.dump(result, open(args.out, "w", encoding="utf-8"), indent=1)
        print("full JSON -> %s" % args.out)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True, help="the CLIENT out.exe pid")
    parser.add_argument("--out", help="write the full JSON here as well")
    parser.add_argument("--dump", action="store_true",
                        help="sub_810270's item -> extra-record-entry table")
    parser.add_argument("--resolve", action="store_true",
                        help="each character's definition and its TWELVE per-slot defaults")
    parser.add_argument("--allow-any-pid", action="store_true",
                        help="skip the dedicated-process refusal. There is no good reason.")
    args = parser.parse_args()

    owners = listening_pids()
    dedicated = owners.get(DEDICATED_CONTROL_PORT, set())
    bridge = owners.get(CLIENT_BRIDGE_PORT, set())
    print("port %d (dedicated control) -> %s"
          % (DEDICATED_CONTROL_PORT, sorted(dedicated) or "nobody"))
    print("port %d (client bridge)     -> %s"
          % (CLIENT_BRIDGE_PORT, sorted(bridge) or "nobody"))
    if args.pid in dedicated and not args.allow_any_pid:
        raise SystemExit(
            "REFUSING: pid %d is listening on %d, so it is the DEDICATED process. Attaching "
            "Frida to it puts a fault in the frame thread. The client is the pid on %d."
            % (args.pid, DEDICATED_CONTROL_PORT, CLIENT_BRIDGE_PORT))
    if bridge and args.pid not in bridge and not args.allow_any_pid:
        print("WARNING: pid %d does not own the bridge port; %s does."
              % (args.pid, sorted(bridge)))
    print("")

    if args.resolve:
        return resolve_mode(args)
    return dump_mode(args)


if __name__ == "__main__":
    sys.exit(main())
