"""UnBurntMongoSchemaSetup.py
run this before running UnBurnt/ UnBurntAPI"""

import pymongo
from pymongo import MongoClient

client = MongoClient("mongodb://127.0.0.1:27017/pymongo_test")
db = client.pymongo_test

# set up collections and model
unBurntConfig = db.unBurntConfig
unBurntTemp = db.unBurntTemp
unBurntState = db.unBurntState
unBurntChart = db.unBurntChart
unBurntFire = db.unBurntFire

unBurntConfigSetup = {
    "_id": "unBurntConfig_id",
    "lowTemp": "20", 
    "highTemp": "71", 
    "checkTime": "3000"
}
unBurntConfig.insert_one(unBurntConfigSetup)

unBurntTempSetup = {
    "_id": "unBurntTemp_id",
    "tempf1": 1, 
    "is_tempf1_valid": False, 
    "tempf2": 1, 
    "is_tempf2_valid": False, 
    "flameValue": 1, 
    "is_flame_valid": False, 
    "combined_temp": 3, 
    "timeElapsed": "0", 
    "checkTimer": "0", 
    "timeNow": 1609954185, 
    "timeStamp": "Wednesday 12:29 PM"
    }
unBurntTemp.insert_one(unBurntTempSetup)

unBurntStateSetup = {
    "_id": "unBurntState_id",
    "state": "cold_off"
    }
unBurntState.insert_one(unBurntStateSetup)

unBurntChartSetup = {    
        "_id": "unBurntChart_id",
        "lowTempLimit": 70,
        "highTempLimit": 100,
        "tempCount": 0,
        "tempOverTime1" : list_of_tempf1,
        "tempOverTime2" : list_of_tempf2,
        "timeElapse" : list_of_time
        }
unBurntChart.insert_one(unBurntChartSetup)