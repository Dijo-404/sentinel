"""Optional Playwright sandbox smoke runner. Never persists session credentials."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright

parser = argparse.ArgumentParser(
    description="Read-only six-role Playwright navigation and responsive smoke checks."
)
parser.add_argument("--base-url", required=True)
parser.add_argument("--output-dir", required=True, type=Path)
parser.add_argument("--browser-executable")
args = parser.parse_args()
BASE = args.base_url.rstrip("/")
OUT = args.output_dir
OUT.mkdir(parents=True, exist_ok=True)
APP = Path(__file__).resolve().parents[1]
ROLES = ["customer", "merchant", "operator", "supervisor", "risk", "admin"]


async def audit(browser, role):
    ctx = await browser.new_context(viewport={"width": 1440, "height": 1000})
    page = await ctx.new_page()
    page.set_default_timeout(10000)
    errors = []
    bad = []
    rows = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on(
        "response",
        lambda r: (
            bad.append({"url": r.url.split("?")[0], "status": r.status})
            if r.status >= 400
            else None
        ),
    )
    try:
        await page.goto(BASE + "/login")
        await page.get_by_test_id("login-email").fill(role + "@example.test")
        await page.get_by_test_id("login-password").fill("demo-password")
        await page.get_by_test_id("login-submit").click()
        await page.wait_for_url("**/" + role + "/dashboard", timeout=30000)
        print(role, "LOGIN PASS", flush=True)
        nav = await page.locator("aside nav a").evaluate_all(
            '(els)=>els.map(e=>({href:e.getAttribute("href"),label:e.innerText}))'
        )
        routes = [n["href"] for n in nav]
        routes += [
            "/"
            + str(p.relative_to(APP / "src/app"))
            .replace("/(protected)", "")
            .removesuffix("/page.tsx")
            for p in (APP / "src/app" / role / "(protected)").rglob("page.tsx")
            if "[" not in str(p)
        ]
        for route in dict.fromkeys(routes):
            errors.clear()
            bad.clear()
            try:
                link = page.locator('aside nav a[href="' + route + '"]')
                if await link.count():
                    await link.click()
                else:
                    await page.goto(BASE + route)
                await page.wait_for_timeout(500)
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                text = await page.locator("body").inner_text()
                slug = role + "-" + route.strip("/").replace("/", "-")
                (OUT / (slug + ".txt")).write_text(text)
                await page.screenshot(path=str(OUT / (slug + ".png")), full_page=True)
                alerts = [
                    text
                    for text in await page.locator(".state-banner[role=alert]").all_text_contents()
                    if text.strip()
                ]
                controls = await page.locator(
                    "main button,main input,main select,main textarea,main a"
                ).evaluate_all(
                    '(els)=>els.map(e=>({tag:e.tagName,text:(e.innerText||e.getAttribute("aria-label")||"").slice(0,100),name:e.name,type:e.type,disabled:e.disabled,href:e.getAttribute("href")}))'
                )
                await page.set_viewport_size({"width": 390, "height": 844})
                await page.wait_for_timeout(150)
                overflow = await page.evaluate(
                    "({scroll:document.documentElement.scrollWidth,width:innerWidth})"
                )
                await page.screenshot(path=str(OUT / (slug + "-mobile.png")), full_page=True)
                await page.set_viewport_size({"width": 1440, "height": 1000})
                row = {
                    "route": route,
                    "url": page.url,
                    "alerts": alerts,
                    "errors": errors.copy(),
                    "bad": bad.copy(),
                    "overflow": overflow,
                    "controls": controls,
                    "body": text[:12000],
                }
                rows.append(row)
                print(
                    role,
                    route,
                    "ALERT " + str(alerts) if alerts else "OK",
                    str(bad),
                    str(overflow),
                    flush=True,
                )
            except Exception as e:
                rows.append({"route": route, "exception": str(e)})
                print(role, route, str(e)[:200], flush=True)
        # Direct cross-role navigation must reject, including legacy routes.
        for target in ["/admin/users", "/supervisor/approvals", "/customer/cases", "/risk/holds"]:
            if (
                target.startswith("/" + role + "/")
                or role in ["operator", "supervisor"]
                and target.startswith("/supervisor/")
            ):
                continue
            await page.goto(BASE + target)
            await page.wait_for_timeout(200)
            assert urlsplit(page.url).path == "/unauthorized", target
            rows.append(
                {
                    "isolation": target,
                    "url": page.url,
                    "text": (await page.locator("body").inner_text())[:400],
                }
            )
        await page.goto(BASE + "/" + role + "/dashboard")
        await page.reload()
        assert await page.get_by_test_id("logout").is_visible()
        # Keyboard palette, theme persistence, and mobile navigation use real controls.
        await page.keyboard.press("Control+k")
        await page.get_by_role("dialog", name="Command palette").wait_for()
        await page.keyboard.press("Escape")
        await page.get_by_role("switch", name="Paper (light) theme").click()
        await page.reload()
        assert (
            await page.get_by_role("switch", name="Paper (light) theme").get_attribute(
                "aria-checked"
            )
            == "true"
        )
        await page.get_by_role("switch", name="Paper (light) theme").click()
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.get_by_role("button", name="Menu", exact=True).click()
        assert (
            await page.get_by_role("button", name="Menu", exact=True).get_attribute("aria-expanded")
            == "true"
        )
        await page.locator("aside nav a").first.click()
        assert (
            await page.get_by_role("button", name="Menu", exact=True).get_attribute("aria-expanded")
            == "false"
        )
        await page.set_viewport_size({"width": 1440, "height": 1000})
        await page.get_by_test_id("logout").click()
        await page.wait_for_url("**/login**")
        await page.goto(BASE + "/" + role + "/dashboard")
        assert urlsplit(page.url).path == "/login"
        rows.append({"logout": "PASS", "keyboard_theme_mobile": "PASS"})
    except Exception as e:
        rows.append(
            {
                "fatal": str(e),
                "url": page.url,
                "body": (await page.locator("body").inner_text())[:2000],
            }
        )
        print(role, "FATAL", str(e)[:200], flush=True)
    (OUT / (role + "-results.json")).write_text(
        json.dumps(
            {"role": role, "navigation": nav if "nav" in locals() else [], "results": rows},
            indent=2,
        )
    )
    await ctx.close()


async def main():
    async with async_playwright() as p:
        probe = await p.request.new_context()
        for _ in range(30):
            try:
                response = await probe.get(BASE + "/v1/capabilities", timeout=5000)
                if response.status == 200:
                    break
            except Exception:
                pass
            await asyncio.sleep(1)
        else:
            raise RuntimeError("Target did not become ready before the browser run")
        await probe.dispose()
        b = await p.chromium.launch(
            headless=True, executable_path=args.browser_executable, args=["--no-sandbox"]
        )
        for offset in [0, 3]:
            await asyncio.gather(*(audit(b, r) for r in ROLES[offset : offset + 3]))
        await b.close()


asyncio.run(main())
reports = [json.loads((OUT / (role + "-results.json")).read_text()) for role in ROLES]
failures = [
    {"role": d["role"], **r}
    for d in reports
    for r in d["results"]
    if r.get("fatal")
    or r.get("exception")
    or r.get("bad")
    or r.get("errors")
    or (r.get("alerts") and r.get("route") != "/merchant/tasks")
    or r.get("overflow", {}).get("scroll", 0) > 390
]
summary = {
    "pages": sum("route" in r for d in reports for r in d["results"]),
    "failures": failures,
    "limits": [
        "Read-only smoke checks; financial dispatch and provider credit are not certified.",
        "Merchant Tasks is a known unwired capability and remains an explicit unavailable state.",
    ],
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps({"pages": summary["pages"], "failures": len(failures)}))
sys.exit(bool(failures))
