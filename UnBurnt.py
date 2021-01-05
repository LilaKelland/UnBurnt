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
from scipy import stats
import apns2
import math
import pymongo
from pymongo import MongoClient
from mongoengine import *
connect('mongoengine_test')

#Initialize variables
list_of_time = [] 
state_change_time = 0
list_of_tempf1 = [] # list of temperatures
list_of_tempf2 = [] # list of temperatures
BURNING_SLOPE = 4 #TODO - have system learn what indicates burning from user response (Notification Actions) /flame sensors/ temps
too_cold_alert_timer = 0
TOO_COLD_ALERT_INTERVAL = 60
TOO_COLD_SHUT_DOWN_TIME = 200
too_hot_alert_timer = 0
TOO_HOT_ALERT_INTERVAL = 30
client = MongoClient()
db = client.pymongo_test

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
    cold_off = State('Cold', initial=True)
    cooking = State('Cooking')
    cooking_too_hot = State("Cooking_too_hot")
    cooking_too_cold = State("Cooking_too_cold")
    burning = State('Burning')

#TODO - add in substates for cooking too hot and cooking too cold to make less confusing
    start_cooking = cold_off.to(cooking) #(when first time temp > _limit)
    temp_dropped_too_cold = cooking.to(cooking_too_cold)
    warmed_back_up = cooking_too_cold.to(cooking)
    temp_too_hot = cooking.to(cooking_too_hot)
    too_hot_to_burn = cooking_too_hot.to(burning)
    cooled_back_down_to_cooking = cooking_too_hot.to(cooking) #*** not used 
    heat_to_burn = cooking.to(burning) #slope > burning_slope and tempf > high temp_limit
    stop_burning = burning.to(cooking) #when temp < high temp add a too cold warning
    cooled_down_to_turn_off = cooking_too_cold.to(cold_off)
    turn_off = cooking.to(cold_off) #when in cooking and temp too low for 200 sec or more or when both temp sensors invalid
    turn_off_from_too_hot = cooking_too_hot.to(cold_off)

#TODO add in state change time  to compare if just changed, leave, 
    def on_start_cooking(self):
        print("warming up from cold to cooking")
        alert(device_token, body = "Up to {}°F.".format(int(bbqSensorSet.tempf1)), title = "Now we're cooking - TIMER STARTED!", sound = "chime", category = "WAS_THERE_FIRE")
        """total_start_time = time.time()
        timer_start_time = total_start_time"""
        write_state_to_file("cooking")
        state_change_time = time.time()
       
    def on_temp_dropped_too_cold(self):
        print("cooking to too cold")
        too_cold_alert_timer = time.time()  
        too_cold_shutdown_timer = time.time() 
        alert(device_token, body = "Cooled down to {}°F.".format(int(bbqSensorSet.tempf1)), title = "Turn UP the BBQ!", sound = 'too_cold.aiff', category = "WAS_THERE_FIRE")
        write_state_to_file("cooking_too_cold")
        state_change_time = time.time()

    def on_warmed_back_up(self):
        print("cooking_too_cold.to(cooking)")
        write_state_to_file("cooking")
        state_change_time = time.time()

    def on_temp_too_hot(self):
        print("cooking.to(cooking_too_hot)")
        too_hot_alert_timer = time.time()
        alert(device_token, body = "It's {}°F.".format(int(bbqSensorSet.tempf1)), title = "Too HOT!", sound = 'too_hot.aiff', category = "WAS_THERE_FIRE")
        write_state_to_file("cooking_too_hot")
        state_change_time = time.time()

    def on_too_hot_to_burn(self):
        print("too hot to burning")
        alert(device_token, body = "It's {}°F.".format(int(bbqSensorSet.tempf1)), title = "On FIRE!", sound = 'fire.aiff', category = "WAS_THERE_FIRE")
        write_state_to_file("burning")
        state_change_time = time.time()

    def on_cooled_back_down_to_cooking(self):
        print("cooking_too_hot.to(cooking)")
        write_state_to_file("cooking")
        state_change_time = time.time()

    def on_heat_to_burn(self):
        print("cooking.to(burning)")
        # check slope?
        alert(device_token, body = "It's {}°F.".format(int(bbqSensorSet.tempf1)), title = "On FIRE!", sound = 'fire.aiff', category = "WAS_THERE_FIRE")
        write_state_to_file("burning")
        state_change_time = time.time()

    def on_stop_burning(self):
        print("burning.to(cooking)")
        write_state_to_file("cooking")
        state_change_time = time.time()
   
    def on_cooled_down_to_turn_off(self):
        print("cooking_too_cold.to(cold_off)")
        alert(device_token, body = "Shutting down.", title = "Enjoy your food!", sound = 'chime', category = "WAS_THERE_FIRE")
        write_state_to_file("cold_off")
        state_change_time = time.time()

    def on_turn_off_from_too_hot(self): 
        print("cooking.to(cold_off)")
        alert(device_token, body = "Shutting down.", title = "Lost connection with sensors.", sound = 'chime', category = "WAS_THERE_FIRE")
        write_state_to_file("cold_off")
        state_change_time = time.time()

    def on_turn_off(self):
        print("cooking.to(cold_off)")
        alert(device_token, body = "Shutting down.", title = "Lost connection with sensors.", sound = 'chime', category = "WAS_THERE_FIRE")
        write_state_to_file("cold_off")
        state_change_time = time.time()

