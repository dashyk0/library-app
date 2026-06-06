from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime
from .. import db
from ..models import Loan

main_bp = Blueprint('main', __name__)

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