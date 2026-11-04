# 画像配置一覧（2026-11-04）

ユーザーが提供したファイルの元のファイル名を保持して `assets/images/` に格納しています。20点すべてを HTML から参照しています。

| 添付画像 | 使用位置 | 表示仕様 |
| --- | --- | --- |
| `top_slider01.jpg` | FVスライド1 | PC/SP共通・`object-fit: cover` |
| `top_slider02.jpg` | FVスライド2 | PC/SP共通 |
| `top_slider03.jpg` | FVスライド3 | PC/SP共通 |
| `top_slider04.jpg` | FVスライド4 | PC/SP共通 |
| `guitar-outline.png` | おすすめギター診断 | PC/SPの寸法だけ切り替え |
| `guitar-icon.png` | 固定試奏予約CTA | ボタン内に表示 |
| `guitar01.jpg` | 商品 Gibson J-45 | PC/SP共通 |
| `guitar02.jpg` | 商品 Martin D-28 | PC/SP共通 |
| `guitar03.jpg` | SP商品カード3 Taylor 114ce | SPのみ |
| `guitar04.jpg` | SP商品カード4 Taylor 114ce | SPのみ、Figma表記を維持 |
| `about.jpg` | ABOUT | PC/SP共通 |
| `staff011.jpg` | 飯塚 健（STORE MANAGER） | PC/SP共通 |
| `staff02.jpg` | 佐藤 芽衣（GUITAR ADVISER） | PC/SP共通 |
| `guide.jpg` | TEST-PLAYING GUIDE | PCは右側画像、SPは背景画像 |
| `instagram01.jpg` | Instagram 1枚目 | PCの繰り返しカードにも使用 |
| `instagram02.jpg` | Instagram 2枚目 | PCの繰り返しカードにも使用 |
| `instagram04.jpg` | Instagram 3枚目 | カンプの画像順に合わせて配置 |
| `instagram03.jpg` | Instagram 4枚目 | カンプの画像順に合わせて配置 |
| `footer_shop-pc.jpg` | フッター店舗外観 PC | PC・タブレット |
| `footer_shop-sp.jpg` | フッター店舗外観 SP | 768px以下 |

**今回提供されていない素材：** 店舗情報の地図（PC/SPの画像）。そのため `index.html` の地図部分のみ、既存の画像参照を残しています。

**FVの挙動：** 画像は 01→02→03→04→01 の順に切り替わります。現在の切り替え間隔（6秒）は実装上の仮値です。
