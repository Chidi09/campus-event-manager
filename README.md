Campus Event Manager
A comprehensive web application designed to streamline event, hall, and bus management within a university or college campus. This system provides different user roles (Student/Staff, DSA, Admin, VC) with tailored functionalities to manage campus activities efficiently.

Table of Contents
Features

Technologies Used

Installation and Setup

Prerequisites

Cloning the Repository

Setting up the Virtual Environment

Installing Dependencies

Database Setup

Running the Application

Usage

File Structure

Contributing

License

Features
User Authentication & Authorization: Secure login and registration system with distinct roles (Student/Staff, DSA, Admin, Vice Chancellor).

Event Management:

Create, view, and manage campus events.

Event registration for users.

Generate attendance certificates for registered attendees.

Automated event reminders.

Hall Booking:

Browse available halls.

Submit booking requests for halls.

Admin approval/rejection of hall bookings.

Bus Booking:

View available bus routes and schedules.

Book bus tickets.

Generate bus tickets with unique identifiers.

Admin management of bus bookings.

Notifications: Real-time notification system for approvals, rejections, event updates, etc.

Admin Dashboard: Centralized dashboard for administrators to manage users, events, halls, buses, and bookings.

DSA Dashboard: Specific dashboard for the Dean of Student Affairs to manage relevant aspects.

Vice Chancellor Dashboard: Overview for the Vice Chancellor.

Responsive Design: User-friendly interface accessible on various devices.

Database Management: Persistent storage using SQLite (default) and SQLAlchemy ORM.

Technologies Used
Backend: Python, Flask

Database: SQLAlchemy (ORM), SQLite (default)

Database Migrations: Alembic

Forms: Flask-WTF, WTForms

Authentication: Flask-Login

Styling: Custom CSS, potentially integrated with a theme.

Frontend: HTML, Jinja2 templating, JavaScript

Environment Management: python-dotenv

Installation and Setup
Follow these steps to get the Campus Event Manager running on your local machine.

Prerequisites
Python 3.8+

pip (Python package installer)

Cloning the Repository
First, clone the repository to your local machine using Git:

git clone https://github.com/your-username/campus_event_manager.git
cd campus_event_manager

(Note: Replace https://github.com/your-username/campus_event_manager.git with your actual GitHub repository URL after you've uploaded it.)

Setting up the Virtual Environment
It's highly recommended to use a virtual environment to manage project dependencies.

python -m venv venv

Activating the Virtual Environment
On Windows:

.\venv\Scripts\activate

On macOS/Linux:

source venv/bin/activate

Installing Dependencies
Once your virtual environment is active, install the required Python packages:

pip install -r requirements.txt

(Note: You will need to create a requirements.txt file if you don't have one. You can generate it using pip freeze > requirements.txt after installing all necessary packages.)

Environment Variables
Create a .env file in the root directory of your project and add the following:

SECRET_KEY='your_secret_key_here'
FLASK_APP=app.py
FLASK_ENV=development # or production

Replace 'your_secret_key_here' with a strong, random string.

Database Setup
The project uses Alembic for database migrations.

Initialize the database (first time only):

flask db init

Create initial migration (first time or after model changes):

flask db migrate -m "Initial migration"

Apply migrations to create tables:

flask db upgrade

Running the Application
With the virtual environment active and dependencies installed, you can run the Flask application:

flask run

The application will typically be accessible at http://127.0.0.1:5000/.

Usage
Registration: New users can register for an account.

Login: Existing users can log in with their credentials.

Dashboards: Depending on the user's role, they will be redirected to their respective dashboards (Student/Staff Dashboard, DSA Dashboard, Admin Dashboard, VC Dashboard).

Explore Features: Navigate through the various sections to manage events, book halls, book buses, and view notifications.

File Structure
campus_event_manager/
├── app.py                  # Main Flask application file
├── models.py               # SQLAlchemy database models
├── forms.py                # WTForms for handling forms
├── extensions.py           # Flask extensions initialization
├── site.db                 # SQLite database file (generated)
├── .env                    # Environment variables
├── .gitignore              # Files/directories to ignore in Git
├── venv/                   # Python virtual environment
├── templates/              # HTML templates (Jinja2)
│   ├── base.html
│   ├── dashboard.html
│   ├── admin_dashboard.html
│   ├── dsa_dashboard.html
│   ├── vc_dashboard.html
│   ├── login.html
│   ├── register.html
│   ├── list_events.html
│   ├── create_event.html
│   ├── event_details.html
│   ├── event_certificate_template.html
│   ├── list_halls.html
│   ├── book_hall_form.html
│   ├── admin_halls.html
│   ├── admin_manage_hall_bookings.html
│   ├── list_buses.html
│   ├── book_bus_form.html
│   ├── admin_buses.html
│   ├── admin_manage_bus_bookings.html
│   ├── my_event_registrations.html
│   ├── my_hall_bookings.html
│   ├── my_bus_bookings.html
│   ├── notifications.html
│   └── ...
├── static/                 # Static assets (CSS, JS, Images, Certificates)
│   ├── css/
│   │   ├── school_theme.css
│   │   └── dashboard_custom.css
│   ├── js/
│   │   └── theme_toggle.js
│   ├── images/
│   │   ├── hero-background.jpg
│   │   └── image45.png
│   └── certificates/       # Generated certificates
├── migrations/             # Alembic migration scripts
│   ├── versions/
│   └── ...
└── README.md               # This file

Contributing
Contributions are welcome! If you'd like to contribute, please follow these steps:

Fork the repository.

Create a new branch (git checkout -b feature/your-feature-name).

Make your changes.

Commit your changes (git commit -m 'Add new feature').

Push to the branch (git push origin feature/your-feature-name).

Create a Pull Request.

License
This project is licensed under the MIT License - see the LICENSE file for details.# campus-event-manager
