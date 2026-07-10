"""콘텐츠 JSON → HTML(Jinja2) → 1080x1350 JPEG.
렌더러: Playwright(우선) / WeasyPrint(폴백, 로컬 테스트용)
"""
import os, subprocess
from jinja2 import Environment, FileSystemLoader

BASE = os.path.join(os.path.dirname(__file__), "..")
TPL_DIR = os.path.join(BASE, "templates")
CHAR_DIR = os.path.join(BASE, "assets", "character")

def _load_chars():
    chars = {}
    for f in os.listdir(CHAR_DIR):
        if f.endswith(".svg"):
            pose = f.replace("bear_", "").replace(".svg", "")
            with open(os.path.join(CHAR_DIR, f), encoding="utf-8") as fh:
                chars[pose] = fh.read()
    return chars

def _num_size(s, base, budget=900):
    """초대형 숫자 자동 크기: ASCII 0.62em, 한글/와이드 1.0em 폭 가정"""
    w = sum(0.62 if ord(ch) < 128 else 1.0 for ch in s)
    return int(min(base, budget / max(w, 1)))

def render_html(content, brand):
    env = Environment(loader=FileSystemLoader(TPL_DIR))
    env.globals["num_size"] = _num_size
    with open(os.path.join(TPL_DIR, "design_system.css"), encoding="utf-8") as f:
        css = f.read()
    tpl = env.get_template("carousel.html.j2")
    return tpl.render(c=content, brand=brand, css=css, chars=_load_chars())

def html_to_jpegs(html, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, "carousel.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    try:
        return _render_playwright(html_path, out_dir)
    except Exception as e:
        print(f"[render] playwright 실패({e}) → weasyprint 폴백")
        return _render_weasyprint(html, out_dir)

def _render_playwright(html_path, out_dir):
    from playwright.sync_api import sync_playwright
    paths = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        page.goto("file://" + os.path.abspath(html_path))
        page.wait_for_timeout(500)
        cards = page.locator(".canvas")
        for i in range(cards.count()):
            out = os.path.join(out_dir, f"card-{i+1}.jpg")
            cards.nth(i).screenshot(path=out, quality=92, type="jpeg")
            paths.append(out)
        browser.close()
    return paths

def _render_weasyprint(html, out_dir):
    from weasyprint import HTML, CSS
    pdf = os.path.join(out_dir, "carousel.pdf")
    HTML(string=html, base_url=TPL_DIR).write_pdf(
        pdf, stylesheets=[CSS(string="@page{size:1080px 1350px;margin:0;}")])
    subprocess.run(["pdftoppm", "-png", "-r", "96", pdf,
                    os.path.join(out_dir, "card")], check=True)
    paths = []
    i = 1
    while os.path.exists(os.path.join(out_dir, f"card-{i}.png")):
        png, jpg = os.path.join(out_dir, f"card-{i}.png"), os.path.join(out_dir, f"card-{i}.jpg")
        subprocess.run(["convert", png, "-quality", "92", jpg], check=True)
        try:
            os.remove(png)
        except OSError:
            pass
        paths.append(jpg)
        i += 1
    return paths
