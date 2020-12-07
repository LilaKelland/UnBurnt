"""UnBurnt.py
reads sensors - 2 thermocouples: one on left and one on right side of BBQ and a flame sensor from ardunio 
determines cooking state and sends push notifications (alerts) via APNS to ios app 
(currently only with predetermined (with device tokens specified) phones)

writes data:
temp and sensor validity unBurntTemp.json 
cooking state - unBurntState.json
chart data - unBurntChart.json

reads data:
cooking high and low temp limits and time between bbq checks - unburtconfig.json

Always running on server - will start alerting phone once in cooking state, 
and will automaticaly go back to cold (sleep) state once BBQ has cooled down.

Works with unBurntAPI.py """

import time
import requests
from statemachine import StateMachine, State
import json
from time import gmtime
from time import strftime
import datetime
from requests.exceptions import RequestException, Timeout
import numpy
import apns2
import math

#TODO --store this in a DB and associate with user id allow for varying number of device token 
l_device_token = "2a76a367f104574d4f595d240d302a62e069fb144d96b7090392e5606f27da18"
m_device_token = "0b8ac8dccb7297cf2ffd7b38d21da8ab652821f166e3cb8a3f4da760da4c9722"
device_token = [l_device_token, m_device_token]

def alert(device_token, body, title, sound, category):
  """send alert to ios UnBurnt app"""
  cli = apns2.APNSClient(mode = "prod",client_cert = "apns-pro.pem")
  alert = apns2.PayloadAlert(body = body, title = title)
  payload = apns2.Payload(alert = alert, sound = sound, category = category, mutable_content = True)#, "action":action)
  n = apns2.Notification(payload = payload, priority = apns2.PRIORITY_LOW)
  for i in range (2):
    response = cli.push(n = n, device_token = device_token[i], topic = 'com.lilakelland.UnBurnt')
    print("yay ", i, device_token[i]) 
  print("resoponse status code", response.status_code)
  assert response.status_code == 200, response.reason
  assert response.apns_id
 
class TempStateMachine(StateMachine):
    """Set up statemachine to handle cooking states"""
    cold = State('Cold', initial=True)
    cooking = State('Cooking')
    burning = State('Burning')

    intial_warm_up = cold.to(cooking) #(when first time temp > _limit)
    heat_to_burn = cooking.to(burning) #slope > burning_slope and tempf > high temp_limit
    stop_burning = burning.to(cooking) #when temp < high temp add a too cold warning
    turn_off = cooking.to(cold) #when in cooking and temp too low for 200 sec or more or when both temp sensors invalid

temp_state = TempStateMachine()
 
class Arduino:
  """ Gets all sensor data from ardunio and caches it if check_it_now == True. This 
  reduces checking time for each individual sensor by 2 sec each"""

  def __init__(self):
        self.last_checked = 0
        self.json = ""

  def requests_temp(self, check_it_now = False):
        time_since_checked = time.time() - self.last_checked
        if (time_since_checked < 3) and (check_it_now == False):
          #print ("Not calling arduino yet since time_since is {0}".format(time_since_checked))
          return(self.json)
        
        self.last_checked = time.time()
        try:
            self.json = requests.get("http://192.168.0.36", timeout = 6)
            print ("Trying to get from arduino and got {0}".format(self.json))
        except Exception as e:
            print ("Getting from Arduino failed with {0}".format(e))
            self.json = ""
            raise e
        finally:
            return(self.json)

class BBQSensor:  
    """grabs individual sensor values and evaluates if NaN"""
    def __init__(self, value_name, arduino):
        # note: value_name must be string (ie "tempf1")
        self.value_name = value_name
        self.arduino = arduino

    def get_value(self):
        try:
            temp = self.arduino.requests_temp()
            self.value = float(temp.json()[self.value_name])
            count = 0
            while (math.isnan(self.value) == True) and (count < 5):
                temp = self.arduino.requests_temp(True)
                self.value = float(temp.json()[self.value_name])
                count += 1
                print ("Arduino returned value |{0}| which is nan on count {1}".format(self.value, count))
            if math.isnan(self.value) == True:
                self.value = 1 #TODO --decide what to do here with this 
        except Exception as e:#(RequestException, Timeout):
                #print("Got exception {0}".format(e)) 
                self.value = 1 #TODO --decide what to do here with this
    
        return(self.value)

  #TODO in future create BBQSensor subclasses: tempsensor, flamesensor to allow for more sensors and comparing capabilities

