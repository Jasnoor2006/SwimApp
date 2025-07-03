from flask import current_app
from flask_mail import Message
from app import mail
import random
import json
from datetime import timedelta
from app import db
from app.models import Event, SwimRace, SwimmerEventRegistration, Swimmer
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from collections import defaultdict
from collections import OrderedDict


def generate_verification_code():
    return str(random.randint(100000, 999999))

def send_email_verification(to_email, code):
    try:
        msg = Message(
            subject="Your SwimApp Verification Code",
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[to_email]
        )
        msg.body = f"Your verification code is: {code}"
        mail.send(msg)
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        return False

def send_sms_verification(phone_number, code):
    print(f"[Simulated SMS] Code {code} sent to {phone_number}")
    return True

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from datetime import datetime
import re

def format_age_gender_phrase(age_groups):
    age_gender_map = {}

    for group in age_groups:
        match = re.match(r'(u\d+|senior)_(boys|girls|men|women)', group.lower())
        if match:
            age, gender = match.groups()
            age = age.upper().replace("U", "U-") if "u" in age else "SENIOR"
            gender = gender.upper()

            if age not in age_gender_map:
                age_gender_map[age] = set()
            age_gender_map[age].add(gender)

    phrases = []
    for age in sorted(age_gender_map.keys(), key=lambda x: (x != "SENIOR", x)):
        genders = sorted(age_gender_map[age], key=lambda g: ["BOYS", "GIRLS", "MEN", "WOMEN"].index(g))
        phrases.append(f"{age} {' & '.join(genders)}")

    return " | ".join(phrases) if phrases else "PARTICIPANTS"


def generate_event_pdf(event_data, schedule_data, filepath):
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    y = height - 50

    # Event info
    event_name = event_data.get('name', 'Event')
    place = event_data.get('place', 'Venue')
    start_date = event_data.get('start_date', '')
    end_date = event_data.get('end_date', '')
    age_groups = event_data.get('age_groups', [])
    association_name = event_data.get('association_name', '').strip().upper()

    gender_age_phrase = format_age_gender_phrase(age_groups)

    # Format date string
    try:
        s_date = datetime.strptime(start_date, "%d %B %Y")
        e_date = datetime.strptime(end_date, "%d %B %Y")
        if s_date.year == e_date.year and s_date.month == e_date.month:
            date_str = f"FROM {s_date.day}th TO {e_date.day}th {e_date.strftime('%B').upper()} - {e_date.year}"
        else:
            date_str = f"FROM {start_date.upper()} TO {end_date.upper()}"
    except:
        date_str = f"FROM {start_date} TO {end_date}"

    # Association name
    if association_name:
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width / 2, y, association_name)
        y -= 30

    # Title line
    full_title = (
        f"{event_name.upper()} FOR {gender_age_phrase} "
        f"TO BE HELD AT THE {place.upper()} {date_str}"
    )

    # Wrapped and center-aligned header
    c.setFont("Helvetica-Bold", 11)
    wrapped_lines = simpleSplit(full_title, "Helvetica-Bold", 11, 500)
    for line in wrapped_lines:
        c.drawCentredString(width / 2, y, line)
        y -= 15

    y -= 10  # space before schedule

    left_margin = 50
    right_margin = 50
    usable_width = width - left_margin - right_margin
    column_gap = 20
    column_width = (usable_width - column_gap) / 2

    col1_x = left_margin
    col2_x = left_margin + column_width + column_gap

    c.setFont("Helvetica-Bold", 11)

    for session in schedule_data:
        if y < 100:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica-Bold", 11)

        y -= 10
        c.setFont("Helvetica-Bold", 10)
        c.drawString(col1_x, y, f"{session['day']} – Morning Session")
        c.drawString(col2_x, y, f"{session['day']} – Evening Session")
        y -= 20
        c.setFont("Helvetica", 10)

        max_len = max(len(session['morning']), len(session['evening']))
        for i in range(max_len):
            if i < len(session['morning']):
                c.drawString(col1_x + 10, y, f"- {session['morning'][i]}")
            if i < len(session['evening']):
                c.drawString(col2_x + 10, y, f"- {session['evening'][i]}")

            y -= 12
            if y < 100:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica-Bold", 10)
                c.drawString(col1_x, y, f"{session['day']} – Morning Session (contd.)")
                c.drawString(col2_x, y, f"{session['day']} – Evening Session (contd.)")
                y -= 15
                c.setFont("Helvetica", 10)

    c.save()



