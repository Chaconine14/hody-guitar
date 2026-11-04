# 商品一覧ページ 実装・検証記録

2026-11-04。承認済み「商品一覧ページ実装計画・画像更新反映版」を実装しました。実装・ブラウザ検証は完了しています。**商品マスターの仮価格・紹介文・検索分類の正式承認が残るため、公開準備完了とは判定しません。**

## 表示と動作

- `selection.html` に更新済みJSONから12商品を重複なく表示。商品IDと `image_src` の対応をPC・SPで共通にしています。
- 5条件のAND検索。選択中の値と適用済み条件を分け、検索ボタンでのみ結果を変更します。リセットは直ちに全件・初期状態へ戻します。
- 初期は `PRODUCTS / 12 ITEMS`、検索後は「検索結果 / 実件数」。0件時も予約案内・店舗写真・フッターを維持します。
- SP検索パネルは初期展開、検索後収納、リセット後展開。開閉とPC/SPの幅変更で入力・結果を保持します。
- HTTP失敗・不正JSONは0件と区別し、結果領域に取得失敗を表示。検索を無効化します。取得前・失敗時の予約選択肢は「未定」だけとし、不完全な商品選択肢を残しません。
- 動的な予約ボタンはイベント委譲で受け取り、選択した `display_name` を既存ダイアログへ渡します。商品一覧だけ「未定＋12機種」、TOP・ガイドの既存4選択肢は維持しています。
- 予約の送信API・確認画面、診断、並べ替え、ページネーションは追加していません。

## 素材・フォント・レイアウトの判断

商品画像は全12ファイルが存在し、画像として正常に読み込めることを確認しました。追加9商品の `image_status` だけをCSV／JSON双方で `PROVIDED_LOCAL_IMAGE` に更新しています。ID・商品名・価格・紹介文・検索属性・表示順・画像パス・テスト期待値は変更していません。

写真はカンプの `1122 / 1402` 比率の枠を確保し、`object-fit: contain` と中央配置で全体を保持します。追加画像は縦長などの構図があるため、余白が異なります。画像を拡大してヘッドやボディを切る処理はしていません。画像対応は [ASSET_MAPPING.md](../ASSET_MAPPING.md)、確認用一覧は [product-images.png](../artifacts/selection/product-images.png) に記録しています。

ロゴ、予約アイコン・矢印、PC／SP店舗写真はFigma素材と既存ガイド素材を照合して再利用しました。SPロゴはレイヤーIDだけが異なり、パス・色・寸法が一致します。メニュー・フッター罫線も形状・色・寸法を照合済みです。商品カード矢印、セレクト矢印、開閉三角、検索条件の罫線、0件シルエットはFigma正式素材を新規配置しました。0件シルエットは既存の診断用素材と異なるため流用していません。照合記録は [asset-comparison.json](../artifacts/selection/asset-comparison.json) に保存しています。

Figmaレイヤーは `Source Sans 3` 指定です。和文のフォールバックは明示されていないため、既存ガイドと同じNoto Sans JPを商品一覧専用の別名 `HODY Selection JP` で読み込みました。400／500／700の使用文字をローカル配信し、既存TOP・ガイドのフォント設定には波及させていません。共通メニュー・予約ダイアログは既存の和文フォールバックを保持しています。Chromeの描画フォント情報から欧文Source Sans 3・和文Noto Sans JPの実使用を確認し、[fonts.json](../artifacts/selection/fonts.json) に保存しました。

PC1440pxは左267pxの検索パネル＋右790pxの3列カード、SP375pxは343pxのパネル・写真と1列カードです。カンプ未提示の中間幅は、承認済みの768px境界を使用し、769〜1200pxはカード2列で重なりを防ぐ補完をしています。適用条件はPCとSPで位置が異なるため、表示枠を2箇所に設け、同じ適用済み状態から描画し、CSSで片方だけ表示します。フォーム・商品カードのDOMは共有です。

共通化はガイドの既存数値を維持したまま、下層ヘッダー／フッターをlayout、下部予約案内をcomponentへ移しました。ガイドの旧クラスも同じ宣言を使い、マークアップは維持しています。

## 6状態の画像・Figmaとの差分

[6画面の比較ページ](../artifacts/selection/comparison.html) には、原寸のFigma画像・実装画像と、並列表示を保存しています。

| 状態 | PC1440px | SP375px |
| --- | --- | --- |
| 初期・12実商品 | [PC初期](../artifacts/selection/pc-initial.png) | [SP初期](../artifacts/selection/sp-initial.png) |
| 検索後・小さめ6件 | [PC結果あり](../artifacts/selection/pc-results.png) | [SP結果あり](../artifacts/selection/sp-results.png) |
| 小さめ＋力強い・0件 | [PC0件](../artifacts/selection/pc-empty.png) | [SP0件](../artifacts/selection/sp-empty.png) |

カンプの114ce繰り返し、PCのD-28欄に配置されたTaylor写真、`000,000円`、例示4件、初期PCの空白行は固定せず、承認済み方針どおり実データを優先しています。このため商品内容・写真・カード高さ・総ページ高が異なります。PCの検索後もプルダウンに選択済みの条件を保持し、カンプの「すべて」に戻っている表示は再現しません。

