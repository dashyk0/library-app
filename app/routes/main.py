from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from .. import db
from ..models import Loan

main_bp = Blueprint('main', __name__)

# Разрешённые расширения для файлов
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Проверка разрешённого расширения"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('books.index'))
    return render_template('landing.html')

@main_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', Loan=Loan)

@main_bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    user = current_user
    
    user.email = request.form.get('email')
    user.phone = request.form.get('phone')
    user.full_name = request.form.get('full_name')
    
    if user.reader:
        birth_date = request.form.get('birth_date')
        if birth_date:
            user.reader.birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
        user.reader.address = request.form.get('address')
    
    db.session.commit()
    flash('Данные успешно обновлены!', 'success')
    return redirect(url_for('main.profile'))

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/contacts')
def contacts():
    return render_template('contacts.html')

@main_bp.route('/terms')
def terms():
    return render_template('terms.html')

@main_bp.route('/privacy')
def privacy():
    return render_template('privacy.html')
    
@main_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not current_user.check_password(current_password):
        flash('Неверный текущий пароль', 'danger')
        return redirect(url_for('main.profile'))
    
    if new_password != confirm_password:
        flash('Новый пароль и подтверждение не совпадают', 'danger')
        return redirect(url_for('main.profile'))
    
    if len(new_password) < 4:
        flash('Пароль должен содержать минимум 4 символа', 'danger')
        return redirect(url_for('main.profile'))
    
    current_user.set_password(new_password)
    db.session.commit()
    flash('Пароль успешно изменён!', 'success')
    return redirect(url_for('main.profile'))

# Загрузка аватара
@main_bp.route('/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('Файл не выбран', 'danger')
        return redirect(url_for('main.profile'))
    
    file = request.files['avatar']
    if file.filename == '':
        flash('Файл не выбран', 'danger')
        return redirect(url_for('main.profile'))
    
    if file and allowed_file(file.filename):
        # Удаляем старый аватар если есть
        if current_user.avatar:
            old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars', current_user.avatar)
            if os.path.exists(old_path):
                os.remove(old_path)
        
        # Сохраняем новый аватар
        filename = secure_filename(file.filename)
        unique_filename = f"avatar_{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        
        # Создаём папку для аватаров если её нет
        avatar_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')
        os.makedirs(avatar_dir, exist_ok=True)
        
        filepath = os.path.join(avatar_dir, unique_filename)
        file.save(filepath)
        
        current_user.avatar = unique_filename
        db.session.commit()
        
        flash('Аватар успешно обновлён!', 'success')
    else:
        flash('Неподдерживаемый формат файла. Используйте JPG, PNG или GIF', 'danger')
    
    return redirect(url_for('main.profile'))