"""콘텐츠 큐/이력 관리 — queue.json 하나로 단순하게"""
import json, os, time, uuid

QUEUE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "queue.json")

def _load():
    if not os.path.exists(QUEUE_PATH):
        return {"items": []}
    with open(QUEUE_PATH, encoding="utf-8") as f:
        return json.load(f)

def _save(q):
    os.makedirs(os.path.dirname(QUEUE_PATH), exist_ok=True)
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)

def add_item(topic_id, topic_title, caption, cards_dir, n_cards):
    q = _load()
    item = {
        "id": f"{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}",
        "topic_id": topic_id, "topic_title": topic_title,
        "caption": caption, "cards_dir": cards_dir, "n_cards": n_cards,
        "status": "pending_approval",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    q["items"].append(item)
    _save(q)
    return item

def set_status(item_id, status):
    q = _load()
    for it in q["items"]:
        if it["id"] == item_id:
            it["status"] = status
    _save(q)

def get_items(status=None):
    q = _load()
    return [it for it in q["items"] if status is None or it["status"] == status]

def published_topic_ids():
    return {it["topic_id"] for it in _load()["items"] if it["status"] == "published"}
