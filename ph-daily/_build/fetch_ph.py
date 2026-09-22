#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request


def get_apify_token():
    cmd = "grep -m1 '^TOKEN=' /home/admin/.openclaw/workspace/scripts/apify-usage.sh | cut -d= -f2"
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    token = proc.stdout.strip().strip("'\"")
    if not token:
        sys.stderr.write("Error: Failed to retrieve Apify token\n")
        sys.exit(1)
    return token


def fetch_url_markdown(url, token):
    endpoint = f"https://api.apify.com/v2/acts/apify~web-fetch/run-sync-get-dataset-items?token={token}&timeout=120"
    payload = json.dumps({"url": url, "formats": ["markdown"]}).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=130) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("markdown") or ""
    return ""


def fetch_markdown(url, token):
    md = ""
    for attempt in range(2):
        try:
            md = fetch_url_markdown(url, token)
            if md and len(md.strip()) > 0:
                break
        except Exception as e:
            sys.stderr.write(f"Attempt {attempt + 1} failed: {e}\n")
        if attempt == 0:
            time.sleep(3)
    return md


def main():
    if len(sys.argv) < 3:
        sys.stderr.write("Usage:\n  python3 fetch_ph.py home <out.md>\n  python3 fetch_ph.py slug <slug> <out.md>\n")
        sys.exit(1)

    mode = sys.argv[1]
    if mode == "home":
        if len(sys.argv) != 3:
            sys.stderr.write("Usage: python3 fetch_ph.py home <out.md>\n")
            sys.exit(1)
        target_url = "https://www.producthunt.com/"
        out_path = sys.argv[2]
    elif mode == "slug":
        if len(sys.argv) != 4:
            sys.stderr.write("Usage: python3 fetch_ph.py slug <slug> <out.md>\n")
            sys.exit(1)
        slug = sys.argv[2]
        target_url = f"https://www.producthunt.com/posts/{slug}"
        fallback_url = f"https://www.producthunt.com/products/{slug}"  # posts 경로가 빈 응답인 제품 대비
        out_path = sys.argv[3]
    else:
        sys.stderr.write(f"Unknown mode: {mode}\n")
        sys.exit(1)

    token = get_apify_token()
    md = fetch_markdown(target_url, token)
    if len(md) < 3000 and mode == "slug":
        md = fetch_markdown(fallback_url, token)  # products 폴백 1회

    if len(md) < 3000:
        sys.stderr.write(f"Error: Fetched markdown length ({len(md)}) is less than 3000 chars (possible block)\n")
        sys.exit(1)

    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    main()
