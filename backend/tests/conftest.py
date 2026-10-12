import os

# tests need no real DB for health/security; provide dummy settings before app import
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/x")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-123")
