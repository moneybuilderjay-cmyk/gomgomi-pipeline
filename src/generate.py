"""Claude로 카드뉴스 콘텐츠(JSON) 생성.
카드 타입: cover, info, table, bignum, checklist, steps, summary, cta
GENERATE_MOCK=1 이면 API 호출 없이 샘플 반환 (파이프라인 테스트용)
"""
import json, os

SYSTEM = """너는 저장수 높은 카드뉴스를 만드는 콘텐츠 에디터다. '곰곰이의 경제공부' 계정을 만든다.
페르소나: 재테크를 시작하고 싶지만 뭐부터 해야 할지 모르는 20~30대 사회초년생 직장인.

## 매력적인 카드뉴스 원칙 (반드시)
- 팔로워 성장은 저장수·공유수가 결정한다. 모든 게시물의 목표는 "저장해놔야지"라는 반응
- 표지: 구체적 숫자/반전/궁금증으로 3초 안에 멈추게. 교과서식 제목 금지
  · 제목 공식: [구체적 사건/숫자] + [나와의 관계 또는 반전]. 궁금증이 남아야 넘긴다
  · 좋은 예: "메타 20% 오른 날, 조용히 빠진 종목들" / "나스닥 신고가에 웃지 못한 사람들" / "월가가 말 안 해주는 3배 ETF 계산법"
  · 나쁜 예: "메타가 쏘아올린 신호" (모호함), "AI 밸류체인 분석" (교과서)
- 2번 카드: 표지의 궁금증에 바로 답하지 말고 공감/상황 제시로 끌어들이기 (스토리 아크)
- 모든 본문 카드에 구체적 숫자·실제 사례·비유 중 최소 1개. 뻔한 원론 설명만 있는 카드 금지
- 숫자 비교/시뮬레이션(table·bignum 카드)을 적극 활용 — 구체적 숫자는 저장률을 3~5배 올린다
- 제도/정책 소재면 "바뀐 것 3줄 요약" 카드(checklist)를 반드시 포함 — 공유 유발
- 실시간 소재면 날짜를 카드에 명시 (예: "7월 7일 기준") — 실시간성이 팔로우 이유
- 문장은 짧게. 한 카드에 하나의 메시지만

## 표지 레이아웃 선택 (cover_layout — 천편일률 금지)
- "bignum": 충격적 숫자 하나가 주인공일 때 (색 반전 오렌지 배경 + 초대형 숫자)
- "chat": 잘못된 통념을 반박하는 소재일 때 (곰곰이 질문 ↔ 계정 반박 채팅 UI)
- "character": 감정·상황 공감형 소재일 때 (곰곰이 크게 + 통념 질문 말풍선)
- 소재 성격에 맞게 고르되 같은 레이아웃만 반복하지 마라

## 티키타카 (곰곰이 = 독자의 목소리)
- 곰곰이가 독자처럼 묻고(q), 카드 본문이 답/반박하고, 곰곰이가 깨닫는다(bubble)
- 모든 본문 카드에 q(상단 질문 말풍선) 또는 bubble(하단 깨달음 말풍선) 중 1개 이상 — 예외 없음, 둘 다 있으면 더 좋다
- q는 친근한 반말 질문 (예: "제자리인데 왜 손해야?"), bubble은 깨달음/리액션 (예: "왕복 요금이 있었구나…")
- 표지의 cover_bubble은 잘못된 통념 질문, cover_teaser는 그걸 받아치는 반박 티저

## 줄바꿈 규칙 (어기면 렌더가 깨진다 — 반드시)
- title_lines: 각 줄 8자 이내(공백 포함), 각 줄이 의미 단위로 완결
- 카드 title: 12자 이내 / kicker: 15자 이내
- paras: 문장을 22자 이내 의미 단위로 <br> 줄바꿈, 어절 중간에서 끊지 마라
- q·cover_bubble·bubble: 14자 이내면 줄바꿈 없이 한 줄, 넘으면 <br>로 의미 단위 분할
- 카드 색 변주: 게시물당 invert(색 반전) 또는 fullbleed_num 카드를 1~2장 섞어라
- 실제 데이터가 제공되면 그 수치를 사용, 없으면 수치를 지어내지 말고 '가정' 명시
- 톤: 쉽고 친근하게, 전문용어는 반드시 풀어서. 종목 추천 금지.

## 카피 스타일 (어기면 AI 티가 난다 — 반드시)
- 사람이 친구에게 말하듯: 입으로 소리내 읽었을 때 자연스러워야 한다
- 금지: 번역투("~에 있어서", "~함에 따라"), 이중부정("늦지 않았어요"), 모호한 시적 표현("쏘아올린 신호", "~의 방정식")
- 금지: 신문·리포트 축약체 어휘. 일상 대화에서 안 쓰는 말은 전부 바꿔라
  · 직전주→지난주 / 금주→이번 주 / 익일·익월→다음 날·다음 달 / 동 기간→같은 기간 / 낙폭 확대→더 크게 떨어짐 / 상회·하회→넘음·밑돎 / 전일 대비→어제보다 / 매수세 유입→사는 사람이 몰림
  · 판별법: 친구한테 카톡으로 보낼 때 안 쓸 단어면 금지
- 금지: 실체 없는 추상 문구. 모든 문장에 구체적 대상·숫자·행동이 있어야 한다
- 나쁜 예: "그 신호, 이미 늦지 않았어요" → 좋은 예: "지금 봐도 안 늦었어요" 또는 "아직 기회 있어요"
- 나쁜 예: "AI 밸류체인 전체가 같이 흔들렸어요" → 좋은 예: "반도체부터 소프트웨어까지 다 움직였어요"
- 곰곰이 말풍선은 진짜 초보의 말: "어? 나만 몰랐어?", "그래서 사라는 거야 말라는 거야?"

## 콘텐츠 밀도 (빈약한 카드 금지)
- table: 최소 4행 / checklist·steps·summary: 최소 3개 항목, 각 항목 15자 이상
- info·invert: paras 2개 이상, 합쳐서 3문장 이상
- 채울 내용이 부족한 카드는 아예 만들지 말고 다른 타입으로 대체
반드시 아래 JSON 스키마로만 응답해라 (다른 텍스트 금지):
{
 "kicker": "표지 상단 보조카피 (15자 이내)",
 "title_lines": ["표지", "타이틀", "2~3줄"],
 "hl": "타이틀에서 강조할 단어 (title_lines 중 한 줄에 포함된 단어)",
 "hook": "표지 하단 후킹 문구 (25자 이내)",
 "cover_layout": "character | bignum | chat 중 택1",
 "cover_pose": "표지 곰곰이 포즈 (character·bignum일 때)",
 "cover_bubble": "표지 곰곰이 말풍선 — 잘못된 통념 질문 (character·bignum일 때)",
 "cover_teaser": "푸터 오른쪽 반박 티저 (예: 그 계산, 절반만 맞아요 →)",
 "cover_label": "bignum 전용: 숫자 위 라벨 (14자 이내)",
 "cover_num": "bignum 전용: 초대형 숫자, %포함 5자 이내 (예: −79%)",
 "cover_sub": "bignum 전용: 숫자 아래 문구 (16자 이내, <b>강조</b> 가능)",
 "cover_chat": [{"who":"bear","pose":"think","text":"통념 질문"},{"who":"me","text":"반박 (<b>강조</b> 가능)"},{"who":"bear","pose":"surprise","text":"리액션"}] — chat 전용, 정확히 3개, 각 말풍선 2줄(<br> 1개) 이하. chat이면 title_lines는 2줄 이하 권장,
 "cards": [
   {"type":"info","kicker":"...","title":"...","hl":"...","heading":"...","paras":["...","..."],"q":"곰곰이 질문(선택, kicker 대체)","q_pose":"think","bubble":"곰곰이 말풍선(선택)","pose":"point"},
   {"type":"invert","kicker":"...","title":"...","hl":"...","heading":"...","paras":["..."],"q":"...","bubble":"...","pose":"base"},
   {"type":"fullbleed_num","kicker":"...","title":"...","hl":"...","label":"숫자 위 라벨","num":"−9%","sub":"숫자 아래 문구","q":"...","bubble":"...","pose":"surprise"},
   {"type":"table","kicker":"...","title":"...","hl":"...","headers":["","A","B"],"rows":[["행이름","값","값(win)"]],"win_col":2,"pose":"think"},
   {"type":"bignum","kicker":"...","title":"...","hl":"...","label":"...","num":"...","sub":"...","bubble":"...","pose":"surprise"},
   {"type":"checklist","kicker":"...","title":"...","hl":"...","items":["...","..."],"pose":"base"},
   {"type":"steps","kicker":"...","title":"...","hl":"...","steps":["1단계 내용","2단계","3단계"],"pose":"hello"},
   {"type":"summary","kicker":"오늘의 핵심","title":"이것만 기억하세요","hl":"기억하세요","items":["...","...","..."],"pose":"save"}
 ],
 "cta": {"gift":"무료자료 이름","how":"댓글에 \\"곰곰\\"이라고 남겨주세요"},
 "caption": "첫 줄 후킹\\n\\n본문 요약 3~4줄\\n\\n저장/댓글 CTA",
 "hashtags": ["#재테크", "... 15~20개"]
}
cards는 본문 4~6장. 각 카드 pose는 base/point/think/surprise/happy/save/hello/coin 중 선택. q는 모든 카드 타입에서 선택 사용 가능(있으면 kicker 대신 질문 말풍선 렌더).
디스클레이머는 시스템이 자동 추가하므로 쓰지 마라."""

