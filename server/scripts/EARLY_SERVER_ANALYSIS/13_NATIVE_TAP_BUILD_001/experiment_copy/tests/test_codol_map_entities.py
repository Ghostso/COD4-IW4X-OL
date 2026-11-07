"""Native MapEnts reader against fixed, fingerprinted shipped collision records.

Offsets are test fixtures, not a runtime collision locator. No game is started.
"""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import pathlib as _codol_pl
_codol_src=_codol_pl.Path(__file__).resolve().parents[1]/'src'
CODOL_INCLUDE=['-I'+str(_codol_src)]+['-I'+str(d) for d in sorted((_codol_src/'codol').iterdir()) if d.is_dir()]

class Asset(C.Structure):
    _fields_ = [('type', C.c_uint32), ('data', C.c_void_p), ('size', C.c_size_t)]

class Span(C.Structure):
    _fields_ = [('offset', C.c_size_t), ('count', C.c_uint32), ('stride', C.c_uint32), ('reference', C.c_uint32)]

class Layout(C.Structure):
    _fields_ = [('sections', Span*21), ('map_entities', C.c_size_t), ('name_reference', C.c_uint32)]

class Border(C.Structure):
    _fields_ = [('values', C.c_float*7)]

class Partition(C.Structure):
    _pack_ = 4
    _fields_ = [('triCount', C.c_uint8), ('borderCount', C.c_uint8),
                ('firstTri', C.c_int), ('borders', C.POINTER(Border))]

class Aabb(C.Structure):
    _fields_ = [('origin', C.c_float*3), ('halfSize', C.c_float*3),
                ('material', C.c_uint16), ('children', C.c_uint16), ('index', C.c_int)]

class Terrain(C.Structure):
    _fields_ = [(n, C.c_uint32) for n in ('vertices_count', 'triangles_count', 'walkable_count',
                                       'borders_count', 'partitions_count', 'aabbs_count')] + [
        ('vertices', C.POINTER(C.c_float*3)), ('triangles', C.POINTER(C.c_uint16*3)),
        ('walkable', C.POINTER(C.c_uint32)), ('borders', C.POINTER(Border)),
        ('partitions', C.POINTER(Partition)), ('aabbs', C.POINTER(Aabb))]

class Stage(C.Structure):
    _fields_ = [('reference', C.c_uint32), ('name', C.c_char_p), ('origin', C.c_float*3),
                ('trigger', C.c_uint16), ('sun', C.c_uint8)]

