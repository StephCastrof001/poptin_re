#!/usr/bin/env python3
import asyncio
import os
import json
from datetime import datetime
from playwright.async_api import async_playwright

class N:
    def __init__(self): 
        self.request = []
        self.end = {}
    
    def c(self, d):
        if not d and d is not False:
            return
        try:
            if not isinstance(d, dict):
                d = {'url': d.get('url', '')}
            if d:
                self.request.append(d)
                u = d.get('url', '')
                if '/api/' in u or 'graphql' in u.lower():
                    self.end.setdefault(u, {'method': d.get('method', 'GET'), 'count': 0})[0] += 1
        except:
            d = {}
            self.request.append(d)
            
class I:
    def __init__(self, e, p, b="https://app.poptin.com"):
        self.email, self.password, self.base = e, p, b
        self.s, self.d = "/home/ubuntu/poptin/builder/screenshots", "/home/ubuntu/poptin/builder/docs"
        os.makedirs(self.s, exist_ok=True)
        os.makedirs(self.d, exist_ok=True)
        self.net = N()
        self.browser, self.context, self.page, self.playwright = None, None, None, None
        
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        )
        self.page = await self.context.new_page()
        return self
    
    async def __aexit__(self, *args):
        if self.browser:
            await self.browser.close()
            await self.context.close()
            if self.page:
                await self.page.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def _screenshot(self, n, pg=None):
        pg = self.page if pg is None else pg
        await pg.screenshot(path=f"{self.s}/{n}.png", full_page=True)
        print(f"  {n}.png")
    
    async def login(self):
        try:
            print("  === Loading and Reloading ===")
            await self.page.goto(self.base); await asyncio.sleep(1)
            await self._screenshot("01_login_page")
            await asyncio.sleep(1)
            await self.page.reload(); await asyncio.sleep(1)
            
            token_input = await self.page.query_selector('input[name="_token"]')
            email_input = await self.page.query_selector('#InputEmail')
            password_input = await self.page.query_selector('#InputPassword')
            
            token = ""
            if token_input:
                token = await token_input.get_attribute("value")
                
            if email_input:
                await email_input.fill(self.email)
            if password_input:
                await password_input.fill(self.password)
            
            print(f"  Token: {token[:20] if token else 'None'}")
            await self._screenshot("01_filled")
            
            form = await self.page.query_selector('form')
            url_before = self.page.url
            await form.evaluate('f => f.submit()')
            
            await asyncio.sleep(3)
            url_after = self.page.url
            print(f"  After form.submit() - URL: {url_after}")
            await self._screenshot("02_submitted")
            
            await asyncio.sleep(1)
            await self.page.reload()
            await asyncio.sleep(2)
            
            form = await self.page.query_selector('form')
            if form:
                url_before2 = self.page.url
                await form.evaluate('f => f.submit()')
                await asyncio.sleep(3)
                url_after2 = self.page.url
                print(f"  After 2nd submit - URL: {url_after2}")
            
            u = await self.page.evaluate('() => { try { return window.user || window.auth || window.currentUser || {status: location.href}; } catch(e) { return e.message; } }')
            print(f"  After 2nd reload - user state: {type(u).__name__}, data: {str(u)[:200]}")
            await asyncio.sleep(2)
            u = await self.page.evaluate('() => { try { return window.user || window.auth || window.currentUser || {status: location.href}; } catch(e) { return e.message; } }')
            print(f"  Final - user state: {type(u).__name__}, data: {str(u)[:200]}")
            await self._screenshot("02_authenticated")
            return self.page, self.context
        except Exception as e:
            print(f"Login error: {e}")
            await self._screenshot("01_error")
            return self.page, self.context
    
    async def find_editor(self):
        print(f"\n=== FINDING EDITOR ===")
        paths = ["/create", "/popup/create", "/new", "/editor?w=new"]
        for path in paths:
            try:
                await self.page.goto(f"{self.base}{path};js='window.__NAV__=true;'", timeout=10000)
                await asyncio.sleep(2)
                u = await self.page.evaluate("() => window.user || window.auth || window.currentUser || {}")
                if u and u.get("id"):
                    print(f"  FOUND: {path}")
                    await self._screenshot("03_" + path.replace("/", "_"), self.page)
                    await self.inspect()
                    return True
                else:
                    print(f"  {path}: no user")
            except Exception as e:
                print(f"  {path}: err - {e}")
        print(f"  No editor found")
        await asyncio.sleep(1)
        return False
    
    async def inspect(self):
        print(f"\n=== INSPECTING ===")
        await asyncio.sleep(1)
        await self._screenshot("04", self.page)
        info = await self.page.evaluate("""async () => {
            const el = document.querySelector('[id*=editor], .editor, .workspace, [style*=width:100%]') || document.body;
            return {id: el.id, class: el.className, w: el.getBoundingClientRect().width,
                    widgets: Array.from(document.querySelectorAll('[data-widget*=""]').length),
                    panels: Array.from(document.querySelectorAll('[id*="panel"]')).length};
        });""")
        print(f"  Container: {info['id']}, Widgets: {info['widgets']}, Panels: {info['panels']}")
        types = await self.page.evaluate("""async () => {
            let t = [];
            ['[class*="type-selector"], [class*="widget-types"], .type-picker, [data-type*=""]').forEach(sel => {
                Array.from(document.querySelectorAll(sel)).forEach(e => {
                    const txt = (e.querySelector('.') || e)?.firstElementChild?.firstChild?.textContent || '';
                    if (txt and !t.includes(txt)) t.push(txt);
                });
            });
            return t.slice(0, 30);
        });""")
        if types: print(f"  Types: {types[:15]}"); await self._screenshot("05_types", self.page)
        w = await self.page.evaluate("""async () => Array.from(document.querySelectorAll('[data-widget*=""]').slice(0, 5));""")
        print(f"  Widgets: {len(w) if w else 0}"); await self._screenshot("06_widgets", self.page)
        await self._screenshot("07_full", self.page)
    
    async def extract(self):
        print(f"\n=== EXTRACTING STATE ===")
        p = self.page if self.page else await self.context.new_page()
        state = await p.evaluate("() => Object.assign({}, localStorage)")
        print(f"  LocalStorage: {len(state)} entries")
        for k, v in list(state.items())[:8]:
            if isinstance(v, dict) and len(str(v)) > 100:
                print(f"    {k}: {str(v)[:200]}")
    
    async def save_reports(self, pg=None):
        lines = [f"## Poptin API Capture {datetime.now().isoformat()}", "=" * 40,
                 f"Session: {self.email}", f"Base: {self.base}",
                 "## Endpoints", "| M | URL | Count |", "|---|---|-|"]
        for ep in sorted(self.net.end.items(), key=lambda x: x[1]['count'], reverse=True)[:10]:
            lines.append(f"| {ep[1]['method']:<2} | {ep[0][:22]:<20} | {ep[1]['count']:<3}|")
        lines += [f"## Screenshots: {self.s}/", f"## Raw JSON: {self.d}/api_capture.json",
                 f"Total Requests: {len(self.net.request)}, Endpoints: {len(self.net.end)}"]
        with open(f"{self.d}/API_CAPTURE.md", "w") as f: 
            f.write("\n".join(lines))
        print(f"\nDone: {self.d}/API_CAPTURE.md")
        with open(f"{self.d}/api_capture.json", "w") as f:
            json.dump({"requests": self.net.request, "endpoint_counts": self.net.end}, f, indent=2)
    
    async def run(self):
        print("=" * 40, "\nPOPTIN INSPECTOR\n" + "=" * 40)
        async with self:
            await self.login()
            await self.find_editor()
            await self.extract()
            await self.save_reports()
        print(f"Done: {self.s}/{self.d}")

async def main():
    async with I("stephanie.castro@pucp.pe", "20063288") as inspector:
        await inspector.run()

if __name__ == "__main__":
    asyncio.run(main())
