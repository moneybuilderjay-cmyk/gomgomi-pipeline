"""무료자료 마크다운 -> 노션 페이지 생성.
사용: python src/notion_publish.py docs/notion/isa_checklist.md
필요 env: NOTION_TOKEN, NOTION_PARENT_PAGE_ID (공개 페이지의 ID)
부모 페이지가 '웹에 게시' 상태면 생성된 하위 페이지도 같은 공개 링크 체계로 접근 가능.
"""
import os, sys, requests

API = "https://api.notion.com/v1"

def _hdr():
    return {
        "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

def _rich(text):
    return [{"type": "text", "text": {"content": text[:2000]}}]

def md_to_blocks(md):
    blocks, title = [], None
    for raw in md.splitlines():
        line = raw.rstrip()
        s = line.strip()
        if not s:
            continue
        if s.startswith("# ") and title is None:
            title = s[2:].strip()
        elif s.startswith("### "):
            blocks.append({"heading_3": {"rich_text": _rich(s[4:])}})
        elif s.startswith("## "):
            blocks.append({"heading_2": {"rich_text": _rich(s[3:])}})
        elif s.startswith("# "):
            blocks.append({"heading_1": {"rich_text": _rich(s[2:])}})
        elif s.startswith("- [ ] ") or s.startswith("- [x] "):
            blocks.append({"to_do": {"rich_text": _rich(s[6:]), "checked": s[3] == "x"}})
        elif s.startswith("- "):
            blocks.append({"bulleted_list_item": {"rich_text": _rich(s[2:])}})
        elif s.startswith("> "):
            blocks.append({"callout": {"rich_text": _rich(s[2:]), "icon": {"emoji": "🐻"}}})
        elif s == "---":
            blocks.append({"divider": {}})
        else:
            blocks.append({"paragraph": {"rich_text": _rich(s)}})
    out = []
    for b in blocks:
        (k, v), = b.items()
        out.append({"object": "block", "type": k, k: v})
    return title or "무료자료", out

def create_page(title, blocks):
    parent = os.environ["NOTION_PARENT_PAGE_ID"].replace("-", "")
    r = requests.post(f"{API}/pages", headers=_hdr(), json={
        "parent": {"page_id": parent},
        "icon": {"emoji": "🐻"},
        "properties": {"title": {"title": _rich(title)}},
        "children": blocks[:100],
    }, timeout=60)
    if not r.ok:
        print(f"[notion] 실패 {r.status_code}: {r.text[:500]}")
    r.raise_for_status()
    d = r.json()
    return d["url"], d["public_url"]

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "docs/notion/isa_checklist.md"
    with open(path, encoding="utf-8") as f:
        md = f.read()
    title, blocks = md_to_blocks(md)
    url, public_url = create_page(title, blocks)
    print(f"[notion] 페이지 생성 완료: {title}")
    print(f"[notion] 내부 URL: {url}")
    print(f"[notion] 공개 URL: {public_url}")
