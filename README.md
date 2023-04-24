#### library-service


### How to run:

- Create venv: `python -m venv venv`
- Activate it: `venv/Scripts/activate`
- Install requirements: `pip install -r reqirements.txt`
- Create new Postgres DB & user
- Copy .env.sample -> .env and populate with all required data
- Run migrations: `python manage.py migrate`
- Run Redis Server: `docker run -d -p 6379:6379 redis`
- Run celery worker for task handling: `celery -A  library_service worker -l INFO -P solo`
- Run celery beat for the task scheduling: `celery -A library_service beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler`
- Create schedule for running sync in DB
- Run app: `python manage.py runserver`



