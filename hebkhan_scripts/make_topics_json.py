#!/usr/bin/env python2.7
# coding=utf8

import re
import csv
import json
import sys
import fileinput
import itertools
import requests
import gevent
from collections import namedtuple
import logging

ILLEGAL_CHARS_IN_ID = re.compile("[-:,\"]")

def make_id(title):
    return "-".join(ILLEGAL_CHARS_IN_ID.sub("-", title).split())

counter = itertools.count(10)
def get_id(prefix, id=None):
    return "%s_%04d" % (prefix, id or next(counter)*10)

def log(msg, *args):
    sys.stderr.write(msg % args + "\n")

def get_topic_tree(videos, root_topic_id='root'):

    class Topic(dict):
        all = {}

        def __init__(self, readable_id, title, parent=None):
            self.__class__.all[readable_id] = self
            self['id'] = readable_id
            self['title'] = title.decode("utf-8")
            self['children'] = []
            self['videos'] = set()
            self['kind'] = "Topic"
            logging.info(" Topic: %s -- %s", "--".join(readable_id), self['title'])
            if parent:
                parent['children'].append(self)

        def get_or_create(self, readable_id, title):
            readable_id = (readable_id,)
            if self != root_topic:
                readable_id = self['id'] + readable_id
            try:
                return self.all[readable_id]
            except KeyError:
                return self.__class__(readable_id, title, parent=self)

    def to_id(ids):
        ids = list(ids)
        parts = (p0 for p0, p1 in zip(ids, ids[1:] + [""]) if p0 not in p1)
        return "--".join(parts).lower().replace(" ","-")

    root_topic = Topic((root_topic_id,), "")
    for i, vid in enumerate(videos):
        topic_ids = [vid[k] for k in sorted(vid) if k.startswith("topic_id")]
        topic_names = [vid[k] for k in sorted(vid) if k.startswith("topic_name")]
        assert len(topic_ids) == len(topic_names), "topic_id columns must match topic_name columns"

        if vid['readable_id']:
            readable_id = vid['readable_id']
        else:
            readable_id = to_id(topic_ids + [("L%s" % vid['line'])])
        description = "\n".join(vid['description'].split("\\n"))
        if vid['source'] == "ani10":
            title = vid['orig_name'].split("-")[-1].strip()
            description += "\n(%s)" % vid['orig_name']
        video = dict(
                     kind = "Video",
                     source = vid['source'],
                     title = title.decode("utf-8"),
                     standalone_title = title.decode("utf-8"),
                     description = description.decode("utf-8"),
                     youtube_id = vid['youtube_id'],
                     readable_id = readable_id,
                     )
        video = {k:v for k,v in video.iteritems() if v!=""}

        topic = root_topic
        for key, title in zip(topic_ids, topic_names):
            if key and title:
                topic = topic.get_or_create(key or "unnamed", title or "unnamed")

        if video['youtube_id'] not in topic['videos']:
            topic['children'].append(video)
            topic['videos'].add(video['youtube_id'])
        logging.debug("    Video: %s -- %s", video['readable_id'], video.get('title'))

    def to_dict(d):
        if d['kind'] == "Topic":
            d['id'] = to_id(d['id'])
            d['children'] = [to_dict(sd) for sd in d['children']]
            del d['videos']
        return dict(d)

    return to_dict(root_topic)

VIDEOS_URL = "https://docs.google.com/spreadsheet/pub?key=0Ap8djBdeiIG7dEg2blg1YlNLbUdBTnJYb1lFUU1fZlE&single=true&gid=1&output=csv"

#http://www.hebrewkhan.org/api/v1/videos/prime-numbers

def get_videos():

    lines = csv.reader(requests.get(VIDEOS_URL).iter_lines())
    header = next(lines)
    Video = lambda line: dict(zip(header, line))

    videos = []
    def get_video(video):
        if video['source'] == "khan":
            khan_info = requests.get("http://www.hebrewkhan.org/api/v1/videos/" + video['readable_id']).json()
            if not khan_info:
                raise Exception("No video for %r" % (video,))
            video['youtube_id'] = khan_info['youtube_id']
        logging.info("got %s", video['youtube_id'])
        videos.append(video)

    from gevent.pool import Pool
    video_getters = Pool(size=100)
    for line in lines:
        if not any(line):
            break
        video = Video(line)
        video_getters.spawn_link_exception(get_video, video)
    video_getters.join()

    return videos

if __name__ == '__main__':
    import gevent.monkey
    gevent.monkey.patch_all()

    logging.basicConfig(level=logging.INFO, format="%(levelname)-10s|%(name)-30s|%(message)s")
    logging.getLogger("requests").setLevel(logging.WARNING)

    root = get_topic_tree(get_videos())
    for tree in root['children']:
        all_children = tree['children']
        for i in xrange(0, len(all_children), 3):
            tree['children'] = all_children[i:i+3]
            logging.info("Writing %s - %s", tree['id'], i)
            with open("tree_of_knowledge-%s-%s.json" % (tree['id'], i), "w") as f:
                f.write(json.dumps(tree,
                                   indent=4,
                                   ensure_ascii=False,
                                   ).encode("utf8") + "\n")

def convert():
    f = fileinput.input()
    content = "".join(f)
    videos = json.loads(content, "utf-8")
    tree = get_topic_tree(videos)
    with open("tree_of_knowledge.json") as f:
        f.write(json.dumps(tree, indent=4) + "\n")
