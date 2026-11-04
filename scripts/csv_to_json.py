#!/usr/bin/env python3
"""Update `products` in JSON from the editable CSV without changing filter choices."""
import csv
import json
from pathlib import Path
root = Path(__file__).resolve().parent.parent
src = root/'data/products.csv'
dst = root/'data/products.json'
base=json.loads(dst.read_text(encoding='utf-8'))
products=[]
with src.open(encoding='utf-8-sig', newline='') as fp:
    for n,r in enumerate(csv.DictReader(fp),start=2):
        if not r['id'] or not r['brand'] or not r['model']:
            raise ValueError(f'CSV {n}行: id / brand / model が不足')
        price=(r['price_yen'] or '').strip().replace(',','')
        if price and (not price.isdigit() or int(price)<1):
            raise ValueError(f'CSV {n}行: price_yenは正の整数か空欄')
        a=(r['amp_connection'] or '').strip()
        if a in ('あり','true','TRUE','True'):amp=True
        elif a in ('なし','false','FALSE','False'):amp=False
        elif a in ('要確認','', 'null','NULL'):amp=None
        else:raise ValueError(f'CSV {n}行: amp_connectionの値が不正: {a}')
        p={key:r[key] for key in ('id','brand','model','display_name','site_role','tagline','description','price_status','body_size','body_shape_reference','image_expected_path','image_status','source_url','verification_note','review_status')}
        p['price_yen']=int(price) if price else None
        p['image_src']=(r['image_src'] or '').strip() or None
        p['playing_styles']=[x.strip() for x in r['playing_styles'].split('|') if x.strip()]
        p['tone_impressions']=[x.strip() for x in r['tone_impressions'].split('|') if x.strip()]
        p['amp_connection']=amp
        p['sort_order']=int(r['sort_order'])
        products.append(p)
if len({p['id'] for p in products})!=len(products): raise ValueError('IDが重複しています')
base['products']=products
dst.write_text(json.dumps(base,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'更新完了: {dst} / {len(products)}件')
print('※ data/test_scenarios.json の期待結果は編集前のデモデータに基づいています。カテゴリや価格を変えた場合は再作成してください。')
