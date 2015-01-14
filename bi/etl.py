# -*- coding: utf-8 -*-
import sys, os
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
from sqlalchemy import create_engine
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
    conn.execute(converted.table.insert(), **vars(converted))

def load_through_student_list(name, max_students=100):
    student_list = model.StudentList.model.all().filter("name =", name).get()
    students = student_list.students.fetch(max_students)
    users = [student.user for student in students]
    user_videos = query_in(model.UserVideo.model, "user", users)
    videos = [user_video.video for user_video in user_videos]
    problems = query_in(model.ProblemLog.model, "user", users)
    exercise_names = [problem.exercise for problem in problems]
    exercises = query_in(model.Exercise.model, "name", exercise_names)
    user_exercises = []
    for user_chunk in chunkify(users, 10):
        for exercise_chunk in chunkify(exercise_names, 10):
            user_exercises.extend(model.UserExercise.model.all().filter("exercise in ", exercise_chunk).filter("user in ", user_chunk))
    
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

if __name__ == '__main__':
    import logging
    logging.basicConfig()
    init_db()
    init_remote_api('hebkhan')
    #load_through_problem_log()
    #load_from_each()
    load_student_lists()
    #load_through_student_list("כיתת מופת - ח3")
    #print_student_lists(300)
    load_through_student_list(u'\u05d81-\u05d84')
