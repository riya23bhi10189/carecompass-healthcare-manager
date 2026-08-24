from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    ROLE_CHOICES = [
        ("PATIENT", "Patient"),
        ("DOCTOR", "Doctor"),
        ("ADMIN", "Admin"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default="PATIENT"
    )

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=100)
    working_start = models.TimeField(default="09:00")
    working_end = models.TimeField(default="17:00")
    slot_duration = models.PositiveIntegerField(default=30)

    def __str__(self):
        full_name = self.user.get_full_name()
        return f"Dr. {full_name or self.user.username}"


class DoctorLeave(models.Model):
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    leave_date = models.DateField()
    reason = models.CharField(max_length=250, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "leave_date"],
                name="unique_doctor_leave_date"
            )
        ]

    def __str__(self):
        return f"{self.doctor} — {self.leave_date}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ("CONFIRMED", "Confirmed"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
        ("ACTION_REQUIRED", "Action Required"),
    ]

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="patient_appointments"
    )

    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name="appointments"
    )

    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    symptoms = models.TextField()

    urgency = models.CharField(max_length=10, default="MEDIUM")
    pre_visit_summary = models.JSONField(null=True, blank=True)

    doctor_notes = models.TextField(blank=True)
    prescription = models.TextField(blank=True)
    post_visit_summary = models.JSONField(null=True, blank=True)

    calendar_event_id = models.CharField(max_length=200, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="CONFIRMED"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "start_at"],
                name="prevent_doctor_double_booking"
            )
        ]

    def __str__(self):
        return f"{self.patient.username} with {self.doctor} at {self.start_at}"


class SlotHold(models.Model):
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    patient = models.ForeignKey(User, on_delete=models.CASCADE)
    start_at = models.DateTimeField()
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "start_at"],
                name="only_one_slot_hold"
            )
        ]


class NotificationJob(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SENT", "Sent"),
        ("FAILED", "Failed"),
    ]

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    job_type = models.CharField(max_length=50)
    payload = models.JSONField(default=dict)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    next_retry_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.job_type} — {self.status}"


class MedicationReminder(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    medicine_name = models.CharField(max_length=150)
    frequency = models.CharField(max_length=100)
    reminder_time = models.TimeField()
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.medicine_name} for {self.appointment.patient.username}"

# Create your models here.
