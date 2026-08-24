# CareCompass System Design

## Overview

CareCompass is a Django-based healthcare appointment and follow-up platform with separate patient, doctor, and administrator workflows. The system uses Django templates for the frontend, Django views and JSON endpoints for the backend API, SQLite for persistence, and role-based access through a Profile model linked to Django’s User model.

Patients search doctors by specialization, submit symptoms, book appointments, reschedule, cancel, and view care plans. Doctors receive a concise pre-visit brief, complete visits, submit prescriptions, and configure medication reminders. Administrators manage doctor profiles and leave dates.

## Double-Booking Prevention

Appointment conflicts are prevented at two levels.

First, the Appointment model has a database-level unique constraint on
`(doctor, start_at)`. This is the final authority: two appointments cannot exist for the same doctor and exact start time, even when requests arrive at the same time.

Second, the booking and rescheduling views use `transaction.atomic()`. The appointment write is treated as a single transaction. If two patients attempt to reserve the same slot simultaneously, one transaction succeeds while the
other raises an IntegrityError. The application catches that error and shows a clear “slot unavailable” message instead of creating duplicate bookings.

The end time is calculated from the selected doctor’s configured slot duration.
This keeps appointment durations consistent with each doctor’s schedule.

## Slot Hold Strategy

The system contains a SlotHold model with doctor, patient, start time, and expiry time fields. It is designed for a future multi-step booking flow where a patient can temporarily reserve a slot while completing symptom intake or payment.

A production implementation creates a hold with a short expiry, such as five minutes, and applies a unique constraint on `(doctor, start_at)`. The final booking transaction converts a valid hold into a confirmed appointment. Expired holds are removed by a background worker. The current MVP uses direct transactional confirmation because the booking process is short, while keeping the SlotHold schema ready for extension.

## Doctor Leave Conflict Handling

When an administrator records a leave date, CareCompass checks all confirmed appointments for the selected doctor and date. Each affected appointment is changed from `CONFIRMED` to `ACTION_REQUIRED`.

The system creates a `LEAVE_CONFLICT` NotificationJob for every affected
appointment. The patient can then reschedule or cancel through the Patient Portal. Completed and cancelled appointments are not changed, because they no longer need scheduling action. This design preserves the appointment history and avoids silently deleting patient data.

## Notifications and Failure Handling

Notifications are not sent directly inside the booking request. Instead, the application first creates a NotificationJob record containing job type, appointment reference, payload, delivery status, attempt count, error message, and next retry time.

A separate Django management command runs as a background worker. It processes pending jobs for booking confirmations, reschedules, cancellations, leave conflicts, post-visit summaries, and medication reminders. Successful jobs are marked `SENT`. Failed jobs are marked `FAILED`, store the error, and receive a future retry time. This prevents temporary email or Calendar failures from breaking a valid appointment.

In demo mode, email is printed in the terminal. The same queue structure can use SMTP, SendGrid, or Mailgun in production.

## LLM and Calendar Reliability

The LLM service generates structured pre-visit and post-visit JSON summaries.
If the OpenAI API is unavailable, missing credentials, or returns invalid
output, the system stores a safe fallback summary. Appointment booking and visit completion continue without interruption.

Google Calendar operations are isolated in a Calendar service. Booking creates an event, rescheduling updates it, and cancellation deletes it. Calendar errors are caught and recorded as retryable jobs, so Calendar outages never invalidate an appointment. Demo mode logs the intended Calendar action without requiring Google credentials.