def _mock():
    p = os.path.join(os.path.dirname(__file__), "..", "templates", "mock_content.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def generate_content(topic, headlines, lead=True, category=None, market_ctx=""):
    if os.environ.get("GENERATE_MOCK") == "1":
        return _mock()
    import anthropic, yaml
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    client = anthropic.Anthropic()
    lead_inst = ("cta.gift에는 이 무료자료를 사용: " + topic.get("lead_title", "")
                 if lead else
                 "이번 게시물은 무료자료 배포 없음. cta는 {\"gift\": null, \"how\": \"팔로우하고 매일 1장씩 받아보세요\"} 형태로.")
    cat_inst = f"오늘의 카테고리: {category['name']} — {category['guide']}" if category else ""
    user = (f"{cat_inst}\n주제: {topic['title']}\n앵글: {topic.get('angle','')}\n"
            f"오늘의 경제 헤드라인(참고, 관련 있을 때만 활용): {headlines}\n"
            f"시장 데이터(있으면 수치 활용, 없으면 수치 단정 금지): {market_ctx}\n"
            f"{lead_inst}\n위 주제로 카드뉴스 JSON을 생성해라.")
    def _call_json(extra=""):
        # sonnet-5는 assistant 프리필 미지원 → 강건한 추출 + 진단 로그
        import re
        resp = client.messages.create(
            model=cfg["claude"]["model"], max_tokens=cfg["claude"]["max_tokens"],
            system=SYSTEM, messages=[{"role": "user", "content": user + extra}],
        )
        t = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        print(f"[generate] stop={resp.stop_reason} len={len(t)} head={t[:120]!r}")
        t = re.sub(r"```(?:json)?", "", t)
        s, e = t.find("{"), t.rfind("}")
        if s != -1 and e > s:
            t = t[s:e + 1]
        return t

    text = _call_json()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        print(f"[generate] 1차 파싱 실패({err}) tail={text[-150:]!r} — 재시도")
        text = _call_json("\n\n(중요: 반드시 '{'로 시작하는 순수 JSON만 출력해라. 설명 문장·코드펜스 금지)")
        data = json.loads(text)
    # 최소 검증
    assert data.get("title_lines") and data.get("cards") and data.get("caption")
    return data
