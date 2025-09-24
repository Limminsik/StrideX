from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import json, os, glob, shutil
from typing import List

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")

app = FastAPI()

# CORS 미들웨어 추가 (외부 접속 지원)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용 (프로덕션에서는 특정 도메인으로 제한)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=os.path.join(APP_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(APP_DIR, "templates"))

# ====== 인덱스 구성: 파일 → 환자ID 매핑 ======
PATIENT_INDEX = {}   # { "SUBJ_001": {"files": [...], "sensors": {...}}, ... }

def _safe_load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] JSON load fail: {path} -> {e}")
        return None

def build_index():
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
        for k in sensors.keys():              # e.g., "smart_insole", "gait_pad", "imu_sensor"
            PATIENT_INDEX[pid]["sensors"][k] = os.path.basename(fp)
    
    print(f"[INDEX] Built for {len(PATIENT_INDEX)} patients:")
    for pid, info in PATIENT_INDEX.items():
        print(f"  {pid}: {info['sensors']} ({len(info['files'])} files)")

build_index()
print("[INDEX] patients:", list(PATIENT_INDEX.keys()))

# ====== 라우팅 ======
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/subjects")
def list_subjects():
    # 드롭다운에 쓸 요약 정보
    out = []
    for pid, info in PATIENT_INDEX.items():
        meta = info.get("meta", {})
        out.append({
            "id": pid,
            "age": meta.get("age"),
            "gender": meta.get("gender"),
            "condition": meta.get("condition"),
            "sensors": list(info["sensors"].keys())
        })
    return {"subjects": out}

@app.get("/api/patient/{patient_id}")
def get_patient(patient_id: str):
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

# 파일 업로드 API
@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """JSON 파일들을 업로드하고 data 폴더에 저장"""
    uploaded_files = []
    errors = []
    
    for file in files:
        if not file.filename.endswith(('.json', '.jsonl', '.ndjson')):
            errors.append(f"{file.filename}: JSON 파일만 업로드 가능합니다.")
            continue
            
        try:
            # 파일 저장
            file_path = os.path.join(DATA_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # JSON 유효성 검사
            data = _safe_load(file_path)
            if not data:
                errors.append(f"{file.filename}: 유효하지 않은 JSON 파일입니다.")
                os.remove(file_path)
                continue
                
            uploaded_files.append(file.filename)
            
        except Exception as e:
            errors.append(f"{file.filename}: 업로드 실패 - {str(e)}")
    
    # 인덱스 재구성
    build_index()
    
    return {
        "success": True,
        "uploaded_files": uploaded_files,
        "errors": errors,
        "total_subjects": len(PATIENT_INDEX)
    }

# 데이터 폴더 초기화 API
@app.post("/api/clear-data")
def clear_data():
    """data 폴더의 모든 파일 삭제"""
    try:
        for filename in os.listdir(DATA_DIR):
            file_path = os.path.join(DATA_DIR, filename)
            if os.path.isfile(file_path) and filename.endswith(('.json', '.jsonl', '.ndjson')):
                os.remove(file_path)
        
        # 인덱스 초기화
        PATIENT_INDEX.clear()
        
        return {"success": True, "message": "모든 데이터가 삭제되었습니다."}
    except Exception as e:
        return {"success": False, "message": f"데이터 삭제 실패: {str(e)}"}
