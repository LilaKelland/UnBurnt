from db import db

class TokenModel(db.Model):
    __tablename__ = 'token'

    token_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80))
    token = db.Column(db.String(80))

    def __init__(self, user_id, token):
        self.user_id = user_id
        self.token = token

    def __repr__(self):
        return f'APNS token for with user_id <{self.user_id}>, <{self.token}>'

    def json(self):
        return {'user_id': self.user_id, 'token': self.token}

    def save_to_db(self):
        db.token.add(self)
        db.token.commit()

    @classmethod  
    def find_by_user_id(cls, user_id):
        return cls.query.filter(user_id = user_id).all()
