
import os, sys, argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="人工智能实训作业辅助系统")
    parser.add_argument("--web", action="store_true", help="启动 Web 界面")
    args = parser.parse_args()

    if args.web:
        print("[*] 启动Web服务: http://127.0.0.1:5050")
        from web_app import app
        os.makedirs(os.path.join(os.path.dirname(__file__), "static"), exist_ok=True)
        app.run(host="127.0.0.1", port=5050, debug=False, threaded=True)
    else:
        print("[*] 正在启动桌面界面...")
        try:
            from app import App
            app = App()
            app.run()
        except ImportError as e:
            print(f"[-] 桌面界面不可用: {e}")
            print("[*] 请尝试: python main.py --web")
            sys.exit(1)
