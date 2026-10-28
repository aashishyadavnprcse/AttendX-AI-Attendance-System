"""
AttendX Notification Service — WhatsApp Dispatcher
Supports:
1. Twilio WhatsApp API (Official SDK)
2. Meta WhatsApp Cloud API (Graph API v19.0)
3. Sandbox / Mock Dispatcher (for automated testing & offline development)
"""

from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None

from notification_service.config import settings

try:
    from twilio.rest import Client as TwilioClient
except ImportError:
    TwilioClient = None


class WhatsAppNotifier:
    """
    Unified WhatsApp notification client for AttendX automated parent alerts.
    """

    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or settings.WHATSAPP_PROVIDER).lower()

        # Initialize Twilio Client if configured
        self.twilio_client = None
        if self.provider == "twilio" and settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            if TwilioClient is not None:
                self.twilio_client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            else:
                print("[WhatsAppNotifier] Warning: twilio package not installed.")

    @staticmethod
    def format_alert_message(
        parent_name: str,
        student_name: str,
        subject: str,
        date_str: str,
        consecutive_days: int = 3,
    ) -> str:
        """
        Formats a personalized, professional WhatsApp notification text.
        """
        greeting = f"Dear {parent_name}," if parent_name else "Dear Parent/Guardian,"
        return (
            f"🚨 *AttendX Official Academic Alert*\n\n"
            f"{greeting}\n\n"
            f"This is an automated attendance notice regarding your student *{student_name}*.\n\n"
            f"📋 *Notice Details:*\n"
            f"• *Status:* Unexcused Absence / Bunk Flagged\n"
            f"• *Consecutive Days Absent:* {consecutive_days} consecutive lecture days\n"
            f"• *Most Recent Subject:* {subject}\n"
            f"• *Incident Date:* {date_str}\n\n"
            f"Continuous attendance is mandatory for academic qualification. "
            f"Please review this with your student or contact the administration desk via the AttendX parent portal.\n\n"
            f"— *AttendX AI Academic Monitoring System*"
        )

    def send_absence_alert(
        self,
        parent_phone: str,
        parent_name: str,
        student_name: str,
        subject: str,
        date_str: str,
        consecutive_days: int = 3,
    ) -> Dict[str, Any]:
        """
        Dispatches personalized WhatsApp alert to parent phone number.
        """
        # Ensure recipient phone has WhatsApp prefix if Twilio
        clean_phone = parent_phone.strip()
        formatted_message = self.format_alert_message(
            parent_name=parent_name,
            student_name=student_name,
            subject=subject,
            date_str=date_str,
            consecutive_days=consecutive_days,
        )

        # -------------------------------------------------------------
        # 1. Twilio WhatsApp Dispatcher
        # -------------------------------------------------------------
        if self.provider == "twilio" and self.twilio_client is not None:
            to_number = f"whatsapp:{clean_phone}" if not clean_phone.startswith("whatsapp:") else clean_phone
            from_number = settings.TWILIO_WHATSAPP_FROM
            try:
                print(f"[WhatsAppNotifier] Sending Twilio WhatsApp to {to_number}...")
                message = self.twilio_client.messages.create(
                    body=formatted_message,
                    from_=from_number,
                    to=to_number,
                )
                return {
                    "success": True,
                    "provider": "twilio",
                    "message_sid": message.sid,
                    "status": message.status,
                    "recipient": to_number,
                }
            except Exception as e:
                print(f"[WhatsAppNotifier Error] Twilio dispatch failed: {e}")
                return {"success": False, "provider": "twilio", "error": str(e)}

        # -------------------------------------------------------------
        # 2. Meta WhatsApp Cloud API (Graph API)
        # -------------------------------------------------------------
        elif self.provider == "meta" and settings.META_WHATSAPP_TOKEN and settings.META_PHONE_NUMBER_ID:
            clean_digits = "".join(filter(str.isdigit, clean_phone))
            url = f"https://graph.facebook.com/v19.0/{settings.META_PHONE_NUMBER_ID}/messages"
            headers = {
                "Authorization": f"Bearer {settings.META_WHATSAPP_TOKEN}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": clean_digits,
                "type": "text",
                "text": {"preview_url": False, "body": formatted_message},
            }
            try:
                print(f"[WhatsAppNotifier] Sending Meta WhatsApp Cloud message to {clean_digits}...")
                resp = requests.post(url, json=payload, headers=headers, timeout=10.0)
                resp_data = resp.json()
                if resp.status_code in [200, 201]:
                    msg_id = resp_data.get("messages", [{}])[0].get("id")
                    return {
                        "success": True,
                        "provider": "meta",
                        "message_id": msg_id,
                        "recipient": clean_digits,
                    }
                else:
                    return {"success": False, "provider": "meta", "error": resp_data}
            except Exception as e:
                return {"success": False, "provider": "meta", "error": str(e)}

        # -------------------------------------------------------------
        # 3. Sandbox / Mock Simulation Mode (Default for Dev / Tests)
        # -------------------------------------------------------------
        else:
            print(f"\n[WhatsApp Mock Sandbox] =======================================")
            print(f" To: {clean_phone} (Parent: {parent_name or 'N/A'})")
            print(f" Dynamic Message Content:\n{formatted_message}")
            print(f"===============================================================\n")
            return {
                "success": True,
                "provider": "mock_sandbox",
                "message_sid": f"mock_msg_{student_name.lower().replace(' ', '_')}",
                "status": "delivered_mock",
                "recipient": clean_phone,
            }
