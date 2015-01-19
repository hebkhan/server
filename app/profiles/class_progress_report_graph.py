# coding=utf8
import datetime
from itertools import izip, chain
import logging
from jinja2.utils import escape

from templatefilters import escapejs, timesince_ago
from points import VideoPointCalculator, video_progress_from_points
from models import Exercise, UserExerciseGraph
from models import UserVideoCss, Video, UserVideo
from models import Topic, Setting
import pickle
import layer_cache


@layer_cache.cache_with_key_fxn(
    lambda : "content_data_%s" % (Setting.cached_content_add_date()),
    layer=layer_cache.Layers.Blobstore)
def get_content_data():
    topics = {str(t.key()):(idx, t) for idx, t in enumerate(Topic.get_visible_topics())}
    topic_names = {}
    def get_topics_of(item):
        def g():
            if not item.topic_string_keys:
                return
            seen = set()
            for tk in item.topic_string_keys:
                try:
                    idx, topic = topics[tk]
                except KeyError:
                    continue
                for depth, tk2 in enumerate(topic.ancestor_keys[:-1][::-1]):
                    try:
                        idx2, topic2 = topics[str(tk2)]
                    except KeyError:
                        continue
                    if idx2 in seen:
                        continue
                    seen.add(idx2)
                    topic_names[idx2] = topic2.title
                    # use depth for sorting by topic level
                    yield depth, idx2
        return [idx for _, idx in sorted(g())]

    videos = {video.key().id():
        dict(
            key_id=video.key().id(),
            name=video.readable_id,
            display_name=video.title,
            topics=get_topics_of(video)
        ) for video in Video.get_all()}

    exercises = {exercise.name:
        dict(
            name=exercise.name,
            display_name=exercise.display_name,
            topics=get_topics_of(exercise),
        ) for exercise in Exercise.get_all_use_cache()}

    return topic_names, videos, exercises


def class_progress_report_graph_context(user_data, list_students):
    if not user_data:
        return {}


    all_topic_names, videos_all, exercises_all = get_content_data()
    list_students = sorted(list_students, key=lambda student: student.nickname)

    student_email_pairs = [(escape(s.email), (s.nickname[:14] + '...') if len(s.nickname) > 17 else s.nickname) for s in list_students]
    emails_escapejsed = [escapejs(s.email) for s in list_students]

    user_exercise_graphs = UserExerciseGraph.get(list_students)

    exercise_list = []

    for name, exercise in exercises_all.iteritems():
        for user_exercise_graph in user_exercise_graphs:
            graph_dict = user_exercise_graph.graph_dict(name)
            if graph_dict and graph_dict["total_done"]:
                exercise_list.append(exercise)
                break

    exercise_list.sort(key=lambda e: e["display_name"])

    all_video_progress = get_video_progress_for_students(list_students, granular=False)
    videos_found = reduce(set.union, all_video_progress.itervalues(), set())
    video_list = [videos_all[vid_id] for vid_id in videos_found if vid_id in videos_all]
    video_list.sort(key=lambda v: v["display_name"])

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

        for e in exercise_list:
            exercise_name, exercise_display, exercise_name_js =  e["name"], e["display_name"], escapejs(e["name"])

            graph_dict = user_exercise_graph.graph_dict(exercise_name)

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

            if status_name:
                student_data['exercises'].append({
                    "status_name": status_name,
                    "progress": graph_dict["progress"],
                    "total_done": graph_dict["total_done"],
                    "last_done": graph_dict["last_done"] if graph_dict["last_done"] and graph_dict["last_done"].year > 1 else '',
                    "last_done_ago": timesince_ago(graph_dict["last_done"]) if graph_dict["last_done"] and graph_dict["last_done"].year > 1 else ''
                })
            else:
                student_data['exercises'].append({
                    "name": exercise_name,
                    "status_name": status_name,
                })

        video_progress = all_video_progress[student]
        for video in video_list:
            status_name = video_progress.get(video["key_id"], "")
            student_data['videos'].append({
                    "name": video["display_name"],
                    "status_name": status_name,
                })

    # prune topics
    topic_names = {
        topic_id: all_topic_names[topic_id]
        for item in chain(exercise_list, video_list)
        for topic_id in item['topics']
    }

    # clean-up video list
    for video in video_list:
        video.pop("key_id")

    student_row_data = [data for key, data in progress_data.iteritems()]

    return {
        'exercise_names': exercise_list,
        'video_names': video_list,
        'topic_names': topic_names,
        'progress_data': student_row_data,
        'coach_email': user_data.email,
        'c_points': reduce(lambda a, b: a + b, map(lambda s: s.points, list_students), 0)
    }


def get_video_progress_for_students(students, granular=True):
    def get_key_and_progress(user_video):
        vid_id = UserVideo.video.get_value_for_datastore(user_video).id()
        points = video_progress_from_points(VideoPointCalculator(user_video))
        if points > 0.9:
            progress = "completed"
        elif points > 0.66:
            progress = "watched-most"
        elif points > 0.33:
            progress = "watched-some"
        else:
            progress = "not-started"
        return vid_id, progress

    dt_start = datetime.datetime.now() - datetime.timedelta(days=31)
    keys = [s.user for s in students]
    key_to_student = dict(zip(keys, students))
    items = []
    for key_chunk in (keys[i:i+30] for i in xrange(0,len(keys),30)):
        query = UserVideo.all().filter("last_watched >=", dt_start)
        items.extend(query.filter("user in", key_chunk))

    students_progress = {}
    for user_video in items:
        user_key = UserVideo.user.get_value_for_datastore(user_video)
        vid_id, progress = get_key_and_progress(user_video)
        students_progress.setdefault(key_to_student[user_key], {})[vid_id] = progress

    return students_progress
