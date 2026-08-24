from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AppointmentForm, RegistrationForm, RescheduleForm
from .services.ai import create_pre_visit_summary, create_post_visit_summary
from .services.calendar import (
    create_calendar_event,
    delete_calendar_event,
    update_calendar_event,
)   
from .models import (
    Appointment,
    DoctorLeave,
    DoctorProfile,
    MedicationReminder,
    NotificationJob,
    Profile,
)


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(
                user=user,
                defaults={"role": "PATIENT"}
            )
            login(request, user)
            messages.success(request, "Your CareCompass account was created.")
            return redirect("dashboard")
    else:
        form = RegistrationForm()

    return render(request, "clinic/register.html", {"form": form})


@login_required
def dashboard(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={"role": "PATIENT"}
    )

    if profile.role == "ADMIN":
        return redirect("/admin/")

    if profile.role == "DOCTOR":
        appointments = Appointment.objects.filter(
            doctor__user=request.user
        ).exclude(status="CANCELLED").order_by("start_at")

        return render(
            request,
            "clinic/doctor_dashboard.html",
            {"appointments": appointments}
        )

    appointments = Appointment.objects.filter(
        patient=request.user
    ).order_by("-start_at")

    return render(
        request,
        "clinic/patient_dashboard.html",
        {"appointments": appointments}
    )


@login_required
def doctor_search(request):
    if request.user.profile.role != "PATIENT":
        return redirect("dashboard")

    query = request.GET.get("specialization", "")

    doctors = DoctorProfile.objects.select_related("user")

    if query:
        doctors = doctors.filter(
            specialization__icontains=query
        )

    return render(
        request,
        "clinic/doctor_search.html",
        {"doctors": doctors, "query": query}
    )


@login_required
def book_appointment(request):
    if request.user.profile.role != "PATIENT":
        return redirect("dashboard")

    if request.method == "POST":
        form = AppointmentForm(request.POST)

        if form.is_valid():
            doctor = form.cleaned_data["doctor"]
            start_at = form.cleaned_data["start_at"]

            # Prevent booking a doctor who is on leave.
            if DoctorLeave.objects.filter(
                doctor=doctor,
                leave_date=start_at.date()
            ).exists():
                form.add_error(
                    "start_at",
                    "This doctor is on leave on the selected date."
                )

            else:
                try:
                    # Atomic transaction + database unique constraint
                    # prevent simultaneous double booking.
                    with transaction.atomic():
                        appointment = form.save(commit=False)
                        appointment.patient = request.user
                        appointment.end_at = start_at + timedelta(
                            minutes=doctor.slot_duration
                        )
                        appointment.status = "CONFIRMED"
                        appointment.save()


                    summary = create_pre_visit_summary(appointment.symptoms)

                    appointment.urgency = summary.get("urgency", "MEDIUM")
                    appointment.pre_visit_summary = summary
                    appointment.save(
                        update_fields=["urgency", "pre_visit_summary"]
                    )

                    # Calendar failure must never cancel a valid appointment.
                    try:
                        calendar_event_id = create_calendar_event(appointment)
                        if calendar_event_id:
                            appointment.calendar_event_id = calendar_event_id
                            appointment.save(update_fields=["calendar_event_id"])
                    except Exception as error:
                        print("Calendar event could not be created:", error)

                        NotificationJob.objects.create(
                            appointment=appointment,
                            job_type="CALENDAR_RETRY",
                            payload={
                                "appointment_id": appointment.id,
                                "error": str(error)
                            }
                        )

                    NotificationJob.objects.create(
                        appointment=appointment,
                        job_type="BOOKING_CONFIRMATION",
                        payload={"appointment_id": appointment.id}
                    )

                    messages.success(
                        request,
                        "Appointment booked successfully."
                    )
                    return redirect("dashboard")

                except IntegrityError:
                    form.add_error(
                        "start_at",
                        "That time slot was just booked. Please choose another time."
                    )
    else:
        form = AppointmentForm()

        doctor_id = request.GET.get("doctor")
        if doctor_id:
            form.initial["doctor"] = doctor_id

    return render(
        request,
        "clinic/book_appointment.html",
        {"form": form}
    )
