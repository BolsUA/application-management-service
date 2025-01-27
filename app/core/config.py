import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Application Management Service"
    DATABASE_URL = str(os.getenv("DATABASE_URL", "sqlite:///todo.db"))
    SECRET_KEY = str(os.getenv('SECRET_KEY', 'K%!MaoL26XQe8iGAAyDrmbkw&bqE$hCPw4hSk!Hf'))
    REGION = str(os.getenv('REGION'))
    USER_POOL_ID = str(os.getenv('USER_POOL_ID'))
    FRONTEND_URL = str(os.getenv('FRONTEND_URL'))
    S3_BUCKET_NAME = str(os.getenv("S3_BUCKET_NAME", "bolsua-storage-dev"))

    # AWS Cognito configuration
    COGNITO_KEYS_URL = f'https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json'


settings = Settings()
