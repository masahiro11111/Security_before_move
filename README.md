# 東京都 地域安全ダッシュボード

引越し前に確認できる治安・人口指標を可視化するWebアプリです。

**データ出典（すべて政府公式）**
- 犯罪データ：警視庁「東京の犯罪」「犯罪発生情報（年計）」
- 外国人人口：東京都統計局「外国人人口」
- 子供・人口：東京都統計局「住民基本台帳による東京都の世帯と人口」

---

## ローカルで起動する

```bash
# 1. リポジトリをクローン
git clone https://github.com/YOUR_USER/tokyo-safety.git
cd tokyo-safety

# 2. 仮想環境を作成（推奨）
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. パッケージをインストール
pip install -r requirements.txt

# 4. 初回データ生成
python scraper.py

# 5. 起動
python app.py
# → http://localhost:5000 でアクセス
```

---

## Render にデプロイする（無料）

1. [render.com](https://render.com) でアカウント作成
2. **New → Web Service** → GitHubリポジトリを接続
3. 設定：
   | 項目 | 値 |
   |------|-----|
   | Build Command | `pip install -r requirements.txt && python scraper.py` |
   | Start Command | `gunicorn app:app --bind 0.0.0.0:$PORT` |
   | Python Version | 3.11 |
4. **Deploy** をクリック

---

## Railway にデプロイする（無料枠あり）

1. [railway.app](https://railway.app) でアカウント作成
2. **New Project → Deploy from GitHub repo**
3. 環境変数 `PORT=8080` を設定（自動認識される場合は不要）
4. `Procfile` が自動的に読み込まれて起動します

---

## データの自動更新（GitHub Actions）

`.github/workflows/update_data.yml` により、**毎月1日に自動でデータを再取得**してコミットします。

### Render の自動再デプロイを有効にする場合

1. Render のサービスページ → **Settings → Deploy Hook** からURLをコピー
2. GitHubリポジトリの **Settings → Secrets → Actions** に
   `RENDER_DEPLOY_HOOK` という名前で貼り付ける
3. 以降、データ更新後に自動でサーバーが最新版に更新されます

---

## ファイル構成

```
tokyo-safety/
├── app.py              # Flask アプリ本体
├── scraper.py          # データ取得モジュール
├── requirements.txt
├── Procfile            # Render/Railway 用
├── data/
│   └── tokyo_safety.json   # 生成されるデータファイル
├── templates/
│   └── index.html      # ダッシュボード HTML
├── static/
│   ├── css/style.css
│   └── js/dashboard.js
└── .github/
    └── workflows/
        └── update_data.yml  # 自動更新ワークフロー
```

---

## API エンドポイント

| エンドポイント | メソッド | 説明 |
|---|---|---|
| `/` | GET | ダッシュボード画面 |
| `/api/data` | GET | 全データ JSON |
| `/api/ward/<区名>` | GET | 特定区のデータ |
| `/api/refresh` | POST | データを手動再取得 |
| `/health` | GET | ヘルスチェック |

---

## CSVで手動更新する方法

警視庁・東京都統計局からCSVをダウンロードして `data/` に置いた場合、
`scraper.py` の `STATIC_*` 定数を更新するか、CSVパスを `CRIME_CSV_URL` から
ローカルパスに変更してください。
