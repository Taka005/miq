# Make it a Quote
## 使い方
- `pip install -r requirements.txt`を実行
- `python main.py`で起動
- `http://localhost:3000/`でアクセスする
## 任意の設定
- `main.py` の `branding` 変数で右下の文字を変更
- `main.py` の `BaseURL` 変数でヘルプドキュメントのURLを変更
## エンドポイント
- `/` (メイン) helpドキュメントを表示
- `/original` 元祖Make it a Quote画像
- `/colour` カラーアイコン
- `/reverse` アイコンの位置反転
## パラメーター
- name: 名前
- tag: 4桁のID
- id: ID
- content: 内容
- icon: アイコン
## イメージ一覧
## オリジナル
![画像](https://cdn.mikn.dev/miaq-original.png)
## カラー
![画像](https://cdn.mikn.dev/miaq-colour.png)
## 反転
![画像](https://cdn.mikn.dev/miaq-reverse.png)
## 公開API
https://miq-api.mikanbot.com
