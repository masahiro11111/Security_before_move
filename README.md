# 東京都 地域安全ダッシュボード

🔗 **公開URL** → `https://YOUR_USERNAME.github.io/Security_before_move/`

引越し前に確認できる治安・人口指標を可視化する静的Webサイトです。  
Flask不要・サーバー不要・**GitHub Pages で完全無料公開**。

**データ出典（すべて政府公式）**
- 犯罪データ：警視庁「東京の犯罪」「犯罪発生情報（年計）」
- 外国人人口：東京都統計局「外国人人口」
- 子供・人口：東京都統計局「住民基本台帳」

---

## ファイル構成

```
/
├── index.html              ← ダッシュボード本体（これだけでサイトが動く）
├── data/
│   └── tokyo_safety.json   ← 表示データ（GitHub Actionsが毎月更新）
├── update_data.py          ← データ更新スクリプト（標準ライブラリのみ）
└── .github/workflows/
    └── update_data.yml     ← 毎月1日に自動実行
```

---

## GitHub Pages の有効化手順

1. リポジトリの **Settings** タブ
2. 左メニュー **Pages**
3. **Source → Deploy from a branch**
4. **Branch → main**、**/ (root)** を選択 → **Save**
5. 数分後に `https://USERNAME.github.io/REPO_NAME/` で公開される

---

## GitHub Actions の権限設定

自動更新ワークフローがコミットを書き込めるようにします。

1. **Settings → Actions → General**
2. **Workflow permissions → Read and write permissions** を選択
3. **Save**

---

## データの自動更新

`.github/workflows/update_data.yml` により **毎月1日 午前3時（JST）** に自動実行されます。

- `update_data.py` が警視庁CSVを取得 → `data/tokyo_safety.json` を更新
- 変更があれば自動コミット
- GitHub Pages がそのまま最新データを配信

手動で今すぐ更新したい場合：  
**Actions タブ → 「データ自動更新」→ Run workflow**
