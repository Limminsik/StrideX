# StrideX Desktop Dashboard

**Gait Physiological Signal Dashboard - StrideX**  
보행 생리학적 신호 대시보드 데스크톱 애플리케이션

## 📋 개요

StrideX는 IMU, Gait Pad, Smart Insole 센서 데이터를 통합하여 보행 분석을 수행하는 데스크톱 대시보드입니다. JSON 형태의 센서 데이터를 로드하고 시각화하여 의료진이 환자의 보행 패턴을 쉽게 분석할 수 있도록 도와줍니다.

## ✨ 주요 기능

### 🎯 데이터 시각화
- **IMU 센서**: 보행 주기, 무릎 굴곡/신전 각도, 발 들림 높이
- **Gait Pad**: 보폭, 보행 속도, 입각기/유각기 비율, 이중지지시간
- **Smart Insole**: 보행 속도, 좌우 균형, 발압 분포, 보행 거리, 보폭, 발각도

### 🎨 인터페이스 특징
- **동그라미 포인터**: L/R 값을 시각적으로 비교하는 아름다운 게이지
- **실시간 수치 표시**: 포인터 위에 정확한 수치 표시
- **Subject 기반 관리**: 환자별 데이터 통합 및 관리
- **Day 선택**: Smart Insole 데이터의 일별 분석

### 🔧 기술적 특징
- **단일 실행파일**: PyInstaller로 패키징된 독립 실행형 앱
- **pywebview 기반**: 네이티브 데스크톱 앱 경험
- **데이터 정규화**: 다양한 JSON 형식 자동 처리
- **UTF-8 완전 지원**: 한글 데이터 완벽 처리

## 🚀 설치 및 실행

### 요구사항
- Windows 10/11
- Python 3.7+ (개발 시)

### 실행 방법
1. **바로 실행**: `StrideX_Desktop.exe` 더블클릭
2. **개발 모드**: `python main.py` 실행

## 📁 프로젝트 구조

```
stridex_exe/
├── main.py                 # 메인 애플리케이션 (pywebview + API Bridge)
├── requirements.txt        # Python 의존성
├── StrideX_Desktop.spec    # PyInstaller 설정
├── assets/
│   └── stridex.ico         # 애플리케이션 아이콘
├── web/                    # 프론트엔드 리소스
│   ├── index.html          # 메인 HTML
│   ├── css/style.css       # 스타일시트
│   ├── js/app.js           # JavaScript 로직
│   └── data/               # 샘플 데이터
├── data/                   # 추가 데이터 파일
├── build/                  # PyInstaller 빌드 임시 파일
├── dist/
│   └── StrideX_Desktop.exe # 최종 실행파일
└── README.md               # 이 파일
```

## 🔨 개발 및 빌드

### 개발 환경 설정
```bash
# 의존성 설치
pip install -r requirements.txt

# 개발 모드 실행
python main.py
```

### 실행파일 빌드
```bash
# PyInstaller로 빌드
pyinstaller StrideX_Desktop.spec

# 또는 직접 명령어
pyinstaller main.py --name "StrideX_Desktop" --onefile --noconsole --icon assets\stridex.ico --add-data "web;web" --add-data "assets\stridex.ico;assets"
```

### 빌드 결과
- **실행파일 위치**: `dist/StrideX_Desktop.exe`
- **크기**: 약 11MB
- **독립 실행**: 별도 설치 없이 바로 실행 가능

## 📊 데이터 형식

### 지원하는 JSON 구조
```json
{
  "meta": {
    "patient": {
      "id": "환자ID",
      "gender": "성별",
      "age": "나이",
      "height": "키",
      "weight": "몸무게"
    }
  },
  "labels": {
    "class": "0 또는 1",
    "side": "L 또는 R",
    "region": "부위",
    "diagnosis_text": "진단 내용"
  },
  "data": {
    "imu_sensor": {
      "values": {
        "gait_cycle": {"L": 1.2, "R": 1.3},
        "knee_flexion_max": {"L": 60, "R": 58},
        "knee_extension_max": {"L": 5, "R": 3},
        "foot_clearance": {"L": 12, "R": 11}
      }
    },
    "gait_pad": {
      "values": {
        "step_length": {"L": 70, "R": 72},
        "velocity": {"L": 120, "R": 118},
        "stance_phase_rate": {"L": 60, "R": 62},
        "swing_phase_rate": {"L": 40, "R": 38},
        "double_support_time": {"L": 15, "R": 16}
      }
    },
    "smart_insole": {
      "values": {
        "day_1": {
          "gait_speed": {"L": 1.2, "R": 1.1},
          "balance": {"L": 50, "R": 50},
          "foot_pressure_rear": {"L": 30, "R": 28},
          "foot_pressure_mid": {"L": 40, "R": 42},
          "foot_pressure_fore": {"L": 30, "R": 30},
          "gait_distance": {"L": 100, "R": 98},
          "stride_length": {"L": 65, "R": 67},
          "foot_angle": {"L": 1, "R": 1}
        }
      }
    }
  }
}
```

## 🎯 사용 방법

1. **데이터 추가**: "데이터 추가" 버튼으로 JSON 파일 선택
2. **Subject 선택**: 좌측 리스트에서 환자 선택
3. **데이터 분석**: 중앙 대시보드에서 센서 데이터 확인
4. **Day 선택**: Smart Insole 섹션에서 일별 데이터 분석
5. **데이터 초기화**: "데이터 초기화" 버튼으로 모든 데이터 삭제

## 🔧 주요 기술 스택

- **Backend**: Python 3.7+, pywebview, tkinter
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Packaging**: PyInstaller
- **Data Processing**: JSON, gzip 지원

## 📈 버전 히스토리

### v1.0.0 (2025-09-24)
- 초기 데스크톱 애플리케이션 출시
- IMU, Gait Pad, Smart Insole 섹션 구현
- 동그라미 포인터와 수치 표시 기능
- Subject 기반 데이터 관리
- UTF-8 완전 지원

## 🤝 기여하기

1. 이슈 리포트: 버그나 개선사항을 이슈로 등록
2. 기능 요청: 새로운 기능 제안
3. 코드 기여: Pull Request로 코드 개선

## 📄 라이선스

© 2025 StrideX. All rights reserved.

---

**StrideX Desktop Dashboard** - 보행 분석의 새로운 표준