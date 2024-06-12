import secrets
from typing import Annotated, Optional

import polars as pl
from fastapi import Depends, HTTPException, security
from fastapi.security import HTTPBasicCredentials
from starlette import status

from quizzical.load_usernames_passwords import load_usernames_passwords


async def check_login_details(credentials: Annotated[HTTPBasicCredentials, Depends(security)], debug:Optional[bool] = True):  #
    username_str = credentials.username
    password_str = credentials.password
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
