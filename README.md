# NosiFit

NosiFit is a web application for tracking workouts, nutrition, recovery and personal fitness progress.

The main goal of this project is to help users plan their training, monitor daily activity and receive useful recommendations based on their performance and workout history.

This project is still in development, and new features are being added regularly.

---

## Features

### Authentication

- User registration
- Login and logout
- Email verification
- Password recovery
- Google OAuth
- GitHub OAuth

### Training

- Create workout sessions
- Save completed workouts
- Training plans
- Strength test
- Muscle load analysis
- Training load index
- Exercise recommendations
- Activity heatmap

### Nutrition

- Daily calorie tracking
- Protein, fat and carbohydrate tracking
- Water intake tracking
- Weight tracking
- Nutrition history

### Recovery

- Recovery habits
- Sleep tracking
- Hydration tracking
- Fatigue analysis

### Profile

- Edit personal information
- Change email
- Change password
- Delete account
- Complete profile information

---

## Technologies

Backend

- Python
- Flask
- SQLAlchemy
- Flask-Login
- Flask-Migrate
- Flask-Mail
- Authlib
- PostgreSQL

Frontend

- HTML
- CSS
- JavaScript

Other

- Git
- GitHub

---

## Project Structure

```
myapp/
│
├── app/
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── training_engine/
│   ├── templates/
│   ├── static/
│   └── ...
│
├── migrations/
└── run.py
```

---

## Installation

Clone the repository

```bash
git clone https://github.com/your_username/NosiFit.git
```

Go to the project directory

```bash
cd NosiFit
```

Create a virtual environment

```bash
python -m venv .venv
```

Activate it

Windows

```bash
.venv\Scripts\activate
```

Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Create a `.env` file and configure:

```
SECRET_KEY=

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

MAIL_USERNAME=
MAIL_PASSWORD=
```

Create a PostgreSQL database and update the connection string in `config.py`.

Run migrations

```bash
flask db upgrade
```

Start the application

```bash
python app.py
```

---

## Screenshots

### Landing Page

(Add screenshot)

### Profile

(Add screenshot)

### Training

(Add screenshot)

### Nutrition

(Add screenshot)

---

## Current Status

The project is still under development.

Completed:

- Authentication system
- OAuth login
- Training module
- Profile management

Currently working on:

- Recovery module
- Dashboard improvements
- Nutrition improvements

---

## Future Plans

- Better analytics
- More recovery recommendations
- Better nutrition statistics
- Mobile responsive improvements
- Performance optimizations

---

## Author

Developed by Yaroslav Fedorak.

GitHub:
https://github.com/YaroslavFedorak
