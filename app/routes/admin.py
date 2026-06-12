from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import func #SQL-функции 
from .. import db
from ..models import User, Reader, Loan, Book, BookCopy

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/') #Привязка URL /admin/ к функции dashboard()
@login_required#Только авторизованные пользователи
def dashboard():
    if not current_user.is_librarian():
        abort(403)
    
    total_books = Book.query.count()
    available_books = BookCopy.query.filter_by(status='available').count()
    issued_books = BookCopy.query.filter_by(status='issued').count()
    overdue_loans = Loan.query.filter(Loan.return_date == None, Loan.due_date < func.current_date()).count()
    recent_loans = Loan.query.order_by(Loan.issue_date.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html',
        total_books=total_books,
        available_books=available_books,
        issued_books=issued_books,
        overdue_loans=overdue_loans,
        recent_loans=recent_loans)

@admin_bp.route('/users')
@login_required
def users():
    if not current_user.is_admin():
        flash('Доступ запрещён. Требуются права администратора.', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    #Извлечение параметров запроса
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    #Построение запроса с поиском
    query = User.query #объект запроса SQLAlchemy к таблице users
    if search:
        query = query.filter(User.username.ilike(f'%{search}%') | User.email.ilike(f'%{search}%'))
    
    users = query.order_by(User.id).paginate(page=page, per_page=20)
    return render_template('admin/users.html', users=users, search=search)


#эндпоинт обрабатывает POST-запросы на изменение роли пользователя
@admin_bp.route('/users/<int:user_id>/change-role', methods=['POST'])
@login_required
def change_role(user_id):
    if not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    if user_id == current_user.id:
        flash('Нельзя изменить свою роль', 'danger')
        return redirect(url_for('admin.users'))
    
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    
    if new_role in ['reader', 'librarian', 'admin']:
        user.role = new_role
        db.session.commit()
        flash(f'Роль пользователя {user.username} изменена на {new_role}', 'success')
    else:
        flash('Некорректная роль', 'danger')
    
    return redirect(url_for('admin.users'))