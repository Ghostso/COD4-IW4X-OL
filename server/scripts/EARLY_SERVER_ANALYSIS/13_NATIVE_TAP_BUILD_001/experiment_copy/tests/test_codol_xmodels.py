"""Native skeletal-prefix reader checked against local XModel assets."""
import ctypes as C
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from test_codol_map_entities import Asset, Entities
import pathlib as _codol_pl
_codol_src=_codol_pl.Path(__file__).resolve().parents[1]/'src'
CODOL_INCLUDE=['-I'+str(_codol_src)]+['-I'+str(d) for d in sorted((_codol_src/'codol').iterdir()) if d.is_dir()]
class Array(C.Structure):
    _fields_=[('ref',C.c_uint32),('count',C.c_uint32),('stride',C.c_uint32),('data',C.c_void_p)]
class Skeleton(C.Structure):
    _fields_=[('storage',C.c_void_p),('name',C.c_char_p),('ref',C.c_uint32),
              ('bones',C.c_uint),('roots',C.c_uint),('surfaces',C.c_uint),('unresolved',C.c_uint),
              ('consumed',C.c_size_t),('arrays',Array*6)]
class OwnedSurface(C.Structure):
    _fields_=[('header',C.c_uint8*84),('arrays',Array*3),('rigid_ref',C.c_uint32),
              ('rigid_count',C.c_uint32),('rigid',C.c_void_p),('rigid_size',C.c_size_t),
              ('relocated_tree_arrays',C.c_uint)]
class OwnedSurfaces(C.Structure):
    _fields_=[('storage',C.c_void_p),('name',C.c_char_p),('name_ref',C.c_uint32),
              ('surfaces_ref',C.c_uint32),('count',C.c_uint),('unresolved',C.c_uint),
              ('surfaces',C.POINTER(OwnedSurface)),('consumed',C.c_size_t)]
class SurfaceArrays(C.Structure):
    _fields_=[('storage',C.c_void_p),('arrays',Array*3)]
class Surface(C.Structure):
    _fields_=[('mins',C.c_float*3),('maxs',C.c_float*3),('bone',C.c_int),('contents',C.c_int),
              ('flags',C.c_int),('tri_count',C.c_uint32),('triangles',C.c_void_p)]
class Collision(C.Structure):
    _fields_=[('count',C.c_uint32),('surfaces',C.POINTER(Surface)),('consumed',C.c_size_t)]
class ScriptString(C.Structure):
    _fields_=[('reference',C.c_uint32),('text',C.c_char_p)]
class LoadStack(C.Structure):
    _fields_=[('block',C.c_uint),('entered',C.c_size_t)]
class Zone(C.Structure):
    _fields_=[('data',C.c_void_p),('size',C.c_size_t),('table_offset',C.c_size_t),
              ('asset_count',C.c_uint32),('string_count',C.c_uint32),('block_size',C.c_uint32*8)]
class LoadBlocks(C.Structure):
    _fields_=[('data',C.c_void_p*8),('capacity',C.c_size_t*8),('position',C.c_size_t*8),
              ('written',C.c_size_t*8),('source',C.c_void_p),('source_size',C.c_size_t),
              ('source_position',C.c_size_t),('active',C.c_uint),('depth',C.c_uint),('stack',LoadStack*64),
              ('asset_aliases',C.c_void_p),('asset_alias_count',C.c_size_t),
              ('asset_alias_capacity',C.c_size_t),('collect_asset_aliases',C.c_int),
              ('directory_reference',C.c_uint32),('dynamic_records',C.c_void_p),
              ('dynamic_record_count',C.c_size_t),('dynamic_record_capacity',C.c_size_t)]
class BoneName(C.Structure):
    _fields_=[('index',C.c_uint16),('reference',C.c_uint32),('text',C.c_char_p)]
class BoneNames(C.Structure):
    _fields_=[('count',C.c_uint),('unresolved',C.c_uint),('names',C.POINTER(BoneName)),('storage',C.c_void_p)]
class BlockView(C.Structure):
    _fields_=[('data',C.c_void_p),('size',C.c_size_t)]
class BoneInfo(C.Structure):
    _fields_=[('bounds',(C.c_float*3)*2),('offset',C.c_float*3),('radiusSquared',C.c_float)]
class Bounds(C.Structure):
    _fields_=[('mins',C.c_float*3),('maxs',C.c_float*3),('radius',C.c_float),
              ('count',C.c_uint32),('ref',C.c_uint32),('bones',C.POINTER(BoneInfo)),
              ('preset',C.c_uint32),('physics',C.c_uint32),('consumed',C.c_size_t),('contents',C.c_uint32),('flags',C.c_uint32)]
class Lod(C.Structure):
    _fields_=[('distance',C.c_float),('count',C.c_uint16),('index',C.c_uint16),
              ('surfaces',C.c_uint32),('name',C.c_uint32),('remaining',C.c_uint8*40)]
class Lods(C.Structure):
    _fields_=[('first',C.c_uint),('count',C.c_uint),('collision_lod',C.c_int),('lods',Lod*4)]
class MaterialSlot(C.Structure):
    _fields_=[('reference',C.c_uint32),('inline_asset',Asset)]
class ModelMaterials(C.Structure):
    _fields_=[('count',C.c_uint),('reference',C.c_uint32),('materials',C.POINTER(MaterialSlot)),('consumed',C.c_size_t)]

def preset_end(b,p):
    h=p;p+=68
    for field in (0,28):
        if struct.unpack_from('<I',b,h+field)[0]==0xffffffff:p=b.index(0,p)+1
    return p

def physics_end(b,p):
    u=lambda at:struct.unpack_from('<I',b,at)[0]
    h=p;p+=72
    if u(h)==0xffffffff:p=b.index(0,p)+1
    if u(h+8):
        geoms=p;p+=u(h+4)*68
        for i in range(u(h+4)):
            if not u(geoms+68*i):continue
            brush=p;p+=68;n=struct.unpack_from('<H',b,brush+24)[0]
            if u(brush+28):
                sides=p;p+=n*8
                for j in range(n):
                    if u(sides+8*j)==0xffffffff:p+=20
            if u(brush+32):p+=u(brush+60)
            if u(brush+64)==0xffffffff:p+=n*20
    return p
def technique_end(b,p):
    u=lambda at:struct.unpack_from('<I',b,at)[0]
    w=lambda at:struct.unpack_from('<H',b,at)[0]
    h=p;p+=204
    if u(h)==0xffffffff:p=b.index(0,p)+1
    for i in range(48):
        if u(h+12+4*i)!=0xffffffff:continue
        technique=p;p+=8;passes=p;p+=w(technique+6)*20
        for j in range(w(technique+6)):
            at=passes+20*j
            if u(at)>=0xfffffffe:
                decl=p;p+=100
                if u(decl)==0xffffffff:p=b.index(0,p)+1
            for field in (4,8):
                if u(at+field)>=0xfffffffe:
                    shader=p;p+=16
                    if u(shader)==0xffffffff:p=b.index(0,p)+1
                    if u(shader+8):p+=w(shader+12)*4
            if u(at+16):
                count=sum(b[at+12:at+15]);args=p;p+=count*8
                for k in range(count):
                    if w(args+8*k) in (1,7) and u(args+8*k+4)==0xffffffff:p+=16
        if u(technique)==0xffffffff:p=b.index(0,p)+1
    return p