class Entities(C.Structure):
    _fields_ = [('storage', C.c_void_p), ('name', C.c_char_p), ('text', C.c_void_p),
                ('reference', C.c_uint32), ('size', C.c_size_t), ('consumed', C.c_size_t),
                ('models_count', C.c_uint32), ('hulls_count', C.c_uint32),
                ('slabs_count', C.c_uint32), ('stages_count', C.c_uint32),
                ('models', C.c_void_p), ('hulls', C.c_void_p), ('slabs', C.c_void_p),
                ('stages', C.POINTER(Stage))]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('zones', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    fixtures = json.loads((root/'tests/codol_map_entities_fixtures.json').read_text())
    with tempfile.TemporaryDirectory(prefix='codol-mapents-') as temporary:
        target = Path(temporary)/('mapents.dll' if os.name == 'nt' else 'mapents.so')
        subprocess.run([os.environ.get('CC', 'gcc'), *CODOL_INCLUDE, '-shared', '-fPIC', '-O2', '-Wall', '-Wextra',
                        '-Werror', str(root/'src/codol/collision/codol_map_entities.c'), str(root/'src/codol/collision/codol_collision_stream.c'),
                        str(root/'src/codol/collision/codol_collision_terrain.c'), '-o', str(target)], check=True)
        lib = C.CDLL(str(target))
        lib.CODOL_ReadMapEntities.argtypes = [C.c_void_p, C.c_size_t, C.POINTER(Entities)]
        lib.CODOL_FreeMapEntities.argtypes = [C.POINTER(Entities)]
        lib.CODOL_LocateCollisionMapEntities.argtypes = [C.POINTER(Asset), C.POINTER(C.c_size_t)]
        lib.CODOL_ReadCollisionMapEntities.argtypes = [C.POINTER(Asset), C.POINTER(Entities)]
        lib.CODOL_ReadCollisionLayout.argtypes = [C.POINTER(Asset), C.POINTER(Layout)]
        lib.CODOL_ReadCollisionTerrain.argtypes = [C.POINTER(Asset), C.POINTER(Terrain)]
        lib.CODOL_FreeCollisionTerrain.argtypes = [C.POINTER(Terrain)]
        try:
            for fixture in fixtures:
                data = (args.zones/fixture['zone']).read_bytes()
                strings = struct.unpack_from('<I', data, 40)[0]; pos = 56+4*strings
                for index in range(strings):
                    if struct.unpack_from('<I', data, 56+4*index)[0] == 0xffffffff:
                        pos = data.index(0, pos)+1
                kind, offset, _, size = struct.unpack_from('<IIII', data, pos+16*fixture['asset'])
                blob = data[offset+40:offset+40+size]
                assert kind in (14, 15) and hashlib.sha256(blob).hexdigest() == fixture['asset_sha256'], fixture['zone']
                collision = C.create_string_buffer(blob); asset = Asset(kind, C.addressof(collision), len(blob)); located = C.c_size_t()
                assert lib.CODOL_LocateCollisionMapEntities(C.byref(asset), C.byref(located)), fixture['zone']
                assert located.value == fixture['offset'], fixture['zone']
                layout = Layout()
                assert lib.CODOL_ReadCollisionLayout(C.byref(asset), C.byref(layout)), fixture['zone']
                assert layout.map_entities == located.value
                for span in layout.sections[1:]:
                    assert span.offset + span.count*span.stride <= layout.map_entities
                vertices, triangles = layout.sections[10], layout.sections[11]
                indices = [x[0] for x in struct.iter_unpack('<H', blob[triangles.offset:triangles.offset+triangles.count*6])]
                if indices:
                    assert max(indices) < vertices.count, fixture['zone']
                partitions = layout.sections[14]
                assert sum(blob[partitions.offset+i*12] for i in range(partitions.count)) == triangles.count, fixture['zone']
                assert sum(blob[partitions.offset+i*12+1] for i in range(partitions.count)) == layout.sections[13].count, fixture['zone']
                terrain = Terrain()
                assert lib.CODOL_ReadCollisionTerrain(C.byref(asset), C.byref(terrain)), fixture['zone']
                try:
                    for section, pointer, count in ((10, terrain.vertices, terrain.vertices_count),
                            (11, terrain.triangles, terrain.triangles_count),
                            (12, terrain.walkable, terrain.walkable_count),
                            (13, terrain.borders, terrain.borders_count)):
                        span = layout.sections[section]
                        assert count == span.count
                        assert C.string_at(pointer, count*span.stride) == blob[span.offset:span.offset+count*span.stride]
                    border_index = 0
                    for i, part in enumerate(terrain.partitions[:terrain.partitions_count]):
                        tri, borders, first = struct.unpack_from('<BB2xi', blob, partitions.offset+i*12)
                        assert (part.triCount, part.borderCount, part.firstTri) == (tri, borders, first)
                        if borders:
                            assert C.addressof(part.borders.contents) == C.addressof(terrain.borders.contents)+border_index*28
                        else:
                            assert not part.borders
                        border_index += borders
                    for i, aabb in enumerate(terrain.aabbs[:terrain.aabbs_count]):
                        values = struct.unpack_from('<3fHH3fi', blob, layout.sections[15].offset+i*32)
                        assert tuple(aabb.origin) == values[:3] and tuple(aabb.halfSize) == values[5:8]
                        assert (aabb.material, aabb.children, aabb.index) == values[3:5]+values[8:]
                    # Invalid geometry must leave an existing owned result untouched.
                    original = bytes(terrain)
                    mutations = [(vertices.offset, struct.pack('<I', 0x7fc00000)),
                                 (partitions.offset+4, struct.pack('<I', triangles.count+1)),
                                 (layout.sections[15].offset+28, struct.pack('<I', 0xffffffff))]
                    nonempty = [i for i in range(partitions.count) if blob[partitions.offset+i*12+1]]
                    if len(nonempty)>1:
                        at = partitions.offset+nonempty[1]*12+8
                        mutations.append((at, struct.pack('<I', struct.unpack_from('<I', blob, at)[0]+4)))
                    for at, replacement in mutations:
                        damaged = C.create_string_buffer(blob[:at]+replacement+blob[at+len(replacement):])
                        invalid = Asset(kind, C.addressof(damaged), len(blob))
                        assert not lib.CODOL_ReadCollisionTerrain(C.byref(invalid), C.byref(terrain))
                        assert bytes(terrain) == original
                finally:
                    lib.CODOL_FreeCollisionTerrain(C.byref(terrain))
                assert not any(bytes(terrain))
                nested = blob[located.value:]; buffer = C.create_string_buffer(nested); out = Entities()
                assert lib.CODOL_ReadCollisionMapEntities(C.byref(asset), C.byref(out)), fixture['zone']
                try:
                    assert out.consumed == fixture['consumed'] and out.size == fixture['text_size']
                    assert hashlib.sha256(C.string_at(out.text, out.size)).hexdigest() == fixture['text_sha256']
                    assert [out.models_count, out.hulls_count, out.slabs_count] == fixture['counts']
                    array_offset = 44
                    if struct.unpack_from('<I', nested)[0] == 0xffffffff:
                        array_offset = nested.index(0, array_offset)+1
                    array_offset += out.size
                    for pointer, count, stride in ((out.models, out.models_count, 8),
                                                   (out.hulls, out.hulls_count, 32),
                                                   (out.slabs, out.slabs_count, 20)):
                        length = count*stride
                        assert C.string_at(pointer, length) == nested[array_offset:array_offset+length]
                        array_offset += length
                    assert out.stages_count == len(fixture['stages'])
                    for actual, expected in zip(out.stages[:out.stages_count], fixture['stages']):
                        assert actual.reference == expected['reference']
                        assert (actual.name.decode('ascii') if actual.name is not None else None) == expected['name']
                        assert list(actual.origin) == expected['origin']
                        assert actual.trigger == expected['trigger'] and actual.sun == expected['sun']
                finally:
                    lib.CODOL_FreeMapEntities(C.byref(out))
            print(f'PASS: {len(fixtures)} shipped MapEnts and owned terrain records, array comparisons and corrupt-geometry rejection')
        finally:
            if os.name == 'nt':
                import _ctypes
                _ctypes.FreeLibrary(lib._handle)
