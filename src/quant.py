"""HyperPass Quant 대시보드 → 곰곰이 재스킨 종목분석 카드 (화/목/토 저녁 발행)

QUANT_FEED_URL(JSON)에서 '오늘의 종목' 분석을 받아 곰곰이 디자인으로 5카드 재구성.
승인 플로우는 기존과 동일, 게시만 19시(KST) 이후로 지연 → 본편성과 시간대 분리.

기대 JSON (오늘의 종목 1개, 리스트면 첫 번째 사용):
{
 "date": "2026-07-07", "week": 138,
 "ticker": "ORCL", "name_kr": "오라클", "sector": "IT",
 "tagline": "DB 제왕에서 AI 클라우드로 변신 중",
 "biz_points": ["기업 DB와 클라우드(OCI), AI 데이터센터 임대", "...", "..."],
 "metrics": {"eps_growth": 21.6, "rev_growth": 31.6, "eps_revision": "B", "roa": 6.6},
 "sector_comp": {"roa": [6.6, 3.3], "op_margin": [32.2, 7.4],
                 "verdict": "섹터 평균 수준 — 품질 보정 중립", "peers": ["SNAP","NVDA"]},
 "valuation": {"price": 143.8, "fair": 266.8, "fair_pe": 253.2, "fair_ps": 280.5,
               "pct_of_fair": 54, "upside": 85.6, "off_high": -58.4,
               "eps_delta_wk": 0.1, "label": "저평가 구간"},
 "summary3": ["...", "...", "..."],
 "watch_next": ["EPS 리비전 등급 유지 여부", "...", "..."],
 "performance": {"weeks": 137, "cum_return": 248.0,
                 "benchmark": "나스닥", "bench_return": 101.2}   # 모의투자 누적 (선택)
}
"""
import os, time
import requests
import render, state, approve

BASE = os.path.join(os.path.dirname(__file__), "..")
QUANT_WEEKDAYS = (1, 3, 5)   # 화/목/토 (0=월)
PUBLISH_AFTER_KST = 19       # 본편성과 시간대 분리

def _kst(fmt):
    return time.strftime(fmt, time.gmtime(time.time() + 9 * 3600))

