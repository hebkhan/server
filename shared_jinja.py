import logging

import webapp2
from webapp2_extras import jinja2

import request_cache
from app import App

SHARED_APP = None
@request_cache.cache()
def get():
    # Make sure configuration is imported before we ever initialize, which should only happen once per request
    import config_jinja

    global SHARED_APP
    if SHARED_APP is None:
        SHARED_APP = webapp2.WSGIApplication(debug=App.is_dev_server)


    from pprint import pformat
    import os
    logging.info("ENVIRON:\n%s\n\n", pformat(dict(os.environ)))
    logging.info("APP:\n%s\n\n", pformat(dict(vars(App))))
    logging.info("JINJA2:\n%s\n\n", pformat(config_jinja.jinja2.default_config))

    return jinja2.get_jinja2(app=SHARED_APP)
