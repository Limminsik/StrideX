# StrideX Desktop Application 빌드 가이드

## 🎯 완성된 데스크톱 앱

**pywebview + FastAPI + PyInstaller** 조합으로 네이티브 데스크톱 앱을 성공적으로 빌드했습니다!

### 📁 프로젝트 구조
```
stridex_web/
├─ backend/
│  ├─ api.py              # FastAPI 백엔드
│  ├─ static/             # 웹 프론트엔드 파일
│  │  ├─ index.html
│  │  ├─ css/style.css
│  │  └─ js/app.js
│  └─ data/               # JSON 데이터 파일들
├─ desktop/
│  └─ main.py             # pywebview 런처
├─ assets/
│  └─ stridex.ico         # 앱 아이콘
├─ dist/
│  └─ StrideX Dashboard.exe  # 최종 실행파일 (11.7MB)
└─ requirements.txt
```

## 🚀 빌드 과정

### 1. 의존성 설치
```bash
pip install -r requirements.txt
pip install pyinstaller Pillow
```

### 2. PyInstaller 빌드
```bash
pyinstaller desktop\main.py ^
  --name "StrideX Dashboard" ^
  --onefile --noconsole ^
  --icon assets\stridex.ico ^
  --add-data "backend\static;backend\static" ^
  --add-data "backend\data;backend\data" ^
  --add-data "assets\stridex.ico;assets" ^
  --hidden-import uvicorn ^
  --hidden-import fastapi ^
  --hidden-import pywebview
```

### 3. 실행
```bash
dist\StrideX Dashboard.exe
```

## ✨ 주요 특징

### 🖥️ 네이티브 데스크톱 앱
- **pywebview**: Chromium/Edge WebView 사용
- **창 크기**: 1400x900 (리사이즈 가능)
- **아이콘**: StrideX 로고 적용
- **제목**: "Gait Physiological Signal Dashboard — StrideX"

### 🔧 내장 서버
- **FastAPI**: 백엔드 API 서버
- **자동 포트**: 사용 가능한 포트 자동 선택
- **로컬 전용**: 127.0.0.1에서만 접근
- **데이터 관리**: JSON 파일 업로드/다운로드

### 📊 완전한 기능
- **Subject 관리**: 환자 데이터 로드/관리
- **3센서 통합**: IMU, Gait Pad, Smart Insole
- **실시간 시각화**: 게이지, 차트, 메타데이터
- **파일 업로드**: JSON 파일 추가/초기화

## 🎨 UI/UX 개선사항

### 레이아웃
- **3열 구조**: 좌측 Subject 목록, 중앙 대시보드, 우측 Meta/Labels
- **반응형**: 다양한 화면 크기 지원
- **스크롤**: 중앙 대시보드 세로 스크롤

### 시각화
- **게이지 바**: L/R 값 비교 (파랑/주황 포인터)
- **애니메이션**: 부드러운 포인터 이동
- **Day 칩**: Smart Insole Day 선택
- **메트릭 라벨**: 한글/영문 병기

### 상호작용
- **버튼**: 좌측 패널에 통합된 데이터 추가/초기화
- **Subject 선택**: 클릭으로 환자 데이터 로드
- **파일 업로드**: 드래그 앤 드롭 지원

## 📦 배포 방법

### 단일 실행파일
- **크기**: 11.7MB
- **의존성**: 모두 포함 (standalone)
- **설치**: 불필요 (실행만 하면 됨)
- **배포**: `StrideX Dashboard.exe` 파일만 전달

### 시스템 요구사항
- **OS**: Windows 10/11
- **메모리**: 최소 4GB RAM
- **디스크**: 50MB 여유 공간
- **네트워크**: 불필요 (로컬 실행)

## 🔧 문제 해결

### 빌드 오류
1. **PIL 오류**: `pip install Pillow`
2. **경로 오류**: Windows는 `;`, Linux/Mac은 `:` 사용
3. **모듈 오류**: `--hidden-import` 옵션 추가

### 실행 오류
1. **포트 충돌**: 자동으로 다른 포트 선택
2. **파일 권한**: 관리자 권한으로 실행
3. **방화벽**: Windows Defender 허용

### 성능 최적화
1. **메모리**: 대용량 JSON 파일 시 메모리 사용량 증가
2. **CPU**: 시각화 업데이트 시 CPU 사용량 증가
3. **디스크**: 임시 파일은 자동 정리

## 🎉 성공 지표

✅ **네이티브 창**: pywebview로 데스크톱 앱 구현  
✅ **내장 서버**: FastAPI 백엔드 자동 실행  
✅ **단일 파일**: PyInstaller로 11.7MB exe 생성  
✅ **아이콘 적용**: StrideX 로고 정상 표시  
✅ **완전 기능**: 웹 버전과 동일한 모든 기능  
✅ **독립 실행**: Python 설치 불필요  

## 🚀 다음 단계

1. **코드 서명**: Windows SmartScreen 경고 제거
2. **인스톨러**: NSIS/Inno Setup으로 설치 프로그램 생성
3. **자동 업데이트**: 버전 관리 및 업데이트 시스템
4. **다중 플랫폼**: macOS/Linux 지원

---

**StrideX Desktop Application이 성공적으로 완성되었습니다!** 🎉✨
