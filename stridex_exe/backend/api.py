from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os, sys, json, glob
from typing import List, Dict, Any
import uvicorn

def resource_path(rel):
    """PyInstaller 대응 경로 처리"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
    return os.path.join(base, rel)

# FastAPI 앱 생성
app = FastAPI(title="StrideX Dashboard")

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 마운트
STATIC_DIR = resource_path("static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# SPA 진입점
@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# 데이터 디렉토리 설정
DATA_DIR = resource_path("data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 환자 인덱스 (메모리 캐시)
PATIENT_INDEX: Dict[str, Dict[str, Any]] = {}

def _safe_load(path: str) -> Dict[str, Any]:
    """JSON 파일 안전 로드"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"파일 로드 실패 {path}: {e}")
        return {}

def build_index():
    """환자 인덱스 구축"""
    PATIENT_INDEX.clear()
    for fp in glob.glob(os.path.join(DATA_DIR, "*.json")):
        data = _safe_load(fp)
        if not data or "meta" not in data or "patient" not in data["meta"]:
            continue
        pid = data["meta"]["patient"].get("id")
        if not pid:
            continue
        if pid not in PATIENT_INDEX:
            PATIENT_INDEX[pid] = {"files": [], "sensors": {}, "meta": data["meta"]["patient"]}
        PATIENT_INDEX[pid]["files"].append(os.path.basename(fp))
        # 센서 타입 추출
        sensors = data.get("data", {})
        for k in sensors.keys():
            PATIENT_INDEX[pid]["sensors"][k] = os.path.basename(fp)
    
    print(f"[INDEX] Built for {len(PATIENT_INDEX)} patients:")
    for pid, info in PATIENT_INDEX.items():
        print(f"  {pid}: {info['sensors']} ({len(info['files'])} files)")

# 앱 시작 시 인덱스 구축
build_index()

@app.get("/api/subjects")
def list_subjects():
    """Subject 목록 반환"""
    subjects = []
    for pid, info in PATIENT_INDEX.items():
        subjects.append({
            "id": pid,
            "sensors": list(info["sensors"].keys()),
            "meta": info["meta"]
        })
    return {"subjects": subjects}

@app.get("/api/patient/{patient_id}")
def get_patient(patient_id: str):
    """특정 환자 데이터 반환"""
    if patient_id not in PATIENT_INDEX:
        raise HTTPException(404, detail="Patient not found in index.")
    
    print(f"[API] Loading patient {patient_id}...")
    
    # 같은 환자의 관련 파일을 모두 읽어서 병합
    merged = {"meta": {"patient": PATIENT_INDEX[patient_id].get("meta")}, "data": {}, "labels": {}}
    
    for fname in PATIENT_INDEX[patient_id]["files"]:
        path = os.path.join(DATA_DIR, fname)
        data = _safe_load(path)
        if not data:
            print(f"[WARN] Failed to load {fname}")
            continue
            
        print(f"[API] Loading {fname}...")
        
        # data 병합
        if "data" in data:
            for sensor_key, payload in data["data"].items():
                merged["data"][sensor_key] = payload
                print(f"[API] Added {sensor_key} data from {fname}")
        
        # labels 병합(있으면)
        if "labels" in data:
            merged["labels"].update(data["labels"])
            print(f"[API] Added labels from {fname}")
    
    print(f"[API] Final merged data keys: {list(merged['data'].keys())}")
    return merged

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """파일 업로드 처리"""
    uploaded_files = []
    total_subjects = 0
    
    for file in files:
        if not file.filename.endswith(('.json', '.jsonl', '.ndjson')):
            continue
            
        file_path = os.path.join(DATA_DIR, file.filename)
        content = await file.read()
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        uploaded_files.append(file.filename)
    
    # 인덱스 재구축
    build_index()
    total_subjects = len(PATIENT_INDEX)
    
    return {
        "success": True,
        "uploaded_files": uploaded_files,
        "total_subjects": total_subjects
    }

@app.post("/api/clear-data")
def clear_data():
    """모든 데이터 초기화"""
    try:
        # 데이터 파일 삭제
        for file_path in glob.glob(os.path.join(DATA_DIR, "*.json")):
            os.remove(file_path)
        
        # 인덱스 초기화
        PATIENT_INDEX.clear()
        
        return {"success": True, "message": "All data cleared successfully"}
    except Exception as e:
        return {"success": False, "message": f"Failed to clear data: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
