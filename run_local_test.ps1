$ErrorActionPreference = "Stop"

Write-Host "🚀 [로컬 환경] 소설싸개 풀스택 통합 실행 스크립트를 시작합니다..." -ForegroundColor Cyan
Write-Host "--------------------------------------------------------"

# 0. 데이터베이스(Docker) 자동 구동
Write-Host "🐳 데이터베이스(PostgreSQL)를 시작합니다..." -ForegroundColor Blue
try {
    docker-compose up -d
    Write-Host "✅ 데이터베이스가 실행되었습니다!" -ForegroundColor Green
    Start-Sleep -Seconds 2
} catch {
    Write-Host "⚠️ Docker 실행 실패. (수동으로 DB를 관리하신다면 무시하세요)" -ForegroundColor Yellow
}
Write-Host "--------------------------------------------------------"

$envFilePath = Join-Path $PSScriptRoot ".env"

# 1. ngrok 프로세스 확인 및 인증 처리
$ngrokPath = "ngrok"
if (-not (Get-Command "ngrok" -ErrorAction SilentlyContinue)) {
    Write-Host "🔎 ngrok 실행 파일을 스캔합니다..." -ForegroundColor Gray
    $wingetDir = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    if (Test-Path $wingetDir) {
        $found = Get-ChildItem -Path $wingetDir -Filter "ngrok.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { $ngrokPath = $found.FullName }
        else { Write-Host "❌ ngrok.exe를 찾을 수 없습니다." -ForegroundColor Red; exit }
    } else { Write-Host "❌ ngrok.exe를 찾을 수 없습니다." -ForegroundColor Red; exit }
}

$existingNgrok = Get-Process -Name "ngrok" -ErrorAction SilentlyContinue
if ($existingNgrok) {
    Write-Host "🧹 기존 ngrok 프로세스를 정리합니다..." -ForegroundColor Yellow
    Stop-Process -Name "ngrok" -Force
    Start-Sleep -Seconds 1
}

# ngrok 인증(Authtoken) 확인 및 등록 로직
if (-not (Test-Path $envFilePath)) { New-Item -Path $envFilePath -ItemType File | Out-Null }
$envContent = Get-Content $envFilePath -Raw

