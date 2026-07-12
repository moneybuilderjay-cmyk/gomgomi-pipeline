"""Instagram API (Instagram Login) 캐러셀 게시.
- 엔드포인트: graph.instagram.com (Meta 앱 'gomgomi publisher-IG' 토큰 사용)
- 이미지는 GitHub raw URL로 호스팅 (Actions가 published/ 폴더 커밋 후 호출)
"""
import os, time, requests

GRAPH = "https://graph.instagram.com/v21.0"

def _check(r, label=""):
    if not r.ok:
        print(f"[publish] API error {r.status_code} at {label}: {r.text[:800]}")
    r.raise_for_status()

def raw_url(item_id, filename):
    repo = os.environ["GITHUB_REPO"]
    branch = os.environ.get("GITHUB_BRANCH", "main")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/published/{item_id}/{filename}"

def publish_carousel(item, n_cards):
    ig = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    child_ids = []
    for i in range(1, n_cards + 1):
        r = requests.post(f"{GRAPH}/{ig}/media", data={
            "image_url": raw_url(item["id"], f"card-{i}.jpg"),
            "is_carousel_item": "true", "access_token": token}, timeout=60)
        _check(r, f"child {i}")
        child_ids.append(r.json()["id"])
        time.sleep(2)
    r = requests.post(f"{GRAPH}/{ig}/media", data={
        "media_type": "CAROUSEL", "children": ",".join(child_ids),
        "caption": item["caption"], "access_token": token}, timeout=60)
    _check(r, "carousel container")
    creation_id = r.json()["id"]
    s, status = {}, None
    for _ in range(30):
        s = requests.get(f"{GRAPH}/{creation_id}", params={
            "fields": "status_code,status", "access_token": token}, timeout=30).json()
        status = s.get("status_code")
        print(f"[publish] container status: {s}")
        if status in ("FINISHED", "ERROR"):
            break
        time.sleep(5)
    if status != "FINISHED":
        raise RuntimeError(f"container not ready: {s}")
    last = None
    for attempt in range(3):
        r = requests.post(f"{GRAPH}/{ig}/media_publish", data={
            "creation_id": creation_id, "access_token": token}, timeout=60)
        if r.ok:
            return r.json()["id"]
        print(f"[publish] media_publish try {attempt+1} failed {r.status_code}: {r.text[:800]}")
        last = r
        time.sleep(15)
    last.raise_for_status()

def refresh_long_lived_token():
    """IG 장기 토큰(60일) 갱신 — 만료 24시간 전부터 가능, 주기 실행 권장"""
    r = requests.get("https://graph.instagram.com/refresh_access_token", params={
        "grant_type": "ig_refresh_token",
        "access_token": os.environ["IG_ACCESS_TOKEN"]}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

def verify_token():
    """토큰/계정 확인용: 프로필 조회"""
    r = requests.get(f"{GRAPH}/me", params={
        "fields": "user_id,username", "access_token": os.environ["IG_ACCESS_TOKEN"]}, timeout=30)
    r.raise_for_status()
    return r.json()
