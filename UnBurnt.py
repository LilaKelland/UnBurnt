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

###----------------------------store this in a DB and associate with user id allow for varying number of device token 
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
 
class TempStateMachine(StateMachine):
    """Set up statemachine to handle cooking states"""
    cold = State('Cold', initial=True)
    cooking = State('Cooking')
    burning = State('Burning')

    intial_warm_up = cold.to(cooking) #(when first time temp > low_temp)
    heat_to_burn = cooking.to(burning) #slope > burning_slope and tempf > high temp
    stop_burning = burning.to(cooking) #when temp < high temp add a too cold warning
    turn_off = cooking.to(cold) #when in cooking and temp too low for 200 sec or more 

temp_state = TempStateMachine()
 
class Arduino:
  """Used to reduce checking time from eachsensors (2 seconds each) - by caching arduino data from requests"""
  def __init__(self):
        self.last_checked = 0
        self.json = ""
  def requests_temp(self, check_it_now = False):
        if ((time.time() - self.last_checked) < 3) and (check_it_now == False):
          return(self.json)
        
        self.last_checked = time.time()
        self.json = requests.get("http://192.168.7.82/")
        return(self.json)


class BBQSensor:  
    def __init__(self, value_name, arduino):
        # value_name must be string
        self.value_name = value_name
        self.arduino = arduino

    def get_value(self):
        try:
            temp = arduino.requests_temp()
            self.value = float(temp.json()[self.value_name])
            count = 0
            while (math.isnan(self.value) == True) and (count < 5):
                temp = arduino.requests_temp(True)
                self.value = float(temp.json()[self.value_name])
                count += 1
            if math.isnan(self.value) == True:
                self.value = 1 #----------- decide what to do here with this 
        except(RequestException):
                self.value = 1 #----------- decide what to do here with this
    
        return(self.value)
        # ----- figure out what ._ is in @ and inits 

  # subclass tempsensor, flamesensor

arduino = Arduino()
thermocouple_left = BBQSensor("tempf1", arduino)
thermocouple_right = BBQSensor("tempf2", arduino)
flame_sensor = BBQSensor("flameValue", arduino)


#tempf1 = thermocouple_left.get_value

#tempf2 = thermocouple_right.get_value
#flame_value = flame_sensor.get_value

class BBQSensorSet():
    def __init__(self, left, right, flame):
        #self.temp_sensors_set = {}
        #self.flame_sensor_set = {} = use  subclass for temp/flame each in future - to make more generatic and flexable have def validatesensor def addSensor...
        self.left_temp = left
        self.right_temp = right
        self.flame_sensor = flame

    def getLeftTemp(self): 
        temp1 = self.left_temp.get_value()
        temp2 = self.right_temp.get_value()
        if (temp1 == 1 and temp2 != 1) or temp1 == 32:
            is_tempf1_valid = False  # to deal with flakiness of sensors
            temp1 = temp2
        #elif (temp1 < (temp2 + 200)) or (temp1 > (temp2 - 200)):
        else:
            is_tempf1_valid = True
        return(temp1, is_tempf1_valid)
      
      # check the left sensor for validity, and return if within some range of the right sensor, otherwise throw an error 

    def getRightTemp(self): 
        temp1 = self.left_temp.get_value()
        temp2 = self.right_temp.get_value()
        if (temp2 == 1 and temp1 != 1) or temp2 == 32:
            is_tempf2_valid = False  # to deal with flakiness of sensors
            temp2 = temp1
        
        #elif (temp1 < (temp2 + 200)) or (temp1 > (temp2 - 200)):
        #compare to previous values?  how do we want to deal with this?

        else:
            is_tempf2_valid = True
        return(temp2, is_tempf2_valid)

    def getFlameValue(self):
        flame = flame_sensor.get_value()
        if flame == 1:
            is_flame_valid = False
        else:
            is_flame_valid = True
        return(flame, is_flame_valid)

bbqSensorSet = BBQSensorSet(thermocouple_left, thermocouple_right, flame_sensor)
(tempf1, is_tempf1_valid) = bbqSensorSet.getLeftTemp()
(tempf2, is_tempf2_valid) = bbqSensorSet.getRightTemp()
(flame_value, is_flame_valid) = bbqSensorSet.getFlameValue()

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
    """Read in cooking limits as set by ios app in  - "tryAlamoFirePost" """
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
time_elapse = [] 
#is_too_hot = False # is this needed?
time_elapse = [] # list of time
temp_over_time = [] # list of temperatures
temp_over_time2 = [] # list of temperatures
temp_count = 0
burning_slope = 4

