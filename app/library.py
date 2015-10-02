#!/usr/bin/python
# -*- coding: utf-8 -*-
import layer_cache
from models import Setting, Topic, TopicVersion, ExerciseVideo, Exercise, Video
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

class TopicDummy(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)

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
            child.key_id = child.key().id()
            add_once(child)

    del topic.children

    if not (topic.content or topic.subtopics):
        return []  # trim this branch

    topic.content_count = Counter(item.kind().lower() for item in topic.content)
    topic.content_count['mobile_exercise'] += sum(1 for item in topic.content if item.kind() == "Exercise" and item.is_mobile_compatible)

    if topic.content and topic.subtopics:
        dummy = TopicDummy(id=topic.id+"-leaf", title=u"תוכן נוסף", content=topic.content, subtopics=[],
                           content_count=topic.content_count, all_content_count=topic.content_count, depth=topic.depth+1)
        topic.subtopics.append(dummy)
        topic.content = []
        topic.content_count = {}

    topic.all_content_count = Counter(topic.content_count)
    for subtopic in topic.subtopics:
        topic.all_content_count.update(subtopic.all_content_count)

    topic.height = math.ceil(len(topic.content)/3.0) * 18

    return [topic]

@layer_cache.cache_with_key_fxn(
        lambda mobile=False, version_number=None: 
        "library_content_by_topic_%s_v%s" % (
        "mobile" if mobile else "desktop", 
        version_number if version_number else Setting.topic_tree_version()),
        layer=layer_cache.Layers.Blobstore
        )
def library_content_html(mobile=False, version_number=None):

    if version_number:
        version = TopicVersion.get_by_number(version_number)
    else:
        version = TopicVersion.get_default_version()

    tree = Topic.get_root(version).make_tree(types = ["Topics", "Video", "Exercise", "Url"])

    root, = prepare(tree)
    topics = root.subtopics

    timestamp = time.time()

    template_values = {
        'topics': topics,
        'is_mobile': mobile,
        # convert timestamp to a nice integer for the JS
        'timestamp': int(round(timestamp * 1000)),
        'version_date': str(version.made_default_on),
        'version_id': version.number,
        'approx_vid_count': Video.approx_count(),
        'exercise_count': Exercise.get_count(),
    }

    html = shared_jinja.get().render_template("library_content_template.html", **template_values)

    return html

class GenerateLibraryContent(request_handler.RequestHandler):

    def post(self):
        # We support posts so we can fire task queues at this handler
        self.get(from_task_queue = True)

    def get(self, from_task_queue = False):
        library_content_html(mobile=False, version_number=None, bust_cache=True)

        if not from_task_queue:
            self.redirect("/")

