import threading, time, socket, sys, os
import webview

def find_free_port():
    """사용 가능한 포트 찾기"""
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def start_server(port):
    """백엔드 서버 시작"""
    import uvicorn
    import sys
    import os
    
    # PyInstaller 환경에서 모듈 경로 추가
    if getattr(sys, 'frozen', False):
        # 실행파일로 실행된 경우
        base_path = sys._MEIPASS
        backend_path = os.path.join(base_path, 'backend')
        sys.path.insert(0, backend_path)
    
    # API 모듈 직접 임포트
    from api import app
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

def run():
    """메인 실행 함수"""
    port = find_free_port()
    print(f"[DESKTOP] Starting server on port {port}")
    
    # 서버 스레드 시작
    t = threading.Thread(target=start_server, args=(port,), daemon=True)
    t.start()

    # 서버 기동 대기
    import requests
    for i in range(50):
        try:
            requests.get(f"http://127.0.0.1:{port}/", timeout=0.2)
            print(f"[DESKTOP] Server ready after {i+1} attempts")
            break
        except Exception:
            time.sleep(0.1)
    else:
        print("[DESKTOP] Server startup timeout!")
        return

    # 웹뷰 창 열기
    webview.create_window(
        title="Gait Physiological Signal Dashboard — StrideX",
        url=f"http://127.0.0.1:{port}/",
        width=1400, 
        height=900,
        resizable=True, 
        confirm_close=True,
        text_select=True
    )
    webview.start()

if __name__ == "__main__":
    run()
