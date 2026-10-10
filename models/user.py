import os
import secrets

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash


class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


def _build_users():
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password_hash = os.environ.get("ADMIN_PASSWORD_HASH")

    if not password_hash:
        password = os.environ.get("ADMIN_PASSWORD")
        if not password:
            password = secrets.token_urlsafe(16)
            print(
                f"⚠️  ADMIN_PASSWORD non défini : mot de passe généré pour "
                f"'{username}' (changez-le en définissant ADMIN_PASSWORD ou "
                f"ADMIN_PASSWORD_HASH) : {password}"
            )
        password_hash = generate_password_hash(password)

    return {username: User(id=1, username=username, password_hash=password_hash)}


users = _build_users()


def get_user(username):
    return users.get(username)
