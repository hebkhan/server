import layer_cache
from models import Video, Url, Topic, Setting, TopicVersion, Exercise

@layer_cache.cache_with_key_fxn(lambda:
    "exercise_title_dicts_%s" % Setting.cached_exercises_date())
def exercise_title_dicts():
    return [{
        "title": exercise.display_name,
        "key": str(exercise.key()),
        "relative_url": exercise.relative_url,
        "id": exercise.name,
    } for exercise in Exercise.get_all_use_cache() if not exercise.summative]

@layer_cache.cache_with_key_fxn(lambda version_number=None: 
    "video_title_dicts_%s" % (
    version_number or Setting.topic_tree_version()))
def video_title_dicts(version_number=None):
    if version_number:
        version = TopicVersion.get_by_number(version_number)
    else:
        version = None

    return [{
        "title": video.title,
        "key": str(video.key()),
        "relative_url": "/video/%s" % video.readable_id,
        "id": video.readable_id
    } for video in Video.get_all_live(version=version) if video is not None]

@layer_cache.cache_with_key_fxn(lambda version_number=None: 
    "url_title_dicts_%s" % (
    version_number or Setting.topic_tree_version()))
def url_title_dicts(version_number=None):
    if version_number:
        version = TopicVersion.get_by_number(version_number)
    else:
        version = None

    return [{
        "title": url.title,
        "key": str(url.key()),
        "relative_url": url.url,
        "id": url.key().id()
    } for url in Url.get_all_live(version=version)]

@layer_cache.cache_with_key_fxn(lambda version_number=None: 
    "topic_title_dicts_%s" % (
    version_number or Setting.topic_tree_version()))
def topic_title_dicts(version_number=None):
    if version_number:
        version = TopicVersion.get_by_number(version_number)
    else:
        version = None

    return [{
        "title": topic.standalone_title,
        "key": str(topic.key()),
        "relative_url": "/%s" % topic.relative_url,
        "id": topic.id
    } for topic in Topic.get_content_topics(version=version)]

