"""Native brush conversion with fingerprinted, explicitly resolved plane fixtures.

Plane offsets are test evidence, never a runtime lookup or heuristic.
"""
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from test_codol_map_entities import Asset, Layout, Terrain, Entities
import pathlib as _codol_pl
_codol_src=_codol_pl.Path(__file__).resolve().parents[1]/'src'
CODOL_INCLUDE=['-I'+str(_codol_src)]+['-I'+str(d) for d in sorted((_codol_src/'codol').iterdir()) if d.is_dir()]

class Plane(C.Structure):
    _fields_ = [('normal', C.c_float*3), ('dist', C.c_float), ('type', C.c_uint8),
                ('signbits', C.c_uint8), ('pad', C.c_uint8*2)]
class Side(C.Structure):
    _pack_ = 2
    _fields_ = [('plane', C.POINTER(Plane)), ('material', C.c_uint),
                ('offset', C.c_int16), ('edges', C.c_uint8), ('pad', C.c_uint8)]
class Brush(C.Structure):
    _fields_ = [('mins', C.c_float*3), ('contents', C.c_int), ('maxs', C.c_float*3),
                ('count', C.c_uint), ('sides', C.POINTER(Side)), ('materials', C.c_int16*6),
                ('edges', C.c_void_p), ('offsets', C.c_int16*6), ('counts', C.c_uint8*6),
                ('pad', C.c_uint8*(14 if C.sizeof(C.c_void_p)==8 else 10))]
class Node(C.Structure):
    _fields_ = [('plane',C.POINTER(Plane)),('children',C.c_int16*2)]
class Brushes(C.Structure):
    _fields_ = [(n,C.c_uint32) for n in ('plane_count','side_count','edge_count','brush_count')]+[
        ('planes', C.POINTER(Plane)), ('sides', C.POINTER(Side)), ('edges', C.c_void_p),
        ('brushes', C.POINTER(Brush)), ('storage', C.c_void_p),
        ('node_count',C.c_uint32),('nodes',C.POINTER(Node))]
class WorldPlanes(C.Structure):
    _fields_ = [('offset',C.c_size_t),('count',C.c_uint32),('reference',C.c_uint32),('name',C.c_char_p)]
class Material(C.Structure):
    _fields_ = [('name',C.c_char*64),('surface',C.c_int),('contents',C.c_int)]
class Materials(C.Structure):
    _fields_ = [('count',C.c_uint32),('unresolved',C.c_uint32),('entries',C.POINTER(Material)),
                ('references',C.POINTER(C.c_uint32))]
class Leaf(C.Structure):
    _fields_ = [('first',C.c_uint16),('count',C.c_uint16),('brush',C.c_int),('terrain',C.c_int),
                ('mins',C.c_float*3),('maxs',C.c_float*3),('node',C.c_int),('cluster',C.c_int16),('pad',C.c_int16)]
class Submodel(C.Structure):
    _fields_ = [('mins',C.c_float*3),('maxs',C.c_float*3),('radius',C.c_float),('leaf',Leaf)]
class Leaves(C.Structure):
    _fields_ = [('count',C.c_uint32),('model_count',C.c_uint32),('leaves',C.POINTER(Leaf)),('models',C.POINTER(Submodel)),
                ('surface_count',C.c_uint32),('surfaces',C.POINTER(C.c_uint32))]
class Branch(C.Structure):
    _fields_ = [('dist',C.c_float),('range',C.c_float),('offsets',C.c_uint16*2)]
class BrushNodeData(C.Union):
    _fields_ = [('brushes',C.POINTER(C.c_uint16)),('branch',Branch)]
class BrushNode(C.Structure):
    _pack_=2
    _fields_ = [('axis',C.c_uint8),('count',C.c_int16),('contents',C.c_int),('data',BrushNodeData)]
class BrushTree(C.Structure):
    _fields_ = [('count',C.c_uint32),('indices_count',C.c_uint32),('pooled_count',C.c_uint32),
                ('nodes',C.POINTER(BrushNode)),('indices',C.POINTER(C.c_uint16))]
