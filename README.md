
# BookStore App

A full-stack bookstore management web application built with Django's MVT (Model-View-Template) architecture. This app provides an intuitive e-commerce experience for browsing, managing, and purchasing books, complete with user authentication, real-time search, and asynchronous email handling.


## Features

- Real-time Search, Filtering, and Pagination: Dynamic interactions synced with URL parameters for seamless user experience without page reloads.
- User Authentication: Secure signup with email verification using Celery for asynchronous task processing (passwords set within 24-hour limit).
- E-commerce Functionality: Cart management, order processing, stock tracking, and payment calculations (subtotals, discounts, totals).
- Responsive UI: Designed with Tailwind CSS for mobile-friendly layouts, including side drawers for filters on small screens.
- Efficient Backend: Optimized ORM queries, form handling, and model relationships (e.g., Author, Publisher, Genre, Stock) to reduce redundancy.
- Additional Tools: Axios for AJAX requests, session-based cart logic, and reusable components for tables, pagination, and cards.

## Tech Stack

**Client:** HTML Template,Tailwind CSS, Flowbite (for UI components), Axios (for API calls).

**Server:** Django (MVT architecture), PostgreSQL (or SQLite for development),Django ORM, Celery (for async tasks like email verification).

**Other:** Custom user models, middleware for permissions, SMTP for password resets.


## Prerequisites
- Python 3.8+

- Node.js (optional, for Tailwind builds if customized)

- Redis (for Celery task queue)
## Installation

1. Clone the Repository:
```bash
git clone https://github.com/AyushThapaChhetri/Django_Learnings.git
cd BookStoreApp
```

2. Set Up Virtual Environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
3. Install Dependencies:
```bash
pip install -r requirements.txt
```
4. Configure Environment:
- Copy .env.example to .env and update settings (e.g., SECRET_KEY, DATABASE_URL, EMAIL_HOST for SMTP).
```bash
DB_NAME=db_name 
DB_USER=postgres 
DB_PASSWORD=db_password
DB_HOST=localhost
DB_PORT=5432
super_user_email= superuser@gmail.com
super_user_password= super_admin_password


host_email=host_email_you_set
host_password=host_password_you_set


CELERY_BROKER_URL=redis://localhost:6379/0
USER_EXPIRATION_HOURS=24
```

- For Celery: Ensure Redis is running (redis-server).



5. Run Migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

6. Create Superuser (for admin access):
```bash
python manage.py createsuperuser
```

7. Run the Development Server:

```bash
( Terminal 1)
python manage.py runserver
```

8. Run Celery (in a separate terminal for async tasks):
```bash
(Terminal 2)
celery -A Project_B worker -l info -P solo    
(Terminal 3 - Monitor Celery with Flower)
celery -A Project_B flower
```

9. Run Tailwind:
```bash
(Terminal 4)
python manage.py tailwind start
```


## Usage/Examples

- Browse Books: Visit the homepage to search, filter by price/genre, and paginate results.
- User Signup/Login: Register with email verification; reset passwords via email.
- Manage Inventory: Admins can CRUD books, stocks, authors, and publishers via the dashboard.
- Shopping Cart: Add items, view cart (updates in real-time), and checkout with order tracking.
- Recycle Bin: Soft-delete books and manage from a dedicated view.

## Appendices

![Image](https://github.com/user-attachments/assets/c2759713-f02a-45bd-b1c4-bd1331df5f40)

![Image](https://github.com/user-attachments/assets/54b72c5e-3941-43be-a267-08a6d1d615cf)

![Image](https://github.com/user-attachments/assets/8ae3e5c5-3f11-494d-8a9c-3a367a4f1b85)

![Image](https://github.com/user-attachments/assets/7616e802-3fc0-4fad-8e4a-9ce51b40439b)

![Image](https://github.com/user-attachments/assets/d4fbf7e8-866f-4ee7-8864-fe710a04feac)
