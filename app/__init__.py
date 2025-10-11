from flask import Flask
from app.extensions import db,migrate

from app.models.userModel import User
from app.models.auditModel import AuditLog
from app.models.loanModal import Loan
from app.models.notificationModel import Notification
from app.models.saccoModel import Sacco
from app.models.transactionModel import Transaction
from app.models.savingModel import Saving

from app.controllers.AuthController import auth_bp


#application factory function
def create_app():
    
    #app instance
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    db.init_app(app)
    migrate.init_app(app,db)


    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    @app.route("/")
    def home():
        return "SACCOConnect"
    
  
    
    

    return app

