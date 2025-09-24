import os, sys, json, pathlib, gzip
import webview
from typing import Dict, Any, List

# UTF-8 인코딩 강제 설정
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass  # --noconsole일 땐 reconfigure 안될 수 있음

APP_TITLE = "Gait Physiological Signal Dashboard - StrideX"

def resource_path(rel_path: str) -> str:
    """PyInstaller 환경에서 리소스 경로 처리"""
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel_path)

class StrideXBridge:
    """JavaScript에서 호출할 Python API Bridge"""
    
    def __init__(self):
        self._subjects = {}  # 메모리 캐시: {subj_id: {meta, labels, data}}
        self._data_dir = resource_path("web/data")
        
        # 앱 시작 시 기존 데이터 로드
        self._load_existing_data()
    
    def _load_existing_data(self):
        """기존 JSON 파일들을 자동 로드"""
        if not os.path.exists(self._data_dir):
            return
            
        json_files = []
        for ext in ["*.json", "*.jsonl", "*.ndjson", "*.json.gz"]:
            json_files.extend(pathlib.Path(self._data_dir).glob(ext))
        
        if json_files:
            self._subjects = self._load_and_group([str(f) for f in json_files])
            print(f"[BRIDGE] Loaded {len(self._subjects)} subjects from {len(json_files)} files")
    
    def _read_text(self, path: str) -> str:
        """파일 읽기 (gzip 지원, UTF-8 강제)"""
        if str(path).lower().endswith(".gz"):
            with gzip.open(path, "rt", encoding="utf-8") as f:
                return f.read()
        return pathlib.Path(path).read_text(encoding="utf-8")
    
    def _load_json_any(self, path: str) -> Dict[str, Any]:
        """JSON 파일 로드 (다양한 형식 지원)"""
        txt = self._read_text(path)
        try:
            obj = json.loads(txt)
            return obj if isinstance(obj, dict) else {"root": obj}
        except Exception:
            # JSONL 형식 시도
            rows = []
            for ln in txt.splitlines():
                s = ln.strip()
                if not s:
                    continue
                try:
                    rows.append(json.loads(s))
                except:
                    break
            return {"records": rows} if rows else {}
    
    def _load_and_group(self, paths: List[str]) -> Dict[str, Dict[str, Any]]:
        """JSON 파일들을 로드하고 Subject ID별로 그룹화"""
        grouped = {}
        
        for path in paths:
            try:
                doc = self._load_json_any(path)
                if not doc:
                    continue
                
                # Subject ID 추출
                subj_id = (
                    doc.get("meta", {}).get("patient", {}).get("id") or
                    doc.get("meta", {}).get("id") or
                    pathlib.Path(path).stem
                )
                
                if not subj_id:
                    continue
                
                # Subject 데이터 초기화
                if subj_id not in grouped:
                    grouped[subj_id] = {
                        "meta": {},
                        "labels": {},
                        "data": {},
                        "files": []
                    }
                
                bucket = grouped[subj_id]
                bucket["files"].append(pathlib.Path(path).name)
                
                # 데이터 병합
                if isinstance(doc.get("meta"), dict):
                    bucket["meta"].update(doc["meta"])
                if isinstance(doc.get("labels"), dict):
                    bucket["labels"].update(doc["labels"])
                if isinstance(doc.get("data"), dict):
                    bucket["data"].update(doc["data"])
                    
            except Exception as e:
                print(f"[WARN] Failed to load {path}: {e}")
                continue
        
        return grouped
    
    # === JavaScript에서 호출할 API 메서드들 ===
    
    def get_subjects(self) -> Dict[str, Any]:
        """Subject 목록 반환"""
        subjects = []
        for subj_id, data in self._subjects.items():
            # 센서 타입 추출
            sensors = []
            for sensor_key in data.get("data", {}).keys():
                if sensor_key in ["imu_sensor", "gait_pad", "smart_insole"]:
                    sensors.append(sensor_key)
            
            subjects.append({
                "id": subj_id,
                "sensors": sensors,
                "meta": data.get("meta", {}),
                "files": data.get("files", [])
            })
        
        return {"ok": True, "subjects": subjects}
    
    def get_subject(self, subj_id: str) -> Dict[str, Any]:
        """특정 Subject 데이터 반환"""
        if subj_id not in self._subjects:
            return {"ok": False, "error": "Subject not found"}
        
        data = self._subjects[subj_id]
        return {
            "ok": True,
            "meta": {"patient": data.get("meta", {})},
            "data": data.get("data", {}),
            "labels": data.get("labels", {})
        }
    
    def add_files(self) -> Dict[str, Any]:
        """파일 선택 다이얼로그로 JSON 파일 추가"""
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            root = tk.Tk()
            root.withdraw()  # 메인 윈도우 숨기기
            
            paths = filedialog.askopenfilenames(
                title="JSON 파일 선택",
                filetypes=[
                    ("JSON files", "*.json *.jsonl *.ndjson *.json.gz"),
                    ("All files", "*.*")
                ]
            )
            
            root.destroy()
            
            if not paths:
                return {"ok": True, "message": "No files selected", "subjects": self.get_subjects()}
            
            # 새 파일들 로드
            new_data = self._load_and_group(list(paths))
            self._subjects.update(new_data)
            
            return {
                "ok": True, 
                "message": f"Added {len(new_data)} subjects from {len(paths)} files",
                "subjects": self.get_subjects()
            }
            
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def clear_data(self) -> Dict[str, Any]:
        """모든 데이터 초기화"""
        self._subjects = {}
        return {"ok": True, "message": "All data cleared", "subjects": self.get_subjects()}
    
    def get_app_info(self) -> Dict[str, Any]:
        """앱 정보 반환"""
        return {
            "ok": True,
            "title": APP_TITLE,
            "version": "1.0.0",
            "subjects_count": len(self._subjects)
        }

def run():
    """메인 실행 함수"""
    # index.html 경로 확인
    index_path = resource_path("web/index.html")
    if not os.path.exists(index_path):
        raise SystemExit(f"index.html not found: {index_path}")
    
    print(f"[MAIN] Starting {APP_TITLE}")
    print(f"[MAIN] Loading from: {index_path}")
    
    # Bridge 인스턴스 생성
    api = StrideXBridge()
    
    # 웹뷰 창 생성 (pywebview 4.x: js_api는 create_window에)
    window = webview.create_window(
        title=APP_TITLE,
        url=pathlib.Path(index_path).as_uri(),  # file:// 경로로 로드
        width=1400,
        height=900,
        resizable=True,
        text_select=True,
        js_api=api           # ✅ pywebview 4.x: 여기로 이동!
    )
    
    # 웹뷰 시작 (서버 없이)
    webview.start(
        gui="edgechromium",  # Windows에서 최신 Edge Chromium 사용
        http_server=False,   # HTTP 서버 사용 안함
        debug=False
    )

if __name__ == "__main__":
    run()