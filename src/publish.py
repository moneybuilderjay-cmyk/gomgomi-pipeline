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


def find_recent_by_caption(caption, max_age_h=72, limit=20):
    """최근 게시물에서 같은 캡션의 미디어를 찾는다 — 중복 게시 방지 가드.
    media_publish가 에러(2207085 'Fatal', 403 rate limit 등)를 반환해도
    실제로는 게시가 완료되는 경우가 있다 (2026-07-19 스페이스X 중복 게시 사고).
    따라서 게시 시도 전과 에러 응답 후에 반드시 실게시 여부를 확인한다."""
    ig = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    key = (caption or "").strip()[:80]
    if not key:
        return None
    try:
        r = requests.get(f"{GRAPH}/{ig}/media", params={
            "fields": "id,caption,timestamp", "limit": limit,
            "access_token": token}, timeout=30)
        r.raise_for_status()
        cutoff = time.time() - max_age_h * 3600
        for m in r.json().get("data", []):
            ts = m.get("timestamp")  # 예: 2026-07-19T11:46:00+0000 (UTC, 러너도 UTC)
            try:
                t = time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")) if ts else None
            except Exception:
                t = None
            if t is not None and t < cutoff:
                continue
            if (m.get("caption") or "").strip()[:80] == key:
                return m["id"]
    except Exception as e:
        print(f"[publish] recent-media check 실패(계속): {e}")
    return None


def publish_carousel(item, n_cards):
    ig = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    # 0) 이미 게시된 건인지 먼저 확인 — 이전 실행이 에러로 착각하고
    #    hosting으로 남겨둔 건을 다시 올리는 사고 방지
    dup = find_recent_by_caption(item["caption"])
    if dup:
        print(f"[publish] 이미 게시된 캡션 발견 → 재게시 생략, 성공 처리: media {dup}")
        return dup
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
        try:
            r = requests.post(f"{GRAPH}/{ig}/media_publish", data={
                "creation_id": creation_id, "access_token": token}, timeout=60)
        except requests.RequestException as e:
            # 타임아웃 등 — 실제 게시됐을 수 있으니 아래 dup 체크로 확인
            print(f"[publish] media_publish try {attempt+1} 예외: {e}")
            r = None
        if r is not None and r.ok:
            return r.json()["id"]
        if r is not None:
            print(f"[publish] media_publish try {attempt+1} failed {r.status_code}: {r.text[:800]}")
            last = r
        time.sleep(15)
        # 에러/타임아웃 응답이어도 IG 쪽에서는 게시가 완료됐을 수 있음
        dup = find_recent_by_caption(item["caption"], max_age_h=1)
        if dup:
            print(f"[publish] 에러 응답이지만 실제 게시 확인 → 성공 처리: media {dup}")
            return dup
    if last is not None:
        last.raise_for_status()
    raise RuntimeError("media_publish 실패: 응답 없음(타임아웃 반복), 실게시도 미확인")


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
