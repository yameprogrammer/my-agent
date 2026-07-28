#!/usr/bin/env bash

# =================================================================
# Termux (Android 스마트폰 홈서버) 자동 배포 스크립트 — IMP-04/05
# =================================================================
# 이 스크립트는 스마트폰 Termux 환경에서 PostgreSQL, pgvector, Python Venv,
# SPA 빌드 및 PM2 프로세스 매니저를 자동으로 설치하고 구동하기 위한 스크립트입니다.
# 사용 방법: Termux 셸에서 `bash deploy/deploy_termux.sh` 실행

set -e

echo "=== [1/7] Termux 시스템 패키지 업데이트 및 필수 패키지 설치 ==="
pkg update -y
pkg install python nodejs postgresql git clang make python-cryptography python-numpy -y

echo "=== [2/7] pgvector extension 소스 빌드 및 설치 ==="
# Termux 환경은 루트 /tmp 에 권한이 없을 수 있으므로 로컬 임시 폴더를 사용합니다.
PGV_TMP="./tmp_pgvector"
if [ -d "$PGV_TMP" ]; then
    rm -rf "$PGV_TMP"
fi
git clone https://github.com/pgvector/pgvector.git "$PGV_TMP"
cd "$PGV_TMP"
make
make install
cd -
rm -rf "$PGV_TMP"
echo "pgvector 설치 완료!"

echo "=== [3/7] PostgreSQL 데이터베이스 초기화 및 백그라운드 구동 ==="
# Termux의 기본 PostgreSQL 데이터 경로를 정의합니다.
PG_DATA="$PREFIX/var/lib/postgres"
if [ ! -d "$PG_DATA" ]; then
    echo "데이터베이스 클러스터를 초기화합니다..."
    initdb -D "$PG_DATA"
fi

# PostgreSQL 서버가 켜져 있는지 확인하고 꺼져 있으면 켭니다.
if ! pg_ctl -D "$PG_DATA" status > /dev/null 2>&1; then
    echo "PostgreSQL 서버를 시작합니다..."
    pg_ctl -D "$PG_DATA" -l "$PG_DATA/server.log" start
    sleep 2
fi

# novel_db 데이터베이스 생성 (이미 존재하면 에러 무시)
createdb -U $(whoami) novel_db || echo "데이터베이스가 이미 존재하거나 생성되었습니다."

echo "=== [4/7] Python 가상환경(Venv) 설정 및 백엔드 의존성 설치 ==="
if [ ! -d ".venv" ]; then
    python -m venv .venv --system-site-packages
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt -v
deactivate
echo "백엔드 의존성 설치 완료!"

echo "=== [5/7] 프론트엔드 SPA 프로덕션 빌드 ==="
cd frontend
npm install
npm run build
cd ..
echo "프론트엔드 SPA 빌드 및 FastAPI 연동 준비 완료!"

echo "=== [6/7] PM2 프로세스 매니저 글로벌 설치 및 백그라운드 등록 ==="
npm install -g pm2
# Termux 경로에 맞춰 ecosystem.config.cjs 수정 및 실행
# PM2로 uvicorn을 python venv 내부 인터프리터로 구동합니다.
pm2 start deploy/ecosystem.config.cjs
pm2 save
echo "PM2 백그라운드 프로세스 등록 완료!"

echo "=== [7/7] .env 환경 변수 템플릿 생성 및 가이드 ==="
if [ ! -f ".env" ]; then
    cp .env.template .env
    # Fernet API Key 암호화 시크릿 키 자동 생성 주입
    FERNET_KEY=$(.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    # JWT_SECRET 임의 생성 주입
    JWT_SECRET_KEY=$(.venv/bin/python -c "import secrets; print(secrets.token_hex(32))")
    
    # 윈도우/맥/리눅스 호환 sed 처리 (Termux 환경 변형 고려)
    sed -i "s/ENVIRONMENT=development/ENVIRONMENT=production/g" .env
    sed -i "s/API_KEY_ENCRYPTION_SECRET=/API_KEY_ENCRYPTION_SECRET=$FERNET_KEY/g" .env
    sed -i "s/JWT_SECRET=dev-secret-key-do-not-use-in-production/JWT_SECRET=$JWT_SECRET_KEY/g" .env
    sed -i "s|DATABASE_URL=postgresql+asyncpg://postgres:password@127.0.0.1:5432/novel_db|DATABASE_URL=postgresql+asyncpg://$(whoami)@127.0.0.1:5432/novel_db|g" .env
    
    echo "" >> .env
    echo "# 12. 접속 포트 설정 (스마트폰 배포 커스텀)" >> .env
    echo "PORT=8080" >> .env
    
    echo "새로운 .env 파일이 생성되었으며, 필수 보안 키(JWT_SECRET, API_KEY_ENCRYPTION_SECRET)와 접속 포트(PORT=8080)가 기본값으로 추가 설정되었습니다."
else
    echo ".env 파일이 이미 존재하므로 덮어쓰지 않았습니다."
fi

echo "--------------------------------------------------------"
echo "🎉 스마트폰 서버(Termux) 배포 준비가 완료되었습니다!"
echo "--------------------------------------------------------"
echo "1. 실제 구동을 위해 .env 파일을 편집하여 필요한 AI API 키 등을 입력하십시오:"
echo "   nano .env"
echo "2. 포트를 변경하고 싶다면 .env 내의 'PORT=8080' 항목을 원하는 포트로 수정하십시오."
echo "3. API 키 및 포트 변경 완료 후 pm2 restart novel-agent 명령으로 재시작하십시오."
echo "4. 웹브라우저로 http://127.0.0.1:<설정한PORT> 에 접속해 구동 상태를 확인하십시오."
echo "--------------------------------------------------------"
