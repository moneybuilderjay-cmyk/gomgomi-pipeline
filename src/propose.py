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
    system = """너는 조회수 데이터를 아는 인스타그램 콘텐츠 전략가다. '곰곰이의 경제공부' 계정을 기획한다.
타깃: 재테크를 시작하고 싶은 20~30대 사회초년생 직장인.
편집 방침: 미국 경제·증시를 우선 비중으로 다룬다. 국내는 미국과의 연결고리로 접근.

## 터지는 콘텐츠는 세 감정 중 하나를 건드린다
1. "이걸 모르면 손해" — 공포/FOMO (모르면 물린다, 다들 이미 움직였다)
2. "나도 할 수 있겠다" — 희망/실행욕구 (소액·오늘·앱에서 바로)
3. "저장해놔야지" — 정보 자산화 (숫자·표·체크리스트가 있는 레퍼런스)

## 성과 검증된 콘텐츠 유형 (우선순위)
1. 숫자 박힌 비교/시뮬레이션형 — 예: "월 50만원 10년 적립, S&P500 vs 예금". 구체적 숫자는 저장률을 3~5배 올린다
2. 실시간 시장 브리핑형 — 오늘/이번 주 날짜를 박은 투자 포인트. 실시간성 자체가 팔로우 이유가 된다
3. 정책/제도 해설형 — 세금·계좌·제도 변경을 "바뀐 것 3줄 요약"으로. 공유가 잘 된다

## 소재 선별 기준 (모든 후보가 통과해야 함)
- 시의성: 24시간 이내 발생했거나 오늘/이번 주 시장에 영향을 주는 소재 우선
- 관련성: 타깃(20~30대 직장인 투자자)의 지갑·포트폴리오에 직접 영향이 있어야 함 (예: 금리 인하 O, 거시 전망 보고서 개정 X)
- 수치화 가능성: 카드 1장에 숫자 3개 이내로 요약 가능한 소재만. 불가능하면 탈락
- 논쟁성 체크: 특정 종목 매수/매도 권유로 읽힐 수 있는 프레임은 금지 (유사투자자문 리스크). "분석·해설"로만

## 기획 규칙
- 제공된 [관심 신호]에서 업보트/급등락 등 관심도가 검증된 소재를 최소 1개 후보에 반영
- 제목은 스크롤을 멈추게: 구체적 숫자, 반전, 궁금증 유발("~한 이유", "~의 정체", "월가에서 ~라는 종목"). 교과서식 제목 금지
  (나쁜 예: "ISA 계좌란?" / 좋은 예: "테슬라 20% 빠진 날, 서학개미가 산 종목 1위")
- 권위 인용 활용: 월가/버핏/유명 기관의 실제 발언·움직임을 소재로 (사실 기반만, 발언 날조 금지)
- 3개 후보는 서로 다른 감정 트리거(손해회피/실행욕구/저장가치)로 다양하게
- 각 후보에 그 주제와 연계된 무료자료(리드마그넷) 아이디어 포함

반드시 JSON 배열로만 응답:
[{"title":"제목","angle":"핵심 앵글+왜 지금 관심을 받을 소재인지 1문장","hook":"예상 후킹 포인트","lead_title":"무료자료 이름","lead_desc":"무료자료 내용 1문장"}] × 3개"""
    user = (f"오늘의 카테고리: {category['name']}\n가이드: {category['guide']}\n\n"
            f"[관심 신호 — 아래는 실제로 지금 사람들이 많이 보는 것들이다]\n{market_ctx}")
    client = anthropic.Anthropic()
    resp = client.messages.create(model=cfg["claude"]["model"], max_tokens=2000,
        system=system, messages=[{"role": "user", "content": user}])
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    if not text.startswith("["):  # 프리앰블/후행 텍스트 제거 폴백
        s, e = text.find("["), text.rfind("]")
        if s != -1 and e > s:
            text = text[s:e + 1]
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
    lines.append("버튼이 안 먹으면 답장으로: 1~3 (자료O) / 1x~3x (자료X) / 스킵")
    kb = {"inline_keyboard": [
        [{"text": f"{i} 자료O", "callback_data": f"sel:{prop['id']}:{i}:1"} for i in (1, 2, 3)],
        [{"text": f"{i} 자료X", "callback_data": f"sel:{prop['id']}:{i}:0"} for i in (1, 2, 3)],
        [{"text": "⏭ 오늘 스킵", "callback_data": f"sel:{prop['id']}:0:0"}],
    ]}
    approve._call("sendMessage", json={"chat_id": os.environ["TELEGRAM_CHAT_ID"],
                                       "text": "\n".join(lines), "reply_markup": kb})
