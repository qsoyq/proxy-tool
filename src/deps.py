import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from settings import AppSettings

security = HTTPBasic()


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = AppSettings().basic_auth_user.encode("utf8")
    is_correct_username = secrets.compare_digest(current_username_bytes, correct_username_bytes)
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = AppSettings().basic_auth_passwd.encode("utf8")
    is_correct_password = secrets.compare_digest(current_password_bytes, correct_password_bytes)
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
