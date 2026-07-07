"""댓글 키워드 감지 → 무료자료 비공개 답장(Private Reply).
- 최근 게시물 댓글을 폴링해 키워드("곰곰")가 있으면 해당 댓글에 자료 링크를 DM으로 발송
- 같은 댓글에 중복 발송하지 않도록 data/replied.json에 기록
"""
import json, os, requests, yaml

GRAPH = "https://graph.instagram.com/v21.0"
BASE = os.path.join(os.path.dirname(__file__), "..")
REPLIED = os.path.join(BASE, "data", "replied.json")

def _magnets():
    p = os.path.join(BASE, "leadmagnets.yaml")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f).get("magnets", [])

def _raw_url(path):
    repo = os.environ["GITHUB_REPO"]
    branch = os.environ.get("GITHUB_BRANCH", "main")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"

def check_and_reply():
    token = os.environ.get("IG_ACCESS_TOKEN")
    ig = os.environ.get("IG_USER_ID")
    magnets = _magnets()
    if not (token and ig and magnets):
        print("[dm] 설정 없음 — 스킵")
        return
    replied = set()
    if os.path.exists(REPLIED):
        replied = set(json.load(open(REPLIED)))
    # 최근 게시물 5개의 댓글 확인
    r = requests.get(f"{GRAPH}/{ig}/media", params={
        "fields": "id,timestamp", "limit": 5, "access_token": token}, timeout=30)
    r.raise_for_status()
    sent = 0
    for m in r.json().get("data", []):
        try:
            cr = requests.get(f"{GRAPH}/{m['id']}/comments", params={
                "fields": "id,text,username", "limit": 50, "access_token": token}, timeout=30)
            cr.raise_for_status()
            comments = cr.json().get("data", [])
        except Exception as e:
            print(f"[dm] 댓글 조회 실패 {m['id']}: {e}")
            continue
        for c in comments:
            if c["id"] in replied:
                continue
            text = c.get("text", "")
            for mg in magnets:
                if mg["keyword"] in text:
                    msg = f"{mg['message']}\n{_raw_url(mg['file'])}"
                    try:
                        pr = requests.post(f"{GRAPH}/{ig}/messages", json={
                            "recipient": {"comment_id": c["id"]},
                            "message": {"text": msg}},
                            params={"access_token": token}, timeout=30)
                        if not pr.ok:
                            print(f"[dm] 발송 실패 {c['id']}: {pr.status_code} {pr.text[:300]}")
                            continue
                        replied.add(c["id"])
                        sent += 1
                        # 공개 답글로 안내 (best-effort)
                        try:
                            requests.post(f"{GRAPH}/{c['id']}/replies", data={
                                "message": "DM으로 보내드렸어요! 📩🐻",
                                "access_token": token}, timeout=30)
                        except Exception:
                            pass
                    except Exception as e:
                        print(f"[dm] 오류 {c['id']}: {e}")
                    break
    os.makedirs(os.path.dirname(REPLIED), exist_ok=True)
    json.dump(sorted(replied), open(REPLIED, "w"))
    print(f"[dm] 발송 {sent}건, 누적 {len(replied)}건")
