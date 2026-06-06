from flask import Blueprint, render_template, Response, send_file, abort, request
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
import io
import csv
from sqlalchemy import func
from .. import db
from ..models import User, Loan, Book, BookCopy

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
def index():
    if not current_user.is_librarian():
        abort(403)
    
    stats = {
        'total_books': Book.query.count(),
        'total_loans': Loan.query.count(),
        'active_loans': Loan.query.filter_by(return_date=None).count(),
        'overdue_loans': Loan.query.filter(Loan.return_date == None, Loan.due_date < date.today()).count(),
    }
    
    if current_user.is_admin():
        librarians = User.query.filter(User.role.in_(['librarian', 'admin'])).all()
    else:
        librarians = [current_user]
    
    librarian_stats = []
    for lib in librarians:
        loans_issued = Loan.query.filter_by(librarian_id=lib.id).count()
        loans_returned = Loan.query.filter(Loan.librarian_id == lib.id, Loan.return_date != None).count()
        librarian_stats.append({
            'name': lib.full_name or lib.username,
            'issued': loans_issued,
            'returned': loans_returned
        })
    
    return render_template('reports/index.html', stats=stats, librarian_stats=librarian_stats)

@reports_bp.route('/popular-books')
@login_required
def popular_books():
    if not current_user.is_librarian():
        abort(403)
    
    popular = db.session.query(
        Book, func.count(Loan.id).label('loan_count')
    ).join(BookCopy, BookCopy.book_id == Book.id)\
     .join(Loan, Loan.copy_id == BookCopy.id)\
     .group_by(Book.id)\
     .order_by(func.count(Loan.id).desc())\
     .limit(20).all()
    
    books = [(book, count) for book, count in popular]
    return render_template('reports/popular_books.html', books=books)

@reports_bp.route('/popular-books-advanced')
@login_required
def popular_books_advanced():
    if not current_user.is_admin():
        abort(403)
    
    # Топ-10 книг
    top_books = db.session.query(
        Book, func.count(Loan.id).label('loan_count')
    ).join(BookCopy, BookCopy.book_id == Book.id)\
     .join(Loan, Loan.copy_id == BookCopy.id)\
     .group_by(Book.id)\
     .order_by(func.count(Loan.id).desc())\
     .limit(10).all()
    
    # Статистика по жанрам
    from ..models import Genre
    genre_stats = db.session.query(
        Genre.name, func.count(Loan.id).label('loan_count')
    ).join(Book.genres).join(BookCopy).join(Loan)\
     .group_by(Genre.id)\
     .order_by(func.count(Loan.id).desc())\
     .limit(5).all()
    
    months = []
    for i in range(11, -1, -1):
        month_date = date.today().replace(day=1) - timedelta(days=i*30)
        months.append(month_date.strftime('%Y-%m'))
    
    return render_template('reports/popular_books_advanced.html', 
                          top_books=top_books, 
                          genre_stats=genre_stats,
                          months=months)

@reports_bp.route('/librarians-stats')
@login_required
def librarians_stats():
    if not current_user.is_admin():
        abort(403)
    
    librarians = User.query.filter(User.role.in_(['librarian', 'admin'])).all()
    
    total_issued = 0
    total_returned = 0
    librarians_stats = []
    
    for lib in librarians:
        issued = Loan.query.filter_by(librarian_id=lib.id).count()
        returned = Loan.query.filter(Loan.librarian_id == lib.id, Loan.return_date != None).count()
        overdue = Loan.query.filter(
            Loan.librarian_id == lib.id, 
            Loan.return_date == None,
            Loan.due_date < date.today()
        ).count()
        on_time = Loan.query.filter(
            Loan.librarian_id == lib.id,
            Loan.return_date != None,
            Loan.due_date >= Loan.return_date
        ).count()
        
        avg_days_result = db.session.query(func.avg(Loan.due_date - Loan.issue_date)).filter(
            Loan.librarian_id == lib.id
        ).scalar()
        avg_days = int(avg_days_result.days) if avg_days_result else 0
        
        total_fine_result = db.session.query(func.sum(Loan.fine_amount)).filter(
            Loan.librarian_id == lib.id
        ).scalar() or 0
        total_fine = float(total_fine_result)
        
        total_issued += issued
        total_returned += returned
        
        efficiency = round((on_time / returned * 100) if returned > 0 else 0, 1)
        
        librarians_stats.append({
            'name': lib.full_name or lib.username,
            'issued': issued,
            'returned': returned,
            'overdue': overdue,
            'on_time': on_time,
            'avg_days': avg_days,
            'total_fine': total_fine,
            'efficiency': efficiency
        })
    
    librarians_stats.sort(key=lambda x: x['efficiency'], reverse=True)
    
    total_librarians = len(librarians)
    avg_issued = total_issued / total_librarians if total_librarians > 0 else 0
    
    return render_template('reports/librarians_stats.html',
                          librarians_stats=librarians_stats,
                          total_librarians=total_librarians,
                          total_issued=total_issued,
                          total_returned=total_returned,
                          avg_issued=avg_issued)