arduino = Arduino()
thermocouple_left = BBQSensor("tempf1", arduino)
thermocouple_right = BBQSensor("tempf2", arduino)
flame_sensor = BBQSensor("flameValue", arduino)

class BBQSensorSet():

    def __init__(self, left, right, flame):
        #TODO --use subclass for temp_sensor_set = {}/flame_sensor_set = {} each in future to make more generatic/ flexible have methods validatesensor, addSensor...
        self.left_temp = left
        self.right_temp = right
        self.flame_sensor = flame
        self.tempf1 = 3
        self.is_tempf1_valid = True 
        self.tempf2 = 0
        self.is_tempf2_valid = False 
        self.flame_value = 1023
        self.is_flame_valid = True

    #def getTemps(self):
    def getLeftTemp(self): 
        """Gets tempf1 and validates"""
        self.tempf1 = self.left_temp.get_value()
        if (self.tempf1 == 1 or self.tempf1 == 32):
            self.is_tempf1_valid = False  # to deal with flakiness of sensors
        #TODO --elif (temp1 < (temp2 + 200)) or (temp1 > (temp2 - 200)):
        #TODO --perhaps compare to previous values of itself? 
        else:
            self.is_tempf1_valid = True

    def getRightTemp(self): 
        """Gets tempf2 and validates"""
        self.tempf2 = self.right_temp.get_value()
        if (self.tempf2 == 1 or self.tempf2 == 32):
            self.is_tempf2_valid = False  
        #TODO elif (temp1 < (temp2 + 200)) or (temp1 > (temp2 - 200)):
        #TODO perhaps compare to previous values of itself? 
        else:
            self.is_tempf2_valid = True

    def getFlameValue(self):
        """Gets flame_value and validates"""   
        self.flame_value = flame_sensor.get_value()
        if self.flame_value <  50:
            self.is_flame_valid = False
        else:
            self.is_flame_valid = True

    def refresh(self):
        self.getLeftTemp()
        self.getRightTemp()
        self.getFlameValue()

bbqSensorSet = BBQSensorSet(thermocouple_left, thermocouple_right, flame_sensor)

def temp_slope(x1,y1,x2,y2):
    """Determine temperature rate of change -- helps determine if burning"""
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
    """Read in cooking limits as set by ios app """
    with open('unBurntConfig.json', 'r') as openfile: 
        config_data = json.load(openfile)
    #Initial case data set:     
    low_temp_limit = 70
    high_temp_limit = 100
    check_time_interval = 30000
    
    if (config_data["lowTemp"] is None) == False: 
        if (is_float(config_data["lowTemp"])): 
            low_temp_limit = float(config_data["lowTemp"])
    if (config_data["highTemp"] is None) == False:
        if (is_float(config_data["highTemp"])):  
            high_temp_limit = float(config_data["highTemp"])
    if (config_data["checkTime"] is None) == False:
        if (is_float(config_data["checkTime"])): 
            check_time_interval = float(config_data["checkTime"])
    return(low_temp_limit, high_temp_limit, check_time_interval)

def write_dashboard_display_data_to_file(bbqSensorSet, list_of_time = [0], check_time_interval = 0, timer_start_time = time.time()):
    if list_of_time == [0]:
        end_time = 0
        timer_start_time = 0
    else:
        end_time = time.time()
    now = datetime.datetime.now()
    #TODO handle the empty array case - special character?
    #TODO initialize the check time
    #print("time since started", str(int(list_of_time[-1])))
    #print("timer countdown", str(int(check_time_interval - (end_time - timer_start_time))))
    sensor_data = {
        "tempf1": int(bbqSensorSet.tempf1),
        "is_tempf1_valid" : bbqSensorSet.is_tempf1_valid,
        "tempf2": int(bbqSensorSet.tempf2),
        "is_tempf2_valid" : bbqSensorSet.is_tempf2_valid,
        "flameValue": int(bbqSensorSet.flame_value),
        "is_flame_valid" : bbqSensorSet.is_flame_valid,
        "timeElapsed": str(int(list_of_time[-1])),
        "checkTimer": str(int(check_time_interval - (end_time - timer_start_time))),
        "timeNow": int(time.time()),  
        "timeStamp": now.strftime("%A %I:%M %p")
        }
    with open("unBurntTemp.json", "w") as outfile: 
        json.dump(sensor_data, outfile)