@login_required
def complete_visit(request, appointment_id):
    if request.user.profile.role != "DOCTOR":
        return redirect("dashboard")

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        doctor__user=request.user
    )

    if request.method == "POST":
        notes = request.POST.get("doctor_notes", "").strip()
        prescription = request.POST.get("prescription", "").strip()
        medicine_name = request.POST.get("medicine_name", "").strip()
        frequency = request.POST.get("frequency", "").strip()
        reminder_time = request.POST.get("reminder_time", "").strip()

        if not notes:
            messages.error(request, "Clinical notes are required.")
        else:
            summary = create_post_visit_summary(notes, prescription)

            appointment.doctor_notes = notes
            appointment.prescription = prescription
            appointment.post_visit_summary = summary
            appointment.status = "COMPLETED"
            appointment.save()

            if medicine_name and frequency and reminder_time:
                MedicationReminder.objects.create(
                    appointment=appointment,
                    medicine_name=medicine_name,
                    frequency=frequency,
                    reminder_time=reminder_time
                    )


            NotificationJob.objects.create(
                appointment=appointment,
                job_type="POST_VISIT_SUMMARY",
                payload={"appointment_id": appointment.id}
            )

            messages.success(
                request,
                "Visit completed and patient care plan generated."
            )
            return redirect("dashboard")

    return render(
        request,
        "clinic/complete_visit.html",
        {"appointment": appointment}
    )
@login_required
def manage_leaves(request):
    if request.user.profile.role != "ADMIN":
        return redirect("dashboard")

    if request.method == "POST":
        doctor_id = request.POST.get("doctor")
        leave_date = request.POST.get("leave_date")
        reason = request.POST.get("reason", "")

        doctor = get_object_or_404(DoctorProfile, id=doctor_id)

        leave, created = DoctorLeave.objects.get_or_create(
            doctor=doctor,
            leave_date=leave_date,
            defaults={"reason": reason}
        )

        if not created:
            messages.error(
                request,
                "This doctor is already marked on leave for that date."
            )
        else:
            affected_appointments = list(
                Appointment.objects.filter(
                doctor=doctor,
                start_at__date=leave_date,
                status="CONFIRMED"
            )
        )

            with transaction.atomic():
                for appointment in affected_appointments:
                    appointment.status = "ACTION_REQUIRED"
                    appointment.save(update_fields=["status"])

                    NotificationJob.objects.create(
                        appointment=appointment,
                        job_type="LEAVE_CONFLICT",
                        payload={
                            "appointment_id": appointment.id,
                            "doctor_id": doctor.id,
                            "leave_date": leave_date
                        }
                    )

            messages.success(
                request,
                f"Leave saved. {len(affected_appointments)} affected appointment(s) need rescheduling."
            )

        return redirect("manage_leaves")

    doctors = DoctorProfile.objects.select_related("user").order_by(
        "specialization"
    )

    leaves = DoctorLeave.objects.select_related(
        "doctor__user"
    ).order_by("-leave_date")

    return render(
        request,
        "clinic/manage_leaves.html",
        {"doctors": doctors, "leaves": leaves}
    )

@login_required
def cancel_appointment(request, appointment_id):
    if request.user.profile.role != "PATIENT":
        return redirect("dashboard")

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        patient=request.user
    )

    if request.method == "POST":
        appointment.status = "CANCELLED"
        appointment.save(update_fields=["status"])

        try:
            delete_calendar_event(appointment.calendar_event_id)

        except Exception as error:
            print("Calendar event could not be deleted:", error)

            NotificationJob.objects.create(
                appointment=appointment,
                job_type="CALENDAR_RETRY",
                payload={
                    "appointment_id": appointment.id,
                    "action": "DELETE",
                    "error": str(error)
                }
            )

        NotificationJob.objects.create(
            appointment=appointment,
            job_type="CANCELLATION",
            payload={"appointment_id": appointment.id}
        )

        messages.success(request, "Appointment cancelled successfully.")

    return redirect("dashboard")

