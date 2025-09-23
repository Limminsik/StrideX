# JSON Viewer (meta / data / labels)

Tkinter + Matplotlib 기반의 로컬 데스크탑 JSON 뷰어입니다. `meta / data / labels` 구조의 파일을 빠르게 탐색하고, `data`의 수치 데이터를 자동 시각화합니다.

## 설치

Python 3.13+ 권장. 필요한 패키지:

```
pip install numpy matplotlib
```

또는 프로젝트 의존성으로 설치:

```
pip install -e .
```

## 실행

```
python 05_viewer_json_app.py C:\dev\05_viewer\data
```

폴더 인자를 생략하면 현재 작업 디렉토리를 기본으로 로드합니다:

```
python 05_viewer_json_app.py
```

### v2 (자동 분류형, 최상단에 meta/data/labels가 없어도 동작)

```
python 05_viewer_json_app_v2.py C:\dev\05_viewer\data
```

또는 폴더 인자 없이 실행 후 앱 좌측 상단 '열기' 버튼으로 선택:

```
python 05_viewer_json_app_v2.py
```

## 주요 기능

- 좌측: 폴더 선택 + JSON 파일 리스트
- 우측 탭:
  - Meta: JSON 트리 뷰 + 상단 요약(ID/age/gender/condition)
  - Data: 채널/키 콤보 선택 → 자동 시각화(1D 라인, 2D 히트맵). 통계(count/mean/std/min/median/max) 출력
  - Labels: JSON 트리 뷰
- 센서 타입 휴리스틱: `imu`, `insole`, `gait_pad` 키워드를 감지하여 시각화 기본값을 조정
- 대용량 배열 자동 다운샘플(기본 5,000포인트)
- 비수치/고차원 배열은 안내 문구로 처리

## 확장 포인트

- 렌더러 분리(`renderer_insole.py`, `renderer_imu.py`, `renderer_pad.py`) 구조로 확장 가능
- 라벨 시간정보가 있으면 플롯 오버레이(추후 기능)
- 동일 로직을 Streamlit/FastAPI 기반 웹 UI로 이식 용이

## 샘플 데이터

`data/` 폴더의 샘플을 활용해 동작을 확인할 수 있습니다.


