"""
東京都 地域安全ダッシュボード — Flask アプリ
起動: python app.py  または  gunicorn app:app
"""

import json
import logging
from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify, render_template, abort

log = logging.getLogger(__name__)
app = Flask(__name__)

DATA_FILE = Path(__file__).parent / "data" / "tokyo_safety.json"


def load_data() -> dict:
    """JSONデータを読み込む。なければその場で生成する。"""
    if not DATA_FILE.exists():
        log.info("データファイルが見つかりません。初回生成します。")
        from scraper import run_all
        return run_all()
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


# ─── ルート ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    """フロントエンド向け全データ JSON。"""
    try:
        return jsonify(load_data())
    except Exception as e:
        log.error("データ読み込みエラー: %s", e)
        abort(500)


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """手動でデータを再取得するエンドポイント。
    本番では Basic Auth 等で保護してください。
    """
    try:
        from scraper import run_all
        data = run_all()
        return jsonify({"status": "ok", "updated_at": data["updated_at"]})
    except Exception as e:
        log.error("更新エラー: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/ward/<ward_name>")
def api_ward(ward_name: str):
    """特定の区市町村のデータを返す。"""
    data = load_data()
    ward = next((w for w in data["wards"] if w["name"] == ward_name), None)
    if not ward:
        abort(404)
    return jsonify(ward)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


# ─── 起動 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
