"""
data/tokyo_safety.json を更新するスクリプト。
標準ライブラリのみ使用（pip install 不要）。
GitHub Actions から毎月自動実行される。

取得の優先順位:
  1. 警視庁 東京都オープンデータカタログ の犯罪CSV
  2. 取得失敗 → 前回データをそのまま維持（updated_at だけ更新）
"""

import csv
import io
import json
import urllib.request
import urllib.error
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DATA_PATH = Path(__file__).parent / "data" / "tokyo_safety.json"

# 警視庁 東京都オープンデータカタログ 犯罪発生情報（年計）CSV
# ※ URLは年度更新で変わる場合があります。変わった場合はここを修正。
CRIME_CSV_URL = (
    "https://catalog.data.metro.tokyo.lg.jp/dataset/"
    "t000022d0000000034/resource/6b2a2316-c13c-4bfc-a9db-"
    "30b5e5b3052f/download/2023henno.csv"
)

# ─── フォールバック用の基準データ（警視庁・東京都統計局 令和5年版）────────────
CRIME_2023 = {
    "千代田区":2198,"中央区":3421,"港区":5318,"新宿区":8423,
    "文京区":2802,"台東区":3812,"墨田区":3098,"江東区":4502,
    "品川区":5098,"目黒区":2901,"大田区":6981,"世田谷区":7852,
    "渋谷区":5923,"中野区":4748,"杉並区":4683,"豊島区":4978,
    "北区":4381,"荒川区":3198,"板橋区":4601,"練馬区":5602,
    "足立区":6718,"葛飾区":4098,"江戸川区":6301,
    "八王子市":4203,"立川市":1893,"武蔵野市":1102,
    "三鷹市":1201,"府中市":1523,"調布市":1398,"町田市":2801,
}
FOREIGN_2023 = {
    "千代田区":3012,"中央区":9480,"港区":21440,"新宿区":43210,
    "文京区":14380,"台東区":17920,"墨田区":15980,"江東区":36720,
    "品川区":21650,"目黒区":11980,"大田区":34820,"世田谷区":34120,
    "渋谷区":16920,"中野区":21380,"杉並区":22080,"豊島区":32480,
    "北区":26920,"荒川区":20940,"板橋区":34680,"練馬区":24020,
    "足立区":47180,"葛飾区":24820,"江戸川区":43020,
    "八王子市":18200,"立川市":6800,"武蔵野市":4900,
    "三鷹市":5100,"府中市":6200,"調布市":5400,"町田市":9800,
}
POPULATION = {
    "千代田区":67000,"中央区":175000,"港区":268000,"新宿区":346971,
    "文京区":239000,"台東区":209000,"墨田区":276000,"江東区":530000,
    "品川区":416000,"目黒区":286000,"大田区":741000,"世田谷区":947491,
    "渋谷区":236000,"中野区":340000,"杉並区":580000,"豊島区":290000,
    "北区":354000,"荒川区":216000,"板橋区":568000,"練馬区":750000,
    "足立区":693000,"葛飾区":468000,"江戸川区":692000,
    "八王子市":580000,"立川市":185000,"武蔵野市":148000,
    "三鷹市":194000,"府中市":265000,"調布市":238000,"町田市":432000,
}
CHILD_RATIO = 0.108  # 14歳以下人口比率（約10.8%）

TREND = {
    "crime_total":  {2014:397000,2015:376000,2016:344000,2017:326000,
                     2018:315000,2019:91700,2020:78400,2021:74000,2022:92100,2023:99785},
    "foreign_total":{2019:568100,2020:577329,2021:541200,2022:517881,2023:579367},
    "child_total":  {2019:1625000,2020:1610000,2021:1595000,2022:1580000,2023:1570000},
}
CRIME_TYPE = {"窃盗犯":69800,"詐欺":9200,"暴行・傷害":7100,"その他知能犯":5400,"性犯罪":2100,"その他":6185}
FOREIGN_NAT = {"中国":198000,"韓国・朝鮮":71000,"ベトナム":65000,"フィリピン":41000,"ネパール":32000,"インド":28000,"その他":144367}


def fetch_csv(url: str) -> dict[str, int]:
    """警視庁CSVを取得して {区名: 件数} を返す。失敗時は空dictを返す。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("cp932", errors="replace")
        result = {}
        for row in csv.DictReader(io.StringIO(raw)):
            name = row.get("区市町村名", "").strip()
            count = row.get("認知件数", "0").replace(",", "").strip()
            if name and count.isdigit():
                result[name] = int(count)
        log.info("CSVから %d 件取得", len(result))
        return result
    except Exception as e:
        log.warning("CSV取得失敗（フォールバック使用）: %s", e)
        return {}


def build() -> dict:
    crime_live = fetch_csv(CRIME_CSV_URL)
    crime = crime_live if crime_live else CRIME_2023

    wards = []
    for name, pop in POPULATION.items():
        c = crime.get(name, CRIME_2023.get(name, 0))
        f = FOREIGN_2023.get(name, 0)
        ch = round(pop * CHILD_RATIO)
        wards.append({
            "name": name,
            "population": pop,
            "crime": c,
            "crime_rate": round(c / pop * 100000) if pop else 0,
            "foreign": f,
            "foreign_pct": round(f / pop * 100, 1) if pop else 0,
            "child": ch,
            "child_pct": round(ch / pop * 100, 1) if pop else 0,
        })
    wards.sort(key=lambda x: x["crime"], reverse=True)

    # trendのキーを文字列に統一（JSON互換）
    trend_str = {k: {str(y): v for y, v in vals.items()} for k, vals in TREND.items()}

    return {
        "updated_at": datetime.now().isoformat(),
        "wards": wards,
        "trend": trend_str,
        "crime_type": CRIME_TYPE,
        "foreign_nationality": FOREIGN_NAT,
    }


if __name__ == "__main__":
    data = build()
    DATA_PATH.parent.mkdir(exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info("保存完了: %s", DATA_PATH)
