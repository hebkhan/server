import webapp2

from gandalf import dashboard, api, middleware

application = webapp2.WSGIApplication([
    ("/gandalf", dashboard.Dashboard),
    ("/gandalf/api/v1/bridges", api.Bridges),
    ("/gandalf/api/v1/bridges/filters", api.Filters),
    ("/gandalf/api/v1/bridges/update", api.UpdateBridge),
    ("/gandalf/api/v1/bridges/filters/update", api.UpdateFilter),
])

application = middleware.GandalfWSGIMiddleware(application)
