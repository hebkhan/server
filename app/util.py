import os
import datetime
import urllib
import request_cache
import logging
import sys
import json
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import db

from asynctools import AsyncMultiTask, QueryTask

from app import App

# Needed for side effects of secondary imports
import nicknames #@UnusedImport
import facebook_util
from phantom_users.phantom_util import get_phantom_user_id_from_cookies, \
    is_phantom_id

from api.auth.google_util import get_google_user_id_and_email_from_oauth_map
from api.auth.auth_util import current_oauth_map, allow_cookie_based_auth

@request_cache.cache()
def get_current_user_id():
    user_id = None

    oauth_map = current_oauth_map()
    if oauth_map:
        user_id = get_current_user_id_from_oauth_map(oauth_map)

    if not user_id and allow_cookie_based_auth():
        user_id = get_current_user_id_from_cookies_unsafe()

    return user_id

def get_current_user_id_from_oauth_map(oauth_map):
    user_id = None

    if oauth_map.uses_google():
        user_id = get_google_user_id_and_email_from_oauth_map(oauth_map)[0]
    elif oauth_map.uses_facebook():
        user_id = facebook_util.get_facebook_user_id_from_oauth_map(oauth_map)

    return user_id

# get_current_user_from_cookies_unsafe is labeled unsafe because it should
# never be used in our JSONP-enabled API. All calling code should just use get_current_user_id.
def get_current_user_id_from_cookies_unsafe():
    user = users.get_current_user()

    if user: # if we have a google account
        user_id = "http://googleid.khanacademy.org/" + user.user_id()
    else: # if not a google account, try facebook
        user_id = facebook_util.get_current_facebook_user_id_from_cookies()

    if not user_id: # if we don't have a user_id, then it's not facebook or google
        user_id = get_phantom_user_id_from_cookies()

    return user_id

def is_phantom_user(user_id):
    return user_id and is_phantom_id(user_id)

def create_login_url(dest_url):
    return "/login?continue=%s" % urllib.quote(dest_url)

def create_mobile_oauth_login_url(dest_url):
    return "/login/mobileoauth?continue=%s" % urllib.quote(dest_url)

def create_post_login_url(dest_url):
    if dest_url.startswith("/postlogin"):
        return dest_url
    else:
        return "/postlogin?continue=%s" % urllib.quote(dest_url)

def create_logout_url(dest_url):
    return "/logout?continue=%s" % urllib.quote(dest_url)

def seconds_since(dt):
    return seconds_between(dt, datetime.datetime.now())

def seconds_between(dt1, dt2):
    timespan = dt2 - dt1
    return float(timespan.seconds + (timespan.days * 24 * 3600))

def minutes_between(dt1, dt2):
    return seconds_between(dt1, dt2) / 60.0

def hours_between(dt1, dt2):
    return seconds_between(dt1, dt2) / (60.0 * 60.0)

def thousands_separated_number(x):
    # See http://stackoverflow.com/questions/1823058/how-to-print-number-with-commas-as-thousands-separators-in-python-2-x
    if x < 0:
        return '-' + thousands_separated_number(-x)
    result = ''
    while x >= 1000:
        x, r = divmod(x, 1000)
        result = ",%03d%s" % (r, result)
    return "%d%s" % (x, result)

def async_queries(queries, limit=100000):

    task_runner = AsyncMultiTask()
    for query in queries:
        task_runner.append(QueryTask(query, limit=limit))
    task_runner.run()

    return task_runner

def config_iterable(plain_config, batch_size=50, limit=1000):

    config = plain_config

    try:
        # This specific use of the QueryOptions private API was suggested to us by the App Engine team.
        # Wrapping in try/except in case it ever goes away.
        from google.appengine.datastore import datastore_query
        config = datastore_query.QueryOptions(
            config=plain_config,
            limit=limit,
            offset=0,
            prefetch_size=batch_size,
            batch_size=batch_size)

    except Exception, e:
        logging.exception("Failed to create QueryOptions config object: %s", e)

    return config

