import asyncio
import os
import sys
import requests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlmodel import select
from app.core.database import get_async_session
from app.models import Project
from app.core.crypto import decrypt_api_key
from app.core.config import settings

async def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    print("🔎 데이터베이스에서 프로젝트 API 키를 조회하고 있습니다...")
    async for session in get_async_session():
        stmt = select(Project).where(Project.llm_provider == "google")
        projects = (await session.execute(stmt)).scalars().all()
        if not projects:
            print("⚠️ google 제공자를 사용하는 프로젝트를 찾을 수 없습니다. 모든 프로젝트를 조회합니다.")
            stmt = select(Project)
            projects = (await session.execute(stmt)).scalars().all()

        if not projects:
            print("❌ 등록된 프로젝트가 없습니다.")
            return

        for p in projects:
            print(f"\n========================================")
            print(f"프로젝트: {p.title} (ID: {p.id})")
            print(f"설정된 모델: {p.llm_model}")
            
            # API 키 결정
            raw_key = p.api_key_override
            decrypted_key = decrypt_api_key(raw_key) if raw_key else None
            
            # 만약 개별 에이전트 키가 있다면 그것도 확인
            plotter_key = decrypt_api_key(p.plotter_api_key) if p.plotter_api_key else None
            
            api_key = plotter_key or decrypted_key or settings.GOOGLE_API_KEY
            
            if not api_key:
                print("❌ API 키가 설정되어 있지 않습니다.")
                continue
                
            print(f"🔑 API Key 감지됨 (길이: {len(api_key)}, 시작: {api_key[:6]}...)")
            
            # Google API 호출하여 모델 리스트 조회
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            try:
                res = requests.get(url)
                if res.status_code == 200:
                    data = res.json()
                    models = data.get("models", [])
                    print(f"✅ 사용 가능한 모델 리스트 ({len(models)}개 발견):")
                    for m in models:
                        name = m.get("name", "").replace("models/", "")
                        methods = m.get("supportedGenerationMethods", [])
                        if "generateContent" in methods:
                            print(f"  - {name} (generateContent 지원)")
                else:
                    print(f"❌ Google API 호출 실패 (HTTP {res.status_code}):")
                    print(res.text)
            except Exception as e:
                print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    # OS 환경 설정
    os.environ["TESTING"] = "True"  # DB 풀 기동 방지용
    asyncio.run(main())
