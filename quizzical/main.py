import base64
import io
import json
import os
import secrets
from typing import List, Optional, Annotated
import httpx
import dotenv
import polars as pl
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from polars import Boolean, Int8
import patito as pt
from starlette import status

from quizzical.QuestionModel import QuestionModel
from quizzical.UserModel import User

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


async def load_usernames_passwords() -> pl.DataFrame:
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


async def check_login_details(credentials: Annotated[HTTPBasicCredentials, Depends(security)], debug:Optional[bool] = True):  #
    username_str = credentials.username #.encode('utf-8')
    password_str = credentials.password #.encode('utf-8')
    if debug: print('user', username_str, 'password', password_str)

    valid_logins = await load_usernames_passwords()

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
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect username or password')
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect username or password')
    except HTTPException as e:
        raise e


@app.get("/login", tags=['Authentication'])
async def login(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    return await check_login_details(credentials)


@app.get('/uses', tags=['List'])
async def list_uses() -> List[str]:
    """List uses, returns as list of strings"""
    q_df = pl.read_excel(DATA_LOCATION, engine='openpyxl')
    uses_list = q_df.get_column('use').unique().to_list()
    return uses_list


@app.get('/subjects', tags=['List'])
async def list_subjects() -> List[str]:
    """List subjects, returns as list of strings"""
    q_df = pl.read_excel(DATA_LOCATION, engine='openpyxl')
    subject_list = q_df.get_column('subject').unique().to_list()
    return subject_list


@app.get("/ask", name='Get questions to ask', tags=['Create'])
async def ask(credentials: Annotated[HTTPBasicCredentials, Depends(security)], n: int = 5, use: Optional[str] = None, subject: Optional[str] = None):
    """LOGIN REQUIRED. Gets n randomly-ordered questions from the database with the use `use` and subject `subject`
    n can be 5,10, or 20
    """
    await check_login_details(credentials)

    if n not in [5, 10, 20]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Number of questions generated should be 5,10 or 20')
    # Authentication

    q_df = pl.read_excel(DATA_LOCATION, engine='openpyxl')
    ctx = pl.SQLContext(questions=q_df, eager=True)
    results = ctx.execute(f'SELECT * FROM questions')
    if isinstance(use, str):
        results = results.filter((pl.col('use') == use))
    if isinstance(subject, str):
        results = results.filter(pl.col('subject') == subject)
    if isinstance(n, int):
        results = results.limit(n)

    # Sort randomly
    results = results.select(pl.col('*').shuffle())
    str_obj = io.StringIO()
    print(results.write_json(str_obj))

    return json.loads(str_obj.getvalue())


async def test_authentication():
    try:
        user_df = await load_usernames_passwords()
        first_user = user_df[0]
        first_username = first_user.get_column('username').item()
        first_password = first_user.get_column('password').item()
        auth_string = base64.b64encode(bytes(f'{first_username}:{first_password}', 'utf-8'))
        print(first_username,first_password)
        print(auth_string)
        header = {'Authorization': f'Basic {auth_string.decode("utf-8")}'}
        print(header)
        async with httpx.AsyncClient() as client:
            response = await client.get('http://localhost:8000/login', headers=header)
            assert 200 <= response.status_code < 300
    except AssertionError as e:
        raise HTTPException(status_code=500, detail=f'{e}')
    return True


async def test_can_load_subjects():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get('http://localhost:8000/subjects')
            assert 200 <= response.status_code < 300
            print(response.json())
            assert len(response.json()) > 1
    except AssertionError as e:
        raise HTTPException(status_code=500, detail=f'{e}')
    return True


@app.get('/test', tags=['Authentication'])
async def test():
    """Test the API is working by checking the log in of the first user in the database and a simple request to list subjects. Returns True if working, else raises an HttpException with more detail"""
    await test_authentication()
    await test_can_load_subjects()
    return True


@app.put('/add', tags=['Create'])
async def add_question(credentials: Annotated[HTTPBasicCredentials, Depends(security)], question: QuestionModel):
    """LOGIN REQUIRED. Insert a new question to the database. The question must have the columns defined in the QuestionModel"""
    await check_login_details(credentials)
    assert isinstance(question, QuestionModel)
    q_df = pl.read_excel(DATA_LOCATION, engine='openpyxl')
    new_row = pl.DataFrame(question, question.base_field_names)
    print(new_row.to_dict())
    q_df = q_df.extend(new_row)
    q_df.write_excel(DATA_LOCATION, engine='openpyxl')
