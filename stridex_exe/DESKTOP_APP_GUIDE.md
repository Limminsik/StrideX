# StrideX Desktop App - 완전한 데스크톱 앱 가이드

## 🎯 개요

**서버 없이 exe 하나만으로 실행되는 완전한 데스크톱 앱**입니다!

- ✅ **서버 불필요**: FastAPI/uvicorn 없이 pywebview로 직접 실행
- ✅ **단일 exe**: PyInstaller로 하나의 실행파일로 패키징
- ✅ **로컬 데이터**: web/data/ 폴더의 JSON 파일들을 자동 로드
- ✅ **파일 선택**: 데스크톱 파일 다이얼로그로 추가 JSON 파일 로드
- ✅ **완전 오프라인**: 인터넷 연결 없이도 모든 기능 동작

## 🏗️ 아키텍처

```
StrideX_Desktop.exe
├── pywebview (Edge Chromium WebView)
├── JavaScript ↔ Python Bridge API
├── web/ 폴더 (HTML/CSS/JS)
└── web/data/ 폴더 (JSON 파일들)
```

## 📁 프로젝트 구조

```
stridex_web/
├── main.py                    # 메인 데스크톱 앱
├── web/                       # 프론트엔드 파일들
│   ├── index.html            # 메인 HTML
│   ├── css/style.css         # 스타일시트
│   ├── js/app.js             # JavaScript (API Bridge 포함)
│   └── data/                 # JSON 데이터 파일들
│       ├── lb_01_imu_001.json
│       ├── lb_01_pad_001.json
│       └── lb_01_insole_001.json
├── assets/
│   └── stridex.ico           # 앱 아이콘
└── requirements.txt          # 의존성
```

## 🚀 실행 방법

### 1. 개발 모드 (Python 직접 실행)
```bash
# 의존성 설치
pip install -r requirements.txt

# 앱 실행
python main.py
```

### 2. 배포 모드 (exe 실행파일)
```bash
# PyInstaller로 빌드 (UTF-8 인코딩 문제 해결)
pyinstaller main.py --name "StrideX_Desktop" --onefile --noconsole --icon assets\stridex.ico --add-data "web;web" --add-data "assets\stridex.ico;assets" --clean

# 실행파일 실행
.\dist\StrideX_Desktop.exe
```

**⚠️ 중요**: em-dash(—) 같은 특수문자는 Python 코드에서 ASCII(-)로 사용하고, HTML에서는 `&mdash;`로 표시합니다.

## 🔧 주요 기능

### 1. 자동 데이터 로드
- 앱 시작 시 `web/data/` 폴더의 모든 JSON 파일을 자동 로드
- Subject ID별로 데이터 그룹화 및 병합

### 2. 파일 추가
- "데이터 추가" 버튼 클릭 시 데스크톱 파일 다이얼로그 열림
- JSON, JSONL, NDJSON, JSON.GZ 형식 지원
- 선택한 파일들을 기존 데이터에 병합

### 3. 데이터 초기화
- "데이터 초기화" 버튼으로 모든 데이터 삭제
- 확인 다이얼로그로 실수 방지

### 4. Subject 선택 및 시각화
- 좌측 Subject 목록에서 선택
- IMU, Gait Pad, Smart Insole 섹션별 시각화
- Meta/Labels 정보 표시

## 🔌 API Bridge

JavaScript에서 Python 함수를 직접 호출:

```javascript
// Subject 목록 가져오기
const result = await window.pywebview.api.get_subjects();

// 특정 Subject 데이터 가져오기
const data = await window.pywebview.api.get_subject("SUBJ_001");

// 파일 추가
const result = await window.pywebview.api.add_files();

// 데이터 초기화
const result = await window.pywebview.api.clear_data();
```

## 🎨 UI 특징

- **3열 레이아웃**: 좌측 Subject 목록, 중앙 대시보드, 우측 Meta/Labels
- **반응형 디자인**: 다양한 화면 크기에 대응
- **한글/영문 라벨**: 자동으로 메트릭명 표시
- **L/R 색상 구분**: 파랑(L), 주황(R)으로 좌우 구분
- **Day 칩 선택**: Smart Insole의 Day 선택을 칩 형태로 구현

## 🐛 문제 해결

### 1. TypeError: start() got an unexpected keyword argument 'js_api' 오류
**원인**: pywebview 4.x에서 `js_api` 매개변수가 `webview.start()`에서 `webview.create_window()`로 이동

**해결방법**:
```python
# ❌ pywebview 3.x 방식 (문제)
webview.start(js_api=api)

# ✅ pywebview 4.x 방식 (수정)
window = webview.create_window(js_api=api)
webview.start()
```

**추가 조치**:
- `requirements.txt`에 `pywebview==4.4.1` 고정
- `pip install -r requirements.txt --upgrade`로 버전 맞춤

### 2. UnicodeEncodeError: 'cp949' codec can't encode character 오류
**원인**: Python 코드에 em-dash(—) 같은 특수문자가 포함되어 Windows cp949 인코딩에서 처리 불가

**해결방법**:
```python
# ❌ 문제가 되는 코드
APP_TITLE = "Gait Physiological Signal Dashboard — StrideX"

# ✅ 수정된 코드
APP_TITLE = "Gait Physiological Signal Dashboard - StrideX"
```

**추가 조치**:
- Python 코드의 모든 특수문자를 ASCII로 변경
- HTML에서는 `&mdash;` 사용 가능
- UTF-8 인코딩 강제 설정 (main.py에 포함됨)

### 3. 앱이 시작되지 않는 경우
- Python 버전 확인 (3.7+ 권장)
- pywebview 설치 확인: `pip install pywebview`
- web/index.html 파일 존재 확인

### 4. 데이터가 로드되지 않는 경우
- web/data/ 폴더에 JSON 파일이 있는지 확인
- JSON 파일 형식이 올바른지 확인
- 콘솔 로그에서 오류 메시지 확인

### 5. 파일 추가가 안 되는 경우
- 파일 다이얼로그가 차단되었는지 확인
- JSON 파일 형식이 지원되는지 확인 (.json, .jsonl, .ndjson, .json.gz)

## 📦 배포

### 1. 단일 exe 파일로 배포
```bash
pyinstaller main.py --name "StrideX_Desktop" --onefile --noconsole --icon assets\stridex.ico --add-data "web;web" --add-data "assets\stridex.ico;assets"
```

### 2. 배포 시 포함할 파일들
- `dist/StrideX_Desktop.exe` (메인 실행파일)
- `web/data/` 폴더 (샘플 데이터, 선택사항)

### 3. 사용자 가이드
- exe 파일을 더블클릭하여 실행
- "데이터 추가" 버튼으로 JSON 파일 로드
- Subject 목록에서 데이터 선택하여 시각화

## 🔄 웹 버전과의 차이점

| 기능 | 웹 버전 | 데스크톱 버전 |
|------|---------|---------------|
| 서버 | FastAPI + uvicorn 필요 | 서버 불필요 |
| 파일 업로드 | HTTP multipart | 데스크톱 다이얼로그 |
| 데이터 저장 | 서버 메모리 | 앱 메모리 |
| 배포 | 서버 + 브라우저 | exe 파일만 |
| 오프라인 | 불가능 | 완전 가능 |

## 🎉 완성!

이제 **exe 하나만 실행하면 모든 기능이 동작하는 완전한 데스크톱 앱**이 완성되었습니다!

- ✅ 서버 설치 불필요
- ✅ 인터넷 연결 불필요  
- ✅ 단일 실행파일로 배포
- ✅ 모든 웹 기능 그대로 유지
