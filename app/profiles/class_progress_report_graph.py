# coding=utf8
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


STATUSES = dict(
    started = "התחיל",
    completed = "צפה",
    review = "סיים",
    struggling = "מתקשה",
    proficient = "מנוסה",
    proficient_implicit = "מנוסה (עקב נסיון ביחידות מתקדמות יותר)",
)
STATUSES[""] = ""


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

    all_video_progress = dict(get_video_progress_for_students(list_students, granular=False))
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
        for video in video_list:
            status_name = video_progress.get(video["key_id"], "")
            status = STATUSES[status_name]
            student_data['videos'].append({
                    "name": video["display_name"],
                    "status": status,
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
    youtube_ids = {video.key().id(): video.youtube_id for video in Video.get_all()}
    def get_key_and_progress(vid_str, student, progress):
        vid_id = int(vid_str[2:])
        if granular and progress is not 'completed':
            try:
                youtube_id = youtube_ids[vid_id]
            except KeyError:
                logging.error("Couldn't get youtube_id for %s", vid_id)
            else:
                user_video = UserVideo.get_for_video_and_user_data(youtube_id, student)
                if user_video:
                    points = video_progress_from_points(VideoPointCalculator(user_video))
                    if points > 0.9:
                        progress = "completed"
                    elif points > 0.66:
                        progress = "watched-most"
                    elif points > 0.33:
                        progress = "watched-some"
        return vid_id, progress

    keys = (UserVideoCss._key_for(student) for student in students)
    data = UserVideoCss.get_by_key_name(keys)
    for student, css in izip(students, data):
        if css:
            vid_css_data = pickle.loads(css.pickled_dict)
            video_progress = dict(
                get_key_and_progress(vid_str, student, progress)
                for progress, vids in vid_css_data.iteritems()
                for vid_str in vids
            )
            yield student, video_progress
        else:
            yield student, {}
