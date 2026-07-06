"""소재 수집: 주제 백로그 + RSS 헤드라인(맥락용)"""
import os, yaml, feedparser

BASE = os.path.join(os.path.dirname(__file__), "..")

def load_config():
    with open(os.path.join(BASE, "config.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)

def next_topic():
    """backlog에서 done 아닌 첫 주제 반환"""
    path = os.path.join(BASE, "backlog.yaml")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for t in data["topics"]:
        if not t.get("done"):
            return t
    return None

def mark_topic_done(topic_id):
    path = os.path.join(BASE, "backlog.yaml")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for t in data["topics"]:
        if t["id"] == topic_id:
            t["done"] = True
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)

def rss_headlines(limit=10):
    """오늘의 경제 헤드라인 — 생성 프롬프트에 맥락으로 주입"""
    cfg = load_config()
    heads = []
    for url in cfg.get("feeds", []):
        try:
            feed = feedparser.parse(url)
            heads += [e.title for e in feed.entries[:5]]
        except Exception:
            continue
    return heads[:limit]
