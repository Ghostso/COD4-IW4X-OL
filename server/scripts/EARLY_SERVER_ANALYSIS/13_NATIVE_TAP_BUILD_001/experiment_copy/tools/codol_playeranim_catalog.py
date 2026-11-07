"""Extract animation token tables from the measured C1 image without running it."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

SHA256 = 'd990610732258b1d00dd6fe63d6691f294312a2e0562955a01ce16216115390d'
TABLES = {'states': (0xcd8668, 'animStateStr'),
          'movements': (0xcd8678, 'animMoveTypesStr'),
          'events': (0xcd8838, 'animEventTypesStr'),
          'conditions': (0xcd8b28, 'animConditionsStr')}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('executable', type=Path)
    ap.add_argument('--native', type=Path, default=Path('src/asmsource/_bg_animation_mp.asm'))
    ap.add_argument('--output', type=Path, default=Path('docs/CODOL_PLAYERANIM_TABLES.json'))
    ap.add_argument('--movement-include', type=Path)
    ap.add_argument('--condition-include', type=Path)
    ap.add_argument('--event-include', type=Path)
    args = ap.parse_args()
    data = args.executable.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256:
        raise ValueError('C1 hash differs from the measured build; table addresses need revalidation')
    pe = struct.unpack_from('<I', data, 60)[0]
    optional = pe + 24
    base = struct.unpack_from('<I', data, optional + 28)[0]
    section_table = optional + struct.unpack_from('<H', data, pe + 20)[0]
    sections = [struct.unpack_from('<IIII', data, section_table + 40*i + 8)
                for i in range(struct.unpack_from('<H', data, pe + 6)[0])]
    def offset(va):
        rva = va - base
        for _, address, size, raw in sections:
            if address <= rva < address + size:
                return raw + rva - address
        raise ValueError(f'Unbacked address {va:#x}')
    def string(va):
        start = offset(va)
        end = data.index(b'\0', start, start + 128)
        value = data[start:end].decode('ascii')
        if not value or any(ord(c) < 32 for c in value):
            raise ValueError('Invalid token')
        return value.lower()
    native = args.native.read_text(encoding='utf-8')
    labels = dict(re.findall(r'^([\w]+):\s*db "([^"]*)",0$', native, re.M))
    result = {'sha256': digest, 'tables': {}}
    for kind, (address, label) in TABLES.items():
        original = re.search(r'^' + label + r': dd (.*)$', native, re.M).group(1)
        original_names = [labels[t.strip()].lower() for t in original.split(',') if t.strip() in labels]
        rows = []
        for i in range(128):
            ptr, cached_hash = struct.unpack_from('<II', data, offset(address + 8*i))
            if cached_hash != 0xffffffff:
                raise ValueError('Unexpected string-table record')
            if not ptr:
                break
            name = string(ptr)
            rows.append({'index': i, 'name': name,
                         'iw3_index': original_names.index(name) if name in original_names else None})
        else:
            raise ValueError('Unterminated table')
        result['tables'][kind] = {'address': hex(address), 'count': len(rows), 'entries': rows}
    # C1's condition-type/value-table pairs. The two playeranimtype entries
    # reference a runtime-filled weapon/animation type table, not static names.
    for row in result['tables']['conditions']['entries']:
        kind, values = struct.unpack_from('<II', data, offset(0xcd8bc0 + 8*row['index']))
        if kind not in (0, 1):
            raise ValueError('Unknown animation condition storage kind')
        row['storage_kind'] = kind
        row['values_address'] = hex(values)
        if values == 0x1504b80:
            row['runtime_values'] = True
        elif values:
            names = []
            for i in range(128):
                ptr, cached_hash = struct.unpack_from('<II', data, offset(values + 8*i))
                if cached_hash != 0xffffffff:
                    raise ValueError('Unexpected condition value record')
                if not ptr:
                    break
                names.append(string(ptr))
            else:
                raise ValueError('Unterminated condition values')
            row['values'] = names
    extra_conditions = [r for r in result['tables']['conditions']['entries'] if r['iw3_index'] is None]
    if len(extra_conditions) != 9:
        raise ValueError('Unexpected number of new conditions')
    for row in result['tables']['conditions']['entries']:
        row['native_index'] = row['iw3_index'] if row['iw3_index'] is not None else 10 + extra_conditions.index(row)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    if args.condition_include:
        lines = ['; Generated C1 condition extensions; legacy IW3 indices stay unchanged.',
                 '%ifdef CODOL_ANIM_CONDITION_TYPES']
        for row in extra_conditions:
            values = 'weaponStrings' if row.get('runtime_values') else (
                f"codol_anim_values_{row['native_index']}" if row.get('values') else '0')
            lines.append(f"dd {row['storage_kind']}, {values}")
        lines.append('%else')
        lines += [f"dd codol_anim_condition_{r['native_index']}, 0xffffffff" for r in extra_conditions]
        lines.append('dd 0, 0xffffffff')
        for row in extra_conditions:
            idx = row['native_index']
            lines.append(f"codol_anim_condition_{idx}: db \"{row['name']}\",0")
            if row.get('values'):
                lines += ['align 4', f'codol_anim_values_{idx}:']
                lines += [f'dd codol_anim_value_{idx}_{i}, 0xffffffff' for i in range(len(row['values']))]
                lines.append('dd 0, 0xffffffff')
                lines += [f'codol_anim_value_{idx}_{i}: db "{value}",0' for i, value in enumerate(row['values'])]
        lines += ['align 4', '%endif']
        args.condition_include.write_text('\n'.join(lines) + '\n', encoding='ascii')
    if args.event_include:
        rows = result['tables']['events']['entries']
        if len(rows) != 24 or any(row['iw3_index'] != row['index'] for row in rows[:21]):
            raise ValueError('Legacy event indices do not match; cannot append safely')
        extra = rows[21:]
        lines = ['; Generated from measured C1 event table; original 21 indices preserved.']
        lines += [f"dd codol_anim_event_{row['index']}, 0xffffffff" for row in extra]
        lines.append('dd 0, 0xffffffff')
        lines += [f"codol_anim_event_{row['index']}: db \"{row['name']}\",0" for row in extra]
        lines.append('align 4')
        args.event_include.write_text('\n'.join(lines) + '\n', encoding='ascii')
    if args.movement_include:
        rows = result['tables']['movements']['entries']
        if len(rows) != 55 or any(row['iw3_index'] != row['index'] for row in rows[:43]):
            raise ValueError('Legacy movement indices do not match; cannot append safely')
        extra = rows[43:]
        lines = ['; Generated by codol_playeranim_catalog.py from measured C1 tables.',
                 '; Source SHA256: ' + digest]
        lines += [f"dd codol_anim_move_{row['index']}, 0xffffffff" for row in extra]
        lines.append('dd 0, 0xffffffff')
        lines += [f"codol_anim_move_{row['index']}: db \"{row['name']}\",0" for row in extra]
        lines.append('align 4')
        args.movement_include.write_text('\n'.join(lines) + '\n', encoding='ascii')
    print({kind: table['count'] for kind, table in result['tables'].items()})

if __name__ == '__main__':
    main()
