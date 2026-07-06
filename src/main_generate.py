"""생성 잡: 주제 선택 → 생성 → 렌더링 → 승인 요청"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import collect, generate, render, state

def main():
    cfg = collect.load_config()
    topic = collect.next_topic()
    if not topic:
        print("백로그 소진 — 주제를 추가하세요")
        return
    headlines = []
    try:
        headlines = collect.rss_headlines()
    except Exception as e:
        print(f"RSS 수집 실패(계속 진행): {e}")
    print(f"주제: {topic['title']}")
    content = generate.generate_content(topic, headlines)
    caption = content["caption"] + "\n\n" + " ".join(content.get("hashtags", []))
    caption += "\n\n" + cfg["brand"]["disclaimer"]
    out_dir = os.path.join(os.path.dirname(__file__), "..", "out", topic["id"])
    html = render.render_html(content, cfg["brand"])
    paths = render.html_to_jpegs(html, out_dir)
    print(f"렌더링 완료: {len(paths)}장 → {out_dir}")
    item = state.add_item(topic["id"], topic["title"], caption, out_dir, len(paths))
    if os.environ.get("TELEGRAM_BOT_TOKEN"):
        import approve
        approve.send_for_approval(item, paths)
        print("Telegram 승인 요청 발송")
    else:
        print("TELEGRAM_BOT_TOKEN 없음 — 승인 요청 스킵 (로컬 테스트)")
    collect.mark_topic_done(topic["id"])

if __name__ == "__main__":
    main()
