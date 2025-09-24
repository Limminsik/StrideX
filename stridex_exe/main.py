import os, sys, json, pathlib, gzip, re
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

# ===== 데이터 정규화 유틸리티 =====
def _to_float(x):
    """값을 float로 변환 (None/NaN 처리)"""
    try:
        if x is None: return None
        if isinstance(x, (int, float)): return float(x)
        if isinstance(x, str) and x.strip() != "": return float(x)
    except Exception:
        pass
    return None

def _coerce_lr(v):
    """dict|scalar -> {"L":f|None, "R":f|None}"""
    if isinstance(v, dict):
        return {"L": _to_float(v.get("L")), "R": _to_float(v.get("R"))}
    f = _to_float(v)
    return {"L": f, "R": None}

def _prettify_labels(raw):
    """Labels를 표시용으로 평탄화"""
    ann = raw.get("annotation") if isinstance(raw, dict) else None
    if isinstance(ann, dict):
        klass, side, region = ann.get("class"), ann.get("side"), ann.get("region")
        diag = raw.get("diagnosis_text")
    else:
        klass, side, region = raw.get("class"), raw.get("side"), raw.get("region")
        diag = raw.get("diagnosis_text")
    
    def _class(v):
        try: 
            iv = int(v)
            return f"{iv} ({'정상' if iv==0 else '무릎관절염'})"
        except: 
            return str(v) if v is not None else "None"
    
    return {
        "class (0:정상, 1:무릎관절염)": _class(klass) if klass is not None else "None",
        "side (병변 측)": side if side is not None else "None",
        "region (부위)": region if region is not None else "None",
        "diagnosis_text (진단 내용)": diag if diag is not None else "None",
    }

def _read_text(p):
    """파일 읽기 (gzip 지원)"""
    p = str(p)
    if p.lower().endswith(".gz"):
        with gzip.open(p, "rt", encoding="utf-8") as f: 
            return f.read()
    return pathlib.Path(p).read_text(encoding="utf-8")

def _load_json_any(p):
    """JSON 파일 로드 (다양한 형식 지원)"""
    txt = _read_text(p)
    try:
        obj = json.loads(txt)
        return obj if isinstance(obj, dict) else {"root": obj}
    except Exception:
        rows = []
        for ln in txt.splitlines():
            s = ln.strip()
            if not s: continue
            try: 
                rows.append(json.loads(s))
            except: 
                break
        return {"records": rows} if rows else {}

def _subj_id(doc, fallback_name):
    """Subject ID 추출"""
    meta = doc.get("meta") or {}
    pid = (meta.get("patient") or {}).get("id")
    return pid or meta.get("id") or fallback_name

def _normalize_subject(bucket):
    """bucket: merged raw dict -> normalized subject dict"""
    meta = bucket.get("meta", {})
    labels = _prettify_labels(bucket.get("labels", {}))

    # IMU 섹션 정규화
    imu_raw = ((bucket.get("data") or {}).get("imu_sensor") or {}).get("values") or {}
    imu = {
        "gait_cycle": _coerce_lr(imu_raw.get("gait_cycle")),
        "knee_flexion_max": _coerce_lr(imu_raw.get("knee_flexion_max")),
        "knee_extension_max": _coerce_lr(imu_raw.get("knee_extension_max")),
        "foot_clearance": _coerce_lr(imu_raw.get("foot_clearance")),
    }

    # Gait Pad 섹션 정규화
    pad_raw = ((bucket.get("data") or {}).get("gait_pad") or {}).get("values") or {}
    gait_pad = {
        "step_length": _coerce_lr(pad_raw.get("step_length")),
        "velocity": {"L": _to_float(pad_raw.get("velocity")), "R": None},  # velocity는 단일 값
        "stance_phase_rate": _coerce_lr(pad_raw.get("stance_phase_rate")),
        "swing_phase_rate": _coerce_lr(pad_raw.get("swing_phase_rate")),
        "double_support_time": _coerce_lr(pad_raw.get("double_support_time")),
    }

    # Smart Insole 섹션 정규화 (day_1..day_10)
    insole_days = []
    si_raw = ((bucket.get("data") or {}).get("smart_insole") or {}).get("values") or {}
    
    def _day_num(k): 
        m = re.match(r"day_(\d+)", str(k))
        return int(m.group(1)) if m else 0
    
    for dk in sorted(si_raw.keys(), key=_day_num):
        day = si_raw[dk] or {}
        insole_days.append({
            "key": dk,
            "gait_speed": {"L": _to_float(day.get("gait_speed")), "R": None},  # 단일 값
            "foot_pressure_rear": _coerce_lr(day.get("foot_pressure_rear")),
            "balance": _coerce_lr(day.get("balance")),
            "foot_pressure_mid": _coerce_lr(day.get("foot_pressure_mid")),
            "foot_angle": _coerce_lr(day.get("foot_angle")),
            "foot_pressure_fore": _coerce_lr(day.get("foot_pressure_fore")),
            "gait_distance": {"L": _to_float(day.get("gait_distance")), "R": None},  # 단일 값
            "stride_length": _coerce_lr(day.get("stride_lenght") or day.get("stride_length")),
        })

    return {
        "meta": meta, 
        "labels": labels, 
        "imu": imu, 
        "gait_pad": gait_pad, 
        "insole": insole_days
    }

