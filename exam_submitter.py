# -*- coding: utf-8 -*-
"""
Exam quiz answer filler - fills in answers WITHOUT submitting.
For testing: simulates manual click and input effects only.
"""
import os, re, time, json
from playwright.sync_api import sync_playwright

from config import BASE_URL, COURSE_URL
import urllib.parse

STORAGE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".login_storage.json")
ANSWER1_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "answer1")


class ExamSubmitter:
    def __init__(self, callback=None, storage_file=None, timer_seconds=120):
        self.callback = callback
        self.storage_file = storage_file or STORAGE_FILE
        self.timer_seconds = timer_seconds
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
        if os.path.exists(self.storage_file):
            with open(self.storage_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            self.context = self.browser.new_context(storage_state=state)
            self.log("[+] 从本地恢复登录态")
        else:
            self.context = self.browser.new_context()
            self.log("[-] 未找到登录态文件")
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
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(self.context.storage_state(), f)
            self.log("[+] 已更新本地登录态")
        self.logged_in = True
        self.log("[+] 登录成功!")
        return True

    def _load_answers(self, exam_id):
        """Load answers for a given exam from _exam_answers.json"""
        json_path = os.path.join(ANSWER1_DIR, "_exam_answers.json")
        if not os.path.exists(json_path):
            self.log(f"[-] 未找到答案JSON文件: {json_path}")
            return []
        with open(json_path, "r", encoding="utf-8") as f:
            all_answers = json.load(f)
        return all_answers.get(str(exam_id), [])

    def fill_exam(self, exam_id, quiz_url):
        """
        Navigate to quiz page, fill in all answers, but do NOT submit.
        Returns True if successful.
        """
        self.log(f"  [*] 考试 id={exam_id}: 正在打开测验页面...")
        try:
            self.page.goto(quiz_url, wait_until="networkidle", timeout=30000)
            time.sleep(1)
        except Exception as e:
            self.log(f"  [-] 无法打开页面: {e}")
            return False

        # Check login
        kw = ["oauth", "login", "authorize"]
        if any(k in self.page.url.lower() for k in kw):
            self.log("  [-] 登录态过期")
            return False

        # Install network interceptor BEFORE entering quiz
        self._install_network_interceptor()

        # Click attempt button if present
        btn = self.page.query_selector(
            'button:has-text("现在参加测验"), button:has-text("继续上次答题"), '
            'button:has-text("再次尝试此测验"), '
            'input[value*="现在参加测验"], input[value*="继续"], '
            'input[value*="再次尝试"]'
        )
        if btn:
            self.log("  [*] 点击答题按钮进入测验...")
            btn.click()
            time.sleep(2)
            self.page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(1)

        # Stop client-side timer + set endtime
        self._disable_timer()
        self._dump_timer_state()

        # Load answers for this exam
        answers = self._load_answers(exam_id)
        if not answers:
            self.log(f"  [-] 未找到考试 {exam_id} 的答案数据")
            return False

        self.log(f"  [*] 共 {len(answers)} 道题答案，开始填入...")

        filled = 0
        for idx, item in enumerate(answers):
            qnum = item["qnum"]
            qtype = item["type"]
            answer_text = item["answer"]

            ok = False
            for _ in range(20):
                if qtype == "multichoice":
                    ok = self._fill_mcq(qnum, answer_text)
                    if not ok:
                        ok = self._fill_essay(qnum, answer_text)
                elif qtype == "essay":
                    html = item.get("html", "")
                    ok = self._fill_essay(qnum, answer_text, html)
                    if not ok:
                        ok = self._fill_mcq(qnum, answer_text)
                else:
                    self.log(f"    第{qnum}题: 跳过(类型={qtype})")
                    ok = True

                if ok:
                    filled += 1
                    break

                # Element not on current page, try next page
                if not self._navigate_next():
                    self.log(f"    第{qnum}题: 当前页未找到且无下一页")
                    break

                time.sleep(0.5)

            if not ok:
                self.log(f"      -> 第{qnum}题 未能填入")

        self.log(f"  [+] 考试 {exam_id}: 已填入 {filled}/{len(answers)} 题答案")
        return True

    def _install_network_interceptor(self):
        """Monitor quiz requests; modify only final-submit POST body for timeup=0."""
        try:
            self.page.route(
                re.compile(r'.*mod/quiz/processattempt\.php.*'),
                self._on_quiz_request,
            )
            self.log("  [*] 网络拦截器已安装(仅拦截processattempt)")
        except Exception as e:
            self.log(f"  [-] 安装网络拦截器失败: {e}")

    def _on_quiz_request(self, route):
        """Intercept processattempt POST; only force timeup=0 on final submit."""
        req = route.request
        yield_params = None
        try:
            if req.method == "POST" and req.post_data:
                params = urllib.parse.parse_qs(req.post_data)
                is_final = params.get('finishattempt', [None])[0] == '1'
                old_timeup = params.get('timeup', [None])[0]
                if is_final:
                    if old_timeup != '0':
                        params['timeup'] = ['0']
                        yield_params = urllib.parse.urlencode(params, doseq=True)
                        self.log(f"  [网络拦截] 最终交卷 timeup: {old_timeup}→0")
                    else:
                        self.log(f"  [网络拦截] 最终交卷 (timeup=0 OK)")
        except Exception as e:
            self.log(f"  [网络拦截] 处理失败: {e}")
        if yield_params is not None:
            route.continue_(post_data=yield_params)
        else:
            route.continue_()

    def _disable_timer(self):
        """Stop quiz timer + trap timeup.value + inject submit hook."""
        if self.timer_seconds <= 0:
            return
        try:
            new_ts = int(time.time()) + self.timer_seconds
            result = self.page.evaluate("""
                (function(ts) {
                    var found = null, inp = document.getElementById('timeup');

                    // 1) Stop M.mod_quiz.timer
                    if (typeof M !== 'undefined' && M.mod_quiz) {
                        var t = M.mod_quiz.timer;
                        if (t) { try { t.stop(null); } catch(e) {} found = 'M.mod_quiz.timer'; }
                        M.mod_quiz.timer = { stop: function(){}, endtime: ts, tick: function(){} };
                    }

                    // 2) Trap timeup.value — silently discard any non-'0' write
                    if (inp && !inp._t2) {
                        inp._t2 = true;
                        inp.value = '0';
                        try {
                            var _val = '0';
                            Object.defineProperty(inp, 'value', {
                                get: function() { return _val; },
                                set: function(v) { _val = '0'; },
                                configurable: false
                            });
                        } catch(e) { /* fallback */ }
                        found = (found || 'timeup');
                    }

                    // 3) Submit hook — extra safety
                    if (!window._t3) {
                        window._t3 = true;
                        document.addEventListener('submit', function() {
                            var tu = document.getElementById('timeup');
                            if (tu) try { tu.value = '0'; } catch(e) {}
                        }, true);
                    }

                    // 4) Hide timer display
                    var el = document.querySelector('#quiz-timer, .quiz-timer, .timer, .timeleft');
                    if (el) { el.style.display = 'none'; found = found || 'hidden'; }
                    return found;
                })(""" + str(new_ts) + """)
            """)
            if result:
                self.log(f"  [*] 计时器已拦截({result}), 设为 {self.timer_seconds}s")
            else:
                self.log(f"  [?] 未找到已知计时器对象, 已强制 timeup=0")
        except Exception as e:
            self.log(f"  [-] 计时器拦截失败: {e}")

    def _dump_timer_state(self):
        """Dump all timer-related JS state for debugging. Call from fill_exam."""
        try:
            info = self.page.evaluate("""() => {
                var r = {};
                r.M_exists = typeof M !== 'undefined';
                if (r.M_exists) {
                    r.M_mod_quiz = typeof M.mod_quiz !== 'undefined';
                    if (r.M_mod_quiz) {
                        r.has_timer = typeof M.mod_quiz.timer !== 'undefined';
                        if (r.has_timer) {
                            r.endtime = M.mod_quiz.timer.endtime;
                            r.has_stop = typeof M.mod_quiz.timer.stop === 'function';
                            r.has_tick = typeof M.mod_quiz.timer.tick === 'function';
                        }
                        r.has_timerinstance = typeof M.mod_quiz.timerinstance !== 'undefined';
                        if (r.has_timerinstance) {
                            r.instance_endtime = M.mod_quiz.timerinstance.endtime;
                        }
                    }
                }
                r.timeup_val = (document.getElementById('timeup') || {}).value;
                r.timer_visible = !!document.querySelector('#quiz-timer, .quiz-timer, .timer, .timeleft');
                r.now_sec = Math.floor(Date.now() / 1000);
                return r;
            }""")
            self.log(f"  [Timer诊断] {info}")
        except Exception as e:
            self.log(f"  [Timer诊断] 失败: {e}")

    def _navigate_next(self):
        """Click '下一题' / next page button if present (NOT the finish button).
        Returns True if navigated, False otherwise."""
        try:
            btn = self.page.query_selector(
                'input[name="next"][value*="下一"], '
                'button:has-text("下一题"), '
                'button:has-text("下一"), '
                'input[value*="Next question"], '
                'input[value*="下一页"]'
            )
            if btn:
                val = btn.get_attribute("value") or btn.inner_text() or ""
                self.log(f"  [*] 点击\"{val}\"...")
                btn.dispatch_event("click")
                time.sleep(1)
                self.page.wait_for_load_state("networkidle", timeout=15000)
                time.sleep(1)
                self._disable_timer()
                return True
        except Exception as e:
            self.log(f"  [-] 切换下一题出错: {e}")
        return False

    def submit_exam(self, exam_id=None):
        """
        Click the finish/submit buttons to submit the exam.
        Flow: click '结束答题' -> click '提交所有答案并结束' -> accept confirm.
        """
        self.log(f"  [*] 正在提交考试{' ' + str(exam_id) if exam_id else ''}...")

        # Ensure timeup=0 before any submit action
        try:
            self.page.evaluate("""
                const inp = document.getElementById('timeup');
                if (inp) inp.value = '0';
            """)
        except:
            pass

        try:
            # Step 1: click finish button on last question page
            finish_btn = self.page.query_selector(
                'input[name="next"][value*="结束"], '
                'button:has-text("结束答题"), '
                'button:has-text("结束考试"), '
                'button:has-text("Finish attempt")'
            )
            if finish_btn:
                value = finish_btn.get_attribute("value") or finish_btn.inner_text() or ""
                self.log(f"  [*] 点击 \"{value}\"...")
                finish_btn.click()
                time.sleep(2)
                self.page.wait_for_load_state("load", timeout=30000)
                time.sleep(1)

            # Step 2: on summary page, click submit all button
            submit_btn = self.page.query_selector(
                'button[id="id_submitbutton"], '
                'input[id="id_submitbutton"], '
                'input[type="submit"][value*="提交"], '
                'input[type="submit"][value*="Submit all"], '
                'input[type="submit"][value*="Finish attempt"], '
                'button:has-text("提交"), '
                'button:has-text("Submit all"), '
                'button:has-text("Finish attempt")'
            )
            if submit_btn:
                text = submit_btn.get_attribute("value") or submit_btn.inner_text() or ""
                self.log(f"  [*] 点击 \"{text}\"...")
                submit_btn.click()
                time.sleep(2)
                self.page.wait_for_load_state("load", timeout=30000)
                time.sleep(1)
                self.log("  [+] 已确认提交")

            # Step 3: click "确定" on the result page
            ok_btn = self.page.query_selector(
                'button:has-text("确定"), '
                'input[value*="确定"], '
                'a:has-text("确定")'
            )
            if ok_btn:
                text = ok_btn.get_attribute("value") or ok_btn.inner_text() or ""
                self.log(f"  [*] 点击 \"{text}\"...")
                ok_btn.click()
                time.sleep(1)

            self.log(f"  [+] 考试{' ' + str(exam_id) if exam_id else ''} 提交完成!")
            return True

        except Exception as e:
            self.log(f"  [-] 提交出错: {e}")
            return False

    @staticmethod
    def _normalize(s):
        """Normalize string for comparison: strip, unify quotes, collapse spaces."""
        s = s.strip()
        # Replace various quote characters with straight quotes
        s = s.replace('\u201c', '"').replace('\u201d', '"')  # double curly
        s = s.replace('\u2018', "'").replace('\u2019', "'")  # single curly
        s = s.replace('\uff02', '"').replace('\uff07', "'")  # fullwidth
        s = re.sub(r'\s+', ' ', s)
        return s

    def _detect_input_type(self, qnum):
        """Detect if a question uses radio (单选) or checkbox (多选).
        Tries multiple naming patterns (Moodle uses _answer, _answer[], _choiceN, etc.)."""
        patterns = [
            f'input[type="radio"][name$=":{qnum}_answer"]',
            f'input[type="radio"][name$=":{qnum}_answer[]"]',
            f'input[type="radio"][name*=":{qnum}_"]',
        ]
        for sel in patterns:
            el = self.page.query_selector(sel)
            if el:
                return "radio"
        patterns = [
            f'input[type="checkbox"][name$=":{qnum}_answer"]',
            f'input[type="checkbox"][name$=":{qnum}_answer[]"]',
            f'input[type="checkbox"][name*=":{qnum}_"]',
        ]
        for sel in patterns:
            el = self.page.query_selector(sel)
            if el:
                return "checkbox"
        return None

    def _fill_mcq(self, qnum, answer_text):
        """Fill MCQ by matching option label text against answer content.
        Falls back to text input if no radio/checkbox is found (handles
        mis-typed shortanswer questions labeled as multichoice)."""
        try:
            if not answer_text:
                return False

            input_type = self._detect_input_type(qnum)
            if not input_type:
                return self._try_fill_text_input(qnum, answer_text)

            # Split multi-select answers by Chinese semicolon
            answer_parts = [a.strip() for a in answer_text.split('；') if a.strip()]

            # Try multiple name patterns for finding inputs
            input_patterns = [
                f'input[type="{input_type}"][name$=":{qnum}_answer"]',
                f'input[type="{input_type}"][name$=":{qnum}_answer[]"]',
                f'input[type="{input_type}"][name*=":{qnum}_"]',
            ]
            inputs = []
            for sel in input_patterns:
                inputs = self.page.query_selector_all(sel)
                if inputs:
                    break
            if not inputs:
                return False

            # Build label cache (input → label_text)
            label_cache = []
            for inp in inputs:
                text = None
                iid = inp.get_attribute("id")
                if iid:
                    lb = self.page.query_selector(f'label[for="{iid}"]')
                    if lb:
                        text = lb.inner_text()
                if text is None:
                    text = self.page.evaluate(
                        '(el) => { const p = el.closest("label"); return p ? p.innerText : null; }',
                        inp
                    )
                if text is None:
                    text = self.page.evaluate(
                        '(el) => { const n = el.nextSibling; return n && n.nodeType === 3 ? n.textContent.trim() : null; }',
                        inp
                    )
                label_cache.append((inp, text))

            clicked_any = False
            for part in answer_parts:
                norm_part = self._normalize(part)
                matched = False
                # Pass 1: exact match (case-sensitive) — avoids Read vs read
                for inp, text in label_cache:
                    if text and self._normalize(text) == norm_part:
                        try:
                            inp.scroll_into_view_if_needed(timeout=3000)
                        except:
                            pass
                        inp.click()
                        time.sleep(0.3)
                        matched = True
                        clicked_any = True
                        break
                # Pass 2: case-insensitive fallback
                if not matched:
                    for inp, text in label_cache:
                        if text and self._normalize(text).lower() == norm_part.lower():
                            try:
                                inp.scroll_into_view_if_needed(timeout=3000)
                            except:
                                pass
                            inp.click()
                            time.sleep(0.3)
                            matched = True
                            clicked_any = True
                            break
                if not matched:
                    avail = [repr(t)[:60] if t else "?" for _, t in label_cache]
                    self.log(f"    第{qnum}题[{input_type}]: 未匹配\"{part}\", 可用选项: {avail}")

            label_type = "单选" if input_type == "radio" else "多选"
            if clicked_any:
                self.log(f"    第{qnum}题[{label_type}]: \"{answer_text}\"")
                return True

            # Fallback: try text input if radio/checkbox click didn't match
            return self._try_fill_text_input(qnum, answer_text)
        except Exception as e:
            self.log(f"    第{qnum}题: 出错 {e}")
            return False

    def _try_fill_text_input(self, qnum, answer_text):
        """Try to fill a text input (填空/简答) for a given question number.
        Tries multiple selector patterns and setting methods."""
        patterns = [
            f'input[type="text"][name$=":{qnum}_answer"]',
            f'input[type="text"][id$=":{qnum}_answer"]',
            f'input[type="text"][name*="[{qnum}]"]',
            f'textarea[name$=":{qnum}_answer"]',
            f'textarea[id$=":{qnum}_answer"]',
        ]
        for sel in patterns:
            el = self.page.query_selector(sel)
            if el:
                try:
                    el.scroll_into_view_if_needed(timeout=3000)
                except:
                    pass
                # Use JavaScript to set value and dispatch input event (more reliable)
                el.evaluate(
                    '(el, text) => { el.value = text; el.dispatchEvent(new Event("input", {bubbles: true})); el.dispatchEvent(new Event("change", {bubbles: true})); }',
                    answer_text
                )
                self.log(f"    第{qnum}题[填空]: 已填入答案 ({len(answer_text)} 字符)")
                return True
        # JS fallback: find any text input/textarea and return a CSS selector for it
        css_sel = self.page.evaluate("""(qnum) => {
            const all = document.querySelectorAll('input[type="text"], textarea');
            const re = new RegExp('[:_]' + qnum + '[_:]?', 'i');
            for (const el of all) {
                if (el.name && re.test(el.name))
                    return 'input[name="' + el.name + '"], textarea[name="' + el.name + '"]';
                if (el.id && re.test(el.id)) return '#' + CSS.escape(el.id);
                const que = el.closest('.que') || el.closest('div[id*="question"]');
                if (que && que.id && re.test(que.id))
                    return '#' + CSS.escape(que.id) + ' input[type="text"], #' + CSS.escape(que.id) + ' textarea';
            }
            return null;
        }""", qnum)
        if css_sel:
            el = self.page.query_selector(css_sel)
            if el:
                try:
                    el.scroll_into_view_if_needed(timeout=3000)
                except:
                    pass
                el.evaluate(
                    '(el, text) => { el.value = text; el.dispatchEvent(new Event("input", {bubbles: true})); el.dispatchEvent(new Event("change", {bubbles: true})); }',
                    answer_text
                )
                self.log(f"    第{qnum}题[填空-JS]: 已填入答案 ({len(answer_text)} 字符)")
                return True
        return False

    def _fill_essay(self, qnum, code_text, html=None):
        """Fill an essay question - type code into the textarea/editor."""
        try:
            # Wait a moment for Atto editor to initialize
            time.sleep(1)

            # Strategy 1: if there's a contenteditable div (Atto editor), use it
            editor = self.page.query_selector(
                f'[id$=":{qnum}_answer_ideditable"]'
            )
            if editor:
                editor.scroll_into_view_if_needed(timeout=3000)
                time.sleep(0.3)
                editor.click()
                time.sleep(0.3)
                # Insert as HTML (use pre-computed html if available)
                content = html if html else self._html_escape(code_text)
                editor.evaluate(
                    '(el, h) => { el.innerHTML = h; }',
                    content
                )
                editor.evaluate(
                    'el => el.dispatchEvent(new Event("input", {bubbles: true}))'
                )
                self.log(f"    第{qnum}题[代码]: 已填入答案 ({len(code_text)} 字符)")
                return True

            # Strategy 2: find textarea (without :not([hidden]) since Atto hides it)
            textarea = self.page.query_selector(
                f'textarea[name$=":{qnum}_answer"]'
            )
            if textarea:
                is_hidden = textarea.get_attribute("hidden")
                if not is_hidden:
                    textarea.scroll_into_view_if_needed(timeout=3000)
                    textarea.click()
                    time.sleep(0.2)
                    self.page.fill(f'textarea[name$=":{qnum}_answer"]', code_text)
                    self.log(f"    第{qnum}题[代码]: 已填入答案 ({len(code_text)} 字符)")
                else:
                    textarea.evaluate(
                        '(el, text) => { el.value = text; el.dispatchEvent(new Event("input", {bubbles: true})); }',
                        code_text
                    )
                    self.log(f"    第{qnum}题[代码]: 已填入答案 (hidden, {len(code_text)} 字符)")
                return True

            # Strategy 3: try filling a plain text input (short answer)
            text_input = self.page.query_selector(
                f'input[type="text"][name$=":{qnum}_answer"]'
            )
            if text_input:
                text_input.scroll_into_view_if_needed(timeout=3000)
                text_input.click()
                time.sleep(0.2)
                self.page.fill(f'input[type="text"][name$=":{qnum}_answer"]', code_text)
                self.log(f"    第{qnum}题[填空]: 已填入答案 ({len(code_text)} 字符)")
                return True

            self.log(f"    第{qnum}题: 未找到文本输入框")
            return False
        except Exception as e:
            self.log(f"    第{qnum}题: 出错 {e}")
            return False

    @staticmethod
    def _html_escape(text):
        """Convert plain text to HTML-safe for Atto editor."""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        parts = text.split("\n\n")
        if len(parts) > 1:
            return "<p>" + "</p><p>".join(
                p.replace("\n", "<br>") for p in parts
            ) + "</p>"
        text = text.replace("\n", "<br>")
        return f"<p>{text}</p>" if text else text

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
