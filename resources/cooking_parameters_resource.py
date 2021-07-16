from flask_restful import Resource, reqparse
# from flask_jwt import jwt_required
from models.cooking_parameters_model import CookingParametersModel
import datetime

class CookingParameters(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('user_id', type=str, required=True, help='This feild cannot be left blank or invalid format') 
    parser.add_argument("low_temp", type=int, required=True, help='This feild cannot be left blank or invalid format')
    parser.add_argument("high_temp", type=int, required=True, help='This feild cannot be left blank or invalid format')
    parser.add_argument("check_time", type=int, required=True, help='This feild cannot be left blank or invalid format')
   
    def put(self): 
        data = CookingParameters.parser.parse_args()
        cooking_parameters = CookingParametersModel.find_by_user_id(data['user_id'])

        if cooking_parameters is None:
            cooking_parameters = CookingParametersModel(data['user_id'], data['low_temp'], data['high_temp'], data['check_time'])
        else:
            cooking_parameters.low_temp = data['low_temp']
            cooking_parameters.high_temp = data['high_temp']
            cooking_parameters.check_time = data['check_time']

        cooking_parameters.save_to_db()

        return cooking_parameters.json()

class DefaultCookingParameters(Resource):

    def get(self, user_id):
        default_cooking_parameters = CookingParametersModel.find_by_user_id(user_id)
        if default_cooking_parameters:
            return default_cooking_parameters.json()
        return {'message': 'user with user_id not found'}, 404

        # return({'user_id': default_cooking_parameters.user_id, 'low_temp': default_cooking_parameters.low_temp, 'high_temp': default_cooking_parameters.high_temp, 'check_time': default.check_time}
