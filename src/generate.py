"""Claude로 카드뉴스 콘텐츠(JSON) 생성.
카드 타입: cover, info, table, bignum, checklist, steps, summary, cta
GENERATE_MOCK=1 이면 API 호출 없이 샘플 반환 (파이프라인 테스트용)
"""
import json, os

SYSTEM = """너는 '곰곰이의 경제공부' 인스타그램 계정의 콘텐츠 에디터다.
페르소나: 재테크를 시작하고 싶지만 뭐부터 해야 할지 모르는 20~30대 사회초년생 직장인.
톤: 쉽고 친근하게, 전문용어는 반드시 풀어서. 종목 추천 금지. 수치는 '가정'임을 명시.
반드시 아래 JSON 스키마로만 응답해라 (다른 텍스트 금지):
{
 "kicker": "표지 상단 보조카피 (15자 이내)",
 "title_lines": ["표지", "타이틀", "2~3줄"],
 "hl": "타이틀에서 강조할 단어 (title_lines 중 한 줄에 포함된 단어)",
 "hook": "표지 하단 후킹 문구 (25자 이내)",
 "cards": [
   {"type":"info","kicker":"...","title":"...","hl":"...","heading":"...","paras":["...","..."],"bubble":"곰곰이 말풍선(선택)","pose":"point"},
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
cards는 본문 4~6장. 각 카드 pose는 base/point/think/surprise/happy/save/hello/coin 중 선택.
디스클레이머는 시스템이 자동 추가하므로 쓰지 마라."""

def _mock():
    p = os.path.join(os.path.dirname(__file__), "..", "templates", "mock_content.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def generate_content(topic, headlines):
    if os.environ.get("GENERATE_MOCK") == "1":
        return _mock()
    import anthropic, yaml
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    client = anthropic.Anthropic()
    user = (f"주제: {topic['title']}\n앵글: {topic.get('angle','')}\n"
            f"오늘의 경제 헤드라인(참고, 관련 있을 때만 활용): {headlines}\n"
            f"위 주제로 카드뉴스 JSON을 생성해라.")
    resp = client.messages.create(
        model=cfg["claude"]["model"], max_tokens=cfg["claude"]["max_tokens"],
        system=SYSTEM, messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    data = json.loads(text)
    # 최소 검증
    assert data.get("title_lines") and data.get("cards") and data.get("caption")
    return data
