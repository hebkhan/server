from request_handler import RequestHandler
import os

class RobotsTxt(RequestHandler):
    """Dynamic robots.txt that hides staging apps from search engines"""
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.write("User-agent: *\n")

        visible_domains = [
            'www.hebrewkhan.org',
        ]

        if os.environ['SERVER_NAME'] in visible_domains:
            self.response.write("Disallow: /_ah/\n")
            self.response.write("Disallow: /admin/\n")
            self.response.write("Disallow: /devadmin/\n")
            self.response.write("Disallow: /video/\n")
            self.response.write("Disallow: /discussion/\n")
        else:
            self.response.write("Disallow: *")
