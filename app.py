import os, sys, threading, queue, time, json
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
except ImportError:
    print("tkinter not available. Install python3-tk or use --no-gui flag.")
    sys.exit(1)

from config import ASSIGNMENTS, ANSWER_DIR, CACHE_DIR, LOGS_DIR, BASE_DIR, COURSE_URL, ACCOUNTS_FILE, SECTION4_URL
from crawler import Crawler
from answer_gen import generate_all, generate_selected, generate_exam_answers
from submitter import Submitter
from exam_submitter import ExamSubmitter


STATUS_MAP = {
    "pending": "待处理", "crawled": "已抓取", "generated": "已生成",
    "passed": "已通过", "failed": "失败", "submitted": "已提交", "skipped": "跳过",
    "completed": "已完成", "uncompleted": "未完成",
}

TYPE_MAP = {"code_assign": "代码", "regular": "报告"}


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("人工智能实训平台作业辅助")
        self.root.geometry("960x720")
        self.root.minsize(800, 600)

        self.logged_in = False
        self.assign_data = {}
        self.task_queue = queue.Queue()

        self.accounts = []
        self.current_account_id = None
        self._load_accounts()

        self.mode = "assign"
        self.exam_assignments = []
        self.exam_assign_data = {}
        self.exam_url_map = {}
        self.exam_loaded = False

        self._build_ui()
        self._auto_select_account()
        self._poll_queue()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("vista")
        style.configure("Success.TLabel", foreground="green")
        style.configure("Fail.TLabel", foreground="red")

        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 账号区 ---
        login_frame = ttk.LabelFrame(main_frame, text=" 账号 ", padding=8)
        login_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(login_frame, text="当前账号:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.account_var = tk.StringVar()
        self.account_combo = ttk.Combobox(login_frame, textvariable=self.account_var,
                                          state="readonly", width=20)
        self.account_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.account_combo.bind("<<ComboboxSelected>>", self._on_account_change)

        self.manage_account_btn = ttk.Button(login_frame, text="管理账号",
                                              command=self._show_account_manager)
        self.manage_account_btn.grid(row=0, column=2, padx=5)

        ttk.Label(login_frame, text="状态:").grid(row=0, column=3, sticky=tk.W, padx=(15, 5))
        self.login_status_var = tk.StringVar(value="未登录")
        self.login_status_label = ttk.Label(login_frame, textvariable=self.login_status_var)
        self.login_status_label.grid(row=0, column=4, sticky=tk.W, padx=5)

        self.login_btn = ttk.Button(login_frame, text="登录", command=self._login_current_account)
        self.login_btn.grid(row=0, column=5, padx=5)

        self.logout_btn = ttk.Button(login_frame, text="退出登录", command=self._do_logout, state=tk.DISABLED)
        self.logout_btn.grid(row=0, column=6, padx=5)

        self.login_all_btn = ttk.Button(login_frame, text="一键登录", command=self._login_all_accounts)
        self.login_all_btn.grid(row=0, column=7, padx=(5, 0))

        self._refresh_account_combo()

        # --- 模式切换 ---
        mode_frame = ttk.Frame(main_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(mode_frame, text="模式:").pack(side=tk.LEFT, padx=(0, 5))
        self.mode_var = tk.StringVar(value="assign")
        ttk.Radiobutton(mode_frame, text="作业列表", variable=self.mode_var,
                        value="assign", command=self._on_mode_change).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(mode_frame, text="考试列表", variable=self.mode_var,
                        value="exam", command=self._on_mode_change).pack(side=tk.LEFT, padx=2)

        # --- 考试时间选择器 ---
        time_frame = ttk.Frame(main_frame)
        time_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(time_frame, text="考试时间:").pack(side=tk.LEFT, padx=(0, 5))
        self.timer_sec_var = tk.IntVar(value=120)
        self.timer_spinbox = ttk.Spinbox(time_frame, from_=0, to=99999,
                                          textvariable=self.timer_sec_var, width=7)
        self.timer_spinbox.pack(side=tk.LEFT)
        ttk.Label(time_frame, text="秒 (0=不修改)").pack(side=tk.LEFT, padx=5)

        self.list_frame = ttk.LabelFrame(main_frame, text=" 作业列表 ", padding=8)
        self.list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        cols = ("select", "id", "title", "type", "status", "score")
        self.tree = ttk.Treeview(self.list_frame, columns=cols, show="headings", height=12)
        self.tree.heading("select", text=" ")
        self.tree.heading("id", text="ID")
        self.tree.heading("title", text="名称")
        self.tree.heading("type", text="类型")
        self.tree.heading("status", text="状态")
        self.tree.heading("score", text="分数")
        self.tree.column("select", width=30, anchor=tk.CENTER)
        self.tree.column("id", width=50, anchor=tk.CENTER)
        self.tree.column("title", width=250)
        self.tree.column("type", width=80, anchor=tk.CENTER)
        self.tree.column("status", width=100, anchor=tk.CENTER)
        self.tree.column("score", width=100, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky=tk.NSEW)
        vsb.grid(row=0, column=1, sticky=tk.NS)
        self.list_frame.grid_rowconfigure(0, weight=1)
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)
        self.tree.tag_configure("passed", foreground="green")
        self.tree.tag_configure("failed", foreground="red")
        self.tree.tag_configure("skipped", foreground="gray")
        self.tree.tag_configure("crawled", foreground="blue")
        self.tree.tag_configure("completed", foreground="green")
        self.tree.tag_configure("uncompleted", foreground="orange")

        for assign_id, title, atype in ASSIGNMENTS:
            short_type = TYPE_MAP.get(atype, atype)
            self.tree.insert("", tk.END, values=("", assign_id, title, short_type, "待处理", ""),
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

        self.check_status_btn = ttk.Button(btn_frame, text="检查状态", command=self._do_check_completion, state=tk.DISABLED)
        self.check_status_btn.pack(side=tk.LEFT, padx=3)

        self.toggle_all_var = tk.IntVar()
        self.toggle_all_cb = ttk.Checkbutton(btn_frame, text="全选", variable=self.toggle_all_var,
                                             command=self._toggle_all)
        self.toggle_all_cb.pack(side=tk.RIGHT, padx=5)

        self.select_uncompleted_btn = ttk.Button(btn_frame, text="全选未完成",
                                                  command=self._toggle_all_uncompleted)
        self.select_uncompleted_btn.pack(side=tk.RIGHT, padx=3)

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
                    self.check_status_btn.config(state=tk.NORMAL)
                elif task == "crawl_done":
                    self.crawl_btn.config(state=tk.NORMAL)
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
                elif task == "check_status_done":
                    self.check_status_btn.config(state=tk.NORMAL)
                elif task == "check_completion":
                    aid = args[0]
                    completed = args[1]
                    score = args[2] if len(args) >= 3 else ""
                    st = "completed" if completed else "uncompleted"
                    self._update_assign_status(aid, st, "已完成" if completed else "未完成", score)
                elif task == "finished":
                    self.root.bell()
                elif task == "refresh_ui":
                    self._refresh_account_combo()
                    self._update_account_ui()
                    self.login_all_btn.config(state=tk.NORMAL)
                elif task == "exam_list_loaded":
                    items, url_map = args
                    self.exam_assignments = items
                    self.exam_assign_data = {aid: {"title": t, "type": tp, "status": "pending"}
                                             for aid, t, tp in items}
                    self.exam_url_map = url_map
                    self.exam_loaded = True
                    if self.mode == "exam":
                        self._rebuild_tree()
                    self._log(f"[+] 考试列表加载完成，共 {len(items)} 项")
                elif task == "exam_list_error":
                    self._log(f"[-] 加载考试列表失败: {args}")
                    self.mode_var.set("assign")
                    self.mode = "assign"
                    self._rebuild_tree()
        except queue.Empty:
            pass
        self.root.after(200, self._poll_queue)

    def _update_assign_status(self, assign_id, status, msg="", score=""):
        label = STATUS_MAP.get(status, status)
        if score:
            label = f"{label} ({score})"
        data = self.assign_data if self.mode == "assign" else self.exam_assign_data
        for child in self.tree.get_children():
            vals = self.tree.item(child, "values")
            if len(vals) >= 2 and int(vals[1]) == assign_id:
                new_vals = list(vals)
                new_vals[4] = label
                new_vals[5] = score
                self.tree.item(child, values=tuple(new_vals), tags=(status,))
                if assign_id in data:
                    data[assign_id]["status"] = status
                    if score:
                        data[assign_id]["score"] = score
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

    def _toggle_all_uncompleted(self):
        data = self.assign_data if self.mode == "assign" else self.exam_assign_data
        for child in self.tree.get_children():
            vals = list(self.tree.item(child, "values"))
            if len(vals) >= 2:
                aid = int(vals[1])
                st = data.get(aid, {}).get("status", "pending")
                vals[0] = "" if st == "completed" else "*"
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

    # ─── 账号管理 ─────────────────────────────────────────────

    def _get_account_storage(self, account_id):
        return os.path.join(BASE_DIR, f".login_storage_{account_id}.json")

    def _load_accounts(self):
        if not os.path.exists(ACCOUNTS_FILE):
            self.accounts = []
            return
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                self.accounts = json.load(f)
        except:
            self.accounts = []

    def _save_accounts(self):
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.accounts, f, ensure_ascii=False, indent=2)

    def _get_account_by_id(self, aid):
        for a in self.accounts:
            if a["id"] == aid:
                return a
        return None

    def _refresh_account_combo(self):
        entries = []
        for a in self.accounts:
            label = f"#{a['id']} {a['nickname']} ({a['username']})"
            entries.append(label)
        self.account_combo["values"] = entries
        if entries and self.current_account_id is not None:
            for a in self.accounts:
                if a["id"] == self.current_account_id:
                    self.account_var.set(f"#{a['id']} {a['nickname']} ({a['username']})")
                    break
            else:
                self.current_account_id = None
        if not entries or self.current_account_id is None:
            self.account_var.set("")
            self.current_account_id = None
            self.login_status_var.set("未登录")
            self.login_status_label.config(foreground="black")
            self.login_btn.config(state=tk.DISABLED)
            self.logout_btn.config(state=tk.DISABLED)

    def _on_account_change(self, event):
        sel = self.account_combo.current()
        if 0 <= sel < len(self.accounts):
            self.current_account_id = self.accounts[sel]["id"]
            self._update_account_ui()

    def _update_account_ui(self):
        aid = self.current_account_id
        if aid is None:
            self.login_status_var.set("未登录")
            self.login_status_label.config(foreground="black")
            self.login_btn.config(state=tk.DISABLED)
            return
        sf = self._get_account_storage(aid)
        if os.path.exists(sf):
            self.logged_in = True
            self.login_status_var.set("已登录")
            self.login_status_label.config(foreground="green")
            self.login_btn.config(state=tk.DISABLED)
            self.logout_btn.config(state=tk.NORMAL)
            self.crawl_btn.config(state=tk.NORMAL)
            self.gen_btn.config(state=tk.NORMAL)
            self.check_status_btn.config(state=tk.NORMAL)
        else:
            self.logged_in = False
            self.login_status_var.set("未登录")
            self.login_status_label.config(foreground="black")
            self.login_btn.config(state=tk.NORMAL)
            self.logout_btn.config(state=tk.DISABLED)
            self.crawl_btn.config(state=tk.DISABLED)
            self.gen_btn.config(state=tk.DISABLED)
            self.submit_selected_btn.config(state=tk.DISABLED)
            self.submit_all_btn.config(state=tk.DISABLED)
            self.check_status_btn.config(state=tk.DISABLED)

    def _login_current_account(self):
        if self.current_account_id is None:
            messagebox.showwarning("提示", "请先选择一个账号")
            return
        account = self._get_account_by_id(self.current_account_id)
        if not account:
            return
        self._do_login(account)

    def _do_login(self, account):
        def task():
            self.task_queue.put(("log", f"[*] 正在登录 {account['nickname']}..."))
            try:
                from crawler import Crawler
                sf = self._get_account_storage(account["id"])
                c = Crawler(callback=lambda m: self.task_queue.put(("log", m)),
                            storage_file=sf)
                ok = c.login_with_credentials(account["username"], account["password"])
                if ok:
                    self.task_queue.put(("login_done", None))
                    self.task_queue.put(("log", f"[+] {account['nickname']} 登录成功"))
                else:
                    self.task_queue.put(("log", f"[-] {account['nickname']} 登录失败"))
            except Exception as e:
                self.task_queue.put(("log", f"[-] 出错: {e}"))

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def _show_account_manager(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("账号管理")
        dialog.geometry("520x400")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.minsize(420, 300)

        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # list
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self._am_listbox = tk.Listbox(list_frame, font=("Consolas", 10))
        self._am_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._am_listbox.yview)
        self._am_listbox.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh_list():
            self._am_listbox.delete(0, tk.END)
            for a in self.accounts:
                sf = self._get_account_storage(a["id"])
                status = "✓" if os.path.exists(sf) else " "
                self._am_listbox.insert(tk.END, f" [{status}] #{a['id']} {a['nickname']} ({a['username']})")

        refresh_list()

        # buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(8, 0))

        def add_account():
            d = tk.Toplevel(dialog)
            d.title("添加账号")
            d.geometry("360x200")
            d.transient(dialog)
            d.grab_set()
            f = ttk.Frame(d, padding=12)
            f.pack(fill=tk.BOTH, expand=True)
            ttk.Label(f, text="昵称:").grid(row=0, column=0, sticky=tk.W, pady=4)
            nick_var = tk.StringVar(value=f"账号{len(self.accounts)+1}")
            ttk.Entry(f, textvariable=nick_var, width=30).grid(row=0, column=1, pady=4)
            ttk.Label(f, text="账号:").grid(row=1, column=0, sticky=tk.W, pady=4)
            user_var = tk.StringVar()
            ttk.Entry(f, textvariable=user_var, width=30).grid(row=1, column=1, pady=4)
            ttk.Label(f, text="密码:").grid(row=2, column=0, sticky=tk.W, pady=4)
            pass_var = tk.StringVar()
            ttk.Entry(f, textvariable=pass_var, width=30, show="*").grid(row=2, column=1, pady=4)

            def save():
                nick = nick_var.get().strip()
                u = user_var.get().strip()
                p = pass_var.get()
                if not u or not p:
                    messagebox.showwarning("提示", "请输入账号和密码", parent=d)
                    return
                new_id = 1
                if self.accounts:
                    new_id = max(a["id"] for a in self.accounts) + 1
                self.accounts.append({"id": new_id, "nickname": nick or f"账号{new_id}",
                                       "username": u, "password": p})
                self._save_accounts()
                d.destroy()
                refresh_list()
                self._refresh_account_combo()

            bf = ttk.Frame(f)
            bf.grid(row=3, column=0, columnspan=2, pady=(12, 0))
            ttk.Button(bf, text="确定", command=save).pack(side=tk.LEFT, padx=4)
            ttk.Button(bf, text="取消", command=d.destroy).pack(side=tk.LEFT, padx=4)
            d.wait_window()

        def edit_account():
            sel = self._am_listbox.curselection()
            if not sel:
                messagebox.showwarning("提示", "请先选择一个账号", parent=dialog)
                return
            idx = sel[0]
            acc = self.accounts[idx]
            d = tk.Toplevel(dialog)
            d.title("编辑账号")
            d.geometry("360x200")
            d.transient(dialog)
            d.grab_set()
            f = ttk.Frame(d, padding=12)
            f.pack(fill=tk.BOTH, expand=True)
            ttk.Label(f, text="昵称:").grid(row=0, column=0, sticky=tk.W, pady=4)
            nick_var = tk.StringVar(value=acc["nickname"])
            ttk.Entry(f, textvariable=nick_var, width=30).grid(row=0, column=1, pady=4)
            ttk.Label(f, text="账号:").grid(row=1, column=0, sticky=tk.W, pady=4)
            user_var = tk.StringVar(value=acc["username"])
            ttk.Entry(f, textvariable=user_var, width=30).grid(row=1, column=1, pady=4)
            ttk.Label(f, text="密码:").grid(row=2, column=0, sticky=tk.W, pady=4)
            pass_var = tk.StringVar(value=acc["password"])
            ttk.Entry(f, textvariable=pass_var, width=30, show="*").grid(row=2, column=1, pady=4)

            def save():
                acc["nickname"] = nick_var.get().strip() or acc["nickname"]
                acc["username"] = user_var.get().strip() or acc["username"]
                acc["password"] = pass_var.get()
                self._save_accounts()
                d.destroy()
                refresh_list()
                self._refresh_account_combo()

            bf = ttk.Frame(f)
            bf.grid(row=3, column=0, columnspan=2, pady=(12, 0))
            ttk.Button(bf, text="确定", command=save).pack(side=tk.LEFT, padx=4)
            ttk.Button(bf, text="取消", command=d.destroy).pack(side=tk.LEFT, padx=4)
            d.wait_window()

        def delete_account():
            sel = self._am_listbox.curselection()
            if not sel:
                messagebox.showwarning("提示", "请先选择一个账号", parent=dialog)
                return
            idx = sel[0]
            acc = self.accounts[idx]
            if not messagebox.askyesno("确认", f"确定删除账号 {acc['nickname']}？", parent=dialog):
                return
            sf = self._get_account_storage(acc["id"])
            if os.path.exists(sf):
                os.remove(sf)
            self.accounts.pop(idx)
            self._save_accounts()
            if self.current_account_id == acc["id"]:
                self.current_account_id = None
            refresh_list()
            self._refresh_account_combo()

        def login_account():
            sel = self._am_listbox.curselection()
            if not sel:
                messagebox.showwarning("提示", "请先选择一个账号", parent=dialog)
                return
            idx = sel[0]
            acc = self.accounts[idx]
            self.current_account_id = acc["id"]
            dialog.destroy()
            self._refresh_account_combo()
            self._login_current_account()

        ttk.Button(btn_frame, text="添加", command=add_account).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="编辑", command=edit_account).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="删除", command=delete_account).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="登录此账号", command=login_account).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="关闭", command=dialog.destroy).pack(side=tk.RIGHT, padx=3)

        dialog.wait_window()

    # ─── 模式切换 ─────────────────────────────────────────────

    def _on_mode_change(self):
        new_mode = self.mode_var.get()
        if new_mode == self.mode:
            return
        self.mode = new_mode
        if new_mode == "exam":
            if not self.exam_loaded:
                self._clear_tree()
                self.list_frame.config(text=" 考试列表 ")
                self._log("[*] 正在加载考试列表...")
                self._load_exam_list()
                return
        self._rebuild_tree()

    def _load_exam_list(self):
        if self.current_account_id is None:
            self.task_queue.put(("log", "[-] 请先选择一个账号"))
            self.mode_var.set("assign")
            self.mode = "assign"
            self._rebuild_tree()
            return
        sf = self._get_account_storage(self.current_account_id)
        if not os.path.exists(sf):
            self.task_queue.put(("log", "[-] 请先登录该账号再加载考试列表"))
            self.mode_var.set("assign")
            self.mode = "assign"
            self._rebuild_tree()
            return

        def task():
            try:
                from crawler import Crawler as C
                c = C(callback=lambda m: self.task_queue.put(("log", m)),
                      storage_file=sf)
                c._start_browser(use_storage=True)
                # Establish session first, then navigate to section 4
                c.page.goto(SECTION4_URL, wait_until="domcontentloaded", timeout=30000)
                kw = ["oauth", "login", "authorize"]
                if any(k in c.page.url.lower() for k in kw):
                    self.task_queue.put(("log", "[-] 登录态已过期，请重新登录"))
                    c.close()
                    self.task_queue.put(("exam_list_error", "登录态过期"))
                    return
                raw = c.get_section_activities(SECTION4_URL)
                c.close()
                items = [(aid, title, tp) for aid, title, tp, _ in raw]
                url_map = {aid: url for aid, _, _, url in raw}
                self.task_queue.put(("exam_list_loaded", (items, url_map)))
            except Exception as e:
                self.task_queue.put(("exam_list_error", str(e)))

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def _clear_tree(self):
        for child in self.tree.get_children():
            self.tree.delete(child)

    def _rebuild_tree(self):
        self._clear_tree()
        if self.mode == "assign":
            items = ASSIGNMENTS
            data = self.assign_data
            title_text = " 作业列表 "
            self.submit_selected_btn.config(text="提交选中")
            self.submit_all_btn.config(text="提交全部（代码题）")
        else:
            items = self.exam_assignments
            data = self.exam_assign_data
            title_text = " 考试列表 "
            self.submit_selected_btn.config(text="提交选中")
            self.submit_all_btn.config(text="提交全部考试")
        self.list_frame.config(text=title_text)
        for assign_id, title, atype in items:
            short_type = TYPE_MAP.get(atype, atype)
            info = data.get(assign_id, {})
            st = info.get("status", "pending")
            label = STATUS_MAP.get(st, st)
            score_text = info.get("score", "")
            self.tree.insert("", tk.END, values=("", assign_id, title, short_type, label, score_text),
                             tags=(st,))

    def _get_current_assignments(self):
        if self.mode == "assign":
            return ASSIGNMENTS
        return self.exam_assignments

    def _login_all_accounts(self):
        to_login = [a for a in self.accounts
                    if not os.path.exists(self._get_account_storage(a["id"]))]
        if not to_login:
            self.task_queue.put(("log", "[*] 所有账号均已登录，无需操作"))
            return
        self.login_all_btn.config(state=tk.DISABLED)
        self.task_queue.put(("log", f"[*] 开始批量登录 {len(to_login)} 个未登录账号..."))

        def task():
            success = 0
            fail = 0
            for i, acc in enumerate(to_login):
                self.task_queue.put(("log", f"  [{i+1}/{len(to_login)}] 登录 {acc['nickname']}..."))
                try:
                    from crawler import Crawler
                    sf = self._get_account_storage(acc["id"])
                    c = Crawler(callback=lambda m: self.task_queue.put(("log", m)),
                                storage_file=sf)
                    ok = c.login_with_credentials(acc["username"], acc["password"])
                    if ok:
                        success += 1
                    else:
                        fail += 1
                        self.task_queue.put(("log", f"  [-XXX-] {acc['nickname']} 登录失败"))
                except Exception as e:
                    fail += 1
                    self.task_queue.put(("log", f"  [-ERR-] {acc['nickname']}: {e}"))
            self.task_queue.put(("log", f"[+] 批量登录完成: 成功 {success}, 失败 {fail}"))
            self.task_queue.put(("refresh_ui", None))

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def _auto_select_account(self):
        for a in self.accounts:
            sf = self._get_account_storage(a["id"])
            if os.path.exists(sf):
                self.current_account_id = a["id"]
                self._refresh_account_combo()
                self._update_account_ui()
                return
        if self.accounts:
            self.current_account_id = self.accounts[0]["id"]
            self._refresh_account_combo()
            self._update_account_ui()

    def _do_logout(self):
        if self.current_account_id is None:
            return
        sf = self._get_account_storage(self.current_account_id)
        if os.path.exists(sf):
            os.remove(sf)
        self.logged_in = False
        self.login_status_var.set("未登录")
        self.login_status_label.config(foreground="black")
        self.login_btn.config(state=tk.NORMAL)
        self.logout_btn.config(state=tk.DISABLED)
        self.crawl_btn.config(state=tk.DISABLED)
        self.gen_btn.config(state=tk.DISABLED)
        self.submit_selected_btn.config(state=tk.DISABLED)
        self.submit_all_btn.config(state=tk.DISABLED)
        self.check_status_btn.config(state=tk.DISABLED)
        self.task_queue.put(("log", "[*] 已退出登录"))

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
            try:
                from crawler import Crawler as C
                sf = self._get_account_storage(self.current_account_id)
                c = C(callback=lambda m: self.task_queue.put(("log", m)),
                      storage_file=sf)
                if not os.path.exists(sf):
                    self.task_queue.put(("log", "[-] 未找到登录态，请先登录该账号"))
                    self.task_queue.put(("crawl_done", None))
                    return
                c._start_browser(use_storage=True)
                c.page.goto(COURSE_URL, wait_until="domcontentloaded", timeout=30000)
                kw = ["oauth", "login", "authorize"]
                if any(k in c.page.url.lower() for k in kw):
                    self.task_queue.put(("log", "[-] 登录态已过期，请重新登录"))
                    c.close()
                    self.task_queue.put(("crawl_done", None))
                    return
                c.logged_in = True

                self.task_queue.put(("log", f"[*] 正在抓取 {len(sel)} 个作业..."))
                cur = self._get_current_assignments()
                if self.mode == "exam":
                    data = c.crawl_exam_selected(sel, self.exam_url_map)
                else:
                    data = c.crawl_selected(sel)
                self.task_queue.put(("log", f"[+] 已抓取 {len(data)} 个作业"))
                c.close()
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
                if self.mode == "exam":
                    total = len(sel)
                    def prog(cur, tot):
                        self.task_queue.put(("progress", (cur, tot)))
                    count = generate_exam_answers(sel, callback=prog)
                    self.task_queue.put(("progress", (count, count)))
                    self.task_queue.put(("log", f"[+] 已生成 {count} 个考试答案文件 (answer1/)"))
                else:
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

    def _do_check_completion(self):
        self.check_status_btn.config(state=tk.DISABLED)

        def task():
            try:
                from status_checker import StatusChecker
                sf = self._get_account_storage(self.current_account_id)
                if not os.path.exists(sf):
                    self.task_queue.put(("log", "[-] 未找到登录态，请先登录该账号"))
                    self.task_queue.put(("check_status_done", None))
                    return

                sc = StatusChecker(
                    storage_file=sf,
                    headless=True,
                    callback=lambda m: self.task_queue.put(("log", m))
                )
                sc.start_browser(use_storage=True)

                if not sc.check_login():
                    self.task_queue.put(("log", "[-] 登录态已过期，请重新登录"))
                    sc.close()
                    self.task_queue.put(("check_status_done", None))
                    return

                self.task_queue.put(("log", "[*] 正在检查所有作业的完成状态..."))
                cur = self._get_current_assignments()
                sel = [aid for aid, _, _ in cur]
                section_url = SECTION4_URL if self.mode == "exam" else COURSE_URL
                url_map = self.exam_url_map if self.mode == "exam" else None

                results = sc.check_all_activities(
                    section_url=section_url,
                    activity_ids=sel,
                    url_map=url_map,
                    strategy=StatusChecker.STRATEGY_BALANCED
                )
                sc.close()

                for aid, info in results.items():
                    completed = info.get("completed", False)
                    score = info.get("score", "")
                    self.task_queue.put(("check_completion", (aid, completed, score)))
                passed = sum(1 for v in results.values() if v.get("completed"))
                self.task_queue.put(("log", f"[+] 检查完成: {passed}/{len(sel)} 已完成"))
            except Exception as e:
                self.task_queue.put(("log", f"[-] 检查状态出错: {e}"))
            finally:
                self.task_queue.put(("check_status_done", None))

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def _do_submit_all(self):
        cur = self._get_current_assignments()
        if self.mode == "exam":
            sel = [aid for aid, _, _ in cur]
            self._run_exam_submit(sel)
        else:
            code_assigns = [(aid, title) for aid, title, atype in cur if atype == "code_assign"]
            self._run_submission(code_assigns)

    def _do_submit_selected(self):
        sel = self._get_selected_ids()
        if not sel:
            messagebox.showinfo("提示", "未选择任何作业，请点击左侧选择框进行选择")
            return
        if self.mode == "exam":
            self._run_exam_submit(sel)
        else:
            cur = self._get_current_assignments()
            filtered = [(aid, title) for aid, title, atype in cur if aid in sel and atype == "code_assign"]
            if not filtered:
                messagebox.showinfo("提示", "所选作业中没有代码题")
                return
            self._run_submission(filtered)

    def _run_submission(self, assign_list):
        self.submit_selected_btn.config(state=tk.DISABLED)
        self.submit_all_btn.config(state=tk.DISABLED)

        def task():
            try:
                sf = self._get_account_storage(self.current_account_id)
                sub = Submitter(callback=lambda m: self.task_queue.put(("log", m)),
                                storage_file=sf)
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

    def _run_exam_submit(self, sel):
        """Submit selected exams: fill answers then click end exam button."""
        self.submit_selected_btn.config(state=tk.DISABLED)
        self.submit_all_btn.config(state=tk.DISABLED)

        def task():
            try:
                sf = self._get_account_storage(self.current_account_id)
                timer_sec = self.timer_sec_var.get()
                sub = ExamSubmitter(callback=lambda m: self.task_queue.put(("log", m)),
                                    storage_file=sf, timer_seconds=timer_sec)
                ok = sub.start()
                if not ok:
                    self.task_queue.put(("log", "[-] 提交考试阶段登录失败"))
                    self.task_queue.put(("submit_done", None))
                    return

                total = len(sel)
                for i, exam_id in enumerate(sel):
                    self.task_queue.put(("progress", (i, total)))
                    url = self.exam_url_map.get(exam_id, "")
                    if not url:
                        self.task_queue.put(("log", f"  [{i+1}/{total}] id={exam_id} -> 无URL，跳过"))
                        continue
                    self.task_queue.put(("log", f"[{i+1}/{total}] 考试 id={exam_id}: 填入答案..."))
                    sub.fill_exam(exam_id, url)
                    self.task_queue.put(("log", f"  [*] 点击结束考试按钮..."))
                    sub.submit_exam(exam_id)

                self.task_queue.put(("progress", (total, total)))
                self.task_queue.put(("log", "[+] 所有考试提交完成!"))
                sub.close()
            except Exception as e:
                self.task_queue.put(("log", f"[-] 提交考试出错: {e}"))
            self.task_queue.put(("submit_done", None))

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = App()
    app.run()
