
import os, sys
import optparse


gae_path = "../../google_appengine/"

extra_paths = [
    gae_path,
    os.path.join("..", "offline"),
    os.path.join("..", "app"),
    os.path.join(gae_path, 'lib', 'webapp2-2.5.2'),
    os.path.join(gae_path, 'lib', 'jinja2-2.6'),
    os.path.join(gae_path, 'lib', 'antlr3'),
    os.path.join(gae_path, 'lib', 'ipaddr'),
    os.path.join(gae_path, 'lib', 'webob'),
    os.path.join(gae_path, 'lib', 'json'),
    os.path.join(gae_path, 'lib', 'yaml', 'lib'),
]

#sys.path[:1] = extra_paths

from secrets_dev import app_engine_username, app_engine_password

def init_remote_api(app_id):
    from remote_api_shell import fix_sys_path
    fix_sys_path()
    from google.appengine.ext.remote_api import remote_api_stub

    login = lambda: (app_engine_username, app_engine_password)

    remote_api_stub.ConfigureRemoteApi(None, '/_ah/remote_api', login, '%s.appspot.com' % app_id)

#import gspread

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
        last_key = entity.key() if hasattr(entity, "key") else entity
        entities = query.filter('__key__ >', last_key).fetch(batch_size)

def update_spreadsheet(key, worksheet, data, chunk_size=200):
    gsclient = gspread.login(app_engine_username, app_engine_password)
    wr = gsclient.open_by_key(key).worksheet(worksheet)
    print "updating %s:" % (wr.title)

    row_generator = iter(data)
    def get_chunk():
        for i, line in enumerate(row_generator):
            yield line
            if i>=chunk_size:
                break

    total_rows = 0
    current_row = 1
    while True:
        rows = list(get_chunk())
        if not rows:
            break
        ncols = len(rows[0])
        total_rows += len(rows)
        wr.resize(total_rows, ncols)
        addr = "%s:%s" % (wr.get_addr_int(current_row, 1),
                          wr.get_addr_int(total_rows, ncols))
        cells = wr.range(addr)
        for cell in cells:
            cell.value = rows[cell.row-current_row][cell.col-1]

        print "updating %s cells (%s)..." % (len(cells), addr)
        wr.update_cells(cells)
        current_row += len(rows)

def update_video_mapping():
    def get_video_mapping():
        videos = models.Video.all()
        keys = "youtube_id", "youtube_id_en", "readable_id"
        yield "hebrew", "english", "name"
        for video in batch_iter(videos):
            if (video.youtube_id_en and video.youtube_id != video.youtube_id_en):
                yield tuple(getattr(video, k) for k in keys)

    print "getting data..."
    update_spreadsheet(key="0Ap8djBdeiIG7dHdKekgwYy1zSDFWRzRSZl9TTDVpNXc", worksheet="mapping", data=mapping)

def update_user_data():
    import md5
    keys = [
        ('user_id', lambda x: md5.new(x).hexdigest().upper()[:8]),
        ('total_seconds_watched', str),
        ('last_activity', str),
        ('badges', len),
        ('all_proficient_exercises', len),
        ('is_profile_public', str),
        ('videos_completed', str),
        ('last_login', str),
        ('username', str),
        ('coaches', len),
        ('has_current_goals', str),
        ('proficient_exercises', len),
        ('joined', str),
        ('points', str),
    ]

    def get_data():
        users = batch_iter(models.UserData.all())
        yield [k for k,_ in keys]
        for u in users:
            yield [fn(getattr(u,k)) for k,fn in keys]

    print "getting data..."
    update_spreadsheet("0Ap8djBdeiIG7dERSdVAtUmdvdl9JNTYzMUF6YnM3YWc", "users", get_data())

import md5
def hashify(x):
    return "U_" + md5.new(x).hexdigest().upper()[:8]

def update_video_data():
    keys = [
        ("user", lambda user: hashify(user.email())),
        ("youtube_id", str),
        ("time_watched", str),
        ("seconds_watched", str),
        ("last_second_watched", str),
        ("points_earned", str),
        ("is_video_completed", str),
        ("video_title", unicode),
    ]

    def get_data():
        logs = batch_iter(models.VideoLog.all(), 500)
        yield [k for k,_ in keys]
        for u in logs:
            yield [fn(getattr(u,k)) for k,fn in keys]

    print "getting data..."
    update_spreadsheet("0Ap8djBdeiIG7dERSdVAtUmdvdl9JNTYzMUF6YnM3YWc", "videos", get_data())
                              

def main():
    parser = optparse.OptionParser()
    parser.add_option('-a', '--app_id',
        action="store", dest="app_id",
        default="hebkhan-dev")

    options, args = parser.parse_args()
    init_remote_api(options.app_id)
    update_video_data()

if __name__ == '__main__':
    main()
