"""本地商品交易规则；装备永久授权，消耗品数量持久化。"""
from codol_rebuild.application.accounts.policy import validate_initialization


def permanent_purchase(state, offer, quantity=1):
    """返回独立的新状态；不写存储、不访问原生客户端。"""
    validate_initialization(state)
    if type(quantity) is not int or quantity != 1:
        raise ValueError('本地购买每次仅支持一份商品')
    contents = offer.get('contents', [{'item_id': offer.get('item_id'),
                                      'stackable': False, 'count': 1}])
    if not isinstance(contents, list) or not contents or offer.get('available') is not True:
        raise ValueError('商品内容无效或不可购买')
    if 'contents' not in offer and offer.get('equipment') is not True:
        raise ValueError('该商品不支持本地装备购买')
    currency, price = offer.get('currency'), offer.get('price')
    if currency not in ('gp', 'cp') or type(price) is not int or not 0 < price <= 2147483647:
        raise ValueError('商品币种或价格无效')
    owned = set(state['owned_ids'])
    quantities = dict(state.get('quantities', {}))
    changed = False
    for content in contents:
        item, count, stackable = content.get('item_id'), content.get('count'), content.get('stackable')
        if type(item) is not int or not 0 < item < 65535 or item in (15400, 20000):
            raise ValueError('无效的物品')
        if type(count) is not int or not 1 <= count <= 2147483647 or type(stackable) is not bool:
            raise ValueError('商品物品数量或类型无效')
        if stackable:
            total = quantities.get(str(item), 1 if item in owned else 0) + count
            if total > 2147483647:
                raise ValueError('物品数量超出上限')
            quantities[str(item)] = total
            changed = True
        elif item not in owned:
            changed = True
        owned.add(item)
    if not changed:
        raise ValueError('已永久拥有该商品的全部装备')
    if state[currency] < price:
        raise ValueError('余额不足')
    result = {
        **state, currency: state[currency] - price,
        'owned_ids': sorted(owned),
    }
    if quantities:
        result['quantities'] = quantities
    return validate_initialization(result)