def absolute_url(relative_url):
    return 'http://%s%s' % (os.environ['HTTP_HOST'], relative_url)

def static_url(relative_url):
#    if App.is_dev_server or not os.environ['HTTP_HOST'].lower().endswith(".khanacademy.org"):
#        return relative_url
#    else:
#        return "http://khan-academy.appspot.com%s" % relative_url
    return relative_url

def clone_entity(e, **extra_args):
    """http://stackoverflow.com/questions/2687724/copy-an-entity-in-google-app-engine-datastore-in-python-without-knowing-property
    Clones an entity, adding or overriding constructor attributes.
    
    The cloned entity will have exactly the same property values as the original
    entity, except where overridden. By default it will have no parent entity or
    key name, unless supplied.
    
    Args:
        e: The entity to clone
        extra_args: Keyword arguments to override from the cloned entity and pass
        to the constructor.
    Returns:
        A cloned, possibly modified, copy of entity e.
    """
    klass = e.__class__
    props = dict((k, v.__get__(e, klass)) for k, v in klass.properties().iteritems())
    props.update(extra_args)
    return klass(**props)

def parse_iso8601(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")

def prefetch_refprops(entities, *props):
    """http://blog.notdot.net/2010/01/ReferenceProperty-prefetching-in-App-Engine
    Loads referenced models defined by the given model properties
    all at once on the given entities.

    Example:
    posts = Post.all().order("-timestamp").fetch(20)
    prefetch_refprop(posts, Post.author)
    """
    # Get a list of (entity,property of this entity)
    fields = [(entity, prop) for entity in entities for prop in props]
    # Pull out an equally sized list of the referenced key for each field (possibly None)
    ref_keys_with_none = [prop.get_value_for_datastore(x) for x, prop in fields]
    # Make a dict of keys:fetched entities
    ref_keys = filter(None, ref_keys_with_none)
    ref_entities = dict((x.key(), x) for x in db.get(set(ref_keys)))
    # Set the fetched entity on the non-None reference properties
    for (entity, prop), ref_key in zip(fields, ref_keys_with_none):
        if ref_key is not None:
            prop.__set__(entity, ref_entities[ref_key])
    return entities

def coalesce(fn, s):
    """Call a function only if the argument is not None"""
    if s is not None:
        return fn(s)
    else:
        return None

def count_with_cursors(query, max_value=None):
    """ Counts the number of items that match a given query, using cursors
    so that it can return a number over 1000.

    USE WITH CARE: should not be done in user-serving requests and can be
    very slow.
    """
    count = 0
    while (count % 1000 == 0 and
             (max_value is None or count < max_value)):
        current_count = len(query.fetch(1000))
        if current_count == 0:
            break

        count += current_count
        if current_count == 1000:
            cursor = query.cursor()
            query.with_cursor(cursor)

    return count

def fetch_from_url(url, as_json=False):
    logging.info("Fetching from %s", url)
    try:
        result = urlfetch.fetch(url, deadline=30)
    except Exception, e:
        typ, exc, tb = sys.exc_info()
        raise typ, "%s (%s)" % (e, url), tb
    if as_json:
        return json.loads(result.content)
    return result.content

from operator import itemgetter as _itemgetter
from keyword import iskeyword as _iskeyword
import sys as _sys

def namedtuple(typename, field_names, verbose=False, rename=False):
    """Returns a new subclass of tuple with named fields.

    >>> Point = namedtuple('Point', 'x y')
    >>> Point.__doc__                   # docstring for the new class
    'Point(x, y)'
    >>> p = Point(11, y=22)             # instantiate with positional args or keywords
    >>> p[0] + p[1]                     # indexable like a plain tuple
    33
    >>> x, y = p                        # unpack like a regular tuple
    >>> x, y
    (11, 22)
    >>> p.x + p.y                       # fields also accessable by name
    33
    >>> d = p._asdict()                 # convert to a dictionary
    >>> d['x']
    11
    >>> Point(**d)                      # convert from a dictionary
    Point(x=11, y=22)
    >>> p._replace(x=100)               # _replace() is like str.replace() but targets named fields
    Point(x=100, y=22)

    """

    # Parse and validate the field names.  Validation serves two purposes,
    # generating informative error messages and preventing template injection attacks.
    if isinstance(field_names, basestring):
        field_names = field_names.replace(',', ' ').split() # names separated by whitespace and/or commas
    field_names = tuple(map(str, field_names))
    if rename:
        names = list(field_names)
        seen = set()
        for i, name in enumerate(names):
            if (not min(c.isalnum() or c=='_' for c in name) or _iskeyword(name)
                or not name or name[0].isdigit() or name.startswith('_')
                or name in seen):
                    names[i] = '_%d' % i
            seen.add(name)
        field_names = tuple(names)
    for name in (typename,) + field_names:
        if not min(c.isalnum() or c=='_' for c in name):
            raise ValueError('Type names and field names can only contain alphanumeric characters and underscores: %r' % name)
        if _iskeyword(name):
            raise ValueError('Type names and field names cannot be a keyword: %r' % name)
        if name[0].isdigit():
            raise ValueError('Type names and field names cannot start with a number: %r' % name)
    seen_names = set()
    for name in field_names:
        if name.startswith('_') and not rename:
            raise ValueError('Field names cannot start with an underscore: %r' % name)
        if name in seen_names:
            raise ValueError('Encountered duplicate field name: %r' % name)
        seen_names.add(name)

    # Create and fill-in the class template
    numfields = len(field_names)
    argtxt = repr(field_names).replace("'", "")[1:-1]   # tuple repr without parens or quotes
    reprtxt = ', '.join('%s=%%r' % name for name in field_names)
    template = '''class %(typename)s(tuple):
        '%(typename)s(%(argtxt)s)' \n
        __slots__ = () \n
        _fields = %(field_names)r \n
        def __new__(_cls, %(argtxt)s):
            return _tuple.__new__(_cls, (%(argtxt)s)) \n
        @classmethod
        def _make(cls, iterable, new=tuple.__new__, len=len):
            'Make a new %(typename)s object from a sequence or iterable'
            result = new(cls, iterable)
            if len(result) != %(numfields)d:
                raise TypeError('Expected %(numfields)d arguments, got %%d' %% len(result))
            return result \n
        def __repr__(self):
            return '%(typename)s(%(reprtxt)s)' %% self \n
        def _asdict(self):
            'Return a new dict which maps field names to their values'
            return dict(zip(self._fields, self)) \n
        def _replace(_self, **kwds):
            'Return a new %(typename)s object replacing specified fields with new values'
            result = _self._make(map(kwds.pop, %(field_names)r, _self))
            if kwds:
                raise ValueError('Got unexpected field names: %%r' %% kwds.keys())
            return result \n
        def __getnewargs__(self):
            return tuple(self) \n\n''' % locals()
    for i, name in enumerate(field_names):
        template += '        %s = _property(_itemgetter(%d))\n' % (name, i)
    if verbose:
        print template

    # Execute the template string in a temporary namespace
    namespace = dict(_itemgetter=_itemgetter, __name__='namedtuple_%s' % typename,
                     _property=property, _tuple=tuple)
    try:
        exec template in namespace
    except SyntaxError, e:
        raise SyntaxError(e.message + ':\n' + template)
    result = namespace[typename]

    # For pickling to work, the __module__ variable needs to be set to the frame
    # where the named tuple is created.  Bypass this step in enviroments where
    # sys._getframe is not defined (Jython for example) or sys._getframe is not
    # defined for arguments greater than 0 (IronPython).
    try:
        result.__module__ = _sys._getframe(1).f_globals.get('__name__', '__main__')
    except (AttributeError, ValueError):
        pass

    return result