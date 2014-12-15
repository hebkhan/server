from collections import defaultdict
from sqlalchemy import Table, Column, Integer, String, DateTime, Boolean, MetaData
from sqlalchemy.dialects.postgresql import ARRAY
from google.appengine.ext import db
import models as appengine_models

metadata = MetaData()

def nested_getattr(obj, path):
    for part in path.split('.'):
        obj = getattr(obj, part)
    return obj

type_map = {db.IntegerProperty: Integer,
            db.StringProperty: String,
            db.DateTimeProperty: DateTime,
            db.BooleanProperty: Boolean}
def appengine_field_to_sqlalchemy_field(field):
    if field.__class__ in type_map:
        return type_map[field.__class__], None
    elif field.__class__ == db.UserProperty:
        return String, lambda user: user.email()
    elif field.__class__ == db.ListProperty:
        return ARRAY(String), lambda l: [i.name() for i in l]
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
        fields = []
        
        for dest, source in field_map.items():
            if dest.startswith('__'):
                continue
            source = source or dest
            alchemy_type, convert = appengine_field_to_sqlalchemy_field(getattr(model, source))
            fields.append(Field(source=source, dest=dest, convert=convert))
            columns.append(Column(dest, alchemy_type))
        table = Table(model.__name__.lower(), metadata, *columns)
        t = super(ModelMeta, cls).__new__(cls, name, bases, {'fields': fields,
                                                             'table': table,
                                                             'model': model})
        appengine_model_to_bi_model[model] = t
        return t

class Model(object):
    __metaclass__ = ModelMeta

    @classmethod
    def from_appengine(cls, obj):
        model = appengine_model_to_bi_model[obj.__class__]
        result = model()
        for field in model.fields:
            setattr(result, field.dest, field.convert(nested_getattr(obj, field.source)))
        return result

class UserData(Model):
    user_id = None
    user_nickname = None
    user_email = None
    username = None
    points = None

class Exercise(Model):
    name = None
    display_name = None
    short_display_name = None

class ProblemLog(Model):
    user = None
    problem_number = None
    exercise = None
    correct = None
    points_earned = None
    time_taken = None
    time_done = None

class StudentList(Model):
    name = None
    coaches = None