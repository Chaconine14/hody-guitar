#!/usr/bin/env python3
"""HODY product data sanity checks; stdlib only."""
import json
from pathlib import Path
root = Path(__file__).resolve().parent.parent
catalog = json.loads((root/'data/products.json').read_text(encoding='utf-8'))
products = catalog['products']

def price_band_ok(price, band):
    if not band:
        return True
    if price is None:
        return False
    if band == 'lt150000': return price < 150000
    if band == '150000_299999': return 150000 <= price < 300000
    if band == '300000_499999': return 300000 <= price < 500000
    if band == 'gte500000': return price >= 500000
    raise ValueError(f'Unknown price band: {band}')

def matches(p, f):
    if not price_band_ok(p['price_yen'], f.get('price_band')): return False
    if f.get('body_size') and p['body_size'] != f['body_size']: return False
    style = f.get('playing_style')
    if style == 'どちらも' and not {'ストローク','指弾き'}.issubset(p['playing_styles']): return False
    if style and style != 'どちらも' and style not in p['playing_styles']: return False
    if f.get('tone_impression') and f['tone_impression'] not in p['tone_impressions']: return False
    amp = f.get('amp_connection')
    if amp == 'yes' and p['amp_connection'] is not True:return False
    if amp == 'no' and p['amp_connection'] is not False:return False
    return True

if __name__ == '__main__':
    assert len(products) == 12, f'12 products expected, got {len(products)}'
    ids=[p['id'] for p in products]
    assert len(set(ids)) == 12, 'Duplicate product IDs'
    assert len({(p['brand'],p['model']) for p in products}) == 12, 'Duplicate brand/model'
    for p in products:
        assert p['price_yen'] is None or (isinstance(p['price_yen'],int) and p['price_yen']>0)
        assert p['body_size'] in {'小さめ','標準','大きめ'}
        assert p['amp_connection'] in {None,True,False}
        assert set(p['playing_styles']).issubset({'ストローク','指弾き'})
        assert set(p['tone_impressions']).issubset({'明るい','力強い','バランス'})
        assert p['source_url'].startswith('https://')
        if p['image_src'] is not None: assert p['image_src'].startswith('assets/')
    cases=json.loads((root/'data/test_scenarios.json').read_text(encoding='utf-8'))
    for case in cases['scenarios']:
        actual=[p['id'] for p in products if matches(p,case['filters'])]
        assert actual==case['expected_ids'], f"{case['name']}: {actual} != {case['expected_ids']}"
        print(f"PASS: {case['name']} => {len(actual)} 件")
    print(f"OK: {len(products)} product records / {len(cases['scenarios'])} scenarios")
