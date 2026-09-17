#!/usr/bin/env python3
# PH 데일리 파이프라인 — 결정론 발행 스크립트 (LLM은 summary/notable 작성만 담당)
# 사용법:
#   publish.py merge   YYYY-MM-DD [--wait N]          _pending 원본 → data.json 병합 (파일 없으면 최대 N초 대기, 기본 300)
#   publish.py publish YYYY-MM-DD [--meta FILE] [--dry] meta 반영 → list_gen → build → git push → URL 200 확인
# 종료코드: 0 성공 / 2 수집데이터 없음 / 3 데이터 손상 / 4 빌드 실패 / 5 push 실패 / 6 URL 확인 실패
import argparse, json, subprocess, sys, time, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))
BASE = Path(__file__).resolve().parent.parent  # ph-daily/
REQ = ["name", "tagline_kr", "desc_kr", "image", "maker", "price_model", "launch_url_used"]


def sh(cmd, cwd=None, timeout=600):
    return subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def cmd_merge(date, wait):
    ddir, pend = BASE / date, BASE / "_pending" / date
    dj = ddir / "data.json"
    if dj.exists():
        print(f"[merge:skip] {dj} 이미 존재 — 병합 생략")
        return 0
    deadline = time.time() + wait
    raws = []
    while True:
        raws = sorted(pend.glob("*.json")) if pend.exists() else []
        if raws:
            break
        if time.time() >= deadline:
            print(f"[merge:FAIL:2] 수집 데이터 없음: {pend} (수집 크론 실패 추정)")
            ft = pend / "FAILED.txt"
            if ft.exists():
                print(f"[merge:info] FAILED.txt: {ft.read_text(encoding='utf-8')[:500]}")
            return 2
        time.sleep(20)
    merged, parse_err = {}, []
    for f in raws:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            parse_err.append(f"{f.name}: {e}")
            continue
        if isinstance(d, dict):
            for slug, p in d.items():
                if isinstance(p, dict):
                    p["slug"] = slug
                    merged[slug] = p
    if not merged:
        print(f"[merge:FAIL:3] 파일은 있으나 유효 제품 없음. 파싱오류: {parse_err}")
        return 3
    products = sorted(merged.values(), key=lambda p: -p.get("upvotes", 0))
    miss = [f"{p.get('slug','?')}:{f}" for p in products for f in REQ if not p.get(f)]
    no_sum = [p.get("slug", "?") for p in products if not p.get("comment_summary")]
    data = {
        "date": date,
        "collected_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
        "summary": "",
        "notable": [],
        "products": products,
    }
    ddir.mkdir(parents=True, exist_ok=True)
    dj.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[merge:ok] 제품 {len(products)}개, 댓글 {sum(len(p.get('comments', [])) for p in products)}개 → {dj}")
    if miss:
        print(f"[merge:warn] 필수필드 누락: {', '.join(miss)}")
    if no_sum:
        print(f"[merge:warn] comment_summary 누락: {', '.join(no_sum)}")
    return 0


def apply_meta(date, meta_path):
    dj = BASE / date / "data.json"
    data = json.loads(dj.read_text(encoding="utf-8"))
    m = json.loads(Path(meta_path).read_text(encoding="utf-8"))
    if m.get("summary"):
        data["summary"] = m["summary"]
    if m.get("notable") is not None:
        data["notable"] = m["notable"]
    dj.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[meta:ok] summary {len(data.get('summary',''))}자, notable {len(data.get('notable',[]))}개 반영")


def cmd_publish(date, meta, dry):
    dj = BASE / date / "data.json"
    if not dj.exists():
        print("[pub:FAIL:3] data.json 없음 — 먼저 merge 실행")
        return 3
    if meta:
        apply_meta(date, meta)
    data = json.loads(dj.read_text(encoding="utf-8"))
    ps = data.get("products", [])
    if not ps:
        print("[pub:FAIL:3] products 비어있음")
        return 3
    if not data.get("summary"):
        top = ps[0]
        data["summary"] = (
            f"오늘 Top {len(ps)} 중 1위는 {top.get('name','?')}(▲{top.get('upvotes',0)}). "
            f"댓글 {sum(len(p.get('comments', [])) for p in ps)}개를 수집했다."
        )
        print("[pub:warn] summary 미작성 — 기본 문장으로 대체")
    ups = [p.get("upvotes", 0) for p in ps]
    if ups != sorted(ups, reverse=True):
        print("[pub:warn] products가 업보트 내림차순이 아님")
    ctot = sum(len(p.get("comments", [])) for p in ps)
    dj.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    r = sh(f"{sys.executable} _build/build_report.py {date}", cwd=BASE)
    if r.returncode:
        print(f"[pub:FAIL:4] build 실패\n{(r.stderr or r.stdout)[-800:]}")
        return 4
    r = sh(f"{sys.executable} _build/list_gen.py", cwd=BASE)
    if r.returncode:
        print(f"[pub:FAIL:4] list_gen 실패\n{(r.stderr or r.stdout)[-800:]}")
        return 4
    print("[pub:build-ok] index.html·목록 갱신 완료")
    if dry:
        print(f"[pub:dry-ok] {date}/index.html 빌드 성공 — push·확인 생략")
        return 0
    r = sh(
        f"git add -A && git commit -m 'ph-daily: {date} 리포트' && git push origin HEAD",
        cwd=BASE.parent,
        timeout=180,
    )
    if r.returncode and "nothing to commit" not in (r.stdout or ""):
        print(f"[pub:FAIL:5] git push 실패\n{(r.stdout or '') + (r.stderr or '')[-600:]}")
        return 5
    url = f"https://workkrst.github.io/ph-daily/{date}/"
    for i in range(10):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20
            ) as resp:
                if resp.status == 200:
                    print(f"[pub:ok] {url} (200, 시도 {i + 1}) — 제품 {len(ps)}개 · 댓글 {ctot}개")
                    return 0
        except Exception:
            pass
        time.sleep(30)
    print(f"[pub:FAIL:6] URL 200 확인 실패: {url} (push는 성공했을 수 있음 — 수동 확인 요망)")
    return 6


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge")
    m.add_argument("date")
    m.add_argument("--wait", type=int, default=300)
    p = sub.add_parser("publish")
    p.add_argument("date")
    p.add_argument("--meta")
    p.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    code = cmd_merge(a.date, a.wait) if a.cmd == "merge" else cmd_publish(a.date, a.meta, a.dry)
    sys.exit(code)


if __name__ == "__main__":
    main()
