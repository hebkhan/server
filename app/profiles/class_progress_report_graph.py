# coding=utf8
from itertools import izip

from jinja2.utils import escape

from templatefilters import escapejs, timesince_ago
from models import Exercise, UserExerciseGraph
from models import UserVideoCss, Video
import pickle


STATUSES = dict(
    started = "התחיל",
    completed = "צפה",
    review = "סיים",
    struggling = "מתקשה",
    proficient = "מנוסה",
    proficient_implicit = "מנוסה (עקב נסיון ביחידות מתקדמות יותר)",
)
STATUSES[""] = ""

def class_progress_report_graph_context(user_data, list_students):
    if not user_data:
        return {}

    list_students = sorted(list_students, key=lambda student: student.nickname)

    student_email_pairs = [(escape(s.email), (s.nickname[:14] + '...') if len(s.nickname) > 17 else s.nickname) for s in list_students]
    emails_escapejsed = [escapejs(s.email) for s in list_students]

    exercises_all = Exercise.get_all_use_cache()
    user_exercise_graphs = UserExerciseGraph.get(list_students)

    exercises_found = []

    for exercise in exercises_all:
        for user_exercise_graph in user_exercise_graphs:
            graph_dict = user_exercise_graph.graph_dict(exercise.name)
            if graph_dict and graph_dict["total_done"]:
                exercises_found.append(exercise)
                break

    exercise_names = [(e.name, e.display_name, escapejs(e.name)) for e in exercises_found]
    exercise_list = sorted(({'name': e.name, 'display_name': e.display_name}
                            for e in exercises_found), key=lambda e: e.display_name)

    all_video_progress = dict(get_video_progress_for_students(list_students))
    videos_found = reduce(set.union, all_video_progress.itervalues(), set())

    videos_all = Video.get_all()
    videos_found = [video for video in videos_all if video.key().id() in videos_found]
    video_list = sorted(({'name': v.readable_id, 'display_name': v.title}
                            for v in videos_found), key=lambda v: v.title)

    progress_data = {}

    for (student, student_email_pair, escapejsed_student_email, user_exercise_graph) in izip(list_students, student_email_pairs, emails_escapejsed, user_exercise_graphs):

        student_email = student.email
        student_review_exercise_names = user_exercise_graph.review_exercise_names()
        progress_data[student_email] = student_data = {
            'email': student.email,
            'nickname': student.nickname,
            'profile_root': student.profile_root,
            'exercises': [],
            'videos': [],
        }

        for (exercise, (_, exercise_display, exercise_name_js)) in izip(exercises_found, exercise_names):

            exercise_name = exercise.name
            graph_dict = user_exercise_graph.graph_dict(exercise_name)

            status = ""
            status_name = ""

            if graph_dict["proficient"]:
                if exercise_name in student_review_exercise_names:
                    status_name = "review"
                else:
                    if not graph_dict["explicitly_proficient"]:
                        status_name = "proficient_implicit"
                    else:
                        status_name = "proficient"
            elif graph_dict["struggling"]:
                status_name = "struggling"
            elif graph_dict["total_done"] > 0:
                status_name = "started"

            status = STATUSES[status_name]
            if status:
                student_data['exercises'].append({
                    "status": status,
                    "status_name": status_name,
                    "progress": graph_dict["progress"],
                    "total_done": graph_dict["total_done"],
                    "last_done": graph_dict["last_done"] if graph_dict["last_done"] and graph_dict["last_done"].year > 1 else '',
                    "last_done_ago": timesince_ago(graph_dict["last_done"]) if graph_dict["last_done"] and graph_dict["last_done"].year > 1 else ''
                })
            else:
                student_data['exercises'].append({
                    "name": exercise_name,
                    "status": status,
                })

        video_progress = all_video_progress[student]
        for video in videos_found:
            status_name = video_progress.get(video.key().id(), "")
            status = STATUSES[status_name]
            student_data['videos'].append({
                    "name": video.title,
                    "status": status,
                    "status_name": status_name,
                })


    student_row_data = [data for key, data in progress_data.iteritems()]

    return {
        'exercise_names': exercise_list,
        'video_names': video_list,
        'progress_data': student_row_data,
        'coach_email': user_data.email,
        'c_points': reduce(lambda a, b: a + b, map(lambda s: s.points, list_students), 0)
    }


def get_video_progress_for_students(students):
    keys = (UserVideoCss._key_for(student) for student in students)
    data = UserVideoCss.get_by_key_name(keys)
    for student, css in izip(students, data):
        if css:
            vid_css_data = pickle.loads(css.pickled_dict)
            video_progress = {
                int(vid_str[2:]): progress
                for progress, vids in vid_css_data.iteritems()
                for vid_str in vids
            }
            yield student, video_progress
        else:
            yield student, {}
