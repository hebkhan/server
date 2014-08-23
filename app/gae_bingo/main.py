from __future__ import absolute_import
import webapp2
from gae_bingo import cache, dashboard, middleware, blotter, api, redirect

application = webapp2.WSGIApplication([
    ("/gae_bingo/persist", cache.PersistToDatastore),
    ("/gae_bingo/log_snapshot", cache.LogSnapshotToDatastore),
    ("/gae_bingo/blotter/ab_test", blotter.AB_Test),
    ("/gae_bingo/blotter/bingo", blotter.Bingo),

    ("/gae_bingo/redirect", redirect.Redirect),

    ("/gae_bingo/dashboard", dashboard.Dashboard),
    ("/gae_bingo/dashboard/export", dashboard.Export),
    ("/gae_bingo/api/v1/experiments", api.Experiments),
    ("/gae_bingo/api/v1/experiments/summary", api.ExperimentSummary),
    ("/gae_bingo/api/v1/experiments/conversions", api.ExperimentConversions),
    ("/gae_bingo/api/v1/experiments/control", api.ControlExperiment),
    ("/gae_bingo/api/v1/alternatives", api.Alternatives),
])

application = middleware.GAEBingoWSGIMiddleware(application)
