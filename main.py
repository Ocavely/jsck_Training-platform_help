import os, sys

if __name__ == "__main__":
    try:
        from app import App
        app = App()
        app.run()
    except ImportError as e:
        print(f"[-] 桌面界面不可用: {e}")
        sys.exit(1)
