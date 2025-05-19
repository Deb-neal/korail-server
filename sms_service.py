from solapi import SolapiMessageService
from solapi.model import RequestMessage
import os
from dotenv import load_dotenv

# Load environment variables (to ensure they're loaded if this module is used directly)
load_dotenv()

def send_sms(to_phone: str, text: str):
    try:
        # Get credentials from environment variables
        api_key = os.getenv("SMS_API_KEY")
        api_secret = os.getenv("SMS_API_SECRET")
        sender = os.getenv("SMS_SENDER")

        # Solapi 서비스 초기화
        message_service = SolapiMessageService(api_key=api_key, api_secret=api_secret)

        # 메시지 구성
        message = RequestMessage(
            from_=sender,
            to=to_phone,
            text=text
        )

        # 전송
        response = message_service.send(message)

        # 로그 출력
        print("✅ 메시지 발송 성공!")
        print(f"📦 Group ID: {response.group_info.group_id}")
        print(f"📨 요청한 메시지 수: {response.group_info.count.total}")
        print(f"✅ 성공 수: {response.group_info.count.registered_success}")
        print(f"❌ 실패 수: {response.group_info.count.registered_failed}")

        return {
            "success": True,
            "group_id": response.group_info.group_id,
            "sent_count": response.group_info.count.registered_success
        }

    except Exception as e:
        print(f"❌ 메시지 발송 실패: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }