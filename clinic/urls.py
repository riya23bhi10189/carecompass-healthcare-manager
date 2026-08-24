from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(
        template_name="clinic/login.html"
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path("doctors/", views.doctor_search, name="doctor_search"),
    path("book/", views.book_appointment, name="book_appointment"),
    path("appointments/<int:appointment_id>/complete/",
        views.complete_visit,
        name="complete_visit"
        ),
    path("manage/leaves/", views.manage_leaves, name="manage_leaves"),
    path(
        "appointments/<int:appointment_id>/cancel/",
        views.cancel_appointment,
        name="cancel_appointment"
    ),
    path(
        "appointments/<int:appointment_id>/reschedule/",
        views.reschedule_appointment,
        name="reschedule_appointment"
    ),    
    path("api/doctors/", views.api_doctors, name="api_doctors"),
    path(
        "api/appointments/me/",
        views.api_my_appointments,
        name="api_my_appointments"
    ),
]