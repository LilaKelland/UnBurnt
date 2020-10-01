import time
import requests
from statemachine import StateMachine, State
import json
from time import gmtime
from time import strftime
import datetime
from requests.exceptions import RequestException
import numpy
import apns2

# Handles ardunio data - writes to - unburnttemp.json - temp and time data for ios app via unBurntAPI.py, 
#   unburntstate.json - cooking state for ios app via unBurntAPI.py
# Reads initial cooking parameters written by ios via unBurntAPI.py - unburntconfig.json
# Sends push notifications for check times and too hot/ too cold/ on fire through pushed.co 


lDeviceToken = "53363e77461b9c7d01851cb0a7e81676a3f4fb552e5b7e8381cb3ef16a3446b3"
mDeviceToken = "a8de10202dbe14830fd08af9c8b447c8872fdbe320d03f5cf86c8e9805bf69b5"
deviceToken = [lDeviceToken, mDeviceToken]


def alert(deviceToken, body, title, sound):
  """for ios UnBurnt app"""
  cli = apns2.APNSClient(mode="prod",client_cert="/Users/lilakelland/Documents/apns-prod.pem")
  alert = apns2.PayloadAlert(body= body, title= title)
  payload = apns2.Payload(alert=alert, sound = sound)
  n = apns2.Notification(payload=payload, priority=apns2.PRIORITY_LOW)
  for i in range (2):
    response = cli.push(n=n, device_token = deviceToken[i], topic = 'com.lilakelland.tryAlamoFirePost')
    print("yay ", i, deviceToken[i]) 
  print(response.status_code)
  assert response.status_code == 200, response.reason
  assert response.apns_id
 

#Set up statemachine to handle cooking states:
class tempStateMachine(StateMachine):
  
    cold = State('Cold', initial=True)
    cooking = State('Cooking')
    burning = State('Burning')

    intialWarmUp = cold.to(cooking) #(when first time temp > lowtemp)
    heatToBurn = cooking.to(burning) #(slope > isBurninf and temp > high temp)
    stopBurning = burning.to(cooking) #when temp < high temp add a too cold warning
    turnOff = cooking.to(cold) #when in cooking and temp too low for 5 min or more 

tempState = tempStateMachine()


def slope_intercept(x1,y1,x2,y2):
    """Determine temperature rate of change - indicative of burning?"""
    try:
      slope = (y2 - y1) / (x2 - x1)
      #print("slope = {}".format(slope))
      #intercept = y1 - slope * x1    
      return (slope)
    except: 
      return (1)

#Initialize variables
tempOverTime = []
timeElapse = [] 
"""defaultLowTemp = 70
defaultHighTemp = 100
defaultCheckTime = 30000"""
isHot = False

def is_float(val):
    try:
        num = float(val)
    except ValueError:
        return(False)
    return(True)

def setCookingParameters():
    """Set by ios app - "tryAlamoFirePost" via UnBurntAPI.py"""
    with open('unburntconfig.json', 'r') as openfile: 
        configData = json.load(openfile)
    lowTemp = 70
    highTemp = 100
    checkTime = 30000
    
    if (is_float(configData["lowTemp"])): 
        lowTemp = float(configData["lowTemp"])
        defaultLowTemp = lowTemp
    if (is_float(configData["highTemp"])):  
        highTemp = float(configData["highTemp"])
        defaultHighTemp = highTemp
    if (is_float(configData["lowTemp"])): 
        checkTime = float(configData["checkTime"])
        #defaultCheckTime
    return(lowTemp, highTemp, checkTime)


#TODO need to be able to update temp without restarting timer**

while True:
  (lowTemp, highTemp, checkTime) = setCookingParameters()
  end = time.time()
  now = datetime.datetime.now()
  #compare and recheck cooking parameters for updates?
  # Get temperature from ardunio and generate elapsed times 

