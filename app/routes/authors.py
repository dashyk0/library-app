from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from .. import db
from ..models import Author

authors_bp = Blueprint('authors', __name__, url_prefix='/authors')

# список авторов
@authors_bp.route('/')
@login_required
def index():
    if not current_user.is_librarian():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Author.query
    if search:
        query = query.filter(Author.full_name.ilike(f'%{search}%'))
    
    authors = query.order_by(Author.full_name).paginate(page=page, per_page=20)
    return render_template('authors/index.html', authors=authors, search=search)

@authors_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if not current_user.is_librarian():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('authors.index'))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        birth_year = request.form.get('birth_year')
        biography = request.form.get('biography')
        
        if not full_name:
            flash('Имя автора обязательно', 'danger')
            return redirect(url_for('authors.create'))
        
        author = Author(
            full_name=full_name,
            birth_year=birth_year or None,
            biography=biography
        )
        db.session.add(author)
        db.session.commit()
        
        flash(f'Автор "{full_name}" добавлен', 'success')
        return redirect(url_for('authors.index'))
    
    return render_template('authors/create.html')

@authors_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    if not current_user.is_librarian():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('authors.index'))
    
    author = Author.query.get_or_404(id)
    
    if request.method == 'POST':
        author.full_name = request.form.get('full_name')
        author.birth_year = request.form.get('birth_year') or None
        author.biography = request.form.get('biography')
        db.session.commit()
        flash(f'Автор "{author.full_name}" обновлён', 'success')
        return redirect(url_for('authors.index'))
    
    return render_template('authors/edit.html', author=author)

@authors_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    if not current_user.is_librarian():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('authors.index'))
    
    author = Author.query.get_or_404(id)
    name = author.full_name
    
    # Проверяем, есть ли книги у этого автора
    if author.books.count() > 0:
        flash(f'Невозможно удалить автора "{name}". У него есть книги в библиотеке.', 'danger')
        return redirect(url_for('authors.index'))
    
    db.session.delete(author)
    db.session.commit()
    flash(f'Автор "{name}" удалён', 'success')
    return redirect(url_for('authors.index'))