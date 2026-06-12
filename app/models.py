from flask_login import UserMixin
from datetime import datetime, date
from . import db

# Ассоциативная таблица для связи книг и жанров (многие-ко-многим)
book_genres = db.Table('book_genres',
    db.Column('book_id', db.Integer, db.ForeignKey('books.id'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('genres.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='reader')
    full_name = db.Column(db.String(150))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    avatar = db.Column(db.String(255), nullable=True)  # хранит путь к файлу аватара
    
    reader = db.relationship('Reader', backref='user', uselist=False, cascade='all, delete-orphan')
    issued_loans = db.relationship('Loan', foreign_keys='Loan.librarian_id', backref='librarian', lazy='dynamic')
    
    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def is_librarian(self):
        return self.role in ['librarian', 'admin']
    
    def is_admin(self):
        return self.role == 'admin'

    #Строковое представление объекта для отладки
    def __repr__(self):
        return f'<User {self.username}>'

class Reader(db.Model):
    __tablename__ = 'readers'
    
    reader_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    library_card_number = db.Column(db.String(30), unique=True, nullable=False)
    birth_date = db.Column(db.Date)
    address = db.Column(db.Text)
    reader_category = db.Column(db.String(50))
    
    loans = db.relationship('Loan', backref='reader', lazy='dynamic', foreign_keys='Loan.reader_id')

class Author(db.Model):
    __tablename__ = 'authors'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    birth_year = db.Column(db.Integer)
    biography = db.Column(db.Text)
    
    books = db.relationship('Book', backref='author', lazy='dynamic')
    
    def __repr__(self):
        return f'<Author {self.full_name}>'

class Genre(db.Model):
    __tablename__ = 'genres'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    
    books = db.relationship('Book', secondary=book_genres, backref=db.backref('genres', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Genre {self.name}>'

class Book(db.Model):
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('authors.id'), nullable=False)
    isbn = db.Column(db.String(13), unique=True)
    publication_year = db.Column(db.Integer)
    publisher = db.Column(db.String(150))
    description = db.Column(db.Text)
    cover_image = db.Column(db.String(255))
    copies_total = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    copies = db.relationship('BookCopy', backref='book', lazy='dynamic', cascade='all, delete-orphan')
    
    @property # делает метод доступным как атрибут
    def copies_available(self):
        return self.copies.filter_by(status='available').count()
    
    def __repr__(self):
        return f'<Book {self.title}>'

class BookCopy(db.Model):
    __tablename__ = 'book_copies'
    
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    inventory_number = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='available')  # available, issued, lost, repair
    location = db.Column(db.String(100))
    acquired_date = db.Column(db.Date)
    
    loans = db.relationship('Loan', backref='copy', lazy='dynamic')
    
    def __repr__(self):
        return f'<BookCopy {self.inventory_number}>'

class Loan(db.Model):
    __tablename__ = 'loans'
    
    id = db.Column(db.Integer, primary_key=True)
    copy_id = db.Column(db.Integer, db.ForeignKey('book_copies.id'), nullable=False)
    reader_id = db.Column(db.Integer, db.ForeignKey('readers.reader_id'), nullable=False)
    librarian_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.DateTime)
    fine_amount = db.Column(db.Numeric(10, 2), default=0)
    
    @property 
    def is_overdue(self):
        if self.return_date:
            return False
        return date.today() > self.due_date
    
    def __repr__(self):
        return f'<Loan {self.id}>'