# WhatsApp Reminder Service - Visual Architecture & Data Flow

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLINIC WEBSITE                                   │
│  (Your existing Django application)                                     │
└─────────────────┬───────────────────────────────────────────────────────┘
                  │
                  │ Creates/Updates
                  ▼
        ┌─────────────────────┐
        │  FollowUp Model     │
        │                     │
        │ - patient           │
        │ - scheduled_date    │
        │ - status            │
        │ - reminder_sent ←── ← Key field!
        └─────────────────────┘
                  ▲
                  │ Polls every 15 minutes
                  │
┌─────────────────┴───────────────────────────────────────────────────────┐
│                    REMINDER SERVICE                                      │
│                 (New background task)                                    │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Django App Ready (apps.py)                                  │      │
│  │  └─> Start APScheduler                                       │      │
│  └──────────────────┬───────────────────────────────────────────┘      │
│                     │                                                   │
│  ┌──────────────────▼───────────────────────────────────────────┐      │
│  │  APScheduler (Background Thread)                             │      │
│  │  Runs every 15 minutes (configurable)                        │      │
│  │  └─> run_reminder_scheduler()                                │      │
│  └──────────────────┬───────────────────────────────────────────┘      │
│                     │                                                   │
│  ┌──────────────────▼───────────────────────────────────────────┐      │
│  │  check_and_send_followup_reminders() [HIGH-LEVEL]            │      │
│  │                                                              │      │
│  │  1. Query FollowUp where:                                   │      │
│  │     - status = 'scheduled'                                  │      │
│  │     - scheduled_date >= NOW                                 │      │
│  │     - scheduled_date <= NOW + 24 hours                      │      │
│  │     - reminder_sent = False                                 │      │
│  │                                                              │      │
│  │  2. For each follow-up (batch_size limit):                  │      │
│  │     - Get patient & phone number                            │      │
│  │     - Create personalized message                           │      │
│  │     - Call send_whatsapp_reminder()                         │      │
│  │                                                              │      │
│  │  3. If success:                                             │      │
│  │     - Set reminder_sent = True                              │      │
│  │     - Save to database                                      │      │
│  │                                                              │      │
│  │  4. Return statistics                                       │      │
│  └──────────────────┬───────────────────────────────────────────┘      │
│                     │                                                   │
│  ┌──────────────────▼───────────────────────────────────────────┐      │
│  │  send_whatsapp_reminder() [LOW-LEVEL]                        │      │
│  │                                                              │      │
│  │  1. Validate credentials:                                   │      │
│  │     - WHATSAPP_TOKEN (from .env)                            │      │
│  │     - WHATSAPP_PHONE_NUMBER_ID (from .env)                  │      │
│  │                                                              │      │
│  │  2. Validate phone number format                            │      │
│  │                                                              │      │
│  │  3. Build JSON payload:                                     │      │
│  │     {                                                       │      │
│  │       "messaging_product": "whatsapp",                      │      │
│  │       "to": "91XXXXXXXXXX",                                 │      │
│  │       "type": "text",                                       │      │
│  │       "text": {"body": "reminder_message"}                  │      │
│  │     }                                                       │      │
│  │                                                              │      │
│  │  4. POST to WhatsApp Cloud API                              │      │
│  │                                                              │      │
│  │  5. Handle response & return result                         │      │
│  └──────────────────┬───────────────────────────────────────────┘      │
└─────────────────────┼──────────────────────────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────────┐
        │  WhatsApp Cloud API              │
        │  (Facebook/Meta)                 │
        └──────────────┬────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────┐
        │  Patient Receives WhatsApp        │
        │  Message on their phone           │
        └──────────────────────────────────┘
```

---

## 📊 Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 1: Create Follow-up (Doctor/Receptionist)                      │
└──────────────────────────────────────────────────────────────────────┘
         │
         │ Creates appointment for tomorrow at 2 PM
         ▼
    ┌─────────────────────────────┐
    │ FollowUp Table              │
    ├─────────────────────────────┤
    │ ID: 1                       │
    │ patient_id: 42              │
    │ scheduled_date: 2026-01-12  │  ← Tomorrow
    │                 14:00       │
    │ status: 'scheduled'         │
    │ reminder_sent: False ←────┐ │  ← Not sent yet!
    └────────────────────────────┘ │
                                    │
                                    │
┌──────────────────────────────────────────────────────────────────────┐
│ STEP 2: Time Passes... (13 hours later, at 1 AM)                    │
│ System checks for reminders every 15 minutes                         │
└──────────────────────────────────────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────┐
    │ Now = 2026-01-12, 01:00     │
    │ Check: 24h from now?        │
    │ 01:00 + 24h = 2026-01-13    │
    │ scheduled = 2026-01-12 14:00│
    │ YES! Within 24 hours ✓      │
    └─────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────┐
    │ Is reminder_sent = False?   │
    │ YES ✓                       │
    │ Status = 'scheduled'?       │
    │ YES ✓                       │
    └─────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────┐
    │ Get Patient Details              │
    ├──────────────────────────────────┤
    │ Name: John Doe                   │
    │ Phone: 9876543210                │
    │ Doctor: Dr. Ami Bhatt            │
    │ Formatted: 919876543210          │
    └──────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────┐
    │ Create Message                   │
    ├──────────────────────────────────┤
    │ "Dear John Doe,                  │
    │                                  │
    │  📅 Your follow-up is scheduled: │
    │  🕐 12 Jan 2026 at 02:00 PM     │
    │  👨‍⚕️ Dr. Ami Bhatt                │
    │                                  │
    │  Please arrive on time."         │
    └──────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────┐
    │ Send to WhatsApp API             │
    │ POST /v21.0/xxx/messages         │
    │ with Bearer token                │
    │ to: 919876543210                 │
    │ text: "Dear John Doe,..."        │
    └──────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────┐
    │ WhatsApp API Response            │
    ├──────────────────────────────────┤
    │ Status: 200 OK                   │
    │ Message ID: wamid.abc123         │
    └──────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────┐
    │ Update Database                  │
    │ SET reminder_sent = True         │
    │ WHERE id = 1                     │
    └──────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────┐
    │ FollowUp Table (Updated)         │
    ├──────────────────────────────────┤
    │ ID: 1                            │
    │ patient_id: 42                   │
    │ scheduled_date: 2026-01-12       │
    │                 14:00            │
    │ status: 'scheduled'              │
    │ reminder_sent: True ✓ ←── UPDATED!
    └──────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────┐
    │ Patient's Phone (WhatsApp)       │
    ├──────────────────────────────────┤
    │ 📱 Message received!             │
    │                                  │
    │ "Dear John Doe,                  │
    │  📅 Your follow-up is scheduled: │
    │  🕐 12 Jan 2026 at 02:00 PM     │
    │  👨‍⚕️ Dr. Ami Bhatt"               │
    └──────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ STEP 3: Next Check (15 minutes later)                               │
│ System checks again...                                               │
└──────────────────────────────────────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────────────────┐
    │ Check: reminder_sent = False?    │
    │ NO! It's True ✗                  │
    │ Skip this follow-up               │
    │ Don't send again!                │
    └──────────────────────────────────┘
```

---

## 🔄 Processing Flow with Filtering

```
START (Every 15 minutes)
  │
  ├─> Get current time: NOW
  │
  ├─> Calculate time window:
  │   END = NOW + 24 hours
  │
  ├─> Query database for:
  │   ┌──────────────────────────────────┐
  │   │ SELECT * FROM followups WHERE    │
  │   │                                  │
  │   │ status = 'scheduled'  ←──────────┤── Only active
  │   │ AND                              │
  │   │ scheduled_date >= NOW ←──────────┤── Not passed
  │   │ AND                              │
  │   │ scheduled_date <= NOW + 24h ←───┤── Within 24h
  │   │ AND                              │
  │   │ reminder_sent = False ←──────────┤── Not sent yet
  │   │                                  │
  │   │ LIMIT batch_size                 │
  │   └──────────────────────────────────┘
  │
  ├─> For each follow-up:
  │   │
  │   ├─> VALIDATE
  │   │   ├─> Patient exists?
  │   │   ├─> Phone number valid?
  │   │   └─> Continue if OK, skip if error
  │   │
  │   ├─> FORMAT
  │   │   ├─> Phone: country_code + phone_no
  │   │   └─> Message: personalized text
  │   │
  │   ├─> SEND
  │   │   ├─> Call send_whatsapp_reminder()
  │   │   ├─> Wait for API response
  │   │   └─> Get result (success/failure)
  │   │
  │   └─> UPDATE DATABASE
  │       ├─> If success: reminder_sent = True
  │       ├─> Save to database
  │       └─> Log the action
  │
  ├─> RETURN STATISTICS
  │   ├─> total_processed = 5
  │   ├─> reminders_sent = 4
  │   ├─> reminders_failed = 1
  │   └─> errors = [...]
  │
  └─> WAIT 15 minutes
      └─> Repeat
```

