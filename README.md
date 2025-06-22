# SwimApp

SwimApp is a Flask-based web application designed to manage swimming events, including organizer registration, event scheduling, swimmer registration, and result management.

## Features

* Organizer and Swimmer dashboards
* Event creation and scheduling
* PDF schedule generation
* Email notifications
* Secure authentication and profile management

## Requirements

* Python 3.9+
* Virtual environment (`venv`)
* Flask
* SQLAlchemy
* Flask-WTF
* Flask-Mail
* Flask-Login

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Jasnoor2006/SwimApp.git
cd SwimApp
```

### 2. Set Up Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file at the root of your project with:

```env
SECRET_KEY=your_secret_key
DATABASE_URL=sqlite:///app.db
MAIL_SERVER=smtp.yourmailprovider.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=youremail@example.com
MAIL_PASSWORD=yourpassword
```

Replace placeholders with your details.

### 5. Database Setup

```bash
flask db init
flask db migrate
flask db upgrade
```

### 6. Run the Application

```bash
python run.py
```

Visit `http://localhost:5000` in your browser to use the app.

## Project Structure

```
SwimApp/
├── app/
│   ├── routes.py
│   ├── models.py
│   ├── templates/
│   └── static/
├── migrations/
├── requirements.txt
├── run.py
├── config.py
└── README.md
```

