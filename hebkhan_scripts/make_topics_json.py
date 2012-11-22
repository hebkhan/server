#!/usr/bin/env python2.7
# coding=utf8

import re
import csv
import json
import sys
import fileinput
import itertools
import urllib2
ILLEGAL_CHARS_IN_ID = re.compile("[-:,\"]")

def make_id(title):
    return "-".join(ILLEGAL_CHARS_IN_ID.sub("-", title).split())

counter = itertools.count(10)
def get_id(prefix, id=None):
    return "%s_%04d" % (prefix, id or next(counter)*10)

def log(msg, *args):
    sys.stderr.write(msg % args + "\n")

def get_topic_tree(videos):

    class Topic(dict):
        all = {}

        def __init__(self, title, id=None, parent=None):
            if not id:
                id = "%s_%03d" % (parent["id"], next(parent.counter)*10)
            self.counter = itertools.count(1)
            self['id'] = id
            self['title'] = title
            self['children'] = []
            self['kind'] = "Topic"
            self.__class__.all[title] = self
            log(" Topic: %s / %s -- %s", parent and parent['id'], self['id'], self['title'])
            if parent:
                parent['children'].append(self)

        @classmethod
        def get_or_create(cls, key, parent_key=None):
            try:
                return cls.all[key]
            except KeyError:
                parent = cls.get_or_create(parent_key) if parent_key else ROOT
                return cls(key, parent=parent)


    def process((id, name, description, topics, youtube_id)):
        video = dict(
                     kind = "Video",
                     title = name,
                     description = description,
                     youtube_id = youtube_id,
                     readable_id = get_id("video", int(id)),
                     )

        t1 = topics[0]
        for t2 in topics[1:]:
            topic = Topic.get_or_create(t2, t1)
            t1 = t2
        topic['children'].append(video)
        log("    Video: %s -- %s", video['readable_id'], video['title'])

    ROOT = Topic('שורש כל הידע', "root")

    for video in videos:
        process(video)

    return ROOT


VIDEOS_URL = "https://docs.google.com/spreadsheet/pub?key=0Ap8djBdeiIG7dFlFbElFRmxKclBIaFdfN3FhcWFnUHc&single=true&gid=1&output=csv"

RE_YOUTUBE_ID = re.compile("\?v=([-\w]+)|\.be/([-\w]+)")

def iter_videos():
    lines = csv.reader(urllib2.urlopen(VIDEOS_URL))
    _header = next(lines)

    c = 0
    for id, name, description, originalName, url, subtopic, topic in lines:
        description += " (%s)" % originalName
        youtube_id, = filter(None, RE_YOUTUBE_ID.search(url).groups())
        topics = map(str.strip, ":".join((topic, subtopic)).split(":"))
        yield (id, name, description, topics, youtube_id)
        c+=1
    print "Read %s lines" % c

if __name__ == '__main__':
    with open("tree_of_knowledge.json", "w") as f:
        f.write(json.dumps(get_topic_tree(iter_videos()),
                           indent=4,
                           ensure_ascii=False,
                           ) + "\n")

def convert():
    f = fileinput.input()
    content = "".join(f)
    videos = json.loads(content, "utf-8")
    tree = get_topic_tree(videos)
    with open("tree_of_knowledge.json") as f:
        f.write(json.dumps(tree, indent=4) + "\n")
