"""
이메일 발송 서비스 (비동기 래퍼)

Python 표준 라이브러리 smtplib를 asyncio.get_event_loop().run_in_executor()로 감싸
비동기 패턴을 유지하면서 이메일을 발송합니다.
외부 라이브러리(aiosmtplib) 없이 동작하므로 추가 의존성이 없습니다.
"""

import asyncio
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import partial
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_email_sync(
    to_address: str,
    subject: str,
    html_body: str,
) -> None:
    """
    smtplib를 사용하는 동기 이메일 발송 함수.
    run_in_executor를 통해 스레드 풀에서 실행됩니다.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP 설정(SMTP_USER / SMTP_PASSWORD)이 없어 이메일을 발송하지 않습니다.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to_address

    # HTML 본문 첨부
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to_address, msg.as_string())
        logger.info("이메일 발송 성공 → %s | 제목: %s", to_address, subject)
    except smtplib.SMTPException as e:
        logger.error("이메일 발송 실패: %s", e)
        raise


async def send_email(
    to_address: str,
    subject: str,
    html_body: str,
) -> None:
    """
    비동기 이메일 발송 진입점.
    smtplib 호출을 스레드 풀로 오프로드하여 이벤트 루프를 블로킹하지 않습니다.
    """
    loop = asyncio.get_event_loop()
    send_func = partial(_send_email_sync, to_address, subject, html_body)
    await loop.run_in_executor(None, send_func)


# ---------------------------------------------------------------------------
# 이메일 템플릿 함수들
# ---------------------------------------------------------------------------

async def send_registration_request_to_admin(
    username: str,
    user_email: Optional[str],
    user_id: int,
) -> None:
    """
    신규 가입 요청이 들어왔을 때 관리자에게 승인 요청 이메일을 발송합니다.
    이메일 본문에 원클릭 승인 링크가 포함됩니다.
    """
    if not settings.ADMIN_EMAIL:
        logger.warning("ADMIN_EMAIL이 설정되지 않아 관리자 알림 이메일을 발송하지 않습니다.")
        return

    approve_url = f"{settings.BASE_URL}/auth/approve/{user_id}"
    subject = f"[AI 소설 작가] 신규 회원가입 승인 요청 — {username}"

    html_body = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head><meta charset="UTF-8"></head>
    <body style="font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif; background:#f4f6f8; margin:0; padding:0;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8; padding:40px 0;">
        <tr><td align="center">
          <table width="560" cellpadding="0" cellspacing="0"
                 style="background:#ffffff; border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.08); overflow:hidden;">
            <!-- 헤더 -->
            <tr>
              <td style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
                         padding:32px 40px; text-align:center;">
                <h1 style="color:#ffffff; margin:0; font-size:22px; font-weight:700; letter-spacing:-0.5px;">
                  📝 AI 소설 작가 시스템
                </h1>
                <p style="color:rgba(255,255,255,0.85); margin:8px 0 0; font-size:14px;">
                  신규 회원가입 승인 요청
                </p>
              </td>
            </tr>
            <!-- 본문 -->
            <tr>
              <td style="padding:40px;">
                <p style="color:#374151; font-size:16px; margin:0 0 24px; line-height:1.6;">
                  새로운 사용자가 회원가입을 요청했습니다. 아래 정보를 확인하고 승인 여부를 결정해 주세요.
                </p>

                <!-- 사용자 정보 박스 -->
                <table width="100%" cellpadding="0" cellspacing="0"
                       style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; margin-bottom:32px;">
                  <tr>
                    <td style="padding:20px 24px;">
                      <table width="100%" cellpadding="6" cellspacing="0">
                        <tr>
                          <td style="color:#6b7280; font-size:13px; width:110px;">사용자명</td>
                          <td style="color:#111827; font-size:14px; font-weight:600;">{username}</td>
                        </tr>
                        <tr>
                          <td style="color:#6b7280; font-size:13px;">이메일</td>
                          <td style="color:#111827; font-size:14px;">{user_email or "미입력"}</td>
                        </tr>
                        <tr>
                          <td style="color:#6b7280; font-size:13px;">사용자 ID</td>
                          <td style="color:#111827; font-size:14px;">#{user_id}</td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>

                <!-- 승인 버튼 -->
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td align="center">
                      <a href="{approve_url}"
                         style="display:inline-block; background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
                                color:#ffffff; text-decoration:none; font-size:16px; font-weight:600;
                                padding:14px 48px; border-radius:8px; letter-spacing:0.3px;">
                        ✅ 회원가입 승인하기
                      </a>
                    </td>
                  </tr>
                </table>

                <p style="color:#9ca3af; font-size:12px; margin:24px 0 0; text-align:center; line-height:1.6;">
                  위 버튼을 클릭하면 해당 계정이 즉시 활성화됩니다.<br>
                  본인이 요청하지 않은 경우 이 이메일을 무시하세요.
                </p>
              </td>
            </tr>
            <!-- 푸터 -->
            <tr>
              <td style="background:#f9fafb; padding:20px 40px; border-top:1px solid #e5e7eb; text-align:center;">
                <p style="color:#9ca3af; font-size:12px; margin:0;">
                  AI 소설 작가 시스템 · 자동 발송 이메일
                </p>
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """

    await send_email(
        to_address=settings.ADMIN_EMAIL,
        subject=subject,
        html_body=html_body,
    )


async def send_approval_notification_to_user(
    username: str,
    user_email: str,
) -> None:
    """
    관리자 승인 완료 후 해당 사용자에게 활성화 완료 이메일을 발송합니다.
    """
    subject = "[AI 소설 작가] 회원가입이 승인되었습니다 🎉"

    html_body = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head><meta charset="UTF-8"></head>
    <body style="font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif; background:#f4f6f8; margin:0; padding:0;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8; padding:40px 0;">
        <tr><td align="center">
          <table width="560" cellpadding="0" cellspacing="0"
                 style="background:#ffffff; border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.08); overflow:hidden;">
            <tr>
              <td style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
                         padding:32px 40px; text-align:center;">
                <h1 style="color:#ffffff; margin:0; font-size:22px; font-weight:700; letter-spacing:-0.5px;">
                  📝 AI 소설 작가 시스템
                </h1>
                <p style="color:rgba(255,255,255,0.85); margin:8px 0 0; font-size:14px;">
                  회원가입 승인 완료
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:40px;">
                <p style="color:#374151; font-size:16px; margin:0 0 16px; line-height:1.6;">
                  안녕하세요, <strong>{username}</strong>님!
                </p>
                <p style="color:#374151; font-size:16px; margin:0 0 32px; line-height:1.6;">
                  회원가입 요청이 관리자에 의해 <strong style="color:#667eea;">승인</strong>되었습니다.
                  이제 서비스에 로그인하여 AI와 함께 소설을 집필해 보세요! 🚀
                </p>
                <table width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td align="center">
                      <a href="{settings.BASE_URL}"
                         style="display:inline-block; background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
                                color:#ffffff; text-decoration:none; font-size:16px; font-weight:600;
                                padding:14px 48px; border-radius:8px;">
                        🖊️ 지금 시작하기
                      </a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="background:#f9fafb; padding:20px 40px; border-top:1px solid #e5e7eb; text-align:center;">
                <p style="color:#9ca3af; font-size:12px; margin:0;">
                  AI 소설 작가 시스템 · 자동 발송 이메일
                </p>
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """

    await send_email(
        to_address=user_email,
        subject=subject,
        html_body=html_body,
    )
