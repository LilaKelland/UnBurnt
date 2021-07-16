from db import db


class SensorReadingModel(db.Model):
    __tablename__ = 'display_data'

    display_data_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80))
    left_temp = db.Column(db.Integer)
    right_temp = db.Column(db.Integer)
    working_temp = db.Column(db.Integer)
    flame_value = db.Column(db.Integer)
    is_left_temp_valid = db.Column(db.Boolean)
    is_right_temp_valid = db.Column(db.Boolean)
    is_flame_valid = db.Column(db.Boolean)
    state = db.Column(db.String(20))
    timestamp = db.Column(db.Integer)
    total_cook_time = db.Column(db.Integer)
    check_food_time = db.Column(db.Integer)
    is_actually_on_fire = db.Column(db.Boolean)
    

    def __init__(self, user_id, left_temp, is_left_temp_valid, right_temp, is_right_temp_valid, working_temp, flame_value, is_flame_valid, state, timestamp, total_cook_time, check_food_time, is_actually_on_fire=None):
        #TODO *********have temps as optional and:if left is None: self.left_temp = "" else: self.left_temp = left_temp
        self.user_id = user_id
        self.left_temp = left_temp
        self.is_left_temp_valid = is_left_temp_valid
        self.right_temp = right_temp
        self.is_right_temp_valid = is_right_temp_valid
        self.working_temp = working_temp
        self.flame_value = flame_value
        self.is_flame_valid = is_flame_valid
        self.state = state # only for calculating is on fire later..
        self.total_cook_time = total_cook_time
        self.check_food_time = check_food_time
        self.timestamp = timestamp
        self.is_actually_on_fire = None if is_actually_on_fire is None else True

    def __repr__(self):
        return f'Sensor reading for with user_id <{self.user_id}>, <{self.left_temp}>, <{self.is_left_temp_valid}>, <{self.right_temp}, <{self.is_right_temp_valid}, <{self.working_temp}>, <{self.flame_value}>, <{self.is_flame_valid}>, <{self.state}>, <{self.is_actually_on_fire}>'

    # def json(self):
    #     return {'user_id': self.user_id, 'low_temp': self.low_temp 'high_temp': self.high_temp, 'check_time': self.check_time}

    def save_to_db(self):
        db.display_data.add(self)
        db.display_data.commit()

    def save_turned_off_to_db(self, state, timestamp):
        self.state = state
        self.timestamp = timestamp
        self.save_to_db()

    @classmethod
    def find_all_readings_since_last_cold_state(cls, user_id):
        if (
            not cls.query([cls.timestamp])
            .filter_by(cls.state == "cold", user_id=user_id)
            .first()
        ):
            return cls.query.filter_by(cls.user.id == user_id).all()

        last_cold_timestamp = cls.query([cls.timestamp]).filter_by(cls.state == "cold", user_id = user_id).first()
        return cls.query.filter_by(user_id == user_id, cls.timestamp >= last_cold_timestamp).all()

    # def find_all_readings_since_last_cold_state(cls, user_id):
    #     if cls.query([timestamp]).filter_by(state == "cold", user_id = user_id).first():
    #         last_cold_timestamp = cls.query([timestamp]).filter_by(state == "cold", user_id = user_id).first()
    #         return cls.query.filter_by(user_id == user_id, timestamp >= last_cold_timestamp).all()
    #     else:
    #         return cls.query.filter_by(user.id == user_id).all()

    @classmethod  
    def find_by_user_id(cls, user_id):
        return cls.query.filter_by(user_id = user_id).first()

   
class DashboardDisplay:
    def __init__(self, user_id):
        self.user_id = user_id

    def get_guage_display_data(self):
        try:
            record = SensorReadingModel.find_by_user_id(self.user_id)
            return ({"working_temp": record.working_temp, 
                "left_temp": record.left_temp,
                "right_temp": record.right_temp,
                "is_left_temp_valid": record.is_left_temp_valid,
                 "is_right_temp_valid": record.is_right_temp_valid, 
                "state": record.state, 
                "timestamp": record.timestamp, 
                "total_cook_time": record.total_cook_time, 
                "check_food_time": record.check_food_time })
        except Exception as e:
            print(e)


class ChartDisplay:
    def __init__(self, user_id):
        self.user_id = user_id

    def get_chart_data(self):
        try:
            SensorReadingModel.find_all_readings_since_last_cold_state(self.user_id)
        except Exception as e:
            print(e)

    def format_chart_data(self):
        time_x = []
        temp_y = []

        for row in self.get_chart_data():
            time_x.append(row.total_cook_time)
            temp_y.append(row.working_temp)

        return({'time_x': time_x, 'temp_y': temp_y})
            