while True:
    (low_temp, high_temp, check_time) = set_cooking_parameters()
    end = time.time()

  #for Cold to warming up (initial) state:
    if (temp_state.current_state == temp_state.cold):
        state_status = {
            "state": "cold"
            }
        with open("unburntstate.json", "w") as outfile: 
            json.dump(state_status, outfile)
        
        try: 
            (tempf1, is_tempf1_valid) = bbqSensorSet.getLeftTemp()
            (tempf2, is_tempf2_valid) = bbqSensorSet.getRightTemp()
            (flame_value, is_flame_valid) = bbqSensorSet.getFlameValue()
            now = datetime.datetime.now()
            sensor_data = {
                "tempf1": int(tempf1),
                "is_tempf1_valid" : is_tempf1_valid,
                "tempf2": int(tempf2),
                "is_tempf2_valid" : is_tempf2_valid,
                "flameValue": flame_value,
                "is_flame_valid" : is_flame_valid,
                "timeElapse": "Stopped (will start when over {} F)".format(low_temp),
                "checkTimer": "Stopped (will start when over {} F)".format(low_temp),
                "timeStamp": now.strftime("%A %I:%M %p")
                }
            with open("unburnttemp.json", "w") as outfile: 
                json.dump(sensor_data, outfile)

            #reset/ initialize chart data
            time_elapse = [] # list of time
            temp_over_time = [] # list of temperatures for Left (tempf1)
            temp_over_time2 = [] # list of temperatures for Right (tempf2)
            temp_count = 0

            #--------------------perhaps change swift not to read/ display until cooking - then remove
            temp_over_time_data = {
                "lowTempLimit": low_temp,
                "highTempLimit": high_temp,
                "tempCount": temp_count,
                "tempOverTime" : temp_over_time,
                "tempOverTime2" : temp_over_time2,
                "timeElapse" : time_elapse
                }
            with open("unBurntChart.json", "w") as outfile: 
                json.dump(temp_over_time_data, outfile)
            #------------------------

        except RequestException:
            print("Still cold - something is up with the ardunio connnection")
      
        if tempf1 > low_temp or tempf2 > low_temp: 
            alert(device_token, body = "It's {} F.".format(tempf1), title = "Now we're cooking - TIMER STARTED!", sound = 'chime')
          # initialize timers 
            total_start = time.time()
            timer_start = total_start
          #change states to "cooking
            state_status = {
                "state": "cooking"
                }
            with open("unburntstate.json", "w") as outfile: 
                json.dump(state_status, outfile)
            temp_state.intial_warm_up()
          
  #for all states other than cold state
    elif (temp_state.current_state != temp_state.cold):  
        try:
        #read and update data (excpet state)
          #Check/ reset BBQ Timer  
          # func - input timer_start, return timer_start
            if ((end - timer_start) >= check_time):
                #reset timer
                timer_start = time.time()
                alert(device_token, body = "How's it looking? Timer resetting.", title = "{} Minute Checkpoint".format(round(check_time/60,2)), sound = 'radar_timer.aif')
          
          #update temp/time arrays
            time_elapse.append(end - total_start) # list of time
            temp_over_time.append(tempf1) # list of temperatures for left sensor
            temp_over_time2.append(tempf2) # list of temperatures for right sensor
            temp_count = len(temp_over_time)

          #read sensors & update ios dashboard display data
            (tempf1, is_tempf1_valid) = bbqSensorSet.getLeftTemp()
            (tempf2, is_tempf2_valid) = bbqSensorSet.getRightTemp()
            (flame_value, is_flame_valid) = bbqSensorSet.getFlameValue()
            now = datetime.datetime.now()
            dashboard_display_data = {
                "tempf1": tempf1,
                "is_tempf1_valid" : is_tempf1_valid,
                "tempf2": tempf2,
                "is_tempf2_valid" : is_tempf2_valid,
                "flameValue": flame_value,
                "is_flame_valid" : is_flame_valid,
                "timeElapse": strftime("%M:%S", gmtime(time_elapse[-1])),  #out of range if alreay in cooking#------------------------------------
                "checkTimer": strftime("%M:%S", gmtime(check_time - (end - timer_start))),
                "timeStamp": now.strftime("%A %I:%M %p") #now.strftime("%A %H:%M:%S")
                }
            with open("unburnttemp.json", "w") as outfile: 
                json.dump(dashboard_display_data, outfile)

          #add to ios chart data
            temp_over_time_data = {
              "lowTempLimit": low_temp,
              "highTempLimit": high_temp,
              "tempCount": temp_count,
              "tempOverTime" : temp_over_time,
              "tempOverTime2" : temp_over_time2,
              "timeElapse" : time_elapse
            }
            with open("unBurntChart.json", "w") as outfile: 
                    json.dump(temp_over_time_data, outfile)
            
          #when in Cooking State:
            if temp_state.current_state == temp_state.cooking:
              #Determine if temperature in the cooking range (is_too_hot / is_too_cold)
                if tempf1 < high_temp:
                    is_too_hot = False
                    
                    if tempf1 < low_temp:  # Too cold
                    # Will shut down (back to cold state) automatically if too cold for more than 200 seconds
                    # Will alert user every 60 seconds on its way to shutting down up til time is reached
                      if (is_too_cold == False):
                        #Then just dipped down into "too cold" - initialize timers:
                          too_cold_timer = time.time()  # to calculate 60 sec warnings that BBQ too cold from
                          shut_down_timer = time.time() # to calculate 200 sec to shut down from
                          is_too_cold = True
                        #Alert user that BBQ too cold  
                          alert(device_token, body = "Cooled down to {} F.".format(tempf1), title = "Turn UP the BBQ!", sound = 'too_cold.aif')

                      elif (end - too_cold_timer) >= 60: 
                          too_cold_timer = time.time() #reset timer
                          alert(device_token, body = "Cooled down to {} F.".format(tempf1), title = "Turn UP the BBQ!", sound = 'too_cold.aif')

                      elif (end - shut_down_timer >= 200):
                          alert(device_token, body = "Shutting down.", title = "Enjoy your food!", sound = 'chime')
                          temp_state.turn_off() # Back to cold state  
                                        
                    else:  # right temp range
                        is_too_cold = False

                else: # it's too hot
                    if is_too_hot == False:
                      #Then it just got too hot - ititialize timers - and sound alert:
                        is_too_hot = True 
                        too_hot_timer = time.time()
                        alert(device_token, body = "It's {} F.".format(tempf1), title = "Too HOT!", sound = 'too_hot.aif')
                    
                    elif end - too_hot_timer >= 30:  #alerts every 30 sec and resets timer
                      too_hot_timer = time.time()
                      alert(device_token, body = "It's {} F.".format(tempf1), title = "Too HOT!", sound = 'too_hot.aif')
                 
                  # Check temperature slope to determine burning:
                    try:
                        slopeL = temp_slope(time_elapse[-2],temp_over_time[-2],time_elapse[-1],temp_over_time[-1])
                    except(IndexError):
                        slopeL = 1

                    try:
                        slopeR = temp_slope(time_elapse[-2],temp_over_time2[-2],time_elapse[-1],temp_over_time2[-1])
                    except(IndexError):
                        slopeR = 1

                    if (slopeL > burning_slope or slopeR > burning_slope or flame_value < 1023):
                        alert(device_token, body = "It's {} F.".format(tempf1), title = "On FIRE!", sound = 'fire.aiff')
                        state_status = {
                            "state": "burning"
                            }
                        with open("unburntstate.json", "w") as outfile: 
                            json.dump(state_status, outfile)
                        temp_state.heat_to_burn() # To 'burning' state (no more alerts til cooled back to cooking)
   
          #when in Burning State:
            if (temp_state.current_state == temp_state.burning):
                if tempf1 < high_temp:
                    #change states to "cooking
                    state_status = {
                        "state": "cooking"
                        }
                    with open("unburntstate.json", "w") as outfile: 
                        json.dump(state_status, outfile)
                    temp_state.stop_burning() # Back to 'cooking' state 

        except RequestException:
          print("network error with sensor")
          print(time_elapse) #date time instead

      #TODO - have timer async run on ios and re adjust when checked 
      
    
 
  
  
