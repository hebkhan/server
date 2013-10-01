import os
import jinja2
import webapp2


class RedirectGTV(webapp2.RequestHandler):
    def get(self):
        self.redirect("/gtv/")


class ViewGTV(webapp2.RequestHandler):
    @webapp2.cached_property
    def jinja2(self):
        return jinja2.get_jinja2(app=self.app)

    def render_template(self, filename, **template_args):
        self.response.write(self.jinja2.render_template(filename, **template_args))

    def get(self):
        self.render_template('index.html')


application = webapp2.WSGIApplication([
    ('/gtv/', ViewGTV),
    ('/gtv', RedirectGTV),
])