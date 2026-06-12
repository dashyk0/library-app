# создаёт и настраивает Flask-приложение, регистрирует все компоненты и возвращает готовый объект app
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager #Управление сессиями пользователей
from flask_migrate import Migrate
from .config import Config

db = SQLAlchemy()
login_manager = LoginManager() #Экземпляр менеджера авторизации
login_manager.login_view = 'auth.login' #URL для редиректа неавторизованного пользователя
login_manager.login_message_category = 'info'#CSS-класс для flash-сообщения
migrate = Migrate()

def create_app():
    #Фабрика приложения 
    app = Flask(__name__) #__name__ помогает Flask найти папки templates и static
    app.config.from_object(Config) # подключаем настройки

    #привязывает созданные ранее объекты к конкретному приложению
    db.init_app(app) 
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Импортируем модели
    from . import models

    # Регистрируем blueprints
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.books import books_bp
    from .routes.loans import loans_bp
    from .routes.admin import admin_bp
    from .routes.reports import reports_bp
    from .routes.readers import readers_bp
    from .routes.authors import authors_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(loans_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(readers_bp)
    app.register_blueprint(authors_bp)

    return app

@login_manager.user_loader #Декоратор, регистрирует функцию для загрузки пользователя
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))