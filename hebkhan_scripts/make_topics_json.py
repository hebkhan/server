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
import shelve
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
        assert len(set(filter(None, topic_ids))) == len(filter(None, topic_ids)), "can't repeat topic_ids: [%s]" % topic_ids
        assert len(topic_ids) == len(topic_names), "topic_id columns must match topic_name columns"

        if vid['readable_id']:
            readable_id = vid['readable_id']
        else:
            readable_id = to_id(topic_ids + [("L%s" % vid['line'])])
        # split using special escape-sequece "\n"
        description = "\n".join(vid['description'].split("\\n"))
        if vid['source'] == "ani10":
            title = vid['orig_name'].split("-")[-1].strip().decode("utf-8")
            description += "\n(%s)" % vid['orig_name']
        else:
            title = vid['title']
        video = dict(
                     kind = "Video",
                     source = vid['source'],
                     title = title,
                     description = description.decode("utf-8"),
                     youtube_id = vid['youtube_id'],
                     youtube_id_en = vid.get('youtube_id_en'),
                     readable_id = readable_id,
                     update = True,
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

from contextlib import contextmanager
@contextmanager
def video_cache():
    cache = shelve.open("video_cache")
    stats = dict(hits=0, misses=0)
    def _get_video(readable_id):
        if readable_id not in cache:
            for i in xrange(5):
                try:
                    cache[readable_id]  = requests.get("http://www.hebrewkhan.org/api/v1/videos/" + readable_id).json()
                    break
                except Exception, e:
                    logging.error(e)
                    gevent.sleep(2)
            else:
                raise
            stats['misses'] += 1
        else:
            stats['hits'] += 1
        return cache[readable_id]
    try:
        yield _get_video
    finally:
        logging.info("Hits: %(hits)s, Misses: %(misses)s", stats)
        cache.close()

def get_videos():

    logging.info("Fetching from %s", VIDEOS_URL)
    lines = csv.reader(requests.get(VIDEOS_URL).iter_lines())
    header = next(lines)
    Video = lambda line: dict(zip(header, line))

    videos = []
    with video_cache() as _get_video:
        def get_video(video):
            if video['source'] == "khan":
                khan_info = _get_video(video['readable_id'])
                if not khan_info:
                    raise Exception("No video for %r" % (video,))
                video['youtube_id'] = id1 = khan_info['youtube_id']
                video['youtube_id_en'] = id2 = khan_info['youtube_id_en']
                video['source'] = "khan" if id1==id2 else "hebkhan"
                video['title'] = khan_info['title']

            logging.info("got %(youtube_id)s (%(source)s)", video)
            videos.append(video)

        from gevent.pool import Pool
        video_getters = Pool(size=50)
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
        for i in xrange(0, len(all_children), 5):
            tree['children'] = all_children[i:i+5]
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
