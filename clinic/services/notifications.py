from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from clinic.models import NotificationJob
from clinic.models import MedicationReminder


def send_notification(job):
    appointment = job.appointment

    if not appointment:
        raise ValueError("This notification has no appointment.")

    patient_email = appointment.patient.email
    doctor_email = appointment.doctor.user.email

    if job.job_type == "BOOKING_CONFIRMATION":
        subject = "CareCompass: Appointment confirmed"
        message = f"""
Your appointment is confirmed.

Doctor: Dr. {appointment.doctor.user.get_full_name()}
Date and time: {appointment.start_at}
Status: {appointment.status}
"""

    elif job.job_type == "MEDICATION_REMINDER":
        subject = "CareCompass: Medication reminder"
        message = f"""
Medication reminder

Medicine: {job.payload.get("medicine_name")}
Frequency: {job.payload.get("frequency")}

Please follow the schedule provided by your doctor.
"""
        # Medication reminders go only to the patient.
        doctor_email = None

    elif job.job_type == "POST_VISIT_SUMMARY":
        subject = "CareCompass: Your post-visit care plan"
        message = f"""
Your doctor has completed your visit.

Please log in to CareCompass to view your patient-friendly care plan,
medication schedule, and follow-up instructions.
"""
    elif job.job_type == "RESCHEDULED":
        subject = "CareCompass: Appointment rescheduled"
        message = f"""
Your appointment has been rescheduled.

Doctor: Dr. {appointment.doctor.user.get_full_name()}
New date and time: {appointment.start_at}

Please log in to CareCompass to review the updated appointment.
"""
    
    elif job.job_type == "CANCELLATION":
        subject = "CareCompass: Appointment cancelled"
        message = f"""
Your appointment has been cancelled.

Doctor: Dr. {appointment.doctor.user.get_full_name()}
Date and time: {appointment.start_at}

Please log in to CareCompass if you need to book another appointment.
"""

    elif job.job_type == "LEAVE_CONFLICT":
        subject = "CareCompass: Appointment requires rescheduling"
        message = f"""
Your doctor is unavailable on the date of your appointment.

Your appointment has been marked Action Required.
Please log in to CareCompass and choose a new slot.
"""

    else:
        subject = "CareCompass notification"
        message = "You have a new update in CareCompass."

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[
            email for email in [patient_email, doctor_email] if email
        ],
        fail_silently=False
    )


def process_pending_jobs():
    jobs = NotificationJob.objects.filter(
        status__in=["PENDING", "FAILED"],
        next_retry_at__lte=timezone.now()
    ).order_by("id")

    for job in jobs:
        try:
            send_notification(job)

            job.status = "SENT"
            job.attempts += 1
            job.last_error = ""
            job.save()

        except Exception as error:
            job.status = "FAILED"
            job.attempts += 1
            job.last_error = str(error)

            # Retry after five minutes.
            job.next_retry_at = timezone.now() + timedelta(minutes=5)
            job.save()

def queue_due_medication_reminders():
    now = timezone.localtime()

    reminders = MedicationReminder.objects.filter(
        active=True,
        reminder_time__hour=now.hour,
        reminder_time__minute=now.minute
    )

    for reminder in reminders:
        already_queued_today = NotificationJob.objects.filter(
            appointment=reminder.appointment,
            job_type="MEDICATION_REMINDER",
            payload__reminder_id=reminder.id,
            created_at__date=now.date()
        ).exists()

        if not already_queued_today:
            NotificationJob.objects.create(
                appointment=reminder.appointment,
                job_type="MEDICATION_REMINDER",
                payload={
                    "reminder_id": reminder.id,
                    "medicine_name": reminder.medicine_name,
                    "frequency": reminder.frequency
                }
            )