from datetime import timedelta

class Config:
     SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/saccoconnect_db'
     JWT_SECRET_KEY = "SACCOCOnnect" 
     JWT_EXPIRATION_DELTA = timedelta(minutes=10)
