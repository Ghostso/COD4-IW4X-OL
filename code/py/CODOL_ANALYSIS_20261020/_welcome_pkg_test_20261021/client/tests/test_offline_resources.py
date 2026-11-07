"""验证按需补件只发布真实、完整、指定版本的缓存资源。"""
import contextlib
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib
from Crypto.Cipher import AES
from codol_rebuild.resources import offline_resources as resources

KEY = bytes(range(24))
NAME = 'MixedCase.iwi'
DATA = b'IWi\x09' + bytes(28) + bytes(range(256))*300


def encoded(data=DATA, filename=NAME, packed=None, declared=None):
    # 测试夹具使用独立的加密方向构造输入，覆盖多个 CTR 分块。
    size = len(data) if declared is None else declared
    compressed = zlib.compress(data, level=0) if packed is None else packed
    name = filename.encode('utf-8'); nonce = zlib.crc32(name, len(name))
    result = bytearray()
    for offset in range(0,len(compressed),32768):
        chunk = compressed[offset:offset+32768]
        iv = struct.pack('<4I',nonce,size,offset,len(chunk))
        result.extend(AES.new(KEY,AES.MODE_CTR,nonce=b'',initial_value=int.from_bytes(iv,'big')).encrypt(chunk))
    return bytes(result)+struct.pack('<I',size)


class ResourceFixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.workspace=self.root/'client/workspaces'
        self.runtime=self.workspace/'offline-runs/test/runtime';self.runtime.mkdir(parents=True)
        self.archive='lf_init_common_marketplace_1_V49.ifs'
        self.source=self.root/'Original Client/IIPS/IIPSDownload'/self.archive
        self.source.parent.mkdir(parents=True);self.source.write_bytes(b'fixture new-version archive')
        self.folder=self.workspace/'offline-resource-raw'/Path(self.archive).stem
        self.raw=self.folder/'main/images'/NAME;self.raw.parent.mkdir(parents=True);self.raw.write_bytes(encoded())
        self.entry={'path':f'main/images/{NAME}','decode_filename':NAME,'encoded_size':self.raw.stat().st_size,'encoded_sha256':resources.file_digest(self.raw)}
        self.receipt={'archive':{'name':self.archive,'sha256':resources.file_digest(self.source)},'entries':{f'main/images/{NAME.lower()}':self.entry}}
        receipt_path=self.folder/'extraction-inventory.json';receipt_path.write_text(json.dumps(self.receipt),encoding='utf-8')
        self.codec=self.root/'codec.txt';self.codec.write_text("KEY = bytes.fromhex('"+KEY.hex()+"')",encoding='ascii')
        self.patches=contextlib.ExitStack();self.addCleanup(self.patches.close)
        self.patches.enter_context(patch.dict(resources.ARCHIVES,{self.archive:resources.file_digest(self.source)},clear=True))
        self.patches.enter_context(patch.dict(resources.RAW_INVENTORIES,{self.archive:resources.file_digest(receipt_path)},clear=True))
        self.patches.enter_context(patch.object(resources,'CODEC_SHA',resources.file_digest(self.codec)))

    def supplier(self):
        return resources.OfflineResourceSupplier(self.root,self.runtime,codec_path=self.codec)

    def test_relative_absolute_and_repeat_publish(self):
        supplier=self.supplier();result=supplier.supply(r'.\main\images\mixedcase.iwi')
        self.assertEqual(result['status'],'supplied');self.assertEqual(Path(result['destination']).read_bytes(),DATA)
        again=supplier.supply(str(self.runtime/'main/images/mixedcase.iwi'))
        self.assertEqual(again['status'],'already_present')
        self.assertEqual(result['provenance']['encoded_sha256'],self.entry['encoded_sha256'])
        self.assertEqual(len((self.runtime.parent/'resource-supply.jsonl').read_text(encoding='utf-8').splitlines()),2)

    def test_wrong_archive_and_changed_cache_never_publish(self):
        supplier=self.supplier();self.source.write_bytes(b'wrong version')
        self.assertEqual(supplier.supply('images/mixedcase.iwi')['status'],'error')
        self.assertFalse((self.runtime/'main/images/mixedcase.iwi').exists())

    def test_ciphertext_tamper_fails_before_decryption(self):
        supplier=self.supplier();self.raw.write_bytes(bytes([self.raw.read_bytes()[0]^1])+self.raw.read_bytes()[1:])
        result=supplier.supply('images/mixedcase.iwi')
        self.assertEqual(result['status'],'error');self.assertIn('摘要',result['reason'])

    def test_only_main_images_and_no_escape(self):
        supplier=self.supplier()
        for name in ['../images/mixedcase.iwi','main/images/../mixedcase.iwi',str(self.root/'outside.iwi'),'main/images/test.iwi:stream']:
            self.assertEqual(supplier.supply(name)['status'],'error',name)
        for name in [r'.\raw\images\mixedcase.iwi','main/test.cfg','images/missing.iwi']:
            self.assertEqual(supplier.supply(name)['status'],'not_found',name)

    def test_receipt_entry_without_actual_file_is_not_found(self):
        supplier=self.supplier();self.raw.unlink()
        self.assertEqual(supplier.supply('images/mixedcase.iwi')['status'],'not_found')

    def test_existing_different_target_is_never_overwritten(self):
        target=self.runtime/'main/images/mixedcase.iwi';target.parent.mkdir(parents=True);target.write_bytes(b'preserve me')
        self.assertEqual(self.supplier().supply('images/mixedcase.iwi')['status'],'error')
        self.assertEqual(target.read_bytes(),b'preserve me')

    def test_actual_receipt_without_public_listing_is_supported(self):
        # 一些新版小分片没有导出 .lst；真实提取收据仍能绑定实际文件及原始文件名。
        self.assertEqual(list(self.folder.glob('*.lst')),[])
        result=self.supplier().supply('images/mixedcase.iwi')
        self.assertEqual(result['status'],'supplied')
        self.assertEqual(result['sha256'],resources.digest(DATA))

    def test_runtime_and_inventory_boundary(self):
        with self.assertRaises(ValueError):resources.OfflineResourceSupplier(self.root,self.root)
        (self.folder/'extraction-inventory.json').write_text('{}',encoding='utf-8')
        with self.assertRaises(ValueError):self.supplier()

    def test_decoded_cache_digest_is_required(self):
        output=self.root/'client/resources/v1649370/offline-resources';target=output/'main/images/mixedcase.iwi';target.parent.mkdir(parents=True);target.write_bytes(DATA)
        report={'source_exe_sha256':resources.EXE_SHA,'source_resource_version':461,'old_version_resources_used':False,'output_root':str(output),'resources':[{'game_path':'main/images/mixedcase.iwi','archive':self.archive,'size':len(DATA),'sha256':resources.digest(DATA)}]}
        (self.root/'client/resources/v1649370/offline-resources-manifest-v3.json').write_text(json.dumps(report),encoding='utf-8')
        # 部署位置不依赖生成时的绝对 output_root；保留历史清单也能加载。
        report['output_root'] = 'Z:/historical/rebuild/workspaces/offline-resources'
        (self.root/'client/resources/v1649370/offline-resources-manifest-v3.json').write_text(json.dumps(report),encoding='utf-8')
        supplier=self.supplier()
        self.assertEqual(supplier._decoded['main/images/mixedcase.iwi'][0], target)
        target.write_bytes(b'bad!'+DATA[4:])
        self.assertEqual(supplier.supply('images/mixedcase.iwi')['status'],'error')


class DecoderTests(unittest.TestCase):
    def test_multiblock_original_filename_case(self):
        self.assertEqual(resources.decode_iwi(encoded(),NAME,KEY),DATA)
        with self.assertRaises((ValueError,zlib.error)):resources.decode_iwi(encoded(),NAME.lower(),KEY)

    def test_eof_tail_size_version_are_mandatory(self):
        invalid=[encoded(packed=zlib.compress(DATA)+b'trailing'),encoded(packed=zlib.compress(DATA)[:-2]),encoded(declared=len(DATA)-1),encoded(data=b'IWi\x08'+DATA[4:]),b'\0'*4]
        for raw in invalid:
            with self.subTest(size=len(raw)):
                with self.assertRaises((ValueError,zlib.error)):resources.decode_iwi(raw,NAME,KEY)


if __name__=='__main__':unittest.main()
