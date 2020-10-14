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

# reads ardunio data writen to unburnttemp.json - temp and time data for ios app via unBurntAPI.py, 
#   unburntstate.json - cooking state for ios app via unBurntAPI.py
# Reads initial cooking parameters written by ios via unBurntAPI.py - unburntconfig.json
# Sends push notifications for check times and too hot/ too cold/ on fire through apns2 to 
# predetermined (with device tokens specified) phones


l_device_token = "53363e77461b9c7d01851cb0a7e81676a3f4fb552e5b7e8381cb3ef16a3446b3"
m_device_token = "a8de10202dbe14830fd08af9c8b447c8872fdbe320d03f5cf86c8e9805bf69b5"
device_token = [l_device_token, m_device_token]
url = 

def alert(device_token, body, title, sound):
  """to send to ios UnBurnt app"""
  cli = apns2.APNSClient(mode="prod",client_cert="apns-prod.pem")
  alert = apns2.PayloadAlert(body= body, title= title)
  payload = apns2.Payload(alert=alert, sound = sound)
  n = apns2.Notification(payload=payload, priority=apns2.PRIORITY_LOW)
  for i in range (2):
    response = cli.push(n=n, device_token = device_token[i], topic = 'com.lilakelland.tryAlamoFirePost')
    print("yay ", i, device_token[i]) 
  print(response.status_code)
  assert response.status_code == 200, response.reason
  assert response.apns_id
 
class tempStateMachine(StateMachine):
    """Set up statemachine to handle cooking states"""
    cold = State('Cold', initial=True)
    cooking = State('Cooking')
    burning = State('Burning')

    intialWarmUp = cold.to(cooking) #(when first time temp > lowtemp)
    heatToBurn = cooking.to(burning) #(slope > isBurning and temp > high temp)
    stopBurning = burning.to(cooking) #when temp < high temp add a too cold warning
    turnOff = cooking.to(cold) #when in cooking and temp too low for 5 min or more 

tempState = tempStateMachine()

def slope_intercept(x1,y1,x2,y2):
    #Determine temperature rate of change - indicative of burning?
    try:
      slope = (y2 - y1) / (x2 - x1)   
      return (slope)
    except: 
      return (1)

def is_float(val):
    try:
        num = float(val)
    except ValueError:
        return(False)
    return(True)

def setCookingParameters():
    """Set by ios app - "tryAlamoFirePost" via UnBurntAPI.py" - reads from unburntconfig json file"""
    with open('unburntconfig.json', 'r') as openfile: 
        configData = json.load(openfile)
    #Initial case data set:     
    lowTemp = 70
    highTemp = 100
    checkTime = 30000
    
    if (is_float(configData["lowTemp"])): 
        lowTemp = float(configData["lowTemp"])
    if (is_float(configData["highTemp"])):  
        highTemp = float(configData["highTemp"])
    if (is_float(configData["lowTemp"])): 
        checkTime = float(configData["checkTime"])
    return(lowTemp, highTemp, checkTime)

#Initialize golbal variables
tempOverTime = []
timeElapse = [] 
isHot = False

while True:
  (lowTemp, highTemp, checkTime) = setCookingParameters()
  end = time.time()
  now = datetime.datetime.now()

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
          sound = 'fire.aiff'
          alert(device_token, body, title, sound)
          
          start = time.time()
          timerstart = start
        
          tempState.intialWarmUp()

  elif (tempState.current_state != tempState.cold):  
    try:
      #Check BBQ Timer to see if entering cool down phase
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
            alert(device_token, body, title, sound)

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
        with open("unBurntChart.json", "w") as outfile: 
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
            #Update unburntstate.json state to "cooking" 
            stateStatus = {
                "state": "cooking"
                }
            with open("unburntstate.json", "w") as outfile: 
              json.dump(stateStatus, outfile)

           #Determine if temperature is in the cooking range isHot 
            if tempf < highTemp:
              isHot = False

            if tempf > lowTemp:
              isCold = False
              #shutDownTimer = time.time()
           
            try:
              #Is burning?  Check temperature slope to determine:
              slope = slope_intercept(timeElapse[-2],tempOverTime[-2],timeElapse[-1],tempOverTime[-1])
              print(slope)
            except(IndexError):
              slope = 1
            
          # On fire?
            if (slope > 4) and (tempf > highTemp):
                title = "On FIRE!"
                body = "It's {} F.".format(tempf)
                sound = 'chime'
                alert(device_token, body, title, sound)
              
                tempState.heatToBurn() # To 'burning' state (no more alerts til cooled back to cooking)
            
          # Too hot?
            if tempf > highTemp:
                if (isHot == False) or (end - tooHotTimer >= 30):
                  tooHotTimer = time.time()
                  shutDownTimer = time.time()
                  isHot = True
                  title = "Too HOT!"
                  body = "It's {} F.".format(tempf)
                  sound = 'chime'
                  alert(device_token, body, title, sound)

          # Too cold?
          # Will shut down (back to cold state) automatically if too cold for more than 200 seconds
          # Will alert user every 60 seconds on its way to shutting down up til time is reached
            elif tempf < lowTemp:
                if (isCold == False):
                  #Then just dipped down into "too cold" - initialize timers:
                    tooColdTimer = time.time()  # to calculate 60 sec warnings that BBQ too cold from
                    shutDownTimer = time.time() # to calculate 200 sec to shut down from
                    isCold = True

                  #Alert user that BBQ too cold  
                    title = "Turn UP the BBQ!"
                    body = "Cooled down to {} F.".format(tempf)
                    sound = 'chime'
                    alert(device_token, body, title, sound)

                elif (end - shutDownTimer >= 200):
                    title = "Enjoy your food!"
                    body = "Shutting down."
                    sound = 'chime'
                    alert(device_token, body, title, sound)
                    
                    tempState.turnOff() # Back to cold state

                elif (end - tooColdTimer) >= 60:
                    tooColdTimer = time.time()
                    title = "Turn UP the BBQ!"
                    body = "Cooled down to {} F.".format(tempf)
                    sound = 'chime'
                    alert(device_token, body, title, sound)
              
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
  #TODO - change alert sounds
  #TODO - have timer async run on ios and re adjust when checked 
  #TODO - change to proper python form
 
 
  
  
