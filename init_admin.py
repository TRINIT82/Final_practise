import sys
import os
import getpass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Тепер імпортуємо app і db з правильних місць
from app import app
from config import db
from models import User


def create_admin():
    with app.app_context():
        print("=== Створення облікового запису адміністратора ===\n")
       

        existing_admin = User.query.filter_by(role='admin').first()
        if existing_admin:
            print(f"Увага! Адміністратор вже існує в базі даних:")
            print(f"Ім'я: {existing_admin.username}, Email: {existing_admin.email}")
            confirm = input("Бажаєте створити ще одного адміністратора? (y/N): ").strip().lower()
            if confirm != 'y':
                print("Операцію скасовано.")
                return
       

        username = input("Введіть ім'я користувача (залиште порожнім для 'admin'): ").strip()
        if not username:
            username = 'admin'
           

        if User.query.filter_by(username=username).first():
            print(f"Помилка: Користувач з іменем '{username}' вже існує.")
            return


        email = input("Введіть email адміністратора (залиште порожнім для 'admin@example.com'): ").strip()
        if not email:
            email = 'admin@example.com'

        if User.query.filter_by(email=email).first():
            print(f"Помилка: Користувач з email '{email}' вже існує.")
            return


        print("\nВведіть пароль для адміністратора:")
        while True:
            password = getpass.getpass("Пароль: ")
            confirm_password = getpass.getpass("Підтвердіть пароль: ")
           
            if len(password) < 6:
                print("Пароль має містити щонайменше 6 символів.")
                continue
            if password != confirm_password:
                print("Паролі не співпадають. Спробуйте ще раз.")
                continue
            break


        try:
            admin = User(
                username=username,
                email=email,
                role='admin'
            )
            admin.set_password(password)
           
            db.session.add(admin)
            db.session.commit()
           
            print("Адміністратора успішно створено!")
            print(f"   Ім'я: {username}")
            print(f"   Email: {email}")
            print(f"   Роль: admin")
            print("Тепер ви можете увійти на сайт під цим обліковим записом.")
           
        except Exception as e:
            db.session.rollback()
            print(f"Сталася помилка при створенні адміністратора: {e}")