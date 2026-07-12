"""힉스필드 생성 카드 URL 목록(data/cardjobs/*_urls.json)을 다운로드해 out/에 저장.
Cowork(Claude)가 카드 생성 후 _urls.json을 커밋하면, fetch-cards 워크플로가 이 스크립트를 실행한다.
형식: {"item_id": "...", "urls": ["https://...card1", ...]}  (표지→본문→CTA 순서)
"""
import json, os, glob, sys
import requests
import state

BASE = os.path.join(os.path.dirname(__file__), "..")
JOB_DIR = os.path.join(BASE, "data", "cardjobs")

def main():
    done = 0
    for path in sorted(glob.glob(os.path.join(JOB_DIR, "*_urls.json"))):
        with open(path, encoding="utf-8") as f:
            job = json.load(f)
        item_id, urls = job["item_id"], job["urls"]
        items = [i for i in state._load()["items"] if i["id"] == item_id]
        if not items:
            print(f"[fetch] {item_id} 큐에 없음 — 스킵")
            continue
        topic_id = items[0]["topic_id"]
        out_dir = os.path.join(BASE, "out", topic_id)
        os.makedirs(out_dir, exist_ok=True)
        for old in glob.glob(os.path.join(out_dir, "card-*.jpg")):  # 이전 렌더 잔재 제거
            os.remove(old)
        for i, url in enumerate(urls, 1):
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            with open(os.path.join(out_dir, f"card-{i}.jpg"), "wb") as f:
                f.write(r.content)
        q = state._load()
        for it in q["items"]:
            if it["id"] == item_id:
                it["n_cards"] = len(urls)
                it["status"] = "rendered"
        state._save(q)
        os.rename(path, path + ".done")
        print(f"[fetch] {item_id}: {len(urls)}장 저장 → rendered")
        done += 1
    print(f"[fetch] 처리 {done}건")

if __name__ == "__main__":
    main()
