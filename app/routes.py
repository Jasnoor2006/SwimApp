import os
import json
import random
import re
import smtplib
from app import app, db
from app.utils import generate_event_schedule, generate_event_pdf, generate_verification_code, send_email_verification, send_sms_verification
from flask import Flask, render_template, redirect, url_for, flash, request, session, abort, current_app, send_file, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, login_required, current_user 
from app.forms import OrganizerSignupForm, SwimmerProfileForm , SwimmerLoginForm, SwimmerVerificationForm, CreateEventForm, OrganizerProfileForm, RescheduleForm, AdminLoginForm, OrganizerLoginForm, NewPasswordForm, AdminProfileForm, SwimmerRegisterForm
from app.models import Organizer, Swimmer, Admin, Event, PublishedEvent, SwimmerEventRegistration, SwimRace
from datetime import datetime, timedelta, date
from email.message import EmailMessage







ADMIN_EMAIL = "jasnoor.tgs@gmail.com"
ADMIN_PASSWORD = "jasnoor@29"

UPLOAD_FOLDER = 'static/profile_pics'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from datetime import datetime

@app.route('/')
def home():
    today = datetime.today().date()
    published_events = Event.query.filter(
        Event.status == "Published",
        Event.start_date >= today
    ).order_by(Event.start_date).all()
    return render_template('home.html', published_events=published_events)


from flask import request  # Make sure this is imported at the top

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    form = AdminLoginForm()
    
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))

    if form.validate_on_submit():
        username_input = form.username.data.strip()
        password_input = form.password.data.strip()

        print("Submitted username:", repr(username_input))
        print("Submitted password:", repr(password_input))

        admin = Admin.query.filter_by(username=username_input).first()
        if admin:
            if check_password_hash(admin.password, password_input):
                login_user(admin)
                session['role'] = 'admin' 
                flash("Admin logged in successfully!", "success")
                return redirect(url_for('admin_dashboard'))
            else:
                flash("Password incorrect", "danger")
        else:
            flash("Admin not found", "danger")
    
    elif request.method == 'POST':
        flash("Form not valid", "danger")

    return render_template('admin_login.html', form=form)


@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    organizers = Organizer.query.all()
    return render_template('admin_dashboard.html', organizers=organizers)


@app.route('/logout')
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

@app.route('/organizer-signup', methods=['GET', 'POST'])
def organizer_signup():
    form = OrganizerSignupForm()
    if form.validate_on_submit():
        existing = Organizer.query.filter_by(email=form.email.data).first()
        if existing:
            flash("Email already registered. Please wait for approval.", "warning")
            return redirect(url_for('organizer_signup'))

        new_org = Organizer(
            association_name=form.association_name.data,
            person_name=form.person_name.data,
            contact=form.contact.data,
            email=form.email.data,
            address=form.address.data,
            approved=False
        )

        db.session.add(new_org)
        db.session.flush()

        new_org.username = generate_username(new_org.association_name, new_org.id)
        db.session.commit()

        send_admin_notification_email(new_org)
        return render_template('approval_confirmation.html')

    return render_template('organizer_signup.html', form=form)



def send_admin_notification_email(organizer):
    try:
        with open('admin_data.json', 'r') as f:
            data = json.load(f)
            admin_email = data.get("email", ADMIN_EMAIL)
    except:
        admin_email = ADMIN_EMAIL

    msg = EmailMessage()
    msg['Subject'] = 'New Organizer Signup Request'
    msg['From'] = 'jasnoor.tgs@gmail.com'
    msg['To'] = admin_email
    msg.set_content(f'''
New organizer signup request:

Association: {organizer.association_name}
Name: {organizer.person_name}
Email: {organizer.email}
Contact: {organizer.contact}
Address: {organizer.address}

Visit the admin dashboard to approve.
''')

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login('jasnoor.tgs@gmail.com', 'zbvqndpaegmuipjv')
        smtp.send_message(msg)

def generate_username(club_name, organizer_id):
    base = re.sub(r'[^a-zA-Z0-9]', '', club_name.lower())[:8]
    return f"{base}{organizer_id}"

@app.route('/approve-organizer/<int:id>')
@login_required
def approve_organizer(id):
    org = Organizer.query.get_or_404(id)
    org.approved = True
    db.session.commit()
    send_organizer_approval_email(org)
    flash(f"Organizer {org.person_name} approved.", "success")
    return redirect(url_for('admin_dashboard'))

def send_organizer_approval_email(organizer):
    msg = EmailMessage()
    msg['Subject'] = 'Your Organizer Account Has Been Approved'
    msg['From'] = 'jasnoor.tgs@gmail.com'
    msg['To'] = organizer.email

    # Generate the set-password URL
    set_password_url = f"http://127.0.0.1:5000/set-password/{organizer.id}"

    msg.set_content(f'''
Hi {organizer.person_name},

Your organizer account for SwimApp has been approved!

Username: {organizer.username}

To get started, please set your password by clicking the link below:
{set_password_url}

Thank you,
SwimApp Admin
''')

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login('jasnoor.tgs@gmail.com', 'zbvqndpaegmuipjv')
        smtp.send_message(msg)

@app.route('/set-password/<int:organizer_id>', methods=['GET', 'POST'])
def set_password(organizer_id):
    organizer = Organizer.query.get_or_404(organizer_id)
    form = NewPasswordForm()

    if request.method == 'POST' and form.validate_on_submit():
        new_password = form.new_password.data
        organizer.password = generate_password_hash(new_password)
        organizer.is_temp_password = False
        db.session.commit()
        flash('Password set successfully.', 'success')
        login_user(organizer)
        session['role'] = 'organizer'
        return redirect(url_for('organizer_dashboard'))

    return render_template('set_password.html', form=form, organizer=organizer)

@app.route('/organizer-login', methods=['GET', 'POST'])
def organizer_login():
    form = OrganizerLoginForm()
    if form.validate_on_submit():
        organizer = Organizer.query.filter_by(username=form.username.data).first()

        if organizer:
            if not organizer.approved:
                flash("Your account is currently disapproved by the admin.", "danger")
                return redirect(url_for('organizer_login'))

            if not organizer.password:
                flash("You must set your password before logging in.", "danger")
                return redirect(url_for('organizer_login'))

            if check_password_hash(organizer.password, form.password.data):
                login_user(organizer)
                session['role'] = 'organizer'
                if organizer.is_temp_password:
                    return redirect(url_for('set_password', organizer_id=organizer.id))

                flash("Login successful!", "success")
                return redirect(url_for('organizer_dashboard'))

        flash("Invalid credentials.", "danger")
    return render_template('organizer_login.html', form=form)

@app.route('/organizer-dashboard')
@login_required
def organizer_dashboard():
    form = OrganizerProfileForm()
    form.person_name.data = current_user.person_name
    events = Event.query.filter_by(organizer_id=current_user.id).all()
    return render_template('organizer_dashboard.html', form=form, events=events)