---

## 💾 Database Schema Relationship

```
┌─────────────────────────────────┐
│ Patient Table                   │
├─────────────────────────────────┤
│ case_no (PK)    │ 42            │
│ name            │ John Doe      │
│ phone_no        │ 9876543210    │
│ doctor          │ dr_1          │
│ address         │ ...           │
└────────┬────────────────────────┘
         │ Has many
         │ (Foreign Key)
         │
         ▼
┌─────────────────────────────────┐
│ FollowUp Table                  │
├─────────────────────────────────┤
│ id (PK)         │ 1             │
│ patient_id (FK) │ 42 ──────┐    │
│ scheduled_date  │ 2026-01..│ Points back
│ status          │ scheduled│ to Patient
│ reminder_sent ◄─┤ False    │
│ created_at      │ 2026-01..│
│ notes           │ ...      │
└────────┬────────────────────────┘
         │
         │ reminder_service checks here!
         │
     ┌───┴───────────────────────────┐
     │                               │
     └───> reminder_sent field       │
         - If False: Check for       │
           reminders to send         │
         - If True: Skip (already    │
           sent)                     │
```

---

## 📱 WhatsApp API Integration

```
YOUR SYSTEM                    WHATSAPP CLOUD API
     │                                │
     │   1. Validate Credentials     │
     │   ─────────────────────────>  │
     │       Token                   │
     │       Phone ID                │
     │                               │
     │   2. Build Message            │
     │   {                           │
     │     "to": "919876543210",     │
     │     "type": "text",           │
     │     "text": {                 │
     │       "body": "Hi John..."    │
     │     }                         │
     │   }                           │
     │                               │
     │   3. POST /messages           │
     │   ─────────────────────────>  │
     │   (with Bearer token)         │
     │                               │
     │                      Process  │
     │                      & Queue  │
     │   4. Response                 │
     │   <─────────────────────────  │
     │   {                           │
     │     "messages": [{            │
     │       "id": "wamid.xxx"       │
     │     }],                       │
     │     "contacts": [{            │
     │       "input": "919876..."    │
     │       "wa_id": "919876..."    │
     │     }]                        │
     │   }                           │
     │                               │
     │                      Send to  │
     │                      Phone    │
     │                               │
     │                         Patient
     │                         receives
     │                         WhatsApp!
```

---

## ⏲️ Timeline Example

```
TODAY (Jan 11, 2026)
│
├─ 12:00 PM  │ Reminder service starts (background)
├─ 12:15 PM  │ Check 1: No follow-ups in 24h window
├─ 12:30 PM  │ Check 2: No follow-ups in 24h window
├─ 12:45 PM  │ Check 3: No follow-ups in 24h window
│
└─ 01:00 PM  │ ⚠️ Follow-up created!
             │ scheduled_date = Jan 12, 2 PM
             │ (23 hours from now)
             │
TONIGHT
│
└─ 01:00 AM  │ Check 50: Follow-up within 24h!
             │ Send reminder ✓
             │ reminder_sent = True
             │
             │ Patient gets WhatsApp message
             │
TOMORROW (Jan 12, 2026)
│
├─ 08:00 AM  │ Check: reminder_sent = True, skip
├─ 08:15 AM  │ Check: reminder_sent = True, skip
├─ 08:30 AM  │ Check: reminder_sent = True, skip
│
└─ 02:00 PM  │ Patient arrives for appointment ✓
```

---

## 🎯 Key Decision Points

```
For each follow-up:

  1. Check: status = 'scheduled'?
     NO  → Skip ✗
     YES → Continue ✓
  
  2. Check: scheduled_date > NOW?
     NO  → Skip (appointment passed) ✗
     YES → Continue ✓
  
  3. Check: scheduled_date <= NOW + 24h?
     NO  → Skip (not yet within 24h) ✗
     YES → Continue ✓
  
  4. Check: reminder_sent = False?
     NO  → Skip (already sent) ✗
     YES → Continue ✓
  
  5. Check: Phone number valid?
     NO  → Log error, skip ✗
     YES → Continue ✓
  
  6. Send WhatsApp message
     Failure → Log error, continue
     Success → Set reminder_sent = True, continue ✓
  
  7. Next follow-up...
```

---

This visual documentation helps understand how the entire system works together!
