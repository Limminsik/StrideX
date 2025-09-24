# StrideX Web Dashboard 배포 가이드

## 🚀 빠른 시작 (로컬 테스트)

### 1. 로컬 실행
```bash
cd C:\dev\05_viewer\stridex_web
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 접속
- **로컬**: http://localhost:8000
- **외부**: http://<공인IP>:8000

---

## 🌐 외부 배포 옵션

### 옵션 A: ngrok (가장 빠름, 테스트용)

1. **ngrok 설치**
   ```bash
   # Windows
   choco install ngrok
   # 또는 https://ngrok.com/download 에서 다운로드
   ```

2. **터널 생성**
   ```bash
   ngrok http 8000
   ```

3. **결과**
   ```
   Forwarding  https://abc123.ngrok.io -> http://localhost:8000
   ```
   - `https://abc123.ngrok.io`를 외부에 공유하면 즉시 접속 가능

### 옵션 B: Docker 배포 (추천)

1. **Docker 이미지 빌드**
   ```bash
   cd C:\dev\05_viewer\stridex_web
   docker build -t stridex .
   ```

2. **컨테이너 실행**
   ```bash
   docker run -d --name stridex -p 8000:8000 stridex
   ```

3. **Docker Compose 사용**
   ```bash
   docker-compose up -d
   ```

### 옵션 C: 서버 배포 (운영용)

#### Ubuntu 서버 설정

1. **서버 준비**
   ```bash
   # Ubuntu 업데이트
   sudo apt update && sudo apt upgrade -y
   
   # Python 3.11 설치
   sudo apt install python3.11 python3.11-venv python3.11-pip -y
   
   # Git 설치
   sudo apt install git -y
   ```

2. **애플리케이션 배포**
   ```bash
   # 프로젝트 클론
   git clone <your-repo-url> stridex
   cd stridex
   
   # 가상환경 생성
   python3.11 -m venv .venv
   source .venv/bin/activate
   
   # 의존성 설치
   pip install -r requirements.txt
   ```

3. **Systemd 서비스 설정**
   ```bash
   sudo nano /etc/systemd/system/stridex.service
   ```

   ```ini
   [Unit]
   Description=StrideX Dashboard
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/home/ubuntu/stridex
   Environment="PATH=/home/ubuntu/stridex/.venv/bin"
   ExecStart=/home/ubuntu/stridex/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

4. **서비스 시작**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable stridex
   sudo systemctl start stridex
   sudo systemctl status stridex
   ```

#### Nginx 리버스 프록시

1. **Nginx 설치**
   ```bash
   sudo apt install nginx -y
   ```

2. **사이트 설정**
   ```bash
   sudo nano /etc/nginx/sites-available/stridex
   ```

   ```nginx
   server {
       listen 80;
       server_name your.domain.com;

       client_max_body_size 50M;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **사이트 활성화**
   ```bash
   sudo ln -s /etc/nginx/sites-available/stridex /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

#### HTTPS 설정 (Let's Encrypt)

1. **Certbot 설치**
   ```bash
   sudo apt install certbot python3-certbot-nginx -y
   ```

2. **SSL 인증서 발급**
   ```bash
   sudo certbot --nginx -d your.domain.com
   ```

---

## 🔧 방화벽 설정

### Windows 방화벽
1. Windows Defender 방화벽 → 고급 설정
2. 인바운드 규칙 → 새 규칙
3. 포트 → TCP → 8000 → 허용

### Ubuntu UFW
```bash
sudo ufw allow 8000/tcp
sudo ufw allow 'Nginx HTTP'
sudo ufw allow 'Nginx HTTPS'
sudo ufw enable
```

---

## 📋 배포 체크리스트

- [ ] 서버에서 정적 파일 경로 확인
- [ ] 파일 업로드 크기 제한 설정 (50MB)
- [ ] CORS 설정 확인
- [ ] HTTPS 적용
- [ ] 도메인 DNS 설정
- [ ] 방화벽 포트 열기
- [ ] 로그 로테이션 설정
- [ ] 백업 전략 수립

---

## 🐛 문제 해결

### 포트 충돌
```bash
# 포트 사용 중인 프로세스 확인
netstat -tulpn | grep :8000
# 또는
lsof -i :8000
```

### 권한 문제
```bash
# 파일 권한 설정
sudo chown -R ubuntu:ubuntu /home/ubuntu/stridex
chmod +x /home/ubuntu/stridex/.venv/bin/uvicorn
```

### 서비스 재시작
```bash
# StrideX 서비스 재시작
sudo systemctl restart stridex
sudo systemctl status stridex

# Nginx 재시작
sudo systemctl restart nginx
```

---

## 📞 지원

문제가 발생하면 다음을 확인하세요:
1. 서비스 상태: `sudo systemctl status stridex`
2. 로그 확인: `sudo journalctl -u stridex -f`
3. 포트 확인: `netstat -tulpn | grep :8000`
4. 방화벽 상태: `sudo ufw status`
