import csv
import io
import json
import os
import secrets
from collections import OrderedDict
from typing import List, Optional, Annotated, Literal

import dotenv
import patito
import polars as pl
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from polars import Boolean, String, Binary, Int8
from pydantic import BaseModel
from starlette import status

from quizzical.QuestionModel import QuestionModel

dotenv.load_dotenv('config.env')

DATA_LOCATION = os.getenv('DATA_LOCATION')

app = FastAPI(title="Quizzical",
              description="An API for multiple choice questions",
              version="0.0.1",
              openapi_tags=[
                  {'name': 'List',
                   'description': 'Endpoints for listing data within database'},
                  {'name': 'Authentication',
                   'description': 'Endpoints for authentication, user management, etc'},
                  {'name': 'Create',
                   'description': 'Endpoints for creating multiple choice questions'}
              ])
security = HTTPBasic()


class UserModel(BaseModel):
    username: str
    password: str
    read: bool
    write: bool


import patito as pt


class User(pt.Model):
    username: str = pt.Field(unique=True)
    password: str
    read: bool  # Permission to read all questions
    write: bool  # Permission to write new questions


userDFSchema = OrderedDict({'username': String, 'password': String, 'read': Boolean, 'write': Boolean})


def load_usernames_passwords() -> pl.DataFrame:
    users = pl.read_csv('data/users.csv', has_header=True, schema_overrides={'read': Int8, 'write': Int8})
    users = users.cast(dtypes={'read': Boolean, 'write': Boolean})
    print(users)
    try:
        assert users.get_column('username').is_unique().all()
    except AssertionError:
        raise HTTPException(status_code=500,
                            detail='Users are not unique in the login database. See the log for exception')

    try:
        User.validate(users)
    except pt.exceptions.DataFrameValidationError as exc:
        print(exc)
        raise HTTPException(status_code=500, detail='Issue in the login database. See the log for exception')
    return users


def check_login_details(credentials: Annotated[HTTPBasicCredentials, Depends(security)], debug:Optional[bool] = True):  #
    username_str = credentials.username #.encode('utf-8')
    password_str = credentials.password #.encode('utf-8')
    if debug: print('user', username_str, 'password', password_str)

    valid_logins = load_usernames_passwords()

    try:
        if valid_logins.filter((pl.col('username') == username_str)).is_empty():
            if debug: print('Username is wrong')
            raise ValueError
        expected_password: str = valid_logins.filter((pl.col('username') == username_str)).get_column('password').item()
        password_correct = secrets.compare_digest(password_str, expected_password)
        if password_correct:
            if debug: print('Logged in successfully')
            return True
        else:
            if debug: print('Password incorrect')
            return False
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect username or password')
    except HTTPException as e:
        raise e


@app.get("/login")
def user(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    return check_login_details(credentials)


@app.get('/uses', tags=['List'])
def list_uses() -> List[str]:
    """List uses, returns as list of strings"""
    q_df = pl.read_excel(DATA_LOCATION, engine='openpyxl')
    uses_list = q_df.get_column('use').unique().to_list()
    return uses_list


@app.get('/subjects', tags=['List'])
def list_subjects() -> List[str]:
    """List subjects, returns as list of strings"""
    q_df = pl.read_excel(DATA_LOCATION, engine='openpyxl')
    subject_list = q_df.get_column('subject').unique().to_list()
    return subject_list


@app.get("/create", tags=['Create'])
def create(n: int = 5, use: Optional[str] = None, subject: Optional[str] = None):
    """Gets n randomly-ordered questions from the database with the use `use` and subject `subject`
    n can be 5,10, or 20
    """
    if n not in [5, 10, 20]:
        raise HTTPException('Number of questions generated should be 5,10 or 20')
    # Authentication

    q_df = pl.read_excel(DATA_LOCATION, engine='openpyxl')
    ctx = pl.SQLContext(questions=q_df, eager=True)
    results = ctx.execute(f'SELECT * FROM questions')
    if isinstance(n, int):
        results = results.limit(n)
    if isinstance(use, str):
        results = results.filter((pl.col('use') == use))
    if isinstance(subject, str):
        results = results.filter(pl.col('subject') == subject)
    # Sort randomly
    str_obj = io.StringIO()
    print(results.write_json(str_obj))

    return json.loads(str_obj.getvalue())


@app.get('/test', tags=['Authentication'])
def test():
    return


@app.put('/add', tags=['Create'])
def add_question(question: QuestionModel):
    """Insert a new question to the database. The question must have the columns defined in the QuestionModel"""
    assert isinstance(question, QuestionModel)
    q_df = pl.read_excel(DATA_LOCATION, engine='openpyxl')
    new_row = pl.DataFrame(question, question.base_field_names)
    print(new_row.to_dict())
    q_df = q_df.extend(new_row)
    q_df.write_excel(DATA_LOCATION, engine='openpyxl')
