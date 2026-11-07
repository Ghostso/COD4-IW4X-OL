"""Offline schema inventory from a trusted alpha0022 zone reader.

Follows the native replay_structured_data stream order. No live process or
profile files are read. Raw type/offset words are retained without guessing
their semantics. This is analysis input for a native definition loader.
"""
import argparse
import json
import struct
import sys
from pathlib import Path


def decode(blob):
    cursor = 0

    def records(count, words):
        nonlocal cursor
        size = count * words * 4
        if count > 1000000 or size > len(blob) - cursor:
            raise ValueError('Truncated or oversized schema records')
        rows = [struct.unpack_from('<' + 'I' * words, blob, cursor + i * words * 4)
                for i in range(count)]
        cursor += size
        return rows

    def string(pointer):
        nonlocal cursor
        if pointer == 0:
            return None
        if pointer != 0xffffffff:
            return None  # Retain the reference in the record for native resolution.
        end = blob.index(b'\0', cursor)
        value = blob[cursor:end].decode('ascii')
        cursor = end + 1
        return value

    name_ptr, count, pointer = records(1, 3)[0]
    name = string(name_ptr)
    if pointer != 0xffffffff:
        raise ValueError('Expected inline definition array')
    definitions = records(count, 15)
    result = []
    for definition in definitions:
        entry = {'version': definition[0], 'format_checksum': definition[1],
                 'root_type_words': definition[10:12], 'size': definition[12]}
        for kind, pair, width, member_width, pointer_word in (
                ('enums', 2, 3, 2, 2), ('structs', 4, 5, 6, 1)):
            n, ptr = definition[pair:pair+2]
            if ptr not in (0, 0xffffffff) or bool(n) != bool(ptr):
                raise ValueError('Invalid schema array reference')
            groups = records(n, width)
            entry[kind] = []
            for group in groups:
                n, ptr = group[0], group[pointer_word]
                if ptr not in (0, 0xffffffff) or bool(n) != bool(ptr):
                    raise ValueError('Invalid schema member array reference')
                members = records(n, member_width)
                entry[kind].append({'words': group, 'members': [
                    {'name': string(member[0]), 'name_reference': member[0],
                     'words': member[1:]} for member in members]})
        for kind, pair in (('indexed_arrays', 6), ('enum_arrays', 8)):
            n, ptr = definition[pair:pair+2]
            if ptr not in (0, 0xffffffff) or bool(n) != bool(ptr):
                raise ValueError('Invalid array-type reference')
            entry[kind] = records(n, 4)
        n, ptr = definition[13:15]
        if ptr not in (0, 0xffffffff) or bool(n) != bool(ptr):
            raise ValueError('Invalid trailing map reference')
        entry['trailing_words'] = [row[0] for row in records(n, 1)]
        result.append(entry)
    if cursor != len(blob):
        raise ValueError('Schema did not consume exact asset boundary')
    return {'name': name, 'bytes': len(blob), 'exact_end': True, 'definitions': result}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    sys.path.insert(0, str(args.reference.resolve()))
    import zone_assets
    zone = zone_assets.open_zone('code_post_gfx_mp')
    asset = next(a for a in zone.by_type(39) if a.name == 'mp/clientmatchdata.def')
    result = decode(asset.blob)
    result['zone'] = 'code_post_gfx_mp'
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'name': result['name'], 'bytes': result['bytes'],
                      'definitions': len(result['definitions']), 'exact_end': True}))


if __name__ == '__main__':
    main()
