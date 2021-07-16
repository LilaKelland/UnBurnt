from db import db

class StateModel(db.Model):
    __tablename__ = 'state'

    state_model_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80))
    state = db.Column(db.String(80))

    def __init__(self, user_id, state):
        self.user_id = user_id
        self.state = state

    def __repr__(self):
        return f'Cooking state for with  <{self.user_id}>, <{self.state}> '

    def json(self):
        return {'user_id': self.user_id, 'state': self.state }

    def save_to_db(self):
        db.cooking_parameters.add(self)
        db.cooking_parameters.commit()

    @classmethod  
    def find_by_user_id(cls, user_id):
        # return(cls.query.filter(cls.user_id==user_id).all())
        return cls.query.filter_by(user_id = user_id).first()
