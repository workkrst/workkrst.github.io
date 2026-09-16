# Product Hunt 데일리 — 날짜별 목록 데이터 자동 생성
# 사용법: python3 list_gen.py   (ph-daily/ 상위에서 실행하거나 경로 지정)
# ph-daily/YYYY-MM-DD/data.json 을 스캔해서 ph-daily/list-data.js 를 생성한다.
import json, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # ph-daily/

def main():
    items = []
    for d in sorted(BASE.iterdir()):
        if not d.is_dir() or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.name):
            continue
        dj = d / "data.json"
        if not dj.exists():
            continue
        try:
            data = json.loads(dj.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[skip] {d.name}: data.json 파싱 실패 ({e})", file=sys.stderr)
            continue
        products = data.get("products", [])
        top = max(products, key=lambda p: p.get("upvotes", 0), default=None)
        items.append({
            "date": data.get("date", d.name),
            "url": f"{d.name}/",
            "top_product": (top or {}).get("name", "-"),
            "count": len(products),
            "upvotes_total": sum(p.get("upvotes", 0) or 0 for p in products),
            "comments_total": sum(len(p.get("comments", [])) for p in products),
        })
    items.sort(key=lambda x: x["date"], reverse=True)
    out = "window.PH_DAILY_LIST = " + json.dumps(items, ensure_ascii=False, indent=2) + ";\n"
    (BASE / "list-data.js").write_text(out, encoding="utf-8")
    print(f"[ok] list-data.js 갱신: {len(items)}일치")

if __name__ == "__main__":
    main()
