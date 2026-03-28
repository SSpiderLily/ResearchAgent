"""One-command launcher for Research Copilot (FastAPI + Streamlit)."""

import subprocess
import sys
import signal
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

BACKEND_CMD = [
    sys.executable, "-m", "uvicorn",
    "backend.main:app",
    "--host", "127.0.0.1",
    "--port", "8000",
    "--reload",
]

FRONTEND_CMD = [
    sys.executable, "-m", "streamlit",
    "run", "frontend/app.py",
    "--server.port", "8501",
]


def main():
    procs: list[subprocess.Popen] = []

    def _cleanup(sig=None, frame=None):
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, _cleanup)
    signal.signal(signal.SIGTERM, _cleanup)

    print("🚀 Starting Research Copilot …")
    print("   Backend  → http://127.0.0.1:8000/docs")
    print("   Frontend → http://127.0.0.1:8501")
    print("   Press Ctrl+C to stop.\n")

     # 启动进程
    backend = subprocess.Popen(BACKEND_CMD, cwd=PROJECT_ROOT)
    frontend = subprocess.Popen(FRONTEND_CMD, cwd=PROJECT_ROOT)
    
    procs = [backend, frontend]

    try:
        # 循环检查每个进程的状态
        while True:
            # poll() 方法检查进程是否已结束，如果未结束则返回 None
            for p in procs:
                if p.poll() is not None: # 如果进程已结束，poll() 会返回退出码
                    # 如果任何一个进程意外退出，则清理并退出
                    print(f"\n⚠️  子进程 {p.pid} 已退出 (code: {p.returncode})")
                    _cleanup()
            
            # 为了不占用过多 CPU，短暂休眠
            import time
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        # 这里会捕获到 Ctrl+C 的信号，但主要逻辑已在信号处理器中
        pass
    
    # 清理资源
    _cleanup()


if __name__ == "__main__":
    main()
