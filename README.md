# CareCompass — Healthcare Appointment & Follow-up Manager

CareCompass is a role-based healthcare appointment platform built with Django. It supports safe appointment booking, doctor leave management, AI-assisted pre-visit and post-visit summaries, medication reminders, notifications, and Google Calendar integration architecture.

## Features

### Patient portal

- Register and log in
- Search doctors by specialization
- Book appointments with symptoms
- View appointment status and AI pre-visit brief
- View patient-friendly post-visit care plan
- Reschedule or cancel appointments

### Doctor portal

- View upcoming appointments
- Review symptoms, urgency, chief complaint, and suggested questions
- Submit clinical notes and prescription
- Generate a patient-friendly post-visit summary
- Create medication reminders

### Admin portal

- Manage doctor profiles
- Set specialization, working hours, and slot duration
- Mark doctors on leave
- Detect affected appointments automatically
- Create rescheduling notification jobs for patients

## Technology Stack

- Backend and frontend: Django 6
- Database: SQLite
- Authentication: Django built-in authentication with role-based profiles
- AI integration: OpenAI Python SDK with graceful fallback
- Email: Django console email backend for demo mode
- Background jobs: Django management command worker
- Google Calendar: Google Calendar API adapter with OAuth 2.0 support

## Demo Credentials

### Admin
- **Username:** `admin`
- **Password:** `riya@12345`

### Patient
- New patients can register using the **Register** option.

### Doctor
- Doctor accounts are created and managed by the administrator.

## login url
https://carecompass-healthcare-manager.onrender.com/
