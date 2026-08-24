from django.contrib import admin

from .models import (
    Profile,
    DoctorProfile,
    DoctorLeave,
    Appointment,
    SlotHold,
    NotificationJob,
    MedicationReminder,
)

admin.site.register(Profile)
admin.site.register(DoctorProfile)
admin.site.register(DoctorLeave)
admin.site.register(Appointment)
admin.site.register(SlotHold)
admin.site.register(NotificationJob)
admin.site.register(MedicationReminder)