def generate_event_schedule(event_id, start_date, end_date):
    event = Event.query.get(event_id)
    if not event:
        raise Exception("Event not found")

    # Calculate duration
    num_days = (end_date - start_date).days + 1
    if num_days <= 0:
        raise Exception("End date must be after start date")

    sessions = []

    # Load selected events (Step 2 JSON)
    try:
        selected_events = json.loads(event.selected_events_json)
    except Exception as e:
        raise Exception(f"Invalid or missing selected events JSON: {e}")

    # Build blank schedule
    for i in range(num_days):
        sessions.append({
            'day': (start_date + timedelta(days=i)).strftime('%A, %d %b %Y'),
            'morning': [],
            'evening': []
        })

    # Display order for assigning events
    display_order = [
        ('senior_men', 'SENIOR MEN'),
        ('senior_women', 'SENIOR WOMEN'),
        ('u19_boys', 'U-19 BOYS'), ('u19_girls', 'U-19 GIRLS'),
        ('u17_boys', 'U-17 BOYS'), ('u17_girls', 'U-17 GIRLS'),
        ('u14_boys', 'U-14 BOYS'), ('u14_girls', 'U-14 GIRLS'),
        ('u12_boys', 'U-12 BOYS'), ('u12_girls', 'U-12 GIRLS'),
        ('u10_boys', 'U-10 BOYS'), ('u10_girls', 'U-10 GIRLS'),
        ('u8_boys', 'U-8 BOYS'), ('u8_girls', 'U-8 GIRLS'),
        ('senior_mixed', 'SENIOR MIXED')
        
    ]

    # Assign events to sessions
    day_index = 0
    session_type = 'morning'

    for group_key, label in display_order:
        if group_key in selected_events:
            for stroke in selected_events[group_key]:
                sessions[day_index][session_type].append(f"{stroke.upper()} – {label}")

                # Alternate session
                session_type = 'evening' if session_type == 'morning' else 'morning'

                # Advance day when we return to morning
                if session_type == 'morning':
                    day_index += 1
                    if day_index >= num_days:
                        day_index = 0

    # Save the updated schedule
    event.event_schedule_json = json.dumps(sessions)
    db.session.commit()

from collections import defaultdict

def parse_time(time_str):
    """Convert time string to float; treat missing/invalid as infinity."""
    try:
        return float(time_str.strip())
    except (ValueError, AttributeError):
        return float('inf')

def get_lane_order(n_lanes):
    """
    Generate lane order for seeding:
    Start at center lane,
    then alternate to right and left, moving outward.
    """
    center = (n_lanes + 1) // 2  # middle lane, 1-indexed
    order = [center]

    offset = 1
    while len(order) < n_lanes:
        right_lane = center + offset
        left_lane = center - offset

        if right_lane <= n_lanes:
            order.append(right_lane)
        if len(order) >= n_lanes:
            break

        if left_lane >= 1:
            order.append(left_lane)

        offset += 1

    return order


def assign_lanes(swimmers, n_lanes):
    """Assign lanes to swimmers in sorted order."""
    lane_order = get_lane_order(n_lanes)
    heat = []
    for i, swimmer in enumerate(swimmers):
        lane = lane_order[i % n_lanes]
        heat.append({
            'swimmer_name': swimmer.swimmer.name,
            'best_time': swimmer.best_time,
            'lane': lane
        })
    return heat

def divide_into_heats(sorted_swimmers, n_lanes=8):
    heats = []
    for i in range(0, len(sorted_swimmers), n_lanes):
        heat_swimmers = sorted_swimmers[i:i + n_lanes]
        assigned = assign_lanes(heat_swimmers, n_lanes)
        heats.append(assigned)
    return heats







def generate_heat_sheet(meet_id, n_lanes=None):
    meet = Event.query.get(meet_id)
    if not meet or not meet.event_schedule_json:
        return {}

    try:
        schedule = json.loads(meet.event_schedule_json)
    except json.JSONDecodeError:
        return {}


    n_lanes = n_lanes or meet.n_lanes or 6
    heat_sheet = OrderedDict()
    start_date = meet.start_date 

    for session_index, session in enumerate(schedule):
        session_date = start_date + timedelta(days=session_index)
        period = 'morning'
        period_label = 'Morning'
        events = session.get(period, [])

        for item in events:
            if "–" not in item:
                continue
            
            stroke, group_info = map(str.strip, item.split("–"))


            parts = group_info.upper().split()
            if len(parts) < 2:
                continue

            age_part = parts[0].replace("-", "").upper()  # e.g., U19 or SENIOR
            gender_word = parts[1].lower()  # e.g., men, women

                
            if age_part.startswith('U'):
                age_group = age_part
            elif age_part == "SENIOR":
                age_group = "SENIOR"
            else:
                print(f"Skipping unknown age group: {age_part}")
                continue

            gender_word = gender_word.lower().strip()

            if gender_word == "men" or gender_word == "boys":
                gender = "MEN"
                age_group_full = f"{age_group}_MEN"
            elif gender_word == "women" or gender_word == "girls":
                gender = "WOMEN"
                age_group_full = f"{age_group}_WOMEN"
            else:
                gender = "MIXED"
                age_group_full = f"{age_group}_MIXED"

            race_name = stroke.strip()

                # Final debug print before query
            print(f"FINAL QUERY -> name='{race_name}', age_group='{age_group_full}', gender='{gender}'")

            race = SwimRace.query.filter_by(
                event_id=meet_id,
                name=race_name,
                age_group=age_group_full,
                gender=gender
            ).first()
            if not race:
                print(f"No race found for query: name='{race_name}', age_group='{age_group_full}', gender='{gender}'")
                continue
            regs = SwimmerEventRegistration.query.filter_by(swim_race_id=race.id).all()
            if not regs:
                continue

            sorted_regs = sorted(regs, key=lambda r: parse_time(r.best_time))
            key_name = f"{stroke.upper()} – {age_group_full.replace('_', ' ')}"
            heats = divide_into_heats(sorted_regs, n_lanes)
            heat_sheet[key_name] = heats

    return heat_sheet
