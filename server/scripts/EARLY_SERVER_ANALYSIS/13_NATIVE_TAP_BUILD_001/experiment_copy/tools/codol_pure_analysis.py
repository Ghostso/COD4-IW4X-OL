"""Compare the reference's captured cp command with local IWD checksum candidates.

Offline analysis, not authentication. Imports trusted alpha0022 netchan_ack and
reads only ZIP central directories. Requires PyCryptodome for MD4 candidates.
No session keys, archive contents, or live process memory are read.
"""
import argparse
import functools
import json
from pathlib import Path
import struct
import sys
import zlib

from Crypto.Hash import MD4


def archive_crcs(path):
    with path.open('rb') as stream:
        stream.seek(-min(path.stat().st_size, 65557), 2)
        tail = stream.read()
        offset = tail.rfind(b'PK\x05\x06')
        if offset < 0 or len(tail) - offset < 22:
            raise ValueError(f'{path.name}: ZIP end record missing')
        end = struct.unpack_from('<4s4H2IH', tail, offset)
        if end[1] or end[2] or end[3] != end[4] or end[4] == 65535:
            raise ValueError(f'{path.name}: unsupported split or ZIP64 directory')
        if offset + 22 + end[7] != len(tail) or end[5] > path.stat().st_size:
            raise ValueError(f'{path.name}: invalid ZIP directory bounds')
        stream.seek(end[6])
        data = stream.read(end[5])
    position, crcs = 0, []
    for _ in range(end[4]):
        if data[position:position + 4] != b'PK\x01\x02' or position + 46 > len(data):
            raise ValueError(f'{path.name}: invalid central directory record')
        crc, _, size = struct.unpack_from('<III', data, position + 16)
        name, extra, comment = struct.unpack_from('<HHH', data, position + 28)
        position += 46 + name + extra + comment
        if position > len(data):
            raise ValueError(f'{path.name}: truncated central directory record')
        if size:
            crcs.append(crc)
    if position != len(data):
        raise ValueError(f'{path.name}: trailing central directory bytes')
    return struct.pack('<' + 'I' * len(crcs), *crcs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', required=True, type=Path)
    parser.add_argument('--main', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.reference.resolve()))
    import netchan_ack
    decoded = netchan_ack.decode_inbound(netchan_ack._REAL_INBOUND, brute_check=False)
    command = next(text for _, text in decoded['cmds'] if text.startswith('cp @ '))
    signed = [int(token) for token in command.split()[2:]]
    if len(signed) < 1 or any(not -(1 << 31) <= value < (1 << 31) for value in signed):
        raise ValueError('Invalid signed checksum list in reference fixture')
    values = [value & 0xffffffff for value in signed]
    feed = functools.reduce(int.__xor__, values, len(values) - 1)
    archives = []
    for path in sorted(args.main.glob('*.iwd')):
        raw = archive_crcs(path)
        candidates = {'crc32_feed0': zlib.crc32(raw)}
        for label, data in [('md4', raw), ('md4_prefix_feed0', bytes(4) + raw)]:
            candidates[label] = functools.reduce(int.__xor__, struct.unpack('<4I', MD4.new(data).digest()))
        archives.append({
            'archive': path.name, 'nonempty_entries': len(raw) // 4,
            'candidate_checksums': candidates,
            'matches': [{'algorithm': name, 'client_index': index}
                        for name, checksum in candidates.items()
                        for index, value in enumerate(values[:-1]) if value == checksum],
        })
    if not archives:
        raise ValueError('No IWD archives found')
    result = {
        'scope': 'One historical alpha0022 netchan_ack._REAL_INBOUND fixture versus current local IWD central directories',
        'warning': 'An aggregate identity does not establish the client checksum algorithm or authenticate assets.',
        'captured_signed_integers': signed,
        'candidate_checksum_count': len(values) - 1,
        'inferred_feed_if_xor_count_aggregate': feed,
        'archive_count': len(archives),
        'match_count': sum(len(row['matches']) for row in archives),
        'archives': archives,
    }
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items()
                      if key.endswith('_count') or key == 'inferred_feed_if_xor_count_aggregate'}))


if __name__ == '__main__':
    main()
