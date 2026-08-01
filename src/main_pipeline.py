"""v2 오케스트레이터 — 매시 실행되며 상태를 전진시킨다.
흐름: 후보 제안(1일 1회) → 사용자가 텔레그램에서 주제+무료자료 여부 선택
     → 카드 생성/렌더 → 텔레그램으로 카드+전체 캡션 전달 (인스타 업로드는 수동)
2026-08-02: 인스타 자동 게시 제거 — 파이프라인의 최종 산출물은 텔레그램 전달까지.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import collect, generate, render, state, approve, propose, market, intelligence, dm, quant

BASE = os.path.join(os.path.dirname(__file__), "..")

# 2026-08-02: 텔레그램 발송 허용 시간대 (KST). 이 밖에는 메시지가 나가는 단계를
# 전부 보류하고 다음 허용 시간대 실행에서 처리한다. GitHub cron 지연으로 실행이
# 새벽(00~02시 KST)까지 밀려 알림이 가던 문제를 크론 조정만으로는 못 막기 때문.
DELIVER_START_KST = 8
DELIVER_END_KST = 22

def kst_hour():
    return int(time.strftime("%H", time.gmtime(time.time() + 9 * 3600)))

def quiet_hours():
    return not (DELIVER_START_KST <= kst_hour() < DELIVER_END_KST)

def weekday_category(cfg):
    wd = int(time.strftime("%w", time.gmtime(time.time() + 9 * 3600)))  # 0=일
    idx = (wd + 6) % 7  # 0=월 로 변환
    return cfg["weekday_categories"][idx]

def main():
    cfg = collect.load_config()
    results = approve.process_updates()
    print(f"[pipeline] 콜백 반영: {results}")

    if quiet_hours():
        print(f"[pipeline] 발송 보류 시간대(KST {kst_hour()}시) — 답장 반영만 하고 종료")
        return

    # 1) 오늘 후보 없으면 제안 발송
    if not propose.has_proposal_today():
        cat = weekday_category(cfg)
        headlines = []
        try:
            headlines = collect.rss_headlines()
        except Exception as e:
            print(f"RSS 실패(계속): {e}")
        ctx = intelligence.collect_signals(cat["pillar"], headlines)
        cands = propose.generate_candidates(cat, headlines, ctx)
        prop = propose.save_proposal(cat, cands)
        propose.send_candidates(prop)
        print(f"[pipeline] 후보 {len(cands)}개 발송 ({cat['name']})")

    # 2) 선택된 후보 → 콘텐츠 생성/렌더/전달 준비
    q = state._load()
    for p in q.get("proposals", []):
        if p.get("status") == "selected":
            cand = p["candidates"][p["selected"] - 1]
            lead = p.get("lead", False)
            cat = {"name": p["category"], "guide": ""}
            headlines = []
            try:
                headlines = collect.rss_headlines()
            except Exception:
                pass
            ctx = intelligence.collect_signals(p.get("pillar", ""), headlines)
            content = generate.generate_content(cand, headlines, lead=lead,
                                                category=cat, market_ctx=ctx)
            caption = content["caption"] + "\n\n" + " ".join(content.get("hashtags", []))
            caption += "\n\n" + cfg["brand"]["disclaimer"]
            out_dir = os.path.join(BASE, "out", p["id"])
            item = state.add_item(p["id"], cand["title"], caption, out_dir, 0)
            # v3 하이브리드: HTML 렌더 대신 카드잡 저장 → Cowork(Claude)가 힉스필드로 카드 생성
            qq = state._load()
            for it in qq["items"]:
                if it["id"] == item["id"]:
                    it["status"] = "awaiting_render"
                    it["lead"] = lead
                    it["lead_title"] = cand.get("lead_title") if lead else None
            state._save(qq)
            import json as _json
            job_dir = os.path.join(BASE, "data", "cardjobs")
            os.makedirs(job_dir, exist_ok=True)
            with open(os.path.join(job_dir, f"{item['id']}.json"), "w", encoding="utf-8") as f:
                _json.dump({"item_id": item["id"], "topic_id": p["id"], "topic_title": cand["title"],
                            "lead": lead, "content": content}, f, ensure_ascii=False, indent=2)
            approve.notify(f"🎨 카피 완성, 카드 생성 대기: {cand['title']}\n다음 카드 배치에서 힉스필드로 제작 후 카드+캡션을 보내드려요.")
            p2 = state._load()
            for pp in p2["proposals"]:
                if pp["id"] == p["id"]:
                    pp["status"] = "generated"
            state._save(p2)
            print(f"[pipeline] 카피 생성 → 카드잡 저장: {cand['title']} (자료 {'O' if lead else 'X'})")

    import glob as _glob

    # 3) 힉스필드 렌더 완료(rendered) 건 → 텔레그램으로 카드+전체 캡션 전달
    # 2026-08-02: 승인/호스팅/게시 단계 제거. 구버전 상태(pending_approval/approved/
    # hosting)로 남아 있던 건도 전체 캡션과 함께 한 번 재전달하고 delivered로 이관.
    for st in ("rendered", "pending_approval", "approved", "hosting"):
        for item in state.get_items(st):
            paths = sorted(_glob.glob(os.path.join(BASE, "out", item["topic_id"], "card-*.jpg")))
            if not paths:
                continue
            approve.send_delivery(item, paths)
            state.set_status(item["id"], "delivered")
            print(f"[pipeline] 카드+캡션 전달: {item['id']} ({len(paths)}장, {st} → delivered)")

    # 4) 화/목/토: HyperPass Quant 종목분석 → 곰곰이 재스킨 (QUANT_FEED_URL 설정 시)
    try:
        quant.maybe_run(cfg)
    except Exception as e:
        print(f"[pipeline] quant 실패(계속): {e}")

    # 5) 댓글 키워드 → 무료자료 비공개 답장
    try:
        dm.check_and_reply()
    except Exception as e:
        print(f"[pipeline] DM 처리 실패(계속): {e}")

if __name__ == "__main__":
    main()
