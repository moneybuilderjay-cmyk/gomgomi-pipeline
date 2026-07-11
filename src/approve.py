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
            f"\n\nID: {item['id']}"
            f"\n(버튼이 안 되면 '승인 {item['id']}' 또는 '반려 {item['id']}'라고 답장)")
    _call("sendMessage", json={"chat_id": chat, "text": text, "reply_markup": kb})

def _handle_text(msg, results):
    """텍스트 답장 폴백 — 콜백 버튼은 텔레그램이 짧게만 보관해 폴링 주기상 유실됨.
    선택: "1"~"3"(자료O), "1x"~"3x"(자료X), "스킵"
    승인: "승인" 또는 "승인 <ID>" / 반려: "반려" 또는 "반려 <ID>" (ID 생략 시 최근 대기 건)"""
    import re, state
    txt = (msg.get("text") or "").strip().lower().replace(" ", "")
    if not txt:
        return
    m = re.fullmatch(r"([123])(x)?", txt)
    if m or txt in ("스킵", "skip"):
        q = state._load()
        waiting = [p for p in q.get("proposals", []) if p.get("status") == "awaiting_selection"]
        if not waiting:
            notify("선택 대기 중인 후보가 없어요.")
            return
        p = waiting[-1]  # 가장 최근 제안
        if txt in ("스킵", "skip"):
            p["status"] = "skipped"
            results[f"proposal:{p['id']}"] = "skipped(text)"
        else:
            p["status"] = "selected"
            p["selected"] = int(m.group(1))
            p["lead"] = m.group(2) is None
            results[f"proposal:{p['id']}"] = f"sel {p['selected']} lead={p['lead']} (text)"
        state._save(q)
        notify(f"접수! [{p.get('date','')}] {p['candidates'][p['selected']-1]['title'] if p.get('selected') else '스킵'}"
               if p.get("selected") else "오늘은 스킵할게요.")
        return
    m = re.fullmatch(r"(승인|반려|거절)((20\d{6}-[0-9a-f]{6}))?", txt)
    if m:
        action = m.group(1)
        item_id = m.group(2)
        q = state._load()
        pending = [i for i in q.get("items", []) if i.get("status") == "pending_approval"]
        target = None
        if item_id:
            target = next((i for i in pending if i["id"] == item_id), None)
        elif pending:
            target = pending[-1]
        if not target:
            notify(f"대상을 못 찾았어요. 대기 중: {', '.join(i['id'] for i in pending) or '없음'}\n'승인 <ID>' 형식으로 답장해주세요.")
            return
        status = "approved" if action == "승인" else "rejected"
        state.set_status(target["id"], status)
        results[target["id"]] = f"{status}(text)"
        notify(f"{'✅ 승인' if status == 'approved' else '❌ 반려'} 처리: {target['topic_title']} ({target['id']})")

def process_updates():
    """콜백 수집 → {item_id: 'approved'|'rejected'} 반환"""
    import state
    results = {}
    offset_file = os.path.join(os.path.dirname(__file__), "..", "data", "tg_offset.txt")
    offset = 0
    if os.path.exists(offset_file):
        offset = int(open(offset_file).read().strip() or 0)
    resp = _call("getUpdates", json={"offset": offset + 1, "timeout": 0,
                                     "allowed_updates": ["message", "callback_query"]})
    print(f"[approve] \uc218\uc2e0 \uc5c5\ub370\uc774\ud2b8 {len(resp.get('result', []))}\uac74")
    for upd in resp.get("result", []):
        offset = max(offset, upd["update_id"])
        print(f"[approve] update {upd['update_id']}: keys={list(upd.keys())}")
        msg = upd.get("message")
        if msg and str(msg.get("chat", {}).get("id")) == str(os.environ.get("TELEGRAM_CHAT_ID", "")):
            _handle_text(msg, results)
        cq = upd.get("callback_query")
        if not cq:
            continue
        data = cq.get("data", "")
        if data.startswith("sel:"):
            _, pid, n, lead = data.split(":")
            q = state._load()
            for p in q.get("proposals", []):
                if p["id"] == pid and p["status"] == "awaiting_selection":
                    if n == "0":
                        p["status"] = "skipped"
                    else:
                        p["status"] = "selected"
                        p["selected"] = int(n)
                        p["lead"] = lead == "1"
            state._save(q)
            results[f"proposal:{pid}"] = f"sel {n} lead={lead}"
        elif ":" in data:
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