def material_end(b,p):
    h=p;p+=96
    u=lambda at:struct.unpack_from('<I',b,at)[0]
    if u(h)==0xffffffff:p=b.index(0,p)+1
    if u(h+0x50)>=0xfffffffe:p=technique_end(b,p)
    if u(h+0x54)==0xffffffff:
        textures=p;p+=b[h+0x48]*12
        for i in range(b[h+0x48]):
            at=textures+12*i;ref=u(at+8)
            if b[at+7]==11:
                if ref==0xffffffff:
                    water=p;p+=68;cells=u(water+12)*u(water+16)
                    if u(water+4):p+=cells*8
                    if u(water+8):p+=cells*4
                    if u(water+64)>=0xfffffffe:
                        image=p;p+=36
                        if u(image+32)==0xffffffff:p=b.index(0,p)+1
                        if u(image)==0xffffffff:p+=16+u(p+12)
            elif ref>=0xfffffffe:
                image=p;p+=36
                if u(image+32)==0xffffffff:p=b.index(0,p)+1
                if u(image)==0xffffffff:p+=16+u(p+12)
    if u(h+0x58)==0xffffffff:p+=b[h+0x49]*32
    if u(h+0x5c)==0xffffffff:p+=b[h+0x4a]*8
    return p
def lod_end(b,p):
    h=p;p+=48
    u=lambda at:struct.unpack_from('<I',b,at)[0]
    w=lambda at:struct.unpack_from('<H',b,at)[0]
    if u(h)==0xffffffff:p=b.index(0,p)+1
    if u(h+4):
        surfaces=p;p+=w(h+8)*84
        for i in range(w(h+8)):
            s=surfaces+i*84
            if u(s+28)==0xffffffff:p+=2*sum(w(s+20+2*j)*(2*j+1) for j in range(4))
            if u(s+32)==0xffffffff:p+=w(s+4)*32
            if u(s+44)==0xffffffff:
                rigid=p;p+=u(s+40)*12
                for j in range(u(s+40)):
                    if u(rigid+j*12+8)==0xffffffff:
                        tree=p;p+=40
                        if u(tree+28):p+=u(tree+24)*16
                        if u(tree+36):p+=u(tree+32)*2
            if u(s+16)==0xffffffff:p+=w(s+6)*6
    return p
def world_visibility_extent(b):
    u=lambda p:struct.unpack_from('<I',b,p)[0]
    w=lambda p:struct.unpack_from('<H',b,p)[0]
    p=628
    for offset in (0,4):
        if u(offset)==0xffffffff:p=b.index(0,p)+1
    if u(24):
        skies=p;p+=u(20)*16
        for i in range(u(20)):
            s=skies+i*16
            if u(s+4):p+=u(s)*4
            if u(s+8)>=0xfffffffe:
                h=p;p+=36
                if u(h+32)==0xffffffff:p=b.index(0,p)+1
                if u(h)==0xffffffff:p+=16+u(p+12)
    if u(56)==0xffffffff:p+=u(8)*20
    if u(60):p+=u(12)*2
    counts=p
    if u(68):p+=u(52)*4
    if u(72):
        trees=p;p+=u(52)*4
        for i in range(u(52)):
            if u(trees+4*i):
                assert u(68)
                n=u(counts+4*i);nodes=p;p+=n*44
                for j in range(n):
                    node=nodes+j*44
                    if u(node+36)==0xffffffff:p+=w(node+34)*2
    if u(76):
        cells=p;p+=u(52)*40
        for i in range(u(52)):
            c=cells+i*40
            if u(c+28):
                portals=p;p+=u(c+24)*60
                for j in range(u(c+24)):
                    portal=portals+j*60
                    if u(portal+28):p+=b[portal+34]*12
            if u(c+36):p+=b[c+32]
    assert p<=len(b)
    return p

def world_draw_extent(b):
    u=lambda p:struct.unpack_from('<I',b,p)[0]
    p=world_visibility_extent(b)
    def image_at(p):
        h=p;p+=36
        if u(h+32)==0xffffffff:p=b.index(0,p)+1
        if u(h)==0xffffffff:p+=16+u(p+12)
        return p
    d=80
    if u(d+4):
        refs=p;p+=u(d)*4
        for i in range(u(d)):
            if u(refs+4*i)>=0xfffffffe:p=image_at(p)
    if u(d+8):p+=u(d)*12
    if u(d+20):
        refs=p;p+=u(d+16)*8
        for i in range(u(d+16)*2):
            if u(refs+4*i)>=0xfffffffe:p=image_at(p)
    for offset in (32,36):
        if u(d+offset)>=0xfffffffe:p=image_at(p)
    if u(d+44):p+=u(d+40)*44
    if u(d+56):p+=u(d+52)
    if u(d+68):p+=u(d+64)*2
    g=152
    if u(g+28):
        axis=u(g+20);assert axis<3
        lo=struct.unpack_from('<H',b,g+8+2*axis)[0];hi=struct.unpack_from('<H',b,g+14+2*axis)[0]
        assert hi>=lo;p+=(hi-lo+1)*2
    if u(g+36):p+=u(g+32)
    if u(g+44):p+=u(g+40)*4
    if u(g+52):p+=u(g+48)*168
    assert p<=len(b)
    return p

def world_scene_extent(b):
    u=lambda p:struct.unpack_from('<I',b,p)[0]
    w=lambda p:struct.unpack_from('<H',b,p)[0]
    p=world_draw_extent(b)
    if u(212):p+=u(208)*60
    if u(248):
        refs=p;p+=u(244)*8
        for i in range(u(244)):
            if u(refs+8*i)>=0xfffffffe:p=material_end(b,p)
    for offset in (256,260):
        if u(offset)>=0xfffffffe:p=material_end(b,p)
    if u(412)>=0xfffffffe:
        h=p;p+=36
        if u(h+32)==0xffffffff:p=b.index(0,p)+1
        if u(h)==0xffffffff:p+=16+u(p+12)
    if u(448):
        records=p;p+=u(32)*12
        for i in range(u(32)):
            r=records+i*12
            if u(r+4):p+=w(r)*2
            if u(r+8):p+=w(r+2)*2
    if u(452):
        records=p;p+=u(32)*8
        for i in range(u(32)):
            r=records+i*8
            if u(r+4):
                hulls=p;p+=u(r)*80
                for j in range(u(r)):
                    hull=hulls+j*80
                    if u(hull+76):p+=u(hull+72)*20
    assert p<=len(b)
    return p

