# app.py
import os
from xhtml2pdf import pisa
from flask import Flask, render_template, request, redirect, url_for, flash, render_template_string, send_file
from dotenv import load_dotenv
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from jinja2 import pass_eval_context
from markupsafe import Markup, escape
import re
from datetime import datetime, date, time, timedelta, UTC
import uuid
import qrcode
import base64
from io import BytesIO
# Import Message for Flask-Mail
from flask_mail import Message # ADDED THIS IMPORT
from flask import abort

# ** FIX: Import extensions from the new extensions.py file **
from extensions import db, migrate, login_manager, csrf, mail, scheduler

# --- Pre-initialization is no longer needed here ---

# Load environment variables from .env file
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)

# Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['PER_PAGE'] = 10 

# --- Flask-Mail Configuration ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

# --- APScheduler Configuration ---
app.config['SCHEDULER_API_ENABLED'] = True
app.config['SCHEDULER_TIMEZONE'] = 'UTC'

# --- Initialize Extensions with the App ---
db.init_app(app)
migrate.init_app(app, db)
csrf.init_app(app)
login_manager.init_app(app)
mail.init_app(app)

# Ensure this path exists or create it.
CERTIFICATES_FOLDER = os.path.join(app.root_path, 'static', 'certificates')
if not os.path.exists(CERTIFICATES_FOLDER):
    os.makedirs(CERTIFICATES_FOLDER)

# --- Late Imports ---
# Now that the circular dependency is broken, these can be imported safely.
from forms import EventForm, RegistrationForm, LoginForm, RegisterForEventForm, CreateStaffForm, HallForm, BusForm, HallBookingForm, RsvpForm, BusBookingForm
from models import User, Event, Registration, Hall, HallBooking, Bus, BusBooking, Notification


# Function to send confirmation email
def send_confirmation_email(user_email, event, registration):
    msg = Message('Event Registration Confirmation', recipients=[user_email])
    msg.body = f"""Hello {registration.user.username},

Thank you for registering for the event: {event.name}!

Event Details:
Name: {event.name}
Date: {event.date.strftime('%A, %B %d, %Y at %I:%M %p')}
Location: {event.location}
Price: {'Free' if event.price == 0 else f'${event.price:.2f}'}

Your Registration Details:
Registration Date: {registration.registration_date.strftime('%Y-%m-%d %H:%M')}
Ticket ID: {registration.ticket_id if registration.ticket_id else 'N/A'}
Payment Status: {registration.payment_status.upper()}

Please keep this email for your records.

We look forward to seeing you there!

Best regards,
The Campus Event Manager Team
"""
    try:
        mail.send(msg)
        print(f"Confirmation email sent to {user_email} for event {event.name}.")
    except Exception as e:
        print(f"Failed to send email to {user_email}: {e}")

# Function to send event reminder emails
def send_event_reminders():
    with app.app_context():
        print("Running scheduled job: send_event_reminders")
        reminder_window_start = datetime.now(UTC)
        reminder_window_end = datetime.now(UTC) + timedelta(days=1)
        
        upcoming_events_for_reminder = Event.query.filter(
            Event.status == 'Approved',
            Event.reminder_sent == False,
            Event.date >= reminder_window_start,
            Event.date <= reminder_window_end
        ).all()

        for event in upcoming_events_for_reminder:
            print(f"Checking event '{event.name}' for reminders.")
            registrations = Registration.query.filter_by(event_id=event.id).all()
            
            for registration in registrations:
                if registration.user and registration.user.email:
                    try:
                        msg = Message(f"Reminder: Upcoming Event - {event.name}", recipients=[registration.user.email])
                        msg.body = f"""Hello {registration.user.username},

This is a friendly reminder for the upcoming event: {event.name}!

Event Details:
Name: {event.name}
Date: {event.date.strftime('%A, %B %d, %Y at %I:%M %p')}
Location: {event.location}

We look forward to seeing you there!

Best regards,
The Campus Event Manager Team
"""
                        mail.send(msg)
                        print(f"Reminder email sent to {registration.user.email} for event {event.name}.")
                    except Exception as e:
                        print(f"Failed to send reminder email to {registration.user.email} for event {event.name}: {e}")
                else:
                    print(f"Skipping reminder for registration {registration.id}: No valid user or email.")
            
            event.reminder_sent = True
            db.session.commit()
            
        print("Finished scheduled job: send_event_reminders")


