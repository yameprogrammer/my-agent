import os
import sys
import io
import time
import re
import subprocess
import shutil
import urllib.request
import json
import signal

# Windows 콘솔(CP949 등)에서 이모지 및 유니코드 출력 시 에러를 방지하기 위해 표준 스트림 인코딩을 UTF-8로 강제 재설정합니다.
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python 3.7 미만 등 reconfigure가 없는 구버전 대비 fallback
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 콘솔 색상 정의 (ANSI Escape Codes)
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    GRAY = '\033[90m'
    MAGENTA = '\033[95m'
    END = '\033[0m'

def print_color(text, color):
    # Windows 레거시 cmd의 경우 ANSI 색상 호환이 안 될 수 있으므로, 에러 방지를 위해 간단히 처리
    try:
        if os.name == 'nt' and not os.environ.get('WT_SESSION'):
            print(text)
        else:
            print(f"{color}{text}{Colors.END}")
    except UnicodeEncodeError:
        # 인코딩 에러 발생 시, CP949 콘솔 등에서 깨지지 않는 아스키/가독성 범위 문자로 대체하여 출력
        clean_text = text.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)
        if os.name == 'nt' and not os.environ.get('WT_SESSION'):
            print(clean_text)
        else:
            print(f"{color}{clean_text}{Colors.END}")

# 전역 프로세스 리스트 (clean up 용)
processes = []

def cleanup(signum=None, frame=None):
    print_color("\n서버 종료 중... 🧹 백그라운드 프로세스들을 안전하게 모두 종료합니다.", Colors.YELLOW)
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=2)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    print_color("✅ 백엔드, 프론트엔드, 터널링 모두 종료 완료!", Colors.GREEN)
    sys.exit(0)

