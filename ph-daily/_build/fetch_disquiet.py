#!/usr/bin/env python3
"""Disquiet.io new product fetcher."""

import argparse
from datetime import datetime, timedelta, timezone
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

REGISTRY_PATH = "/home/admin/report-hub/ph-daily/_pending/disquiet_seen.json"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
KST = timezone(timedelta(hours=9))


def fetch_page(page_num, timeout=30):
    url = f"https://disquiet.io/products?page={page_num}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return resp.read().decode("utf-8", errors="replace")
                sys.stderr.write(
                    f"[Page {page_num}] Attempt {attempt + 1} returned status {resp.status}\n"
                )
        except Exception as e:
            sys.stderr.write(f"[Page {page_num}] Attempt {attempt + 1} failed: {e}\n")
        if attempt == 0:
            time.sleep(3)
    return None


def parse_disquiet_page(html_text):
    """Extract main product list items from HTML, discarding sidebar and AD items."""
    # 1. Determine sidebar start to discard popular products and bottom items
    pop_idx = html_text.find("인기 프로덕트")
    if pop_idx == -1:
        pop_idx = html_text.find("인기프로덕트")

    sidebar_idx = -1
    if pop_idx != -1:
        aside_idx = html_text.rfind("<aside", 0, pop_idx)
        if aside_idx != -1 and (pop_idx - aside_idx) < 10000:
            sidebar_idx = aside_idx
        else:
            sidebar_idx = pop_idx
    else:
        aside_w300 = html_text.find('<aside class="w-[300px]')
        if aside_w300 != -1:
            sidebar_idx = aside_w300
        else:
            nav_idx = html_text.find('<nav aria-label="Pagination"')
            if nav_idx != -1:
                sidebar_idx = nav_idx

    main_html = html_text[:sidebar_idx] if sidebar_idx != -1 else html_text

    # 2. Extract card chunks
    card_starts = [
        m.start()
        for m in re.finditer(r'<div class=[\"\']card group relative', main_html)
    ]
    products = []
    for i, start in enumerate(card_starts):
        end = card_starts[i + 1] if i + 1 < len(card_starts) else len(main_html)
        card_chunk = main_html[start:end]

        # Ignore AD cards
        if re.search(r">\s*AD\s*<", card_chunk) or "disquiet-ad-slot" in card_chunk:
            continue

        # Extract slug
        m_slug = re.search(r'href=[\"\']/products/([^\"\'/?#]+)[\"\']', card_chunk)
        if not m_slug:
            continue
        slug = m_slug.group(1).strip()

        # Extract name
        m_name = re.search(
            r"<h3[^>]*>[\s\S]*?<a[^>]*>([\s\S]*?)</a>[\s\S]*?</h3>", card_chunk
        )
        if not m_name:
            m_name = re.search(
                r'<a[^>]+href=[\"\']/products/[^\"\'/?#]+[\"\'][^>]*>([\s\S]*?)</a>',
                card_chunk,
            )
        raw_name = m_name.group(1) if m_name else ""
        name = html.unescape(re.sub(r"<[^>]+>", "", raw_name)).strip()

        # Extract tagline
        m_tag = re.search(
            r'<p[^>]*class=[\"\'][^\"\']*text-base-content/60[^\"\']*[\"\'][^>]*>([\s\S]*?)</p>',
            card_chunk,
        )
        if not m_tag:
            m_tag = re.search(r"<p[^>]*>([\s\S]*?)</p>", card_chunk)
        raw_tag = m_tag.group(1) if m_tag else ""
        tagline = html.unescape(re.sub(r"<[^>]+>", "", raw_tag)).strip()

        # Extract upvotes
        m_up = re.search(r'aria-label=[\"\']추천\s*([\d,]+)[\"\']', card_chunk)
        if not m_up:
            m_up = re.search(
                r'id=[\"\']upvote_product_\d+[\"\'][\s\S]*?<span[^>]*class=[\"\'][^\"\']*text-base-content[^\"\']*[\"\'][^>]*>\s*([\d,]+)\s*</span>',
                card_chunk,
            )
        if not m_up:
            m_up = re.search(
                r'id=[\"\']upvote_product_\d+[\"\'][\s\S]*?<span[^>]*>\s*([\d,]+)\s*</span>',
                card_chunk,
            )

        upvotes = 0
        if m_up:
            try:
                upvotes = int(m_up.group(1).replace(",", ""))
            except (ValueError, TypeError):
                upvotes = 0

        products.append({
            "slug": slug,
            "name": name,
            "tagline": tagline,
            "upvotes": upvotes,
            "url": f"https://disquiet.io/products/{slug}",
        })

    return products


