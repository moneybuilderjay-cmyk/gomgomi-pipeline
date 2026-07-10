"""v2 오케스트레이터 — 2시간마다 실행되며 상태를 전진시킨다.
흐름: 후보 제안(1일 1회) → 사용자가 텔레그램에서 주제+무료자료 여부 선택
     → 카드 생성/렌더 → 게시 승인 → 호스팅 커밋 → 게시
"""
import os, sys, shutil, time
sys.path.insert(0, os.path.dirname(__file__))
import collect, generate, render, state, approve, propose, publish, market, intelligence, dm, quant

BASE = os.path.join(os.path.dirname(__file__), "..")

def weekday_category(cfg):
    wd = int(time.strftime("%w", time.gmtime(time.time() + 9 * 3600)))  # 0=일
    idx = (wd + 6) % 7  # 0=월 로 변환
    return cfg["weekday_categories"][idx]

def main():
    cfg = collect.load_config()
    results = approve.process_updates()
    print(f"[pipeline] 콜백 반영: {results}")
    q = state._load()

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

    # 2) 선택된 후보 → 콘텐츠 생성/렌더/승인요청
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
            html = render.render_html(content, cfg["brand"])
            paths = render.html_to_jpegs(html, out_dir)
            item = state.add_item(p["id"], cand["title"], caption, out_dir, len(paths))
            # lead 메타 기록
            qq = state._load()
            for it in qq["items"]:
                if it["id"] == item["id"]:
                    it["lead"] = lead
                    it["lead_title"] = cand.get("lead_title") if lead else None
            state._save(qq)
            approve.send_for_approval(item, paths)
            p2 = state._load()
            for pp in p2["proposals"]:
                if pp["id"] == p["id"]:
                    pp["status"] = "generated"
            state._save(p2)
            print(f"[pipeline] 생성+승인요청: {cand['title']} (자료 {'O' if lead else 'X'})")

    # 2.4) 승인 대기 리마인더 — 텔레그램 콜백은 24시간 후 만료되므로 버튼을 주기적으로 재전송
    import glob as _glob
    now = time.time()
    q = state._load()
    changed = False
    for it in q.get("items", []):
        if it["status"] != "pending_approval":
            continue
        last = it.get("resent_ts") or time.mktime(time.strptime(it["created"], "%Y-%m-%d %H:%M:%S"))
        if now - last > 20 * 3600:
            try:
                paths = sorted(_glob.glob(os.path.join(BASE, "out", it["topic_id"], "card-*.jpg")))
                if paths:
                    approve.send_for_approval(it, paths)
                else:
                    approve.notify(f"⏰ 승인 대기 중: {it['topic_title']}\nID: {it['id']} — 다음 실행에서 다시 안내드려요")
                it["resent_ts"] = now
                changed = True
                print(f"[pipeline] 승인 요청 재전송: {it['id']}")
            except Exception as e:
                print(f"[pipeline] 재전송 실패 {it['id']}: {e}")
    if changed:
        state._save(q)

    # 2.5) 화/목/토: HyperPass Quant 종목분석 → 곰곰이 재스킨 (QUANT_FEED_URL 설정 시)
    try:
        quant.maybe_run(cfg)
    except Exception as e:
        print(f"[pipeline] quant 실패(계속): {e}")

    # 3) 승인 건 → published/ 복사 (커밋은 워크플로가)
    just_copied = set()
    for item in state.get_items("approved"):
        dest = os.path.join(BASE, "published", item["id"])
        if not os.path.exists(dest):
            shutil.copytree(item["cards_dir"], dest)
            state.set_status(item["id"], "hosting")
            just_copied.add(item["id"])
            print(f"[pipeline] {item['id']} 호스팅 준비 (다음 실행에서 게시)")

    # 4) 호스팅 완료 건 → 게시
    for item in state.get_items("hosting"):
        if item["id"] in just_copied:
            continue
        if not quant.publish_allowed(item):
            print(f"[pipeline] {item['id']} 퀀트 건 — 19시(KST) 이후 게시 대기")
            continue
        if os.path.exists(os.path.join(BASE, "published", item["id"])):
            media_id = publish.publish_carousel(item, item["n_cards"])
            state.set_status(item["id"], "published")
            approve.notify(f"✅ 게시 완료: {item['topic_title']} (media {media_id})")
            print(f"[pipeline] 게시 완료: {item['topic_title']}")

    # 5) 댓글 키워드 → 무료자료 비공개 답장
    try:
        dm.check_and_reply()
    except Exception as e:
        print(f"[pipeline] DM 처리 실패(계속): {e}")

if __name__ == "__main__":
    main()
