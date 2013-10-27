import webapp2

from gae_bingo.tests import RunStep
from gae_bingo import middleware

application = webapp2.WSGIApplication([
    ("/gae_bingo/tests/run_step", RunStep),
])

application = middleware.GAEBingoWSGIMiddleware(application)

