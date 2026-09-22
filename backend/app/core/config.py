import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://hortifruti:hortifruti123@localhost:5432/hortifruti_erp")
SECRET_KEY = os.getenv("SECRET_KEY", "MUDE-ESTA-CHAVE-EM-PRODUCAO-MIN-32-CHARS")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480
REFRESH_TOKEN_EXPIRE_DAYS = 30
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
