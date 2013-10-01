import webapp2

from gandalf.tests import RunStep
from gandalf import middleware

application = webapp2.WSGIApplication([
    ("/gandalf/tests/run_step", RunStep),
])

application = middleware.GandalfWSGIMiddleware(application)
