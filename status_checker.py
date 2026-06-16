"""
Status Checker - 虚拟浏览器多策略状态检测模块

用法:
  from status_checker import StatusChecker
  sc = StatusChecker(storage_file=".login_storage.json")
  sc.start_browser()
  if sc.check_login():
      results = sc.check_all_activities("http://10.10.15.23/course/view.php?id=14&section=3")
      # results = {387: {"completed": True, "score": "10.00/10.00"},
      #            415: {"completed": False, "score": ""}, ...}
  sc.close()
"""

import os, json, time, re
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout


class StatusChecker:
    """虚拟浏览器状态检测器 - 三策略递进检测"""

    STRATEGY_FAST = "fast"       # 仅从课程页面解析完成标记
    STRATEGY_BALANCED = "balanced"  # 课程页面 + 关键作业单独检查
    STRATEGY_ACCURATE = "accurate"  # 逐个页面精确检查

    def __init__(self, storage_file=None, headless=True, callback=None):
        self.storage_file = storage_file
        self.headless = headless
        self.callback = callback
        self._pw = None
        self.browser = None
        self.context = None
        self.page = None

    def log(self, msg):
        if self.callback:
            self.callback(msg)

    def start_browser(self, use_storage=True):
        """启动虚拟浏览器（支持 headless 模式）"""
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        )
        if use_storage and self.storage_file and os.path.exists(self.storage_file):
            with open(self.storage_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            self.context = self.browser.new_context(
                storage_state=state,
                viewport={"width": 1280, "height": 720},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"
                )
            )
            self.log("[+] 已加载本地登录态")
        else:
            self.context = self.browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"
                )
            )
        self.page = self.context.new_page()
        # 反检测: 隐藏 webdriver 特征
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

    def check_login(self, url=None):
        """验证登录态是否有效"""
        check_url = url or "http://10.10.15.23/course/view.php?id=14"
        try:
            self.page.goto(check_url, wait_until="domcontentloaded", timeout=30000)
            kw = ["oauth", "login", "authorize", "login/index"]
            if any(k in self.page.url.lower() for k in kw):
                self.log("[-] 登录态已过期")
                return False
            self.log("[+] 登录态有效")
            return True
        except Exception as e:
            self.log(f"[-] 页面访问失败: {e}")
            return False

    # =========================================================
    #  策略一: 课程页面快速检测（基于 Moodle 完成标记 + 成绩标记）
    # =========================================================
    def _fast_check_from_course_page(self, section_url):
        """
        从课程页面解析活动完成状态。
        返回 {activity_id: True/False, ...} 和未确定的活动 ID 列表。
        """
        results = {}
        undetermined = []

        try:
            self.page.goto(section_url, wait_until="networkidle", timeout=30000)
            time.sleep(1)
        except Exception as e:
            self.log(f"[-] 加载课程页面失败: {e}")
            return results, []

        page_data = self.page.evaluate("""() => {
            const items = [];
            document.querySelectorAll('li.activity').forEach(li => {
                const link = li.querySelector('a[href*="id="]');
                if (!link) return;
                const m = link.href.match(/id=(\\d+)/);
                if (!m) return;
                const id = parseInt(m[1]);
                const html = li.innerHTML;
                const text = li.innerText || '';

                let hasCompletionMark =
                    html.includes('completion-manual-y') ||
                    html.includes('completion-auto-y') ||
                    html.includes('completion_complete') ||
                    li.querySelector('.completion-complete') !== null ||
                    li.querySelector('.completion-y') !== null;

                let hasGrade = li.querySelector('.grade') !== null ||
                    li.querySelector('.feedbacktext') !== null ||
                    li.querySelector('.gradereport') !== null;

                let hasSubmitText =
                    text.includes('已提交') ||
                    text.includes('Submitted') ||
                    text.includes('submitted') ||
                    text.includes('已完成');

                const hasIncomplete =
                    html.includes('completion-manual-n') ||
                    html.includes('completion-auto-n') ||
                    html.includes('completion-incomplete') ||
                    li.querySelector('.completion-incomplete') !== null ||
                    li.querySelector('.completion-n') !== null;

                const hasFeedback = li.querySelector('a[href*="grade"]') !== null ||
                    text.includes('查看') || text.includes('feedback');

                // 提取分数文本（多种策略）
                let gradeText = '';
                const gradeEl = li.querySelector('.grade, .score, .gradereport span, .details .grade, .activity-grade');
                if (gradeEl) {
                    gradeText = gradeEl.innerText.trim();
                }
                // 尝试从全文本中提取 "X/Y" 格式分数
                if (!gradeText) {
                    const m2 = text.match(/(\\d+\\.?\\d*)\\s*\\/\\s*(\\d+\\.?\\d*)/);
                    if (m2) gradeText = m2[0];
                }

                // 增强: 考试/测验活动专用检测
                const isQuiz = html.includes('modtype_quiz') || link.href.includes('/mod/quiz/');
                if (isQuiz) {
                    // 测验页面上的 "分数:"、"Grade:"、"最高分:"、"得分:" 等文本
                    if (text.includes('最高分') || text.includes('分数:') || text.includes('Grade:'))
                        hasSubmitText = true;
                    // 活动包含数字分值 (如 "10.00/10.00" 一定有 "/")
                    if (gradeText) {
                        hasGrade = true;
                        hasCompletionMark = true;
                    }
                }

                items.push({
                    id, hasCompletionMark, hasGrade, hasSubmitText,
                    hasIncomplete, hasFeedback, gradeText,
                    html_preview: html.substring(0, 200)
                });
            });
            return items;
        }""")

        for item in page_data:
            aid = item["id"]
            grade_text = item.get("gradeText", "")
            has_incomplete = item["hasIncomplete"]
            has_grade = bool(grade_text) or item["hasGrade"]

            if has_incomplete:
                results[aid] = {"completed": False, "score": grade_text}
            elif has_grade:
                # 有分数文本即视为已完成
                results[aid] = {"completed": True, "score": grade_text}
            elif item["hasCompletionMark"] or item["hasSubmitText"] or item["hasFeedback"]:
                results[aid] = {"completed": True, "score": grade_text}
            elif item["hasGrade"]:
                # hasGrade 已在上面的 has_grade 处理过了
                results[aid] = {"completed": True, "score": grade_text}
            else:
                undetermined.append(aid)

        self.log(f"  [fast] 课程页面检测: {len(results)} 个确定, {len(undetermined)} 个待定")
        if page_data:
            d = page_data[0]
            self.log(f"  [debug] 首项 id={d['id']}: gradeText=[{d.get('gradeText','')}] "
                     f"hasGrade={d.get('hasGrade')} hasMark={d.get('hasCompletionMark')} "
                     f"hasSubmit={d.get('hasSubmitText')} hasIncomplete={d.get('hasIncomplete')} "
                     f"hasFB={d.get('hasFeedback')}")
        return results, undetermined

    # =========================================================
    #  策略二: 按页面特征深度检查（批量加载，逐页确认）
    # =========================================================
    def _deep_check_assignments(self, ids, base_url):
        """
        逐个导航到作业提交页面进行精确检测。
        返回 {activity_id: True/False, ...}
        """
        results = {}
        total = len(ids)

        for i, aid in enumerate(ids):
            self.log(f"  [deep] ({i+1}/{total}) 检查 id={aid}...")
            url = f"{base_url}/mod/assign/view.php?id={aid}&action=editsubmission"
            try:
                self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(1.5)
                status = self.page.evaluate("""() => {
                    const html = document.body.innerHTML;
                    const text = (document.body.innerText || '').toLowerCase();

                    // 1. 标准提交收据
                    const receipt = document.querySelector('.submissionreceipt');
                    if (receipt) {
                        const style = getComputedStyle(receipt);
                        if (style.display !== 'none' && style.visibility !== 'hidden')
                            return 'completed';
                    }

                    // 2. 提交状态文本
                    const st = document.querySelector('.submissionstatustext, .submission-status, .submissionmsg');
                    if (st) {
                        const t = st.innerText.toLowerCase();
                        if (t.includes('已提交') || (t.includes('submitted') && !t.includes('not')))
                            return 'completed';
                        if (t.includes('draft') || t.includes('未提交') || t.includes('none'))
                            return 'incomplete';
                    }

                    // 3. 代码题专用: ace editor + 提交按钮
                    const hasEditor = document.getElementById('ace_editor') !== null;
                    const submitBtn = document.getElementById('submit_assign') ||
                        document.querySelector('button[name=submit_assign]');
                    if (hasEditor) {
                        if (submitBtn && submitBtn.offsetParent !== null) return 'incomplete';
                        // editor 存在但不显示提交按钮 => 可能已提交
                        const editorContent = document.querySelector('.ace_content');
                        if (editorContent && editorContent.innerText.trim().length > 0)
                            return 'completed';
                    }

                    // 4. 已提交的链接/按钮特征
                    if (document.querySelector('a[href*="action=editsubmission"]')) return 'completed';
                    if (document.querySelector('.submission_actions')) return 'completed';

                    // 5. 编辑框/textarea 特征
                    const ta = document.querySelector('textarea');
                    const editable = document.querySelector('[contenteditable="true"]');
                    if (!ta && !editable) {
                        // 无编辑区域 => 可能已提交
                        if (text.includes('grade') || text.includes('feedback') || text.includes('已评'))
                            return 'completed';
                        if (text.includes('submitted') || text.includes('已提交'))
                            return 'completed';
                        return 'completed';  // 无提交框即视为已完成
                    }

                    // 6. 页面文本线索
                    if (text.includes('submitted') && text.includes('submission')) return 'completed';
                    if (text.includes('已提交') || text.includes('已完成')) return 'completed';

                    // 7. 检查是否有编辑提交框且可见
                    if (ta && ta.offsetParent !== null) return 'incomplete';
                    if (editable && editable.offsetParent !== null) return 'incomplete';

                    return 'incomplete';
                }""")

                results[aid] = {"completed": status == "completed", "score": ""}
            except Exception as e:
                self.log(f"  [-]: id={aid} 检测异常: {e}")
                results[aid] = {"completed": False, "score": ""}

        return results

    def _deep_check_exams(self, ids, url_map):
        """检查考试页面的完成状态 + 提取最高分 (逐页精确检测)"""
        results = {}
        total = len(ids)

        for i, aid in enumerate(ids):
            url = url_map.get(aid, "")
            if not url:
                results[aid] = {"completed": False, "score": ""}
                continue
            self.log(f"  [deep] ({i+1}/{total}) 考试 id={aid}...")
            try:
                self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(1.5)
                data = self.page.evaluate("""() => {
                    const text = (document.body.innerText || '').trim();
                    const html = document.body.innerHTML;

                    let completed = false;
                    let score = '';

                    // ── 提取最高分（多种策略） ──

                    // 策略A: 查找 "X/Y" 格式分数,取最大值
                    const allGrades = [];
                    const re = /(\\d+\\.?\\d*)\\s*\\/\\s*(\\d+\\.?\\d*)/g;
                    let m;
                    while ((m = re.exec(text)) !== null) {
                        allGrades.push({ num: parseFloat(m[1]), max: parseFloat(m[2]), raw: m[0] });
                    }

                    // 策略B: 查找 "得X分"、"X分"、"X分/Y"
                    const cnRe = /(\\d+\\.?\\d*)\\s*分/;
                    const cnM = text.match(cnRe);
                    if (cnM && !allGrades.length) {
                        allGrades.push({ num: parseFloat(cnM[1]), max: 0, raw: cnM[1] });
                    }

                    // 取最高分
                    if (allGrades.length > 0) {
                        allGrades.sort((a, b) => b.num - a.num);
                        const best = allGrades[0];
                        score = best.raw;
                        if (best.max > 0) score = best.raw;
                        completed = true;
                    }

                    // ── 状态判断 ──
                    const hasAttemptBtn = Array.from(
                        document.querySelectorAll('button, input[type=submit]')
                    ).some(b => {
                        const t = (b.innerText || b.value || '').toLowerCase();
                        return t.includes('现在参加') || t.includes('继续上次');
                    });

                    // 已提交/已完成特征
                    const hasSubmittedText =
                        text.includes('已提交') ||
                        text.includes('Your attempt') ||
                        text.includes('attempt') ||
                        html.includes('summaries') ||
                        html.includes('reviewlink');

                    // 有明显分数 或 已提交文本 → 已完成
                    if (score && hasSubmittedText) {
                        completed = true;
                    } else if (score && !hasAttemptBtn) {
                        completed = true;
                    } else if (hasSubmittedText && !hasAttemptBtn) {
                        completed = true;
                    } else if (hasAttemptBtn) {
                        completed = false;
                    } else if (score) {
                        completed = true;
                    } else {
                        completed = false;
                    }

                    return { completed, score };
                }""")
                results[aid] = data
                if data.get("score"):
                    self.log(f"    -> 分数: {data['score']}, 已完成={data['completed']}")
                else:
                    self.log(f"    -> 无分数, 已完成={data['completed']}")
            except Exception as e:
                self.log(f"  [-]: 考试 id={aid} 检测异常: {e}")
                results[aid] = {"completed": False, "score": ""}

        return results

    # =========================================================
    #  统一检测入口
    # =========================================================
    def check_all_activities(self, section_url, activity_ids=None, url_map=None,
                             strategy=STRATEGY_BALANCED):
        """
        统一状态检测入口。

        参数:
          section_url  - 课程小节 URL（如 SECTION3_URL 或 SECTION4_URL）
          activity_ids - 要检测的活动 ID 列表，None=检测全部
          url_map      - 活动 URL 映射 {id: url}，用于考试
          strategy     - STRATEGY_FAST / STRATEGY_BALANCED / STRATEGY_ACCURATE

        返回:
          {activity_id: {"completed": bool, "score": str}, ...}
        """
        start = time.time()
        all_results = {}
        is_exam = "section=4" in str(section_url)

        if is_exam and url_map:
            # ── 考试模式: 直接逐页深度检测 ──
            # 课程页面不可靠，必须导航到每个考试页面提取状态 + 最高分
            ids = activity_ids or list(url_map.keys())
            self.log(f"[*] 考试模式: 逐页检测 {len(ids)} 项 (获取最高分)...")
            deep_results = self._deep_check_exams(ids, url_map)
            all_results.update(deep_results)

        else:
            # ── 作业模式: 课程页面快速检测 + 可选深度检测 ──
            fast_results, undetermined = self._fast_check_from_course_page(section_url)
            all_results.update(fast_results)

            if activity_ids is not None:
                all_results = {k: v for k, v in all_results.items() if k in activity_ids}
                undetermined = [aid for aid in undetermined if aid in activity_ids]
                for aid in activity_ids:
                    if aid not in all_results and aid not in undetermined:
                        undetermined.append(aid)

            if strategy != self.STRATEGY_FAST and undetermined:
                base_url = "http://10.10.15.23"
                deep_results = self._deep_check_assignments(undetermined, base_url)
                all_results.update(deep_results)

        elapsed = time.time() - start
        self.log(f"[+] 检测完成 ({strategy}), 耗时 {elapsed:.1f}s")
        return all_results

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
