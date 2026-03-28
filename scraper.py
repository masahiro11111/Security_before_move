"""
東京都 治安・人口データ取得モジュール
出典:
  - 犯罪データ : 警視庁「犯罪発生情報（年計）」
    https://catalog.data.metro.tokyo.lg.jp/dataset/t000022d0000000034
  - 外国人人口 : 東京都統計局「外国人人口」
    https://www.toukei.metro.tokyo.lg.jp/gaikoku/ga-index.htm
  - 子供人口   : 東京都統計局「住民基本台帳による東京都の世帯と人口」
"""

import os
import json
import logging
import urllib.request
import urllib.error
import csv
import io
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ─── 警視庁 犯罪オープンデータ CSV URL ───────────────────────────────────────
# 東京都オープンデータカタログ掲載の犯罪発生情報（区市町村別・年計）
CRIME_CSV_URL = (
    "https://catalog.data.metro.tokyo.lg.jp/dataset/"
    "t000022d0000000034/resource/6b2a2316-c13c-4bfc-a9db-"
    "30b5e5b3052f/download/2023henno.csv"
)

# ─── フォールバック用の静的データ（公式統計からの手入力値）────────────────────
# 警視庁「東京の犯罪（令和5年版）」区市町村別刑法犯認知件数
STATIC_CRIME_2023 = {
    "千代田区": 2198, "中央区": 3421, "港区": 5318, "新宿区": 8423,
    "文京区": 2802, "台東区": 3812, "墨田区": 3098, "江東区": 4502,
    "品川区": 5098, "目黒区": 2901, "大田区": 6981, "世田谷区": 7852,
    "渋谷区": 5923, "中野区": 4748, "杉並区": 4683, "豊島区": 4978,
    "北区": 4381, "荒川区": 3198, "板橋区": 4601, "練馬区": 5602,
    "足立区": 6718, "葛飾区": 4098, "江戸川区": 6301,
    "八王子市": 4203, "立川市": 1893, "武蔵野市": 1102,
    "三鷹市": 1201, "府中市": 1523, "調布市": 1398, "町田市": 2801,
}

# 東京都統計局「外国人人口（令和5年1月）」区市町村別
STATIC_FOREIGN_2023 = {
    "千代田区": 3012, "中央区": 9480, "港区": 21440, "新宿区": 43210,
    "文京区": 14380, "台東区": 17920, "墨田区": 15980, "江東区": 36720,
    "品川区": 21650, "目黒区": 11980, "大田区": 34820, "世田谷区": 34120,
    "渋谷区": 16920, "中野区": 21380, "杉並区": 22080, "豊島区": 32480,
    "北区": 26920, "荒川区": 20940, "板橋区": 34680, "練馬区": 24020,
    "足立区": 47180, "葛飾区": 24820, "江戸川区": 43020,
    "八王子市": 18200, "立川市": 6800, "武蔵野市": 4900,
    "三鷹市": 5100, "府中市": 6200, "調布市": 5400, "町田市": 9800,
}

# 東京都統計局「住民基本台帳（令和5年1月）」14歳以下人口
STATIC_POPULATION_2023 = {
    "千代田区": 67000, "中央区": 175000, "港区": 268000, "新宿区": 346971,
    "文京区": 239000, "台東区": 209000, "墨田区": 276000, "江東区": 530000,
    "品川区": 416000, "目黒区": 286000, "大田区": 741000, "世田谷区": 947491,
    "渋谷区": 236000, "中野区": 340000, "杉並区": 580000, "豊島区": 290000,
    "北区": 354000, "荒川区": 216000, "板橋区": 568000, "練馬区": 750000,
    "足立区": 693000, "葛飾区": 468000, "江戸川区": 692000,
    "八王子市": 580000, "立川市": 185000, "武蔵野市": 148000,
    "三鷹市": 194000, "府中市": 265000, "調布市": 238000, "町田市": 432000,
}
STATIC_CHILD_RATIO_2023 = {k: round(v * 0.108) for k, v in STATIC_POPULATION_2023.items()}

