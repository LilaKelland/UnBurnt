from flask_restful import Resource, reqparse
from models.token_model import TokenModel

class Token(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('user_id', type=str, required=True, help='This feild cannot be left blank or invalid format') 
    parser.add_argument('token', type=str, required=True, help='This feild cannot be left blank or invalid format') 
    def post(self):
        data = Token.parser.parse_args()
        token = TokenModel(data['user_id'], data['token'])
    
        try:
            token.save_to_db() 
            check_token = TokenModel.find_by_user_id(data['user_id'])
            if not check_token:
                raise Exception
            
        except Exception as e:
            print(e)
            return {"message": "An error occurred inserting the item"}, 500 

        return(token.json()), 201 

   