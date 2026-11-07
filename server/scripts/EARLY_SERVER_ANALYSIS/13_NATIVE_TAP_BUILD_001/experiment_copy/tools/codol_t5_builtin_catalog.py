"""Extract the static GSC resolver tables from the locally verified T5 server.

Offline analysis only. Requires pefile. Addresses are pinned to the executable
hash; this does not load code, attach to a process, or implement any builtin.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

import pefile


EXPECTED_SHA256 = '4e325afa62cd2e1c2cea2af42cfe80282233f2e25706b865a51b3ded0842eff5'
# Scr_GetMethod at 0x6615c0 tries these specialized tables in this order,
# then BuiltIn_GetMethod. Specialized resolvers ignore the third table word:
# the outer resolver initializes the returned developer flag to zero.
TABLES = [
    ('function', 0x660a50, 0xe08510, 383, True),
    ('method', 0x60f9a0, 0xcb4540, 154, False),
    ('method', 0x665cd0, 0xcc8550, 18, False),
    ('method', 0x67d110, 0xcc8e30, 89, False),
    ('method', 0x620a30, 0xcb8480, 26, False),
    ('method', 0x640b30, 0xcbffa0, 27, False),
    ('method', 0x919ac0, 0xd359d8, 77, False),
    ('method', 0x661680, 0xe09708, 234, True),
]


def extract(path):
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError('Unsupported T5 executable: resolver addresses require the verified SHA-256')
    pe = pefile.PE(data=data)
    base = pe.OPTIONAL_HEADER.ImageBase
    entries, seen = [], set()
    for kind, resolver, table, count, uses_developer in TABLES:
        for index in range(count):
            address = table + index * 12
            name_va, function, flags = struct.unpack('<III', pe.get_data(address - base, 12))
            raw = pe.get_data(name_va - base, 256)
            end = raw.find(b'\0')
            if end < 1:
                raise ValueError(f'Unterminated name at {address:#x}')
            name = raw[:end].decode('ascii')
            section = pe.get_section_by_rva(function - base)
            if not re.fullmatch(r'[a-zA-Z_][a-zA-Z_0-9]*', name) or flags not in (0, 1):
                raise ValueError(f'Invalid builtin record at {address:#x}')
            if section is None or not section.Characteristics & 0x20000000:
                raise ValueError(f'Non-executable builtin target at {address:#x}')
            key = kind, name.lower()
            entries.append({
                'name': name.lower(), 'kind': kind,
                'resolver_va': hex(resolver), 'record_va': hex(address),
                'function_va': hex(function), 'table_developer_flag': flags,
                'developer_only': bool(flags) if uses_developer else False,
                'selected_by_resolver': key not in seen,
            })
            seen.add(key)
    return {
        'scope': 'Static server GSC function and method resolver tables in this T5 executable; not other builds or client scripts',
        'executable_sha256': digest,
        'record_count': len(entries),
        'resolved_function_count': sum(kind == 'function' for kind, _ in seen),
        'resolved_method_count': sum(kind == 'method' for kind, _ in seen),
        'entries': entries,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = extract(args.executable)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k.endswith('_count')}))


if __name__ == '__main__':
    main()
