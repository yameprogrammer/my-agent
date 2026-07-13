import os
import sys
import subprocess
import time
import shutil
import re
import socket
import requests
import webbrowser

# 터미널 색상 정의
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    GRAY = "\033[90m"
    END = "\033[0m"

def print_color(text, color):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    
    # 윈도우 환경(CP949) 인코딩 에러 방지
    try:
        print(f"{color}{text}{Colors.END}")
    except UnicodeEncodeError:
        try:
            print(f"{color}{text.encode('utf-8', errors='ignore').decode('cp949', errors='ignore')}{Colors.END}")
        except Exception:
            print(text)

processes = []

def cleanup():
    print_color("\n🛑 모든 로컬 테스트 서버를 정리하고 프로세스를 종료합니다...", Colors.YELLOW)
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    print_color("👋 정리 완료. 종료합니다.", Colors.GREEN)

def main():
    # 윈도우 인코딩 환경 설정
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    print_color("🚀 [로컬 개발 환경] 프로세스 구동 스크립트를 기동합니다...", Colors.CYAN)

    # 0. 데이터베이스 포트 가드 (Docker Desktop 미기동으로 인한 30초 대기 락 현상 예방)
    db_host = "127.0.0.1"
    db_port = 5432
    
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

    # 1. 환경 설정 로드
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_file_path = os.path.join(script_dir, ".env")
    if not os.path.exists(env_file_path):
        with open(env_file_path, "w", encoding="utf-8") as f:
            f.write("")

    with open(env_file_path, "r", encoding="utf-8") as f:
        env_content = f.read()

    # USE_NGROK 옵션 검사 (기본값 True)
    use_ngrok_match = re.search(r'(?m)^USE_NGROK=["\']?([^"\'\r\n]+)["\']?$', env_content)
    use_ngrok = True
    if use_ngrok_match:
        use_ngrok = use_ngrok_match.group(1).strip().lower() != "false"

    ngrok_url = None

    if use_ngrok:
        # OS별 ngrok 탐색
        is_windows = sys.platform.startswith('win')
        ngrok_filename = "ngrok.exe" if is_windows else "ngrok"
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
            winget_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages")
            if os.path.exists(winget_dir):
                for root, dirs, files in os.walk(winget_dir):
                    if ngrok_filename in files:
                        ngrok_path = os.path.join(root, ngrok_filename)
                        print_color(f"🔎 winget 패키지에서 ngrok을 찾았습니다: {ngrok_path}", Colors.GREEN)
                        break

        # ngrok을 못 찾았을 때 로컬 전용 모드로 우회 유도
        if not ngrok_path:
            print_color("❌ ngrok 실행 파일을 찾을 수 없습니다.", Colors.RED)
            print_color("💡 텔레그램 승인봇 알림 기능(외부 통신)을 쓰지 않으실 경우, 로컬 전용 모드로 구동할 수 있습니다.", Colors.YELLOW)
            choice = input("👉 로컬 전용 모드(외부 비공개)로 전환하여 계속 구동할까요? (Y/n): ").strip().lower()
            if choice == "" or choice == "y":
                use_ngrok = False
                print_color("🛡️ 로컬 전용 모드로 전환합니다 (외부 노출 안전 차단).", Colors.GREEN)
            else:
                print_color("👉 다운로드 주소: https://ngrok.com/download", Colors.YELLOW)
                sys.exit(1)

    if use_ngrok:
        # NGROK_AUTHTOKEN 검사
        token_match = re.search(r'(?m)^NGROK_AUTHTOKEN=["\']?([^"\'\r\n]+)["\']?$', env_content)
        if not token_match:
            print_color("\n⚠️ [중요] ngrok은 보안상 가입자의 인증 토큰이 있어야만 사용할 수 있습니다!", Colors.RED)
            print("1. https://dashboard.ngrok.com/signup 에 접속하여 구글 계정 등으로 5초 만에 로그인/가입하세요.")
            print("2. https://dashboard.ngrok.com/get-started/your-authtoken 화면에 있는 긴 토큰을 복사하세요.")
            ngrok_token = input("👉 복사한 ngrok 토큰을 여기에 붙여넣기 하세요: ").strip()
            
            if ngrok_token:
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
                print_color("💡 로컬 전용 모드로 실행하려면 .env 파일에 USE_NGROK=False 를 입력해 주세요.", Colors.YELLOW)
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
        for _ in range(10):
            time.sleep(1)
            try:
                res = requests.get("http://127.0.0.1:4040/api/tunnels")
                if res.status_code == 200:
                    tunnels = res.json().get("tunnels", [])
                    for tunnel in tunnels:
                        if tunnel.get("proto") == "https":
                            ngrok_url = tunnel["public_url"]
                            break
                    if ngrok_url:
                        break
            except Exception:
                pass
        
        if not ngrok_url:
            print_color("❌ URL 발급 실패: ngrok이 켜졌는지 확인하세요.", Colors.RED)
            cleanup()
            sys.exit(1)
        print_color(f"✅ 터널 생성 완료: {ngrok_url}", Colors.GREEN)
    else:
        # 로컬 전용 모드
        ngrok_url = "http://localhost:8080"
        print_color("🛡️ 로컬 전용 모드로 구동을 시작합니다 (외부 터널 없음).", Colors.GREEN)

    # 3. 필수 환경 변수 체크 및 입력 유도 (텔레그램 사용 시에만 필수 체크)
    if use_ngrok:
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
    
    print_color(f"✅ 구동 URL({ngrok_url})을 환경변수(BASE_URL)에 주입했습니다.", Colors.GREEN)
    print("--------------------------------------------------------")

    # 4. 가상 환경 파이썬 탐색
    venv_python = os.path.join(script_dir, ".venv", "Scripts", "python.exe") if sys.platform.startswith('win') else os.path.join(script_dir, ".venv", "bin", "python")
    if not os.path.exists(venv_python):
        venv_python = sys.executable

    # 5. 프론트엔드 (Vite SPA) 브레드크럼 및 자동 브라우저 오픈
    print_color("🎨 프론트엔드(Vite SPA)가 백엔드 통합 웹서버(8080 포트)로 구동됩니다...", Colors.MAGENTA)
    try:
        # uvicorn 기동 전에 브라우저를 띄우기 위해 약간의 딜레이 후 백그라운드 스레드나 프로세스로 실행하거나 단순 브라우저 팝업
        # 8080 포트 접속 주소를 기본 브라우저에서 열기
        open_url = ngrok_url if ngrok_url else "http://localhost:8080"
        print_color(f"🔗 접속 주소: {open_url}", Colors.GREEN)
        
        # uvicorn 서버가 완전히 뜰 때까지 백그라운드 딜레이 후 브라우저 오픈
        def open_browser():
            time.sleep(2)
            webbrowser.open(open_url)
            
        import threading
        threading.Thread(target=open_browser, daemon=True).start()
        print_color("✅ 브라우저 기동 알림 설정 완료! (서버 시작 후 자동 오픈)", Colors.GREEN)
    except Exception as e:
        print_color(f"⚠️ 브라우저 자동 기동 중 오류 발생: {e}", Colors.YELLOW)

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
