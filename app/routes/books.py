from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from .. import db
from ..models import Book, Author, Genre, BookCopy, Loan

books_bp = Blueprint('books', __name__, url_prefix='/books')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_cover_image(file):
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        return unique_filename
    return None

@books_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Book.query
    if search:
        query = query.filter(Book.title.ilike(f'%{search}%'))
    
    books = query.order_by(Book.title).paginate(page=page, per_page=12)
    
    popular_books = db.session.query(
        Book, func.count(Loan.id).label('loan_count')
    ).join(BookCopy, BookCopy.book_id == Book.id)\
     .join(Loan, Loan.copy_id == BookCopy.id)\
     .filter(Loan.return_date != None)\
     .group_by(Book.id)\
     .order_by(func.count(Loan.id).desc())\
     .limit(5).all()
    
    popular_books_list = []
    for book, count in popular_books:
        book.loan_count = count
        popular_books_list.append(book)
    
    return render_template('books/index.html', books=books, search=search, popular_books=popular_books_list)

@books_bp.route('/<int:id>')
@login_required
def show(id):
    book = Book.query.get_or_404(id)
    available_copies = book.copies.filter_by(status='available').count()
    return render_template('books/show.html', book=book, available_copies=available_copies)

@books_bp.route('/delete-select')
@login_required
def delete_select():
    if not current_user.is_librarian():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('books.index'))
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Book.query
    if search:
        query = query.filter(Book.title.ilike(f'%{search}%'))
    
    books = query.order_by(Book.title).paginate(page=page, per_page=10)
    return render_template('books/delete_select.html', books=books, search=search)

@books_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if not current_user.is_librarian():
        flash('Доступ запрещён. Требуются права библиотекаря.', 'danger')
        return redirect(url_for('books.index'))
    
    authors = Author.query.order_by(Author.full_name).all()
    genres = Genre.query.order_by(Genre.name).all()
    
    if request.method == 'POST':
        title = request.form.get('title')
        author_id = request.form.get('author_id')
        isbn = request.form.get('isbn')
        publication_year = request.form.get('publication_year')
        publisher = request.form.get('publisher')
        description = request.form.get('description')
        copies_total = int(request.form.get('copies_total', 1))
        cover_file = request.files.get('cover_image')
        
        if not title or not author_id:
            flash('Название и автор обязательны', 'danger')
            return redirect(url_for('books.create'))
        
        cover_image = save_cover_image(cover_file)
        
        book = Book(
            title=title,
            author_id=author_id,
            isbn=isbn,
            publication_year=publication_year or None,
            publisher=publisher,
            description=description,
            copies_total=copies_total,
            cover_image=cover_image
        )
        db.session.add(book)
        db.session.flush()
        
        genre_ids = request.form.getlist('genres')
        for genre_id in genre_ids:
            genre = Genre.query.get(genre_id)
            if genre:
                book.genres.append(genre)
        
        for i in range(copies_total):
            copy = BookCopy(
                book_id=book.id,
                inventory_number=f'INV-{book.id}-{i+1}',
                status='available',
                location='Основной зал'
            )
            db.session.add(copy)
        
        db.session.commit()
        flash(f'Книга "{title}" успешно добавлена', 'success')
        return redirect(url_for('books.show', id=book.id))
    
    return render_template('books/create.html', authors=authors, genres=genres)

@books_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    if not current_user.is_librarian():
        flash('Доступ запрещён. Требуются права библиотекаря.', 'danger')
        return redirect(url_for('books.index'))
    
    book = Book.query.get_or_404(id)
    authors = Author.query.order_by(Author.full_name).all()
    genres = Genre.query.order_by(Genre.name).all()
    
    if request.method == 'POST':
        book.title = request.form.get('title')
        book.author_id = request.form.get('author_id')
        book.isbn = request.form.get('isbn')
        book.publication_year = request.form.get('publication_year') or None
        book.publisher = request.form.get('publisher')
        book.description = request.form.get('description')
        
        # Обновляем жанры
        book.genres = []
        genre_ids = request.form.getlist('genres')
        for genre_id in genre_ids:
            genre = Genre.query.get(genre_id)
            if genre:
                book.genres.append(genre)
        
        # Загружаем новую обложку
        cover_file = request.files.get('cover_image')
        if cover_file and cover_file.filename:
            cover_image = save_cover_image(cover_file)
            if cover_image:
                # Удаляем старую обложку если есть
                if book.cover_image:
                    old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], book.cover_image)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                book.cover_image = cover_image
        
        db.session.commit()
        flash(f'Книга "{book.title}" обновлена', 'success')
        return redirect(url_for('books.show', id=book.id))
    
    return render_template('books/edit.html', book=book, authors=authors, genres=genres)

# Удаление книги (доступно библиотекарю)
@books_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    if not current_user.is_librarian():
        flash('Доступ запрещён. Требуются права библиотекаря.', 'danger')
        return redirect(url_for('books.index'))
    
    book = Book.query.get_or_404(id)
    title = book.title
    
    # Удаляем обложку
    if book.cover_image:
        old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], book.cover_image)
        if os.path.exists(old_path):
            os.remove(old_path)
    
    # Удаляем связанные выдачи
    for copy in book.copies:
        Loan.query.filter_by(copy_id=copy.id).delete()
    
    # Удаляем экземпляры
    BookCopy.query.filter_by(book_id=book.id).delete()
    
    # Удаляем книгу
    db.session.delete(book)
    db.session.commit()
    
    flash(f'Книга "{title}" удалена', 'success')
    return redirect(url_for('books.delete_select'))