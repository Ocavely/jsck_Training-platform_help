import os, time, json
from playwright.sync_api import sync_playwright

from config import BASE_URL, ANSWER_DIR, COURSE_URL

STORAGE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".login_storage.json")


def code_lang_map(lang):
    m = {'Java': 'java', 'Python3': 'py3', 'c++': 'cpp'}
    return m.get(lang, (lang or 'py3').lower())


class Submitter:
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

    def _launch(self):
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=False, channel="msedge")
        if os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
            self.context = self.browser.new_context(storage_state=state)
            self.log("[+] 从本地恢复登录态")
        else:
            self.context = self.browser.new_context()
            self.log("[-] 未找到登录态文件，需要手动登录")
        self.page = self.context.new_page()

    def start(self):
        self.log("[*] 正在启动浏览器...")
        self._launch()
        self.page.goto(COURSE_URL, wait_until="domcontentloaded", timeout=30000)
        kw = ["oauth", "login", "authorize"]
        if any(k in self.page.url.lower() for k in kw):
            self.log("[+] 登录态过期，请手动登录...")
            t = 0
            while any(k in self.page.url.lower() for k in kw):
                time.sleep(2); t += 2
                if t % 20 == 0:
                    self.log(f"[+] 等待 {t} 秒...")
                try:
                    self.page.wait_for_url("**/course/**", timeout=2000)
                except:
                    pass
                if t > 300:
                    self.log("[-] 登录超时!")
                    return False
            with open(STORAGE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.context.storage_state(), f)
            self.log("[+] 已更新本地登录态")
        self.logged_in = True
        self.log("[+] 登录成功!")
        return True

    def submit_one(self, assign_id, code):
        try:
            url = f"{BASE_URL}/mod/assign/view.php?id={assign_id}&action=editsubmission&sub_type=code_assign"
            self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
            kw = ["oauth", "login", "authorize"]
            if any(k in self.page.url.lower() for k in kw):
                return {"id": assign_id, "status": "failed", "msg": "登录态过期"}
            time.sleep(1)

            vals = self.page.evaluate("""() => {
                if (typeof codeAssignSubmissionValues === 'undefined') return null;
                return {
                    question_id: codeAssignSubmissionValues.question_id,
                    instance_id: codeAssignSubmissionValues.instance_id,
                    test_case: codeAssignSubmissionValues.test_case,
                    type: codeAssignSubmissionValues.type,
                    id: codeAssignSubmissionValues.id,
                    memory_limit: codeAssignSubmissionValues.memory_limit,
                    time_limit: codeAssignSubmissionValues.time_limit,
                    code_lang: codeAssignSubmissionValues.code_lang,
                };
            }""")
            if not vals:
                return {"id": assign_id, "status": "failed", "msg": "未找到判题参数"}

            cl = code_lang_map(vals.get('code_lang'))
            self.page.evaluate("""(c) => {
                try { ace.edit('ace_editor').setValue(c); } catch(e) {}
            }""", code)
            time.sleep(0.3)

            api_resp = self.page.evaluate("""(data) => {
                var result = null;
                $.ajax({
                    url: '/judge/index.php',
                    type: 'POST', data: data, dataType: 'json', async: false,
                    success: function(r) { result = r; },
                    error: function(xhr) { result = {code: -1, message: xhr.statusText}; }
                });
                return result;
            }""", {
                'm': 'judge', 'c': 'server', 'a': 'post_judge_api',
                'code': code, 'code_lang': cl,
                'test_case': vals['test_case'],
                'memory_limit': vals['memory_limit'],
                'time_limit': vals['time_limit'],
                'question_id': vals['question_id'],
                'instance_id': vals['instance_id'],
                'type': vals['type'],
            })

            if api_resp and api_resp.get('code') in [1, 2]:
                # form.submit() 提交结果（正常表单提交，确保服务端完整处理）
                self.page.evaluate("""(args) => {
                    var form = document.createElement('form');
                    form.method = 'post'; form.style.display = 'none';
                    form.action = '/mod/assign/codeAssignSubmissionResult.php';
                    var add = function(n, v) {
                        var i = document.createElement('input');
                        i.type = 'hidden'; i.name = n; i.value = v;
                        form.appendChild(i);
                    };
                    add('judge_data', JSON.stringify(args.data));
                    add('judge_code', ace.edit('ace_editor').getValue());
                    add('id', args.id);
                    add('s', '1');
                    document.body.appendChild(form);
                    form.submit();
                }""", {
                    'data': api_resp.get('data', {}),
                    'id': str(vals['id']),
                })

                # 等待表单提交后的导航完成（codeAssignSubmissionResult.php 处理完后会重定向或显示结果页）
                try:
                    self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                except:
                    pass
                time.sleep(2)

                self.log(f"    结果页URL: {self.page.url}")

                # 查找并点击"提交作业"按钮，完成最终提交
                has_submit_btn = self.page.evaluate("""() => {
                    var btn = document.getElementById('submit_assign');
                    if (!btn) btn = document.querySelector('button[name=submit_assign]');
                    if (!btn) btn = document.querySelector('button[id=submit_assign]');
                    if (btn) return {exists: true, text: btn.innerText.trim(), visible: btn.offsetParent !== null};
                    return {exists: false};
                }""")

                if has_submit_btn.get('exists'):
                    self.log(f"    发现提交作业按钮: '{has_submit_btn.get('text')}'")
                    try:
                        self.page.click("button[name=submit_assign], button[id=submit_assign]", timeout=5000)
                        self.log(f"    已点击提交作业按钮")
                        try:
                            self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                        except:
                            pass
                        time.sleep(2)
                        self.log(f"    提交后URL: {self.page.url}")
                    except Exception as e:
                        self.log(f"    点击提交按钮出错: {e}")
                        # 如果点击按钮失败，尝试直接 AJAX 提交
                        self.log("    尝试通过 AJAX 直接提交...")
                else:
                    self.log("    未找到提交作业按钮，可能已自动提交")

                judge_result = api_resp.get('data', {}).get('result', '')
                if judge_result:
                    return {"id": assign_id, "status": "passed", "msg": judge_result}
                return {"id": assign_id, "status": "passed", "msg": "已提交"}
            else:
                msg = api_resp.get('message', '无响应') if api_resp else 'API 错误'
                return {"id": assign_id, "status": "failed", "msg": msg}
        except Exception as e:
            return {"id": assign_id, "status": "failed", "msg": str(e)}

    def submit_assignments(self, assign_list, progress_callback=None):
        results = {}
        total = len(assign_list)
        for i, (assign_id, _) in enumerate(assign_list):
            filepath = os.path.join(ANSWER_DIR, f"{assign_id}_answer.py")
            if not os.path.exists(filepath):
                self.log(f"  [{i+1}/{total}] 未找到答案文件 {assign_id}，跳过")
                if progress_callback:
                    progress_callback(i + 1, total, assign_id, "skipped", "无答案文件")
                continue
            with open(filepath, "r", encoding="utf-8") as f:
                code = f.read()
            self.log(f"  [{i+1}/{total}] 正在提交 {assign_id}...")
            result = self.submit_one(assign_id, code)
            results[assign_id] = result
            status_str = result.get("status", "failed")
            msg = result.get("msg", "")
            cn = {"passed": "通过", "failed": "失败", "submitted": "已提交", "skipped": "跳过"}
            self.log(f"    -> {cn.get(status_str, status_str)}: {msg}")
            if progress_callback:
                progress_callback(i + 1, total, assign_id, status_str, result.get("msg", ""))
        # 最后再刷一次课程页面，确保所有状态已更新
        try:
            self.page.goto(COURSE_URL, wait_until="domcontentloaded", timeout=15000)
            time.sleep(1)
        except:
            pass
        return results

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
