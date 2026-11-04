# GUITAR FINDER 実装・検証記録

2026-11-04。承認済みのインライン診断を実装しました。中断時点の質問設定・採点関数・画面切り替え・予約連携を保持し、残っていた表示補正・検証・記録を完了しました。

## 実装内容

TOPの開始ボタンから、同じGUITAR FINDER内を「Q1 → Q2 → Q3 → 結果」に切り替えます。診断用モーダル、オーバーレイ、Esc終了、フォーカストラップ、背景スクロール禁止はありません。通常のページスクロールで閲覧でき、他のTOPセクションは表示を維持します。

- PCの4択は2列×2段、3択は3列×1段、SPは1列。回答順は左上から自然な順序です。
- 結果はPC・SPとも商品2列。CTAはPCで再診断→予約の横並び、SPで予約→再診断の縦並び。
- 本文は通常のフロー配置とし、カンプの最低寸法を保ちながら、長い質問・タイプ名・説明に応じて高さが伸びます。切り替え境界は768pxです。
- Q2・Q3・結果に「前の質問へ」を追加。戻った回答は保持し、選び直せます。再診断は全回答を消してQ1へ戻ります。再読み込み時は導入に戻ります。
- 切り替え時に見出しへフォーカスし、セクション先頭へスクロール。動きの軽減設定時は即時移動し、進捗と結果をライブ領域でも通知します。
- 導入の予約バナーは診断開始後に非表示とし、カンプの質問・結果を妨げません。

## ロジック・設定の分離

`js/finder-config.js` が質問・選択肢・結果タイプの文言、`js/finder-logic.js` がDOM非依存の採点・推薦・タイプ判定、`js/finder.js` が取得と表示・操作を担当します。商品名・画像・属性は共通の `data/products.json` から読み込み、別の商品の一覧は作っていません。

`scoreProduct(product, answers)` は数値を返します。`recommendGuitars(products, answers)` は状態、タイプID、推薦商品と得点を返します。未回答の `null` と、未定回答の `any` を区別し、未回答では `incomplete` を返します。

| 質問 | 加点 |
| --- | --- |
| 音色 | `tone_impressions` 一致＋3、未定0 |
| サイズ | `body_size` 一致＋4、未定0 |
| 指定の弾き方 | `playing_styles` 一致＋2 |
| 弾き方が「どちらも好き・まだわからない」 | 両スタイル登録＋3、片方＋1 |

正のスコアを得た商品を得点降順、同点は `sort_order` 昇順で並べ、異なるIDの上位2件を表示します。全未定の場合だけ、標準サイズ・バランス音色・両スタイルの3条件を満たす商品を先に配置します。商品データは並べ替えや採点によって変更しません。

### 結果タイプ

次の順で、推薦商品すべてに当てはまる最初の条件を使用します。名称と説明は設定ファイルで編集できます。

| 優先順／ID | 表示名 | 条件 | 現マスターの48通りでの件数 |
| --- | --- | --- | ---: |
| 1 `compact` | コンパクトで抱えやすい | 全候補が小さめ | 12 |
| 2 `large` | 響き豊かなラージボディ | 全候補が大きめ | 17 |
| 3 `finger` | 指弾きを楽しむ | 指弾き回答、全候補に指弾きタグ | 7 |
| 4 `stroke` | ストロークを楽しむ | ストローク回答、全候補にストロークタグ | 5 |
| 5 `allround` | バランス型オールラウンダー | 全候補がバランス音色・両スタイル対応 | 6 |
| 6 `bright` | 明るい音を楽しむ | 全候補に明るい音色タグ | 1 |
| 7 `compare` | 弾き比べで見つける | 上記以外の候補 | 0（補完条件のテスト済み） |

マスターの `body_shape_reference` が混在する候補を「王道ドレッドノート」とまとめるなど、形状固有名の断定はしていません。タイプは承認済みの汎用名称と共通属性から判定します。

### 推薦例

| 回答 | 第一候補／得点 | 第二候補／得点 | タイプ |
| --- | --- | --- | --- |
| 明るい／小さめ／指弾き | Gibson B-25／9 | Taylor GS Mini／9 | コンパクトで抱えやすい |
| 力強い／大きめ／ストローク | Gibson J-45／9 | Martin D-28／9 | 響き豊かなラージボディ |
| すべて未定 | Taylor 114ce／3 | Taylor 214ce／3 | バランス型オールラウンダー |