@reports_bp.route('/export/popular-books-csv')
@login_required
def export_popular_books_csv():
    if not current_user.is_admin():
        abort(403)
    
    popular = db.session.query(
        Book, func.count(Loan.id).label('loan_count')
    ).join(BookCopy, BookCopy.book_id == Book.id)\
     .join(Loan, Loan.copy_id == BookCopy.id)\
     .group_by(Book.id)\
     .order_by(func.count(Loan.id).desc())\
     .all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Рейтинг', 'Название книги', 'Автор', 'Год издания', 'Количество выдач'])
    
    for idx, (book, count) in enumerate(popular, 1):
        writer.writerow([
            idx,
            book.title,
            book.author.full_name,
            book.publication_year or '',
            count
        ])
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename=popular_books_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return response

@reports_bp.route('/export/librarians-stats-csv')
@login_required
def export_librarians_stats():
    if not current_user.is_admin():
        abort(403)
    
    librarians = User.query.filter(User.role.in_(['librarian', 'admin'])).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Библиотекарь', 'Выдано книг', 'Возвращено', 'Просрочек', 'Вовремя', 'Средний срок (дн)', 'Сумма штрафов', 'Эффективность'])
    
    for lib in librarians:
        issued = Loan.query.filter_by(librarian_id=lib.id).count()
        returned = Loan.query.filter(Loan.librarian_id == lib.id, Loan.return_date != None).count()
        overdue = Loan.query.filter(Loan.librarian_id == lib.id, Loan.return_date == None, Loan.due_date < date.today()).count()
        on_time = Loan.query.filter(Loan.librarian_id == lib.id, Loan.return_date != None, Loan.due_date >= Loan.return_date).count()
        avg_days_result = db.session.query(func.avg(Loan.due_date - Loan.issue_date)).filter(Loan.librarian_id == lib.id).scalar()
        avg_days = int(avg_days_result.days) if avg_days_result else 0
        total_fine_result = db.session.query(func.sum(Loan.fine_amount)).filter(Loan.librarian_id == lib.id).scalar() or 0
        efficiency = round((on_time / returned * 100) if returned > 0 else 0, 1)
        
        writer.writerow([
            lib.full_name or lib.username,
            issued,
            returned,
            overdue,
            on_time,
            avg_days,
            float(total_fine_result),
            f"{efficiency}%"
        ])
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename=librarians_stats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return response

@reports_bp.route('/export/loans')
@login_required
def export_loans():
    if not current_user.is_librarian():
        abort(403)
    
    loans = Loan.query.order_by(Loan.issue_date.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Книга', 'Читатель', 'Библиотекарь', 'Дата выдачи', 'Срок возврата', 'Дата возврата', 'Штраф'])
    
    for loan in loans:
        writer.writerow([
            loan.id,
            loan.copy.book.title,
            loan.reader.user.full_name or loan.reader.user.username,
            loan.librarian.full_name or loan.librarian.username,
            loan.issue_date.strftime('%d.%m.%Y %H:%M'),
            loan.due_date.strftime('%d.%m.%Y'),
            loan.return_date.strftime('%d.%m.%Y %H:%M') if loan.return_date else '',
            float(loan.fine_amount) if loan.fine_amount else 0
        ])
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename=loans_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return response

@reports_bp.route('/export/books')
@login_required
def export_books():
    if not current_user.is_librarian():
        abort(403)
    
    books = Book.query.order_by(Book.title).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Название', 'Автор', 'Год', 'ISBN', 'Издательство', 'Всего экземпляров', 'Доступно'])
    
    for book in books:
        writer.writerow([
            book.id,
            book.title,
            book.author.full_name,
            book.publication_year or '',
            book.isbn or '',
            book.publisher or '',
            book.copies_total,
            book.copies_available
        ])
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename=books_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return response

@reports_bp.route('/export/users')
@login_required
def export_users():
    if not current_user.is_admin():
        abort(403)
    
    users = User.query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Логин', 'Email', 'Роль', 'Полное имя', 'Телефон', 'Дата регистрации', 'Номер билета'])
    
    for user in users:
        writer.writerow([
            user.id,
            user.username,
            user.email,
            user.role,
            user.full_name or '',
            user.phone or '',
            user.created_at.strftime('%d.%m.%Y') if user.created_at else '',
            user.reader.library_card_number if user.reader else ''
        ])
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename=users_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return response