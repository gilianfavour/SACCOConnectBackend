from datetime import timedelta

class Config:
     SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/saccoconnect_db'
     JWT_SECRET_KEY = "SACCOCOnnect" 
     JWT_EXPIRATION_DELTA = timedelta(minutes=10)
     
     SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT settings
     JWT_SECRET_KEY = 'your-jwt-secret-key'  # 🔑 must be set
     JWT_TOKEN_LOCATION = ['headers']        # where to look for the token
