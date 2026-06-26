from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from config import db, login_manager
from functools import wraps
import requests
from models import User, Property, Review, Order

app = Flask(__name__)
app.config['SECRET_KEY'] = 'advancsec'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agency.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager.init_app(app)

login_manager.login_view = 'login'
login_manager.login_message = 'Будь-ласка, увійдіть у систему'

@app.route('/register', methods=['GET', 'POST'])
def register():
    from models import User
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not username or not email or not password:
            flash('Будь-ласка, заповніть всі поля.', 'warning')
            
        elif password != confirm_password:
            flash('Паролі не співпадають', 'danger')
            
        elif User.query.filter_by(username=username).first():
            flash('Користувач з таким іменем вже існує', 'danger')
            
        elif User.query.filter_by(email=email).first():
            flash('Користувача з такою електроною поштою вже існує', 'danger')
            
        else:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            
            flash('Реєстрація успішна! Увійдіть у систему', 'success')
            
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    from models import User
    
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Будь ласка, заповніть всі поля', 'warning')
        
        else:
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                flash('Вхід виконано успішно !', 'success')
                next_page = request.args.get('next')
                
                return redirect (next_page or url_for('dashboard'))
            
            else:
                flash('Невірне ім\'я користувача або пароль.','danger')
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Ви вийшли з системи', 'info')
    
    return redirect(url_for('index'))
 
def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Будь-ласка, увійдіть у систему.','warning')
                return redirect(url_for('login'))
            
            if current_user.is_admin != True:
                flash('У вас немає прав доступу до цієї сторінки.', 'danger')
                
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
    
@app.route('/')
def index():
    properties = Property.query.limit(6).all()
    
    reviews = Review.query.filter_by(is_approved=True).all()
    
    try:
        response = requests.get('https://api.exchangerate-api.com/v4/latest/USD')
        rates = response.json()['rates']
    except:
        rates = None

    return render_template('index.html',
                           properties=properties,
                           reviews=reviews,
                           rates=rates)
    
@app.route('/catalog')
def catalog():
    properties = Property.query.all()
    
    return render_template('catalog.html', properties=properties)

@app.context_processor
def inject_rates():
    try:
        response = requests.get('https://api.exchangerate-api.com/v4/latest/USD')
        rates = response.json()['rates']
    except:
        rates = None
        
    return dict(rates=rates)

@app.route('/reviews')
def reviews():
    reviews = Review.query.filter_by(is_approved=True).all()
    
    return render_template('review.html', reviews=reviews)

@app.route('/reviews/add', methods=['POST'])
@login_required
def add_review():
    text = request.form.get('text', '').strip()
    rating_val = request.form.get('rating')
    
    if not text:
        flash('Текст відгуку не може бути порожнім.', 'warning')
        return redirect(url_for('reviews'))
    
    try:
        rating = int(rating_val) if rating_val else 5
    except ValueError:
        rating = 5

    new_review = Review(
        text=text, 
        user_id=current_user.id, 
        rating=rating,        
        is_approved=False      
    )
    
    db.session.add(new_review)
    db.session.commit()
    
    flash('Дякуємо! Ваш відгук успішно надіслано на модерацію.', 'success')
    return redirect(url_for('reviews'))

@app.route('/property/<int:id>')
def property_detail(id):
    property = Property.query.get_or_404(id)
    
    return render_template('property.html', property=property)

@app.route('/cart/clear', methods=['POST'])
@login_required
def cart_clear():
    Order.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('Кошик очищено.', 'info')
    return redirect(url_for('cart'))

@app.route('/cart/add/<int:property_id>', methods=['POST'])
@login_required
def cart_add(property_id):

    existing = Order.query.filter_by(
        user_id=current_user.id,
        property_id=property_id
    ).first()
    
    if existing:
        flash('Вже є у кошику', 'warning')
    else:
        order = Order(user_id=current_user.id, property_id=property_id)
        db.session.add(order)
        db.session.commit()
        flash('Додано в кошик!', 'success')
    
    return redirect(url_for('property_detail', id=property_id))

@app.route('/cart')
@login_required
def cart():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    total = sum(o.property.price_usd for o in orders)
    
    return render_template('cart.html', orders=orders, total=total)

@app.route('/dashboard')
@login_required
def dashboard():
    if getattr(current_user, 'is_admin', False):
        
        properties = Property.query.all()
        reviews = Review.query.all()
        users = User.query.all()
        
        return render_template('admin_dashboard.html', properties=properties, reviews=reviews, users=users)
    
    user_orders = Order.query.filter_by(user_id=current_user.id).all()
    
    return render_template('user_dashboard.html', orders=user_orders)
    
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin: 
            flash('Доступ заборонено. Ця сторінка лише для адміністраторів.', 'danger')
            
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/admin')
@admin_required
def admin_dashboard():
    properties = Property.query.all()
    reviews = Review.query.all()
    users = User.query.all()
    
    return render_template('admin_dashboard.html', properties=properties, reviews=reviews, users=users)


@app.route('/admin/property/add', methods=['POST'])
@login_required
def admin_add_property():

    if not getattr(current_user, 'is_admin', False):
        flash('У вас немає прав доступу до цієї дії.', 'danger')
        return redirect(url_for('dashboard'))
    
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    price_usd = request.form.get('price_usd', '').strip()
    address = request.form.get('address', '').strip()
    image_url = request.form.get('image_url', '').strip()
    

    if not title or not price_usd:
        flash('Назва об\'єкта та ціна є обов\'язковими для заповнення!', 'warning')
        
        return redirect(url_for('dashboard'))
    
    try:

        new_property = Property(
            title=title,
            description=description,
            price_usd=float(price_usd),
            address=address,
            image_url=image_url
        )
        db.session.add(new_property)
        db.session.commit()
        flash('Новий об\'єкт нерухомості успішно додано!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Помилка при збереженні в базу: {str(e)}', 'danger')
        
    return redirect(url_for('dashboard'))

@app.route('/admin/property/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_property(id):
    property_to_delete = Property.query.get_or_404(id)
    db.session.delete(property_to_delete)
    db.session.commit()
    
    flash('Обʼєкт видалено з каталогу.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/review/approve/<int:review_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_approve_review(review_id):
    review = Review.query.get_or_404(review_id)
    review.is_approved = True
    db.session.commit()
    flash('Відгук успішно схвалено й опубліковано!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/review/reject/<int:review_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_reject_review(review_id):
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash('Відгук відхилено та видалено з бази даних.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/payment/<int:order_id>', methods=['GET', 'POST'])
@login_required
def simulate_payment(order_id):

    order = Order.query.get_or_404(order_id)
    
    if request.method == 'POST':

        order.is_paid = True 
        db.session.commit()
        
        flash('✨ Оплата пройшла успішно! Об\'єкт заброньовано.', 'success')
        return redirect(url_for('cart'))
        
    return render_template('payments.html', order=order)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("База створена")
    app.run(debug=True)