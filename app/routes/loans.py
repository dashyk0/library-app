from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import date, timedelta, datetime
from .. import db
from ..models import Loan, BookCopy, Reader, Book

loans_bp = Blueprint('loans', __name__, url_prefix='/loans')

#список всех выдач
@loans_bp.route('/')
@login_required
def index():
    if not current_user.is_librarian():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.index'))
    
    status = request.args.get('status', 'active')
    
    if status == 'active':
        loans = Loan.query.filter_by(return_date=None).order_by(Loan.due_date).all()
    elif status == 'history':
        loans = Loan.query.filter(Loan.return_date.isnot(None)).order_by(Loan.return_date.desc()).all()
    else:
        loans = Loan.query.order_by(Loan.issue_date.desc()).all()
    
    return render_template('loans/index.html', loans=loans, status=status)

#выбор книги для выдачи
@loans_bp.route('/select-book')
@login_required
def select_book():
    if not current_user.is_librarian():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Book.query
    if search:
        query = query.filter(
            Book.title.ilike(f'%{search}%') | 
            Book.author.has(full_name.ilike(f'%{search}%'))
        )
    
    books = query.order_by(Book.title).paginate(page=page, per_page=10)
    return render_template('loans/select_book.html', books=books, search=search)

#выдача книги
@loans_bp.route('/issue/<int:book_id>', methods=['GET', 'POST'])
@login_required
def issue_book(book_id):
    if not current_user.is_librarian():
        flash('Доступ запрещён. Только библиотекарь может выдавать книги.', 'danger')
        return redirect(url_for('books.show', id=book_id))
    
    book = Book.query.get_or_404(book_id)
    available_copy = book.copies.filter_by(status='available').first()
    
    if not available_copy:
        flash(f'Нет доступных экземпляров книги "{book.title}"', 'danger')
        return redirect(url_for('books.show', id=book_id))
    
    if request.method == 'POST':
        reader_id = request.form.get('reader_id')
        days = int(request.form.get('days', 14))
        
        if not reader_id:
            flash('Выберите читателя', 'danger')
            return redirect(url_for('loans.issue_book', book_id=book_id))
        
        reader = Reader.query.get_or_404(reader_id)
        
        loan = Loan(
            copy_id=available_copy.id,
            reader_id=reader.reader_id,
            librarian_id=current_user.id,
            due_date=date.today() + timedelta(days=days)
        )
        
        available_copy.status = 'issued'
        db.session.add(loan)
        db.session.commit()
        
        flash(f'Книга "{book.title}" выдана читателю {reader.user.full_name or reader.user.username} на {days} дней', 'success')
        return redirect(url_for('books.show', id=book_id))
    
    readers = Reader.query.all()
    return render_template('loans/issue_form.html', book=book, readers=readers)

#выбор книги для возврата
@loans_bp.route('/select-return-book')
@login_required
def select_return_book():
    if not current_user.is_librarian():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    # Показываем только книги, у которых есть активные выдачи
    query = Book.query.join(BookCopy).join(Loan).filter(Loan.return_date == None).distinct()
    
    if search:
        query = query.filter(
            Book.title.ilike(f'%{search}%') | 
            Book.author.has(full_name.ilike(f'%{search}%'))
        )
    
    books = query.order_by(Book.title).paginate(page=page, per_page=10)
    return render_template('loans/select_return_book.html', books=books, search=search)

#возврат книги
@loans_bp.route('/return/<int:book_id>/select-reader', methods=['GET', 'POST'])
@login_required
def select_reader_for_return(book_id):
    if not current_user.is_librarian():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.index'))
    
    book = Book.query.get_or_404(book_id)
    
    # Находим читателей, у которых есть активная выдача этой книги
    readers_with_loan = Reader.query.join(Loan).join(BookCopy).filter(
        BookCopy.book_id == book_id,
        Loan.return_date == None
    ).distinct().all()
    
    if request.method == 'POST':
        reader_id = request.form.get('reader_id')
        if not reader_id:
            flash('Выберите читателя', 'danger')
            return redirect(url_for('loans.select_reader_for_return', book_id=book_id))
        
        # Находим активную выдачу
        active_loan = Loan.query.join(BookCopy).filter(
            BookCopy.book_id == book_id,
            Loan.return_date == None,
            Loan.reader_id == reader_id
        ).first()
        
        if active_loan:
            active_loan.return_date = datetime.now()
            active_loan.copy.status = 'available'
            
            # Расчёт штрафа при просрочке
            today = date.today()
            if active_loan.due_date < today:
                days_overdue = (today - active_loan.due_date).days
                active_loan.fine_amount = days_overdue * 10
                flash(f'Книга "{book.title}" возвращена с просрочкой {days_overdue} дней. Штраф: {active_loan.fine_amount} руб.', 'warning')
            else:
                flash(f'Книга "{book.title}" успешно возвращена', 'success')
            
            db.session.commit()
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Активная выдача не найдена', 'danger')
            return redirect(url_for('loans.select_reader_for_return', book_id=book_id))
    
    return render_template('loans/select_reader_for_return.html', book=book, readers=readers_with_loan)