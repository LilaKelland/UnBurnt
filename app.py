# Unburnt REST API - to be run concurrently with UnBurnt.py 

import os

from flask import Flask
from flask_restful import Resource, Api, reqparse
from resources.cooking_parameters_resource import CookingParameters, DefaultCookingParameters
from resources.display_resource import ChartDisplayResource, DashboardDisplayResource
from resources.token_resource import Token
from resources.state_resource import CookingState


app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///unburnt.db'#os.environ.get('DATABASE_URL?sslmode=require', 'sqlite:///unburnt.db').replace('postgres://', 'postgresql://') # second value is default value
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
api = Api(app)

api.add_resource(DashboardDisplayResource, '/dashboardDisplay')
api.add_resource(ChartDisplayResource, '/chartDisplay')
api.add_resource(CookingParameters, '/cookingParameters')
app.add_resource(DefaultCookingParameters, '/defaultCookingParameters')
api.add_resource(CookingState), '/cookingState')
api.add_resource(Token, '/token')
# api.add_resource(Arduino, '/arduino')

if __name__ == "__main__":
    from db import db
    db.init_app(app)
    app.run(host='192.168.4.29', port=5000, debug=True)


# @app.route('/getTempTime')
# def getTempTime():
#     """Current temps, time/date, time left to check BBQ, total cook time"""
#     tempSensorData = db.unBurntTemp.find_one({"_id": "unBurntTemp_id"})
#     pprint(tempSensorData)
#     return json.loads(dumps(tempSensorData))


# @app.route('/getState')
# def getState():
#     """cooking state"""
#     stateStatus = db.unBurntState.find_one({"_id": "unBurntState_id"})
#     pprint(stateStatus)
#     return json.loads(dumps(stateStatus))


# @app.route('/getTempTimeArray')
# def getTempTimeArray():
#     """Temperature and time lists for the chart view"""
#     tempTimetry = db.unBurntChart.find_one({"_id": "unBurntChart_id"})
#     return json.loads(dumps(tempTimetry))


# @app.route('/setToken')
# def getToken():
#     """Get token for APNS"""

#     token = request.GET.get("tokenString")
#     setToken(token)

# def setToken(token):
#     tokenData = {
#           "token": token,
#     }
#     db.unBurntToken.insert_one(tokenData)

#      # with open("token.json", "w") as outfile: 
#       #  json.dump(tokenData, outfile)




# @app.route('/fakeArduino')
# #simulated sensors - in times when sensors not available
# def GetSimulatedArdunioValues():
#     return({"tempf1":"69.25","tempf2":"70.0","flameValue":"1023"})

# @app.route('/isBurning')
# def getIsBurning():
#     """#Retreives is_burning from ios"""

#     try:
#         isBurning = request.GET.get("isBurning")
#         print("isBurning:", isBurning)
#         actuallyBurning= {
#             "is_burning" : isBurning  
#             }
    
#         with open("isBurning.json", "w") as outfile: 
#             json.dump(actuallyBurning, outfile) 
#            # db.unBurntIsBurning.insert_one({isburning})
#             #TODO add grab /link other required info for supervised learning 
#         return("success")
        
#     except:
#         return("didn't work")
    




# if __name__ == '__main__':
#     #app.run(host='0.0.0.0', port=8080, debug=True, reloader=True) # run on pi server
#     app.run(host=' 10.0.0.9', port=8080, debug=True, reloader=True) # run on computer