def write_state_to_file(state_status):
    state_status_data = {
        "state": state_status
        }
    with open("unBurntState.json", "w") as outfile: 
        json.dump(state_status_data, outfile)

def write_chart_data_to_file(low_temp_limit, high_temp_limit, list_of_tempf1, list_of_tempf2, list_of_time):
    temp_count = len(list_of_tempf1)
    temp_over_time_data = {
        "lowTempLimit": low_temp_limit,
        "highTempLimit": high_temp_limit,
        "tempCount": temp_count,
        "tempOverTime1" : list_of_tempf1,
        "tempOverTime2" : list_of_tempf2,
        "timeElapse" : list_of_time
        }
    with open("unBurntChart.json", "w") as outfile: 
        json.dump(temp_over_time_data, outfile)

#Initialize variables
list_of_time = [] 
state_change_time = 0
list_of_tempf1 = [] # list of temperatures
list_of_tempf2 = [] # list of temperatures
burning_slope = 4 #TODO - have system learn what indicates burning from user response (Notification Actions) /flame sensors/ temps

while True:
    (low_temp_limit, high_temp_limit, check_time_interval) = set_cooking_parameters()
    check_min, check_sec = divmod(check_time_interval, 60)
    
#for Cold state (during warm up to low_temp_limit, or shutdown)
    if (temp_state.current_state == temp_state.cold): 
        end_time = 0
        write_state_to_file("cold") 
        bbqSensorSet.refresh()
        #print(bbqSensorSet.tempf1, bbqSensorSet.is_tempf1_valid, bbqSensorSet.tempf2, bbqSensorSet.is_tempf2_valid, bbqSensorSet.flame_value, bbqSensorSet.is_flame_valid)
        write_dashboard_display_data_to_file(bbqSensorSet) #removed last 3 optionals

        #reset/ initialize chart data
        list_of_time = [] 
        list_of_tempf1 = [] 
        list_of_tempf2 = [] 
        write_chart_data_to_file(low_temp_limit, high_temp_limit, list_of_tempf1, list_of_tempf2, list_of_time)
        #TODO -- change swift code to read in state in 3rd view controller so this will not needed until cooking state
        
        if (bbqSensorSet.tempf1 or bbqSensorSet.tempf2) > low_temp_limit: 
            alert(device_token, body = "Up to {}°F.".format(int(bbqSensorSet.tempf1)), title = "Now we're cooking - TIMER STARTED!", sound = "chime", category = "WAS_THERE_FIRE")
          
          # initialize timers and move to cooking state
            total_start_time = time.time()
            timer_start_time = total_start_time
            write_state_to_file("cooking")
            state_change_time = time.time()
            temp_state.intial_warm_up()
          
