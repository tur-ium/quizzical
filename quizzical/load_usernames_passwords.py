import patito as pt
import polars as pl
from fastapi import HTTPException
from polars import Int8, Boolean

from quizzical.UserModel import User


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
