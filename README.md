# 곰곰이 인스타그램 자동화 파이프라인 (Phase 1)

주제 백로그 → Claude 생성 → 카드뉴스 렌더링 → Telegram 승인 → Instagram 캐러셀 게시

## 흐름
1. **generate 잡** (매일 06:00 KST): `backlog.yaml`에서 다음 주제 선택 → Claude가 카드 JSON 생성
   → Jinja2+디자인시스템으로 HTML 조립 → Playwright로 1080×1350 JPEG 렌더링 → Telegram으로 승인 요청
2. **Telegram에서 [✅ 승인] 또는 [❌ 반려]** 버튼 클릭
3. **publish 잡** (18:00/18:30 KST): 승인 건 이미지를 `published/`에 커밋(GitHub raw 호스팅) → Graph API로 캐러셀 게시 → 완료 알림

## 로컬 테스트 (API 키 없이)
```bash
pip install -r requirements.txt jinja2 pyyaml
GENERATE_MOCK=1 python src/main_generate.py   # out/t001/ 에 카드 생성
```

## 셋업 체크리스트
- [ ] GitHub 리포 생성 후 이 폴더 push
- [ ] Secrets 등록: ANTHROPIC_API_KEY, IG_USER_ID, IG_ACCESS_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, (META_APP_ID/SECRET)
- [ ] Telegram: @BotFather로 봇 생성 → 봇과 대화 시작 → chat_id 확인
- [x] Meta 앱(gomgomi publisher, ID 1073300481892731) + Instagram 로그인 API 토큰 — 발급 완료
- [ ] Actions 탭에서 generate 수동 실행(workflow_dispatch)으로 첫 테스트

## 구조
```
src/            collect(수집) generate(Claude) render(렌더링) approve(승인) publish(게시) state(큐)
templates/      carousel.html.j2 + design_system.css + mock_content.json
assets/character/  곰곰이 SVG 8종
backlog.yaml    주제 백로그 (소진되면 추가)
data/queue.json 콘텐츠 상태: pending_approval → approved → hosting → published
```

## 주의
- 토큰(60일) 만료 전 갱신: `publish.refresh_long_lived_token()` (graph.instagram.com/refresh_access_token) — Phase 2에서 자동화 예정
- 게시 API: Instagram 로그인 방식(graph.instagram.com), IG_USER_ID=17841445728976310
- 계정당 24시간 50게시 제한 (1일 1포스팅이므로 여유)
- Graph API 스펙은 구현 시점 Meta 문서 기준으로 재확인 (현재 v21.0)
