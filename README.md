# Django Online Course Assessment

This project extends IBM Developer Skills Network's public `tfjzl-final-cloud-app-with-database` starter repository with the Coursera final project's multiple-choice assessment feature. The project keeps the starter app's `onlinecourse` models and routes, including `Course`, `Lesson`, `Learner`, and `Enrollment`; the starter did not include the assessment models or final-project implementation.

## Included

- Course list, course details, lessons, login, registration, and enrollment.
- `Question`, `Choice`, and `Submission` models. A question belongs to a course and uses `question_text`; choices use `choice_text`; a submission belongs to an `Enrollment` and stores selected choices.
- Admin inlines for lessons, questions, and choices.
- Authenticated, enrolled learners can submit one radio-button answer per question; unanswered questions receive zero points.
- Server-side validation rejects choices from a different question and submissions for another course.
- Weighted automatic scoring with per-question answer review and an 80% passing threshold.
- Idempotent demo-data setup and Django tests.

The starter's `admin.py` imported four models. For the rubric's seven imported classes, this implementation adds the three assessment models (`Question`, `Choice`, and `Submission`) to those four imports. `Enrollment` remains the existing relationship model and is reached from `Submission` through the model field.

## Local setup

Requirements: Python 3.11 or newer and Git. The repository pins Django 5.2.18, the current 5.2 LTS security patch at the time this project was prepared.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py makemigrations onlinecourse
python manage.py migrate
python manage.py seed_demo
python manage.py check
python manage.py test
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. The demo account usernames are `admin` and `demo`. `seed_demo` generates random local-only passwords and saves them to `.local-credentials.txt`, which is excluded from Git. Run the command again if the local credentials file is lost; it resets the demo account passwords and refreshes the demo course data.

## Assessment flow

1. Log in as `demo`.
2. Open **Python and Django Essentials** from the course list.
3. Enroll if needed, then answer the assessment.
4. Submit to see the saved submission, score, pass/fail result, and answer review.

The `admin` account can manage courses and lessons, create questions and choices through inline forms, and inspect submissions.

## Source attribution

Starter project: [IBM Developer Skills Network — tfjzl-final-cloud-app-with-database](https://github.com/ibm-developer-skills-network/tfjzl-final-cloud-app-with-database). The starter is provided under Apache License 2.0; the original license is included in this repository.
