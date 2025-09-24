# StrideX Dashboard 배포 가이드

## 🚀 빠른 시작

### 로컬 개발 서버
```bash
# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행 (로컬만)
uvicorn main:app --reload

# 외부 접속 가능한 서버 실행
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Docker 배포
```bash
# Docker 이미지 빌드
docker build -t stridex-dashboard .

# Docker 컨테이너 실행
docker run -p 8000:8000 -v $(pwd)/data:/app/data stridex-dashboard

# Docker Compose 사용
docker-compose up -d
```

## 🌐 외부 접속 설정

### 1. 방화벽 설정
```bash
# Windows (관리자 권한)
netsh advfirewall firewall add rule name="StrideX Dashboard" dir=in action=allow protocol=TCP localport=8000

# Linux
sudo ufw allow 8000
```

### 2. 공인 IP 확인
```bash
# Windows
curl ifconfig.me

# Linux
curl ifconfig.me
```

### 3. 접속 URL
- 로컬: `http://localhost:8000`
- 외부: `http://<공인IP>:8000`

## 🔧 프로덕션 배포

### Nginx 리버스 프록시 설정
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### HTTPS 설정 (Let's Encrypt)
```bash
# Certbot 설치
sudo apt install certbot python3-certbot-nginx

# SSL 인증서 발급
sudo certbot --nginx -d your-domain.com
```

## 📊 모니터링

### 헬스체크
```bash
# 서버 상태 확인
curl http://localhost:8000/api/subjects

# Docker 헬스체크
docker ps
```

### 로그 확인
```bash
# Docker 로그
docker-compose logs -f stridex

# 시스템 로그
journalctl -u stridex
```

## 🛠️ 문제 해결

### 포트 충돌
```bash
# 포트 사용 중인 프로세스 확인
netstat -ano | findstr :8000

# 프로세스 종료
taskkill /PID <PID> /F
```

### CORS 오류
- `main.py`에서 `allow_origins` 설정 확인
- 브라우저 개발자 도구에서 네트워크 탭 확인

### 파일 업로드 오류
- `python-multipart` 패키지 설치 확인
- 파일 크기 제한 확인 (기본 1MB)

## 📁 디렉토리 구조
```
stridex_web/
├── main.py              # FastAPI 서버
├── requirements.txt     # Python 의존성
├── Dockerfile          # Docker 이미지 설정
├── docker-compose.yml  # Docker Compose 설정
├── data/               # JSON 데이터 파일
├── static/             # 정적 파일 (CSS, JS)
└── templates/          # HTML 템플릿
```

## 🔒 보안 고려사항

1. **CORS 설정**: 프로덕션에서는 특정 도메인만 허용
2. **파일 업로드**: 파일 크기 및 타입 제한
3. **HTTPS**: 프로덕션에서는 반드시 HTTPS 사용
4. **방화벽**: 필요한 포트만 개방

## 📞 지원

문제가 발생하면 다음을 확인하세요:
1. 서버 로그 확인
2. 네트워크 연결 상태 확인
3. 방화벽 설정 확인
4. 포트 사용 상태 확인
