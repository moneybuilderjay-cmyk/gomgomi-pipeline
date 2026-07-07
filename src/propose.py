"""주제 후보 생성 + 텔레그램 발송 (2단계 승인의 1단계)"""
import json, os, time, uuid
import approve, state

def generate_candidates(category, headlines, market_ctx):
    """Claude로 후보 3개 생성: [{title, angle, lead_title, lead_desc}]"""
    if os.environ.get("GENERATE_MOCK") == "1":
        return [{"title": f"목업 후보 {i}", "angle": "테스트", "lead_title": f"목업 자료 {i}",
                 "lead_desc": "테스트용"} for i in (1, 2, 3)]
    import anthropic, yaml
    with open(os.path.join(os.path.dirname(__file__), "..", "config.yaml"), encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    system = """너는 '곰곰이의 경제공부' 인스타그램의 콘텐츠 기획자다.
타깃: 재테크를 시작하고 싶은 20~30대 사회초년생. 핵심 가치: '돈 되는 정보'를 쉽게.
주어진 오늘의 카테고리에 맞는 카드뉴스 주제 후보 3개를 제안해라.
각 후보에는 그 주제와 연계된 무료자료(리드마그넷) 아이디어도 포함해라.
반드시 JSON 배열로만 응답: [{"title":"끌리는 제목(질문/숫자형)","angle":"핵심 앵글 1문장","lead_title":"무료자료 이름","lead_desc":"무료자료 내용 1문장"}] × 3개"""
    user = (f"오늘의 카테고리: {category['name']}\n가이드: {category['guide']}\n"
            f"오늘의 경제 헤드라인: {headlines}\n시장 데이터: {market_ctx}")
    client = anthropic.Anthropic()
    resp = client.messages.create(model=cfg["claude"]["model"], max_tokens=2000,
        system=system, messages=[{"role": "user", "content": user}])
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    return json.loads(text)[:3]

def today_kst():
    return time.strftime("%Y-%m-%d", time.gmtime(time.time() + 9 * 3600))

def has_proposal_today():
    q = state._load()
    return any(p.get("date") == today_kst() for p in q.get("proposals", []))

def save_proposal(category, candidates):
    q = state._load()
    q.setdefault("proposals", [])
    prop = {"id": uuid.uuid4().hex[:6], "date": today_kst(),
            "category": category["name"], "pillar": category["pillar"],
            "candidates": candidates, "status": "awaiting_selection"}
    q["proposals"].append(prop)
    state._save(q)
    return prop

def send_candidates(prop):
    lines = [f"🐻 [{prop['date']} · {prop['category']}] 오늘의 주제 후보\n"]
    for i, c in enumerate(prop["candidates"], 1):
        lines.append(f"{i}️⃣ {c['title']}\n   ↳ {c['angle']}\n   🎁 무료자료: {c['lead_title']} — {c['lead_desc']}\n")
    lines.append("번호를 선택하세요. (자료O = 무료자료 CTA 포함 / 자료X = 일반 게시물)")
    kb = {"inline_keyboard": [
        [{"text": f"{i} 자료O", "callback_data": f"sel:{prop['id']}:{i}:1"} for i in (1, 2, 3)],
        [{"text": f"{i} 자료X", "callback_data": f"sel:{prop['id']}:{i}:0"} for i in (1, 2, 3)],
        [{"text": "⏭ 오늘 스킵", "callback_data": f"sel:{prop['id']}:0:0"}],
    ]}
    approve._call("sendMessage", json={"chat_id": os.environ["TELEGRAM_CHAT_ID"],
                                       "text": "\n".join(lines), "reply_markup": kb})
