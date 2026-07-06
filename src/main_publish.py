"""게시 잡: 승인 콜백 반영 → 승인 건 게시"""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(__file__))
import state, approve, publish

def main():
    approve.process_updates()
    approved = state.get_items("approved")
    just_copied = set()
    if not approved:
        print("게시할 승인 건 없음")
        return
    base = os.path.join(os.path.dirname(__file__), "..")
    for item in approved:
        # 이미지를 published/로 복사 (워크플로가 커밋 → raw URL 유효화)
        dest = os.path.join(base, "published", item["id"])
        if not os.path.exists(dest):
            shutil.copytree(item["cards_dir"], dest)
            print(f"{item['id']} → published/ 복사 완료. 커밋 후 다음 실행에서 게시됩니다.")
            state.set_status(item["id"], "hosting")
            just_copied.add(item["id"])
            continue
        media_id = publish.publish_carousel(item, item["n_cards"])
        state.set_status(item["id"], "published")
        approve.notify(f"✅ 게시 완료: {item['topic_title']} (media {media_id})")

    # hosting 상태(이미 커밋된) 건 게시
    for item in state.get_items("hosting"):
        if item["id"] in just_copied:
            continue
        dest = os.path.join(base, "published", item["id"])
        if os.path.exists(dest):
            media_id = publish.publish_carousel(item, item["n_cards"])
            state.set_status(item["id"], "published")
            approve.notify(f"✅ 게시 완료: {item['topic_title']} (media {media_id})")

if __name__ == "__main__":
    main()
