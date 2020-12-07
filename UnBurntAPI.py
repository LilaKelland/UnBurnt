# UnBurntAPI.py
# July 2020

# passes current temp and times from ardunio via unBurnt.py to ios through unBurntTempp.json 
# reads in config from ios app via from unBurntConfig.json: highTemp, lowTemp, checkTime 
# passes state from UnBurnt.py via unBurntState.json to ios app
# grabs tokens for APNS push notifications when initally set

from bottle import Bottle, response, request
import json

app = Bottle()

@app.route('/getTempTime')
def getTempTime():
    """Current temps, time/date, time left to check BBQ, total cook time for ios"""
   
    with open('unBurntTemp.json', 'r') as openfile: 
        tempData = json.load(openfile) 
        print(tempData)

    tempSensorData = {
        "tempf1" : tempData["tempf1"],
        "is_tempf1_valid" : tempData["is_tempf1_valid"],
        "tempf2": tempData["tempf2"],
        "is_tempf2_valid" : tempData["is_tempf2_valid"],
        "flameValue": tempData["flameValue"],
        "is_flame_valid" : tempData["is_flame_valid"],
        "timeElapsed" : tempData["timeElapsed"],
        "checkTimer" : tempData["checkTimer"],
        "timeNow" : tempData["timeNow"],
        "timeStamp" : str(tempData["timeStamp"])
        }

    return(json.dumps(tempSensorData))


@app.route('/getState')
def getState():
    """Reads cooking state"""
   
    with open('unBurntState.json', 'r') as openfile: 
        stateData = json.load(openfile) 
        print(stateData)

    stateStatus = {
        "state": str(stateData["state"])
        }

    return(json.dumps(stateStatus))


@app.route('/getTempTimeArray')
def getTempTimeArray():
    """Temperature and time lists for the chart view"""

    with open('unBurntChart.json', 'r') as openfile: 
        TempTimeData = json.load(openfile) 

    tempTimetry = {
        "highTempLimit": TempTimeData["highTempLimit"],
        "lowTempLimit": TempTimeData["lowTempLimit"],
        "tempCount": TempTimeData["tempCount"],
        "tempArray": TempTimeData["tempOverTime1"],
        "tempArray2": TempTimeData["tempOverTime2"],
        "timeArray": TempTimeData["timeElapse"]
        }

    return(json.dumps(tempTimetry))


@app.route('/setToken')
def getToken():
    """# Get token from ios"""

    token = request.GET.get("tokenString")
    setToken(token)

def setToken(token):
    tokenData = {
          "token": token,
    }

    with open("token.json", "w") as outfile: 
        json.dump(tokenData, outfile)


@app.route('/cookingParameters')
def getCookingParameters():
    """Retreives cooking parameters from ios"""

    try:
        lowTemp = request.GET.get("lowTemp")
        highTemp = request.GET.get("highTemp")
        checkTime = request.GET.get("checkTime")
        print(lowTemp, highTemp, checkTime)
        cookingParameters = {
            "lowTemp" : lowTemp,
            "highTemp" : highTemp,
            "checkTime" : checkTime
            }
    
        with open("unBurntConfig.json", "w") as outfile: 
            json.dump(cookingParameters, outfile) 

        return("success")
        
    except:
        return("didn't work")


@app.route('/isBurning')
def getIsBurning():
    """#Retreives is_burning from ios"""

    try:
        isBurning = request.GET.get("isBurning")
        print(isBurning)
        actuallyBurning= {
            "is_burning" : isBurning  
            }
    
        with open("isBurning.json", "w") as outfile: 
            json.dump(actuallyBurning, outfile) 

        return("success")
        
    except:
        return("didn't work")
    

@app.route('/getDefaultConfig')
def getDefaultConfig():
    """#Retreives cooking parameters from unBurntConfig.json for defaults"""

    with open("unBurntConfig.json", 'r') as openfile: 
            configData = json.load(openfile) 

    return(json.dumps(configData))

    
if __name__ == '__main__':
    app.run(host='192.168.0.19', port=8080, debug=True, reloader=True)
    #server 192.168.0.35 - but set to 0.0.0.0
    #computer 192.168.0.19

