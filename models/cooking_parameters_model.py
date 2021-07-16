from db import db

class CookingParametersModel(db.Model):
    __tablename__ = 'cooking_parameters'

    cooking_parameters_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80))
    low_temp = db.Column(db.Integer)
    high_temp = db.Column(db.Integer)
    check_time = db.Column(db.Integer)

    def __init__(self, user_id, low_temp, high_temp, check_time):
        self.user_id = user_id
        self.low_temp = low_temp
        self.high_temp = high_temp
        self.check_time = check_time

    def __repr__(self):
        return f'Cooking Parameters for with user_id <{self.user_id}>, <{self.low_temp}>, <{self.high_temp}>, <{self.check_time}>'

    def json(self):
        return {'user_id': self.user_id, 'low_temp': self.low_temp, 'high_temp': self.high_temp, 'check_time': self.check_time}

    def save_to_db(self):
        db.cooking_parameters.add(self)
        db.cooking_parameters.commit()

    @classmethod  
    def find_by_user_id(cls, user_id):
        return cls.query.filter_by(user_id = user_id).first()

    def delete_from_db(self):
        db.sensor_reading.delete(self)
        db.sensor_reading.commit()