class StaticModel(C.Structure):
    _pack_=4
    _fields_ = [('writable',C.c_uint16),('xmodel',C.c_void_p),('origin',C.c_float*3),
                ('axis',(C.c_float*3)*3),('mins',C.c_float*3),('maxs',C.c_float*3)]
class StaticModels(C.Structure):
    _fields_ = [('count',C.c_uint32),('unresolved',C.c_uint32),('models',C.POINTER(StaticModel)),('refs',C.POINTER(C.c_uint32))]
class CollisionMap(C.Structure):
    _fields_ = [('materials',Materials),('brushes',Brushes),('terrain',Terrain),('leaves',Leaves),
                ('tree',BrushTree),('entities',Entities),('static_count',C.c_uint32),('static_models',StaticModels),('checksum',C.c_uint32)]

def check_bounds(mins,maxs,blob,offset):
    values=struct.unpack_from('<6f',blob,offset)
    assert tuple(mins)==tuple(C.c_float(values[i]-values[i+3]).value for i in range(3))
    assert tuple(maxs)==tuple(C.c_float(values[i]+values[i+3]).value for i in range(3))

def check_leaf(leaf,blob,offset):
    assert (leaf.first,leaf.count,leaf.brush,leaf.terrain)==struct.unpack_from('<HHii',blob,offset)
    assert leaf.node==struct.unpack_from('<i',blob,offset+36)[0] and leaf.cluster==-1
    check_bounds(leaf.mins,leaf.maxs,blob,offset+12)

