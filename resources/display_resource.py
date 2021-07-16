from flask_restful import Resource, reqparse
# from flask_jwt import jwt_required
from models.sensor_reading_model import SensorReadingModel, ChartDisplay, DashboardDisplay
import datetime

class DashboardDisplayResource(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('user_id', type=str, required=True, help='This feild cannot be left blank or invalid format') 
  
    def post(self):
        data = DashboardDisplayResource.parser.parse_args()
        dashboard_display = DashboardDisplay(data['user_id'])
    
        try:
            return(dashboard_display.get_guage_display_data())
        except:
            return {"message": "An error occurred retreiving from dashboard_display"}, 400


class ChartDisplayResource(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('user_id', type=str, required=True, help='This feild cannot be left blank or invalid format') 
  
    def post(self):
        data = ChartDisplayResource.parser.parse_args()
        chart_display = ChartDisplay(data['user_id'])
    
        try:
            return (chart_display.formated_chart_data())
        except Exception as e:
            print(e)
            return {"message": "An error occurred retreiving from chart"}, 400