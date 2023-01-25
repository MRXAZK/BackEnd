from pydantic import BaseSettings, EmailStr


class Settings(BaseSettings):
    BASE_URL: str
    MONGO_INITDB_ROOT_USERNAME: str
    MONGO_INITDB_ROOT_PASSWORD: str
    MONGO_INITDB_DATABASE: str
    MONGO_INITDB_HOST: str
    MONGO_INITDB_OPTION: str
    # MONGO_INITDB_PORT: int
    MONGO_INITDB_COLLECTION_USER: str
    MONGO_INITDB_COLLECTION_OCR: str
    
    AWS_ACCESS_KEY: str
    AWS_SECRET_KEY: str
    AWS_REGION: str
    AWS_BUCKET_NAME: str
    
    JWT_PUBLIC_KEY: str
    JWT_PRIVATE_KEY: str
    REFRESH_TOKEN_EXPIRES_IN: int
    ACCESS_TOKEN_EXPIRES_IN: int
    JWT_ALGORITHM: str

    CLIENT_ORIGIN: str

    EMAIL_HOST: str
    EMAIL_PORT: int
    EMAIL_USERNAME: str
    EMAIL_PASSWORD: str
    EMAIL_FROM: EmailStr

    class Config:
        env_file = './.env'


settings = Settings()