# Helper function to create a notification
def create_notification(user_id, message, notification_type=None, related_id=None):
    with app.app_context(): # Ensure app context is pushed if called outside a request
        notification = Notification(
            user_id=user_id,
            message=message,
            notification_type=notification_type,
            related_id=related_id
        )
        db.session.add(notification)
        db.session.commit()
        print(f"Notification created for user {user_id}: {message}")

# Helper function to generate QR code as base64
def generate_qr_code_base64(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# Helper function to generate PDF
def generate_pdf_from_template(template_name, filename, context):
    """Generates a PDF from a Jinja2 template."""
    html = render_template(template_name, **context)
    path = os.path.join(CERTIFICATES_FOLDER, filename)
    try:
        with open(path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(
                html,                # the HTML to convert
                dest=pdf_file)       # file handle to receive result
        if pisa_status.err:
            print(f"PDF generation error for {filename}: {pisa_status.err}")
            return None
        print(f"PDF generated successfully: {path}")
        return path
    except Exception as e:
        print(f"Error generating PDF {filename}: {e}")
        return None


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- Custom Jinja Filter: nl2br ---
_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')

@app.template_filter()
@pass_eval_context
def nl2br(eval_ctx, value):
    br = "<br>\n"
    if eval_ctx.autoescape:
        value = escape(value)
        br = Markup(br)
    result = "\n\n".join(
        f"<p>{br.join(p.splitlines())}</p>"
        for p in _paragraph_re.split(value)
    )
    return Markup(result) if eval_ctx.autoescape else result
# --- End of Custom Filter ---


# --- Helper Decorators ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def dsa_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'dsa':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def vc_office_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'vc_office':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Authentication and General Routes ---
@app.route('/')
@login_required
def index():
    if current_user.role == 'student':
        return redirect(url_for('dashboard'))
    elif current_user.role == 'dsa':
        return redirect(url_for('dsa_dashboard'))
    elif current_user.role == 'vc_office':
        return redirect(url_for('vc_dashboard'))
    elif current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        abort(403)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User(username=form.username.data, email=form.email.data, role=form.role.data, image_file='default.jpg')
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'dsa':
                return redirect(url_for('dsa_dashboard'))
            elif user.role == 'vc_office':
                return redirect(url_for('vc_dashboard'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'dsa':
        return redirect(url_for('dsa_dashboard'))
    elif current_user.role == 'vc_office':
        return redirect(url_for('vc_dashboard'))
    return render_template('dashboard.html', name=current_user.username)

# --- Admin Routes ---
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    # This dashboard can be expanded with more stats later
    my_events = Event.query.filter_by(created_by=current_user.id).order_by(Event.date.desc()).all()
    return render_template('admin_dashboard.html', my_events=my_events)

@app.route('/admin/create_staff', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_create_staff():
    form = CreateStaffForm()
    if form.validate_on_submit():
        new_staff = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data,
            image_file='default.jpg'
        )
        new_staff.set_password(form.password.data)
        db.session.add(new_staff)
        db.session.commit()
        flash(f'Staff account for {new_staff.username} ({new_staff.role}) created successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('create_staff.html', title='Create Staff Account', form=form)

@app.route('/admin/halls', methods=['GET', ' POST'])
@login_required
@admin_required
def admin_manage_halls():
    form = HallForm()
    if form.validate_on_submit():
        existing_hall = Hall.query.filter_by(name=form.name.data).first()
        if existing_hall:
            flash(f"A hall with the name '{form.name.data}' already exists.", 'warning')
        else:
            new_hall = Hall(
                name=form.name.data,
                capacity=form.capacity.data,
                location_details=form.location_details.data
            )
            db.session.add(new_hall)
            db.session.commit()
            flash(f"Hall '{new_hall.name}' added successfully!", 'success')
            return redirect(url_for('admin_manage_halls'))
    halls = Hall.query.order_by(Hall.name).all()
    return render_template('admin_halls.html', halls=halls, form=form)


@app.route('/admin/buses', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_manage_buses():
    form = BusForm()
    if form.validate_on_submit():
        existing_bus = Bus.query.filter_by(identifier=form.identifier.data).first()
        if existing_bus:
            flash(f"A bus with the identifier '{form.identifier.data}' already exists.", 'warning')
        else:
            new_bus = Bus(
                identifier=form.identifier.data,
                capacity=form.capacity.data,
                driver_contact=form.driver_contact.data,
                route_details=form.route_details.data
            )
            db.session.add(new_bus)
            db.session.commit()
            flash(f"Bus '{new_bus.identifier}' added successfully!", 'success')
            return redirect(url_for('admin_manage_buses'))
    buses = Bus.query.order_by(Bus.identifier).all()
    return render_template('admin_buses.html', buses=buses, form=form)


@app.route('/admin/hall_bookings', methods=['GET'])
@login_required
@admin_required
def admin_manage_hall_bookings():
    pending_bookings = HallBooking.query.filter_by(status='Pending').order_by(HallBooking.requested_date, HallBooking.start_time).all()
    processed_bookings = HallBooking.query.filter(HallBooking.status != 'Pending').order_by(HallBooking.processed_timestamp.desc(), HallBooking.requested_date.desc()).all()
    return render_template('admin_manage_hall_bookings.html', pending_bookings=pending_bookings, processed_bookings=processed_bookings)

@app.route('/admin/hall_booking/approve/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def admin_approve_hall_booking(booking_id):
    booking = HallBooking.query.get_or_404(booking_id)
    if booking.status == 'Pending':
        booking.status = 'Approved'
        booking.processed_by_admin_id = current_user.id
        booking.processed_timestamp = datetime.now(UTC)
        db.session.commit()
        flash(f"Booking ID {booking.id} for '{booking.hall.name}' has been approved.", 'success')
        # Notify the student who made the booking
        create_notification(booking.student_id, f"Your hall booking for '{booking.hall.name}' on {booking.requested_date.strftime('%Y-%m-%d')} has been APPROVED!", 'booking_status_update', booking.id) #cite: uploaded:app.py
    else:
        flash(f"Booking ID {booking.id} is not in 'Pending' state.", 'warning')
    return redirect(url_for('admin_manage_hall_bookings'))

@app.route('/admin/hall_booking/reject/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def admin_reject_hall_booking(booking_id):
    booking = HallBooking.query.get_or_404(booking_id)
    if booking.status == 'Pending':
        booking.status = 'Rejected'
        booking.processed_by_admin_id = current_user.id
        booking.processed_timestamp = datetime.now(UTC)
        booking.admin_remarks = request.form.get('admin_remarks', "Rejected by Admin")
        db.session.commit()
        flash(f"Booking ID {booking.id} for '{booking.hall.name}' has been rejected.", 'success')
        # Notify the student who made the booking
        create_notification(booking.student_id, f"Your hall booking for '{booking.hall.name}' on {booking.requested_date.strftime('%Y-%m-%d')} has been REJECTED. Remarks: {booking.admin_remarks}", 'booking_status_update', booking.id) #cite: uploaded:app.py
    else:
        flash(f"Booking ID {booking.id} is not in 'Pending' state.", 'warning')
    return redirect(url_for('admin_manage_hall_bookings'))

# --- Admin Bus Bookings ---
@app.route('/admin/bus_bookings', methods=['GET'])
@login_required
@admin_required
def admin_manage_bus_bookings():
    pending_bookings = BusBooking.query.filter_by(status='Pending').order_by(BusBooking.requested_date, BusBooking.pickup_time).all()
    processed_bookings = BusBooking.query.filter(BusBooking.status != 'Pending').order_by(BusBooking.processed_timestamp.desc(), BusBooking.requested_date.desc()).all()
    return render_template('admin_manage_bus_bookings.html', pending_bookings=pending_bookings, processed_bookings=processed_bookings)

@app.route('/admin/bus_booking/approve/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def admin_approve_bus_booking(booking_id):
    booking = BusBooking.query.get_or_404(booking_id)
    if booking.status == 'Pending':
        booking.status = 'Approved'
        booking.processed_by_admin_id = current_user.id
        booking.processed_timestamp = datetime.now(UTC)
        
        # Generate bus ticket PDF
        qr_data = f"Bus Booking ID: {booking.id}\nPassenger: {booking.requester.username}\nBus: {booking.bus.identifier}\nDate: {booking.requested_date.strftime('%Y-%m-%d')}"
        qr_code_base64 = generate_qr_code_base64(qr_data)
        
        ticket_filename = f"bus_ticket_{booking.id}.pdf"
        ticket_path = generate_pdf_from_template(
            'bus_ticket_template.html',
            ticket_filename,
            context={
                'booking': booking,
                'qr_code_base64': qr_code_base64,
                'now': datetime.now(UTC)
            }
        )
        
        if ticket_path:
            booking.certificate_path = os.path.relpath(ticket_path, app.root_path) # Store path relative to app root
            booking.certificate_generated_at = datetime.now(UTC)
            flash(f"Bus ticket generated at {ticket_path}", 'info')
        else:
            flash("Failed to generate bus ticket PDF.", 'danger')

        db.session.commit()
        flash(f"Bus Booking ID {booking.id} for '{booking.bus.identifier if booking.bus else 'N/A'}' has been approved.", 'success')
        # Notify the student who made the booking
        create_notification(booking.student_id, f"Your bus booking for '{booking.bus.identifier if booking.bus else 'N/A'}' on {booking.requested_date.strftime('%Y-%m-%d')} has been APPROVED! Your ticket is now available.", 'booking_status_update', booking.id)
    else:
        flash(f"Bus Booking ID {booking.id} is not in 'Pending' state.", 'warning')
    return redirect(url_for('admin_manage_bus_bookings'))

@app.route('/admin/bus_booking/reject/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def admin_reject_bus_booking(booking_id):
    booking = BusBooking.query.get_or_404(booking_id)
    if booking.status == 'Pending':
        booking.status = 'Rejected'
        booking.processed_by_admin_id = current_user.id
        booking.processed_timestamp = datetime.now(UTC)
        booking.admin_remarks = request.form.get('admin_remarks', "Rejected by Admin")
        db.session.commit()
        flash(f"Bus Booking ID {booking.id} for '{booking.bus.identifier if booking.bus else 'N/A'}' has been rejected.", 'success')
        # Notify the student who made the booking
        create_notification(booking.student_id, f"Your bus booking for '{booking.bus.identifier if booking.bus else 'N/A'}' on {booking.requested_date.strftime('%Y-%m-%d')} has been REJECTED. Remarks: {booking.admin_remarks}", 'booking_status_update', booking.id)
    else:
        flash(f"Bus Booking ID {booking.id} is not in 'Pending' state.", 'warning')
    return redirect(url_for('admin_manage_bus_bookings'))

# --- Event Routes (Creation, Approval, RSVP) ---
@app.route("/events")
def list_events():
    events = Event.query.order_by(Event.date.asc()).all()
    return render_template('list_events.html', title='Available Events', events=events)
@app.route('/create_event', methods=['GET', 'POST'])
@admin_required
def create_event():
    form = EventForm()
    if form.validate_on_submit():
        event = Event(
            name=form.name.data,
            description=form.description.data,
            date=form.date.data,
            location=form.location.data,
            price=form.price.data,
            capacity=form.capacity.data,
            created_by=current_user.id,
            status='Pending DSA Approval'
        )
        db.session.add(event)
        db.session.commit()
        flash('Your event has been created and is awaiting DSA approval!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('create_event.html', title='New Event', form=form)

@app.route('/dsa/dashboard')
@login_required
@dsa_required
def dsa_dashboard():
    pending_events = Event.query.filter_by(status='Pending DSA Approval').order_by(Event.date).all()
    return render_template('dsa_dashboard.html', pending_events=pending_events)

@app.route('/dsa/approve_event/<int:event_id>', methods=['POST'])
@login_required
@dsa_required
def dsa_approve_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.status == 'Pending DSA Approval':
        event.status = 'Pending VC Office Approval'
        event.dsa_approver_id = current_user.id
        db.session.commit()
        flash(f"Event '{event.name}' approved and sent for VC Office approval.", 'success')
        # Notify the event creator
        create_notification(event.created_by, f"Your event '{event.name}' has been approved by DSA and sent to VC Office.", 'event_status_update', event.id)
    else:
        flash(f"Event '{event.name}' could not be approved at this stage.", 'warning')
    return redirect(url_for('dsa_dashboard'))

@app.route('/dsa/reject_event/<int:event_id>', methods=['POST'])
@login_required
@dsa_required
def dsa_reject_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.status == 'Pending DSA Approval':
        event.status = 'DSA Rejected'
        event.dsa_approver_id = current_user.id
        db.session.commit()
        flash(f"Event '{event.name}' has been rejected.", 'success')
        # Notify the event creator
        create_notification(event.created_by, f"Your event '{event.name}' has been rejected by DSA.", 'event_status_update', event.id)
    else:
        flash(f"Event '{event.name}' could not be rejected at this stage.", 'warning')
    return redirect(url_for('dsa_dashboard'))

@app.route('/vc/dashboard')
@login_required
@vc_office_required
def vc_dashboard():
    target_status = 'Pending VC Office Approval'
    pending_events = Event.query.filter_by(status=target_status).order_by(Event.date).all()
    return render_template('vc_dashboard.html', pending_events=pending_events)

@app.route('/vc/approve_event/<int:event_id>', methods=['POST'])
@login_required
@vc_office_required
def vc_approve_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.status == 'Pending VC Office Approval':
        event.status = 'Approved'
        event.vc_approver_id = current_user.id
        db.session.commit()
        flash(f"Event '{event.name}' has been fully approved and is now live.", 'success')
        # Notify the event creator
        create_notification(event.created_by, f"Your event '{event.name}' has been fully APPROVED and is now live!", 'event_status_update', event.id)
    else:
        flash(f"Event '{event.name}' could not be approved at this stage.", 'warning')
    return redirect(url_for('vc_dashboard'))

@app.route('/vc/reject_event/<int:event_id>', methods=['POST'])
@login_required
@vc_office_required
def vc_reject_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.status == 'Pending VC Office Approval':
        event.status = 'VC Rejected'
        event.vc_approver_id = current_user.id
        db.session.commit()
        flash(f"Event '{event.name}' has been rejected by the VC Office.", 'success')
        # Notify the event creator
        create_notification(event.created_by, f"Your event '{event.name}' has been rejected by the VC Office.", 'event_status_update', event.id)
    else:
        flash(f"Event '{event.name}' could not be rejected at this stage.", 'warning')
    return redirect(url_for('vc_dashboard'))

@app.route('/rsvp/<int:event_id>', methods=['POST'])
@login_required
def rsvp_event(event_id):
    if current_user.role != 'student':
        flash('Only students can RSVP for events.', 'danger')
        return redirect(url_for('dashboard'))

    event = Event.query.get_or_404(event_id)

    if event.status != 'Approved':
        flash('This event is not currently open for RSVPs or has not been approved.', 'warning')
        return redirect(url_for('list_events'))

    if Registration.query.filter_by(user_id=current_user.id, event_id=event.id).first():
        flash('You have already RSVP\'d for this event.', 'info')
    else:
        try:
            payment_status = 'N/A' if event.price == 0 else 'pending'
            new_registration = Registration(user_id=current_user.id, event_id=event.id, payment_status=payment_status)
            
            # If event is free, generate ticket immediately
            if payment_status == 'paid' or event.price == 0:
                ticket_id = str(uuid.uuid4())
                new_registration.ticket_id = ticket_id

                qr_data = f"Event: {event.name}\nAttendee: {current_user.username}\nTicket ID: {ticket_id}"
                qr_code_base64 = generate_qr_code_base64(qr_data)
                
                certificate_filename = f"event_certificate_{new_registration.id}_{ticket_id}.pdf"
                certificate_path = generate_pdf_from_template(
                    'event_certificate_template.html',
                    certificate_filename,
                    context={
                        'user': current_user,
                        'event': event,
                        'registration': new_registration,
                        'qr_code_base64': qr_code_base64,
                        'now': datetime.now(UTC)
                    }
                )
                if certificate_path:
                    new_registration.certificate_path = os.path.relpath(certificate_path, app.root_path)
                    new_registration.certificate_generated_at = datetime.now(UTC)
                    flash(f"Event certificate generated at {certificate_path}", 'info')
                else:
                    flash("Failed to generate event certificate PDF.", 'danger')

            db.session.add(new_registration)
            db.session.commit()

            if payment_status == 'paid' or event.price == 0:
                flash(f'Successfully registered for {event.name}! Your ticket ID is: {new_registration.ticket_id}', 'success')
                send_confirmation_email(current_user.email, event, new_registration)
            else:
                flash(f'Your registration for {event.name} is pending payment. Please complete payment to confirm.', 'warning')
            return redirect(url_for('my_event_registrations'))

        except Exception as e:
            db.session.rollback()
            flash(f'Could not process your RSVP. An error occurred: {e}', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/cancel_rsvp/<int:event_id>', methods=['POST'])
@login_required
def cancel_rsvp_event(event_id):
    if current_user.role != 'student':
        flash('Only students can manage RSVPs.', 'danger')
        return redirect(url_for('dashboard'))

    event = Event.query.get_or_404(event_id)
    registration_record = Registration.query.filter_by(user_id=current_user.id, event_id=event.id).first()

    if registration_record:
        # Optional: Delete the generated certificate file if it exists
        if registration_record.certificate_path and os.path.exists(os.path.join(app.root_path, registration_record.certificate_path)):
            os.remove(os.path.join(app.root_path, registration_record.certificate_path))
            print(f"Deleted certificate file: {registration_record.certificate_path}")

        db.session.delete(registration_record)
        db.session.commit()
        flash('Your RSVP has been cancelled.', 'success')
    else:
        flash('You were not RSVP\'d for this event.', 'info')
    return redirect(url_for('dashboard'))

# --- Student Resource Viewing & Booking Routes ---
@app.route('/halls')
@login_required
def list_halls():
    halls = Hall.query.order_by(Hall.name).all()
    return render_template('list_halls.html', halls=halls)

@app.route('/hall/book/<int:hall_id>', methods=['GET', 'POST'])
@login_required
def book_hall_request(hall_id):
    hall = Hall.query.get_or_404(hall_id)
    form = HallBookingForm()

    # Fetch approved events for the dropdown
    approved_events = Event.query.filter_by(status='Approved').order_by(Event.date.desc()).all()
    # Use an empty string for the "None" option value to work with the Optional() validator
    form.event_id.choices = [('', '-- None --')] + [(e.id, f'{e.name} ({e.date.strftime("%Y-%m-%d")})') for e in approved_events]

    if form.validate_on_submit():
        # Validation (e.g., end_time > start_time) is now handled by the form.
        new_booking = HallBooking(
            hall_id=hall.id,
            student_id=current_user.id,
            requested_date=form.requested_date.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            purpose=form.purpose.data,
            event_id=form.event_id.data, # Will be None if '-- None --' is selected
            status='Pending',
            timestamp=datetime.now(UTC)
        )
        db.session.add(new_booking)
        db.session.commit()
        flash(f"Booking request for '{hall.name}' submitted successfully!", 'success')
        # Redirecting to their own bookings page is better UX
        return redirect(url_for('my_hall_bookings'))

    # If validation fails, the template will be re-rendered with errors.
    return render_template('book_hall_form.html', form=form, hall=hall)


@app.route('/my_hall_bookings')
@login_required
def my_hall_bookings():
    bookings = HallBooking.query.filter_by(student_id=current_user.id).order_by(HallBooking.timestamp.desc()).all()
    return render_template('my_hall_bookings.html', bookings=bookings)

@app.route('/buses')
@login_required
def list_buses():
    buses = Bus.query.order_by(Bus.identifier).all()
    return render_template('list_buses.html', buses=buses)

@app.route('/bus/book/<int:bus_id>', methods=['GET', 'POST'])
@login_required
def book_bus_request(bus_id):
    bus = Bus.query.get_or_404(bus_id)
    form = BusBookingForm()

    # Populate event choices
    approved_events = Event.query.filter_by(status='Approved').order_by(Event.date.desc()).all()
    form.event_id.choices = [('', '-- None --')] + [(e.id, f'{e.name} ({e.date.strftime("%Y-%m-%d")})') for e in approved_events]

    if form.validate_on_submit():
        # Custom validation for passenger count against bus capacity
        if form.number_of_passengers.data and form.number_of_passengers.data > bus.capacity:
            flash(f'Number of passengers ({form.number_of_passengers.data}) exceeds bus capacity ({bus.capacity}).', 'danger')
            return render_template('book_bus_form.html', bus=bus, form=form)

        new_booking = BusBooking(
            bus_id=bus.id,
            student_id=current_user.id,
            requested_date=form.requested_date.data,
            pickup_time=form.pickup_time.data,
            pickup_location=form.pickup_location.data,
            destination=form.destination.data,
            number_of_passengers=form.number_of_passengers.data,
            purpose=form.purpose.data,
            event_id=form.event_id.data,
            status='Pending',
            timestamp=datetime.now(UTC)
        )
        db.session.add(new_booking)
        db.session.commit()
        flash(f"Bus booking request for '{bus.identifier}' submitted successfully!", 'success')
        return redirect(url_for('my_bus_bookings'))

    return render_template('book_bus_form.html', bus=bus, form=form)

@app.route('/my_bus_bookings')
@login_required
def my_bus_bookings():
    bookings = BusBooking.query.filter_by(student_id=current_user.id).order_by(BusBooking.timestamp.desc()).all()
    return render_template('my_bus_bookings.html', bookings=bookings)

# Route to download the generated PDF certificate/ticket
@app.route('/download/certificate/<string:file_path>')
@login_required
def download_certificate(file_path):
    # Ensure the file path is safe and within the CERTIFICATES_FOLDER
    abs_path = os.path.join(app.root_path, file_path)
    if not os.path.exists(abs_path) or not abs_path.startswith(CERTIFICATES_FOLDER):
        abort(404, description="File not found or unauthorized access.")
    
    # Check if the current user is authorized to download this specific certificate
    # For event certificates:
    if 'event_certificate' in file_path:
        # Extract registration ID from filename or query database
        try:
            # Assuming filename format: event_certificate_{registration.id}_{ticket_id}.pdf
            reg_id_match = re.search(r'event_certificate_(\d+)_', os.path.basename(file_path))
            if reg_id_match:
                registration_id = int(reg_id_match.group(1))
                registration = Registration.query.get(registration_id)
                if registration and (registration.user_id == current_user.id or current_user.role == 'admin'): # Admin can download
                    return send_file(abs_path, as_attachment=True)
        except Exception as e:
            print(f"Error checking event certificate authorization: {e}")
            abort(403, description="Unauthorized to access this certificate.")
    
    # For bus tickets:
    elif 'bus_ticket' in file_path:
        # Extract booking ID from filename or query database
        try:
            # Assuming filename format: bus_ticket_{booking.id}.pdf
            booking_id_match = re.search(r'bus_ticket_(\d+).pdf', os.path.basename(file_path))
            if booking_id_match:
                booking_id = int(booking_id_match.group(1))
                booking = BusBooking.query.get(booking_id)
                if booking and (booking.student_id == current_user.id or current_user.role == 'admin'): # Admin can download
                    return send_file(abs_path, as_attachment=True)
        except Exception as e:
            print(f"Error checking bus ticket authorization: {e}")
            abort(403, description="Unauthorized to access this ticket.")

    abort(403, description="Unauthorized to access this document.")


# --- Event Details and Registration Routes ---
@app.route("/event/<int:event_id>")
def event_details(event_id):
    event = Event.query.get_or_404(event_id)
    registration_form = RegisterForEventForm()

    is_registered = False
    if current_user.is_authenticated:
        existing_registration = Registration.query.filter_by(
            user_id=current_user.id,
            event_id=event.id
        ).first()
        if existing_registration:
            is_registered = True

    current_registrations = Registration.query.filter_by(event_id=event.id).count()
    remaining_capacity = None
    if event.capacity is not None:
        remaining_capacity = event.capacity - current_registrations

    return render_template(
        'event_details.html',
        title=event.name,
        event=event,
        registration_form=registration_form,
        is_registered=is_registered,
        remaining_capacity=remaining_capacity
    )


@app.route("/event/<int:event_id>/register", methods=['POST'])
@login_required
def register_for_event(event_id):
    event = Event.query.get_or_404(event_id)
    form = RegisterForEventForm()

    if form.validate_on_submit():
        existing_registration = Registration.query.filter_by(
            user_id=current_user.id,
            event_id=event.id
        ).first()

        if existing_registration:
            flash('You are already registered for this event!', 'warning')
            return redirect(url_for('event_details', event_id=event.id))

        if event.capacity is not None:
            current_registrations = Registration.query.filter_by(event_id=event.id).count()
            if current_registrations >= event.capacity:
                flash('Sorry, this event is at full capacity!', 'danger')
                return redirect(url_for('event_details', event_id=event.id))

        ticket_id = None
        payment_status = 'N/A'

        if event.price > 0:
            payment_status = 'pending'
            flash(f'Event requires payment. Proceed to payment for {event.name}. (Payment simulation: Current status is {payment_status})', 'info')
        else:
            payment_status = 'paid'
            ticket_id = str(uuid.uuid4())

        new_registration = Registration(
            user_id=current_user.id,
            event_id=event.id,
            ticket_id=ticket_id,
            payment_status=payment_status
        )
        db.session.add(new_registration)
        db.session.commit() # Commit here to get new_registration.id for filename

        if payment_status == 'paid' or event.price == 0:
            # Generate event certificate PDF
            qr_data = f"Event: {event.name}\nAttendee: {current_user.username}\nTicket ID: {new_registration.ticket_id}"
            qr_code_base64 = generate_qr_code_base64(qr_data)
            
            certificate_filename = f"event_certificate_{new_registration.id}_{new_registration.ticket_id}.pdf"
            certificate_path = generate_pdf_from_template(
                'event_certificate_template.html',
                certificate_filename,
                context={
                    'user': current_user,
                    'event': event,
                    'registration': new_registration,
                    'qr_code_base64': qr_code_base64,
                    'now': datetime.now(UTC)
                }
            )
            if certificate_path:
                new_registration.certificate_path = os.path.relpath(certificate_path, app.root_path)
                new_registration.certificate_generated_at = datetime.now(UTC)
                flash(f"Event certificate generated at {certificate_path}", 'info')
            else:
                flash("Failed to generate event certificate PDF.", 'danger')

            db.session.commit() # Commit again to save certificate_path
            flash(f'Successfully registered for {event.name}! Your ticket ID is: {new_registration.ticket_id}', 'success')
            send_confirmation_email(current_user.email, event, new_registration)
        else:
            flash(f'Your registration for {event.name} is pending payment. Please complete payment to confirm.', 'warning')
        return redirect(url_for('my_event_registrations'))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {field}: {error}", 'danger')
        return redirect(url_for('event_details', event_id=event.id))

@app.route("/my_event_registrations")
@login_required
def my_event_registrations():
    registrations = Registration.query.filter_by(user_id=current_user.id).all()
    return render_template('my_event_registrations.html', title='My Event Registrations', registrations=registrations)


# New routes for viewing and managing notifications
@app.route('/notifications')
@login_required
def notifications():
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
    # Mark all unread notifications as read when viewed
    unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    for notif in unread_notifications:
        notif.is_read = True
    db.session.commit()
    return render_template('notifications.html', notifications=user_notifications)

@app.route('/mark_notification_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    notification.is_read = True
    db.session.commit()
    flash('Notification marked as read.', 'info')
    return redirect(url_for('notifications'))

@app.context_processor
def inject_unread_notifications_count():
    if current_user.is_authenticated:
        unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return dict(unread_notifications_count=unread_count)
    return dict(unread_notifications_count=0)

# Add this context processor to app.py
@app.context_processor
def inject_now():
    return {'now': datetime.now(UTC)} # Make current UTC time available in templates


# --- Main Execution ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Initialize and start the scheduler when the app runs
        scheduler.init_app(app)
        scheduler.start()
        # Add the reminder job to run every 6 hours
        if not scheduler.get_job('send_reminders'):
            scheduler.add_job(id='send_reminders', func=send_event_reminders, trigger='interval', seconds=21600)
    app.run(debug=True)
