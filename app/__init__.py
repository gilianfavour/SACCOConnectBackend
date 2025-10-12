from flask import Flask
from flask_cors import CORS
from app.extensions import db,migrate
from flask_jwt_extended import JWTManager

from app.models.userModel import User
from app.models.auditModel import AuditLog
from app.models.loanModal import Loan
from app.models.notificationModel import Notification
from app.models.saccoModel import Sacco
from app.models.transactionModel import Transaction
from app.models.savingModel import Saving

from app.controllers.AuthController import auth_bp
from app.controllers.saccoController import sacco_bp
from app.controllers.DashBoardController import dashboard_bp
from app.controllers.SavingController import saving_bp
from app.controllers.UserContoller import user_bp
from app.controllers.TransactionController import transaction_bp
from app.controllers.NotificationController import notification_bp


#application factory function
def create_app():
    
    #app instance
    app = Flask(__name__)
    CORS(app, origins="http://localhost:3000")
    app.config.from_object('config.Config')
    
    db.init_app(app)
    migrate.init_app(app,db)

    # JWT setup
    jwt = JWTManager(app)


    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(sacco_bp, url_prefix='/api/saccos')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(saving_bp, url_prefix='/api/savings')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(transaction_bp, url_prefix='/api/transactions')
    app.register_blueprint(notification_bp, url_prefix='/api/notifications')

    @app.route("/")
    def home():
        return "SACCOConnect"
    
  
    
    

    return app