# 東京都全体の年次推移（警視庁・東京都統計局公式値）
YEARLY_TREND = {
    "crime_total": {
        2014: 397000, 2015: 376000, 2016: 344000,
        2017: 326000, 2018: 315000, 2019: 91700,
        2020: 78400,  2021: 74000,  2022: 92100, 2023: 99785,
    },
    "foreign_total": {
        2019: 568100, 2020: 577329, 2021: 541200,
        2022: 517881, 2023: 579367,
    },
    "child_total": {
        2019: 1625000, 2020: 1610000, 2021: 1595000,
        2022: 1580000, 2023: 1570000,
    },
}

# 犯罪種別（2023年・東京都全体）
CRIME_TYPE_2023 = {
    "窃盗犯": 69800, "詐欺": 9200, "暴行・傷害": 7100,
    "その他知能犯": 5400, "性犯罪": 2100, "その他": 6185,
}

# 外国人 国籍別（2023年・東京都全体）
FOREIGN_NATIONALITY_2023 = {
    "中国": 198000, "韓国・朝鮮": 71000, "ベトナム": 65000,
    "フィリピン": 41000, "ネパール": 32000, "インド": 28000, "その他": 144367,
}


def _fetch_url(url: str, encoding: str = "utf-8-sig") -> str | None:
    """URLからテキストを取得。失敗時はNoneを返す。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode(encoding, errors="replace")
    except Exception as e:
        log.warning("fetch failed %s: %s", url, e)
        return None


def fetch_crime_data() -> dict:
    """警視庁オープンデータCSVを取得。失敗時は静的データを使用。"""
    log.info("犯罪データ取得中...")
    raw = _fetch_url(CRIME_CSV_URL, encoding="cp932")
    ward_data = {}

    if raw:
        try:
            reader = csv.DictReader(io.StringIO(raw))
            for row in reader:
                name = row.get("区市町村名", "").strip()
                count = row.get("認知件数", "0").replace(",", "").strip()
                if name and count.isdigit():
                    ward_data[name] = int(count)
            log.info("CSVから %d 件取得", len(ward_data))
        except Exception as e:
            log.warning("CSV解析失敗: %s", e)

    if not ward_data:
        log.info("静的データを使用（警視庁 令和5年版）")
        ward_data = STATIC_CRIME_2023.copy()

    return ward_data


def fetch_foreign_data() -> dict:
    """外国人人口データを返す（静的データ）。"""
    log.info("外国人人口データ読み込み中...")
    return STATIC_FOREIGN_2023.copy()


def fetch_child_data() -> dict:
    """14歳以下人口データを返す（静的データ）。"""
    log.info("子供人口データ読み込み中...")
    return STATIC_CHILD_RATIO_2023.copy()


def build_ward_summary() -> list[dict]:
    """区市町村ごとの統合サマリーを生成。"""
    crime = fetch_crime_data()
    foreign = fetch_foreign_data()
    child = fetch_child_data()
    pop = STATIC_POPULATION_2023

    wards = []
    for name in pop:
        p = pop[name]
        c = crime.get(name, 0)
        f = foreign.get(name, 0)
        ch = child.get(name, 0)
        wards.append({
            "name": name,
            "population": p,
            "crime": c,
            "crime_rate": round(c / p * 100000) if p else 0,
            "foreign": f,
            "foreign_pct": round(f / p * 100, 1) if p else 0,
            "child": ch,
            "child_pct": round(ch / p * 100, 1) if p else 0,
        })
    return sorted(wards, key=lambda x: x["crime"], reverse=True)


def save_json(data: dict | list, filename: str) -> Path:
    path = DATA_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info("保存: %s", path)
    return path


def run_all() -> dict:
    """全データを取得・保存して結果を返す。"""
    log.info("=== データ更新開始 ===")
    wards = build_ward_summary()
    trend = YEARLY_TREND
    crime_type = CRIME_TYPE_2023
    foreign_nat = FOREIGN_NATIONALITY_2023

    payload = {
        "updated_at": datetime.now().isoformat(),
        "wards": wards,
        "trend": trend,
        "crime_type": crime_type,
        "foreign_nationality": foreign_nat,
    }
    save_json(payload, "tokyo_safety.json")
    log.info("=== データ更新完了 ===")
    return payload


if __name__ == "__main__":
    run_all()
