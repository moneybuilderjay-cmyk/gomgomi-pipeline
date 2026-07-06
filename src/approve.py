"""Telegram 승인 플로우.
- send_for_approval: 카드 이미지 앨범 + 캡션 + [승인/반려] 버튼 전송
- process_updates: getUpdates 폴링해 콜백 반영 (게시 잡에서 호출)
"""
import os, requests

API = "https://api.telegram.org/bot{token}/{method}"

def _call(method, **kwargs):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    r = requests.post(API.format(token=token, method=method), timeout=30, **kwargs)
    r.raise_for_status()
    return r.json()

def send_for_approval(item, card_paths):
    chat = os.environ["TELEGRAM_CHAT_ID"]
    # 1) 카드 앨범 (최대 10장)
    media, files = [], {}
    for i, p in enumerate(card_paths[:10]):
        key = f"photo{i}"
        files[key] = open(p, "rb")
        media.append({"type": "photo", "media": f"attach://{key}"})
    _call("sendMediaGroup", data={"chat_id": chat, "media": __import__("json").dumps(media)}, files=files)
    # 2) 캡션 + 승인 버튼
    kb = {"inline_keyboard": [[
        {"text": "✅ 승인", "callback_data": f"approve:{item['id']}"},
        {"text": "❌ 반려", "callback_data": f"reject:{item['id']}"},
    ]]}
    text = (f"[승인 요청] {item['topic_title']}\n\n--- 캡션 ---\n{item['caption'][:900]}"
            f"\n\nID: {item['id']}")
    _call("sendMessage", json={"chat_id": chat, "text": text, "reply_markup": kb})

def process_updates():
    """콜백 수집 → {item_id: 'approved'|'rejected'} 반환"""
    import state
    results = {}
    offset_file = os.path.join(os.path.dirname(__file__), "..", "data", "tg_offset.txt")
    offset = 0
    if os.path.exists(offset_file):
        offset = int(open(offset_file).read().strip() or 0)
    resp = _call("getUpdates", json={"offset": offset + 1, "timeout": 0})
    print(f"[approve] \uc218\uc2e0 \uc5c5\ub370\uc774\ud2b8 {len(resp.get('result', []))}\uac74")
    for upd in resp.get("result", []):
        offset = max(offset, upd["update_id"])
        cq = upd.get("callback_query")
        if not cq:
            continue
        data = cq.get("data", "")
        if ":" in data:
            action, item_id = data.split(":", 1)
            status = "approved" if action == "approve" else "rejected"
            state.set_status(item_id, status)
            results[item_id] = status
            try:  # 콜백이 오래되면 400 — 무시
                _call("answerCallbackQuery", json={"callback_query_id": cq["id"],
                      "text": f"{item_id} -> {status}"})
            except Exception:
                pass
    os.makedirs(os.path.dirname(offset_file), exist_ok=True)
    with open(offset_file, "w") as f:
        f.write(str(offset))
    return results

def notify(text):
    _call("sendMessage", json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text})
