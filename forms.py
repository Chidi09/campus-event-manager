# forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, IntegerField, SubmitField, DateTimeLocalField, PasswordField, SelectField, DateField, TimeField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Email, EqualTo, ValidationError
from datetime import datetime

class EventForm(FlaskForm):
    name = StringField('Event Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Description', validators=[DataRequired()])
    # Use DateTimeLocalField for a datetime picker in HTML5
    # format='%Y-%m-%dT%H:%M' is crucial for proper browser rendering
    date = DateTimeLocalField('Date and Time', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired(), Length(min=2, max=100)])
    price = FloatField('Ticket Price (USD)', validators=[Optional(), NumberRange(min=0)]) # Optional for free events
    capacity = IntegerField('Capacity (Leave blank for unlimited)', validators=[Optional(), NumberRange(min=1)])
    submit = SubmitField('Create Event')

class RegisterForEventForm(FlaskForm):
    # We won't need many fields here as the event and user are determined by context
    submit = SubmitField('Register for Event')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    role = SelectField(
        'Role',
        choices=[('student', 'Student')],  # Only student visible
        validators=[DataRequired()]
    )
    submit = SubmitField('Register')

    def validate_username(self, username):
        from app import User
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is already taken. Please choose a different one.')

    def validate_email(self, email):
        from app import User
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered. Please use a different one or log in.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CreateStaffForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    role = SelectField('Staff Role', choices=[
        ('dsa', 'DSA'),
        ('vc_office', 'VC Office')
    ], validators=[DataRequired()])
    submit = SubmitField('Create Staff Account')

    def validate_username(self, username):
        from app import User
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is already taken. Please choose a different one.')

    def validate_email(self, email):
        from app import User
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered. Please use a different one.')

class HallForm(FlaskForm):
    name = StringField('Hall Name', validators=[DataRequired()])
    capacity = IntegerField('Capacity', validators=[DataRequired(), NumberRange(min=1)])
    location_details = TextAreaField('Location Details')
    submit = SubmitField('Add Hall')

class BusForm(FlaskForm):
    identifier = StringField('Bus Identifier (e.g., Reg No, Name)', validators=[DataRequired(), Length(max=100)])
    capacity = IntegerField('Capacity', validators=[DataRequired(), NumberRange(min=1)])
    driver_contact = StringField('Driver Contact (Optional)', validators=[Optional(), Length(max=100)])
    route_details = TextAreaField('Route/Availability Details (Optional)', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Add Bus')

class HallBookingForm(FlaskForm):
    requested_date = DateField('Requested Date', validators=[DataRequired()])
    start_time = TimeField('Start Time', validators=[DataRequired()])
    end_time = TimeField('End Time', validators=[DataRequired()])
    purpose = TextAreaField('Purpose of Booking', validators=[DataRequired()])
    # Modified event_id to handle empty string for Optional field
    event_id = SelectField(
        'Link to an Event (Optional)',
        coerce=lambda x: int(x) if x else None, # Convert '' to None
        validators=[Optional()]
    )
    submit = SubmitField('Submit Booking Request')

    def validate_end_time(self, field):
        if self.start_time.data and field.data:
            if field.data <= self.start_time.data:
                raise ValidationError('End time must be after start time.')

class RsvpForm(FlaskForm):
    submit = SubmitField('RSVP')

class BusBookingForm(FlaskForm):
    requested_date = DateField('Requested Date', validators=[DataRequired()])
    pickup_time = TimeField('Pickup Time', validators=[DataRequired()])
    pickup_location = StringField('Pickup Location', validators=[DataRequired(), Length(max=200)])
    destination = StringField('Destination', validators=[DataRequired(), Length(max=200)])
    number_of_passengers = IntegerField('Number of Passengers (Optional)', validators=[Optional(), NumberRange(min=1)])
    purpose = TextAreaField('Purpose of Booking', validators=[DataRequired(), Length(max=1000)])
    # Modified event_id to handle empty string for Optional field
    event_id = SelectField(
        'Link to an Event (Optional)',
        coerce=lambda x: int(x) if x else None, # Convert '' to None
        validators=[Optional()]
    )
    submit = SubmitField('Submit Booking Request')