## 予約・例外処理

診断の予約ボタンは `hody:finder-reservation` イベントで、マスター由来の商品IDを含む推薦商品と復帰先ボタンを既存予約JSへ渡します。開いている間だけ選択肢を「未定＋推薦候補」にし、第一候補を選択します。第二候補へ変更できます。選択肢には `data-product-id` を保持し、既存フォームの値は従来どおり商品名です。

予約を閉じると元の選択肢・選択値を復元し、結果の予約ボタンへフォーカスを戻します。診断結果と他の入力項目は保持します。通常のTOP予約は既存4選択肢、商品一覧は13選択肢、ガイドは既存4選択肢を維持しています。

商品取得は初回開始時に行い、成功したデータを同じページ内で再利用します。取得中・HTTP失敗・不正JSON・候補なしを分け、失敗時に架空の商品を表示しません。候補0件では予約を無効にし、1件なら1枚だけ表示します。失敗後の再診断で取得を再試行します。遅延応答が戻っても、戻る操作で表示中の質問を上書きしません。

画像未設定・読み込み失敗時は4:5の枠を保ち、「画像を表示できません」を表示します。名前と推薦順位を維持し、他機種の写真は流用しません。

## 素材・Figma比較

欧文は既存のSource Sans 3、和文はGoogle FontsのNoto Sans JPの使用文字を400／500／700でローカル配信しています。別名 `HODY Finder JP` として診断内だけに適用し、他のTOPセクションと既存予約画面には波及させていません。[実描画フォントの記録](../artifacts/finder/fonts-and-extra-checks.json) で確認できます。

導入シルエット・PC予約アイコン・結果の明色矢印・SP結果罫線をFigma原本から保存しました。既存画像の低解像度版との差を避けるため、導入だけ原本PNGを使用しています。SP予約アイコン・バナー矢印・再診断矢印は、Figma原本とファイル一致したガイド素材を再利用しています。[素材照合](../artifacts/finder/assets.json) に寸法と参照先を記録しました。

| 画面 | PC1440px | SP375px |
| --- | --- | --- |
| 導入 | [PC導入](../artifacts/finder/pc-intro.png) | [SP導入](../artifacts/finder/sp-intro.png) |
| Q1・4択 | [PC Q1](../artifacts/finder/pc-q1.png) | [SP Q1](../artifacts/finder/sp-q1.png) |
| Q2・4択 | [PC Q2](../artifacts/finder/pc-q2.png) | [SP Q2](../artifacts/finder/sp-q2.png) |
| Q3・3択 | [PC Q3](../artifacts/finder/pc-q3.png) | [SP Q3](../artifacts/finder/sp-q3.png) |
| 大きめの結果 | [PC結果](../artifacts/finder/pc-result.png) | [SP結果](../artifacts/finder/sp-result.png) |
| コンパクトの結果 | [PC結果](../artifacts/finder/pc-result-compact.png) | [SP結果](../artifacts/finder/sp-result-compact.png) |
| 全未定の結果 | [PC結果](../artifacts/finder/pc-result-allround.png) | [SP結果](../artifacts/finder/sp-result-allround.png) |

[6画面のFigma比較ページ](../artifacts/finder/comparison.html) に原寸Figma画像・並列比較を保存しています。導入はPC676px／SP619px、Q3はPC697px／SP619pxのセクション高を再現しています。

カンプとの差分は、承認済みの「前の質問へ」、Q1・Q2の4択配置、共通特性に基づくタイプ名・説明文、マスターどおりの商品画像・ブランド・モデル表記です。カンプのYamaha欄に重複したD-28写真や「LL-16」表記は固定していません。説明の長さが異なるため、SP結果はカンプより短くなります。文字の描画や小数座標には約1pxの差が残ります。

## テスト結果

すべて成功しています。[診断検証JSON](../artifacts/finder/verification.json)、[最終6幅確認](../artifacts/finder/final-layout.json)、[商品一覧の回帰結果](../artifacts/finder/selection-regression/verification.json)、[ガイドの回帰結果](../artifacts/finder/guide-regression/verification.json) を保存しました。

