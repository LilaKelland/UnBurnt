# UnBurntAPI.py
# July 2020

# passes current temp and times from ardunio via unBurnt.py to ios through unBurntTempp.json 
# reads in config from ios app via from unBurntConfig.json: highTemp, lowTemp, checkTime 
# passes state from UnBurnt.py via unBurntState.json to ios app
# grabs tokens for APNS push notifications when initally set

from bottle import Bottle, response, request
import json
from bson.json_util import loads
from bson.json_util import dumps
from pymongo import MongoClient
from pprint import pprint

client = MongoClient("mongodb://127.0.0.1:27017/pymongo_test")
db = client.pymongo_test
app = Bottle()

@app.route('/getTempTime')
def getTempTime():
    """Current temps, time/date, time left to check BBQ, total cook time"""
    tempSensorData = db.unBurntTemp.find_one({"_id": "unBurntTemp_id"})
    pprint(tempSensorData)
    return json.loads(dumps(tempSensorData))


@app.route('/getState')
def getState():
    """cooking state"""
    stateStatus = db.unBurntState.find_one({"_id": "unBurntState_id"})
    pprint(stateStatus)
    return json.loads(dumps(stateStatus))


@app.route('/getTempTimeArray')
def getTempTimeArray():
    """Temperature and time lists for the chart view"""
    tempTimetry = db.unBurntChart.find_one({"_id": "unBurntChart_id"})
    return json.loads(dumps(tempTimetry))


@app.route('/setToken')
def getToken():
    """Get token for APNS"""

    token = request.GET.get("tokenString")
    setToken(token)

def setToken(token):
    tokenData = {
          "token": token,
    }
    db.unBurntToken.insert_one(tokenData)

     # with open("token.json", "w") as outfile: 
      #  json.dump(tokenData, outfile)


@app.route('/cookingParameters')
def getCookingParameters():
    """Retreives cooking parameters from ios"""

    try:
        lowTemp = request.GET.get("lowTemp")
        highTemp = request.GET.get("highTemp")
        checkTime = request.GET.get("checkTime")
        print(lowTemp, highTemp, checkTime)
        
        cookingParameters = {
            "lowTemp" : str(lowTemp),
            "highTemp" : str(highTemp),
            "checkTime" : str(checkTime)
            }
        print(cookingParameters)
        db.unBurntConfig.update_one({"_id": "unBurntConfig_id"}, {"$set":{
            "lowTemp" : str(lowTemp),
            "highTemp" : str(highTemp),
            "checkTime" : str(checkTime)
        }}, upsert=True)

        """with open("unBurntConfig.json", "w") as outfile: 
            json.dump(cookingParameters, outfile) """
        return("success")
        
    except:
        return("didn't work")

@app.route('/fakeArduino')
#simulated sensors - in times when sensors not available
def GetSimulatedArdunioValues():
    return({"tempf1":"69.25","tempf2":"70.0","flameValue":"1023"})

@app.route('/isBurning')
def getIsBurning():
    """#Retreives is_burning from ios"""

    try:
        isBurning = request.GET.get("isBurning")
        print("isBurning:", isBurning)
        actuallyBurning= {
            "is_burning" : isBurning  
            }
    
        with open("isBurning.json", "w") as outfile: 
            json.dump(actuallyBurning, outfile) 
           # db.unBurntIsBurning.insert_one({isburning})
            #TODO add grab /link other required info for supervised learning 
        return("success")
        
    except:
        return("didn't work")
    

@app.route('/getDefaultConfig')
def getDefaultConfig():
    """#Retreives cooking parameters from unBurntConfig.json for defaults"""
    configData = db.unBurntConfig.find_one({"_id": "unBurntConfig_id"})
    pprint(configData)

    return json.loads(dumps(configData))


if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=8080, debug=True, reloader=True) # run on pi server
    app.run(host='192.168.4.29', port=8080, debug=True, reloader=True) # run on computer


