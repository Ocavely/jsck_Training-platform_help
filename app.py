import os, sys, threading, queue, time, json
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
except ImportError:
    print("tkinter not available. Install python3-tk or use --no-gui flag.")
    sys.exit(1)

from config import ASSIGNMENTS, ANSWER_DIR, CACHE_DIR, LOGS_DIR, BASE_DIR
from crawler import Crawler
from answer_gen import generate_all, generate_selected
from submitter import Submitter


STATUS_MAP = {
    "pending": "待处理", "crawled": "已抓取", "generated": "已生成",
    "passed": "已通过", "failed": "失败", "submitted": "已提交", "skipped": "跳过",
}

TYPE_MAP = {"code_assign": "代码", "regular": "报告"}


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("人工智能实训平台作业辅助")
        self.root.geometry("960x720")
        self.root.minsize(800, 600)

        self.logged_in = False
        self.crawler = None
        self.submitter = None
        self.assign_data = {}
        self.task_queue = queue.Queue()

        self._build_ui()
        self._poll_queue()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("vista")
        style.configure("Success.TLabel", foreground="green")
        style.configure("Fail.TLabel", foreground="red")

        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 登录区 ---
        login_frame = ttk.LabelFrame(main_frame, text=" 登录 ", padding=8)
        login_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(login_frame, text="状态:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.login_status_var = tk.StringVar(value="未登录")
        self.login_status_label = ttk.Label(login_frame, textvariable=self.login_status_var)
        self.login_status_label.grid(row=0, column=1, sticky=tk.W, padx=5)

        self.login_btn = ttk.Button(login_frame, text="登录", command=self._do_login)
        self.login_btn.grid(row=0, column=2, padx=5)

        self.logout_btn = ttk.Button(login_frame, text="退出登录", command=self._do_logout, state=tk.DISABLED)
        self.logout_btn.grid(row=0, column=3, padx=5)

        list_frame = ttk.LabelFrame(main_frame, text=" 作业列表 ", padding=8)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        cols = ("select", "id", "title", "type", "status")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=12)
        self.tree.heading("select", text=" ")
        self.tree.heading("id", text="ID")
        self.tree.heading("title", text="名称")
        self.tree.heading("type", text="类型")
        self.tree.heading("status", text="状态")
        self.tree.column("select", width=30, anchor=tk.CENTER)
        self.tree.column("id", width=50, anchor=tk.CENTER)
        self.tree.column("title", width=250)
        self.tree.column("type", width=80, anchor=tk.CENTER)
        self.tree.column("status", width=100, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        vsb.grid(row=0, column=1, sticky=tk.NS)
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)
        self.tree.tag_configure("passed", foreground="green")
        self.tree.tag_configure("failed", foreground="red")
        self.tree.tag_configure("skipped", foreground="gray")
        self.tree.tag_configure("crawled", foreground="blue")

        for assign_id, title, atype in ASSIGNMENTS:
            short_type = TYPE_MAP.get(atype, atype)
            self.tree.insert("", tk.END, values=("", assign_id, title, short_type, "待处理"),
                             tags=("pending",))
            self.assign_data[assign_id] = {"title": title, "type": atype, "status": "pending"}

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        self.crawl_btn = ttk.Button(btn_frame, text="抓取作业", command=self._do_crawl, state=tk.DISABLED)
        self.crawl_btn.pack(side=tk.LEFT, padx=3)

        self.gen_btn = ttk.Button(btn_frame, text="生成答案", command=self._do_generate, state=tk.DISABLED)
        self.gen_btn.pack(side=tk.LEFT, padx=3)

        self.submit_selected_btn = ttk.Button(btn_frame, text="提交选中", command=self._do_submit_selected, state=tk.DISABLED)
        self.submit_selected_btn.pack(side=tk.LEFT, padx=3)

        self.submit_all_btn = ttk.Button(btn_frame, text="提交全部（代码题）", command=self._do_submit_all, state=tk.DISABLED)
        self.submit_all_btn.pack(side=tk.LEFT, padx=3)

        self.view_387_btn = ttk.Button(btn_frame, text="打开网页", command=self._open_387, state=tk.DISABLED)
        self.view_387_btn.pack(side=tk.LEFT, padx=3)

        self.toggle_all_var = tk.IntVar()
        self.toggle_all_cb = ttk.Checkbutton(btn_frame, text="全选", variable=self.toggle_all_var,
                                             command=self._toggle_all)
        self.toggle_all_cb.pack(side=tk.RIGHT, padx=5)

        # --- 进度条 ---
        prog_frame = ttk.Frame(main_frame)
        prog_frame.pack(fill=tk.X, pady=(0, 5))

        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(prog_frame, orient=tk.HORIZONTAL,
                                            variable=self.progress_var, mode="determinate")
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.progress_label = ttk.Label(prog_frame, text="0%", width=6)
        self.progress_label.pack(side=tk.RIGHT, padx=5)

        # --- 日志区 ---
        log_frame = ttk.LabelFrame(main_frame, text=" 运行日志 ", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD,
                                                   font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] {msg}\n")
        self.log_text.see(tk.END)

    def _poll_queue(self):
        try:
            while True:
                task, args = self.task_queue.get_nowait()
                if task == "log":
                    self._log(args)
                elif task == "progress":
                    cur, total = args
                    pct = int(cur / total * 100) if total > 0 else 0
                    self.progress_var.set(pct)
                    self.progress_label.config(text=f"{pct}%")
                elif task == "login_done":
                    self.logged_in = True
                    self.login_status_var.set("已登录")
                    self.login_status_label.config(foreground="green")
                    self.login_btn.config(state=tk.DISABLED)
                    self.logout_btn.config(state=tk.NORMAL)
                    self.crawl_btn.config(state=tk.NORMAL)
                    self.gen_btn.config(state=tk.NORMAL)
                elif task == "crawl_done":
                    self.crawl_btn.config(state=tk.NORMAL)
                    self.view_387_btn.config(state=tk.NORMAL)
                    self.gen_btn.config(state=tk.NORMAL)
                elif task == "gen_done":
                    self.gen_btn.config(state=tk.NORMAL)
                    self.submit_selected_btn.config(state=tk.NORMAL)
                    self.submit_all_btn.config(state=tk.NORMAL)
                elif task == "submit_progress":
                    assign_id, status, msg = args
                    self._update_assign_status(assign_id, status, msg)
                elif task == "submit_done":
                    self.submit_selected_btn.config(state=tk.NORMAL)
                    self.submit_all_btn.config(state=tk.NORMAL)
                elif task == "finished":
                    self.root.bell()
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queue)

    def _update_assign_status(self, assign_id, status, msg=""):
        label = STATUS_MAP.get(status, status)
        for child in self.tree.get_children():
            vals = self.tree.item(child, "values")
            if len(vals) >= 2 and vals[1] == assign_id:
                new_vals = list(vals)
                new_vals[4] = label
                self.tree.item(child, values=tuple(new_vals), tags=(status,))
                self.assign_data[assign_id]["status"] = status
                break

    def _on_tree_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        col = self.tree.identify_column(event.x)
        if col == "#1":
            vals = list(self.tree.item(item, "values"))
            vals[0] = "" if vals[0] else "*"
            self.tree.item(item, values=tuple(vals))

    def _toggle_all(self):
        val = self.toggle_all_var.get()
        marker = "*" if val else ""
        for child in self.tree.get_children():
            vals = list(self.tree.item(child, "values"))
            vals[0] = marker
            self.tree.item(child, values=tuple(vals))

    def _get_selected_ids(self):
        ids = []
        for child in self.tree.get_children():
            vals = self.tree.item(child, "values")
            if len(vals) >= 2 and vals[0] == "*":
                try:
                    ids.append(int(vals[1]))
                except:
                    pass
        return ids

    def _do_login(self):
        def task():
            self.task_queue.put(("log", "[*] 正在启动浏览器登录..."))
            try:
                c = Crawler(callback=lambda m: self.task_queue.put(("log", m)))
                ok = c.login_only()
                self.crawler = c
                if ok:
                    self.task_queue.put(("login_done", None))
                    self.task_queue.put(("log", "[+] 登录成功"))
                else:
                    self.task_queue.put(("log", "[-] 登录失败"))
            except Exception as e:
                self.task_queue.put(("log", f"[-] 出错: {e}"))

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def _do_logout(self):
        if self.crawler:
            try:
                self.crawler.close()
            except:
                pass
            self.crawler = None
        self.logged_in = False
        self.login_status_var.set("未登录")
        self.login_status_label.config(foreground="black")
        self.login_btn.config(state=tk.NORMAL)
        self.logout_btn.config(state=tk.DISABLED)
        self.crawl_btn.config(state=tk.DISABLED)
        self.gen_btn.config(state=tk.DISABLED)
        self.submit_selected_btn.config(state=tk.DISABLED)
        self.submit_all_btn.config(state=tk.DISABLED)
        self.view_387_btn.config(state=tk.DISABLED)
        self.task_queue.put(("log", "[*] 已退出登录"))

        sf = os.path.join(BASE_DIR, ".login_storage.json")
        if os.path.exists(sf):
            os.remove(sf)

    def _get_selected_ids_for_action(self, action_name="操作"):
        sel = self._get_selected_ids()
        if not sel:
            self.task_queue.put(("log", f"[-] 请先在列表中勾选要{action_name}的作业"))
            return None
        return sel

    def _do_crawl(self):
        sel = self._get_selected_ids_for_action("抓取")
        if not sel:
            return

        def task():
            self.task_queue.put(("log", f"[*] 正在抓取 {len(sel)} 个作业..."))
            c = Crawler(callback=lambda m: self.task_queue.put(("log", m)))
            try:
                data = c.crawl_selected(sel)
                self.crawler = c
                self.task_queue.put(("log", f"[+] 已抓取 {len(data)} 个作业"))
            except Exception as e:
                self.task_queue.put(("log", f"[-] 抓取出错: {e}"))
            self.task_queue.put(("crawl_done", None))

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def _do_generate(self):
        sel = self._get_selected_ids_for_action("生成答案")
        if not sel:
            return
        self.gen_btn.config(state=tk.DISABLED)

        def task():
            try:
                total = len(sel)

                def prog(cur, tot):
                    self.task_queue.put(("progress", (cur, tot)))

                count = generate_selected(sel, callback=prog)
                self.task_queue.put(("progress", (count, count)))
                self.task_queue.put(("log", f"[+] 已生成 {count} 个答案文件 (answer/)"))
                self.task_queue.put(("gen_done", None))
            except Exception as e:
                self.task_queue.put(("log", f"[-] 生成答案出错: {e}"))
                self.task_queue.put(("gen_done", None))

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def _do_submit_all(self):
        code_assigns = [(aid, title) for aid, title, atype in ASSIGNMENTS if atype == "code_assign"]
        self._run_submission(code_assigns)

    def _do_submit_selected(self):
        sel = self._get_selected_ids()
        if not sel:
            messagebox.showinfo("提示", "未选择任何作业，请点击左侧选择框进行选择")
            return
        filtered = [(aid, title) for aid, title, atype in ASSIGNMENTS if aid in sel and atype == "code_assign"]
        if not filtered:
            messagebox.showinfo("提示", "所选作业中没有代码题")
            return
        self._run_submission(filtered)

    def _run_submission(self, assign_list):
        self.submit_selected_btn.config(state=tk.DISABLED)
        self.submit_all_btn.config(state=tk.DISABLED)

        def task():
            try:
                sub = Submitter(callback=lambda m: self.task_queue.put(("log", m)))
                ok = sub.start()
                if not ok:
                    self.task_queue.put(("log", "[-] 提交阶段登录失败"))
                    self.task_queue.put(("submit_done", None))
                    return

                total = len(assign_list)

                def prog(cur, tot, aid, status, msg):
                    self.task_queue.put(("progress", (cur, tot)))
                    self.task_queue.put(("submit_progress", (aid, status, msg)))

                results = sub.submit_assignments(assign_list, progress_callback=prog)
                sub.close()

                passed = sum(1 for r in results.values() if r.get("status") in ("passed", "submitted"))
                failed = sum(1 for r in results.values() if r.get("status") == "failed")
                skipped = sum(1 for r in results.values() if r.get("status") == "skipped")

                self.task_queue.put(("log", f"[+] 完成! 通过: {passed}, 失败: {failed}, 跳过: {skipped}"))
                self.task_queue.put(("progress", (total, total)))
                self.task_queue.put(("submit_done", None))
                self.task_queue.put(("finished", None))
            except Exception as e:
                self.task_queue.put(("log", f"[-] 提交出错: {e}"))
                self.task_queue.put(("submit_done", None))

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def _open_387(self):
        import subprocess
        url = "http://10.10.15.23/mod/assign/view.php?id=387&action=editsubmission"
        try:
            subprocess.Popen(["start", url], shell=True)
        except:
            pass
        self.task_queue.put(("log", "[*] 已在浏览器中打开，请手动提交"))

    def run(self):
        self.root.mainloop()
        if self.crawler:
            try:
                self.crawler.close()
            except:
                pass


if __name__ == "__main__":
    app = App()
    app.run()