#Cold to warming up initial state:
  if (tempState.current_state == tempState.cold):
      tooColdCount = 0
      stateStatus = {
          "state": "cold"
          }
      with open("unburntstate.json", "w") as outfile: 
          json.dump(stateStatus, outfile)
      
      try: 
          temp = requests.get("http://192.168.7.82/")
          tempf = float(temp.json()["tempf"])

          temptry = {
            "tempf": tempf,
            "timeElapse": "Stopped (will start when over {} F)".format(lowTemp),
            "checkTimer": "Stopped (will start when over {} F)".format(lowTemp),
            "timeStamp": now.strftime("%A %I:%M %p")
            }
          with open("unburnttemp.json", "w") as outfile: 
              json.dump(temptry, outfile)

          timeElapse = [] # list of time
          tempOverTime = [] # list of temperatures
          tempCount = 0
          
          tempOverTimeData = {
            "lowTempLimit": lowTemp,
            "highTempLimit": highTemp,
            "tempCount": tempCount,
            "tempOverTime" : tempOverTime,
            "timeElapse" : timeElapse
          }
          with open("UnBurntChart.json", "w") as outfile: 
                  json.dump(tempOverTimeData, outfile)

      except RequestException:
          print("Still cold - something is up with the ardunio connnection")
    
      if tempf > lowTemp:
          title = "Now we're cooking - TIMER STARTED!"
          body = "It's {} F.".format(tempf)
          sound = 'chime'
          alert(deviceToken, body, title, sound)
          
          start = time.time()
          timerstart = start
        
          tempState.intialWarmUp()

  elif (tempState.current_state != tempState.cold):  
    try:
      #Check BBQ Timer 
        if ((end - timerstart) >= checkTime):
            timeMinute = round(checkTime/60,2)
            print("end - timerstart ", end - timerstart)
            print("end- start (total time) ", end-start)
            timerstart = time.time()
            print("end - timerstart ", end - timerstart)
            #print(timeMinute)
            title = "{} Minute Checkpoint".format(timeMinute)
            body = "How's it looking? Timer resetting."
            sound = 'chime'
            alert(deviceToken, body, title, sound)

        temp = requests.get("http://192.168.7.82/")
        tempf = float(temp.json()["tempf"])

        timeElapse.append(end - start) # list of time
        tempOverTime.append(tempf) # list of temperatures
        tempCount = len(tempOverTime)
        
        tempOverTimeData = {
          "lowTempLimit": lowTemp,
          "highTempLimit": highTemp,
          "tempCount": tempCount,
          "tempOverTime" : tempOverTime,
          "timeElapse" : timeElapse
         }
        with open("UnBurntChart.json", "w") as outfile: 
                json.dump(tempOverTimeData, outfile)
        
        temptry = {
              "tempf": tempf,
              "timeElapse": strftime("%M:%S", gmtime(timeElapse[-1])),
              "checkTimer": strftime("%M:%S", gmtime(checkTime - (end - timerstart))),
              "timeStamp": now.strftime("%A %H:%M:%S")
              }
        with open("unburnttemp.json", "w") as outfile: 
              json.dump(temptry, outfile)
          
      #Cooking State:
        if tempState.current_state == tempState.cooking:
            stateStatus = {
                "state": "cooking"
                }
              
            with open("unburntstate.json", "w") as outfile: 
              json.dump(stateStatus, outfile)

           #Initialize temp variables 
            if tempf < highTemp:
              isHot = False

            if tempf > lowTemp:
              isCold = False
              shutDownTimer = time.time()
           
            try:
              #Is burning?  Check temperature slope to determine:
              slope = slope_intercept(timeElapse[-2],tempOverTime[-2],timeElapse[-1],tempOverTime[-1])
            except(IndexError):
              slope = 1
            
            # On fire?
            if (slope > 4) and (tempf > highTemp):
                title = "On FIRE!"
                body = "It's {} F.".format(tempf)
                sound = 'chime'
                alert(deviceToken, body, title, sound)
              
                tempState.heatToBurn() # To 'burning' state (no more alerts til cool)
            
          # Too hot?
            if tempf > highTemp:
                if (isHot == False) or (end - tooHotTimer >= 30):
                  tooHotTimer = time.time()
                  shutDownTimer = time.time()
                  isHot = True
                  title = "Too HOT!"
                  body = "It's {} F.".format(tempf)
                  sound = 'chime'
                  alert(deviceToken, body, title, sound)

          # Too cold?
            elif tempf < lowTemp:
                if (isCold == False):
                    tooColdTimer = time.time()
                    shutDownTimer = time.time()
                    isCold = True

                    title = "Turn UP the BBQ!"
                    body = "Cooled down to {} F.".format(tempf)
                    sound = 'chime'
                    alert(deviceToken, body, title, sound)

                elif (end - shutDownTimer >= 200):
                    title = "Enjoy your food!"
                    body = "Shutting down."
                    sound = 'chime'
                    alert(deviceToken, body, title, sound)
                    
                    tempState.turnOff()

                elif (end - tooColdTimer) >= 60:
                    tooColdTimer = time.time()
                    title = "Turn UP the BBQ!"
                    body = "Cooled down to {} F.".format(tempf)
                    sound = 'chime'
                    alert(deviceToken, body, title, sound)
              
      #Burning State:
        if (tempState.current_state == tempState.burning):
            stateStatus = {
              "state": "burning"
              }
            with open("unburntstate.json", "w") as outfile: 
              json.dump(stateStatus, outfile)
            if tempf < highTemp:
                tempState.stopBurning() # Back to 'cooking' state 

    except RequestException:
      print("network error with sensor")
      print(timeElapse) #date time instead


 #change sound for for timer
 #bbq slam for checkpoints
 #Fire for on fire
  #TODO - add it variable to adjust reminder time and noise?  ()
 
 #TODO update parameters
  
  
