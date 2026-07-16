# ==========================================
# 1단계: 프론트엔드 빌드 (Node.js)
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ==========================================
# 2단계: 백엔드 및 런타임 환경 구성 (Python)
# ==========================================
FROM python:3.11-slim AS runner

# WeasyPrint(EPUB/PDF 컴파일러) 및 SSL, 빌드에 필요한 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libffi-dev \
    shared-mime-info \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libjpeg-dev \
    libopenjp2-7-dev \
    libgdk-pixbuf2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Python 백엔드 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 백엔드 소스코드 복사
COPY app/ ./app/

# 1단계에서 빌드된 프론트엔드 정적 파일 복사 (FastAPI에서 SPA 형태로 통합 서빙)
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 컨테이너 내 포트 개방
EXPOSE 8080

# uvicorn 기동 (프록시 헤더 설정 적용: Nginx 등의 뒤에서 HTTPS 클라이언트 IP 신뢰 가능하도록)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips=*"]