class StrideXBridge:
    """JavaScript에서 호출할 Python API Bridge"""
    
    def __init__(self):
        self._subjects = {}  # 정규화된 데이터: {subj_id: normalized_subject}
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
            self._load_and_normalize([str(f) for f in json_files])
            print(f"[BRIDGE] Loaded {len(self._subjects)} subjects from {len(json_files)} files")
    
    def _load_and_normalize(self, paths: List[str]):
        """JSON 파일들을 로드하고 정규화"""
        merged = {}
        
        for path in paths:
            try:
                doc = _load_json_any(path)
                if not doc:
                    continue
                
                # Subject ID 추출
                subj_id = _subj_id(doc, pathlib.Path(path).stem)
                if not subj_id:
                    continue
                
                # Subject 데이터 초기화
                if subj_id not in merged:
                    merged[subj_id] = {
                        "meta": {},
                        "labels": {},
                        "data": {},
                        "files": []
                    }
                
                bucket = merged[subj_id]
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
        
        # 정규화된 데이터로 변환
        for subj_id, bucket in merged.items():
            self._subjects[subj_id] = _normalize_subject(bucket)
            print(f"[BRIDGE] Normalized subject {subj_id}: {list(self._subjects[subj_id].keys())}")
    
    # === JavaScript에서 호출할 API 메서드들 ===
    
    def get_subjects(self) -> Dict[str, Any]:
        """Subject 목록 반환 (전체 데이터 포함)"""
        subjects = []
        for subj_id, data in self._subjects.items():
            # 센서 타입 추출
            sensors = []
            if data.get("imu"): sensors.append("imu")
            if data.get("gait_pad"): sensors.append("gait_pad")
            if data.get("insole"): sensors.append("insole")
            
            subjects.append({
                "id": subj_id,
                "sensors": sensors,
                "meta": data.get("meta", {}),
                "labels": data.get("labels", {}),
                "imu": data.get("imu", {}),
                "gait_pad": data.get("gait_pad", {}),
                "insole": data.get("insole", []),
                "files": data.get("files", [])
            })
        
        return {
            "ok": True, 
            "subjects": subjects,
            "ids": list(self._subjects.keys())
        }
    
    def get_subject(self, subj_id: str) -> Dict[str, Any]:
        """특정 Subject 데이터 반환 (정규화된 형태)"""
        if subj_id not in self._subjects:
            print(f"[BRIDGE] Subject {subj_id} not found")
            return {"ok": False, "error": "Subject not found"}
        
        data = self._subjects[subj_id]
        print(f"[BRIDGE] Subject {subj_id} 데이터 반환:")
        print(f"  - Meta keys: {list(data.get('meta', {}).keys())}")
        print(f"  - Labels keys: {list(data.get('labels', {}).keys())}")
        print(f"  - IMU keys: {list(data.get('imu', {}).keys())}")
        print(f"  - Gait Pad keys: {list(data.get('gait_pad', {}).keys())}")
        print(f"  - Insole days: {len(data.get('insole', []))}")
        
        return {
            "ok": True,
            "meta": data.get("meta", {}),
            "labels": data.get("labels", {}),
            "imu": data.get("imu", {}),
            "gait_pad": data.get("gait_pad", {}),
            "insole": data.get("insole", [])
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
            
            # 새 파일들 로드 및 정규화
            self._load_and_normalize(list(paths))
            
            result = self.get_subjects()
            return {
                "ok": True, 
                "message": f"Added {len(paths)} files",
                "subjects": result["subjects"],
                "ids": result["ids"]
            }
            
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def clear_data(self) -> Dict[str, Any]:
        """모든 데이터 초기화"""
        self._subjects = {}
        print("[BRIDGE] All data cleared")
        return {"ok": True, "message": "All data cleared", "subjects": [], "ids": []}
    
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