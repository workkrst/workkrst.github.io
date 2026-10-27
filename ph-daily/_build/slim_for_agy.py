#!/usr/bin/env python3
"""slim_for_agy.py <D> — 발행 agy 입력용 slim JSON 생성.

{D}/data.json 의 products에서 agy(분석·브리핑·디스콰이엇 코멘트)에 필요한 필드만 남겨
/tmp/ph-slim-{D}.json 로 저장. 코멘트 영어 원문(text)·이미지·URL 등 제거.

출력: SLIM:<bytes>
"""
import json
import sys
from pathlib import Path

BASE = Path("/home/admin/report-hub/ph-daily")
MAX_COMMENTS = 8
KR_MAX = 220


def slim(d: str) -> int:
    data = json.loads((BASE / d / "data.json").read_text())
    products = []
    for p in data.get("products", []):
        comments = [
            {"author": c.get("author"), "is_maker": bool(c.get("is_maker")),
             "kr": (c.get("kr") or "")[:KR_MAX]}
            for c in (p.get("comments") or [])[:MAX_COMMENTS]
        ]
        products.append({
            "slug": p.get("slug"),
            "name": p.get("name"),
            "tagline_kr": p.get("tagline_kr"),
            "categories": p.get("categories"),
            "upvotes": p.get("upvotes"),
            "comments_count": p.get("comments_count"),
            "desc_kr": p.get("desc_kr"),
            "comment_summary": p.get("comment_summary"),
            "warnings": p.get("warnings"),
            "comments": comments,
        })
    out = {"date": data.get("date"), "products": products}
    dst = Path(f"/tmp/ph-slim-{d}.json")
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"SLIM:{dst.stat().st_size}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: slim_for_agy.py <YYYY-MM-DD>", file=sys.stderr)
        sys.exit(1)
    sys.exit(slim(sys.argv[1]))