if __name__=='__main__':
    world_prefixes=0;mapents_replayed=0;clipmaps_replayed=0
    zone_prefixes=0;prefix_assets=0;stopped_types={};complete_zones=0;animations_replayed=0;effects_replayed=0;sounds_replayed={11:0,12:0,13:0}
    lighting_replayed={16:0,18:0,20:0,22:0,24:0,25:0,26:0,28:0,31:0,38:0,39:0,40:0,41:0,42:0,43:0}
    names_resolved=0;names_pooled=0;physics_replayed=0;surfaces_replayed=0;images_replayed=0;techniques_replayed=0;materials_replayed=0
    relocated_models=0
    pooled_materials=0
    pooled_surfaces=0
    model_physics=[0,0]
    model_flags={}
    root=Path(__file__).resolve().parents[1]; total=0; collisions=0; unsupported=0; materials=0; material_unsupported=0; lods=0; techniques=0
    with tempfile.TemporaryDirectory(prefix='codol-models-') as temporary:
        target=Path(temporary)/('models.dll' if os.name=='nt' else 'models.so')
        subprocess.run([os.environ.get('CC', 'gcc'), *CODOL_INCLUDE,'-shared','-fPIC','-O2','-Wall','-Wextra','-Werror',
                        str(root/'src/codol/assets/codol_load_blocks.c'),
                        str(root/'src/codol/assets/codol_xsurface.c'),
                        str(root/'src/codol/collision/codol_collision_stream.c'),str(root/'src/codol/collision/codol_map_entities.c'),
                        str(root/'src/codol/assets/codol_xmodel_bounds.c'),str(root/'src/codol/assets/codol_asset_stream.c'),str(root/'src/codol/assets/codol_xmodel_skeleton.c'),str(root/'src/codol/assets/codol_xmodel_collision.c'),'-o',str(target)],check=True)
        lib=C.CDLL(str(target));lib.CODOL_ReadXModelSkeleton.argtypes=[C.POINTER(Asset),C.POINTER(Skeleton)]
        lib.CODOL_FreeXModelSkeleton.argtypes=[C.POINTER(Skeleton)]
        lib.CODOL_ReadModelSurfaces.argtypes=[C.POINTER(Asset),C.POINTER(OwnedSurfaces)]
        lib.CODOL_FreeModelSurfaces.argtypes=[C.POINTER(OwnedSurfaces)]
        lib.CODOL_ResolveSurfaceArrays.argtypes=[C.POINTER(OwnedSurface),C.POINTER(BlockView),C.POINTER(SurfaceArrays)]
        lib.CODOL_FreeSurfaceArrays.argtypes=[C.POINTER(SurfaceArrays)]
        def verify_inline_surface_arrays(owned):
            for k in range(owned.count):
                surface=owned.surfaces[k]
                if any(a.count and not a.data for a in surface.arrays):continue
                resolved=SurfaceArrays()
                assert lib.CODOL_ResolveSurfaceArrays(C.byref(surface),(BlockView*8)(),C.byref(resolved))
                try:
                    for before,after in zip(surface.arrays,resolved.arrays):
                        assert (before.ref,before.count,before.stride)==(after.ref,after.count,after.stride)
                        assert not after.data or after.data%16==0
                        assert C.string_at(before.data,before.count*before.stride)==C.string_at(after.data,after.count*after.stride)
                finally:lib.CODOL_FreeSurfaceArrays(C.byref(resolved))
        lib.CODOL_InitLoadBlocks.argtypes=[C.POINTER(LoadBlocks),C.c_void_p,C.c_size_t,C.POINTER(C.c_uint32),C.c_uint]
        lib.CODOL_FreeLoadBlocks.argtypes=[C.POINTER(LoadBlocks)]
        lib.CODOL_ReplayPhysicsAsset.argtypes=[C.POINTER(LoadBlocks),C.c_uint,C.POINTER(C.c_uint32)]
        lib.CODOL_ReplayModelSurfaces.argtypes=[C.POINTER(LoadBlocks),C.POINTER(C.c_uint32)]
        lib.CODOL_ReplayImage.argtypes=[C.POINTER(LoadBlocks),C.POINTER(C.c_uint32)]
        lib.CODOL_ReplayTechniqueSet.argtypes=[C.POINTER(LoadBlocks),C.POINTER(C.c_uint32)]
        lib.CODOL_ReplayMaterial.argtypes=[C.POINTER(LoadBlocks),C.POINTER(C.c_uint32)]
        lib.CODOL_ReplayXModel.argtypes=[C.POINTER(LoadBlocks),C.POINTER(C.c_uint32)]
        lib.CODOL_ReplayAnimation.argtypes=[C.POINTER(LoadBlocks),C.POINTER(C.c_uint32)]
        lib.CODOL_ReplayEffect.argtypes=[C.POINTER(LoadBlocks),C.POINTER(C.c_uint32)]
        lib.CODOL_ReplaySoundAsset.argtypes=[C.POINTER(LoadBlocks),C.c_uint,C.POINTER(C.c_uint32)]
        lib.CODOL_ReplayWorldVisibility.argtypes=[C.POINTER(LoadBlocks),C.POINTER(C.c_uint32)]
        lib.CODOL_ReplayWorldDraw.argtypes=[C.POINTER(LoadBlocks),C.POINTER(C.c_uint32)]
        lib.CODOL_ReplayWorldScene.argtypes=[C.POINTER(LoadBlocks),C.POINTER(C.c_uint32)]
        lib.CODOL_ReplayWorld.argtypes=[C.POINTER(LoadBlocks),C.POINTER(C.c_uint32)]
        lib.CODOL_LocateCollisionMapEntities.argtypes=[C.POINTER(Asset),C.POINTER(C.c_size_t)]
        lib.CODOL_ReadMapEntities.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(Entities)]
        lib.CODOL_FreeMapEntities.argtypes=[C.POINTER(Entities)]
        lib.CODOL_ReplayMapEntities.argtypes=[C.POINTER(LoadBlocks),C.POINTER(C.c_uint32)]
        lib.CODOL_ReplayCollision.argtypes=[C.POINTER(LoadBlocks),C.POINTER(C.c_uint32)]
        lib.CODOL_BeginZoneReplay.argtypes=[C.POINTER(Zone),C.POINTER(LoadBlocks)]
        lib.CODOL_ReplayZoneAsset.argtypes=[C.POINTER(Zone),C.c_uint,C.POINTER(LoadBlocks)]
        lib.CODOL_ResolveXModelBoneNames.argtypes=[C.POINTER(Skeleton),C.POINTER(ScriptString),C.c_uint,C.POINTER(BoneNames)]
        lib.CODOL_FreeXModelBoneNames.argtypes=[C.POINTER(BoneNames)]
        lib.CODOL_RelocateXModelSkeleton.argtypes=[C.POINTER(Skeleton),C.POINTER(BlockView),C.POINTER(Skeleton)]
        lib.CODOL_ReadXModelCollision.argtypes=[C.POINTER(Asset),C.POINTER(Collision)]
        lib.CODOL_FreeXModelCollision.argtypes=[C.POINTER(Collision)]
        lib.CODOL_ReadXModelBounds.argtypes=[C.POINTER(Asset),C.POINTER(Bounds)]
        lib.CODOL_ReadXModelLods.argtypes=[C.POINTER(Asset),C.POINTER(Lods)]
        lib.CODOL_ReadXModelMaterials.argtypes=[C.POINTER(Asset),C.POINTER(ModelMaterials)]
        lib.CODOL_FreeXModelMaterials.argtypes=[C.POINTER(ModelMaterials)]
        lib.CODOL_FreeXModelBounds.argtypes=[C.POINTER(Bounds)]
        lib.CODOL_ReadXModelExtent.argtypes=[C.POINTER(Asset),C.POINTER(C.c_size_t)]
        lib.CODOL_XModelInlineSurfaceAssets.argtypes=[C.POINTER(Asset),C.POINTER(Asset)]
        lib.CODOL_AdvancePhysicsPresetStream.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
        lib.CODOL_AdvancePhysicsMapStream.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
        lib.CODOL_AdvanceMaterialStream.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
        lib.CODOL_AdvanceModelSurfacesStream.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
        lib.CODOL_AdvanceTechniqueSetStream.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
        try:
            for path in sorted(Path(sys.argv[1]).glob('*.zone')):
                data=path.read_bytes(); strings=struct.unpack_from('<I',data,40)[0]; table=56+strings*4
                pool=(ScriptString*strings)()
                for i in range(strings):
                    pool[i].reference=struct.unpack_from('<I',data,56+4*i)[0]
                    if pool[i].reference==0xffffffff:
                        end=data.index(0,table);pool[i].text=data[table:end];table=end+1
                zone_buffer=C.create_string_buffer(data)
                zone=Zone(C.addressof(zone_buffer),len(data),table,struct.unpack_from('<I',data,48)[0],strings,
                          (C.c_uint32*8)(*struct.unpack_from('<8I',data,8)))
                blocks=LoadBlocks()
                assert lib.CODOL_BeginZoneReplay(C.byref(zone),C.byref(blocks)),(path.name,'zone initialization')
                try:
                    assert blocks.source_position==table+zone.asset_count*16
                    for asset_index in range(zone.asset_count):
                        status=lib.CODOL_ReplayZoneAsset(C.byref(zone),asset_index,C.byref(blocks))
                        assert status>=0,(path.name,asset_index,'zone replay')
                        if status==0:
                            kind=struct.unpack_from('<I',data,table+16*asset_index)[0]
                            stopped_types[kind]=stopped_types.get(kind,0)+1;break
                        prefix_assets+=1
                    else:
                        assert blocks.source_position==len(data)
                        complete_zones+=1
                    zone_prefixes+=1
                finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                lib.CODOL_ReplayZone.argtypes=[C.POINTER(Zone),C.POINTER(LoadBlocks),C.POINTER(C.c_uint)]
                blocks=LoadBlocks();failed_asset=C.c_uint()
                assert lib.CODOL_ReplayZone(C.byref(zone),C.byref(blocks),C.byref(failed_asset)),(path.name,'whole-zone transaction',failed_asset.value)
                lib.CODOL_ResolveMaterialAlias.argtypes=[C.POINTER(LoadBlocks),C.c_uint32,C.POINTER(Asset)]
                lib.CODOL_ResolveSurfaceAlias.argtypes=[C.POINTER(LoadBlocks),C.c_uint32,C.POINTER(Asset)]
                lib.CODOL_ResolvePhysicsAlias.argtypes=[C.POINTER(LoadBlocks),C.c_uint,C.c_uint32,C.POINTER(Asset)]
                lib.CODOL_XModelInlinePhysicsAssets.argtypes=[C.POINTER(Asset),C.POINTER(Asset)]
                try:
                    assert blocks.source_position==len(data) and blocks.active==3 and blocks.depth==1
                    views=(BlockView*8)(*(BlockView(blocks.data[b],blocks.written[b]) for b in range(8)))
                    views[0]=BlockView() # Scratch headers cannot back persistent arrays.
                    for index in range(zone.asset_count):
                        kind,offset,_,size=struct.unpack_from('<4I',data,table+16*index)
                        if kind!=4:continue
                        source=Skeleton();owned=Skeleton();names=BoneNames()
                        asset=Asset(4,C.addressof(zone_buffer)+40+offset,size)
                        physics_assets=(Asset*2)()
                        assert lib.CODOL_XModelInlinePhysicsAssets(C.byref(asset),physics_assets)
                        for physics_type,ref in enumerate(struct.unpack('<2I',C.string_at(asset.data+0x160,8))):
                            if not ref:
                                assert not physics_assets[physics_type].data
                                continue
                            resolved=physics_assets[physics_type]
                            if ref<0xfffffffe:
                                assert not resolved.data
                                assert lib.CODOL_ResolvePhysicsAlias(C.byref(blocks),physics_type,ref,C.byref(resolved)),(path.name,index,physics_type,hex(ref),'physics alias')
                                assert not lib.CODOL_ResolvePhysicsAlias(C.byref(blocks),1-physics_type,ref,C.byref(Asset()))
                            blob=C.string_at(resolved.data,resolved.size)
                            assert resolved.type==physics_type
                            assert (physics_end(blob,0) if physics_type else preset_end(blob,0))==len(blob)
                            model_physics[physics_type]+=1
                        model_lods=Lods()
                        assert lib.CODOL_ReadXModelLods(C.byref(asset),C.byref(model_lods))
                        for lod in model_lods.lods:
                            if not 0<lod.surfaces<0xfffffffe:continue
                            resolved=Asset();decoded=OwnedSurfaces()
                            assert lib.CODOL_ResolveSurfaceAlias(C.byref(blocks),lod.surfaces,C.byref(resolved)),(path.name,index,hex(lod.surfaces),'pooled LOD alias')
                            assert resolved.type==3
                            assert not lib.CODOL_ResolveMaterialAlias(C.byref(blocks),lod.surfaces,C.byref(Asset()))
                            assert lib.CODOL_ReadModelSurfaces(C.byref(resolved),C.byref(decoded))
                            assert decoded.consumed==resolved.size
                            lib.CODOL_FreeModelSurfaces(C.byref(decoded));pooled_surfaces+=1
                        slots=ModelMaterials()
                        assert lib.CODOL_ReadXModelMaterials(C.byref(asset),C.byref(slots))
                        try:
                            for slot in slots.materials[:slots.count]:
                                if not 0<slot.reference<0xfffffffe:continue
                                resolved=Asset()
                                assert lib.CODOL_ResolveMaterialAlias(C.byref(blocks),slot.reference,C.byref(resolved)),(path.name,index,hex(slot.reference),'pooled material alias')
                                blob=C.string_at(resolved.data,resolved.size)
                                assert resolved.type==5 and material_end(blob,0)==len(blob)
                                pooled_materials+=1
                        finally:lib.CODOL_FreeXModelMaterials(C.byref(slots))
                        try:
                            assert lib.CODOL_ReadXModelSkeleton(C.byref(asset),C.byref(source))
                            assert lib.CODOL_RelocateXModelSkeleton(C.byref(source),views,C.byref(owned)),(path.name,index,'retained skeleton relocation')
                            assert not owned.unresolved
                            assert all(not a.data or a.data%16==0 for a in owned.arrays)
                            assert lib.CODOL_ResolveXModelBoneNames(C.byref(owned),pool,strings,C.byref(names)),(path.name,index,'retained bone names')
                            assert not names.unresolved,(path.name,index,'unresolved bone strings')
                            relocated_models+=1
                        finally:
                            lib.CODOL_FreeXModelBoneNames(C.byref(names))
                            lib.CODOL_FreeXModelSkeleton(C.byref(owned))
                            lib.CODOL_FreeXModelSkeleton(C.byref(source))
                finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                for i in range(struct.unpack_from('<I',data,48)[0]):
                    kind,offset,_,size=struct.unpack_from('<4I',data,table+16*i)
                    if kind in (14,15,19):
                        blob=data[40+offset:40+offset+size];buffer=C.create_string_buffer(blob)
                        start=C.c_size_t()
                        if kind!=19:
                            asset=Asset(kind,C.addressof(buffer),size)
                            assert lib.CODOL_LocateCollisionMapEntities(C.byref(asset),C.byref(start)),(path.name,i,'mapents position')
                        parsed=Entities();blocks=LoadBlocks();reference=C.c_uint32()
                        assert lib.CODOL_ReadMapEntities(C.addressof(buffer)+start.value,size-start.value,C.byref(parsed))
                        try:
                            caps=(C.c_uint32*8)(44,0,0,parsed.consumed+4096,0,0,0,0)
                            assert lib.CODOL_InitLoadBlocks(C.byref(blocks),buffer,size,caps,0)
                            blocks.source_position=start.value
                            assert lib.CODOL_ReplayMapEntities(C.byref(blocks),C.byref(reference)),(path.name,i,'mapents replay')
                            assert blocks.source_position-start.value==parsed.consumed and blocks.active==0 and blocks.depth==0
                            mapents_replayed+=1
                        finally:
                            lib.CODOL_FreeLoadBlocks(C.byref(blocks));lib.CODOL_FreeMapEntities(C.byref(parsed))
                        if kind in (14,15):
                            caps=(C.c_uint32*8)(*((x+4095)&~4095 for x in zone.block_size))
                            caps[0]=max(caps[0],2048)
                            assert lib.CODOL_InitLoadBlocks(C.byref(blocks),buffer,size,caps,0)
                            try:
                                assert lib.CODOL_ReplayCollision(C.byref(blocks),C.byref(reference)),(path.name,i,'complete collision replay')
                                assert blocks.source_position==size and blocks.active==0 and blocks.depth==0,(path.name,i,'collision extent',blocks.source_position,size)
                                clipmaps_replayed+=1
                            finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                    if kind==21:
                        blob=data[40+offset:40+offset+size];buffer=C.create_string_buffer(blob)
                        blocks=LoadBlocks();caps=(C.c_uint32*8)(1024,0,(zone.block_size[2]+4095)&~4095,size*2+4096,0,0,0,0);reference=C.c_uint32()
                        assert lib.CODOL_InitLoadBlocks(C.byref(blocks),buffer,size,caps,0)
                        try:
                            assert lib.CODOL_ReplayWorldVisibility(C.byref(blocks),C.byref(reference)),(path.name,i,'world visibility prefix')
                            assert blocks.source_position==world_visibility_extent(blob) and blocks.active==3 and blocks.depth==1
                            assert blocks.position[0]==628 and reference.value==1
                            world_prefixes+=1
                        finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                        assert lib.CODOL_InitLoadBlocks(C.byref(blocks),buffer,size,caps,0)
                        try:
                            assert lib.CODOL_ReplayWorldDraw(C.byref(blocks),C.byref(reference)),(path.name,i,'world draw prefix')
                            assert blocks.source_position==world_draw_extent(blob) and blocks.active==3 and blocks.depth==1
                        finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                        assert lib.CODOL_InitLoadBlocks(C.byref(blocks),buffer,size,caps,0)
                        try:
                            assert lib.CODOL_ReplayWorldScene(C.byref(blocks),C.byref(reference)),(path.name,i,'world scene prefix')
                            assert blocks.source_position==world_scene_extent(blob) and blocks.active==3 and blocks.depth==1
                        finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                        caps[0]=2048
                        for block in (6,7):caps[block]=(zone.block_size[block]+4095)&~4095
                        assert lib.CODOL_InitLoadBlocks(C.byref(blocks),buffer,size,caps,0)
                        try:
                            assert lib.CODOL_ReplayWorld(C.byref(blocks),C.byref(reference)),(path.name,i,'complete world replay')
                            assert blocks.source_position==size and blocks.active==0 and blocks.depth==0,(path.name,i,'complete world extent',blocks.source_position,size)
                        finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                    if kind in lighting_replayed:
                        # Isolated replay checks world, lighting, weapon and effect assets, including those
                        # beyond an unsupported asset in the ordered zone traversal.
                        blocks=LoadBlocks();caps=(C.c_uint32*8)(8192,0,(zone.block_size[2]+4095)&~4095,size*2+4096,0,0,0,0)
                        for block in (6,7):caps[block]=(zone.block_size[block]+4095)&~4095
                        assert lib.CODOL_InitLoadBlocks(C.byref(blocks),zone_buffer,len(data),caps,3)
                        blocks.source_position=40+offset
                        try:
                            assert lib.CODOL_ReplayZoneAsset(C.byref(zone),i,C.byref(blocks))==1,(path.name,i,'world/lighting/weapon/effect replay')
                            assert blocks.source_position==40+offset+size and blocks.active==3 and blocks.depth==0
                            lighting_replayed[kind]+=1
                        finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                    if kind in sounds_replayed:
                        blob=data[40+offset:40+offset+size];buffer=C.create_string_buffer(blob)
                        blocks=LoadBlocks();caps=(C.c_uint32*8)(size+4096,0,0,size*2+4096,0,0,0,0);reference=C.c_uint32()
                        assert lib.CODOL_InitLoadBlocks(C.byref(blocks),buffer,size,caps,0)
                        try:
                            assert lib.CODOL_ReplaySoundAsset(C.byref(blocks),kind,C.byref(reference)),(path.name,i,'sound replay',kind)
                            assert blocks.source_position==size and blocks.active==0 and blocks.depth==0,(path.name,i,'sound extent',blocks.source_position,size)
                            sounds_replayed[kind]+=1
                        finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                    if kind==30:
                        blob=data[40+offset:40+offset+size];buffer=C.create_string_buffer(blob)
                        blocks=LoadBlocks();caps=(C.c_uint32*8)(1024,0,0,size*2+4096,0,0,size*2+4096,size*2+4096);reference=C.c_uint32()
                        assert lib.CODOL_InitLoadBlocks(C.byref(blocks),buffer,size,caps,0)
                        try:
                            assert lib.CODOL_ReplayEffect(C.byref(blocks),C.byref(reference)),(path.name,i,'effect replay')
                            assert blocks.source_position==size and blocks.active==0 and blocks.depth==0,(path.name,i,'effect extent',blocks.source_position,size)
                            effects_replayed+=1
                        finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                    if kind==2:
                        blob=data[40+offset:40+offset+size];buffer=C.create_string_buffer(blob)
                        blocks=LoadBlocks();caps=(C.c_uint32*8)(88,0,0,size*2+4096,0,0,0,0);reference=C.c_uint32()
                        assert lib.CODOL_InitLoadBlocks(C.byref(blocks),buffer,size,caps,0)
                        try:
                            assert lib.CODOL_ReplayAnimation(C.byref(blocks),C.byref(reference)),(path.name,i,'animation replay')
                            assert blocks.source_position==size and blocks.active==0 and blocks.depth==0,(path.name,i,'animation extent',blocks.source_position,size)
                            animations_replayed+=1
                        finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                    if kind==10:
                        blob=data[40+offset:40+offset+size];buffer=C.create_string_buffer(blob)
                        blocks=LoadBlocks();caps=(C.c_uint32*8)(36,0,0,size+4096,0,0,0,0);reference=C.c_uint32()
                        assert lib.CODOL_InitLoadBlocks(C.byref(blocks),buffer,size,caps,0)
                        try:
                            assert lib.CODOL_ReplayImage(C.byref(blocks),C.byref(reference)),(path.name,i,'image replay')
                            assert blocks.source_position==size and blocks.active==0 and blocks.depth==0
                            assert reference.value==1 and blocks.position[0]==36
                            images_replayed+=1
                        finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                    if kind in (0,1):
                        blob=data[40+offset:40+offset+size];buffer=C.create_string_buffer(blob);end=C.c_size_t()
                        advance=lib.CODOL_AdvancePhysicsPresetStream if kind==0 else lib.CODOL_AdvancePhysicsMapStream
                        expected=(preset_end if kind==0 else physics_end)(blob,0)
                        assert advance(buffer,size,C.byref(end)) and end.value==expected==size,(path.name,i,'physics extent',end.value,expected,size)
                        blocks=LoadBlocks();capacities=(C.c_uint32*8)(72,0,0,size*2+4096,0,0,0,0);reference=C.c_uint32()
                        assert lib.CODOL_InitLoadBlocks(C.byref(blocks),buffer,size,capacities,0)
                        try:
                            assert lib.CODOL_ReplayPhysicsAsset(C.byref(blocks),kind,C.byref(reference)),(path.name,i,'physics replay')
                            assert blocks.source_position==size and blocks.active==0 and blocks.depth==0
                            assert reference.value==1 and blocks.position[0]==(68 if kind==0 else 72)
                            physics_replayed+=1
                        finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                    if kind==9:
                        blob=data[40+offset:40+offset+size];buffer=C.create_string_buffer(blob);end=C.c_size_t()
                        assert lib.CODOL_AdvanceTechniqueSetStream(buffer,size,C.byref(end)),(path.name,i,'technique')
                        assert end.value==technique_end(blob,0)==size,(path.name,i,end.value,size)
                        blocks=LoadBlocks();caps=(C.c_uint32*8)(304,0,0,size*2+4096,0,0,0,0);reference=C.c_uint32()
                        assert lib.CODOL_InitLoadBlocks(C.byref(blocks),buffer,size,caps,0)
                        try:
                            assert lib.CODOL_ReplayTechniqueSet(C.byref(blocks),C.byref(reference)),(path.name,i,'technique replay')
                            assert blocks.source_position==size and blocks.active==0 and blocks.depth==0
                            techniques_replayed+=1
                        finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                        techniques+=1
                    if kind==3:
                        blob=data[40+offset:40+offset+size];buffer=C.create_string_buffer(blob);end=C.c_size_t()
                        assert lib.CODOL_AdvanceModelSurfacesStream(buffer,size,C.byref(end)),(path.name,i,'surfaces')
                        assert end.value==lod_end(blob,0)==size,(path.name,i,end.value,size)
                        surface_asset=Asset(3,C.addressof(buffer),size);owned_surfaces=OwnedSurfaces()
                        assert lib.CODOL_ReadModelSurfaces(C.byref(surface_asset),C.byref(owned_surfaces)),(path.name,i,'owned surfaces')
                        try:
                            assert owned_surfaces.consumed==size and owned_surfaces.count==struct.unpack_from('<H',blob,8)[0]
                            verify_inline_surface_arrays(owned_surfaces)
                            header_start=blob.index(0,48)+1 if struct.unpack_from('<I',blob)[0]==0xffffffff else 48
                            for surface_index in range(owned_surfaces.count):
                                surface=owned_surfaces.surfaces[surface_index]
                                assert bytes(surface.header)==blob[header_start+84*surface_index:header_start+84*(surface_index+1)]
                                for array in surface.arrays:
                                    if array.data:
                                        assert owned_surfaces.storage<=array.data<=owned_surfaces.storage+size-array.count*array.stride
                        finally:lib.CODOL_FreeModelSurfaces(C.byref(owned_surfaces))
                        blocks=LoadBlocks();cap=size*2+4096;caps=(C.c_uint32*8)(48,0,0,cap,0,0,cap,cap);reference=C.c_uint32()
                        assert lib.CODOL_InitLoadBlocks(C.byref(blocks),buffer,size,caps,0)
                        try:
                            assert lib.CODOL_ReplayModelSurfaces(C.byref(blocks),C.byref(reference)),(path.name,i,'surface replay')
                            assert blocks.source_position==size and blocks.active==0 and blocks.depth==0
                            surfaces_replayed+=1
                        finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                        lods+=1
                    if kind==5:
                        blob=data[40+offset:40+offset+size];buffer=C.create_string_buffer(blob);end=C.c_size_t()
                        expected=material_end(blob,0);ok=lib.CODOL_AdvanceMaterialStream(buffer,size,C.byref(end))
                        if expected is None:
                            assert not ok;material_unsupported+=1
                        else:
                            assert ok and end.value==expected==size,(path.name,i,'material extent',end.value,expected,size)
                            blocks=LoadBlocks();caps=(C.c_uint32*8)(400,0,0,size*2+4096,0,0,0,0);reference=C.c_uint32()
                            assert lib.CODOL_InitLoadBlocks(C.byref(blocks),buffer,size,caps,0)
                            try:
                                assert lib.CODOL_ReplayMaterial(C.byref(blocks),C.byref(reference)),(path.name,i,'material replay')
                                assert blocks.source_position==size and blocks.active==0 and blocks.depth==0
                                materials_replayed+=1
                            finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                            materials+=1
                    if kind!=4:continue
                    blob=data[40+offset:40+offset+size]; buffer=C.create_string_buffer(blob)
                    asset=Asset(4,C.addressof(buffer),size); result=Skeleton()
                    assert lib.CODOL_ReadXModelSkeleton(C.byref(asset),C.byref(result)),(path.name,i)
                    try:
                        assert (result.bones,result.roots,result.surfaces)==tuple(blob[4:7])
                        inline_assets=(Asset*4)()
                        assert lib.CODOL_XModelInlineSurfaceAssets(C.byref(asset),inline_assets)
                        decoded_lods=Lods()
                        assert lib.CODOL_ReadXModelLods(C.byref(asset),C.byref(decoded_lods)),(path.name,i,'LOD metadata')
                        assert (decoded_lods.first,decoded_lods.count)==tuple(blob[0x128:0x12a])
                        assert decoded_lods.collision_lod==struct.unpack_from('<b',blob,0x12a)[0]
                        assert bytes(decoded_lods.lods)==blob[0x48:0x128]
                        pos=0x168; unresolved=0; ref=struct.unpack_from('<I',blob)[0]
                        if ref==0xffffffff:
                            end=blob.index(0,pos);assert result.name==blob[pos:end];pos=end+1
                        elif ref:unresolved+=1
                        for j,stride in enumerate((2,1,8,12,1,32)):
                            a=result.arrays[j];ref=struct.unpack_from('<I',blob,0x2c+4*j)[0]
                            count=result.bones-result.roots if j in (1,2,3) else result.bones
                            assert (a.ref,a.count,a.stride)==(ref,count,stride)
                            if ref==0xffffffff:
                                assert a.data%16==0
                                assert C.string_at(a.data,count*stride)==blob[pos:pos+count*stride];pos+=count*stride
                            else:
                                assert not a.data
                                if ref and count:unresolved+=1
                        assert result.consumed==pos and result.unresolved==unresolved
                        names=BoneNames()
                        resolved=lib.CODOL_ResolveXModelBoneNames(C.byref(result),pool,strings,C.byref(names))
                        names_resolved+=bool(resolved);names_pooled+=not resolved
                        assert bool(resolved)==bool(result.arrays[0].data or not result.bones),(path.name,i,'bone names')
                        try:
                            assert names.count==(result.bones if resolved else 0)
                            missing=0
                            raw=C.string_at(result.arrays[0].data,2*result.bones) if resolved else b''
                            for j in range(names.count):
                                index=struct.unpack_from('<H',raw,2*j)[0]
                                assert names.names[j].index==index
                                assert names.names[j].reference==pool[index].reference
                                assert names.names[j].text==pool[index].text
                                missing+=pool[index].text is None
                            assert names.unresolved==missing
                        finally:lib.CODOL_FreeXModelBoneNames(C.byref(names))
                        decoded_materials=ModelMaterials()
                        assert lib.CODOL_ReadXModelMaterials(C.byref(asset),C.byref(decoded_materials))
                        assert decoded_materials.count==result.surfaces
                        assert decoded_materials.reference==struct.unpack_from('<I',blob,0x44)[0]
                        supported=True
                        if struct.unpack_from('<I',blob,0x44)[0]:
                            refs=struct.unpack_from('<'+'I'*result.surfaces,blob,pos);pos+=4*result.surfaces
                            for slot,r in enumerate(refs):
                                decoded=decoded_materials.materials[slot]
                                assert decoded.reference==r
                                if r>=0xfffffffe:
                                    next_pos=material_end(blob,pos)
                                    if next_pos is None:supported=False;break
                                    assert decoded.inline_asset.type==5 and decoded.inline_asset.size==next_pos-pos
                                    assert C.string_at(decoded.inline_asset.data,next_pos-pos)==blob[pos:next_pos]
                                    pos=next_pos
                                else:assert not decoded.inline_asset.data
                        else:
                            assert all(not decoded_materials.materials[k].reference for k in range(result.surfaces))
                        if supported:assert decoded_materials.consumed==pos
                        lib.CODOL_FreeXModelMaterials(C.byref(decoded_materials))
                        if supported:
                            for j in range(4):
                                if struct.unpack_from('<I',blob,0x50+56*j)[0]>=0xfffffffe:
                                    start=pos;pos=lod_end(blob,pos);length=pos-start;chunk=C.create_string_buffer(blob[start:pos])
                                    assert inline_assets[j].size==length
                                    assert C.string_at(inline_assets[j].data,length)==blob[start:pos]
                                    nested_asset=Asset(3,C.addressof(chunk),length);nested_owned=OwnedSurfaces()
                                    assert lib.CODOL_ReadModelSurfaces(C.byref(nested_asset),C.byref(nested_owned)),(path.name,i,'nested owned surfaces')
                                    assert nested_owned.consumed==length
                                    verify_inline_surface_arrays(nested_owned)
                                    lib.CODOL_FreeModelSurfaces(C.byref(nested_owned))
                                    blocks=LoadBlocks();cap=length*2+4096;caps=(C.c_uint32*8)(48,0,0,cap,0,0,cap,cap);reference=C.c_uint32()
                                    assert lib.CODOL_InitLoadBlocks(C.byref(blocks),chunk,length,caps,0)
                                    try:
                                        assert lib.CODOL_ReplayModelSurfaces(C.byref(blocks),C.byref(reference)),(path.name,i,'nested surface replay')
                                        assert blocks.source_position==length and blocks.active==0 and blocks.depth==0
                                        surfaces_replayed+=1
                                    finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                                if struct.unpack_from('<I',blob,0x54+56*j)[0]==0xffffffff:pos=blob.index(0,pos)+1
                        collision=Collision(); ok=lib.CODOL_ReadXModelCollision(C.byref(asset),C.byref(collision))
                        if not supported:
                            assert not ok;unsupported+=1
                        else:
                            assert ok,(path.name,i,'collision')
                            try:
                                assert collision.count==struct.unpack_from('<I',blob,0x130)[0]
                                start=pos;pos+=collision.count*44
                                for j,surface in enumerate(collision.surfaces[:collision.count]):
                                    at=start+j*44;values=struct.unpack_from('<6f',blob,at+8)
                                    assert tuple(surface.mins)==tuple(C.c_float(values[k]-values[k+3]).value for k in range(3))
                                    assert tuple(surface.maxs)==tuple(C.c_float(values[k]+values[k+3]).value for k in range(3))
                                    assert (surface.bone,surface.contents,surface.flags)==struct.unpack_from('<3i',blob,at+32)
                                    assert surface.tri_count==struct.unpack_from('<I',blob,at+4)[0]
                                    assert C.string_at(surface.triangles,surface.tri_count*48)==blob[pos:pos+surface.tri_count*48]
                                    pos+=surface.tri_count*48
                                assert collision.consumed==pos
                                geometry=Bounds()
                                assert lib.CODOL_ReadXModelBounds(C.byref(asset),C.byref(geometry)),(path.name,i,'bounds')
                                try:
                                    values=struct.unpack_from('<6f',blob,0x140)
                                    assert tuple(geometry.mins)==tuple(C.c_float(values[k]-values[k+3]).value for k in range(3))
                                    assert tuple(geometry.maxs)==tuple(C.c_float(values[k]+values[k+3]).value for k in range(3))
                                    assert geometry.radius==struct.unpack_from('<f',blob,0x13c)[0]
                                    assert geometry.contents==struct.unpack_from('<I',blob,0x134)[0]
                                    assert geometry.flags==blob[0x12b]
                                    model_flags[geometry.flags]=model_flags.get(geometry.flags,0)+1
                                    assert geometry.count==result.bones
                                    assert geometry.ref==struct.unpack_from('<I',blob,0x138)[0]
                                    if geometry.ref:
                                        for k in range(geometry.count):
                                            raw=struct.unpack_from('<7f',blob,pos+28*k);bone=geometry.bones[k]
                                            assert tuple(bone.offset)==raw[:3]
                                            assert tuple(bone.bounds[0])==tuple(C.c_float(raw[a]-raw[a+3]).value for a in range(3))
                                            assert tuple(bone.bounds[1])==tuple(C.c_float(raw[a]+raw[a+3]).value for a in range(3))
                                            assert bone.radiusSquared==raw[6]
                                        pos+=geometry.count*28
                                    else:assert not geometry.bones
                                    assert geometry.consumed==pos
                                    assert (geometry.preset,geometry.physics)==struct.unpack_from('<2I',blob,0x160)
                                    if not geometry.preset and not geometry.physics:assert pos==size
                                    for kind,ref,extent in ((0,geometry.preset,preset_end),(1,geometry.physics,physics_end)):
                                        if ref<0xfffffffe:continue
                                        start=pos;pos=extent(blob,pos);chunk=C.create_string_buffer(blob[start:pos]);length=pos-start
                                        blocks=LoadBlocks();caps=(C.c_uint32*8)(72,0,0,length*2+4096,0,0,0,0);reference=C.c_uint32()
                                        assert lib.CODOL_InitLoadBlocks(C.byref(blocks),chunk,length,caps,0)
                                        try:
                                            assert lib.CODOL_ReplayPhysicsAsset(C.byref(blocks),kind,C.byref(reference)),(path.name,i,'nested physics replay')
                                            assert blocks.source_position==length and blocks.active==0 and blocks.depth==0
                                            physics_replayed+=1
                                        finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                                    end=C.c_size_t()
                                    assert lib.CODOL_ReadXModelExtent(C.byref(asset),C.byref(end)) and end.value==pos==size,(path.name,i,'model extent',end.value,pos,size)
                                    blocks=LoadBlocks();cap=size*2+4096;caps=(C.c_uint32*8)(760,0,0,cap,0,0,cap,cap);reference=C.c_uint32()
                                    assert lib.CODOL_InitLoadBlocks(C.byref(blocks),buffer,size,caps,0)
                                    try:
                                        assert lib.CODOL_ReplayXModel(C.byref(blocks),C.byref(reference)),(path.name,i,'complete model replay')
                                        assert blocks.source_position==size and blocks.active==0 and blocks.depth==0
                                        assert reference.value==1 and blocks.position[0]==360
                                    finally:lib.CODOL_FreeLoadBlocks(C.byref(blocks))
                                finally:lib.CODOL_FreeXModelBounds(C.byref(geometry))
                                collisions+=1
                            finally:lib.CODOL_FreeXModelCollision(C.byref(collision))
                        total+=1
                    finally:lib.CODOL_FreeXModelSkeleton(C.byref(result))
        finally:
            if os.name=='nt':
                import _ctypes
                _ctypes.FreeLibrary(lib._handle)
    assert zone_prefixes and complete_zones==zone_prefixes and not stopped_types,(
        'incomplete ordered zone replay',complete_zones,zone_prefixes,stopped_types)
    print(f'PASS: {total} native XModel skeletal prefixes, inline arrays and explicit pooled references')
    print(f'PASS: {total} model material-slot references and inline asset views')
    print(f'PASS: {collisions} collision records; {unsupported} models explicitly require nested dependency loaders')
    print(f'PASS: {materials} complete material extents; {material_unsupported} require nested technique loaders')
    print(f'PASS: {lods} complete standalone model-surface extents')
    print(f'PASS: {techniques} complete standalone technique-set extents')
    print(f'PASS: {collisions} model and bone bounds, centers, radii and preserved physics references')
    print(f'PASS: {collisions} complete XModel extents including inline physics dependencies')
    print(f'PASS: {names_resolved} owned bone-name bindings; {names_pooled} pooled index arrays explicitly require relocation')
    print(f'PASS: {relocated_models} complete owned skeletons and bone names resolved from retained zone blocks')
    print(f'PASS: {pooled_materials} pooled model material slots resolved to complete typed source assets')
    print(f'PASS: {pooled_surfaces} pooled LOD surface references resolved to complete typed source assets')
    print(f'PASS: model physics dependencies resolved: {model_physics[0]} presets, {model_physics[1]} collision maps')
    print(f'PASS: model flag bytes preserved: {model_flags}')
    print(f'PASS: {physics_replayed} standalone and inline physics assets replayed into loader blocks')
    print(f'PASS: {surfaces_replayed} standalone and inline surface assets replayed across blocks 3, 6 and 7')
    print(f'PASS: {images_replayed} standalone images replayed into loader blocks')
    print(f'PASS: {techniques_replayed} standalone technique sets replayed into loader blocks')
    print(f'PASS: {materials_replayed} complete standalone materials replayed with dependencies')
    print(f'PASS: {collisions} complete XModels replayed with all inline dependencies')
    print(f'PASS: {zone_prefixes} zone initializations, {prefix_assets} ordered assets, {complete_zones} complete zones; unsupported stops {stopped_types}')
    print(f'PASS: {animations_replayed} complete standalone animations replayed')
    print(f'PASS: {effects_replayed} complete standalone effects replayed')
    print(f'PASS: sound assets replayed by type: {sounds_replayed}')
    print(f'PASS: world/lighting/weapon/effect assets replayed by type: {lighting_replayed}')
    print(f'PASS: {world_prefixes} complete graphics worlds, including all earlier prefix checks')
    print(f'PASS: {mapents_replayed} map entity records replayed with triggers and stages')
    print(f'PASS: {clipmaps_replayed} complete collision maps replayed with dependencies')
