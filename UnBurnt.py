"""UnBurnt.py
reads ardunio data writen to unburnttemp.json - temp and time data for ios app via unBurntAPI.py, 
#   unburntstate.json - cooking state for ios app via unBurntAPI.py
# Reads initial cooking parameters written by ios via unBurntAPI.py - unburntconfig.json
# Sends push notifications for check times and too hot/ too cold/ on fire through apns2 to 
# predetermined (with device tokens specified) phones"""

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
import math

l_device_token = "53363e77461b9c7d01851cb0a7e81676a3f4fb552e5b7e8381cb3ef16a3446b3"
m_device_token = "a8de10202dbe14830fd08af9c8b447c8872fdbe320d03f5cf86c8e9805bf69b5"
device_token = [l_device_token, m_device_token]

def alert(device_token, body, title, sound):
  """send alert to ios UnBurnt app"""
  cli = apns2.APNSClient(mode="prod",client_cert="apns-prod.pem")
  alert = apns2.PayloadAlert(body = body, title = title)
  payload = apns2.Payload(alert = alert, sound = sound)
  n = apns2.Notification(payload = payload, priority = apns2.PRIORITY_LOW)
  for i in range (2):
    response = cli.push(n = n, device_token = device_token[i], topic = 'com.lilakelland.tryAlamoFirePost')
    print("yay ", i, device_token[i]) 
  print(response.status_code)
  assert response.status_code == 200, response.reason
  assert response.apns_id
 
class temp_state_machine(StateMachine):
    """Set up statemachine to handle cooking states"""
    cold = State('Cold', initial=True)
    cooking = State('Cooking')
    burning = State('Burning')

    intial_warm_up = cold.to(cooking) #(when first time temp > low_temp)
    heat_to_burn = cooking.to(burning) #(slope > isBurning and tempf > high temp)
    stop_burning = burning.to(cooking) #when temp < high temp add a too cold warning
    turn_off = cooking.to(cold) #when in cooking and temp too low for 5 min or more 

temp_state = temp_state_machine()

def temp_slope(x1,y1,x2,y2):
    """Determine temperature rate of change - indicative of burning?"""
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

def set_cooking_parameters():
    """Read in and set parameters (unburntconfig.json) set by ios app in  - "tryAlamoFirePost" via UnBurntAPI.py" """
    with open('unburntconfig.json', 'r') as openfile: 
        config_data = json.load(openfile)
    #Initial case data set:     
    low_temp = 70
    high_temp = 100
    check_time = 30000
    
    if (is_float(config_data["lowTemp"])): 
        low_temp = float(config_data["lowTemp"])
    if (is_float(config_data["highTemp"])):  
        high_temp = float(config_data["highTemp"])
    if (is_float(config_data["checkTime"])): 
        check_time = float(config_data["checkTime"])
    return(low_temp, high_temp, check_time)

#Initialize golbal variables
temp_over_time = []
time_elapse = [] 
is_too_hot = False

while True:
  (low_temp, high_temp, check_time) = set_cooking_parameters()
  end = time.time()
  now = datetime.datetime.now()

