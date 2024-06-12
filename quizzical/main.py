import io
import json
import os
from typing import List, Optional, Annotated
import dotenv
import polars as pl
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette import status

from quizzical.QuestionModel import QuestionModel
from quizzical.check_login_credentials import check_login_details
from tests.async_tests import test_authentication, test_can_load_subjects

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


@app.get('/test', tags=['Authentication'])
async def test():
    """Test the API is working by checking the log in of the first user in the database and a simple request to list subjects. Returns True if working, else raises an HttpException with more detail"""
    await test_authentication()
    await test_can_load_subjects()
    return True
