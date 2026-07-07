"""FMP(Financial Modeling Prep) 시장 데이터 — FMP_API_KEY 있을 때만 사용.
Jay의 FMP 대시보드 연동은 추후 확장 (여기서는 직접 API 호출)
"""
import os, requests

BASE = "https://financialmodelingprep.com/api/v3"

def _key():
    return os.environ.get("FMP_API_KEY")

def sector_performance():
    if not _key():
        return None
    try:
        r = requests.get(f"{BASE}/sector-performance", params={"apikey": _key()}, timeout=20)
        r.raise_for_status()
        return r.json()[:11]
    except Exception as e:
        print(f"[market] sector 실패: {e}")
        return None

def earnings_calendar(days=7):
    if not _key():
        return None
    try:
        import datetime
        today = datetime.date.today()
        r = requests.get(f"{BASE}/earning_calendar", params={
            "from": today.isoformat(),
            "to": (today + datetime.timedelta(days=days)).isoformat(),
            "apikey": _key()}, timeout=20)
        r.raise_for_status()
        big = [e for e in r.json() if e.get("symbol") and "." not in e["symbol"]][:15]
        return big
    except Exception as e:
        print(f"[market] earnings 실패: {e}")
        return None

def market_context(pillar):
    """카테고리별로 프롬프트에 넣을 시장 데이터 문자열"""
    parts = []
    if pillar in ("us_calendar", "weekly_wrap"):
        ec = earnings_calendar()
        if ec:
            parts.append("이번 주 실적 발표: " + ", ".join(f"{e['symbol']}({e['date']})" for e in ec[:10]))
    if pillar in ("us_calendar", "us_stock", "weekly_wrap"):
        sp = sector_performance()
        if sp:
            parts.append("섹터 등락: " + ", ".join(f"{s['sector']} {s['changesPercentage']}" for s in sp[:8]))
    return "\n".join(parts) if parts else "(시장 데이터 없음 — 일반 지식으로 작성하되 구체적 수치 단정 금지)"