#Cold to warming up initial state:
  if (temp_state.current_state == temp_state.cold):
      #tooColdCount = 0
      state_status = {
          "state": "cold"
          }
      with open("unburntstate.json", "w") as outfile: 
          json.dump(state_status, outfile)
      
      try: 
          temp = requests.get("http://192.168.7.82/")
          tempf = float(temp.json()["tempf"])
          tempf2 = float(temp.json()["tempf2"])
          print(tempf)
          print(tempf2)
          flame_value = float(temp.json()["flameValue"])
          print(flame_value)

          if math.isnan(tempf) == False:
            ardunio_data = {
              "tempf": tempf,
              "tempf2": tempf2,
              "flameValue": flame_value,
              "timeElapse": "Stopped (will start when over {} F)".format(low_temp),
              "checkTimer": "Stopped (will start when over {} F)".format(low_temp),
              "timeStamp": now.strftime("%A %I:%M %p")
              }
            with open("unburnttemp.json", "w") as outfile: 
                json.dump(ardunio_data, outfile)

            time_elapse = [] # list of time
            temp_over_time = [] # list of temperatures
            temp_count = 0
            
            temp_over_time_data = {
              "lowTempLimit": low_temp,
              "highTempLimit": high_temp,
              "tempCount": temp_count,
              "tempOverTime" : temp_over_time,
              "timeElapse" : time_elapse
            }
            with open("unBurntChart.json", "w") as outfile: 
                    json.dump(temp_over_time_data, outfile)

      except RequestException:
          print("Still cold - something is up with the ardunio connnection")
    
      if tempf > low_temp:
          title = "Now we're cooking - TIMER STARTED!"
          body = "It's {} F.".format(tempf)
          sound = 'chime'
          alert(device_token, body, title, sound)
          
          start = time.time()
          timerstart = start
        
          temp_state.intial_warm_up()

  elif (temp_state.current_state != temp_state.cold):  
    try:
      #Check BBQ Timer to see if entering cool down phase
        if ((end - timerstart) >= check_time):
            time_minute = round(check_time/60,2)
            print("end - timerstart ", end - timerstart)
            print("end - start (total time) ", end-start)
            timerstart = time.time()
            print("end - timerstart ", end - timerstart)
            alert(device_token, body = "How's it looking? Timer resetting.", title = "{} Minute Checkpoint".format(time_minute), sound = 'radar_timer.aif')

        temp = requests.get("http://192.168.7.82/")
        tempf = float(temp.json()["tempf"])

        time_elapse.append(end - start) # list of time
        temp_over_time.append(tempf) # list of temperatures
        temp_count = len(temp_over_time)
        
        temp_over_time_data = {
          "lowTempLimit": low_temp,
          "highTempLimit": high_temp,
          "tempCount": temp_count,
          "tempOverTime" : temp_over_time,
          "timeElapse" : time_elapse
         }
        with open("unBurntChart.json", "w") as outfile: 
                json.dump(temp_over_time_data, outfile)
        
        temptry = {
              "tempf": tempf,
              "timeElapse": strftime("%M:%S", gmtime(time_elapse[-1])),
              "checkTimer": strftime("%M:%S", gmtime(check_time - (end - timerstart))),
              "timeStamp": now.strftime("%A %H:%M:%S")
              }
        with open("unburnttemp.json", "w") as outfile: 
              json.dump(temptry, outfile)
          
      #Cooking State:
        if temp_state.current_state == temp_state.cooking:
            #Update unburntstate.json state to "cooking" 
            state_status = {
                "state": "cooking"
                }
            with open("unburntstate.json", "w") as outfile: 
              json.dump(state_status, outfile)

           #Determine if temperature is in the cooking range is_too_hot 
            if tempf < high_temp:
              is_too_hot = False

            if tempf > low_temp:
              is_too_cold = False
              #shut_down_timer = time.time()
           
            try:
              #Is burning?  Check temperature slope to determine:
              slope = temp_slope(time_elapse[-2],temp_over_time[-2],time_elapse[-1],temp_over_time[-1])
            except(IndexError):
              slope = 1
            
          # On fire?
            if (slope > 4) and (tempf > high_temp):
                alert(device_token, body = "It's {} F.".format(tempf), title = "On FIRE!", sound = 'fire.aiff')
                temp_state.heat_to_burn() # To 'burning' state (no more alerts til cooled back to cooking)
            
          # Too hot?
            if tempf > high_temp:
                if (is_too_hot == False) or (end - too_hot_timer >= 30):
                  too_hot_timer = time.time()
                  shut_down_timer = time.time()
                  is_too_hot = True 
                  alert(device_token, body = "It's {} F.".format(tempf), title = "Too HOT!", sound = 'too_hot.aif')

          # Too cold?
          # Will shut down (back to cold state) automatically if too cold for more than 200 seconds
          # Will alert user every 60 seconds on its way to shutting down up til time is reached
            elif tempf < low_temp:
                if (is_too_cold == False):
                  #Then just dipped down into "too cold" - initialize timers:
                    too_cold_timer = time.time()  # to calculate 60 sec warnings that BBQ too cold from
                    shut_down_timer = time.time() # to calculate 200 sec to shut down from
                    is_too_cold = True
                  #Alert user that BBQ too cold  
                    alert(device_token, body = "Cooled down to {} F.".format(tempf), title = "Turn UP the BBQ!", sound = 'too_cold.aif')

                elif (end - shut_down_timer >= 200):
                    alert(device_token, body = "Shutting down.", title = "Enjoy your food!", sound = 'chime')
                    temp_state.turn_off() # Back to cold state

                elif (end - too_cold_timer) >= 60:
                    too_cold_timer = time.time()
                    alert(device_token, body = "Cooled down to {} F.".format(tempf), title = "Turn UP the BBQ!", sound = 'too_cold.aif')
              
      #Burning State:
        if (temp_state.current_state == temp_state.burning):
            state_status = {
              "state": "burning"
              }
            with open("unburntstate.json", "w") as outfile: 
              json.dump(state_status, outfile)
            if tempf < high_temp:
                temp_state.stop_burning() # Back to 'cooking' state 

    except RequestException:
      print("network error with sensor")
      print(time_elapse) #date time instead

  #TODO - have timer async run on ios and re adjust when checked 
  
 
 
  
  
