#!/usr/bin/env python3
"""extract_raw.py <D> — PH 원본 .md를 agy 입력용 compact JSON으로 압축.

_pending/{D}/raw/top5.json 의 slug 각각에 대해 raw/<slug>.md 를 파싱해
raw/<slug>.compact.json 생성 + raw/_compact_manifest.json 작성.

출력: EXTRACTED:<n>/<total>
- 개별 slug 파싱 실패는 건너뛰고 manifest에서 원본 md를 가리킴 (파이프라인 죽지 않음)
"""
import json
import re
import sys
from pathlib import Path

BASE = Path("/home/admin/report-hub/ph-daily")


def strip_md_links(s: str) -> str:
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)  # images
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)  # links -> text
    return s.strip()


def parse_md(md: str, slug: str) -> dict:
    lines = md.splitlines()

    name = tagline = None
    for ln in lines:
        if name is None and ln.startswith("# "):
            name = ln[2:].strip()
            continue
        if name and tagline is None and ln.startswith("## "):
            tagline = ln[3:].strip()
            break

    # 이미지: 첫 번째는 헤더 아이콘이므로 두 번째 imgix URL이 런치 아이콘 (data.json 관례와 일치)
    img_urls = re.findall(r"!\[[^\]]*\]\((https://ph-files\.imgix\.net[^)]*)\)", md)
    image = img_urls[1] if len(img_urls) > 1 else (img_urls[0] if img_urls else None)

    wm = re.search(r"\[Visit website\]\((https?://[^)]+)\)", md)
    website = wm.group(1) if wm else None

    pm = re.search(r"(Free Options|Payment Required|Free Trial|Paid|Free)", md)
    price_model = pm.group(1) if pm else None

    desc_parts = []
    for ln in lines:
        t = ln.strip()
        if len(t) > 80 and not t.startswith(("#", "[", "!", "*", ">", "|")):
            desc_parts.append(t)
            if len(desc_parts) == 2:
                break
    desc = " ".join(desc_parts)[:1200]

    categories = list(dict.fromkeys(
        m.group(1) for m in re.finditer(
            r"\[([^\]]+)\]\(https://www\.producthunt\.com/categories/[^)]*\)", md)))

    comments = []
    i = 0
    while i < len(lines) and len(comments) < 14:
        m = re.match(r"^\[([^\]]+)\]\(https://www\.producthunt\.com/@[^)]+\)\s*$", lines[i].strip())
        if not m:
            i += 1
            continue
        author = m.group(1)
        j = i + 1
        is_maker = False
        text_lines = []
        while j < len(lines):
            t = lines[j].strip()
            if t == "Maker":
                is_maker = True
                j += 1
                continue
            if t.startswith("Upvote"):
                break
            if re.match(r"^\[[^\]]+\]\(https://www\.producthunt\.com/@[^)]+\)$", t):
                break  # next comment author
            if t and not t.startswith(("![", "[![", "Report", "Share")) and "####" not in t \
                    and not re.match(r"^\d+[hm] ago$", t):
                text_lines.append(t)
            j += 1
        text = strip_md_links(" ".join(text_lines))
        text = re.sub(r"\s+", " ", text).strip().lstrip("•").strip()
        if (text and len(text) > 5 and "####" not in text
                and not re.match(r"^\d+\s+reviews?\b", text)
                and "What's great" not in text and "What could be improved" not in text):
            comments.append({"author": author, "is_maker": is_maker, "text": text[:500]})
        i = j

    return {
        "slug": slug,
        "name": name,
        "tagline": tagline,
        "desc": desc,
        "categories": categories,
        "image": image,
        "website": website,
        "price_model": price_model,
        "ph_url": f"https://www.producthunt.com/products/{slug}",
        "comments": comments[:12],
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: extract_raw.py <YYYY-MM-DD>", file=sys.stderr)
        return 1
    d = sys.argv[1]
    raw = BASE / "_pending" / d / "raw"
    top5 = json.loads((raw / "top5.json").read_text())

    manifest, ok = {}, 0
    for item in top5:
        slug = item["slug"]
        src = raw / f"{slug}.md"
        dst = raw / f"{slug}.compact.json"
        try:
            parsed = parse_md(src.read_text(), slug)
            if not parsed.get("name"):
                raise ValueError("name not found")
            dst.write_text(json.dumps(parsed, ensure_ascii=False, indent=1))
            manifest[slug] = dst.name
            ok += 1
        except Exception as e:
            print(f"WARN: {slug} compact failed ({e}), fallback to raw md", file=sys.stderr)
            manifest[slug] = src.name

    (raw / "_compact_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1))
    print(f"EXTRACTED:{ok}/{len(top5)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