| 検証 | 結果 |
| --- | --- |
| 48通りの判定 | 手計算の期待順位表と一致。商品入力順を逆転しても結果一致、元データの変更なし |
| 採点単体 | 0／音色3／サイズ4／スタイル2／未定片方1／未定両方3、最大10を確認 |
| UIの48通り | PC・SP双方で全48通りを操作し、順位・タイプ・名前・画像対応が一致 |
| 戻る・再診断・キーボード | 回答保持と変更、全リセット、Enter／Space、見出しフォーカス、診断中にページがロックされないことを確認 |
| 予約連携 | 第一候補・第二候補のIDと名称、選択変更、元選択肢と値の復元、他入力の保持、結果ボタンへの復帰を確認 |
| 6画面幅 | 1440／375／320／768／769／1024pxで導入・3問・結果、2列カード、4択・3択の配置、はみ出しを確認 |
| 例外 | HTTP503と再試行、不正JSON、候補0／1件、画像未設定／404、長い名称・説明、遅延応答後の戻る操作を確認 |
| TOPの外観回帰 | 診断以外の8領域と通常予約をPC／SPで比較。寸法・字体指定・色・画像参照が一致 |
| 写真描画の微差 | Chromeのコンテキスト間で再サンプリング差が出るため、画像以外は0.1、写真を含む平均色差は1を閾値に使用（0〜255）。今回最大0.18未満。通常予約は画素一致 |
| 商品一覧 | 8シナリオ、12商品、検索・リセット・予約・例外・指定幅を既存スクリプトで確認 |
| ガイド | FAQ、予約、入力検証、メニュー、指定幅を既存スクリプトで確認 |
| スライダー | 既存検証で自動切替とアクティブな画像／バーが各1件であることを確認 |
| 変更範囲 | 商品JSON／CSV、既存シナリオ、商品一覧・ガイドHTML、メニュー・スライダーJSは変更前とバイト一致 |

検証用Python環境にPlaywrightとPillowが必要です。本体のライブラリは追加していません。

```bash
python3 -m http.server 8767
python3 scripts/build-css.py
python3 scripts/check_data.py
python3 scripts/verify-finder.py --base-url http://localhost:8767
python3 scripts/verify-selection.py --base-url http://localhost:8767 --output artifacts/finder/selection-regression
python3 scripts/verify-guide.py --base-url http://localhost:8767/ --output artifacts/finder/guide-regression
```

TOP画像回帰は `verify-finder.py --baseline-dir /private/tmp/hody-finder-baseline` で実行しました。この一時ミラーがない環境でも、保存済みの変更前後画像と検証JSONを確認できます。

## 変更・追加ファイル

| ファイル | 内容 |
| --- | --- |
| `index.html` | 開始ボタン、診断フック、導入のフロー配置、正式素材参照、診断JS読み込み |
| `js/finder-config.js` | 3問・11選択肢と7タイプの文言設定 |
| `js/finder-logic.js` | 採点・安定した推薦・共通特性のタイプ判定 |
| `js/finder.js` | インライン画面、取得と例外、フォーカス・スクロール、予約受け渡し |
| `js/reservation.js` | 診断からの受け取り、一時的な候補と元の選択肢の復元 |
| `scss/object/project/_finder.scss` / `css/style.css` | 可変高さ、各状態の配置、指定幅、専用フォント。生成CSSを更新 |
| `assets/images/finder/` 内4点 | Figmaの導入PNG・PC予約アイコン・結果明色矢印・SP罫線 |
| `assets/fonts/finder-noto-jp-{400,500,700}.ttf` | 診断専用Noto Sans JP。既存OFLライセンスを使用 |
| `scripts/verify-finder.py` | 48通り、UI、例外、予約、表示幅、TOP画像回帰の検証 |
| `README.md` / `ASSET_MAPPING.md` / `IMPLEMENTATION_NOTES.md` / 本書 | 使用方法、素材、実装状態、検証結果の記録 |
| `artifacts/finder/` | 原寸画面・Figma比較・素材・フォント・回帰画像・検証JSON |

## 未完了・確認事項

依頼された診断機能と検証に未完了事項はありません。商品属性の編集上の分類・仮情報の承認状態は引き続きマスターのまま維持しています。既存予約の確認画面・送信APIは今回の対象外で、従来どおり入力検証までです。
