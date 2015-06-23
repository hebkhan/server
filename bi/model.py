from sqlalchemy import Table, Column, BigInteger, String, DateTime, Boolean, MetaData, Float
from sqlalchemy.dialects.postgresql import ARRAY
from google.appengine.ext import db
import models as appengine_models

metadata = MetaData()

def nested_getattr(obj, path):
    for part in path.split('.'):
        obj = getattr(obj, part)
    return obj

type_map = {db.IntegerProperty: BigInteger,
            db.StringProperty: String,
            db.StringListProperty: ARRAY(String),
            db.TextProperty: String,
            db.FloatProperty: Float,
            db.DateTimeProperty: DateTime,
            db.BooleanProperty: Boolean}
def appengine_field_to_sqlalchemy_field(field):
    if field.__class__ in type_map:
        return type_map[field.__class__], None
    elif field.__class__ == db.UserProperty:
        return String, lambda user: user.email()
    elif field.__class__ == db.ListProperty:
        return ARRAY(String), lambda l: [(i.name() or i.id()) for i in l]
    elif field.__class__ == db.ReferenceProperty:
        return BigInteger, lambda value: value.key().id()
    else:
        assert False, "invalid field: {}".format(field)

class Field(object):
    def __init__(self, source, dest, convert):
        self.source = source
        self.dest = dest
        self.convert = convert or (lambda x: x)

appengine_model_to_bi_model = {}

class ModelMeta(type):
    def __new__(cls, name, bases, field_map):
        if name == 'Model':
            return super(ModelMeta, cls).__new__(cls, name, bases, field_map)
        model = getattr(appengine_models, name)
        columns = []
        if field_map.get('id_type'):
            columns.append(Column('id', field_map.get('id_type'), primary_key=True))
        
        fields = []
        
        for dest, source in field_map.items():
            if dest.startswith('__') or dest == 'id_type':
                continue
            source = source or dest
            alchemy_type, convert = appengine_field_to_sqlalchemy_field(getattr(model, source))
            fields.append(Field(source=source, dest=dest, convert=convert))
            columns.append(Column(dest, alchemy_type))
        table = Table(model.__name__.lower(), metadata, *columns)
        t = super(ModelMeta, cls).__new__(cls, name, bases, {'fields': fields,
                                                             'id_type': field_map.get('id_type'),
                                                             'table': table,
                                                             'model': model})
        appengine_model_to_bi_model[model] = t
        return t

def key_to_string(key):
    suffix = key.id_or_name()
    parent = key.parent()
    if parent is None:
        return suffix
    else:
        return key_to_string(parent) + '%' + suffix

class Model(object):
    __metaclass__ = ModelMeta

    @classmethod
    def from_appengine(cls, obj):
        model = appengine_model_to_bi_model[obj.__class__]
        result = model()
        for field in model.fields:
            setattr(result, field.dest, field.convert(nested_getattr(obj, field.source)))
        if model.id_type:
            result.id = key_to_string(obj.key())
        return result

class UserData(Model):
    id_type = String

    user_id = None
    user_nickname = None
    user_email = None
    username = None
    points = None
    joined = None
    student_lists = None
    coaches = None

class Exercise(Model):
    id_type = BigInteger

    name = None
    display_name = None
    short_display_name = None
    creation_date = None

class ProblemLog(Model):
    user = None
    problem_number = None
    exercise = None
    correct = None
    points_earned = None
    time_taken = None
    time_done = None

class UserExercise(Model):
    id_type = String

    user = None
    exercise = None
    last_done = None
    total_done = None
    total_correct = None
    _progress = None

class UserVideo(Model):
    id_type = String

    user = None
    video = None
    completed = None
    last_watched = None
    seconds_watched = None
    duration = None

class Video(Model):
    id_type = BigInteger

    date_added = None
    title = None
    url = None
    readable_id = None
    youtube_id = None
    description = None
    duration = None

class StudentList(Model):
    id_type = BigInteger

    name = None
    coaches = None