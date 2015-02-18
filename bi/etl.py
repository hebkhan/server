# -*- coding: utf-8 -*-
import os
import sys
import time
import logging
import datetime
    
logger = logging.getLogger(__name__)

gae_path = "/usr/local/google_appengine/"

extra_paths = [
    '.',
    gae_path,
    os.path.join("..", "offline"),
    os.path.join("..", "app"),
    os.path.join("..", "utils"),
    os.path.join(gae_path, 'lib', 'webapp2-2.5.2'),
    os.path.join(gae_path, 'lib', 'jinja2-2.6'),
    os.path.join(gae_path, 'lib', 'antlr3'),
    os.path.join(gae_path, 'lib', 'ipaddr'),
    os.path.join(gae_path, 'lib', 'webob-1.2.3'),
    os.path.join(gae_path, 'lib', 'json'),
    os.path.join(gae_path, 'lib', 'yaml', 'lib'),
]
sys.path[:1] = extra_paths
os.environ["SERVER_SOFTWARE"] = "Miner"

from itertools import chain
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from mining import init_remote_api
import model

conn = None
def init_db():
    global conn
    engine = create_engine("postgresql+psycopg2://bi:khanbipassword@104.130.160.51/bi")
    model.metadata.create_all(engine)
    conn = engine.connect()

def chunkify(iterable, chunk_size):
    data = list(iterable)
    for i in xrange(0, len(data), chunk_size):
        yield data[i:i + chunk_size]

def query_in(model, key, values, batch_size=30):
    result = []
    for chunk in chunkify(values, batch_size):
        result.extend(model.all().filter(key + " in", chunk))
    return result

def convert_and_insert(appengine_obj):    
    converted = model.Model.from_appengine(appengine_obj)
    try:
        conn.execute(converted.table.insert(), **vars(converted))
    except IntegrityError:
        conn.execute(converted.table.update().where(converted.table.c.id == converted.id).values(**vars(converted)))

def load_through_student_list(name, max_students=100):
    logger.warn('getting classes')
    student_list = model.StudentList.model.all().filter("name =", name).get()
    logger.warn('getting students')
    students = student_list.students.fetch(max_students)
    users = [student.user for student in students]
    logger.warn('getting videos')
    user_videos = query_in(model.UserVideo.model, "user", users)
    videos = [user_video.video for user_video in user_videos]
    logger.warn('getting problems')
    problems = query_in(model.ProblemLog.model, "user", users)
    exercise_names = [problem.exercise for problem in problems]
    logger.warn('getting exercises')
    exercises = query_in(model.Exercise.model, "name", exercise_names)
    user_exercises = []
    logger.warn('getting user exercises')
    for user_chunk in chunkify(users, 3):
        for exercise_chunk in chunkify(exercise_names, 10):
            logger.warn('getting chunk')
            for retry in xrange(100):
                try:
                    user_exercises.extend(model.UserExercise.model.all().filter("exercise in ", exercise_chunk).filter("user in ", user_chunk))
                    break
                except:
                    logger.warn('retry {}'.format(retry))
    init_db()
    for obj in chain(students, problems, exercises, user_videos, videos, user_exercises):
        try:
            convert_and_insert(obj)
        except IntegrityError:
            pass

def load_from_each(n=1):
    for cls in model.Model.__subclasses__():
        for obj in cls.model.all().fetch(n):
            convert_and_insert(obj)

def load_through_problem_log(n=1000):
    problems = model.ProblemLog.model.all().fetch(n)
    exercise_names = [problem.exercise for problem in problems]
    exercises = query_in(model.Exercise.model, "name", exercise_names)
    user_ids = [problem.user for problem in problems]
    users = query_in(model.UserData.model, "user_email", [i.email() for i in user_ids])
    for obj in chain(problems, users, exercises):
        convert_and_insert(obj)

def load_student_lists(n=100):
    student_lists = model.StudentList.model.all().fetch(n)
    for student_list in student_lists:
        convert_and_insert(student_list)

def print_student_lists(n=100):
    student_lists = model.StudentList.model.all().fetch(n)
    for student_list in student_lists:
        print student_list.students.count(), student_list.key(), repr(student_list.name)

def load_data_in_range(start, end):
    logger.warn('getting user exercises')
    user_exercises = model.UserExercise.model.all().filter("last_done >= ", start).filter("last_done < ", end).fetch(10000)
    logger.warn('getting user videos')
    user_videos = model.UserVideo.model.all().filter("last_watched >= ", start).filter("last_watched < ", end).fetch(10000)
    logger.warn('got {} user exercises and {} user videos'.format(len(user_exercises), len(user_videos)))
    existing_videos = {id for (id,) in conn.execute(select([model.Video.table.c.id]))}
    video_keys = {v._video for v in user_videos}
    videos_to_fetch = [v for v in video_keys if v.id() not in existing_videos]
    logger.warn('fetching {} out of {} videos'.format(len(videos_to_fetch), len(video_keys)))
    videos = model.Video.model.get(videos_to_fetch)
    exercise_names = {user_exercise.exercise for user_exercise in user_exercises}
    existing_exercises = {name for (name,) in conn.execute(select([model.Exercise.table.c.name]))}
    exercises_to_fetch = exercise_names - existing_exercises
    logger.warn('fetching {} out of {} exercises'.format(len(exercises_to_fetch), len(existing_exercises)))
    exercises = query_in(model.Exercise.model, "name", exercises_to_fetch)
    user_emails = {i.user.email() for i in user_videos + user_exercises}
    existing_users = {u for (u,) in conn.execute(select([model.UserData.table.c.user_email]))}
    users_to_fetch = user_emails - existing_users
    logger.warn('getting {} out of {} users'.format(len(users_to_fetch), len(existing_users)))
    users = query_in(model.UserData.model, "user_email", users_to_fetch)
    student_list_ids = [student_list_key.id() for user in users for student_list_key in user.student_lists]
    student_lists = model.StudentList.model.get_by_id(student_list_ids)
    logger.warn('getting coaches')
    users += query_in(model.UserData.model, "user_email",
                      {coach.name()
                       for student_list in student_lists
                       for coach in student_list.coaches})
    logger.warn('inserting')
    for obj in chain(student_lists, users, exercises, videos, user_exercises, user_videos):
        convert_and_insert(obj)

def load_data_daily():
    last_night = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    day_before = last_night - datetime.timedelta(days=1)
    while True:
        logger.warn('fetching from {} to {}'.format(day_before, last_night))
        load_data_in_range(day_before, last_night)
        day_before = last_night
        last_night += datetime.timedelta(days=1)
        time.sleep((last_night - datetime.datetime.now()).total_seconds() + 3600) # sleep until 1AM
        
if __name__ == '__main__':
    logging.basicConfig()
    init_db()
    init_remote_api('hebkhan')
    #load_through_problem_log()
    #load_from_each()
    #load_student_lists()
    #load_through_student_list("כיתת מופת - ח3")
    #print_student_lists(300)
    #load_through_student_list(u'\u05d81-\u05d84')
    #load_data_in_range(datetime.datetime(2015, 2, 15, 19), datetime.datetime(2015, 2, 16))
    load_data_daily()