def load_registry(registry_path=REGISTRY_PATH):
    if os.path.exists(registry_path):
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "slugs" in data and isinstance(
                    data["slugs"], list
                ):
                    return data["slugs"]
        except Exception as e:
            sys.stderr.write(
                f"Warning: Failed to read registry from {registry_path}: {e}\n"
            )
    return []


class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write(f"Error: {message}\n")
        self.print_help(sys.stderr)
        sys.exit(1)


def parse_args():
    parser = CustomArgumentParser(
        description="Fetch new products from disquiet.io",
        usage="%(prog)s <out.json> [--pages N] [--init] [--keep K]",
    )
    parser.add_argument("out_json", help="Path to output JSON file")
    parser.add_argument(
        "--pages",
        type=int,
        default=2,
        help="Number of pages to fetch (default: 2)",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize registry with fetched slugs",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=None,
        help="Keep K items in output when using --init",
    )
    parser.add_argument(
        "--registry", default=REGISTRY_PATH, help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--local-files", nargs="*", default=None, help=argparse.SUPPRESS
    )
    return parser.parse_args()


def main():
    args = parse_args()

    page_htmls = {}
    if args.local_files:
        for idx, fpath in enumerate(args.local_files, start=1):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    page_htmls[idx] = f.read()
            except Exception as e:
                sys.stderr.write(f"Failed to read local file {fpath}: {e}\n")
    else:
        for p in range(1, args.pages + 1):
            content = fetch_page(p)
            if content:
                page_htmls[p] = content

    if not page_htmls:
        sys.stderr.write("Fatal: No pages could be fetched/read.\n")
        sys.exit(1)

    page_products = {}
    all_products = []
    for p in sorted(page_htmls.keys()):
        prods = parse_disquiet_page(page_htmls[p])
        page_products[p] = prods
        all_products.extend(prods)

    total_main_count = len(all_products)

    # Deduplicate preserving document order
    unique_products = []
    seen_in_crawl = set()
    for item in all_products:
        slug = item["slug"]
        if slug not in seen_in_crawl:
            seen_in_crawl.add(slug)
            unique_products.append(item)

    all_crawl_slugs = [p["slug"] for p in unique_products]

    # Load existing registry
    old_registry_slugs = load_registry(args.registry)
    old_registry_set = set(old_registry_slugs)

    if args.init:
        # --init: 레지스트리를 이번 수집 slug 전부로 시딩.
        updated_registry_slugs = list(all_crawl_slugs)
        # --keep K 동시 지정 시 페이지1 메인 리스트 앞에서 K개는 new에 넣어 out.json에 포함(레지스트리에는 그것도 전부 시딩). --keep 없으면 products는 빈 배열.
        if args.keep is not None and args.keep > 0:
            page1_prods = page_products.get(1, [])
            new_products = page1_prods[: args.keep]
        else:
            new_products = []
    else:
        # 일반 실행: new = (1..N 페이지 메인 리스트 slug, 문서 순서, 중복 제거) - 레지스트리.
        new_products = [
            p for p in unique_products if p["slug"] not in old_registry_set
        ]
        # 갱신 레지스트리(기존+new 전부)
        updated_registry_slugs = list(old_registry_slugs)
        reg_set = set(old_registry_slugs)
        for p in new_products:
            if p["slug"] not in reg_set:
                updated_registry_slugs.append(p["slug"])
                reg_set.add(p["slug"])

    # Build out.json structure
    now_kst = datetime.now(KST)
    output_data = {
        "date": now_kst.strftime("%Y-%m-%d"),
        "fetched_at": now_kst.isoformat(timespec="minutes"),
        "count": len(new_products),
        "products": new_products,
    }

    # Ensure parent directory exists
    out_path = os.path.abspath(args.out_json)
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Save out.json
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except Exception as e:
        sys.stderr.write(f"Fatal: Failed to write {out_path}: {e}\n")
        sys.exit(1)

    # Save <out.json>.registry
    registry_path = f"{out_path}.registry"
    try:
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(
                {"slugs": updated_registry_slugs}, f, ensure_ascii=False, indent=2
            )
            f.write("\n")
    except Exception as e:
        sys.stderr.write(f"Fatal: Failed to write registry {registry_path}: {e}\n")
        sys.exit(1)

    # Stderr diagnosis summary
    success_pages = len(page_htmls)
    total_requested_pages = (
        len(args.local_files) if args.local_files else args.pages
    )
    sys.stderr.write(
        f"[진단 요약] 페이지 확보: {success_pages}/{total_requested_pages} | 메인 리스트: {total_main_count}개 | new: {len(new_products)}개\n"
    )

    sys.exit(0)


if __name__ == "__main__":
    main()