if (-not ($envContent -match "(?m)^NGROK_AUTHTOKEN=`"?([^`"\r\n]+)`"?$")) {
    Write-Host "`n⚠️ [중요] ngrok은 보안상 가입자의 인증 토큰이 있어야만 사용할 수 있습니다!" -ForegroundColor Red
    Write-Host "1. https://dashboard.ngrok.com/signup 에 접속하여 구글 계정 등으로 5초 만에 로그인/가입하세요." -ForegroundColor White
    Write-Host "2. https://dashboard.ngrok.com/get-started/your-authtoken 화면에 있는 긴 토큰을 복사하세요." -ForegroundColor White
    $ngrokToken = Read-Host "👉 복사한 ngrok 토큰을 여기에 붙여넣기 하세요 (마우스 우클릭)"
    
    if (-not [string]::IsNullOrWhiteSpace($ngrokToken)) {
        & $ngrokPath config add-authtoken $ngrokToken
        Write-Host "✅ ngrok 인증 토큰이 시스템에 등록되었습니다!" -ForegroundColor Green
        
        if (-not $envContent.EndsWith("`n") -and $envContent.Length -gt 0) { $envContent += "`n" }
        $envContent += "NGROK_AUTHTOKEN=`"$ngrokToken`"`n"
        $envContent | Set-Content $envFilePath -NoNewline
    } else {
        Write-Host "❌ 토큰을 입력하지 않으시면 터널을 열 수 없습니다." -ForegroundColor Red
        exit
    }
}

Write-Host "🌐 ngrok을 백그라운드에서 실행하여 8080 포트(백엔드)를 터널링합니다..." -ForegroundColor Green
Start-Process -FilePath $ngrokPath -ArgumentList "http 8080" -WindowStyle Hidden

Write-Host "⏳ 텔레그램용 HTTPS URL 발급을 기다리는 중..." -ForegroundColor Yellow
$ngrokUrl = $null
$retryCount = 0

while ($null -eq $ngrokUrl -and $retryCount -lt 15) {
    Start-Sleep -Seconds 2
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -ErrorAction Stop
        $tunnel = $response.tunnels | Where-Object { $_.public_url -match "^https" }
        if ($tunnel) {
            $ngrokUrl = $tunnel.public_url
        }
    } catch { }
    $retryCount++
}

if ([string]::IsNullOrEmpty($ngrokUrl)) {
    Write-Host "❌ URL 발급 실패: ngrok이 설치되어 있는지 확인하세요. (https://ngrok.com/download)" -ForegroundColor Red
    exit
}
Write-Host "✅ 터널 생성 완료: $ngrokUrl" -ForegroundColor Green

# 2. .env 파일 점검 및 BASE_URL 동적 주입
if (-not (Test-Path $envFilePath)) {
    New-Item -Path $envFilePath -ItemType File | Out-Null
}
$envContent = Get-Content $envFilePath -Raw

# 필수 변수 검사
$varsToCheck = @("TELEGRAM_BOT_TOKEN", "ADMIN_TELEGRAM_CHAT_ID", "TELEGRAM_WEBHOOK_SECRET")
foreach ($var in $varsToCheck) {
    if (-not ($envContent -match "(?m)^$var=`"?([^`"\r\n]+)`"?$")) {
        $inputValue = Read-Host "⚠️ [$var] 값을 입력하세요"
        if (-not $envContent.EndsWith("`n") -and $envContent.Length -gt 0) { $envContent += "`n" }
        $envContent += "$var=`"$inputValue`"`n"
    }
}

# BASE_URL 교체 (ngrok의 https 주소)
if ($envContent -match "(?m)^BASE_URL=.*$") {
    $envContent = $envContent -replace "(?m)^BASE_URL=.*$", "BASE_URL=`"$ngrokUrl`""
} else {
    if (-not $envContent.EndsWith("`n") -and $envContent.Length -gt 0) { $envContent += "`n" }
    $envContent += "BASE_URL=`"$ngrokUrl`"`n"
}
$envContent | Set-Content $envFilePath -NoNewline
Write-Host "✅ 동적 URL($ngrokUrl)을 환경변수(BASE_URL)에 주입했습니다." -ForegroundColor Green
Write-Host "--------------------------------------------------------"

# 3. 가상 환경 검사
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "❌ 가상 환경(.venv)을 찾을 수 없습니다." -ForegroundColor Red
    exit
}

# 4. 프론트엔드 (UI) 구동
Write-Host "🎨 프론트엔드 화면(Streamlit)을 백그라운드 창에서 구동합니다..." -ForegroundColor Magenta
$uiProcess = Start-Process -FilePath $venvPython -ArgumentList "-m streamlit run ui/app.py --server.port 8501" -PassThru -WindowStyle Minimized
Write-Host "✅ UI 구동 완료! (잠시 후 브라우저가 자동으로 열립니다)" -ForegroundColor Green
Write-Host "--------------------------------------------------------"

# 5. 백엔드 (API) 구동
Write-Host "🚀 소설싸개 백엔드 서버(uvicorn)를 구동합니다..." -ForegroundColor Cyan
Write-Host "🛑 모두 종료하시려면 이 창에서 [Ctrl+C] 를 누르세요." -ForegroundColor DarkGray

try {
    # uvicorn 실행 (종료 시까지 터미널 블록)
    & $venvPython -m uvicorn app.main:app --port 8080 --reload
} finally {
    Write-Host "`n서버 종료 중... 🧹 백그라운드 프로세스들을 안전하게 모두 종료합니다." -ForegroundColor Yellow
    Get-Process -Name "ngrok" -ErrorAction SilentlyContinue | Stop-Process -Force
    if ($uiProcess) {
        Stop-Process -Id $uiProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "✅ 백엔드, 프론트엔드, 터널링 모두 종료 완료!" -ForegroundColor Green
}
