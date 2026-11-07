"""Native IWD key derivation/cipher tests; optional C1.exe and original model IWDs."""
import ctypes as C
import json
import os
from pathlib import Path
import re
import random
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib
import pathlib as _codol_pl
_codol_src=_codol_pl.Path(__file__).resolve().parents[1]/'src'
CODOL_INCLUDE=['-I'+str(_codol_src)]+['-I'+str(d) for d in sorted((_codol_src/'codol').iterdir()) if d.is_dir()]

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    dll=Path(tmp)/('iwd.dll' if os.name=='nt' else 'iwd.so')
    make=(root/'src/mbedtls/makefile').read_text().split('OBJS_CRYPTO=',1)[1].split('OBJS_X509=',1)[0]
    sources=[str(root/'src/mbedtls'/f'{n}.c') for n in re.findall(r'(\w+)\.o',make)]
    sources += [str(root/'src/zlib'/f'{n}.c') for n in ('unzip','iw4ol_utils','inflate','inffast','inftrees','adler32','crc32')]
    stub=Path(tmp)/'memory.c'
    stub.write_text('#include <stdlib.h>\nvoid *Z_TagMalloc(int n,int tag){(void)tag;return malloc(n);}\nvoid Z_Free(void *p){free(p);}\n')
    sources.append(str(stub))
    subprocess.run([os.environ.get('CC', 'gcc'), *CODOL_INCLUDE,'-shared','-fPIC','-static-libgcc','-DCODOL_SERVER','-O1','-I'+str(root/'src'),
        str(root/'src/codol/assets/codol_client_crypto.c'),str(root/'src/codol/assets/codol_iwd_crypto.c'),str(root/'src/codol/assets/codol_iwd_fs.c'),*sources,'-o',str(dll)],check=True)
    lib=C.CDLL(str(dll))
    lib.CODOL_ReadIwdKey.argtypes=[C.c_char_p,C.c_void_p]
    lib.CODOL_InitIwdFilesystem.argtypes=[C.c_char_p]
    lib.CODOL_ClearIwdFilesystem.argtypes=[]
    lib.CODOL_IsEncryptedIwd.argtypes=[C.c_char_p]
    lib.CODOL_OpenIwdArchive.argtypes=[C.c_char_p];lib.CODOL_OpenIwdArchive.restype=C.c_void_p
    lib.CODOL_IwdChecksumWord.argtypes=[C.c_char_p,C.c_uint32,C.c_uint32]
    lib.CODOL_IwdChecksumWord.restype=C.c_uint32
    lib.CODOL_DecryptClientMaterial.argtypes=[C.c_char_p,C.c_void_p,C.c_void_p,C.c_size_t]
    filename=lib.CODOL_IwdCryptFilename;chunk=lib.CODOL_IwdCryptDataChunk
    for fn in (filename,chunk):fn.argtypes=[C.c_void_p,C.c_uint32,C.c_uint32,C.c_void_p,C.c_void_p,C.c_size_t]
    key=C.create_string_buffer(bytes(range(24)))
    lib.unzOpenIwd.argtypes=[C.c_char_p,C.c_void_p];lib.unzOpenIwd.restype=C.c_void_p
    lib.unzOpen.argtypes=[C.c_char_p];lib.unzOpen.restype=C.c_void_p
    for n in ('unzClose','unzGoToFirstFile','unzGoToNextFile','unzOpenCurrentFile','unzCloseCurrentFile'):
        getattr(lib,n).argtypes=[C.c_void_p]
    lib.unzGetOffset.argtypes=[C.c_void_p];lib.unzGetOffset.restype=C.c_ulong
    lib.unzSetOffset.argtypes=[C.c_void_p,C.c_ulong]
    lib.unzReadCurrentFile.argtypes=[C.c_void_p,C.c_void_p,C.c_uint]
    lib.unzGetCurrentFileInfo.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_ulong,C.c_void_p,C.c_ulong,C.c_void_p,C.c_ulong]
    def check_zip(path,expected_path,encrypted):
        h=lib.CODOL_OpenIwdArchive(os.fsencode(path)) if encrypted==2 else lib.unzOpenIwd(os.fsencode(path),key) if encrypted else lib.unzOpen(os.fsencode(path))
        assert h
        try:
            with zipfile.ZipFile(expected_path) as expected:
                seen=set()
                for _ in expected.infolist():
                    position=lib.unzGetOffset(h)
                    assert lib.unzGoToFirstFile(h)==0 and lib.unzSetOffset(h,position)==0
                    if encrypted and lib.CODOL_IsEncryptedIwd(os.fsencode(path)):
                        assert lib.unzSetOffset(h,position+1)!=0 and lib.unzGetOffset(h)==position
                    name=C.create_string_buffer(65536)
                    assert lib.unzGetCurrentFileInfo(h,None,name,len(name),None,0,None,0)==0
                    entry=expected.getinfo(name.value.decode());seen.add(entry.filename)
                    prefix=C.create_string_buffer(5)
                    assert lib.unzGetCurrentFileInfo(h,None,prefix,5,None,0,None,0)==0
                    assert prefix.raw==entry.filename.encode()[:5]
                    assert lib.unzOpenCurrentFile(h)==0
                    data=bytearray();i=0
                    while True:
                        size=(1,7,16385,65537)[i%4];i+=1;buf=C.create_string_buffer(size)
                        n=lib.unzReadCurrentFile(h,buf,size);assert n>=0
                        if not n:break
                        data+=buf.raw[:n]
                    assert lib.unzCloseCurrentFile(h)==0
                    assert data==expected.read(entry.filename)
                    lib.unzGoToNextFile(h)
                assert seen==set(expected.namelist())
        finally:assert lib.unzClose(h)==0
    def crypt(fn,data,archive,ordinal):
        src=C.create_string_buffer(data);out=C.create_string_buffer(len(data))
        assert fn(key,archive,ordinal,src,out,len(data))
        return out.raw
    plain=bytes(range(64))
    assert crypt(filename,plain,0x12345678,7).hex()=='a2b11e001924626137064431326abe4f02dd9b1afb2cd7fcbcff0399b431c721148ee8b58ee4e3d979a0351d5d0664d295750c607e5c4a42cf2e10d46ceb8cdb'
    assert crypt(chunk,plain,0x12345678,0x4001).hex()=='89780b9e2710e33e2233d2da15aeda970aa79e402cc74474c1a86ae096a2c9c20bc82766e7986d3f4c1923a491f0a3f165ba39b34685d3dd215879fddbaaf093'
    sentinel=C.create_string_buffer(b'unchanged');before=sentinel.raw
    assert not chunk(key,0,0,None,sentinel,0x4001) and sentinel.raw==before
    assert not filename(key,0,0,None,sentinel,65536) and sentinel.raw==before
    saved=key.raw
    assert not lib.CODOL_ReadIwdKey(b'/missing-codol-client.exe',key) and key.raw==saved
    plain_zip=Path(tmp)/'_repacked'/'iw_model_test.iwd';plain_zip.parent.mkdir()
    with zipfile.ZipFile(plain_zip,'w') as z:
        z.writestr('models/stored',bytes(range(256))*2,compress_type=0)
        z.writestr('models/deflated',random.Random(3).randbytes(50000),compress_type=8)
        z.writestr('models/empty',b'',compress_type=0)
    encrypted=bytearray(plain_zip.read_bytes());archive=zlib.crc32(plain_zip.name.encode());data_offsets=[]
    with zipfile.ZipFile(plain_zip) as z:
        central=z.start_dir
        for index,entry in enumerate(z.infolist()):
            local=entry.header_offset
            name_size,extra_size=struct.unpack_from('<HH',encrypted,local+26)
            name=bytes(encrypted[local+30:local+30+name_size])
            ciphertext=crypt(filename,name,archive,index)
            encrypted[local+30:local+30+name_size]=ciphertext
            offset=local+30+name_size+extra_size;data_offsets.append(offset)
            for pos in range(0,entry.compress_size,0x4000):
                size=min(0x4000,entry.compress_size-pos)
                encrypted[offset+pos:offset+pos+size]=crypt(chunk,bytes(encrypted[offset+pos:offset+pos+size]),archive,offset+pos)
            nl,el,cl=struct.unpack_from('<HHH',encrypted,central+28)
            assert nl==name_size
            encrypted[central+46:central+46+nl]=ciphertext;central+=46+nl+el+cl
    encrypted_zip=Path(tmp)/plain_zip.name;encrypted_zip.write_bytes(encrypted)
    check_zip(encrypted_zip,plain_zip,True);check_zip(plain_zip,plain_zip,False)
    for name in (b'iw_model_00.iwd',b'localized_chinese_iw_sound_00.iwd',b'C:\\main\\iw_ui_image_00.iwd',b'/main/iw_adlc_00.iwd'):
        assert lib.CODOL_IsEncryptedIwd(name)
    assert not lib.CODOL_IsEncryptedIwd(b'/iw_model_directory/custom.iwd')
    assert not lib.CODOL_OpenIwdArchive(os.fsencode(encrypted_zip))
    ordinary=Path(tmp)/'iw_model_directory'/'custom.iwd';ordinary.parent.mkdir()
    ordinary.write_bytes(plain_zip.read_bytes());check_zip(ordinary,plain_zip,2)
    bad_path=Path(tmp)/'bad'/plain_zip.name;bad_path.parent.mkdir()
    encrypted[data_offsets[0]]^=1;bad_path.write_bytes(encrypted)
    h=lib.unzOpenIwd(os.fsencode(bad_path),key);assert h and lib.unzOpenCurrentFile(h)==0
    buf=C.create_string_buffer(1024)
    assert lib.unzReadCurrentFile(h,buf,1024)==512
    assert lib.unzCloseCurrentFile(h)!=0 and lib.unzClose(h)==0
    files=0;total=0
    checksum_archives=0
    if len(sys.argv)>1:
        assert lib.CODOL_ReadIwdKey(os.fsencode(sys.argv[1]),key)
        assert lib.CODOL_InitIwdFilesystem(os.fsencode(sys.argv[1]))
        if os.environ.get('CODOL_IWD_CHECKSUM_CATALOG'):
            catalog=json.loads(Path(os.environ['CODOL_IWD_CHECKSUM_CATALOG']).read_text())
            class FileInfo(C.Structure):
                _fields_=[('words',C.c_ulong*14),('time',C.c_uint*6)]
            for row in catalog['archives']:
                path=Path(sys.argv[1]).parent/'main'/row['archive']
                h=lib.CODOL_OpenIwdArchive(os.fsencode(path));assert h
                words=[]
                try:
                    for index in range(row['entry_count']):
                        info=FileInfo();name=C.create_string_buffer(256)
                        assert lib.unzGetCurrentFileInfo(h,C.byref(info),name,len(name),None,0,None,0)==0
                        if info.words[7]:
                            words.append(lib.CODOL_IwdChecksumWord(name.value,info.words[5],row['hash_size']))
                        next_result=lib.unzGoToNextFile(h)
                        assert next_result == (0 if index+1<row['entry_count'] else -100)
                finally:
                    assert lib.unzClose(h)==0
                checksum=zlib.crc32(struct.pack('<'+'I'*len(words),*words))
                assert checksum==row['client_checksum'],(path.name,hex(checksum),hex(row['client_checksum']))
                checksum_archives+=1
        with open(sys.argv[1],'rb') as f:
            f.seek(0x838b20);blob=C.create_string_buffer(f.read(256))
        untouched=C.create_string_buffer(b'x'*40);before=untouched.raw
        assert not lib.CODOL_DecryptClientMaterial(os.fsencode(sys.argv[1]),blob,untouched,40)
        assert untouched.raw==before
        bad=C.create_string_buffer(256)
        assert not lib.CODOL_DecryptClientMaterial(os.fsencode(sys.argv[1]),bad,untouched,24)
        assert untouched.raw==before
        for path in map(Path,sys.argv[2:]):
            check_zip(path,path.parent/'_repacked'/path.name,2)
            check_zip(path.parent/'_repacked'/path.name,path.parent/'_repacked'/path.name,False)
            archive=zlib.crc32(path.name.encode())
            with path.open('rb') as f,zipfile.ZipFile(f) as z,zipfile.ZipFile(path.parent/'_repacked'/path.name) as expected:
                for index,entry in enumerate(z.infolist()):
                    f.seek(entry.header_offset);h=f.read(30)
                    assert h[:4]==b'PK\x03\x04'
                    name_size,extra_size=struct.unpack_from('<HH',h,26)
                    name=crypt(filename,f.read(name_size),archive,index).split(b'\0',1)[0].decode()
                    offset=entry.header_offset+30+name_size+extra_size
                    f.seek(offset);encrypted=f.read(entry.compress_size);compressed=bytearray()
                    assert len(encrypted)==entry.compress_size
                    for pos in range(0,len(encrypted),0x4000):
                        compressed+=crypt(chunk,encrypted[pos:pos+0x4000],archive,offset+pos)
                    data=zlib.decompress(compressed,-15) if entry.compress_type==8 else bytes(compressed)
                    assert len(data)==entry.file_size and zlib.crc32(data)==entry.CRC
                    assert data==expected.read(name),(path.name,name)
                    files+=1;total+=len(data)
        if len(sys.argv)>2:
            h=lib.CODOL_OpenIwdArchive(os.fsencode(sys.argv[2]));assert h
            assert not lib.CODOL_InitIwdFilesystem(b'/missing-codol-client.exe')
            assert not lib.CODOL_OpenIwdArchive(os.fsencode(sys.argv[2]))
            name=C.create_string_buffer(65536)
            assert lib.unzGetCurrentFileInfo(h,None,name,len(name),None,0,None,0)==0
            assert name.value.startswith(b'models/') and lib.unzClose(h)==0
        lib.CODOL_ClearIwdFilesystem()
    print(f'PASS: native IWD ZIP/cipher fixtures; {files} original entries, {total} bytes match repacked files')
    if checksum_archives:
        print(f'PASS: {checksum_archives} native archive checksum vectors match independently read C1 records')
    if os.name=='nt':
        import _ctypes
        _ctypes.FreeLibrary(lib._handle)
