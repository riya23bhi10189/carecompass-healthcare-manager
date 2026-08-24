import os
from pathlib import Path

from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from dotenv import load_dotenv
load_dotenv()


SCOPES = ["https://www.googleapis.com/auth/calendar"]


def calendar_is_enabled():
    return os.getenv("GOOGLE_CALENDAR_ENABLED", "False").lower() == "true"


def get_calendar_service(interactive=False):
    credentials_file = Path(settings.BASE_DIR) / os.getenv(
        "GOOGLE_CREDENTIALS_FILE",
        "credentials.json"
    )

    token_file = Path(settings.BASE_DIR) / os.getenv(
        "GOOGLE_TOKEN_FILE",
        "token.json"
    )

    credentials = None

    if token_file.exists():
        credentials = Credentials.from_authorized_user_file(
            token_file,
            SCOPES
        )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    elif not credentials or not credentials.valid:
        if not interactive:
            raise RuntimeError(
                "Google Calendar is not authorised yet. "
                "Run the calendar setup command first."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_file,
            SCOPES
        )

        credentials = flow.run_local_server(port=0)

    token_file.write_text(credentials.to_json())

    return build("calendar", "v3", credentials=credentials)


def create_calendar_event(appointment):
    # Demo mode: booking still works when Calendar is not configured.
    if not calendar_is_enabled():
        print("Calendar demo mode: event would be created.")
        return ""

    service = get_calendar_service()

    doctor_name = appointment.doctor.user.get_full_name()
    patient_name = appointment.patient.get_full_name()

    event = {
        "summary": f"CareCompass: {patient_name} with Dr. {doctor_name}",
        "description": (
            "Healthcare appointment created by CareCompass. "
            "Please log in to view appointment details."
        ),
        "start": {
            "dateTime": appointment.start_at.isoformat(),
            "timeZone": settings.TIME_ZONE,
        },
        "end": {
            "dateTime": appointment.end_at.isoformat(),
            "timeZone": settings.TIME_ZONE,
        },
        "attendees": [
            {"email": appointment.patient.email},
            {"email": appointment.doctor.user.email},
        ],
    }

    created_event = service.events().insert(
        calendarId="primary",
        body=event,
        sendUpdates="all"
    ).execute()

    return created_event["id"]

def delete_calendar_event(event_id):
    if not event_id:
        return

    if not calendar_is_enabled():
        print("Calendar demo mode: event would be deleted.")
        return

    service = get_calendar_service()

    service.events().delete(
        calendarId="primary",
        eventId=event_id,
        sendUpdates="all"
    ).execute()

def update_calendar_event(appointment):
    if not appointment.calendar_event_id:
        return create_calendar_event(appointment)

    if not calendar_is_enabled():
        print("Calendar demo mode: event would be updated.")
        return appointment.calendar_event_id

    service = get_calendar_service()

    event = {
        "summary": (
            f"CareCompass: {appointment.patient.get_full_name()} "
            f"with Dr. {appointment.doctor.user.get_full_name()}"
        ),
        "start": {
            "dateTime": appointment.start_at.isoformat(),
            "timeZone": settings.TIME_ZONE,
        },
        "end": {
            "dateTime": appointment.end_at.isoformat(),
            "timeZone": settings.TIME_ZONE,
        },
        "attendees": [
            {"email": appointment.patient.email},
            {"email": appointment.doctor.user.email},
        ],
    }

    updated_event = service.events().update(
        calendarId="primary",
        eventId=appointment.calendar_event_id,
        body=event,
        sendUpdates="all"
    ).execute()

    return updated_event["id"]