# AttendX Automated WhatsApp Notification Microservice

Automated parent alert microservice running daily background cron jobs via **APScheduler**, detecting students with 3+ consecutive unexcused absences or lecture bunks, and triggering personalized **WhatsApp alerts** via the **Twilio API** or **Meta WhatsApp Cloud API**.

---

## 🏗️ Architecture Overview

```
notification_service/
├── config.py              # Environment variable parser (.env loader)
├── whatsapp_client.py     # Dual-provider client: Twilio WhatsApp + Meta WhatsApp Cloud API
├── absence_detector.py    # Database query detecting 3+ consecutive absence/bunk days
├── scheduler.py           # APScheduler configuration (Daily cron at 17:00 / 5:00 PM)
├── worker.py              # Standalone daemon entrypoint & CLI manual runner
├── test_notification.py   # Test runner & mock sandbox verification
├── requirements.txt       # Dependencies (apscheduler, twilio, requests, sqlalchemy)
├── .env.example           # Environment template for Twilio & WhatsApp Cloud API
└── README.md              # Setup and deployment documentation
```

---

## ⏰ Cron Automation Logic

1. **Daily Execution Trigger**:
   - Runs daily after class hours (**17:00 / 5:00 PM**) via APScheduler's `CronTrigger(hour=17, minute=0)`.
2. **Detection Rule**:
   - Queries `AttendanceLog` records grouped by calendar date.
   - Identifies students who have status `ABSENT` or notes containing `BUNK_DETECTED` for **3 or more consecutive lecture dates**.
3. **Deduplication Engine**:
   - Inspects `last_parent_alert_at` on the `User` record to ensure parents receive at most **one alert per day**, preventing notification spam.

---

## 📱 Dynamic WhatsApp Message Template

Personalized template dynamically populating student, parent, and class session variables:

```text
🚨 *AttendX Official Academic Alert*

Dear {{ParentName}},

This is an automated attendance notice regarding your student *{{StudentName}}*.

📋 *Notice Details:*
• *Status:* Unexcused Absence / Bunk Flagged
• *Consecutive Days Absent:* {{ConsecutiveDays}} consecutive lecture days
• *Most Recent Subject:* {{SubjectName}}
• *Incident Date:* {{IncidentDate}}

Continuous attendance is mandatory for academic qualification. Please review this with your student or contact the administration desk via the AttendX parent portal.

— *AttendX AI Academic Monitoring System*
```

---

## ⚙️ Configuration (`.env`)

Copy `.env.example` to `.env` inside `notification_service/`:

### Option A: Twilio WhatsApp API
```env
WHATSAPP_PROVIDER="twilio"
TWILIO_ACCOUNT_SID="ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
TWILIO_AUTH_TOKEN="your_twilio_auth_token"
TWILIO_WHATSAPP_FROM="whatsapp:+14155238886"  # Twilio Sandbox or Approved Sender
```

### Option B: Meta WhatsApp Cloud API (Graph API)
```env
WHATSAPP_PROVIDER="meta"
META_WHATSAPP_TOKEN="EAAG..."
META_PHONE_NUMBER_ID="109283746501928"
META_TEMPLATE_NAME="attendx_consecutive_absence_alert"
```

---

## 🚀 Execution Guide

### 1. Install Dependencies
```bash
cd notification_service
pip install -r requirements.txt
```

### 2. Start the Daily Background Daemon
```bash
python worker.py
```

### 3. On-Demand / Immediate Manual Execution
```bash
# Execute the scan and dispatch alerts immediately
python worker.py --run-now

# Dry-run mode: scans database and previews dynamic messages without sending live WhatsApp messages
python worker.py --dry-run
```

### 4. Run Automated Test Verification
```bash
python test_notification.py
```
