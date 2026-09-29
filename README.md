# NosiFit

NosiFit is a full-stack web application for managing training, nutrition and recovery in one place.

I started the project as a way to build something more than a simple workout tracker. The application combines workout planning, training load analysis, recovery data, nutrition tracking and daily dashboard analytics.

NosiFit is currently at **v0.1.0-beta**. The core application modules are connected and working together, while the project continues to evolve toward a stable release.

## Features

### Authentication & Account

- Email and password authentication
- Email verification
- Password recovery
- Google OAuth
- GitHub OAuth
- Profile management
- Email and password changes
- Account deletion
- OAuth account management

### Training

- Workout sessions
- Training plans
- Exercise selection and management
- Strength testing
- Training load calculation
- Muscle load analysis
- Exercise recommendations
- Equipment management
- Injury information
- Training history

### Dashboard

- Daily overview
- Daily balance score
- Training load
- Recovery score
- Sleep data
- Nutrition summary
- Training recommendations
- Activity heatmap
- Day details and history
- Calendar view
- Workout editor

### Recovery

- Recovery score
- Sleep tracking
- Recovery habits
- Habit logging
- Recovery statistics
- Fatigue and recovery analysis
- Recovery recommendations

### Nutrition

- Daily calorie tracking
- Protein, fat and carbohydrate tracking
- Meal logging
- Saved meals
- Nutrition goals
- Water intake tracking
- Weight tracking
- Nutrition statistics
- Nutrition recommendations

### Onboarding & Assessment

- User onboarding
- Fitness questionnaire
- Training assessment
- Personal profile data
- Training goals and experience
- Equipment and injury information

### Localization

The application currently supports:

- English
- Polish
- Russian
- Ukrainian

Translations are separated by application module and are used across the frontend and server-rendered pages.

## Tech Stack

### Backend

- Python
- Flask
- SQLAlchemy
- Flask-Migrate
- Flask-Login
- Flask-Mail
- Authlib
- PostgreSQL
- Jinja2

### Frontend

- HTML
- CSS
- JavaScript
- TypeScript
- Jinja templates

### Development

- Git
- GitHub
- pytest
- pytest-cov
- python-dotenv

## Project Structure

The project is split into a web layer and a backend layer.

```
NosiFit/
│
├── backend/
│   ├── app/
│   │   ├── dashboard/
│   │   ├── models/
│   │   ├── recovery/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── training/
│   │
│   └── config.py
│
├── web/
│   └── app/
│       ├── i18n/
│       ├── routes/
│       ├── templates/
│       ├── static/
│       │   ├── css/
│       │   ├── js/
│       │   └── ts/
│       └── ...
│
├── migrations/
├── requirements.txt
├── run.py
└── README.md
```

The backend contains the main application logic, services, models and training/recovery calculations. The web layer contains Flask routes, Jinja templates and frontend assets.

## Training & Recommendation System

One of the main parts of NosiFit is the training analysis system.

Training recommendations can use information such as:

- Previous workouts
- Exercise load
- Training frequency
- Muscle load
- User experience
- Weak and strong areas
- Recovery state
- Available equipment
- Injuries and limitations

The project also contains a training load calculation system with separate logic for exercises, repetitions, timed exercises, sessions and physiological factors.

## Dashboard Analytics

The dashboard combines information from several modules instead of showing training data separately.

The daily overview can include:

- Daily balance
- Training score and load
- Recovery score
- Sleep
- Nutrition
- Water intake
- Recommendations

The heatmap is used to view daily activity and balance over time, with a calendar view for inspecting individual days.

## Installation

Clone the repository:

```bash
git clone https://github.com/YaroslavFedorak/NosiFit.git
cd NosiFit
```

Create and activate a virtual environment:

### Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
SECRET_KEY=

DATABASE_URL=

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

MAIL_USERNAME=
MAIL_PASSWORD=
```

NosiFit uses PostgreSQL. Set `DATABASE_URL` to your local PostgreSQL connection string.

Run the database migrations:

```bash
flask db upgrade
```

Start the development server:

```bash
python run.py
```

The application will run on:

```
http://localhost:5000
```

## Current Status

NosiFit is an active personal project and is still being developed.

The main application areas are already implemented:

- Authentication and OAuth
- Training and workout management
- Training plans
- Training load analysis
- Recovery tracking
- Nutrition tracking
- Dashboard analytics
- Recommendations
- Profile management
- Onboarding and assessment
- Localization

Current development is focused on improving the existing modules, refining the dashboard and analytics, and continuing to improve the overall structure of the application.

## Future Plans

- More detailed training and recovery analytics
- More personalized recommendations
- Further nutrition improvements
- Better mobile and responsive support
- Performance improvements
- More integrations and client interfaces

## Author

**Yaroslav Fedorak**

GitHub: https://github.com/YaroslavFedorak
