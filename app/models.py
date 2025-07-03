from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)


class Organizer(db.Model, UserMixin):
    __tablename__ = 'organizers'
    id = db.Column(db.Integer, primary_key=True)
    association_name = db.Column(db.String(120), nullable=False)
    person_name = db.Column(db.String(120), nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    username = db.Column(db.String(64), unique=True)
    password = db.Column(db.String(200))
    approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_temp_password = db.Column(db.Boolean, default=True)

class SwimRace(db.Model):
    __tablename__ = 'swim_race'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g., "50m Freestyle"
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))  # link to the Meet/Event
    age_group = db.Column(db.String(20))
    gender = db.Column(db.String(20))


class Swimmer(db.Model, UserMixin):
    __tablename__ = 'swimmer'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20), unique=True, index=True, info={'constraint_name': 'uq_swimmer_phone'})
    password_hash = db.Column(db.String(200))
    verification_code = db.Column(db.String(6))
    is_verified = db.Column(db.Boolean, default=False)

    gender = db.Column(db.String(20))
    dob = db.Column(db.String(20)) 
    emergency_name = db.Column(db.String(100))
    emergency_contact = db.Column(db.String(20))
    address = db.Column(db.Text)
    sfi_number = db.Column(db.String(50))
    aadhaar_file = db.Column(db.String(200))
    sfi_file = db.Column(db.String(200))
    event_registrations = db.relationship('SwimmerEventRegistration', back_populates='swimmer')
#http://127.0.0.1:5000/admin-clear-all


class PublishedEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(120), nullable=False)
    place = db.Column(db.String(120), nullable=False)
    start_date = db.Column(db.String(20), nullable=False)
    end_date = db.Column(db.String(20), nullable=False)
    age_groups = db.Column(db.Text, nullable=False)  # JSON string or comma-separated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# app/models.py


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    place = db.Column(db.String(120))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    age_groups = db.Column(db.Text)
    registration_start_date = db.Column(db.Date, nullable=True)
    registration_end_date = db.Column(db.Date, nullable=True)
    level = db.Column(db.String(50))
    status = db.Column(db.String(20))
    association_name = db.Column(db.String(200)) 
    organizer_id = db.Column(db.Integer, db.ForeignKey('organizers.id'), nullable=False)
    organizer = db.relationship('Organizer', backref='events')
    selected_events_json = db.Column(db.Text)
    event_schedule_json = db.Column(db.Text, nullable=True)
    visibility = db.Column(db.String(20))
    full_title = db.Column(db.String(500))
    max_individual_events = db.Column(db.Integer, nullable=True)
    n_lanes = db.Column(db.Integer, nullable=True)





class DraftEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey('organizers.id'))
    event_name = db.Column(db.String(120))
    place = db.Column(db.String(120))
    start_date = db.Column(db.String(20))
    end_date = db.Column(db.String(20))
    age_groups = db.Column(db.Text)  # Store JSON list as string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SwimmerEventRegistration(db.Model):
    __tablename__ = 'swimmer_event_registration'
    id = db.Column(db.Integer, primary_key=True)
    
    swimmer_id = db.Column(db.Integer, db.ForeignKey('swimmer.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)  # the meet
    meet_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)

    swim_race_id = db.Column(db.Integer, db.ForeignKey('swim_race.id'))  # NEW
    swim_race = db.relationship('SwimRace', backref='registrations')     # NEW

    swimmer = db.relationship('Swimmer', back_populates='event_registrations')
    event = db.relationship('Event', foreign_keys=[event_id], backref='swimmer_registrations')
    meet = db.relationship('Event', foreign_keys=[meet_id])
    best_time = db.Column(db.String(20))  
    age_group_choices = db.Column(db.Text)