#### library-service
Book:
Title: str
Author: str
Cover: Enum: HARD | SOFT
Inventory: positive int
Daily fee: decimal (in $USD)

User (Customer):
Email: str
First name: str
Last name: str
Password: str
Is staff: bool
Borrowing:
Borrow date: date
Expected return date: date
Actual return date: date
Book id: int
User id: int
Payment:
Status: Enum: PENDING | PAID
Type: Enum: PAYMENT | FINE
Borrowing id: int
Session url: Url  # url to stripe payment session
Session id: str  # id of stripe payment session
Money to pay: decimal (in $USD)  # calculated borrowing total price



