import subprocess
import webbrowser
import time
import os
import sys

def main():
    """StrideX Dashboard 실행"""
    print("StrideX Dashboard Starting...")
    
    # 현재 디렉토리 설정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(current_dir)
    os.chdir(project_dir)
    
    # Python 경로 확인
    python_exe = sys.executable
    
    # FastAPI 서버 시작
    print("Starting FastAPI server...")
    server_process = subprocess.Popen([
        python_exe, "-m", "uvicorn", 
        "backend.api:app", 
        "--host", "127.0.0.1", 
        "--port", "8000"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # 서버 시작 대기
    print("Waiting for server to start...")
    time.sleep(5)
    
    # 서버 상태 확인
    try:
        import requests
        response = requests.get("http://127.0.0.1:8000/", timeout=5)
        if response.status_code == 200:
            print("Server is ready!")
        else:
            print("Server is not responding properly")
            return
    except Exception as e:
        print(f"Server check failed: {e}")
        return
    
    # 브라우저에서 열기 (한 번만)
    print("Opening browser...")
    webbrowser.open("http://127.0.0.1:8000")
    
    print("StrideX Dashboard is running!")
    print("Press Ctrl+C to stop...")
    
    try:
        # 서버가 계속 실행되도록 대기
        server_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    main()
