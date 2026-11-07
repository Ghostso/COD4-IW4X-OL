# -*- coding: utf-8 -*-
"""80/70 SKU 页 —— 哨兵探针。

思路:
  客户端对每个值做**逐值类型检查**(codol_crypto.py:260-261 实证:
  该写 I32(0x07) 写成 U32(0x08) 会被拒)。所以 SKUObj 的每个字段
  类型标签必须精确。

  我们不知道精确序列, 就做"哨兵探针":
    - 每个字段填一个唯一常量(id=0x11111111, productId=0x22222222,
      price=0x44444444, currency=0x55, name="PROBE0")
    - 客户端解析成功 -> 这些值会进它构造的 SKUObj, 存活在内存里
    - 之后扫内存找哨兵: 命中 = 这条编码被接受

  开关 market-sku-probe.on + market-sku-probe.txt(变体号)。
  纯实验, 默认关; 一旦出错把开关删掉即可恢复空页。

变体:
  1  按 AS3 类型表全部字段(type-correct): id=i32, currency=u8,
     stackable/purchasable/...=bool, name=string, 其余 u32
  2  最小字段: name, id, productId, price, currency, purchasable
  3  无 name(有些条目可能不带名字)
  4  全 u32(上一版失败方案的复现, 作为对照)
"""
import os
import struct

import codol_crypto as cc

ROOT = os.path.dirname(os.path.abspath(__file__))
FLAG = os.path.join(ROOT, "market-sku-probe.on")
VARFILE = os.path.join(ROOT, "market-sku-probe.txt")
COUNTFILE = os.path.join(ROOT, "market-sku-probe-count.txt")

SENT_NAME = b"PROBE0"
SENT_ID = 0x11111111
SENT_PRODUCT = 0x22222222
SENT_ORIG = 0x33333333
SENT_PRICE = 0x44444444
SENT_CUR = 0x55


def probe_enabled():
    return os.path.exists(FLAG)


def variant():
    try:
        return int(open(VARFILE, encoding="ascii").read().strip())
    except Exception:
        return 1


def count():
    try:
        return max(1, min(16, int(open(COUNTFILE, encoding="ascii").read().strip())))
    except Exception:
        return 1


def _v1():
    """按 AS3 类型表: String/int/Boolean/uint 各用对应 tag。"""
    b = cc.Buf()
    b.string(SENT_NAME.decode())
    b.i32(SENT_ID)            # id: AS3 int
    b.u32(0)                  # promoSkuId
    b.u32(0)                  # cp
    b.u32(0)                  # cc
    b.u32(0)                  # duration
    b.bool_(False)            # stackable: Boolean
    b.u32(SENT_PRODUCT)       # productId
    b.i32(0)                  # requirementLevel
    b.i32(0)                  # requirementPrestige
    b.u32(0)                  # requirementUnlockFlag
    b.bool_(True)             # purchasable: Boolean
    b.u32(SENT_ORIG)          # originalPrice
    b.u32(SENT_PRICE)         # price
    b.u8(SENT_CUR)            # currency: 与余额对象一致用 u8
    b.bool_(False)            # couponEnable
    b.bool_(False)            # ignoreEntitlement
    b.u32(0)                  # indexInProduct: AS3 uint
    b.bool_(False)            # ignoreDiscount
    return b.data()


def _v2():
    b = cc.Buf()
    b.string(SENT_NAME.decode())
    b.i32(SENT_ID)
    b.u32(SENT_PRODUCT)
    b.u32(SENT_PRICE)
    b.u8(SENT_CUR)
    b.bool_(True)
    return b.data()


def _v3():
    b = cc.Buf()
    b.i32(SENT_ID)
    b.u32(SENT_PRODUCT)
    b.u32(SENT_PRICE)
    b.u8(SENT_CUR)
    b.bool_(True)
    return b.data()


def _v4():
    """全 u32(旧失败方案): 仅作对照。"""
    b = cc.Buf()
    b.string(SENT_NAME.decode())
    b.u32(SENT_ID)
    b.u32(0)
    b.u32(0)
    b.u32(0)
    b.u32(0)
    b.bool_(False)
    b.u32(SENT_PRODUCT)
    b.u32(0)
    b.u32(0)
    b.u32(0)
    b.bool_(True)
    b.u32(SENT_ORIG)
    b.u32(SENT_PRICE)
    b.u32(SENT_CUR)
    b.bool_(False)
    b.bool_(False)
    b.u32(0)
    b.bool_(False)
    return b.data()


BUILDERS = {1: _v1, 2: _v2, 3: _v3, 4: _v4}


def build_objects():
    """返回要作为 80/70 resultObjects 的对象列表。"""
    fn = BUILDERS.get(variant(), _v1)
    return [fn() for _ in range(count())]


if __name__ == "__main__":
    print("variant=%d count=%d" % (variant(), count()))
    for i, o in enumerate(build_objects()):
        print("object %d: %d bytes" % (i, len(o)))
        print("  ", o.hex(" "))
