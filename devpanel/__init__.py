import os, logging

from google.appengine.ext import db, deferred
from google.appengine.api import users, urlfetch
import util
from app import App
from models import UserData
from common_core.models import CommonCoreMap
import request_handler
import user_util
import itertools, functools
from api.auth.xsrf import ensure_xsrf_cookie

import gdata.youtube
import gdata.youtube.data
import gdata.youtube.service
import urllib
import csv
import StringIO
import simplejson
import re
import models
import zlib
import pickle

class Panel(request_handler.RequestHandler):

    @user_util.developer_only
    def get(self):
        self.render_jinja2_template('devpanel/panel.html', { "selected_id": "panel" })

class KhanSyncStepLog(db.Model):
    dt = db.DateTimeProperty(auto_now_add = True)
    topics = db.StringProperty()
    remap_doc_id = db.StringProperty()

    error = db.TextProperty()
    done = db.BooleanProperty()

class Sync(request_handler.RequestHandler):

    @user_util.developer_only
    def get(self):
        latest_log = KhanSyncStepLog.all().order("-dt").get()

        template_values = {
                "selected_id": "sync",
                "syncing" : latest_log and not latest_log.done,
                "last_sync" : latest_log.dt if latest_log else None,
                "topics": latest_log.topics if latest_log else "math, physics, biology",
                "remap_doc_id": latest_log.remap_doc_id if latest_log else "",
                "sync_error": latest_log.error if latest_log else "",
        }
        self.render_jinja2_template('devpanel/sync.html', template_values)

    @user_util.developer_only
    def post(self):
        topics = self.request_string("topics")
        topics = set(str(s).strip() for s in topics.split(","))
        remap_doc_id = self.request_string("remap_doc_id")

        try:
            self.topic_update_from_live(topics, remap_doc_id)
        except Exception, e:
            logging.exception("Error initiating sync (%s, %s)", topics, remap_doc_id)
            sync_error = "Error initiating sync: %s" % e

            template_values = {
                    "selected_id": "sync",
                    "last_sync" : None,
                    "topics": ", ".join(topics),
                    "remap_doc_id": remap_doc_id,
                    "sync_error": sync_error,
            }

            self.render_jinja2_template('devpanel/sync.html', template_values)
        else:
            self.redirect('/devadmin/sync')

    def topic_update_from_live(self, topics, remap_doc_id):

        step_log = KhanSyncStepLog(topics=", ".join(sorted(topics)),
                                   remap_doc_id=remap_doc_id)

        logging.info("Importing topics from khanacademy.org: %s", ", ".join(sorted(topics)))

        url = "http://www.khanacademy.org/api/v1/topictree"
        try:
            result = urlfetch.fetch(url, deadline=30)
        except Exception, e:
            raise Exception("%s (%s)" % (e, url))
        topictree = simplejson.loads(result.content)

        url = "https://docs.google.com/spreadsheet/pub?key=%s&single=true&gid=0&output=csv" % remap_doc_id
        try:
            result = urlfetch.fetch(url, deadline=30)
        except Exception, e:
            raise Exception("%s (%s)" % (e, url))


        def filter_unwanted(branch):
            if not branch["kind"] == "Topic":
                return None
            if branch["id"] in topics:
                topics.remove(branch["id"]) # so we can tell if any topics weren't found
                return True
            wanted_children = []
            wanted = False
            for child in branch["children"]:
                ret = filter_unwanted(child)
                if ret in (None, True):
                    wanted_children.append(child)
                wanted |= (ret or False)
            branch["children"][:] = wanted_children
            return wanted

        filter_unwanted(topictree)
        if topics:
            raise Exception("These topics were not found in the live topictree: %s", ", ".join(sorted(topics)))

        mapping = {}
        reader = csv.reader(StringIO.StringIO(result.content))
        for row in reader:
            if set(map(str.lower, row)) & set(["serial","subject","english","hebrew"]):
                header = [re.sub("\W","_",r.lower()) for r in row]
                mapped_vids = (dict(zip(header, row)) for row in reader)
                mapping = dict((m["english"], m["hebrew"]) for m in mapped_vids if m["hebrew"])
                logging.info("Loaded %s mapped videos", len(mapping))
                break

        if not mapping:
            raise Exception("Unrecognized spreadsheet format")

        logging.info("calling /_ah/queue/deferred_import")
        step_log.put()

        # importing the full topic tree can be too large so pickling and compressing
        deferred.defer(khan_import_task, step_log,
                       zlib.compress(pickle.dumps((topictree, mapping))),
                       _queue="import-queue",
                       _url="/_ah/queue/deferred_import")

def khan_import_task(step_log, data):

    try:
        models.topictree_import_task("edit", "root", False,
                                     data,
                                     replace=False,
                                     )
    except Exception, e:
        step_log.error = "Error in task: %s" % e
        step_log.put()
        raise

    step_log.done = True
    step_log.put()

    return True