def asset_blob(data, index):
    count = struct.unpack_from('<I',data,40)[0]; pos=56+4*count
    for i in range(count):
        if struct.unpack_from('<I',data,56+4*i)[0]==0xffffffff: pos=data.index(0,pos)+1
    kind, offset, _, size=struct.unpack_from('<4I',data,pos+16*index)
    return kind, data[40+offset:40+offset+size]

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]; zones=Path(sys.argv[1])
    clips=json.loads((root/'tests/codol_map_entities_fixtures.json').read_text())
    plane_fixtures=json.loads((root/'tests/codol_plane_fixtures.json').read_text())
    with tempfile.TemporaryDirectory(prefix='codol-brushes-') as temporary:
        dll=Path(temporary)/('brushes.dll' if os.name=='nt' else 'brushes.so')
        subprocess.run([os.environ.get('CC', 'gcc'), *CODOL_INCLUDE,'-shared','-fPIC','-O2','-Wall','-Wextra','-Werror',
                        *[str(root/'src'/'codol'/'collision'/s) for s in ('codol_collision_static_models.c','codol_collision_map.c','codol_collision_terrain.c','codol_collision_brush_tree.c','codol_collision_leaves.c','codol_collision_materials.c','codol_world_planes.c','codol_collision_brushes.c','codol_collision_stream.c','codol_map_entities.c')],
                        '-o',str(dll)],check=True)
        lib=C.CDLL(str(dll))
        try:
            lib.CODOL_ReadCollisionLayout.argtypes=[C.POINTER(Asset),C.POINTER(Layout)]
            lib.CODOL_ReadCollisionBrushes.argtypes=[C.POINTER(Asset),C.c_void_p,C.c_size_t,C.POINTER(Brushes)]
            lib.CODOL_FreeCollisionBrushes.argtypes=[C.POINTER(Brushes)]
            lib.CODOL_ReadWorldPlanes.argtypes=[C.POINTER(Asset),C.POINTER(WorldPlanes)]
            lib.CODOL_WorldBaseName.argtypes=[C.POINTER(Asset)]
            lib.CODOL_WorldBaseName.restype=C.c_char_p
            lib.CODOL_ReadWorldBrushes.argtypes=[C.POINTER(Asset),C.POINTER(Asset),C.POINTER(Brushes)]
            lib.CODOL_ReadCollisionMaterials.argtypes=[C.POINTER(Asset),C.c_void_p,C.c_void_p,C.POINTER(Materials)]
            lib.CODOL_FreeCollisionMaterials.argtypes=[C.POINTER(Materials)]
            lib.CODOL_ReadCollisionLeaves.argtypes=[C.POINTER(Asset),C.POINTER(Leaves)]
            lib.CODOL_FreeCollisionLeaves.argtypes=[C.POINTER(Leaves)]
            lib.CODOL_ReadCollisionBrushTree.argtypes=[C.POINTER(Asset),C.POINTER(BrushTree)]
            lib.CODOL_FreeCollisionBrushTree.argtypes=[C.POINTER(BrushTree)]
            lib.CODOL_ReadCollisionMap.argtypes=[C.POINTER(Asset),C.POINTER(Asset),C.c_void_p,C.c_void_p,C.POINTER(CollisionMap)]
            lib.CODOL_FreeCollisionMap.argtypes=[C.POINTER(CollisionMap)]
            for clip,pf in zip(clips,plane_fixtures):
                assert clip['zone']==pf['zone']
                data=(zones/clip['zone']).read_bytes()
                kind,blob=asset_blob(data,clip['asset']); _,gfx=asset_blob(data,pf['asset'])
                assert hashlib.sha256(blob).hexdigest()==clip['asset_sha256']
                assert hashlib.sha256(gfx).hexdigest()==pf['asset_sha256']
                raw=gfx[pf['offset']:pf['offset']+pf['count']*20]
                assert hashlib.sha256(raw).hexdigest()==pf['planes_sha256']
                source=C.create_string_buffer(blob); planes=C.create_string_buffer(raw)
                world_source=C.create_string_buffer(gfx); world=Asset(21,C.addressof(world_source),len(gfx)); span=WorldPlanes()
                assert lib.CODOL_WorldBaseName(C.byref(world))==pf['map_name'].encode('ascii')
                assert lib.CODOL_ReadWorldPlanes(C.byref(world),C.byref(span)),clip['zone']
                assert (span.offset,span.count)==(pf['offset'],pf['count']),clip['zone']
                asset=Asset(kind,C.addressof(source),len(blob)); layout=Layout(); out=Brushes()
                assert lib.CODOL_ReadCollisionLayout(C.byref(asset),C.byref(layout))
                combined=CollisionMap()
                assert lib.CODOL_ReadCollisionMap(C.byref(asset),C.byref(world),None,None,C.byref(combined)),clip['zone']
                assert combined.checksum==struct.unpack_from('<I',blob,204)[0]
                try:
                    assert combined.brushes.brush_count==layout.sections[17].count
                    assert combined.terrain.aabbs_count==layout.sections[15].count
                    assert combined.leaves.count==layout.sections[6].count
                    assert combined.tree.count==layout.sections[8].count
                    assert combined.materials.count==layout.sections[2].count
                    assert combined.static_count==layout.sections[1].count
                    assert combined.static_models.count==combined.static_count==combined.static_models.unresolved
                    for i,model in enumerate(combined.static_models.models[:combined.static_count]):
                        at=layout.sections[1].offset+76*i
                        assert not model.xmodel and model.writable==0
                        assert combined.static_models.refs[i]==struct.unpack_from('<I',blob,at)[0]
                        assert tuple(model.origin)==struct.unpack_from('<3f',blob,at+4)
                        assert tuple(v for row in model.axis for v in row)==struct.unpack_from('<9f',blob,at+16)
                        check_bounds(model.mins,model.maxs,blob,at+52)
                    assert hashlib.sha256(C.string_at(combined.entities.text,combined.entities.size)).hexdigest()==clip['text_sha256']
                    saved=bytes(combined)
                    # Last-stage failure must unwind all previously staged geometry.
                    at=layout.map_entities+8
                    damaged=C.create_string_buffer(blob[:at]+bytes(4)+blob[at+4:])
                    invalid=Asset(kind,C.addressof(damaged),len(blob))
                    for _ in range(2):
                        assert not lib.CODOL_ReadCollisionMap(C.byref(invalid),C.byref(world),None,None,C.byref(combined))
                        assert bytes(combined)==saved
                    assert lib.CODOL_ReadCollisionMap(C.byref(asset),C.byref(world),None,None,C.byref(combined))
                    assert hashlib.sha256(C.string_at(combined.entities.text,combined.entities.size)).hexdigest()==clip['text_sha256']
                finally: lib.CODOL_FreeCollisionMap(C.byref(combined))
                assert not any(bytes(combined))
                tree=BrushTree()
                assert lib.CODOL_ReadCollisionBrushTree(C.byref(asset),C.byref(tree)),clip['zone']
                try:
                    section=layout.sections[8]; pos=section.offset+section.count*20; used=0; extra=tree.pooled_count
                    assert tree.count==section.count and tree.pooled_count==layout.sections[7].count
                    assert C.string_at(tree.indices,tree.pooled_count*2)==blob[layout.sections[7].offset:layout.sections[7].offset+tree.pooled_count*2]
                    for i,node in enumerate(tree.nodes[:tree.count]):
                        at=section.offset+20*i
                        assert (node.axis,node.count,node.contents)==struct.unpack_from('<B x h i',blob,at)
                        if node.count>0:
                            ref=struct.unpack_from('<I',blob,at+8)[0]
                            if ref==0xffffffff:
                                assert C.string_at(node.data.brushes,node.count*2)==blob[pos:pos+node.count*2]
                                assert C.addressof(node.data.brushes.contents)==C.addressof(tree.indices.contents)+2*extra
                                extra+=node.count;pos+=node.count*2
                            else:
                                assert C.addressof(node.data.brushes.contents)==C.addressof(tree.indices.contents)+2*used
                                used+=node.count
                        else:
                            branch=node.data.branch
                            assert (branch.dist,branch.range,*branch.offsets)==struct.unpack_from('<ffHH',blob,at+8)
                    assert used==tree.pooled_count and extra==tree.indices_count
                finally: lib.CODOL_FreeCollisionBrushTree(C.byref(tree))
                leaves=Leaves()
                assert lib.CODOL_ReadCollisionLeaves(C.byref(asset),C.byref(leaves)),clip['zone']
                try:
                    assert leaves.count==layout.sections[6].count and leaves.model_count==layout.sections[16].count
                    section=layout.sections[9]
                    assert leaves.surface_count==section.count
                    assert list(leaves.surfaces[:leaves.surface_count])==list(struct.unpack_from('<'+str(section.count)+'I',blob,section.offset))
                    for i,entry in enumerate(leaves.leaves[:leaves.count]):
                        check_leaf(entry,blob,layout.sections[6].offset+40*i)
                    for i,entry in enumerate(leaves.models[:leaves.model_count]):
                        at=layout.sections[16].offset+68*i
                        check_bounds(entry.mins,entry.maxs,blob,at)
                        assert entry.radius==struct.unpack_from('<f',blob,at+24)[0]
                        check_leaf(entry.leaf,blob,at+28)
                    saved=bytes(leaves)
                    for at,value in ((layout.sections[6].offset+36,0xffffffff),
                                     (layout.sections[16].offset+24,0x7fc00000)):
                        damaged=C.create_string_buffer(blob[:at]+struct.pack('<I',value)+blob[at+4:])
                        invalid=Asset(kind,C.addressof(damaged),len(blob))
                        assert not lib.CODOL_ReadCollisionLeaves(C.byref(invalid),C.byref(leaves))
                        assert bytes(leaves)==saved
                finally: lib.CODOL_FreeCollisionLeaves(C.byref(leaves))
                materials=Materials()
                assert lib.CODOL_ReadCollisionMaterials(C.byref(asset),None,None,C.byref(materials)),clip['zone']
                try:
                    section=layout.sections[2]; pos=section.offset+12*section.count; unresolved=0
                    assert materials.count==section.count
                    for i,entry in enumerate(materials.entries[:materials.count]):
                        ref,surface,contents=struct.unpack_from('<Iii',blob,section.offset+12*i)
                        assert (entry.surface,entry.contents)==(surface,contents)
                        if ref==0xffffffff:
                            end=blob.index(0,pos)
                            assert entry.name==blob[pos:end] and materials.references[i]==0
                            pos=end+1
                        else:
                            unresolved+=1
                            assert materials.references[i]==ref and entry.name==b''
                    assert materials.unresolved==unresolved
                finally: lib.CODOL_FreeCollisionMaterials(C.byref(materials))
                assert lib.CODOL_ReadWorldBrushes(C.byref(asset),C.byref(world),C.byref(out)),clip['zone']
                try:
                    assert C.addressof(out.brushes.contents)%16==0
                    for i,plane in enumerate(out.planes[:out.plane_count]):
                        values=struct.unpack_from('<4f',raw,20*i)
                        assert tuple(plane.normal)+(plane.dist,)==values
                        assert plane.signbits==sum((1<<j) for j in range(3) if values[j]<0)
                    s=layout.sections
                    assert out.node_count==s[5].count
                    for i,node in enumerate(out.nodes[:out.node_count]):
                        ref,a,b=struct.unpack_from('<Ihh',blob,s[5].offset+8*i)
                        assert tuple(node.children)==(a,b)
                        assert C.addressof(node.plane.contents)==C.addressof(out.planes.contents)+ref-s[0].reference
                    assert C.string_at(out.edges,out.edge_count)==blob[s[4].offset:s[4].offset+out.edge_count]
                    for i,side in enumerate(out.sides[:out.side_count]):
                        ref,mat,offset,edges=struct.unpack_from('<IHBB',blob,s[3].offset+8*i)
                        assert C.addressof(side.plane.contents)==C.addressof(out.planes.contents)+ref-s[0].reference
                        assert (side.material,side.offset,side.edges)==(mat,offset,edges)
                    side_index=edge_index=0
                    for i,brush in enumerate(out.brushes[:out.brush_count]):
                        record=blob[s[17].offset+36*i:s[17].offset+36*(i+1)]
                        assert brush.count==struct.unpack_from('<H',record)[0]
                        assert tuple(brush.materials)==struct.unpack_from('<6h',record,12)
                        assert tuple(brush.offsets)==tuple(record[24:30])
                        assert tuple(brush.counts)==tuple(record[30:36])
                        bounds=struct.unpack_from('<6f',blob,s[18].offset+24*i)
                        for j in range(3):
                            assert brush.mins[j]==C.c_float(bounds[j]-bounds[3+j]).value
                            assert brush.maxs[j]==C.c_float(bounds[j]+bounds[3+j]).value
                        assert brush.contents==struct.unpack_from('<i',blob,s[19].offset+4*i)[0]
                        if brush.count: assert C.addressof(brush.sides.contents)==C.addressof(out.sides.contents)+side_index*C.sizeof(Side)
                        edges=sum(brush.counts)+sum(out.sides[side_index+j].edges for j in range(brush.count))
                        if edges: assert brush.edges==out.edges+edge_index
                        side_index+=brush.count; edge_index+=edges
                    saved=bytes(out)
                    for at,value in ((0,0x12345678),(8,pf['count']+1)):
                        damaged=C.create_string_buffer(gfx[:at]+struct.pack('<I',value)+gfx[at+4:])
                        invalid=Asset(21,C.addressof(damaged),len(gfx))
                        assert not lib.CODOL_ReadWorldBrushes(C.byref(asset),C.byref(invalid),C.byref(out))
                        assert bytes(out)==saved
                    assert not lib.CODOL_ReadCollisionBrushes(C.byref(asset),planes,len(raw)-1,C.byref(out))
                    for at,value in ((s[3].offset,0xffffffff),(s[18].offset+12,0xbf800000)):
                        damaged=C.create_string_buffer(blob[:at]+struct.pack('<I',value)+blob[at+4:])
                        invalid=Asset(kind,C.addressof(damaged),len(blob))
                        assert not lib.CODOL_ReadCollisionBrushes(C.byref(invalid),planes,len(raw),C.byref(out))
                        assert bytes(out)==saved
                finally: lib.CODOL_FreeCollisionBrushes(C.byref(out))
            print('PASS: 19 world-plane, brush, leaf, material and brush-tree conversions with pointer relocation and malformed-input rejection')
        finally:
            if os.name == "nt":
                import _ctypes
                _ctypes.FreeLibrary(lib._handle)
