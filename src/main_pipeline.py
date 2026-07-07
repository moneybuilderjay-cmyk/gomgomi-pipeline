"""v2 오케스트레이터 — 2시간마다 실행되며 상태를 전진시킨다.
흐름: 후보 제안(1일 1회) → 사용자가 텔레그램에서 주제+무료자료 여부 선택
     → 카드 생성/렌더 → 게시 승인 → 호스팅 커밋 → 게시
"""
import os, sys, shutil, time
sys.path.insert(0, os.path.dirname(__file__))
import collect, generate, render, state, approve, propose, publish, market

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
        ctx = market.market_context(cat["pillar"])
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
            ctx = market.market_context(p.get("pillar", ""))
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
        if os.path.exists(os.path.join(BASE, "published", item["id"])):
            media_id = publish.publish_carousel(item, item["n_cards"])
            state.set_status(item["id"], "published")
            approve.notify(f"✅ 게시 완료: {item['topic_title']} (media {media_id})")
            print(f"[pipeline] 게시 완료: {item['topic_title']}")

if __name__ == "__main__":
    main()
