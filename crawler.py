import os, time, json, re
from datetime import datetime
from playwright.sync_api import sync_playwright

from config import BASE_URL, COURSE_URL, CACHE_DIR, ASSIGNMENTS

STORAGE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".login_storage.json")


class Crawler:
    def __init__(self, callback=None):
        self.callback = callback
        self._pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.logged_in = False

    def log(self, msg):
        if self.callback:
            self.callback(msg)

    def _start_browser(self, use_storage=False):
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=False, channel="msedge")
        if use_storage and os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
            self.context = self.browser.new_context(storage_state=state)
            self.log("[+] 从本地恢复登录态")
        else:
            self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def _wait_login(self):
        self.page.goto(COURSE_URL, wait_until="domcontentloaded", timeout=30000)
        kw = ["oauth", "login", "authorize"]
        if any(k in self.page.url.lower() for k in kw):
            self.log("[+] 请在浏览器中手动登录...")
            t = 0
            while any(k in self.page.url.lower() for k in kw):
                time.sleep(2)
                t += 2
                if t % 20 == 0:
                    self.log(f"[+] 等待 {t} 秒...")
                try:
                    self.page.wait_for_url("**/course/**", timeout=2000)
                except:
                    pass
                if t > 300:
                    self.log("[-] 登录超时!")
                    return False
        self.logged_in = True
        self._save_storage()
        self.log("[+] 登录成功!")
        return True

    def _save_storage(self):
        if self.context:
            state = self.context.storage_state()
            with open(STORAGE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f)
            self.log("[+] 已保存登录态到本地")

    def login_only(self):
        self._start_browser(use_storage=False)
        ok = self._wait_login()
        if ok:
            self.close()
        return ok

    def login_and_crawl(self):
        self._start_browser(use_storage=False)
        ok = self._wait_login()
        if not ok:
            return {}
        return self._do_crawl()

    def crawl_with_storage(self):
        """使用已有登录态启动浏览器并抓取全部"""
        if not os.path.exists(STORAGE_FILE):
            self.log("[-] 未找到本地登录态，需要完整登录")
            return self.login_and_crawl()
        self._start_browser(use_storage=True)
        self.page.goto(COURSE_URL, wait_until="domcontentloaded", timeout=30000)
        kw = ["oauth", "login", "authorize"]
        if any(k in self.page.url.lower() for k in kw):
            self.log("[-] 登录态已过期，需要重新登录")
            self.close()
            return self.login_and_crawl()
        self.logged_in = True
        self.log("[+] 登录态有效")
        return self._do_crawl()

    def crawl_selected(self, ids):
        if not self.page:
            if os.path.exists(STORAGE_FILE):
                self._start_browser(use_storage=True)
                self.page.goto(COURSE_URL, wait_until="domcontentloaded", timeout=30000)
                kw = ["oauth", "login", "authorize"]
                if any(k in self.page.url.lower() for k in kw):
                    self.log("[-] 登录态已过期")
                    return {}
                self.logged_in = True
            else:
                self.log("[-] 未找到登录态，请先登录")
                return {}
        results = {}
        total = len(ids)
        for i, assign_id in enumerate(ids):
            title = ""
            for aid, t, _ in ASSIGNMENTS:
                if aid == assign_id:
                    title = t
                    break
            self.log(f"  [{i+1}/{total}] {title} (id={assign_id})...")
            info = self.get_assignment_info(assign_id)
            if info:
                info["name"] = title
                results[assign_id] = info
            else:
                self.log("  -> 失败")
        self.log(f"[+] 抓取完成: {len(results)} 个作业")
        return results

    def _do_crawl(self):
        results = {}
        total = len(ASSIGNMENTS)
        for i, (assign_id, title, atype) in enumerate(ASSIGNMENTS):
            self.log(f"  [{i+1}/{total}] {title} (id={assign_id})...")
            info = self.get_assignment_info(assign_id)
            if info:
                info["name"] = title
                info["assign_type"] = atype
                results[assign_id] = info
            else:
                self.log("  -> 失败")
        self.log(f"[+] 抓取完成: {len(results)} 个作业")
        return results

    def get_assignment_info(self, assign_id):
        url = f"{BASE_URL}/mod/assign/view.php?id={assign_id}&action=editsubmission"
        try:
            self.page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(2)
            html = self.page.content()
            os.makedirs(CACHE_DIR, exist_ok=True)
            cache_path = os.path.join(CACHE_DIR, f"assign_{assign_id}.html")
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(html)
            info = {"id": assign_id, "html": html}
            m = re.search(r'<h2>([^<]+)</h2>', html)
            if m:
                info["title"] = m.group(1)
            m = re.search(r'codeAssignSubmissionValues\s*=\s*({.*?});', html)
            if m:
                try:
                    info["code_values"] = json.loads(m.group(1))
                    info["type"] = "code_assign"
                except:
                    info["type"] = "regular"
            else:
                info["type"] = "regular"
            return info
        except Exception as e:
            self.log(f"  [-]: {e}")
            return None

    def close(self):
        try:
            if self.browser:
                self.browser.close()
        except:
            pass
        try:
            if self._pw:
                self._pw.stop()
        except:
            pass
