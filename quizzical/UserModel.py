from collections import OrderedDict

import patito as pt
from polars import String, Boolean


class User(pt.Model):
    username: str = pt.Field(unique=True)
    password: str
    read: bool  # Permission to read all questions
    write: bool  # Permission to write new questions


userDFSchema = OrderedDict({'username': String, 'password': String, 'read': Boolean, 'write': Boolean})
