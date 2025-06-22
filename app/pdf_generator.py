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

    # Draw the association name in bold, larger size
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

    # Draw schedule
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