#for all states other than cold
    else:
        try:
            #check the timer, and reset if interval reached
            if ((end_time - timer_start_time) >= check_time_interval):
                timer_start_time = time.time()
                alert(device_token, body = "How's it looking? Timer resetting.", title = f"{int(check_min)}:{int(check_sec)} Checkpoint", sound = 'radar_timer.aiff', category = "WAS_THERE_FIRE")

            #update temp/time lists
            end_time = time.time()
            list_of_time.append(end_time - total_start_time)  
            list_of_tempf1.append(bbqSensorSet.tempf1) 
            list_of_tempf2.append(bbqSensorSet.tempf2) 

            #read sensors & update ios dashboard display data
            bbqSensorSet.refresh()
            print (bbqSensorSet.tempf1, bbqSensorSet.tempf2)
            if (bbqSensorSet.is_tempf2_valid == False) and (bbqSensorSet.is_tempf1_valid == False):
                print("temperature sensors offline, shutting down.")
                # wait 10 seconds 
                #then turn off
                temp_state.turn_off() 
                continue 
            write_dashboard_display_data_to_file(bbqSensorSet, list_of_time, check_time_interval, timer_start_time)
            write_chart_data_to_file(low_temp_limit, high_temp_limit, list_of_tempf1, list_of_tempf2, list_of_time)
            

    #when in Cooking State:
            if temp_state.current_state == temp_state.cooking:

                if (bbqSensorSet.tempf1 < high_temp_limit) and (bbqSensorSet.tempf1 > low_temp_limit):
                    #Temp is within range
                    is_too_hot = False
                    is_too_cold = False
                    continue
      
                elif bbqSensorSet.tempf1 < low_temp_limit:
                    # Too cold  
                    if (is_too_cold == False):
                        #Then temp just dipped down into "too cold" - initialize timers and send alert:
                        too_cold_alert_timer = time.time()  
                        shut_down_timer = time.time() 
                        is_too_cold = True  
                        alert(device_token, body = "Cooled down to {}°F.".format(int(bbqSensorSet.tempf1)), title = "Turn UP the BBQ!", sound = 'too_cold.aiff', category = "WAS_THERE_FIRE")

                    elif (end_time - too_cold_alert_timer) >= 60: 
                        #reset timer and send alert 
                        too_cold_alert_timer = time.time() 
                        alert(device_token, body = "Cooled down to {}°F.".format(int(bbqSensorSet.tempf1)), title = "Turn UP the BBQ!", sound = 'too_cold.aiff', category = "WAS_THERE_FIRE")

                    elif (end_time - shut_down_timer >= 200):
                        #too long in cold state - shutting down
                        alert(device_token, body = "Shutting down.", title = "Enjoy your food!", sound = 'chime', category = "WAS_THERE_FIRE")
                        temp_state.turn_off() # (Back to cold state)  
                                        
                elif bbqSensorSet.tempf1 > high_temp_limit: 
                    # it's too hot
                    if is_too_hot == False:
                        #Then temp just raised above "too hot" - initialize timers and send alert:
                        is_too_hot = True 
                        too_hot_timer = time.time()
                        alert(device_token, body = "It's {}°F.".format(int(bbqSensorSet.tempf1)), title = "Too HOT!", sound = 'too_hot.aiff', category = "WAS_THERE_FIRE")
                    
                    elif end_time - too_hot_timer >= 30: 
                        #reset timer and send alert 
                        too_hot_timer = time.time()
                        alert(device_token, body = "It's {}°F.".format(int(bbqSensorSet.tempf1)), title = "Too HOT!", sound = 'too_hot.aiff', category = "WAS_THERE_FIRE")
                 
                  # Check temperature slope to determine burning:
                    try:
                        slopeL = temp_slope(list_of_time[-2], list_of_tempf1[-2], list_of_time[-1], list_of_tempf1[-1])
                    except(IndexError):
                        slopeL = 1

                    try:
                        slopeR = temp_slope(list_of_time[-2], list_of_tempf2[-2], list_of_time[-1], list_of_tempf2[-1])
                    except(IndexError):
                        slopeR = 1

                    if ((slopeL > burning_slope) or (slopeR > burning_slope) or (bbqSensorSet.flame_value < 1023 and bbqSensorSet.is_flame_valid == True)):
                        alert(device_token, body = "It's {}°F.".format(int(bbqSensorSet.tempf1)), title = "On FIRE!", sound = 'fire.aiff', category = "WAS_THERE_FIRE")
                        write_state_to_file("burning")
                        temp_state.heat_to_burn() 


    #when in Burning State
            if (temp_state.current_state == temp_state.burning):
                if bbqSensorSet.tempf1 < high_temp_limit:
                    write_state_to_file("cooking")
                    temp_state.stop_burning() # Back to 'cooking' state 

        except RequestException:
          print("network error with sensor")
          print("list of times ", list_of_time) #date time instead

      
    
 
  
  