# 시그널 핸들러 등록
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def main():
    print_color("🚀 [로컬 환경] 소설싸개 풀스택 통합 실행 스크립트를 시작합니다...", Colors.CYAN)
    print("--------------------------------------------------------")

    # 0. 데이터베이스(Docker) 자동 구동
    print_color("🐳 데이터베이스(PostgreSQL)를 시작합니다...", Colors.BLUE)
    try:
        subprocess.run(["docker-compose", "up", "-d"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print_color("✅ 데이터베이스가 실행되었습니다!", Colors.GREEN)
        time.sleep(2)
    except Exception:
        print_color("⚠️ Docker 실행 실패. (수동으로 DB를 관리하신다면 무시하세요)", Colors.YELLOW)
    print("--------------------------------------------------------")

    # 0.1 데이터베이스 포트 가용성 검사
    import socket
    db_port = 5432
    db_host = "127.0.0.1"
    
    def check_port(host, port):
        try:
            with socket.create_connection((host, port), timeout=2):
                return True
        except OSError:
            return False
            
    if not check_port(db_host, db_port):
        print_color(f"\n❌ 오류: 데이터베이스 포트({db_port})가 닫혀 있습니다.", Colors.RED)
        print_color("💡 원인: Docker Desktop이 비활성화 상태이거나, PostgreSQL 컨테이너가 정상적으로 실행되지 않았습니다.", Colors.YELLOW)
        print_color("👉 해결방법: Docker Desktop을 켜고 데이터베이스 컨테이너가 정상 기동된 상태에서 다시 시도해 주세요.", Colors.GRAY)
        sys.exit(1)

    # 1. OS별 ngrok 탐색
    is_windows = sys.platform.startswith('win')
    ngrok_filename = "ngrok.exe" if is_windows else "ngrok"
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_ngrok_root = os.path.join(script_dir, ngrok_filename)
    local_ngrok_bin = os.path.join(script_dir, "bin", ngrok_filename)

    ngrok_path = None

    if os.path.exists(local_ngrok_root):
        ngrok_path = local_ngrok_root
        print_color(f"🔎 프로젝트 루트에서 ngrok을 감지했습니다: {ngrok_path}", Colors.GREEN)
    elif os.path.exists(local_ngrok_bin):
        ngrok_path = local_ngrok_bin
        print_color(f"🔎 프로젝트 bin 폴더에서 ngrok을 감지했습니다: {ngrok_path}", Colors.GREEN)
    elif shutil.which("ngrok"):
        ngrok_path = "ngrok"
        print_color("🔎 시스템 PATH에서 ngrok을 감지했습니다.", Colors.GREEN)
    elif is_windows:
        # Windows의 경우 winget 경로 추가 탐색
        winget_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages")
        if os.path.exists(winget_dir):
            for root, dirs, files in os.walk(winget_dir):
                if ngrok_filename in files:
                    ngrok_path = os.path.join(root, ngrok_filename)
                    print_color(f"🔎 winget 패키지에서 ngrok을 찾았습니다: {ngrok_path}", Colors.GREEN)
                    break

    if not ngrok_path:
        print_color("❌ ngrok 실행 파일을 찾을 수 없습니다. 프로젝트 루트 또는 bin 폴더에 ngrok을 배치하거나 설치해주세요.", Colors.RED)
        print_color("👉 다운로드 주소: https://ngrok.com/download", Colors.YELLOW)
        sys.exit(1)

    # 2. .env 파일 및 NGROK_AUTHTOKEN 로드
    env_file_path = os.path.join(script_dir, ".env")
    if not os.path.exists(env_file_path):
        with open(env_file_path, "w", encoding="utf-8") as f:
            f.write("")

    with open(env_file_path, "r", encoding="utf-8") as f:
        env_content = f.read()

    # NGROK_AUTHTOKEN 검사
    token_match = re.search(r'(?m)^NGROK_AUTHTOKEN=["\']?([^"\'\r\n]+)["\']?$', env_content)
    if not token_match:
        print_color("\n⚠️ [중요] ngrok은 보안상 가입자의 인증 토큰이 있어야만 사용할 수 있습니다!", Colors.RED)
        print("1. https://dashboard.ngrok.com/signup 에 접속하여 구글 계정 등으로 5초 만에 로그인/가입하세요.")
        print("2. https://dashboard.ngrok.com/get-started/your-authtoken 화면에 있는 긴 토큰을 복사하세요.")
        ngrok_token = input("👉 복사한 ngrok 토큰을 여기에 붙여넣기 하세요: ").strip()
        
        if ngrok_token:
            # ngrok config에 추가
            try:
                subprocess.run([ngrok_path, "config", "add-authtoken", ngrok_token], check=True)
                print_color("✅ ngrok 인증 토큰이 시스템에 등록되었습니다!", Colors.GREEN)
            except Exception as e:
                print_color(f"⚠️ 인증 토큰 등록 중 경고 발생 (수동 등록 권장): {e}", Colors.YELLOW)
            
            if env_content and not env_content.endswith("\n"):
                env_content += "\n"
            env_content += f'NGROK_AUTHTOKEN="{ngrok_token}"\n'
            with open(env_file_path, "w", encoding="utf-8") as f:
                f.write(env_content)
        else:
            print_color("❌ 토큰을 입력하지 않으시면 터널을 열 수 없습니다.", Colors.RED)
            sys.exit(1)

    # ngrok 실행
    print_color("🌐 ngrok을 백그라운드에서 실행하여 8080 포트(백엔드)를 터널링합니다...", Colors.GREEN)
    try:
        ngrok_proc = subprocess.Popen([ngrok_path, "http", "8080"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(ngrok_proc)
    except Exception as e:
        print_color(f"❌ ngrok 실행 실패: {e}", Colors.RED)
        sys.exit(1)

    print_color("⏳ 텔레그램용 HTTPS URL 발급을 기다리는 중...", Colors.YELLOW)
    ngrok_url = None
    for _ in range(15):
        time.sleep(2)
        try:
            req = urllib.request.Request("http://localhost:4040/api/tunnels")
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                for tunnel in data.get("tunnels", []):
                    if tunnel.get("public_url", "").startswith("https"):
                        ngrok_url = tunnel["public_url"]
                        break
            if ngrok_url:
                break
        except Exception:
            pass

    if not ngrok_url:
        print_color("❌ URL 발급 실패: ngrok이 켜졌는지 확인하세요.", Colors.RED)
        cleanup()

    print_color(f"✅ 터널 생성 완료: {ngrok_url}", Colors.GREEN)

    # 3. 필수 환경 변수 체크 및 입력 유도
    vars_to_check = ["TELEGRAM_BOT_TOKEN", "ADMIN_TELEGRAM_CHAT_ID", "TELEGRAM_WEBHOOK_SECRET"]
    
    for var in vars_to_check:
        var_match = re.search(rf'(?m)^{var}=["\']?([^"\'\r\n]+)["\']?$', env_content)
        if not var_match:
            inputValue = input(f"⚠️ [{var}] 값을 입력하세요: ").strip()
            if env_content and not env_content.endswith("\n"):
                env_content += "\n"
            env_content += f'{var}="{inputValue}"\n'

    # BASE_URL 업데이트
    base_url_match = re.search(r'(?m)^BASE_URL=.*$', env_content)
    if base_url_match:
        env_content = re.sub(r'(?m)^BASE_URL=.*$', f'BASE_URL="{ngrok_url}"', env_content)
    else:
        if env_content and not env_content.endswith("\n"):
            env_content += "\n"
        env_content += f'BASE_URL="{ngrok_url}"\n'
    
    with open(env_file_path, "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print_color(f"✅ 동적 URL({ngrok_url})을 환경변수(BASE_URL)에 주입했습니다.", Colors.GREEN)
    print("--------------------------------------------------------")

    # 4. 가상 환경 파이썬 탐색
    venv_python = os.path.join(script_dir, ".venv", "Scripts", "python.exe") if is_windows else os.path.join(script_dir, ".venv", "bin", "python")
    if not os.path.exists(venv_python):
        venv_python = sys.executable

    # 5. 프론트엔드 (Streamlit) 구동
    print_color("🎨 프론트엔드 화면(Streamlit)을 백그라운드에서 구동합니다...", Colors.MAGENTA)
    try:
        ui_proc = subprocess.Popen([venv_python, "-m", "streamlit", "run", "ui/app.py", "--server.port", "8501"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(ui_proc)
        print_color("✅ UI 구동 완료! (잠시 후 브라우저가 자동으로 열립니다)", Colors.GREEN)
    except Exception as e:
        print_color(f"⚠️ Streamlit 구동 중 오류 발생: {e}", Colors.YELLOW)

    print("--------------------------------------------------------")

    # 6. 백엔드 (uvicorn) 구동 (foreground blocking)
    print_color("🚀 소설싸개 백엔드 서버(uvicorn)를 구동합니다...", Colors.CYAN)
    print_color("🛑 모두 종료하시려면 이 창에서 [Ctrl+C] 를 누르세요.", Colors.GRAY)
    
    try:
        subprocess.run([venv_python, "-m", "uvicorn", "app.main:app", "--port", "8080", "--reload"])
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()

if __name__ == "__main__":
    main()