class MergeUsers(request_handler.RequestHandler):

    @user_util.developer_only
    def get(self):

        source = self.request_user_data("source_email")
        target = self.request_user_data("target_email")

        merged = self.request_bool("merged", default=False)
        merge_error = ""

        if not merged and bool(source) != bool(target):
            merge_error = "Both source and target user emails must correspond to existing accounts before they can be merged."

        template_values = {
                "selected_id": "users",
                "source": source,
                "target": target,
                "merged": merged,
                "merge_error": merge_error,
        }

        self.render_jinja2_template("devpanel/mergeusers.html", template_values)

    @user_util.developer_only
    def post(self):

        if not self.request_bool("confirm", default=False):
            self.get()
            return

        source = self.request_user_data("source_email")
        target = self.request_user_data("target_email")

        merged = False

        if source and target:

            old_source_email = source.email

            # Make source the new official user, because it has all the historical data.
            # Just copy over target's identifying properties.
            source.current_user = target.current_user
            source.user_email = target.user_email
            source.user_nickname = target.user_nickname
            source.user_id = target.user_id

            # Put source, which gives it the same identity as target 
            source.put()

            # Delete target
            target.delete()

            self.redirect("/devadmin/emailchange?merged=1&source_email=%s&target_email=%s" % (old_source_email, target.email))
            return

        self.redirect("/devadmin/emailchange")
        
class Manage(request_handler.RequestHandler):

    @user_util.admin_only # only admins may add devs, devs cannot add devs
    @ensure_xsrf_cookie
    def get(self):
        developers = UserData.all()
        developers.filter('developer = ', True).fetch(1000)
        template_values = { 
            "developers": developers,
            "selected_id": "devs",
        }

        self.render_jinja2_template('devpanel/devs.html', template_values) 
        
class ManageCoworkers(request_handler.RequestHandler):

    @user_util.developer_only
    @ensure_xsrf_cookie
    def get(self):

        user_data_coach = self.request_user_data("coach_email")
        user_data_coworkers = []

        if user_data_coach:
            user_data_coworkers = user_data_coach.get_coworkers_data()

        template_values = {
            "user_data_coach": user_data_coach,
            "user_data_coworkers": user_data_coworkers,
            "selected_id": "coworkers",
        }

        self.render_jinja2_template("devpanel/coworkers.html", template_values)
        
def update_common_core_map(remap_doc_id, reset=False):
    fetch = functools.partial(urlfetch.fetch, deadline=30)
    from util import namedtuple

    url_fmt = "http://docs.google.com/spreadsheet/pub?key=%s&gid=%s&single=true&output=csv"

    try:
        # gid=8 for second worksheet
        url = url_fmt % (remap_doc_id, 8)
        result = fetch(url)
    except Exception, e:
        raise Exception("%s (%s)" % (e, url))

    logging.info("Loading domains")
    reader = csv.reader(StringIO.StringIO(result.content))
    headerline = reader.next()
    domains = {}
    Domain = namedtuple("Domain", headerline)
    for line in reader:
        if not line[0]:
            break
        domain = Domain(*line)
        data = dict(domain._asdict())
        domains[domain.code] = data
        logging.info("  %(code)s - %(name)s", data)

    try:
        # gid=9 for 3rd worksheet
        url = url_fmt % (remap_doc_id, 9)
        result = fetch(url)
    except Exception, e:
        raise Exception("%s (%s)" % (e, url))

    logging.info("Loading common core map")
    reader = csv.reader(StringIO.StringIO(result.content))
    headerline = reader.next()
    Row = namedtuple("Row", headerline)

    cc_standards = {}

    for line in reader:
        row = Row(*line)
        if not row.standard:
            break

        try:
            cc = cc_standards[row.standard]
        except KeyError:
            cc = {}
            cc["standard"] = row.standard
            cc["grade"], cc["domain_code"], cc["level"] = row.standard.split(".",2)
            cc["domain"] = domains[cc["domain_code"]]['name'].decode("utf8")
            cc["cc_cluster"] = row.cluster.decode("utf8")
            cc["cc_description"] = row.description.decode("utf8")
            cc["videos"] = set()
            cc["exercises"] = set()
            
            cc_standards[row.standard] = cc

        if row.exercise_name:
            cc['exercises'].add(row.exercise_name)

        if row.youtube_id:
            cc['videos'].add(row.youtube_id)

    while reset:
        maps = CommonCoreMap.all(keys_only=True).fetch(limit=500)
        if not maps:
            break
        logging.info("Clearing %s Common Core Maps", len(maps))
        db.delete(maps)

    cc_list = []
    for standard, data in cc_standards.iteritems():
        videos, exercises = data.pop("videos"), data.pop("exercises")
        cc = CommonCoreMap.all().filter("standard = ", standard).get()
        if not cc:
            cc = CommonCoreMap(**data)
        map(cc.update_exercise, exercises)
        map(cc.update_video, videos)
        cc_list.append(cc)

    logging.info("Updating %s Common Core Maps", len(cc_list))
    db.put(cc_list)

    logging.info("Busting caches")
    CommonCoreMap.get_all_structured(lightweight=True, bust_cache=True)
    CommonCoreMap.get_all_structured(lightweight=False, bust_cache=True)
    logging.info("Done with CommonCore.")

class ManageCommonCore(request_handler.RequestHandler):

    @user_util.developer_only
    @ensure_xsrf_cookie
    def get(self):
        template_values = {
            "selected_id": "commoncore",
        } 

        self.render_jinja2_template("devpanel/uploadcommoncorefile.html", template_values)

    @user_util.developer_only
    @ensure_xsrf_cookie
    def post(self):

        logging.info("Accessing %s" % self.request.path)

        remap_doc_id = self.request_string("remap_doc_id")
        reset = self.request_bool("reset")
        deferred.defer(update_common_core_map, remap_doc_id, reset)

        self.redirect("/devadmin")
        return
