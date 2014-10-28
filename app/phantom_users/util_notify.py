# coding=utf8
import models
from notifications import UserNotifier
import request_handler

def welcome(user_data):
    if user_data == None:
        return False
    UserNotifier.push_login_for_user_data(user_data,"ברוכים הבאים לאקדמיית קהאן! לחוויה מלאה ממולץ [login]")
    
def update(user_data, user_exercise, threshold=False, isProf=False, gotBadge=False):
    if user_data == None:
        return False
        
    if not user_data.is_phantom:
        return False

    numquest = None

    if user_exercise != None:
        numquest = user_exercise.total_done
        prof = str(models.Exercise.get_by_name(user_exercise.exercise).display_name)


    numbadge = user_data.badges
    numpoint = user_data.points

    # First question
    if (numquest == 1):
        UserNotifier.push_login_for_user_data(user_data,"פתרתם את התרגיל הראשון שלכם! כדאי לכם [login]")  
    # Every 10 questions, more than 20 every 5  
    if (numquest != None and numquest % 10 == 0) or \
       (numquest != None and numquest > 20 and numquest % 5 == 0):
        UserNotifier.push_login_for_user_data(user_data,"פתרתם "+str(numquest)+" תרגילים! כדאי לכם [login]")
    #Proficiency
    if isProf:
        UserNotifier.push_login_for_user_data(user_data,"אתם מיומנים ב-"+str(prof)+". כדאי לכם [login]")
    #First Badge
    if numbadge != None and len(numbadge) == 1 and gotBadge:
        achievements_url = "%s/achievements" % user_data.profile_root
        UserNotifier.push_login_for_user_data(
                user_data,
                "ברכות על ה<a href='%s'>תג</a> הראשון שלכם! כדאי לכם [login]" %
                        achievements_url)
    #Every badge after
    if numbadge != None and len(numbadge) > 1 and gotBadge:
        UserNotifier.push_login_for_user_data(user_data,"השגתם <a href='/profile'>"+str(len(numbadge))+" תגים</a> עד כה. כדאי לכם [login]")
    #Every 2.5k points
    if numpoint != None and threshold:
        numpoint = 2500*(numpoint/2500)+2500
        UserNotifier.push_login_for_user_data(user_data,"השגתם <a href='/profile'>"+str(numpoint)+ " נקודות</a>! כדאי לכם [login]")


#Toggle Notify allows the user to close the notification bar (by deleting the memcache) until a new notification occurs. 
class ToggleNotify(request_handler.RequestHandler):
    def post(self):
        UserNotifier.clear_login()

