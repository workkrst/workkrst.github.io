# Product Hunt 데일리 — 일일 리포트 HTML 생성기
# 사용법: python3 build_report.py YYYY-MM-DD
# ph-daily/YYYY-MM-DD/data.json 을 읽어 같은 폴더에 index.html 을 생성한다.
import json, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # ph-daily/

TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex, nofollow">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PH 데일리 __DATE__</title>
<style>
:root{--bg:#f6f7f9;--card:#ffffff;--ink:#1a1d23;--sub:#5c6470;--line:#e6e9ee;--acc:#da552f;--chip:#eef1f5;--badge:#fdeee8;}
@media (prefers-color-scheme: dark){:root{--bg:#14161a;--card:#1d2026;--ink:#e8eaee;--sub:#9aa3af;--line:#2a2f38;--acc:#ff6b3d;--chip:#262b33;--badge:#3a2a22;}}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans KR",sans-serif;background:var(--bg);color:var(--ink);line-height:1.6;padding-bottom:60px}
.wrap{max-width:1040px;margin:0 auto;padding:20px 16px}
.topbtn{position:fixed;top:14px;right:14px;z-index:50;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:999px;padding:8px 16px;font-size:14px;font-weight:600;cursor:pointer;text-decoration:none;box-shadow:0 2px 10px rgba(0,0,0,.12)}
.topbtn:hover{border-color:var(--acc);color:var(--acc)}
header h1{font-size:24px;font-weight:800;letter-spacing:-.3px}
header .meta{color:var(--sub);font-size:14px;margin-top:4px}
.summary{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:18px 0;font-size:15px}
.summary b{color:var(--acc)}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:14px 0}
.chip{background:var(--chip);border:none;color:var(--ink);border-radius:999px;padding:6px 14px;font-size:13px;cursor:pointer;font-weight:600}
.chip.on{background:var(--acc);color:#fff}
.spacer{flex:1}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;cursor:pointer;transition:.15s;display:flex;flex-direction:column;gap:10px}
.card:hover{border-color:var(--acc);transform:translateY(-2px)}
.card .head{display:flex;gap:12px;align-items:center}
.card img{width:52px;height:52px;border-radius:12px;object-fit:cover;background:var(--chip)}
.card .name{font-size:17px;font-weight:800}
.card .tag{font-size:13px;color:var(--sub)}
.up{color:var(--acc);font-weight:800;font-size:14px;white-space:nowrap}
.row{display:flex;flex-wrap:wrap;gap:6px}
.badge{background:var(--chip);color:var(--sub);border-radius:6px;padding:2px 8px;font-size:12px;font-weight:600}
.badge.price{background:var(--badge);color:var(--acc)}
.desc{font-size:13.5px;color:var(--sub)}
.foot{font-size:12px;color:var(--sub);margin-top:auto}
.note{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-top:14px}
.note h3{font-size:16px;margin-bottom:8px}
.note p{font-size:14px;color:var(--sub)}
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:90;display:none;align-items:flex-start;justify-content:center;padding:4vh 12px}
.modal-bg.open{display:flex}
.modal{background:var(--card);border-radius:16px;max-width:720px;width:100%;max-height:88vh;overflow-y:auto;padding:24px}
.modal h2{font-size:20px;display:flex;align-items:center;gap:12px}
.modal .m-head{display:flex;gap:14px;align-items:center;margin-bottom:12px}
.modal .m-head img{width:64px;height:64px;border-radius:14px;object-fit:cover;background:var(--chip)}
.close{position:sticky;top:0;float:right;background:var(--chip);border:none;color:var(--ink);border-radius:999px;width:32px;height:32px;font-size:16px;cursor:pointer}
.sect{margin-top:18px}
.sect h4{font-size:15px;margin-bottom:8px;color:var(--acc)}
.warn{background:var(--badge);color:var(--acc);border-radius:10px;padding:10px 14px;font-size:13px;margin-top:10px}
.cmt{border-top:1px solid var(--line);padding:12px 0}
.cmt .who{font-weight:700;font-size:13px;display:flex;align-items:center;gap:6px}
.cmt .mk{background:var(--acc);color:#fff;font-size:11px;border-radius:4px;padding:1px 6px;font-weight:700}
.cmt .orig-btn{background:var(--chip);border:none;color:var(--sub);font-size:11px;border-radius:6px;padding:2px 8px;cursor:pointer;margin-left:auto}
.cmt .kr{font-size:14px;margin-top:4px}
.cmt .en{display:none;font-size:13px;color:var(--sub);margin-top:6px;white-space:pre-wrap}
.cmt.show-en .en{display:block}
.orig-all{background:var(--chip);border:none;color:var(--ink);font-size:12px;border-radius:8px;padding:6px 12px;cursor:pointer;font-weight:600}
.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(80px);background:var(--ink);color:var(--bg);padding:10px 20px;border-radius:999px;font-size:13px;transition:.25s;opacity:0;z-index:99}
.toast.show{transform:translateX(-50%);opacity:1}
footer{text-align:center;color:var(--sub);font-size:12px;margin-top:30px}
a{color:var(--acc)}
</style>
</head>
<body>
<a class="topbtn" href="../">☰ 목록</a>
<div class="wrap">
<header>
<h1>🚀 Product Hunt 데일리</h1>
<div class="meta">__DATE__ · Top 5 · 수집 댓글 __CTOT__개 · 수집 __AT__</div>
</header>
<div class="summary" id="summary"></div>
<div class="toolbar" id="toolbar"></div>
<div class="grid" id="grid"></div>
<div id="notables"></div>
<footer>workkrst.github.io/ph-daily · 데이터 출처: Product Hunt · 자동 수집</footer>
</div>
<div class="modal-bg" id="mbg"><div class="modal" id="modal"></div></div>
<div class="toast" id="toast"></div>
<script>
const DATA = __DATA__;
const $=s=>document.querySelector(s);
function toast(m){const t=$('#toast');t.textContent=m;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2200)}
$('#summary').innerHTML='<b>오늘의 요약</b> — '+DATA.summary;
const cats=[...new Set(DATA.products.flatMap(p=>p.categories||[]))];
let state={cat:localStorage.getItem('phd_cat_'+DATA.date)||'전체',sort:localStorage.getItem('phd_sort_'+DATA.date)||'up'};
function renderToolbar(){
 const tb=$('#toolbar');tb.innerHTML='';
 cats.forEach(c=>{const b=document.createElement('button');b.className='chip'+(state.cat===c?' on':'');b.textContent=c;b.onclick=()=>{state.cat=c;localStorage.setItem('phd_cat_'+DATA.date,c);renderToolbar();renderGrid()};tb.appendChild(b)});
 const all=document.createElement('button');all.className='chip'+(state.cat==='전체'?' on':'');all.textContent='전체';all.onclick=()=>{state.cat='전체';localStorage.setItem('phd_cat_'+DATA.date,'전체');renderToolbar();renderGrid()};tb.prepend(all);
 const sp=document.createElement('div');sp.className='spacer';tb.appendChild(sp);
 const su=document.createElement('button');su.className='chip'+(state.sort==='up'?' on':'');su.textContent='업보트순';
 const sn=document.createElement('button');sn.className='chip'+(state.sort==='name'?' on':'');sn.textContent='이름순';
 su.onclick=()=>{state.sort='up';localStorage.setItem('phd_sort_'+DATA.date,'up');renderToolbar();renderGrid()};
 sn.onclick=()=>{state.sort='name';localStorage.setItem('phd_sort_'+DATA.date,'name');renderToolbar();renderGrid()};
 tb.appendChild(su);tb.appendChild(sn);
 const oa=document.createElement('button');oa.className='chip';oa.id='origall';oa.textContent='원문 모두 보기';oa.onclick=()=>{const on=!document.body.classList.contains('en-all');document.body.classList.toggle('en-all',on);document.querySelectorAll('.cmt').forEach(c=>c.classList.toggle('show-en',on));oa.textContent=on?'번역만 보기':'원문 모두 보기'};tb.appendChild(oa);
}
function priceBadge(p){return p.price_model&&p.price_model!=='확인불가'?`<span class="badge price">${p.price_model}${p.price_detail?' · '+p.price_detail:''}</span>`:`<span class="badge price">가격 확인불가</span>`}
function renderGrid(){
 const g=$('#grid');g.innerHTML='';
 let ps=DATA.products.filter(p=>state.cat==='전체'||(p.categories||[]).includes(state.cat));
 ps.sort((a,b)=>state.sort==='up'?(b.upvotes-a.upvotes):a.name.localeCompare(b.name));
 ps.forEach(p=>{
  const c=document.createElement('div');c.className='card';
  c.innerHTML=`<div class="head">${p.image?`<img src="${p.image}" onerror="this.style.visibility='hidden'">`:''}<div style="flex:1"><div class="name">${p.name}</div><div class="tag">${p.tagline_kr||''}</div></div><div class="up">▲ ${p.upvotes}</div></div>
  <div class="row">${(p.categories||[]).slice(0,3).map(x=>`<span class="badge">${x}</span>`).join('')}${priceBadge(p)}</div>
  <div class="desc">${p.desc_kr||''}</div>
  <div class="foot">💬 댓글 ${p.comments?p.comments.length:0}개${p.maker?' · 메이커 '+p.maker:''}</div>`;
  c.onclick=()=>openModal(p);g.appendChild(c);
 });
}
function openModal(p){
 const m=$('#modal');const tot=(p.comments||[]).length;
 m.innerHTML=`<button class="close" onclick="document.getElementById('mbg').classList.remove('open')">✕</button>
 <div class="m-head">${p.image?`<img src="${p.image}" onerror="this.style.visibility='hidden'">`:''}<div><h2>${p.name} <span class="up">▲ ${p.upvotes}</span></h2><div class="tag">${p.tagline_kr||''}${p.tagline_en?' — <span style="opacity:.7">'+p.tagline_en+'</span>':''}</div></div></div>
 <div class="row">${(p.categories||[]).map(x=>`<span class="badge">${x}</span>`).join('')}${priceBadge(p)}</div>
 <div class="sect"><h4>제품 소개</h4><p style="font-size:14px">${p.desc_kr||''}</p>
 <p style="font-size:13px;color:var(--sub);margin-top:6px">메이커: ${p.maker||'확인 불가'} · 가격: ${p.price_model||'확인 불가'}${p.price_detail?' ('+p.price_detail+')':''}</p></div>
 ${(p.comment_summary)?`<div class="sect"><h4>댓글 흐름 한눈에</h4><p style="font-size:14px;color:var(--sub)">${p.comment_summary}</p></div>`:''}
 ${(p.warnings&&p.warnings.length)?`<div class="warn">⚠ ${p.warnings.join('<br>⚠ ')}</div>`:''}
 <div class="sect"><h4>댓글 전문 (${tot}개)</h4><div id="cmts">${(p.comments||[]).map((c,i)=>`<div class="cmt" id="c${i}"><div class="who">${c.author}${c.is_maker?'<span class="mk">메이커</span>':''}<button class="orig-btn" onclick="document.getElementById('c${i}').classList.toggle('show-en')">원문</button></div><div class="kr">${c.kr||''}</div><div class="en">${c.text||''}</div></div>`).join('')||'<p style="color:var(--sub);font-size:13px">수집된 댓글 없음</p>'}</div></div>
 ${p.launch_url_used?`<p style="font-size:11px;color:var(--sub);margin-top:10px">출처: <a href="${p.launch_url_used}" rel="nofollow">${p.launch_url_used}</a></p>`:''}`;
 $('#mbg').classList.add('open');
}
$('#mbg').addEventListener('click',e=>{if(e.target===$('#mbg'))$('#mbg').classList.remove('open')});
(function(){const n=DATA.notable||[];if(!n.length)return;const by=Object.fromEntries(DATA.products.map(p=>[p.slug||p.name,p]));const box=document.createElement('div');box.className='note';box.innerHTML='<h3>⭐ 주목할 만한 제품</h3>'+n.map(nt=>{const p=by[nt.slug]||{};return `<p style="margin-top:8px"><b style="color:var(--ink)">${p.name||nt.slug}</b> — ${nt.why}</p>`}).join('');$('#notables').appendChild(box)})();
renderToolbar();renderGrid();
</script>
</body>
</html>"""

def main():
    if len(sys.argv) < 2:
        print("사용법: python3 build_report.py YYYY-MM-DD", file=sys.stderr); sys.exit(1)
    date = sys.argv[1]
    ddir = BASE / date
    dj = ddir / "data.json"
    data = json.loads(dj.read_text(encoding="utf-8"))
    data.setdefault("date", date)
    ctot = sum(len(p.get("comments", [])) for p in data.get("products", []))
    html = (TEMPLATE
            .replace("__DATA__", json.dumps(data, ensure_ascii=False, indent=1))
            .replace("__DATE__", date)
            .replace("__CTOT__", str(ctot))
            .replace("__AT__", data.get("collected_at", "")))
    out = ddir / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"[ok] {out} 생성 ({len(html)//1024}KB, 댓글 {ctot}개)")

if __name__ == "__main__":
    main()
