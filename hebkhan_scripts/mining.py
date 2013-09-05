
import os, sys
import optparse


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "google_appengine"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from secrets_dev import app_engine_username, app_engine_password

def init_remote_api(app_id):
    from remote_api_shell import fix_sys_path
    fix_sys_path()
    from google.appengine.ext.remote_api import remote_api_stub

    login = lambda: (app_engine_username, app_engine_password)

    remote_api_stub.ConfigureRemoteApi(None, '/_ah/remote_api', login, '%s.appspot.com' % app_id)

import gspread

os.environ["SERVER_SOFTWARE"] = "Miner"
import models

def batch_iter(query, batch_size=1000):
    query = query.order("__key__")
    entities = query.fetch(batch_size)
    i = 0
    while entities:
        print "Batch", i*batch_size + len(entities), ":"
        for entity in entities:
            yield entity
        entities = query.filter('__key__ >', entities[-1].key()).fetch(batch_size)


def update_spreadsheet():

    def get_video_mapping():
        videos = models.Video.all()
        keys = "youtube_id", "youtube_id_en", "readable_id"
        yield "hebrew", "english", "name"
        for video in batch_iter(videos):
            if (video.youtube_id_en and video.youtube_id != video.youtube_id_en):
                yield tuple(getattr(video, k) for k in keys)

    print "getting data..."
    mapping = list(get_video_mapping())

    client = gspread.login(app_engine_username, app_engine_password)
    wr = client.open_by_key("0Ap8djBdeiIG7dHdKekgwYy1zSDFWRzRSZl9TTDVpNXc").worksheet("mapping")
    rows, cols = len(mapping), len(mapping[0])
    print "resizing to %sx%s" % (rows, cols)
    wr.resize(rows, cols)

    cells = wr.range("A1:%s" % wr.get_addr_int(rows, cols))
    for cell in cells:
        cell.value = mapping[cell.row-1][cell.col-1]

    print "updating spreadsheet"
    wr.update_cells(cells)

def main():
    parser = optparse.OptionParser()
    parser.add_option('-a', '--app_id',
        action="store", dest="app_id",
        default="hebkhan-dev")

    options, args = parser.parse_args()
    init_remote_api(options.app_id)
    update_spreadsheet()

if __name__ == '__main__':
    main()