0件画面では主要な位置・高さをカンプに合わせています。PCはヘッダー93px、導入155px、条件191px、検索領域842px、予約案内335px、店舗写真506px、フッター547pxで、総高2669pxです。SPはヘッダー81px、導入開始139px、条件枠y254／高さ216px、予約案内開始y992／高さ415px、店舗写真開始y1467です。SPのフッター開始などに約1pxの差と、ブラウザ／Figmaの文字描画の微差が残ります。

## 検証結果

[機械検証結果](../artifacts/selection/verification.json) と比較画像を保存しました。macOS上のChrome／Playwright、画像比較にPillowを使用しています。

| 検証 | 結果 |
| --- | --- |
| 既存8シナリオ | 全件成功。ブラウザPC／SP双方と `scripts/check_data.py` で期待ID・順序を確認 |
| 全12機種の画像 | PC／SPと追加4幅で読み込み・ID対応・同じパス・containを確認 |
| 全12機種の検索・予約 | PC／SP双方で各商品の属性を検索し、商品カードから正しい名称を引き継ぎ |
| 価格境界 | 149999／150000／299999／300000／499999／500000と未設定を実際のJS検索モジュールで確認 |
| 配列・未確認属性 | 「どちらも」の両タグ一致、アンプtrue／falseとnullの区別を8シナリオで確認 |
| 状態保持・リセット | 未適用の編集値、開閉・幅変更での保持、リセット直後の全件表示を確認 |
| 取得失敗 | HTTP503／不正JSONで失敗文言・検索無効・0件との区別を確認 |
| レスポンシブ | 320／768／769／1024pxで全件・結果あり・0件・リセット・横はみ出しを確認 |
| キーボード・モーダル | SPパネルのEnter／Space、予約フォーカストラップ、Esc／閉じる／PC背景、フォーカス復帰、入力検証、SPメニューからの予約を確認 |
| TOP／ガイド回帰 | PC／SPの変更前後画像とダイアログを比較。ページ平均色差の最大値0.0231未満（0〜255、許容0.1）。ダイアログは画素一致、タイトル描画フォントも一致 |
| 既存機能 | TOPスライダーの自動切替とアクティブ数、ガイドFAQの初期展開・複数開閉、既存予約選択肢を確認 |
| データ差分 | CSV／JSONは9件の画像ステータス以外の変更なし、シナリオファイルはバイト一致 |

再実行はHTTPサーバーとPlaywright／Pillowを利用できるPython環境で行います。検証用依存は本体に追加していません。

```bash
python3 scripts/build-css.py
python3 scripts/check_data.py
python3 scripts/verify-selection.py --base-url http://localhost:8000
# 変更前ファイルを配置したミラーがある場合のみ、画像回帰比較も実行
python3 scripts/verify-selection.py --base-url http://localhost:8000 --baseline-dir /path/to/snapshot
```

今回の変更前ミラーは `/private/tmp/hody-selection-baseline/` に保持しています。ミラーがない環境でも、保存済みbefore／after画像と検証JSONから結果を参照できます。

## 変更ファイルと理由

| ファイル | 変更理由 |
| --- | --- |
| `selection.html` | 商品一覧、検索、0件、共通予約導線・メニュー・ダイアログ |
| `js/selection.js` | JSON取得、DOM描画、条件の状態管理、SP開閉、予約選択肢 |
| `js/selection-search.js` | 表示から独立したAND検索・価格範囲判定 |
| `js/reservation.js` | 動的商品カードにも対応するイベント委譲。既存の開閉・検証は維持 |
| `scss/object/project/_selection-page.scss` | 商品一覧専用の字体・カンプ寸法・レスポンシブ |
| `scss/object/component/_trial-invite.scss` | ガイドと商品一覧が共有する下部予約案内 |
| `scss/layout/_header.scss` / `_footer.scss` | ガイドの既存下層スタイルを移動し、新ページでも再利用 |
| `scss/object/project/_guide-page.scss` | 共通化した宣言を移動し、ガイド固有部分を維持 |
| `scss/style.scss` / `scripts/build-css.py` / `css/style.css` | 新partialの読み込みと生成済みCSS |
| `index.html` / `guide.html` | 商品一覧へのリンク先のみ接続 |
| `data/products.csv` / `data/products.json` | 追加9点の画像ステータスだけ更新 |
| `assets/images/selection/` 内6点 | Figma正式素材のローカル保存 |
| `assets/fonts/selection-noto-jp-{400,500,700}.ttf` | 商品一覧に必要な日本語の明示的な読み込み |
| `scripts/verify-selection.py` | 検索・画像・予約・各幅・回帰のブラウザ検証 |
| `README.md` / `ASSET_MAPPING.md` / `IMPLEMENTATION_NOTES.md` | 表示方法、素材対応、実装状態の記録 |
| `docs/SEARCH_SPEC.md` / `docs/REVIEW_REQUIRED.md` / 本書 | 元資料と承認済み仕様の相違、公開前確認事項、検証記録 |
| `artifacts/selection/` | 6状態・Figma比較・画像対応・回帰比較・検証JSON |

ユーザーが追加済みの商品写真や `.DS_Store`、`test_scenarios.json`、元の依頼文 `docs/CODEX_REQUEST.md` は変更していません。

## 公開前に残る事項

画像不足はありません。仮価格12件、紹介文、編集上の検索分類、J-45／B-25／GS Miniなどの販売個体のアンプ接続仕様は正式確認が必要です。現在のマスター値・レビュー状態を維持しています。予約確認画面・送信処理は依頼範囲外で、既存と同じく入力検証までです。