@login_required
def reschedule_appointment(request, appointment_id):
    if request.user.profile.role != "PATIENT":
        return redirect("dashboard")

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        patient=request.user
    )

    if request.method == "POST":
        form = RescheduleForm(request.POST, instance=appointment)

        if form.is_valid():
            doctor = form.cleaned_data["doctor"]
            start_at = form.cleaned_data["start_at"]

            if DoctorLeave.objects.filter(
                doctor=doctor,
                leave_date=start_at.date()
            ).exists():
                form.add_error(
                    "start_at",
                    "This doctor is on leave on the selected date."
                )
            else:
                try:
                    with transaction.atomic():
                        updated_appointment = form.save(commit=False)
                        updated_appointment.end_at = start_at + timedelta(
                            minutes=doctor.slot_duration
                        )
                        updated_appointment.status = "CONFIRMED"
                        updated_appointment.save()

                    try:
                        calendar_event_id = update_calendar_event(updated_appointment)

                        if calendar_event_id:
                            updated_appointment.calendar_event_id = calendar_event_id
                            updated_appointment.save(update_fields=["calendar_event_id"])

                    except Exception as error:
                        NotificationJob.objects.create(
                            appointment=updated_appointment,
                            job_type="CALENDAR_RETRY",
                            payload={
                                "appointment_id": updated_appointment.id,
                                "action": "UPDATE",
                                "error": str(error)
                            }
                        )

                    NotificationJob.objects.create(
                        appointment=updated_appointment,
                        job_type="RESCHEDULED",
                        payload={
                            "appointment_id": updated_appointment.id
                        }
                    )

                    messages.success(
                        request,
                        "Appointment rescheduled successfully."
                    )
                    return redirect("dashboard")

                except IntegrityError:
                    form.add_error(
                        "start_at",
                        "That time slot is unavailable. Please choose another."
                    )
    else:
        form = RescheduleForm(instance=appointment)

    return render(
        request,
        "clinic/reschedule_appointment.html",
        {
            "form": form,
            "appointment": appointment
        }
    )
@require_GET
def api_doctors(request):
    specialization = request.GET.get("specialization", "")

    doctors = DoctorProfile.objects.select_related("user")

    if specialization:
        doctors = doctors.filter(
            specialization__icontains=specialization
        )

    data = [
        {
            "id": doctor.id,
            "name": (
                doctor.user.get_full_name()
                or doctor.user.username
            ),
            "specialization": doctor.specialization,
            "working_start": doctor.working_start.strftime("%H:%M"),
            "working_end": doctor.working_end.strftime("%H:%M"),
            "slot_duration_minutes": doctor.slot_duration,
        }
        for doctor in doctors
    ]

    return JsonResponse({"doctors": data})


@login_required
@require_GET
def api_my_appointments(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={"role": "PATIENT"}
    )

    if profile.role != "PATIENT":
        return JsonResponse(
            {"error": "Only patients can access this endpoint."},
            status=403
        )

    appointments = Appointment.objects.filter(
        patient=request.user
    ).select_related(
        "doctor__user"
    ).order_by("-start_at")

    data = [
        {
            "id": appointment.id,
            "doctor": (
                appointment.doctor.user.get_full_name()
                or appointment.doctor.user.username
            ),
            "specialization": appointment.doctor.specialization,
            "start_at": appointment.start_at.isoformat(),
            "end_at": appointment.end_at.isoformat(),
            "status": appointment.status,
            "urgency": appointment.urgency,
            "pre_visit_summary": appointment.pre_visit_summary,
            "post_visit_summary": appointment.post_visit_summary,
        }
        for appointment in appointments
    ]

    return JsonResponse({"appointments": data})