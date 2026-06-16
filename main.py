
import os, sys

if __name__ == "__main__":
    print("[*] 正在启动桌面界面...")
    try:
        from app import App
        app = App()
        app.run()
    except ImportError as e:
        print(f"[-] 桌面界面不可用: {e}")
        sys.exit(1)