temp_state = TempStateMachine()
 
class Arduino:
  """ Gets sensor data from ardunio and caches it if check_it_now == True. This 
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
            self.json = requests.get("http://192.168.0.37", timeout = 6)
            print ("Trying to get from arduino and got {0}".format(self.json.json()))

        except Exception as e:
            print ("Getting from Arduino failed with {0}".format(e))
            self.json = ""
            raise e
            if KeyboardInterrupt:
                exit()
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

        except Exception as e:  #(RequestException, Timeout):
                #print("Got exception {0}".format(e)) 
                self.value = 1 #TODO --decide what to do here with this
    
        return(self.value)

    def is_burning(self):
        pass

class Thermocouple(BBQSensor):
    def __init__(self, value_name, arduino):
    # note: value_name must be string (ie "tempf1")
        self.value_name = value_name
        self.arduino = arduino
        self.slope = 1

    # Compare values?

    def get_time_x(self, list_of_time):
        try:
            x1 = list_of_time[-3]
            x2 = list_of_time[-2]
            x3 = list_of_time[-1]
            
        except(IndexError):
            #TODO raise exception
            x1 = 1
            x2 = 1
            x3 = 1
        return(x1, x2, x3)

    def get_temp_y(self, list_of_temp):
        try:
            y1 = list_of_temp[-3]
            y2 = list_of_temp[-2]
            y3 = list_of_temp[-1]
        except(IndexError):
            #TODO raise exception
            y1 = 1
            y2 = 1
            y3 = 1
        return(y1, y2, y3)

    def temp_slope(self, list_of_temp, list_of_time):
        try:
            (x1, x2, x3) = self.get_time_x(list_of_time) 
            (y1, y2, y3) = self.get_temp_y(list_of_temp) 
            if (x1, x2, x3 == 1): #TODO if exception raised:
                self.slope = 1
                return(self.slope)
            else:
                self.slope = stats.theilslopes([y1,y2,y3],[x1,x2,x3],0.9) # (ydata,xdata,confidence)  
            
            if self.slope > 1 :
                print('x1:', x1, 'x2:', x2)
                print('y1:', y1, 'y2:', y2)
                print("slope:", self.slope)

        except: 
            self.slope = 1
        return(self.slope)

    def is_burning(self, list_of_temp, list_of_time):
        if (self.temp_slope(list_of_temp, list_of_time) > BURNING_SLOPE):
            print(f'burning slope: {self.slope}')
            return(True)
        else:
            return(False)


class FlameSensor(BBQSensor):
    def __init__(self, value_name, arduino):
    # note: value_name must be string (ie "tempf1")
        self.value_name = value_name
        self.arduino = arduino

    def is_burning(self, flame_value):
        if flame_value < 1023:
            return(True)
        else:
            return(False)
 

arduino = Arduino()
thermocouple_left = Thermocouple("tempf1", arduino)
thermocouple_right = Thermocouple("tempf2", arduino)
flame_sensor = FlameSensor("flameValue", arduino)

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
        self.combinedTemp = self.tempf1

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
    
    def compareTemps(self):
        if self.is_tempf1_valid and self.is_tempf2_valid:
            if abs(self.tempf1 - self.tempf2) > 200:
                self.is_tempf1_valid = False
                self.is_tempf2_valid = False
            else:
                self.combinedTemp = (self.tempf1 + self.tempf2)/2

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
   
    sensor_data = {
        "tempf1": int(bbqSensorSet.tempf1),
        "is_tempf1_valid" : bbqSensorSet.is_tempf1_valid,
        "tempf2": int(bbqSensorSet.tempf2),
        "is_tempf2_valid" : bbqSensorSet.is_tempf2_valid,
        "flameValue": int(bbqSensorSet.flame_value),
        "is_flame_valid" : bbqSensorSet.is_flame_valid,
        "combined_temp": int(bbqSensorSet.combinedTemp),
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


while True:
    (low_temp_limit, high_temp_limit, check_time_interval) = set_cooking_parameters()
    check_min, check_sec = divmod(check_time_interval, 60)
    
    if temp_state.is_cold_off:  #(temp_state.current_state == temp_state.cold_off): # can I just uses if temp_state.cold_off
        end_time = 0
        write_state_to_file("cold_off") 
        print(temp_state.current_state)
        bbqSensorSet.refresh()
        bbqSensorSet.compareTemps()
        print("combined temps", bbqSensorSet.combinedTemp)
        print(bbqSensorSet.tempf1, bbqSensorSet.is_tempf1_valid, bbqSensorSet.tempf2, bbqSensorSet.is_tempf2_valid, bbqSensorSet.flame_value, bbqSensorSet.is_flame_valid)
        write_dashboard_display_data_to_file(bbqSensorSet) #removed last 3 optionals

        #reset/ initialize chart data
        list_of_time = [] 
        list_of_tempf1 = [] 
        list_of_tempf2 = [] 
        write_chart_data_to_file(low_temp_limit, high_temp_limit, list_of_tempf1, list_of_tempf2, list_of_time)
        #TODO -- change swift code to read in state in 3rd view controller so this will not needed until cooking state
        
        if bbqSensorSet.combinedTemp > low_temp_limit: 
            #TODO also check for state_change_time >10 sec?
            total_start_time = time.time()
            timer_start_time = total_start_time
            temp_state.start_cooking()
            continue
          
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
           # print("combined temps", bbqSensorSet.combinedTemp)

            #read sensors & update ios dashboard display data
            bbqSensorSet.refresh()
            if (bbqSensorSet.is_tempf2_valid == False) and (bbqSensorSet.is_tempf1_valid == False):
                print("temperature sensors offline, shutting down.")
                temp_state.turn_off() 
                continue 

            write_dashboard_display_data_to_file(bbqSensorSet, list_of_time, check_time_interval, timer_start_time)
            write_chart_data_to_file(low_temp_limit, high_temp_limit, list_of_tempf1, list_of_tempf2, list_of_time)
            

    #when in Cooking State: - make state objects to hold behaviour! 
            if temp_state.is_cooking:  #(temp_state.current_state == temp_state.cooking): 
                if bbqSensorSet.combinedTemp < low_temp_limit:
                    temp_state.temp_dropped_too_cold()
               
                elif bbqSensorSet.combinedTemp > high_temp_limit:
                    temp_state.temp_too_hot()

                if ((flame_sensor.is_burning(bbqSensorSet.flame_value) and bbqSensorSet.is_flame_valid == True) or thermocouple_left.is_burning(list_of_tempf1, list_of_time) or thermocouple_right.is_burning(list_of_tempf2, list_of_time)) :               
                    print(f'flame value: {bbqSensorSet.flame_value}, is_flame_valid: { bbqSensorSet.is_flame_valid}, thermocouple_left_is_burning: {thermocouple_left.is_burning(list_of_tempf1, list_of_time)}, right_is_burning: {thermocouple_right.is_burning(list_of_tempf2, list_of_time)} ')
                    temp_state.heat_to_burn() 


            if temp_state.is_cooking_too_cold: #(temp_state.current_state == temp_state.cooking_too_cold):  
                if (end_time - too_cold_alert_timer) >= TOO_COLD_ALERT_INTERVAL:  
                    too_cold_alert_timer = time.time() 
                    alert(device_token, body = "Cooled down to {}°F.".format(int(bbqSensorSet.tempf1)), title = "Turn UP the BBQ!", sound = 'too_cold.aiff', category = "WAS_THERE_FIRE")

                elif ((end_time - too_cold_shutdown_timer) >= TOO_COLD_SHUT_DOWN_TIME):  
                   # alert(device_token, body = "Shutting down.", title = "Enjoy your food!", sound = 'chime', category = "WAS_THERE_FIRE")
                    temp_state.cooled_down_to_turn_off() # (Back to cold_off state)  

                if bbqSensorSet.combinedTemp > low_temp_limit:
                    temp_state.warmed_back_up()

                
            if temp_state.is_cooking_too_hot: #(temp_state.current_state == temp_state.cooking_too_hot):              
                if (end_time - too_hot_alert_timer) >= TOO_HOT_ALERT_INTERVAL: 
                    too_hot_alert_timer = time.time()
                    alert(device_token, body = "It's {}°F.".format(int(bbqSensorSet.tempf1)), title = "Too HOT!", sound = 'too_hot.aiff', category = "WAS_THERE_FIRE")
                 
                  # Check temperature slope to determine burning:
                  #TODO replace with check slope function or method 

                    if ((flame_sensor.is_burning(bbqSensorSet.flame_value) and bbqSensorSet.is_flame_valid == True) or thermocouple_left.is_burning(list_of_tempf1, list_of_time) or thermocouple_left.is_burning(list_of_tempf2,list_of_time)) :                
                        temp_state.too_hot_to_burn() 
                
                elif bbqSensorSet.combinedTemp < high_temp_limit:
                    temp_state.cooled_back_down_to_cooking()

            if temp_state.is_burning: #current_state == temp_state.burning):  
                if (bbqSensorSet.combinedTemp < high_temp_limit) and (not flame_sensor.is_burning(bbqSensorSet.flame_value)):
                    temp_state.stop_burning() 

        except RequestException:
          print("network error with sensor")
          print("list of times ", list_of_time) #date time instead

      
    
 
  
  