@app.route('/admin-profile', methods=['GET', 'POST'])
@login_required
def admin_profile():
    form = AdminProfileForm()
    data_file = 'admin_data.json'
    admin_name = "Admin"

    if request.method == 'GET' or not form.validate_on_submit():
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                form.name.data = data.get('name', 'Jasnoor Kaur')
                form.email.data = data.get('email', 'jasnoor.tgs@gmail.com')
                form.notifications.data = data.get('notifications', True)
                admin_name = form.name.data
    else:
        if form.password.data and form.password.data != form.confirm_password.data:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('admin_profile'))

        new_data = {
            'name': form.name.data,
            'email': form.email.data,
            'notifications': form.notifications.data
        }

        if form.profile_picture.data and allowed_file(form.profile_picture.data.filename):
            filename = secure_filename(form.profile_picture.data.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            form.profile_picture.data.save(filepath)
            new_data['profile_picture'] = f"profile_pics/{filename}"

        with open(data_file, 'w') as f:
            json.dump(new_data, f)

        flash("Profile updated successfully!", "success")
        form.name.data = new_data["name"]
        form.email.data = new_data["email"]
        form.notifications.data = new_data["notifications"]
        admin_name = new_data["name"]

    return render_template('admin_profile.html', form=form, admin_name=admin_name)

@app.route('/toggle-approval/<int:id>')
@login_required
def toggle_approval(id):
    organizer = Organizer.query.get_or_404(id)
    organizer.approved = not organizer.approved
    db.session.commit()

    if organizer.approved:
        send_organizer_approval_email(organizer)
        flash(f"{organizer.person_name} has been approved and notified.", "success")
    else:
        flash(f"{organizer.person_name} has been disapproved.", "info")

    return redirect(url_for('admin_dashboard'))

@app.route('/delete-organizer/<int:id>')
@login_required
def delete_organizer(id):
    org = Organizer.query.get_or_404(id)
    db.session.delete(org)
    db.session.commit()
    flash(f"Organizer {org.person_name} has been removed.", "warning")
    return redirect(url_for('admin_dashboard'))

@app.context_processor
def inject_admin_info():
    try:
        with open('admin_data.json', 'r') as f:
            data = json.load(f)
            return dict(
                admin_name=data.get("name", "Admin"),
                admin_picture=data.get("profile_picture", "profile_pics/default.png")
            )
    except:
        return dict(admin_name="Admin", admin_picture="profile_pics/default.png")

@app.route('/organizer-profile', methods=['GET', 'POST'])
@login_required
def organizer_profile():
    if current_user.__class__.__name__ != 'Organizer':
        abort(403)

    form = OrganizerProfileForm(obj=current_user)  # ✅ auto-fill fields

    if form.validate_on_submit():  # ✅ handle form submission
        current_user.person_name = form.person_name.data
        current_user.association_name = form.association_name.data
        current_user.email = form.email.data
        current_user.contact = form.contact.data
        current_user.address = form.address.data

        db.session.commit()  # ✅ save to DB
        flash("Profile updated successfully.")
        return redirect(url_for('organizer_profile'))

    return render_template("organizer_profile.html", form=form)


@app.route('/events')
@login_required
def events():
    return render_template('events.html')

@app.route('/create-event', methods=['GET', 'POST'])
@login_required
def create_event():
    form = CreateEventForm()

    # Prefill form from session
    if request.method == 'GET' and 'event_id' in session:
        form.event_name.data = session.get('event_name')
        form.place.data = session.get('place')
        form.association_name.data = session.get('association_name')
        form.age_groups.data = session.get('age_groups', [])
        level_raw = session.get('level', '')
        form.meet_levels.data = [lvl.strip() for lvl in level_raw.split(',')] if level_raw else []
        form.max_individual_events.data = session.get('max_individual_events')
        start_date_str = session.get('start_date')
        end_date_str = session.get('end_date')
        reg_start_str = session.get('registration_start_date')
        reg_end_str = session.get('registration_end_date')

        if start_date_str:
            form.start_date.data = datetime.strptime(start_date_str, '%d/%m/%Y')
        if end_date_str:
            form.end_date.data = datetime.strptime(end_date_str, '%d/%m/%Y')
        if reg_start_str:
            form.registration_start_date.data = datetime.strptime(reg_start_str, '%d/%m/%Y')
        if reg_end_str:
            form.registration_end_date.data = datetime.strptime(reg_end_str, '%d/%m/%Y')

    if form.validate_on_submit():
        # Get form data
        event_name = form.event_name.data
        place = form.place.data
        association_name = form.association_name.data
        start_date_obj = form.start_date.data
        end_date_obj = form.end_date.data
        reg_start = form.registration_start_date.data
        reg_end = form.registration_end_date.data
        selected_groups = form.age_groups.data
        custom_age_groups = request.form.getlist('custom_age_groups')
        selected_levels = form.meet_levels.data
        organizer_id=current_user.id
        max_individual = form.max_individual_events.data


        if not start_date_obj or not end_date_obj:
            flash("Please select valid start and end dates.")
            return render_template('create_event.html', form=form)

        num_days = (end_date_obj - start_date_obj).days + 1
        all_age_groups = selected_groups + custom_age_groups
        level = selected_levels[0] if selected_levels else "Not specified"

        # ✅ Now create the event with age_groups
        new_event = Event(
            name=event_name,
            place=place,
            start_date=start_date_obj,
            end_date=end_date_obj,
            level=level,
            status="Draft",
            organizer_id=current_user.id,
            association_name=association_name,
            registration_start_date=reg_start,
            registration_end_date=reg_end,
            age_groups=','.join(all_age_groups),
            max_individual_events=max_individual

        )

        db.session.add(new_event)
        db.session.commit()

        # Store in session
        session['event_id'] = new_event.id
        session['event_name'] = event_name
        session['place'] = place
        session['start_date'] = start_date_obj.strftime('%d/%m/%Y')
        session['end_date'] = end_date_obj.strftime('%d/%m/%Y')
        session['registration_start_date'] = reg_start.strftime('%d/%m/%Y')
        session['registration_end_date'] = reg_end.strftime('%d/%m/%Y')
        session['num_days'] = num_days
        session['level'] = level
        session['age_groups'] = all_age_groups
        session['custom_age_groups'] = custom_age_groups
        session['association_name'] = association_name
        session['max_individual_events'] = max_individual


        return redirect(url_for('create_event_step_2'))

    if form.errors:
        print("Form Errors:", form.errors)

    return render_template('create_event.html', form=form)


@app.route('/create-event-step-2', methods=['GET', 'POST'])
@login_required
def create_event_step_2():
    age_groups = session.get('age_groups', [])
    event_id = session.get('event_id')
    selected_events = session.get('selected_events', {})
    if not event_id:
        flash("Event not found.")
        return redirect(url_for('create_event'))

    event_map = {
    "senior_men": [
        "50 m Freestyle", "100 m Freestyle", "200 m Freestyle", "400 m Freestyle",
        "800 m Freestyle", "1500 m Freestyle",
        "50 m Backstroke", "100 m Backstroke", "200 m Backstroke",
        "50 m Breaststroke", "100 m Breaststroke", "200 m Breaststroke",
        "50 m Butterfly", "100 m Butterfly", "200 m Butterfly",
        "200 m Individual Medley", "400 m Individual Medley",
        "4 x 100 m Freestyle Relay", "4 x 200 m Freestyle Relay", 
        "4 x 100 m Medley Relay", "4 x 200 m Freestyle Relay Mixed", 
        "4 x 100 m Freestyle Relay Mixed", "4 x 50 m Freestyle Relay Mixed", 
        "4 x 100 m Medley Relay Mixed", "4 x 50 m Medley Relay Mixed"
    ],
    "senior_women": [
        "50 m Freestyle", "100 m Freestyle", "200 m Freestyle", "400 m Freestyle",
        "800 m Freestyle", "1500 m Freestyle",
        "50 m Backstroke", "100 m Backstroke", "200 m Backstroke",
        "50 m Breaststroke", "100 m Breaststroke", "200 m Breaststroke",
        "50 m Butterfly", "100 m Butterfly", "200 m Butterfly",
        "200 m Individual Medley", "400 m Individual Medley",
        "4 x 100 m Freestyle Relay", "4 x 200 m Freestyle Relay", "4 x 100 m Medley Relay"
    ],
    "u19_boys": [
        "50 m Freestyle", "100 m Freestyle", "200 m Freestyle", "400 m Freestyle",
        "800 m Freestyle", "1500 m Freestyle",
        "50 m Backstroke", "100 m Backstroke", "200 m Backstroke",
        "50 m Breaststroke", "100 m Breaststroke", "200 m Breaststroke",
        "50 m Butterfly", "100 m Butterfly", "200 m Butterfly",
        "200 m Individual Medley", "400 m Individual Medley",
        "4 x 100 m Freestyle Relay", "4 x 200 m Freestyle Relay", "4 x 100 m Medley Relay"
    ],
    "u19_girls": [
        "50 m Freestyle", "100 m Freestyle", "200 m Freestyle", "400 m Freestyle",
        "800 m Freestyle", "1500 m Freestyle",
        "50 m Backstroke", "100 m Backstroke", "200 m Backstroke",
        "50 m Breaststroke", "100 m Breaststroke", "200 m Breaststroke",
        "50 m Butterfly", "100 m Butterfly", "200 m Butterfly",
        "200 m Individual Medley", "400 m Individual Medley",
        "4 x 100 m Freestyle Relay", "4 x 200 m Freestyle Relay", "4 x 100 m Medley Relay"
    ],
    "u18_boys": [
        "50 m Freestyle", "100 m Freestyle", "200 m Freestyle", "400 m Freestyle",
        "800 m Freestyle", "1500 m Freestyle",
        "50 m Backstroke", "100 m Backstroke", "200 m Backstroke",
        "50 m Breaststroke", "100 m Breaststroke", "200 m Breaststroke",
        "50 m Butterfly", "100 m Butterfly", "200 m Butterfly",
        "200 m Individual Medley", "400 m Individual Medley",
        "4 x 100 m Freestyle Relay", "4 x 200 m Freestyle Relay", "4 x 100 m Medley Relay"
    ],
    "u18_girls": [
        "50 m Freestyle", "100 m Freestyle", "200 m Freestyle", "400 m Freestyle",
        "800 m Freestyle", "1500 m Freestyle",
        "50 m Backstroke", "100 m Backstroke", "200 m Backstroke",
        "50 m Breaststroke", "100 m Breaststroke", "200 m Breaststroke",
        "50 m Butterfly", "100 m Butterfly", "200 m Butterfly",
        "200 m Individual Medley", "400 m Individual Medley",
        "4 x 100 m Freestyle Relay", "4 x 200 m Freestyle Relay", "4 x 100 m Medley Relay"
    ],
    "u17_boys": [
        "50 m Freestyle", "100 m Freestyle", "200 m Freestyle", "400 m Freestyle",
        "50 m Backstroke", "100 m Backstroke",
        "50 m Breaststroke", "100 m Breaststroke",
        "50 m Butterfly", "100 m Butterfly",
        "200 m Individual Medley",
        "4 x 50 m Freestyle Relay", "4 x 50 m Medley Relay"
    ],
    "u17_girls": [
        "50 m Freestyle", "100 m Freestyle", "200 m Freestyle", "400 m Freestyle",
        "50 m Backstroke", "100 m Backstroke",
        "50 m Breaststroke", "100 m Breaststroke",
        "50 m Butterfly", "100 m Butterfly",
        "200 m Individual Medley",
        "4 x 50 m Freestyle Relay", "4 x 50 m Medley Relay"
    ],
    "u14_boys": [
        "50 m Freestyle", "100 m Freestyle",
        "50 m Backstroke", "100 m Backstroke",
        "50 m Breaststroke", "100 m Breaststroke",
        "50 m Butterfly", "100 m Butterfly",
        "200 m Individual Medley",
        "4 x 50 m Freestyle Relay", "4 x 50 m Medley Relay"
    ],
    "u14_girls": [
        "50 m Freestyle", "100 m Freestyle",
        "50 m Backstroke", "100 m Backstroke",
        "50 m Breaststroke", "100 m Breaststroke",
        "50 m Butterfly", "100 m Butterfly",
        "200 m Individual Medley",
        "4 x 50 m Freestyle Relay", "4 x 50 m Medley Relay"
    ],
    "u12_boys": [
        "50 m Freestyle", "100 m Freestyle",
        "50 m Backstroke", "100 m Backstroke",
        "50 m Breaststroke", "100 m Breaststroke",
        "50 m Butterfly", "100 m Butterfly",
        "200 m Individual Medley",
        "4 x 50 m Freestyle Relay", "4 x 50 m Medley Relay"
    ],
    "u12_girls": [
        "50 m Freestyle", "100 m Freestyle",
        "50 m Backstroke", "100 m Backstroke",
        "50 m Breaststroke", "100 m Breaststroke",
        "50 m Butterfly", "100 m Butterfly",
        "200 m Individual Medley",
        "4 x 50 m Freestyle Relay", "4 x 50 m Medley Relay"
    ],
    "u10_boys": [
        "25 m Freestyle", "50 m Freestyle",
        "25 m Backstroke", "50 m Backstroke",
        "25 m Breaststroke", "50 m Breaststroke",
        "25 m Butterfly", "50 m Butterfly",
        "4 x 50 m Freestyle Relay", "4 x 50 m Medley Relay"
    ],
    "u10_girls": [
        "25 m Freestyle", "50 m Freestyle",
        "25 m Backstroke", "50 m Backstroke",
        "25 m Breaststroke", "50 m Breaststroke",
        "25 m Butterfly", "50 m Butterfly",
        "4 x 50 m Freestyle Relay", "4 x 50 m Medley Relay"
    ],
    "u8_boys": [
        "25 m Freestyle", "50 m Freestyle",
        "25 m Backstroke", "50 m Backstroke",
        "25 m Breaststroke", "50 m Breaststroke",
        "25 m Butterfly", "50 m Butterfly",
        "4 x 50 m Freestyle Relay", "4 x 50 m Medley Relay"
    ],
    "u8_girls": [
        "25 m Freestyle", "50 m Freestyle",
        "25 m Backstroke", "50 m Backstroke",
        "25 m Breaststroke", "50 m Breaststroke",
        "25 m Butterfly", "50 m Butterfly",
        "4 x 50 m Freestyle Relay", "4 x 50 m Medley Relay"
    ]
}

    
    
    fallback_events = event_map.get("senior_men", [])
    filtered_events = {}

    for group in age_groups:
        if group.strip().lower() == "other":
            continue

        normalized_key = group.strip().lower().replace(" ", "_")
        if normalized_key in event_map:
            filtered_events[normalized_key] = event_map[normalized_key]

        else:
            filtered_events[group] = fallback_events
        
    if request.method == 'POST':
        try:
            selected_events = {
                key.replace("swim_events_", ""): request.form.getlist(key)
                for key in request.form
                if key.startswith('swim_events_')
        }

            if not selected_events:
                flash("Please select at least one event.")
                return redirect(url_for('create_event_step_2'))

        # ✅ Save to session for step 3
            session['selected_events'] = selected_events

        # ✅ Also save to the Event model in DB
            event = Event.query.get(event_id)
            if event:
                event.selected_events_json = json.dumps(selected_events)
                db.session.commit()

                for age_group, events in selected_events.items():
                    for name in events:
                        gender = "MIXED" if "Mixed" in name else ("MEN" if "boys" in age_group or "men" in age_group else "WOMEN")
                        race = SwimRace(
                            name=name.strip(),
                            age_group=age_group.upper(),
                            gender=gender.upper(),
                            event_id=event.id
                        )
                        db.session.add(race)

                db.session.commit()

            return redirect(url_for('create_event_step_3', event_id=event_id))

        except Exception as e:
            print("POST error in step 2:", e)
            return f"Error: {str(e)}", 500

    return render_template(
        'create_event_step_2.html',
        age_groups=list(filtered_events.keys()),
        age_group_events=filtered_events,
        selected_events=selected_events
    )
        




@app.route('/create-event-step-3', methods=['GET'])
@login_required 
def create_event_step_3():
    from datetime import datetime, timedelta

    age_groups = session.get('age_groups', [])
    start_date = session.get('start_date')
    num_days = session.get('num_days')
    selected_events = session.get('selected_events', {})
    event_id = session.get('event_id')
    print("event_id from session:", event_id)

    if not age_groups or not start_date or not num_days or not selected_events:
        flash("Missing data from previous steps.")
        return redirect(url_for('create_event'))

    start = datetime.strptime(start_date, '%d/%m/%Y')
    sessions = []
    for i in range(num_days):
        sessions.append({'day': (start + timedelta(days=i)).strftime('%A, %d %b %Y'), 'morning': [], 'evening': []})

    display_order = [
        ('senior_men', 'SENIOR MEN'),
        ('senior_women', 'SENIOR WOMEN'),
        ('u19_boys', 'U-19 BOYS'), ('u19_girls', 'U-19 GIRLS'),
        ('u18_boys', 'U-18 BOYS'), ('u18_girls', 'U-18 GIRLS'),
        ('u17_boys', 'U-17 BOYS'), ('u17_girls', 'U-17 GIRLS'),
        ('u14_boys', 'U-14 BOYS'), ('u14_girls', 'U-14 GIRLS'),
        ('u12_boys', 'U-12 BOYS'), ('u12_girls', 'U-12 GIRLS'),
        ('u10_boys', 'U-10 BOYS'), ('u10_girls', 'U-10 GIRLS'),
        ('u8_boys', 'U-8 BOYS'), ('u8_girls', 'U-8 GIRLS')
    ]

    males = [x for x in display_order if 'boys' in x[0] or 'men' in x[0]]
    females = [x for x in display_order if 'girls' in x[0] or 'women' in x[0]]
    display_order = [val for pair in zip(males, females) for val in pair]
    if len(males) > len(females):
        display_order += males[len(females):]
    elif len(females) > len(males):
        display_order += females[len(males):]

    event_map = []
    for key, label in display_order:
        if key in selected_events:
            for event in selected_events[key]:
                event_map.append((event.strip(), label))


    mixed_relays = [
        "4 x 200m Freestyle Relay Mixed",
        "4 x 100m Freestyle Relay Mixed",
        "4 x 50m Freestyle Relay Mixed",
        "4 x 50m Medley Relay Mixed",
        "4 x 100m Medley Relay Mixed"
    ]
    for event in mixed_relays:
        event_map.append((event.strip(), ""))

    def is_heat_final_event(event_name, days):
        m = re.match(r'^(\d+)', event_name)
        if not m: return False
        d = int(m.group(1))
        return d in ([50, 100] if days == 2 else [50, 100])

    def add_events(event_list, idx, time):
        added = set()
        mixed_queue = []

        for event_template in event_list:
            for ev, group in event_map:
                if ev == event_template:
                    key = f"{ev}_{group}_{time}"
                    if key in added: continue
                    stage = "(Heats)" if time == 'morning' and is_heat_final_event(ev, num_days) else \
                            "(Finals)" if time == 'evening' and is_heat_final_event(ev, num_days) else \
                            "(Timed Final)"
                    final_line = f"{ev} – {group} {stage}" if group else f"{ev} {stage}"

                    if 'Relay Mixed' in ev:
                        final_line = f"{ev} {stage}"
                    else:
                        final_line = f"{ev} – {group} {stage}" if group else f"{ev} {stage}"
                    if 'Mixed' in ev and time == 'evening':
                        mixed_queue.append(final_line)
                    else:
                        sessions[idx][time].append(final_line)
                    added.add(key)

        if time == 'evening':
            sessions[idx][time].extend(mixed_queue)

    schedule_2_day = {
        'day1_morning': ['1500 m Freestyle', '100 m Breaststroke', '200 m Freestyle', '100 m Backstroke',
                         '200 m Individual Medley', '50 m Freestyle', '200 m Butterfly', '50 m Breaststroke'],
        'day1_evening': ['800 m Freestyle', '100 m Breaststroke', '100 m Backstroke', '50 m Freestyle', '50 m Breaststroke',
                         '4 x 100 m Freestyle Relay', '4 x 50 m Freestyle Relay'],
        'day2_morning': ['400 m Freestyle', '100 m Butterfly', '50 m Backstroke', '200 m Breaststroke',
                         '100 m Freestyle', '200 m Backstroke', '400 m Individual Medley', '50 m Butterfly', '4 x 200 m Freestyle Relay'],
        'day2_evening': ['100 m Butterfly', '50 m Backstroke', '100 m Freestyle', '50 m Butterfly',
                         '4 x 100 m Medley Relay', '4 x 50 m Medley Relay']
    }

    schedule_3_day = {
        'day1_morning': ['800 m Freestyle', '200 m Individual Medley', '100 m Butterfly',
                         '200 m Backstroke', '50 m Freestyle', '50 m Breaststroke'],
        'day1_evening': ['100 m Butterfly', '50 m Freestyle', '50 m Breaststroke',
                         '4 x 100 m Freestyle Relay', '4 x 50 m Freestyle Relay', '4 x 200 m Freestyle Relay Mixed'],
        'day2_morning': ['400 m Freestyle', '50 m Backstroke', '200 m Breaststroke',
                         '100 m Freestyle', '200 m Butterfly'],
        'day2_evening': ['400 m Individual Medley', '50 m Backstroke', '100 m Freestyle', '50 m Butterfly',
                         '4 x 100 m Medley Relay', '4 x 50 m Medley Relay','4 x 100 m Freestyle Relay Mixed', '4 x 50 m Freestyle Relay Mixed' ],
        'day3_morning': ['1500 m Freestyle', '100 m Breaststroke', '200 m Freestyle',
                         '100 m Backstroke', '50 m Butterfly'],
        'day3_evening': ['100 m Breaststroke', '200 m Freestyle', '100 m Backstroke', '50 m Butterfly',
                         '4 x 200 m Freestyle Relay', '4 x 50 m Medley Relay Mixed', '4 x 100 m Medley Relay Mixed']
    }

    schedule = schedule_2_day if num_days == 2 else schedule_3_day if num_days == 3 else None
    if not schedule:
        flash("Only 2-day or 3-day event structures are supported.")
        return redirect(url_for('create_event'))

    for i in range(num_days):
        add_events(schedule.get(f'day{i+1}_morning', []), i, 'morning')
        add_events(schedule.get(f'day{i+1}_evening', []), i, 'evening')

    event_id = session.get('event_id')
    if not event_id:
        flash("Event ID missing.")
        return redirect(url_for('create_event'))

# 🔥 Convert to integer
    try:
        event_id = int(event_id)
    except ValueError:
        flash("Invalid event ID in session.")
        return redirect(url_for('create_event'))

    new_event = Event.query.get(event_id)
    if not new_event:
        flash("Event not found.")
        return redirect(url_for('create_event'))

    import json
    new_event.event_schedule_json = json.dumps(sessions)
    db.session.commit()

    session['sessions_data'] = sessions

    return render_template("create_event_step_3.html", sessions=sessions, event_id=new_event.id)


from app.pdf_generator import generate_event_pdf

import os

@app.route('/published-events')
@login_required
def published_events():
    published_events = Event.query.filter_by(organizer_id=current_user.id, status='Published').all()
    return render_template('published_events.html', published_events=published_events)


@app.route('/publish-event/<int:event_id>', methods=['POST'])
@login_required
def publish_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.organizer_id != current_user.id:
        flash("You are not authorized to publish this event.", "danger")
        return redirect(url_for('published_events'))

    visibility_choice = request.form.get("visibility")  # should be 'swimmer' or 'organizer'
    if visibility_choice not in ['swimmer', 'organizer']:
        flash("Invalid visibility option selected.", "danger")
        return redirect(url_for('published_events'))


    event.status = "Published"
    event.visibility = visibility_choice
    db.session.commit()

    # Generate PDF from session['sessions_data']
    from app.pdf_generator import generate_event_pdf

    event_data = {
        "name": event.name,
        "place": event.place,
        "start_date": event.start_date.strftime("%d %B %Y"),
        "end_date": event.end_date.strftime("%d %B %Y"),
        "level": event.level,
        "age_groups": session.get("age_groups", []),
        "association_name": event.association_name
    }

    schedule_data = session.get('sessions_data')


    os.makedirs("app/static/pdfs", exist_ok=True)

    pdf_path = os.path.join("app/static/pdfs", f"event_{event.id}.pdf")
    generate_event_pdf(event_data, schedule_data, pdf_path)

    flash("Event published and PDF generated!", "success")
    return redirect(url_for("published_events"))


  # make sure this is imported


@app.route('/swimmer-register', methods=['GET', 'POST'])
def swimmer_register():
    form = SwimmerRegisterForm()

    if form.validate_on_submit():
        if not form.email.data and not form.phone.data:
            flash("Please provide either an email or a phone number.", "danger")
            return redirect(url_for('swimmer_register'))

        if form.email.data:
            if Swimmer.query.filter_by(email=form.email.data).first():
                flash("Email already registered.", "danger")
                return redirect(url_for('swimmer_register'))

        if form.phone.data:
            if Swimmer.query.filter_by(phone=form.phone.data).first():
                flash("Phone already registered.", "danger")
                return redirect(url_for('swimmer_register'))

        verification_code = generate_verification_code()

        # Save temp swimmer info in session
        session['temp_swimmer'] = {
            "username": form.username.data,
            "name": form.name.data,
            "email": form.email.data or None,
            "phone": form.phone.data or None,
            "verification_code": verification_code
        }

        if form.email.data:
            send_email_verification(form.email.data, verification_code)
        elif form.phone.data:
            send_sms_verification(form.phone.data, verification_code)

        flash("A verification code has been sent. Please verify.", "info")
        return redirect(url_for('swimmer_verify'))

    return render_template('swimmer_register.html', form=form)



@app.route('/swimmer-verify', methods=['GET', 'POST'])
def swimmer_verify():
    form = SwimmerVerificationForm()

    if form.validate_on_submit():
        entered_code = form.code.data
        temp = session.get('temp_swimmer')

        if not temp:
            flash("Session expired. Please register again.", "warning")
            return redirect(url_for('swimmer_register'))

        if entered_code == temp['verification_code']:
            swimmer = Swimmer(
                name=temp['name'],
                username=temp['username'],
                email=temp['email'],
                phone=temp['phone'],
                verification_code=entered_code,
                is_verified=True
            )
            db.session.add(swimmer)
            db.session.commit()

            session['swimmer_id'] = swimmer.id
            session.pop('temp_swimmer', None)
            return redirect(url_for('swimmer_set_password'))
        else:
            flash("Invalid verification code.", "danger")

    return render_template('swimmer_verify.html', form=form)



@app.route('/swimmer-set-password', methods=['GET', 'POST'])
def swimmer_set_password():
    swimmer_id = session.get('swimmer_id')
    if not swimmer_id:
        flash("Session expired. Please register again.", "warning")
        return redirect(url_for('swimmer_register'))

    swimmer = Swimmer.query.get(swimmer_id)
    if not swimmer:
        flash("Invalid swimmer.", "danger")
        return redirect(url_for('swimmer_register'))

    form = NewPasswordForm()
    if form.validate_on_submit():
        swimmer.password_hash = generate_password_hash(form.new_password.data)
        db.session.commit()
        login_user(swimmer)
        session['user_type'] = 'swimmer'
        session['role'] = 'swimmer'
        session.pop('swimmer_id', None)
        flash("Password set successfully!", "success")
        return redirect(url_for('swimmer_dashboard'))

    return render_template('swimmer_set_password.html', form=form)

@app.route('/meet-register/<int:event_id>', methods=['GET', 'POST'])
@login_required
def meet_register(event_id):
    if session.get('role') != 'swimmer':
        flash("Unauthorized access to registration.", "danger")
        return redirect(url_for('login_selection'))

    event = Event.query.get_or_404(event_id)
    swimmer = Swimmer.query.get(current_user.id)

    allowed_age_groups = event.age_groups.split(',') if event.age_groups else []

    if not swimmer.dob:
        flash("Please complete your profile with your date of birth before registering.")
        return redirect(url_for('swimmer_profile'))

    if not is_eligible(str(swimmer.dob), event.start_date, allowed_age_groups):
        flash("You are not eligible for this event based on your age.", "warning")
        return redirect(url_for('swimmer_dashboard'))

    # Load selected events
    selected_events_json = event.selected_events_json or '{}'
    all_events = json.loads(selected_events_json)

    import re

    stroke_priority = {
        'freestyle': 1,
        'backstroke': 2,
        'breaststroke': 3,
        'butterfly': 4,
        'medley': 5,
        'relay': 6,
        'relay_mixed': 7
    }

    def get_event_key(name):
        name_lower = name.lower()

        # Stroke category
        if 'freestyle' in name_lower and 'relay' not in name_lower:
            stroke = 'freestyle'
        elif 'backstroke' in name_lower:
            stroke = 'backstroke'
        elif 'breaststroke' in name_lower:
            stroke = 'breaststroke'
        elif 'butterfly' in name_lower:
            stroke = 'butterfly'
        elif 'individual medley' in name_lower:
            stroke = 'medley'
        elif 'relay mixed' in name_lower:
            stroke = 'relay_mixed'
        elif 'relay' in name_lower:
            stroke = 'relay'
        else:
            stroke = 'zzz'

        # Distance
        dist_match = re.search(r'(\d+)', name_lower)
        distance = int(dist_match.group(1)) if dist_match else 9999

        return (stroke_priority.get(stroke, 999), distance, name_lower)

    unique_event_names = sorted(
        set(ev for group in all_events.values() for ev in group),
        key=get_event_key
    )

    if request.method == 'POST':
        selected = request.form.getlist('event_choices')
        print("Selected Events:", selected)
        print("Max allowed:", event.max_individual_events)


        individual_events = [ev for ev in selected if 'relay' not in ev.lower()]
        

        max_allowed = event.max_individual_events or 999  # Fallback in case not set

        if len(individual_events) > max_allowed:
            flash(f"You selected {len(individual_events)} individual events, but the limit is {max_allowed}.", "danger")
            return redirect(url_for('meet_register', event_id=event_id))

        for event_name in selected:
            race = SwimRace.query.filter_by(name=event_name.strip(), event_id=event.id).first()

            if race:
                existing = SwimmerEventRegistration.query.filter_by(
                    swimmer_id=swimmer.id,
                    swim_race_id=race.id
                ).first()

                if not existing:
                    registration = SwimmerEventRegistration(
                        swimmer_id=swimmer.id,
                        event_id=event.id,
                        meet_id=event.id,
                        swim_race_id=race.id
                    )
                    db.session.add(registration)

        # ✅ Commit the changes to the database
        db.session.commit()

        return render_template("registration_success.html", event=event)


    # ✅ Correct GET response
    return render_template('meet_registration.html',
                           event=event,
                           swimmer=swimmer,
                           event_choices=unique_event_names)


@app.route('/swimmer-dashboard')
@login_required
def swimmer_dashboard():
    if session.get('role') != 'swimmer':

        flash("Unauthorized access to swimmer dashboard.", "danger")
        return redirect(url_for('swimmer_login'))

    today = datetime.today().date()

    # 👇 Safely wrap DB access to prevent autoflush errors
    with db.session.no_autoflush:
        events = Event.query.filter_by(visibility='swimmer', status='Published') \
                            .filter(Event.start_date >= today) \
                            .order_by(Event.start_date).all()

        import json
        for e in events:
            if isinstance(e.event_schedule_json, str):
                try:
                    e.event_schedule_json = json.loads(e.event_schedule_json)
                except json.JSONDecodeError:
                    e.event_schedule_json = []

            e.full_title = generate_full_event_title(e)

        swimmer = Swimmer.query.filter_by(id=current_user.id).first()

    return render_template('swimmer_dashboard.html', swimmer=swimmer, events=events, current_time=datetime.now())
    
def generate_full_event_title(event):
    from datetime import datetime
    import re

    try:
        s_date = datetime.strptime(event.start_date, "%d %B %Y")
        e_date = datetime.strptime(event.end_date, "%d %B %Y")
        if s_date.year == e_date.year and s_date.month == e_date.month:
            date_str = f"FROM {s_date.day}th TO {e_date.day}th {e_date.strftime('%B').upper()} - {e_date.year}"
        else:
            date_str = f"FROM {event.start_date.upper()} TO {event.end_date.upper()}"
    except:
        date_str = f"FROM {event.start_date} TO {event.end_date}"

    age_groups = event.age_groups if isinstance(event.age_groups, list) else event.age_groups.split(',')

    def format_age_gender_phrase(groups):
        age_gender_map = {}
        for group in groups:
            match = re.match(r'(u\d+|senior)_(boys|girls|men|women)', group.lower())
            if match:
                age, gender = match.groups()
                age = age.upper().replace("U", "U-") if "u" in age else "SENIOR"
                gender = gender.upper()
                age_gender_map.setdefault(age, set()).add(gender)

        phrases = []
        for age in sorted(age_gender_map.keys(), key=lambda x: (x != "SENIOR", x)):
            genders = sorted(age_gender_map[age], key=lambda g: ["BOYS", "GIRLS", "MEN", "WOMEN"].index(g))
            phrases.append(f"{age} {' & '.join(genders)}")
        return " | ".join(phrases) if phrases else "PARTICIPANTS"

    gender_age_phrase = format_age_gender_phrase(age_groups)
    return f"{event.name.upper()} FOR {gender_age_phrase} TO BE HELD AT THE {event.place.upper()} {date_str}"


@app.route('/swimmer-profile', methods=['GET', 'POST'])
@login_required
def swimmer_profile():
    if session.get('user_type') != 'swimmer':
        flash("Access denied.", "danger")
        return redirect(url_for('login_selection'))

    swimmer = Swimmer.query.filter_by(id=current_user.id).first()
    form = SwimmerProfileForm()
    edit_mode = request.args.get('edit') == 'true'

    # --- Handle GET (prefill values) ---
    if request.method == 'GET' and edit_mode:
        form.name.data = swimmer.name
        form.email.data = swimmer.email
        form.phone.data = swimmer.phone
        form.gender.data = swimmer.gender
        form.emergency_name.data = swimmer.emergency_name
        form.emergency_contact.data = swimmer.emergency_contact
        form.address.data = swimmer.address
        form.sfi_number.data = swimmer.sfi_number

        # Convert stored date (date or str) to dd/mm/yyyy string for input display
        if swimmer.dob:
            if isinstance(swimmer.dob, str):
                try:
                    dob_obj = datetime.strptime(swimmer.dob, '%Y-%m-%d')
                except ValueError:
                    dob_obj = None
            else:
                dob_obj = swimmer.dob
            form.dob.data = dob_obj if dob_obj else None


    # --- Handle POST (form submitted) ---
    if request.method == 'POST' and form.validate_on_submit():
        print("✅ Form validated and submitted.")
        swimmer.name = form.name.data
        swimmer.email = form.email.data
        swimmer.phone = form.phone.data
        swimmer.gender = form.gender.data
        swimmer.emergency_name = form.emergency_name.data
        swimmer.emergency_contact = form.emergency_contact.data
        swimmer.address = form.address.data
        swimmer.sfi_number = form.sfi_number.data

        # Convert submitted string to date
        try:
            dob_str = request.form.get('dob')
            swimmer.dob = datetime.strptime(dob_str, '%d/%m/%Y').date()
        except Exception as e:
            print("⚠️ DOB conversion error:", e)
            flash("Date of Birth must be in dd/mm/yyyy format.", "danger")
            return redirect(url_for('swimmer_profile', edit='true'))

        # Handle uploads
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        if form.aadhaar_file.data:
            aadhaar_filename = secure_filename(form.aadhaar_file.data.filename)
            aadhaar_path = os.path.join(app.config['UPLOAD_FOLDER'], aadhaar_filename)
            form.aadhaar_file.data.save(aadhaar_path)
            swimmer.aadhaar_file = aadhaar_filename

        if form.sfi_file.data:
            sfi_filename = secure_filename(form.sfi_file.data.filename)
            sfi_path = os.path.join(app.config['UPLOAD_FOLDER'], sfi_filename)
            form.sfi_file.data.save(sfi_path)
            swimmer.sfi_file = sfi_filename
        

        db.session.commit()
        print("✅ Changes committed to DB.")
        flash("Profile updated successfully!", "success")
        return redirect(url_for('swimmer_profile'))

    if form.errors:
        print("⚠️ Form validation failed.")
        print(form.errors)

    return render_template('swimmer_profile.html', form=form, swimmer=swimmer, edit=edit_mode)


@app.route('/swimmer-login', methods=['GET', 'POST'])
def swimmer_login():
    form = SwimmerLoginForm()

    if form.validate_on_submit():
        swimmer = Swimmer.query.filter_by(username=form.username.data).first()
        if swimmer and check_password_hash(swimmer.password_hash, form.password.data):
            login_user(swimmer)
            session['role'] = 'swimmer'


            flash("Login successful!", "success")
            return redirect(url_for('swimmer_dashboard'))

        else:
            flash("Invalid username or password.", "danger")

    return render_template('swimmer_login.html', form=form)


@app.route('/signup-selection')
def signup_selection():
    return render_template('signup_selection.html')

@app.route('/login-selection')
def login_selection():
    return render_template('login_selection.html')


@app.route('/admin-clear-swimmers')
@login_required
def clear_all_swimmers():
    if not isinstance(current_user._get_current_object(), Admin):
        return "Unauthorized", 403

    all_swimmers = Swimmer.query.all()
    for swimmer in all_swimmers:
        db.session.delete(swimmer)
    db.session.commit()
    return "✅ All swimmers deleted."

# Note: Keep the original '/admin-clear-all' endpoint for clearing organizers
@app.route('/admin-clear-all')
@login_required
def clear_all_organizers():
    if not isinstance(current_user._get_current_object(), Admin):
        return "Unauthorized", 403

    all_organizers = Organizer.query.all()
    for organizer in all_organizers:
        db.session.delete(organizer)
    db.session.commit()
    return "✅ All organizers deleted."



@app.route('/draft-events')
@login_required
def draft_events():
    if not isinstance(current_user, Organizer):
        flash("Access denied: Only organizers can view draft events.", "danger")
        return redirect(url_for('home'))

    drafts = Event.query.filter_by(organizer_id=current_user.id, status='Draft').order_by(Event.start_date).all()
    return render_template('draft_events.html', drafts=drafts)


def parse_date(date_string):
    try:
        return datetime.strptime(date_string, '%Y-%m-%d')  # HTML default
    except ValueError:
        return datetime.strptime(date_string, '%d/%m/%Y')
        
@app.route('/reschedule-event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def reschedule_event(event_id):
    event = Event.query.get_or_404(event_id)

    if request.method == 'POST':
        new_start = request.form['start_date']
        new_end = request.form['end_date']
        from datetime import datetime
        start_date = datetime.strptime(new_start, '%d/%m/%Y')
        end_date = datetime.strptime(new_end, '%d/%m/%Y')

        event.start_date = start_date
        event.end_date = end_date

        # ✅ Regenerate schedule using same logic
        from app.utils import generate_event_schedule, generate_event_pdf
        generate_event_schedule(event.id, start_date, end_date)

        sessions = json.loads(event.event_schedule_json or '[]')

        # Build data for PDF
        try:
            age_groups = json.loads(event.age_groups)
        except:
            age_groups = event.age_groups.split(',') if event.age_groups else []

        event_data = {
            'name': event.name,
            'place': event.place,
            'start_date': start_date.strftime('%d %B %Y'),
            'end_date': end_date.strftime('%d %B %Y'),
            'level': event.level,
            'age_groups': age_groups,
            'association_name': event.association_name
        }

# ✅ Load full session data (has 'morning' and 'evening')
        sessions = json.loads(event.event_schedule_json or '[]')

# ✅ This is exactly what your PDF function expects now
        schedule_data = []
        for session in sessions:
            schedule_data.append({
                'day': session['day'],
                'morning': session.get('morning', []),
                'evening': session.get('evening', [])
            })

# Save the new PDF using the correct schedule
        pdf_path = os.path.join(current_app.root_path, 'static', 'pdfs', f'event_{event.id}.pdf')
        generate_event_pdf(event_data, schedule_data, pdf_path)


        db.session.commit()
        flash("Event rescheduled successfully. PDF updated.", "success")
        return redirect(url_for('published_events'))

    if request.method == 'GET':
        start_date = event.start_date.strftime('%d/%m/%Y')
        end_date = event.end_date.strftime('%d/%m/%Y')
        return render_template("reschedule_event.html", event=event,
                               start_date=start_date, end_date=end_date)



@app.route('/move-to-draft/<int:event_id>', methods=['POST'])
@login_required
def move_to_draft(event_id):
    event = Event.query.get_or_404(event_id)
    event.status = "Draft"
    db.session.commit()
    flash("Event moved to draft.", "info")
    return redirect(url_for('published_events'))


@app.route('/delete-draft/<int:event_id>', methods=['POST'])
@login_required
def delete_draft_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.organizer_id != current_user.id or event.status != "Draft":
        abort(403)

    db.session.delete(event)
    db.session.commit()
    flash("Draft event deleted.", "success")
    return redirect(url_for('draft_events'))

@app.route('/delete-published/<int:event_id>', methods=['POST'])
@login_required
def delete_published_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event.organizer_id != current_user.id or event.status != "Published":
        abort(403)

    db.session.delete(event)
    db.session.commit()
    flash("Published event deleted.", "success")
    return redirect(url_for('published_events'))


@app.route('/event/<int:event_id>/pdf')
@login_required
def view_event_pdf(event_id):
    # Your PDF generation or return logic
    return send_file(f"static/pdfs/event_{event_id}.pdf", as_attachment=False)

@app.route('/clear-create-event-session', methods=['POST'])
@login_required
def clear_create_event_session():
    event_id = request.form.get('event_id')
    event = Event.query.filter_by(id=event_id, organizer_id=current_user.id).first()

    if not event:
        flash("Event not found.")
        return redirect(url_for('published_events'))

    # Fill session
    session['event_id'] = event.id
    session['event_name'] = event.name
    session['place'] = event.place
    session['association_name'] = event.association_name
    session['start_date'] = event.start_date.strftime('%d/%m/%Y')
    session['end_date'] = event.end_date.strftime('%d/%m/%Y')
    session['registration_start_date'] = event.registration_start_date.strftime('%d/%m/%Y')
    session['registration_end_date'] = event.registration_end_date.strftime('%d/%m/%Y')
    session['num_days'] = (event.end_date - event.start_date).days + 1
    session['age_groups'] = event.age_groups.split(',') if event.age_groups else []
    session['level'] = event.level

    return redirect(url_for('create_event'))


@app.route('/start-new-event')
@login_required
def start_new_event():
    # Clear all session keys related to event creation
    session.pop('event_id', None)
    session.pop('event_name', None)
    session.pop('place', None)
    session.pop('association_name', None)
    session.pop('start_date', None)
    session.pop('end_date', None)
    session.pop('registration_start_date', None)
    session.pop('registration_end_date', None)
    session.pop('age_groups', None)
    session.pop('selected_events', None)
    session.pop('num_days', None)
    # Redirect to create event
    return redirect(url_for('create_event'))
    
@app.route('/admin-swimmers')
@login_required  # Optional: protect with login
def admin_swimmers():
    swimmers = Swimmer.query.all()
    return render_template("admin_swimmers.html", swimmers=swimmers)




def is_eligible(swimmer_dob, event_start_date, allowed_age_groups):
    dob = datetime.strptime(swimmer_dob, "%Y-%m-%d").date()
    age = event_start_date.year - dob.year - ((event_start_date.month, event_start_date.day) < (dob.month, dob.day))

    eligibility = {
        'U-14': age <= 14,
        'U-17': age <= 17,
        'U-19': age <= 19,
        'SENIOR': True  # Everyone eligible
    }

    normalized_groups = []
    for group in allowed_age_groups:
        group = group.lower().strip()

        if 'u14' in group:
            normalized_groups.append('U-14')
        elif 'u17' in group:
            normalized_groups.append('U-17')
        elif 'u19' in group:
            normalized_groups.append('U-19')
        elif 'senior' in group:
            normalized_groups.append('SENIOR')

    return any(eligibility.get(group, False) for group in normalized_groups)

@app.route('/view-event-entries/<int:event_id>')
@login_required
def view_event_entries(event_id):
    from datetime import date, datetime

    def get_age_group(dob):
        if not dob:
            return "Unknown Age Group"
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age <= 10:
            return "U-10"
        elif age <= 14:
            return "U-14"
        elif age <= 17:
            return "U-17"
        elif age <= 19:
            return "U-19"
        else:
            return "Senior"

    event = Event.query.get_or_404(event_id)
    registrations = SwimmerEventRegistration.query.filter_by(event_id=event_id).all()

    swimmer_map = {}
    event_structure = {}

    for reg in registrations:
        swimmer = reg.swimmer
        swimmer_id = swimmer.id

        # Convert DOB to datetime
        dob_raw = swimmer.dob
        dob_obj = None
        if isinstance(dob_raw, str):
            try:
                dob_obj = datetime.strptime(dob_raw, '%Y-%m-%d').date()
            except ValueError:
                dob_obj = None
        else:
            dob_obj = dob_raw

        if swimmer_id not in swimmer_map:
            swimmer_map[swimmer_id] = {
                'name': swimmer.name,
                'email': swimmer.email,
                'gender': swimmer.gender,
                'dob': dob_obj.strftime('%d/%m/%Y') if dob_obj else 'N/A',
                'registered_events': set()
            }

        if reg.swim_race:
            swimmer_map[swimmer_id]['registered_events'].add(reg.swim_race.name)

            # Populate event_structure (grouping)
            age_group = get_age_group(dob_obj)
            gender = swimmer.gender or "Unspecified"
            race_name = reg.swim_race.name

            swimmer_data = {
                'name': swimmer.name,
                'dob': dob_obj.strftime('%d/%m/%Y') if dob_obj else 'N/A',
            }

            if race_name not in event_structure:
                event_structure[race_name] = {}
            if age_group not in event_structure[race_name]:
                event_structure[race_name][age_group] = {}
            if gender not in event_structure[race_name][age_group]:
                event_structure[race_name][age_group][gender] = []

            event_structure[race_name][age_group][gender].append(swimmer_data)

    # Convert to list and sort races
    swimmer_entries = []
    for swimmer in swimmer_map.values():
        swimmer['registered_events'] = sorted(list(swimmer['registered_events']))
        swimmer_entries.append(swimmer)

    return render_template(
        'event_entries.html',
        event=event,
        swimmers=swimmer_entries,
        event_structure=event_structure
    )


@app.route('/view-registered-swimmers')
@login_required
def view_registered_swimmers():
    organizer_id = current_user.id
    events = Event.query.filter_by(organizer_id=organizer_id).all()
    return render_template('view_registered_swimmers.html', events=events)
