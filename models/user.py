from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# Simulé : base utilisateur
users = {
    "admin": User(id=1, username="admin", password="admin123")
}

def get_user(username):
    return users.get(username)