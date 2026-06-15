import os, sys, time, json, threading, queue
from flask import Flask, render_template, jsonify, request, Response, stream_with_context

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ASSIGNMENTS, ANSWER_DIR, CACHE_DIR, BASE_DIR
from answer_gen import generate_all as gen_answers, generate_selected as gen_selected

app = Flask(__name__, template_folder="templates", static_folder="static")

# global state (single-user)
state = {
    "logged_in": False,
    "status": {},
    "log_queue": queue.Queue(),
    "progress": (0, 0),
    "busy": False,
}


# ---------- API Routes ----------

@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/status")
def api_status():
    return jsonify({
        "logged_in": state["logged_in"],
        "busy": state["busy"],
        "progress": state["progress"],
        "assignments": [
            {
                "id": aid,
                "title": title,
                "type": atype,
                "status": state["status"].get(aid, {}).get("status", "pending"),
                "msg": state["status"].get(aid, {}).get("msg", ""),
            }
            for aid, title, atype in ASSIGNMENTS
        ],
    })


@app.route("/api/log")
def api_log():
    def generate():
        while True:
            try:
                msg = state["log_queue"].get(timeout=30)
                yield f"data: {json.dumps({'msg': msg})}\n\n"
            except queue.Empty:
                yield f"data: {json.dumps({'ping': True})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route("/api/login", methods=["POST"])
def api_login():
    if state["busy"]:
        return jsonify({"ok": False, "error": "忙碌中"})
    state["busy"] = True

    def task():
        try:
            from crawler import Crawler
            log("[*] 正在启动浏览器登录...")
            c = Crawler(callback=log)
            ok = c.login_only()
            state["logged_in"] = ok
            state["crawler"] = c
            if ok:
                log("[+] 登录成功")
            else:
                log("[-] 登录失败")
        except Exception as e:
            log(f"[-] 出错: {e}")
        finally:
            state["busy"] = False

    threading.Thread(target=task, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/crawl", methods=["POST"])
def api_crawl():
    if state["busy"]:
        return jsonify({"ok": False, "error": "忙碌中"})
    data = request.get_json() or {}
    sel = data.get("selected")
    if not sel:
        return jsonify({"ok": False, "error": "未选择作业"})
    state["busy"] = True

    def task():
        try:
            from crawler import Crawler
            log(f"[*] 正在抓取 {len(sel)} 个作业...")
            c = Crawler(callback=log)
            data = c.crawl_selected(sel)
            state["logged_in"] = True
            state["crawler"] = c
            log(f"[+] 已抓取 {len(data)} 个作业")
        except Exception as e:
            log(f"[-] 抓取出错: {e}")
        finally:
            state["busy"] = False

    threading.Thread(target=task, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/generate", methods=["POST"])
def api_generate():
    if state["busy"]:
        return jsonify({"ok": False, "error": "忙碌中"})
    data = request.get_json() or {}
    sel = data.get("selected")
    if not sel:
        return jsonify({"ok": False, "error": "未选择作业"})
    state["busy"] = True

    def task():
        try:
            log("[*] 正在生成答案文件...")

            def prog(cur, tot):
                state["progress"] = (cur, tot)

            count = gen_selected(sel, callback=prog)
            state["progress"] = (count, count)
            log(f"[+] 已生成 {count} 个答案文件")
            for aid in sel:
                _update_status(aid, "generated")
        except Exception as e:
            log(f"[-] 生成答案出错: {e}")
        finally:
            state["busy"] = False

    threading.Thread(target=task, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/submit", methods=["POST"])
def api_submit():
    if state["busy"]:
        return jsonify({"ok": False, "error": "忙碌中"})
    if not state.get("logged_in"):
        return jsonify({"ok": False, "error": "未登录"})

    data = request.get_json() or {}
    sel = data.get("selected")
    if not sel:
        return jsonify({"ok": False, "error": "未选择作业"})
    state["busy"] = True

    def task():
        try:
            log("[*] 正在启动提交...")
            from submitter import Submitter
            sub = Submitter(callback=log)
            ok = sub.start()
            if not ok:
                log("[-] 登录失败")
                state["busy"] = False
                return

            assign_list = [(aid, title) for aid, title, atype in ASSIGNMENTS if aid in sel and atype == "code_assign"]

            log(f"[*] 正在提交 {len(assign_list)} 个作业...")
            total = len(assign_list)

            def prog(cur, tot, aid, status, msg):
                state["progress"] = (cur, tot)
                _update_status(aid, status, msg)

            results = sub.submit_assignments(assign_list, progress_callback=prog)
            sub.close()

            passed = sum(1 for r in results.values() if r.get("status") in ("passed", "submitted"))
            failed = sum(1 for r in results.values() if r.get("status") == "failed")
            skipped = sum(1 for r in results.values() if r.get("status") == "skipped")
            log(f"[+] 完成! 通过: {passed}, 失败: {failed}, 跳过: {skipped}")
            state["progress"] = (total, total)
        except Exception as e:
            log(f"[-] 提交出错: {e}")
        finally:
            state["busy"] = False

    threading.Thread(target=task, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    c = state.get("crawler")
    if c:
        try:
            c.close()
        except:
            pass
    state["logged_in"] = False
    state["crawler"] = None
    state["submitter"] = None
    sf = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".login_storage.json")
    if os.path.exists(sf):
        os.remove(sf)
    log("[*] 已退出登录，已清除本地登录态")
    return jsonify({"ok": True})


# ---------- Helpers ----------

def log(msg):
    ts = time.strftime("%H:%M:%S")
    formatted = f"[{ts}] {msg}"
    state["log_queue"].put(formatted)


def _update_status(aid, status, msg=""):
    if aid not in state["status"]:
        state["status"][aid] = {}
    state["status"][aid]["status"] = status
    if msg:
        state["status"][aid]["msg"] = msg


if __name__ == "__main__":
    os.makedirs("static", exist_ok=True)
    app.run(host="127.0.0.1", port=5050, debug=False, threaded=True)
