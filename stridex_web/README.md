# StrideX Web Dashboard

StrideX 생체신호 대시보드의 웹 기반 버전입니다.

## 🚀 기능

- **Subject 기반 데이터 관리**: 환자 ID별 센서 데이터 통합
- **실시간 시각화**: IMU, Gait Pad, Smart Insole 데이터 시각화
- **인터랙티브 UI**: Subject 선택, Day 선택, 지표 설명 토글
- **반응형 디자인**: 다양한 화면 크기 지원

## 📁 프로젝트 구조

```
stridex_web/
├── main.py              # FastAPI 서버
├── data/                # JSON 데이터 파일
├── static/
│   ├── css/            # 스타일시트
│   ├── js/             # JavaScript 앱
│   └── img/            # 이미지 파일
├── templates/
│   └── index.html      # HTML 템플릿
├── requirements.txt    # Python 의존성
└── README.md          # 프로젝트 문서
```

## 🛠️ 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 서버 실행
```bash
python main.py
```

### 3. 브라우저에서 접속
```
http://localhost:8000
```

## 🔧 API 엔드포인트

- `GET /` - 메인 대시보드 페이지
- `GET /api/subjects` - 모든 Subject 목록
- `GET /api/subject/{id}` - 특정 Subject 데이터
- `GET /api/subject/{id}/sensor/{type}` - 특정 센서 데이터

## 📊 지원 센서

- **IMU**: 보행 주기, 무릎 각도, 발 들림 높이
- **Gait Pad**: 보폭, 보행 속도, 입각기/유각기 비율
- **Smart Insole**: 보행 속도, 균형, 압력 분포, Day별 데이터

## 🎨 UI 특징

- **DualMarkerGaugeRow**: L/R 값을 같은 바에 두 마커로 표시
- **반응형 그리드**: 화면 크기에 따라 자동 조정
- **실시간 업데이트**: Subject 선택 시 즉시 데이터 반영
- **직관적 네비게이션**: 좌측 Subject 리스트, 중앙 대시보드

## 🔄 기존 stridex.py와의 차이점

- **웹 기반**: 브라우저에서 실행, 크로스 플랫폼 지원
- **API 분리**: 데이터 처리와 UI 완전 분리
- **확장성**: 나중에 모바일, 태블릿 지원 가능
- **배포**: 웹 서버 또는 Electron으로 데스크톱 앱화

## 📝 개발 노트

- 기존 `stridex.py`의 핵심 기능을 웹으로 포팅
- FastAPI를 사용한 RESTful API 구현
- Chart.js, Plotly.js 등 웹 차트 라이브러리 활용 가능
- Figma 디자인 시스템 적용 예정
