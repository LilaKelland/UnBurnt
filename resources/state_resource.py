from flask_restful import Resource, reqparse
from models.state_model import StateModel

class CookingState(Resource):

    def get(self, user_id):
        cooking_state = StateModel.find_by_user_id(user_id)
        if cooking_state:
            return cooking_state.json()
        return {'message': 'cooking state with that user_id not found'}, 404