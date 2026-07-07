"""콘텐츠 인텔리전스 — '사람들이 실제로 많이 보는 것'을 신호로 수집.
소스: ①국내외 주요 경제 RSS ②Reddit 투자 서브레딧 상위글(관심도=업보트)
     ③FMP 급등/급락/거래대금 상위(시장의 실제 관심) ④실적 캘린더
"""
import os, requests
import market

UA = {"User-Agent": "gomgomi-pipeline/1.0"}

GLOBAL_FEEDS = [
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",   # CNBC Top
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",  # MarketWatch
    "https://finance.yahoo.com/news/rssindex",
]
REDDIT_SUBS = ["stocks", "investing", "wallstreetbets"]

def rss_titles(urls, limit=6):
    import feedparser
    out = []
    for u in urls:
        try:
            f = feedparser.parse(u)
            out += [e.title for e in f.entries[:limit]]
        except Exception:
            continue
    return out

def reddit_top(limit=8):
    """업보트 상위 = 실제 관심도 신호"""
    out = []
    for sub in REDDIT_SUBS:
        try:
            r = requests.get(f"https://www.reddit.com/r/{sub}/top.json",
                             params={"t": "day", "limit": limit}, headers=UA, timeout=15)
            r.raise_for_status()
            for p in r.json()["data"]["children"]:
                d = p["data"]
                out.append(f"[r/{sub} ▲{d['ups']}] {d['title']}")
        except Exception as e:
            print(f"[intel] reddit/{sub} 실패: {e}")
    out.sort(key=lambda s: -int(s.split("▲")[1].split("]")[0]) if "▲" in s else 0)
    return out[:12]

def fmp_movers():
    """급등/급락/거래대금 상위 — 시장이 지금 주목하는 종목"""
    key = os.environ.get("FMP_API_KEY")
    if not key:
        return []
    out = []
    for kind, label in [("gainers", "급등"), ("losers", "급락"), ("actives", "거래상위")]:
        try:
            r = requests.get(f"https://financialmodelingprep.com/api/v3/stock_market/{kind}",
                             params={"apikey": key}, timeout=15)
            r.raise_for_status()
            top = r.json()[:5]
            out.append(label + ": " + ", ".join(
                f"{s['symbol']} {s.get('changesPercentage', 0):.1f}%" for s in top))
        except Exception as e:
            print(f"[intel] fmp/{kind} 실패: {e}")
    return out

def collect_signals(pillar, kr_headlines):
    """카테고리별 신호 묶음 → 기획 프롬프트 입력용 텍스트.
    미국 신호를 앞에 배치 (편집 방침: 미국 경제·증시 우선)"""
    parts = []
    glob = rss_titles(GLOBAL_FEEDS)
    if glob:
        parts.append("[미국/해외 주요 뉴스]\n" + "\n".join(glob[:8]))
    movers = fmp_movers()
    if movers:
        parts.append("[오늘 미국시장이 주목한 종목]\n" + "\n".join(movers))
    red = reddit_top()
    if red:
        parts.append("[미국 투자 커뮤니티 관심 상위(업보트순)]\n" + "\n".join(red))
    mc = market.market_context(pillar)
    if mc and "없음" not in mc:
        parts.append("[시장 데이터]\n" + mc)
    if kr_headlines:
        parts.append("[국내 헤드라인(보조)]\n" + "\n".join(kr_headlines[:8]))
    return "\n\n".join(parts) if parts else "(신호 없음)"
