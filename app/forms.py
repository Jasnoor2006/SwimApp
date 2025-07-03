from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField, FileField, SelectMultipleField, DateField, RadioField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Optional
from wtforms.widgets import ListWidget, CheckboxInput
from wtforms import IntegerField
from wtforms.validators import NumberRange





class OrganizerSignupForm(FlaskForm):
    association_name = StringField('Association/Club Name', validators=[DataRequired()])
    person_name = StringField('Contact Person Name', validators=[DataRequired()])
    contact = StringField('Contact', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    address = StringField('Address', validators=[DataRequired()])
    submit = SubmitField('Request Signup')

class OrganizerProfileForm(FlaskForm):
    person_name = StringField('Name', validators=[DataRequired()])
    association_name = StringField('Association', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    contact = StringField('Contact', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired()])
    submit = SubmitField('Save Changes')

class AdminLoginForm(FlaskForm):
    username = StringField('Admin Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class NewPasswordForm(FlaskForm):
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Set Password')

class OrganizerLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class AdminProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    profile_picture = FileField('Upload Profile Picture')
    password = PasswordField('New Password')
    confirm_password = PasswordField('Confirm Password', validators=[
        EqualTo('password', message='Passwords must match.')
    ])
    notifications = BooleanField('Receive signup notification emails')
    submit = SubmitField('Save Changes')

class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class CreateEventForm(FlaskForm):
    association_name = StringField("Association Name", validators=[DataRequired()])
    event_name = StringField("Event Name", validators=[DataRequired()])
    place = StringField("Place", validators=[DataRequired()])
    start_date = DateField("Start Date", format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField("End Date", format='%Y-%m-%d', validators=[DataRequired()])
    registration_start_date = DateField("Registration Start Date", format='%Y-%m-%d', validators=[DataRequired()])
    registration_end_date = DateField("Registration End Date", format='%Y-%m-%d', validators=[DataRequired()])
    max_individual_events = IntegerField("Max Individual Events per Swimmer", validators=[NumberRange(min=1, max=50)])

    age_groups = MultiCheckboxField("Age Groups", choices=[
        ('senior_men', 'Senior (Men)'),
        ('senior_women', 'Senior (Women)'),
        ('u19_boys', 'U-19 (Boys)'),
        ('u19_girls', 'U-19 (Girls)'),
        ('u18_boys', 'U-18 (Boys)'),
        ('u18_girls', 'U-18 (Girls)'),
        ('u17_boys', 'U-17 (Boys)'),
        ('u17_girls', 'U-17 (Girls)'),
        ('u14_boys', 'U-14 (Boys)'),
        ('u14_girls', 'U-14 (Girls)'),
        ('u12_boys', 'U-12 (Boys)'),
        ('u12_girls', 'U-12 (Girls)'),
        ('u10_boys', 'U-10 (Boys)'),
        ('u10_girls', 'U-10 (Girls)'),
        ('u8_boys', 'U-8 (Boys)'),
        ('u8_girls', 'U-8 (Girls)'),
        ('other', 'Other')
    ], validators=[DataRequired()])

    meet_levels = RadioField("Meet Level", choices=[
        ('District', 'District'),
        ('State', 'State'),
        ('National', 'National'),
        ('Club', 'Club')
    ], validators=[DataRequired()])
    submit = SubmitField("Next")


class SwimmerRegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired()])
    contact_method = RadioField('Preferred Contact', choices=[('email', 'Email'), ('phone', 'Phone')], default='email')
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('Phone Number', validators=[Optional()])
    submit = SubmitField('Send Verification Code')

    def validate(self, extra_validators=None):  # ✅ FIXED SIGNATURE
        rv = super().validate(extra_validators=extra_validators)  # ✅ Call parent with args
        if not rv:
            return False

        if self.contact_method.data == 'email' and not self.email.data:
            self.email.errors.append("Email is required for email verification.")
            return False
        if self.contact_method.data == 'phone' and not self.phone.data:
            self.phone.errors.append("Phone number is required for phone verification.")
            return False

        return True

class SwimmerProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[Email()])
    phone = StringField('Phone')
    gender = SelectField('Gender', choices=[('', 'Select'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    dob = StringField('Date of Birth') 
    emergency_name = StringField('Emergency Contact Name')
    emergency_contact = StringField('Emergency Contact Number')
    address = TextAreaField('Address')
    sfi_number = StringField('SFI Number')
    aadhaar_file = FileField('Upload Aadhaar')
    sfi_file = FileField('Upload SFI Document')


class SwimmerVerificationForm(FlaskForm):
    code = StringField('Verification Code', validators=[DataRequired()])
    submit = SubmitField('Verify')


class SwimmerPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Set Password')

class SwimmerLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RescheduleForm(FlaskForm):
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    submit = SubmitField('Update Dates')