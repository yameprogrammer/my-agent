$ErrorActionPreference = "Stop"

Write-Host "🧹 .env 텔레그램 설정 초기화 스크립트를 시작합니다..." -ForegroundColor Cyan

$envFilePath = Join-Path $PSScriptRoot ".env"

if (-not (Test-Path $envFilePath)) {
    Write-Host "⚠️ .env 파일을 찾을 수 없습니다. 삭제할 내용이 없습니다." -ForegroundColor Yellow
    exit
}

$envContent = Get-Content $envFilePath -Raw

# 삭제할 키 목록
$keysToRemove = @(
    "TELEGRAM_BOT_TOKEN",
    "ADMIN_TELEGRAM_CHAT_ID",
    "TELEGRAM_WEBHOOK_SECRET",
    "BASE_URL"
)

$modified = $false

foreach ($key in $keysToRemove) {
    # 정규식을 사용하여 해당 키가 포함된 전체 줄을 제거
    $pattern = "(?m)^$key=.*`r?`n?"
    if ($envContent -match $pattern) {
        $envContent = $envContent -replace $pattern, ""
        Write-Host "🗑️ 삭제 완료: $key" -ForegroundColor Gray
        $modified = $true
    }
}

if ($modified) {
    # 불필요하게 남은 빈 줄 정리
    $envContent = $envContent -replace "(?m)^\s*`r?`n", ""
    $envContent | Set-Content $envFilePath -NoNewline
    Write-Host "`n✅ .env 파일에서 텔레그램 및 로컬 터널(ngrok) 설정이 성공적으로 제거되었습니다!" -ForegroundColor Green
} else {
    Write-Host "`n✅ .env 파일에 삭제할 텔레그램/터널 관련 설정이 없습니다." -ForegroundColor Green
}
