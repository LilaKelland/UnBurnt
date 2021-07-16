# UnBurnt

Still a work in progress. 

After having too many dinners go from "just a couple more minutes" to completely burnt on the BBQ, an ios app that alerts to temperature fluctuations and cooking times when BBQing was born.

See UnBurntApp repository for xcode files.
See UnBurntArduino repository for Arduino set up.

Deployed on a raspberry pi server via Docker.

The python code reads in sensor data (in this case are attached to an ardunio Nano with wifi), and using push notifications:
-  Alerts user when the BBQ has warmed up to a user-defined minimum cooking temerature 
-  Alerts user at user-defined timer intervals to check on food
-  Alerts user when BBQ is too hot or too cold 

## Next Steps:
- add in machine learning with notifications with action from user (once get it to work properly) and the temperature slope data and flame sensor




