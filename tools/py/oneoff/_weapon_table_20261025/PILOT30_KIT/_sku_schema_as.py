# -*- coding: utf-8 -*-
"""★★ 权威 schema: 客户端 SKU 对象的 ActionScript 字段偏移表。

来源: 运行中的客户端内存转储
      REF_LOBBY_KIT\mem_marketplace\hit_marketplace_0x035B29F4.bin @0xCB124

原文(可读字符串):

    name.String.pos.130.id.int.156.promoSkuId.177.cp.206.cc.238.duration.
    269.stackable.Boolean.296.productId.329.requirementLevel.357.
    requirementPrestige.392.requirementUnlockFlag.430.purchasable.474.
    originalPrice.516.price.548.currency.572.couponEnable.602.
    ignoreEntitlement.637.indexInProduct.uint.678.ignoreDiscount.713
    codo.objects.SKUObj.CustomObject

这串是 Scaleform AS3 的 **CustomObject 字段定义表**: `字段名.类型.pos(N)`,
其中 `pos` 是字段在对象里的槽位号(不是字节偏移)。

★ 意义: 这是我们缺的"客户端到底按什么格式读 SKU"的**权威答案**。
  之前用 exe 内嵌的 marketplace-catalog.json 只是启动器那份, 字段对不上;
  这里才是客户端真正认的字段集合与顺序。

字段表(按 pos 升序):
"""

SKU_AS_FIELDS = [
    # (name, type, pos)
    ("name", "String", 130),
    ("id", "int", 156),
    ("promoSkuId", None, 177),
    ("cp", None, 206),
    ("cc", None, 238),
    ("duration", None, 269),
    ("stackable", "Boolean", 296),
    ("productId", None, 329),
    ("requirementLevel", None, 357),
    ("requirementPrestige", None, 392),
    ("requirementUnlockFlag", None, 430),
    ("purchasable", None, 474),
    ("originalPrice", None, 516),
    ("price", None, 548),
    ("currency", None, 572),
    ("couponEnable", None, 602),
    ("ignoreEntitlement", None, 637),
    ("indexInProduct", "uint", 678),
    ("ignoreDiscount", None, 713),
]

# 由同一转储得到的其它关键关系:
#   @0xA032F  MarketplacePriceSelector 里: itemData -> skus / promoSkus / sortedSkus
#             -> skuData(每条含 skuIdx / rowIsChecked / type / bnd / sdb)
#   @0xA053C  isUsingNewDiscountSystem / mHasHPEHP / indexInProduct
#             currency 取值: CP / GP / EHP / HP   (★ 比 catalog 的 1/2 多两种)
MARKET_RELATIONS = {
    "itemData.skus": "商品下的 SKU 列表",
    "itemData.promoSkus": "促销 SKU",
    "itemData.sortedSkus": "排序后的 SKU",
    "sku.promoSkus": "SKU 自己的促销项",
    "currencies": ["CP", "GP", "EHP", "HP"],
}


def dump():
    print("SKU 对象字段(按 pos):")
    for name, typ, pos in SKU_AS_FIELDS:
        print("  pos=%-4d %-22s %s" % (pos, name, typ or ""))


if __name__ == "__main__":
    dump()
