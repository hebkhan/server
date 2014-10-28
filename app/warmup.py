import logging

import request_handler
import library
from badges import util_badges
from app import App

class Warmup(request_handler.RequestHandler):

    def get(self):
        if App.is_dev_server:
            logging.info("Warmup: deleting caches")
            from google.appengine.ext import blobstore
            from google.appengine.ext import db
            for k in blobstore.BlobInfo.all():
                logging.info(" -- %s", k.key())
                k.delete()

        logging.info("Warmup: loading homepage html")
        library.library_content_html(mobile=False)
        library.library_content_html(mobile=True)

        logging.info("Warmup: loading badges")
        util_badges.all_badges()
        util_badges.all_badges_dict()

