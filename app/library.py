import layer_cache
from models import Setting, Topic, TopicVersion, ExerciseVideo, Exercise
import request_handler
import shared_jinja
import time
import math
import logging
from collections import Counter

# helpful function to see topic structure from the console.  In the console:
# import library
# library.library_content_html(bust_cache=True)
#
# Within library_content_html: print_topics(topics)
def print_topics(topics):
    for topic in topics:
        print topic.homepage_title
        print topic.depth
        if topic.subtopics:
            print "subtopics:"
            for subtopic in topic.subtopics:
                print subtopic.homepage_title
                if subtopic.subtopics:
                    print "subsubtopics:"
                    for subsubtopic in subtopic.subtopics:
                        print subsubtopic.homepage_title
                    print " "
            print " "
        print " "

def walk_children(node):
    if node.key().kind() == "Topic":
        for child in node.children:
            for node in walk_children(child):
                yield node
    else:
        yield node

def prepare(topic, depth=0, max_depth=4):
    topic.content = []
    topic.subtopics = []
    topic.depth = depth
    topic.is_leaf = depth >= max_depth

    def add_once(child, _dups=set()):
        if child.key() not in _dups:
            _dups.add(child.key())
            topic.content.append(child)
        else:
            logging.debug("Dup: %s (%s)", child.readable_id, topic.id)

    for child in topic.children:
        if child.key().kind() == "Topic":
            if topic.is_leaf:
                map(add_once, walk_children(child))
            else:
                topic.subtopics.extend(prepare(child, depth=depth+1, max_depth=max_depth))
        else:
            add_once(child)

    del topic.children

    if not (topic.content or topic.subtopics):
        return []  # trim this branch

    topic.height = math.ceil(len(topic.content)/3.0) * 18

    topic.content_count = Counter(item.kind().lower() for item in topic.content)
    topic.all_content_count = Counter(topic.content_count)
    for subtopic in topic.subtopics:
        topic.all_content_count.update(subtopic.all_content_count)

    return [topic]

def add_related_exercises(videos):
    exercises = {e.key():e for e in Exercise.get_all_use_cache()}
    relations = {}
    for exvid in ExerciseVideo.all().run():
        ex = exercises.get(exvid.key_for_exercise())
        if ex:
            relations.setdefault(exvid.key_for_video(),[]).append(ex)

    for exs in relations.itervalues():
        exs.sort(key=lambda e: (e.v_position, e.h_position))

    logging.info("%s related videos", len(relations))
    for vid in videos:
        exs = relations.get(vid.key()) or []
        vid.cached_related_exercises = exs

@layer_cache.cache_with_key_fxn(
        lambda ajax=False, version_number=None: 
        "library_content_by_topic_%s_v%s" % (
        "ajax" if ajax else "inline", 
        version_number if version_number else Setting.topic_tree_version()),
        layer=layer_cache.Layers.Blobstore
        )
def library_content_html(ajax=False, version_number=None):

    if version_number:
        version = TopicVersion.get_by_number(version_number)
    else:
        version = TopicVersion.get_default_version()

    tree = Topic.get_root(version).make_tree(types = ["Topics", "Video", "Exercise", "Url"])

    videos = [item for item in walk_children(tree) if item.kind()=="Video"]
    add_related_exercises(videos)

    topics = prepare(tree)[0].subtopics

    # special case the duplicate topics for now, eventually we need to either make use of multiple parent functionality (with a hack for a different title), or just wait until we rework homepage
    topics = [topic for topic in topics if (not topic.id == "new-and-noteworthy")]

    timestamp = time.time()

    template_values = {
        'topics': topics,
        'ajax' : ajax,
        # convert timestamp to a nice integer for the JS
        'timestamp': int(round(timestamp * 1000)),
        'version_date': str(version.made_default_on),
        'version_id': version.number
    }

    html = shared_jinja.get().render_template("library_content_template.html", **template_values)

    return html

class GenerateLibraryContent(request_handler.RequestHandler):

    def post(self):
        # We support posts so we can fire task queues at this handler
        self.get(from_task_queue = True)

    def get(self, from_task_queue = False):
        library_content_html(ajax=True, version_number=None, bust_cache=True)

        if not from_task_queue:
            self.redirect("/")

