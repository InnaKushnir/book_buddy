#### library-service

RESTful API for Library service.

 #### Features
* Users can register, login and logout in the library_service using email and password.
* The API allows for manage the inventory of books.
* The API allows for manage books borrowing.
* The API allows for manage customers.
* The API allows for displaying notifications.
* The API allows for handling payments.
* The API provides the Swagger documentation.

#### Installation
##### Python3 must be already installed.
```
git clone https://github.com/InnaKushnir/book_buddy
cd book_buddy
python -m venv venv
venv/Scripts/activate
pip install -r requirements.txt
```
* Copy .env.sample -> .env and populate with all required data.

#### Run the following necessary commands
```
python manage.py migrate
```

* Docker is used to run a Redis container that is used as a broker for Celery.
```
docker run -d -p 6379:6379 redis
```
The Celery library is used to schedule tasks and launch workers.
* Starting the Celery worker is done with the command.
```
celery -A library_service worker -l INFO -P solo
```
* The Celery scheduler is configured as follows.
```
celery -A library_service beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
```
* Create schedule for running sync in DB.
```
python manage.py runserver
```
#### Test user

* Email: `admin@gmail.com`
* Password: `12345admin`

* Register on the website using the link.

`http://127.0.0.1:8000/api/user/register/`

* Get the token using the link. 

`http://127.0.0.1:8000/api/user/token/`



### How to run with Docker:

- Copy .env.sample -> .env and populate with all required data
- `docker-compose up --build`
- Create admin user & Create schedule for running sync in DB
- Run app: `python manage.py runserver`