def fetch_today(url):
    headers = {}
    key = os.environ.get("QUANT_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    d = r.json()
    if isinstance(d, list):
        d = d[0]
    return d

def build_content(d):
    """대시보드 JSON → 곰곰이 카드 스키마 (기존 carousel.html.j2 재사용)"""
    m = d.get("metrics", {})
    sc = d.get("sector_comp", {})
    v = d.get("valuation", {})
    tk, nm = d.get("ticker", ""), d.get("name_kr", "")
    paras = list(d.get("biz_points", []))[:3]
    if m:
        paras.append(f"EPS 성장 전망 <b>{m.get('eps_growth','-')}%</b> · "
                     f"매출 성장 전망 <b>{m.get('rev_growth','-')}%</b> · "
                     f"EPS 리비전 <b>{m.get('eps_revision','-')}</b>")
    rows = []
    if sc.get("roa"):
        rows.append(["수익성 ROA", f"{sc['roa'][0]}%", f"{sc['roa'][1]}%"])
    if sc.get("op_margin"):
        rows.append(["영업이익률", f"{sc['op_margin'][0]}%", f"{sc['op_margin'][1]}%"])
    if sc.get("verdict"):
        rows.append(["종합", sc["verdict"], ""])
    cards = [
        {"type": "info", "kicker": "STEP 1 · 종목 분석", "title": "뭐 하는 회사인가",
         "hl": "회사", "paras": paras, "pose": "point",
         "bubble": f"{nm}, 곰곰이랑 뜯어보자!"},
        {"type": "table", "kicker": "STEP 2 · 섹터 분석",
         "title": f"{d.get('sector','섹터')} 섹터 속 위치", "hl": "위치",
         "headers": ["", tk, "섹터 평균"], "rows": rows, "win_col": 1, "pose": "think"},
        {"type": "bignum", "kicker": "STEP 3 · 주가 분석", "title": "그래서 지금 가격은",
         "hl": "가격", "label": f"현재가 ${v.get('price','-')} · 모델 적정주가 ${v.get('fair','-')}",
         "num": f"{v.get('pct_of_fair','-')}%",
         "sub": f"모델 적정주가 대비 현재가 수준 · 52주 고점 대비 {v.get('off_high','-')}%"
                f"<br>※ 성장률 추정이 빗나가면 적정주가도 함께 틀립니다",
         "pose": "surprise"},
        {"type": "checklist", "kicker": "다음 주에 볼 것", "title": "관찰 포인트",
         "hl": "관찰", "items": d.get("watch_next", [])[:4], "pose": "save"},
    ]
    perf = d.get("performance", {})
    if perf.get("cum_return") is not None:
        cards.append(
            {"type": "table", "kicker": "이 방식의 기록", "title": "모의투자 누적 성과",
             "hl": "누적 성과",
             "headers": ["", "이 전략", perf.get("benchmark", "벤치마크")],
             "rows": [[f"{perf.get('weeks','-')}주 누적",
                       f"+{perf['cum_return']}%",
                       f"+{perf.get('bench_return','-')}%"],
                      ["", "모의투자 기록", "같은 기간"]],
             "win_col": 1, "pose": "happy",
             "bubble": "꾸준함이 답이야!"})
    cards += [
        {"type": "summary", "kicker": "오늘의 기록", "title": "세 줄 요약",
         "hl": "요약", "items": d.get("summary3", [])[:3], "pose": "base"},
    ]
    cards = [c for c in cards if c.get("paras") or c.get("rows") or c.get("items") or c["type"] == "bignum"]
    caption = (f"[종목 기록] {nm} ({tk}) — {d.get('tagline','')}\n\n"
               f"매주 화·목·토, 데이터로 미국 종목 하나씩 기록합니다.\n"
               f"저장해두고 다음 주와 비교해보세요 🐻\n\n"
               f"※ 개인 기록·교육 목적이며 매수/매도 추천이 아닙니다. 투자 판단과 책임은 본인에게 있습니다.")
    tags = ["#미국주식", "#해외주식", f"#{nm}", f"#{tk}", "#주식공부", "#종목분석",
            "#재테크", "#서학개미", "#경제공부", "#곰곰이"]
    return {
        "kicker": f"오늘의 종목 · {d.get('date', _kst('%Y-%m-%d'))}",
        "title_lines": [nm, tk], "hl": tk,
        "hook": f"\"{d.get('tagline','')}\"",
        "cards": cards,
        "cta": {"gift": None, "how": "매주 화·목·토, 같은 방식으로 기록해요"},
        "caption": caption, "hashtags": tags,
    }

def maybe_run(cfg):
    """화/목/토 KST, 피드 URL이 설정돼 있고 오늘 건이 없으면 생성→승인요청"""
    url = os.environ.get("QUANT_FEED_URL")
    if not url:
        return
    wd = (int(_kst("%w")) + 6) % 7  # 0=월
    if wd not in QUANT_WEEKDAYS:
        return
    today = _kst("%Y%m%d")
    topic_id = f"quant-{today}"
    if any(it["topic_id"] == topic_id for it in state._load()["items"]):
        return
    d = fetch_today(url)
    content = build_content(d)
    caption = content["caption"] + "\n\n" + " ".join(content["hashtags"])
    caption += "\n\n" + cfg["brand"]["disclaimer"]
    out_dir = os.path.join(BASE, "out", topic_id)
    html = render.render_html(content, cfg["brand"])
    paths = render.html_to_jpegs(html, out_dir)
    item = state.add_item(topic_id, f"[종목] {content['title_lines'][0]} {content['title_lines'][1]}",
                          caption, out_dir, len(paths))
    q = state._load()
    for it in q["items"]:
        if it["id"] == item["id"]:
            it["quant"] = True
    state._save(q)
    approve.send_for_approval(item, paths)
    print(f"[quant] 생성+승인요청: {content['title_lines']}")

def publish_allowed(item):
    """퀀트 건은 19시(KST) 이후에만 게시 — 본편성과 시간대 분리"""
    if not item.get("quant"):
        return True
    return int(_kst("%H")) >= PUBLISH_AFTER_KST
