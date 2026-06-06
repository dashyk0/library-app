from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from .. import db
from ..models import User, Reader, Loan

readers_bp = Blueprint('readers', __name__, url_prefix='/readers')

@readers_bp.route('/')
@login_required
def index():
    if not current_user.is_librarian():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Reader.query.join(User)
    if search:
        query = query.filter(
            User.full_name.ilike(f'%{search}%') | 
            User.username.ilike(f'%{search}%') | 
            Reader.library_card_number.ilike(f'%{search}%')
        )
    
    readers = query.paginate(page=page, per_page=15)
    return render_template('readers/index.html', readers=readers, search=search)

@readers_bp.route('/<int:id>')
@login_required
def show(id):
    if not current_user.is_librarian() and current_user.id != id:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.index'))
    
    reader = Reader.query.get_or_404(id)
    active_loans = reader.loans.filter_by(return_date=None).all()
    loan_history = reader.loans.filter(Loan.return_date.isnot(None)).order_by(Loan.return_date.desc()).limit(10).all()
    
    return render_template('readers/show.html', reader=reader, active_loans=active_loans, loan_history=loan_history)

@readers_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    if not current_user.is_librarian() and current_user.id != id:
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.index'))
    
    reader = Reader.query.get_or_404(id)
    user = reader.user
    
    if request.method == 'POST':
        user.full_name = request.form.get('full_name')
        user.phone = request.form.get('phone')
        reader.birth_date = request.form.get('birth_date') or None
        reader.address = request.form.get('address')
        reader.reader_category = request.form.get('reader_category')
        
        db.session.commit()
        flash('Данные читателя обновлены', 'success')
        return redirect(url_for('readers.show', id=reader.reader_id))
    
    return render_template('readers/edit.html', reader=reader, user=user)

@readers_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    if not current_user.is_admin():
        flash('Доступ запрещён. Только администратор может удалять читателей.', 'danger')
        return redirect(url_for('readers.index'))
    
    reader = Reader.query.get_or_404(id)
    name = reader.user.full_name or reader.user.username
    
    active_loans = reader.loans.filter_by(return_date=None).count()
    if active_loans > 0:
        flash(f'Невозможно удалить читателя "{name}". У него есть активные выдачи.', 'danger')
        return redirect(url_for('readers.show', id=id))
    
    user = reader.user
    db.session.delete(reader)
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Читатель "{name}" удалён', 'success')
    return redirect(url_for('readers.index'))