from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

# Import db from the extensions module
from extensions import db

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')

    hall_bookings_made = db.relationship('HallBooking', foreign_keys='HallBooking.student_id', backref='requester', lazy='dynamic')
    bus_bookings_made = db.relationship('BusBooking', foreign_keys='BusBooking.student_id', backref='requester', lazy='dynamic')
    
    registrations = db.relationship('Registration', backref='user', lazy=True)
    
    events_dsa_approved = db.relationship('Event', foreign_keys='Event.dsa_approver_id', back_populates='dsa_approver', lazy=True)
    events_vc_approved = db.relationship('Event', foreign_keys='Event.vc_approver_id', back_populates='vc_approver', lazy=True)
    # Corrected: Refer to Event.created_by directly
    created_events = db.relationship('Event', foreign_keys='Event.created_by', back_populates='creator', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_rsvpd(self, event_id):
        return Registration.query.filter_by(user_id=self.id, event_id=event_id).first() is not None

    def __repr__(self):
        return f'<User {self.username} ({self.email}) - {self.role}>'

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)  # <-- Unified date + time field
    location = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, default=0.0)
    capacity = db.Column(db.Integer)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_event_created_by'), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    status = db.Column(db.String(50), nullable=False, default='Pending DSA Approval')
    dsa_approver_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_event_dsa_approver_id'), nullable=True)
    vc_approver_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_event_vc_approver_id'), nullable=True)

    dsa_approver = db.relationship('User', foreign_keys=[dsa_approver_id], back_populates='events_dsa_approved', lazy=True, primaryjoin="Event.dsa_approver_id == User.id")
    vc_approver = db.relationship('User', foreign_keys=[vc_approver_id], back_populates='events_vc_approved', lazy=True, primaryjoin="Event.vc_approver_id == User.id")
    creator = db.relationship('User', back_populates='created_events', foreign_keys=[created_by])

    registrations = db.relationship('Registration', backref='event', lazy=True)

    reminder_sent = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"Event('{self.name}', '{self.date}', '{self.status}')"

class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_registration_user_id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', name='fk_registration_event_id'), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    ticket_id = db.Column(db.String(50), unique=True, nullable=True)
    payment_status = db.Column(db.String(20), default='pending')
    certificate_path = db.Column(db.String(255), nullable=True)
    certificate_generated_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"Registration('{self.user_id}', '{self.event_id}')"

class Hall(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    location_details = db.Column(db.Text, nullable=True)
    bookings = db.relationship('HallBooking', backref='hall', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Hall {self.name}>'

class HallBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hall_id = db.Column(db.Integer, db.ForeignKey('hall.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)
    requested_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    processed_by_admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    processed_timestamp = db.Column(db.DateTime, nullable=True)
    admin_remarks = db.Column(db.Text, nullable=True)
    processor = db.relationship('User', foreign_keys=[processed_by_admin_id], lazy='select')

    def __repr__(self):
        return f'<HallBooking ID {self.id} for Hall {self.hall_id} by User {self.student_id}>'

class Bus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(100), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    driver_contact = db.Column(db.String(100), nullable=True)
    route_details = db.Column(db.Text, nullable=True)
    bookings = db.relationship('BusBooking', backref='bus', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Bus {self.identifier}>'

class BusBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bus_id = db.Column(db.Integer, db.ForeignKey('bus.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)
    requested_date = db.Column(db.Date, nullable=False)
    pickup_time = db.Column(db.Time, nullable=False)
    pickup_location = db.Column(db.String(200), nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    number_of_passengers = db.Column(db.Integer, nullable=True)
    purpose = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    processed_by_admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    processed_timestamp = db.Column(db.DateTime, nullable=True)
    admin_remarks = db.Column(db.Text, nullable=True)
    processor = db.relationship('User', foreign_keys=[processed_by_admin_id], lazy='select')
    certificate_path = db.Column(db.String(255), nullable=True) # Added for bus tickets
    certificate_generated_at = db.Column(db.DateTime, nullable=True) # Added for bus tickets

    def __repr__(self):
        return f'<BusBooking ID {self.id} for Bus {self.bus_id} by User {self.student_id}>'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    notification_type = db.Column(db.String(50), nullable=True)
    related_id = db.Column(db.Integer, nullable=True)

    user = db.relationship('User', backref=db.backref('notifications', lazy=True))

    def __repr__(self):
        return f"Notification('{self.user.username}', '{self.message[:30]}...', Read: {self.is_read})"
