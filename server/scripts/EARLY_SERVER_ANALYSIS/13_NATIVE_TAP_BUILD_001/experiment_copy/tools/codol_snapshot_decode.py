"""Strict baseline/delta snapshot check using alpha0022's independent readers.

Offline only. The supplied payload starts at snapshot opcode 0, including its
seven-byte header and EOF. Imports only the explicitly supplied trusted reference.
"""
import argparse
import collections
import json
from pathlib import Path
import struct
import sys


def decode_snapshot(payload, sequence=0, base=None):
    import delta_snapshot as ds

    class StrictReader(ds.pf.MsgReader):
        def _b(self, index):
            if not 0 <= index < len(self.data):
                raise ValueError(f'Truncated snapshot at byte {index}')
            return self.data[index]

    if len(payload) < 8 or payload[0] != 0:
        raise ValueError('Expected a complete snapshot header')
    delta = payload[5]
    if delta:
        if not base or not 1 <= delta <= 31 or sequence - delta != base['sequence'] or payload[6] & 8:
            raise ValueError('Delta does not identify the supplied valid base')
    else:
        base = None
    server_time = struct.unpack_from('<I', payload, 1)[0]
    reader = StrictReader(payload[7:])
    if bool(reader.read_bit()) != bool(delta):
        raise ValueError('Playerstate delta flag disagrees with snapshot header')
    rov, player, hint2, gates = ds.decode_playerstate_delta(reader,
        base['ps'] if base else {}, server_time,
        hint2_from=base['hint2'] if base else None,
        hud_from=base['hud'] if base else None)
    if gates['s5d0'] or gates['s3340']:
        raise ValueError('Reference reader does not handle nonempty reserved player arrays')
    if reader.read_bit() or reader.read_bits(4):
        raise ValueError('Reference baseline check requires empty animation commands')
    actors = ds.ac.decode_actors(reader, base['actors'] if base else {}, server_time)
    old_entities = base['entities'] if base else {}
    merged = {n: {'number': n, 'eType': row['eType'], 'fields': dict(row['fields'])}
              for n, row in old_entities.items()}
    last = -1
    while True:
        number = ds.ec._read_index(reader, last)
        if number == ds.ec.ENTITY_SENTINEL:
            break
        if not last < number < 2047:
            raise ValueError('Invalid or unordered entity index')
        last = number
        old = old_entities.get(number)
        by_index = None
        if old:
            table = ds.ss.entity_table(old['eType'])
            by_index = {i: old['fields'][offset] for i, (offset, bits, _) in enumerate(table)
                        if offset in old['fields'] and bits not in ds.NO_DELTA_POS_BITS}
        row = ds.ec.decode_entity_payload(reader, server_time, frm_by_index=by_index)
        if row.get('removed') or row.get('unchanged'):
            if not old:
                raise ValueError('Entity references a missing prior record')
            if row.get('removed'):
                merged.pop(number)
            continue
        target = merged.setdefault(number, {'number': number, 'fields': {}})
        if old and old['eType'] != row['eType']:
            target['fields'] = {}
        target['eType'] = row['eType']
        target['fields'].update(row['fields'])
    entities = [merged[n] for n in sorted(merged)]
    clients = ds.ss.decode_clients(reader, server_time)
    if base and clients:
        raise ValueError('Changed client records require a from-aware client decoder')
    if base:
        clients = base['clients']
    numbers = [row['number'] for row in entities]
    if numbers != sorted(set(numbers)) or any(not 0 <= n < 2047 for n in numbers):
        raise ValueError('Invalid or unordered entity indices')
    client_numbers = [row['clientNum'] for row in clients]
    if client_numbers != sorted(set(client_numbers)) or any(not 0 <= n < 32 for n in client_numbers):
        raise ValueError('Invalid or unordered client indices')
    if any(row.get('removed') or row.get('unchanged') for row in entities + clients):
        raise ValueError('Baseline references absent prior records')
    if reader.read_bit():
        raise ValueError('Nonempty sixth snapshot section')
    opcode = reader.read_byte()
    matchdata = None
    if opcode == 4:
        name = bytearray()
        for _ in range(64):
            value = reader.read_byte()
            if not value:
                break
            name.append(value)
        else:
            raise ValueError('Unterminated match-data schema name')
        if not name:
            raise ValueError('Empty match-data schema name')
        record = bytes(reader.read_byte() for _ in range(1024))
        matchdata = {'name': name.decode('ascii'), 'record': record}
        opcode = reader.read_byte()
    if opcode != 5 or reader.readcount != len(reader.data):
        raise ValueError('Snapshot did not end exactly at EOF')
    brush = [{'number': row['number'], 'model': row['fields'].get(0x98, 0)}
             for row in entities if row.get('fields', {}).get(0xa8) == 0xffffff]
    report = {
        'bytes': len(payload), 'server_time': server_time, 'flags': payload[6],
        'delta': delta, 'base_sequence': base['sequence'] if base else None,
        'rov': rov, 'player_fields': len(player), 'hint2_fields': len(hint2),
        'entities': len(entities), 'entity_types': dict(collections.Counter(row['eType'] for row in entities)),
        'clients': client_numbers, 'actors': len(actors), 'brush_models': brush,
        'exact_eof': True,
    }
    state = {'sequence': sequence, 'ps': player, 'hint2': hint2, 'hud': gates['hud'],
             'actors': actors, 'entities': merged, 'clients': clients}
    state['matchdata'] = matchdata
    if matchdata is not None:
        report['matchdata'] = {'name': matchdata['name'], 'bytes': len(record),
                               'version': int.from_bytes(record[:4], 'little'),
                               'checksum': record[4:8].hex()}
    return report, state


def decode_baseline(payload):
    return decode_snapshot(payload)[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.reference.resolve()))
    print(json.dumps(decode_baseline(args.snapshot.read_bytes())))


if __name__ == '__main__':
    main()
