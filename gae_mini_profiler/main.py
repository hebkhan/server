import webapp2
from google.appengine.ext.webapp import template

from gae_mini_profiler import profiler

application = webapp2.WSGIApplication([
    ("/gae_mini_profiler/request", profiler.RequestStatsHandler),
    ("/gae_mini_profiler/shared", profiler.SharedStatsHandler),
])

template.register_template_library('gae_mini_profiler.templatetags')