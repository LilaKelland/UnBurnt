# UnBurntAPI.py
# July 2020

# passes current temp and times from  (and ardunio) via unburnttempp.json 
# reads in config from ios app via from unburntconfig.json: highTemp, lowTemp, checkTime, fireAlert 
# passes state from UnBurnt.py via unburntstate.json to ios app

#TODO
#ios app will then display current temp, current state, and swipe for graph and state over time with colour
#ios app will have stop and start/restart buttonsp

from bottle import Bottle, response, request
import json
import numpy as np

app = Bottle()


#Current temp, timer to check BBQ, total Cook time 
@app.route('/getTempTime')
def getTempTime():
   
    with open('unburnttemp.json', 'r') as openfile: 
        tempData = json.load(openfile) 
        print(tempData)

    temptry = {
        "tempf": tempData["tempf"],
        "timeElapse": str(tempData["timeElapse"]),
        "checkTimer": str(tempData["checkTimer"]),
        "timeStamp": str(tempData["timeStamp"])
        }

    return(json.dumps(temptry))


#Cooking state    
@app.route('/getState')
def getState():
   
    with open('unburntstate.json', 'r') as openfile: 
        stateData = json.load(openfile) 
        print(stateData)

    statetry = {
        "state": str(stateData["state"])
        }

    return(json.dumps(statetry))

# Temperature and time lists for the chart view
@app.route('/getTempTimeArray')
def getTempTimeArray():
   
    with open('unBurntChart.json', 'r') as openfile: 
        TempTimeData = json.load(openfile) 

    tempTimetry = {
        "highTempLimit": TempTimeData["highTempLimit"],
        "lowTempLimit": TempTimeData["lowTempLimit"],
        "tempCount": TempTimeData["tempCount"],
        "tempArray": TempTimeData["tempOverTime"],
        "timeArray": TempTimeData["timeElapse"]
        
        }

    return(json.dumps(tempTimetry))

# Get token from ios
@app.route('/setToken')
def getToken():
    token = request.GET.get("tokenString")
    setToken(token)

def setToken(token):
    tokenData = {
          "token": token,
    }
    with open("token.json", "w") as outfile: 
        json.dump(tokenData, outfile)


#Retreives cooking parameters from ios
@app.route('/cookingParameters')
def getCookingParameters():
    lowTemp = request.GET.get("lowTemp")
    highTemp = request.GET.get("highTemp")
    checkTime = request.GET.get("checkTime")
    print(lowTemp, highTemp, checkTime)
    cookingParameters = {
        "lowTemp" : lowTemp,
        "highTemp" : highTemp,
        "checkTime" : checkTime
        }
  
    with open("unburntconfig.json", "w") as outfile: 
        json.dump(cookingParameters, outfile) 

    return("success")

#Retreives cooking parameters from unburntconfig.json for defaults
@app.route('/getDefaultConfig')
def getDefaultConfig():

    with open("unburntconfig.json", 'r') as openfile: 
            configData = json.load(openfile) 

    """configDatatry = {
        lowTemp: configData["lowTemp"],
        highTemp: configData["highTemp"],
        checkTime: configData["checkTime"]
    }"""

    return(json.dumps(configData))


    
if __name__ == '__main__':
    app.run(host='192.168.7.87',debug=True)
