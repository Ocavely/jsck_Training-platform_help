import os, time, json, re
from datetime import datetime
from playwright.sync_api import sync_playwright

from config import BASE_URL, COURSE_URL, CACHE_DIR, ASSIGNMENTS

STORAGE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".login_storage.json")


class Crawler:
    def __init__(self, callback=None, storage_file=None):
        self.callback = callback
        self.storage_file = storage_file or STORAGE_FILE
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
        if use_storage and os.path.exists(self.storage_file):
            with open(self.storage_file, "r", encoding="utf-8") as f:
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
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(state, f)
            self.log("[+] 已保存登录态到本地")

    def login_only(self):
        self._start_browser(use_storage=False)
        ok = self._wait_login()
        if ok:
            self.close()
        return ok

    def login_with_credentials(self, username, password):
        self._start_browser(use_storage=False)
        self.page.goto(COURSE_URL, wait_until="domcontentloaded", timeout=30000)
        kw = ["oauth", "login", "authorize"]
        if not any(k in self.page.url.lower() for k in kw):
            self.log("[+] 已有登录态，无需登录")
            self.logged_in = True
            self._save_storage()
            self.close()
            return True
        self.log("[*] 检测到登录页面，正在自动填写账号密码...")
        try:
            self.page.wait_for_selector('#app', timeout=10000)
            self.page.wait_for_timeout(1000)
            self.page.evaluate("""args => {
                const vm = document.querySelector('#app').__vue_app__._instance.proxy;
                vm.form.username = args.u;
                vm.form.password = args.p;
                vm.submitForm({type: 'click'});
            }""", {"u": username, "p": password})
            self.page.wait_for_timeout(5000)
            kw = ["oauth", "login", "authorize"]
            if any(k in self.page.url.lower() for k in kw):
                self.log("[-] 自动登录失败，请检查账号密码或改用手动登录")
                return False
            self.logged_in = True
            self._save_storage()
            self.log("[+] 自动登录成功!")
            self.close()
            return True
        except Exception as e:
            self.log(f"[-] 自动登录出错: {e}")
            return False

    def login_and_crawl(self):
        self._start_browser(use_storage=False)
        ok = self._wait_login()
        if not ok:
            return {}
        return self._do_crawl()

    def crawl_with_storage(self):
        """使用已有登录态启动浏览器并抓取全部"""
        if not os.path.exists(self.storage_file):
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

    def crawl_selected(self, ids, assignments=None, url_map=None):
        if not self.page:
            if os.path.exists(self.storage_file):
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
        lookup = assignments or ASSIGNMENTS
        for i, assign_id in enumerate(ids):
            title = ""
            for aid, t, _ in lookup:
                if aid == assign_id:
                    title = t
                    break
            self.log(f"  [{i+1}/{total}] {title} (id={assign_id})...")
            activity_url = url_map.get(assign_id) if url_map else None
            info = self.get_assignment_info(assign_id, url=activity_url)
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

    def get_assignment_info(self, assign_id, url=None):
        if url is None:
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

    def crawl_exam_selected(self, ids, url_map):
        """Crawl quiz exams: enter attempt and capture question content"""
        results = {}
        total = len(ids)
        for i, exam_id in enumerate(ids):
            url = url_map.get(exam_id, "")
            if not url:
                self.log(f"  [{i+1}/{total}] id={exam_id} -> 无URL，跳过")
                continue
            self.log(f"  [{i+1}/{total}] 考试 id={exam_id}...")
            try:
                self.page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(1)
                # Click "现在参加测验" or "继续上次答题"
                btn = self.page.query_selector('button:has-text("现在参加测验"), button:has-text("继续上次答题"), input[value*="现在参加测验"], input[value*="继续"]')
                if btn:
                    self.log(f"    点击答题按钮...")
                    btn.click()
                    time.sleep(2)
                html = self.page.content()
                os.makedirs(CACHE_DIR, exist_ok=True)
                cache_path = os.path.join(CACHE_DIR, f"exam_{exam_id}.html")
                with open(cache_path, "w", encoding="utf-8") as f:
                    f.write(html)
                info = {"id": exam_id, "html": html, "type": "quiz"}
                results[exam_id] = info
            except Exception as e:
                self.log(f"  [-]: {e}")
        self.log(f"[+] 抓取完成: {len(results)} 个考试")
        return results

    def check_completion(self, assign_id):
        """Check if an assignment has been completed/submitted on the platform"""
        from config import BASE_URL, CACHE_DIR
        url = f"{BASE_URL}/mod/assign/view.php?id={assign_id}&action=editsubmission"
        try:
            self.page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(2)
            html = self.page.content()
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(os.path.join(CACHE_DIR, f"status_{assign_id}.html"), "w", encoding="utf-8") as f:
                f.write(html)
        except Exception as e:
            self.log(f"  [-] 页面加载失败 id={assign_id}: {e}")
            return False
        try:
            result = self.page.evaluate("""() => {
                const text = (document.body.innerText || '').toLowerCase();
                // 1. submission receipt (Moodle standard)
                const receipt = document.querySelector('.submissionreceipt');
                if (receipt && receipt.offsetParent !== null) return true;
                // 2. explicit submission status text
                const st = document.querySelector('.submissionstatustext, .submission-status');
                if (st) {
                    const t = st.innerText.toLowerCase();
                    if (t.includes('已提交') || t.includes('submitted')) return true;
                    if (t.includes('draft') || t.includes('未提交')) return false;
                }
                // 3. submit_assign button visible → not completed
                const btn = document.getElementById('submit_assign') ||
                           document.querySelector('button[name=submit_assign],button[id=submit_assign]');
                if (btn && btn.offsetParent !== null) return false;
                // 4. edit submission link → already submitted
                if (document.querySelector('a[href*="action=editsubmission"]')) return true;
                // 5. no editor / no submit area → likely submitted
                var editor = document.getElementById('ace_editor');
                if (!editor) {
                    var ta = document.querySelector('textarea');
                    if (!ta) return true;
                }
                // 6. page text clues
                if (text.includes('已提交') || text.includes('submitted') && text.includes('submission'))
                    return true;
                return false;
            }""")
            if result:
                self.log(f"  [+] id={assign_id} 已完成")
                return True
            else:
                self.log(f"  [ ] id={assign_id} 未完成")
                return False
        except Exception as e:
            self.log(f"  [-] 检查 id={assign_id} 时出错: {e}")
            return False

    def check_multiple_completion(self, ids, page_url=None, lookup=None):
        """Check completion status from course page checkmarks (one page load)"""
        results = {}
        url = page_url or COURSE_URL
        lookup_list = lookup or ASSIGNMENTS
        try:
            self.page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(1)

            debug_html = self.page.evaluate("() => document.querySelector('li.activity') ? 'activity_found' : 'no_activity'")
            self.log(f"  [debug] page URL: {self.page.url}, activity check: {debug_html}")
            time.sleep(1)

            status_map = self.page.evaluate("""() => {
                const map = {};
                document.querySelectorAll('li.activity').forEach(li => {
                    const link = li.querySelector('a[href*="id="]');
                    if (!link) return;
                    const m = link.href.match(/id=(\\d+)/);
                    if (!m) return;
                    const aid = parseInt(m[1]);
                    const done = li.innerHTML.includes('completion-manual-y') || li.innerHTML.includes('completion-auto-y');
                    map[aid] = done;
                });
                return map;
            }""")
            self.log(f"  [debug] status_map keys: {list(status_map.keys())}")
        except Exception as e:
            self.log(f"  [-] 加载课程页失败: {e}")
            return {aid: False for aid in ids}

        for aid in ids:
            completed = status_map.get(aid, False)
            results[aid] = completed
            title = str(aid)
            for a, t, _ in lookup_list:
                if a == aid:
                    title = t
                    break
            if completed:
                self.log(f"  [+] {title} (id={aid}) ✓ 已完成")
            else:
                self.log(f"  [ ] {title} (id={aid}) 未完成")
        return results

    def get_section_activities(self, section_url):
        """Visit a course section page and return list of (id, title, type, url) activities"""
        self.page.goto(section_url, wait_until="networkidle", timeout=30000)
        time.sleep(1)
        activities = self.page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('li.activity').forEach(li => {
                const link = li.querySelector('a[href*="id="]');
                if (!link) return;
                const href = link.href;
                const m = href.match(/id=(\\d+)/);
                if (!m) return;
                const id = parseInt(m[1]);
                const nameEl = li.querySelector('.instancename');
                const name = nameEl ? nameEl.innerText.trim() : ('活动' + id);
                let modType = 'regular';
                const pathname = new URL(href).pathname;
                if (pathname.includes('/mod/assign/')) modType = 'code_assign';
                results.push({id, name, type: modType, url: href});
            });
            return results;
        }""")
        return [(a["id"], a["name"], a["type"], a["url"]) for a in activities]

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
