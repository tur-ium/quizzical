import base64

import httpx
from fastapi import HTTPException

from quizzical.load_usernames_passwords import load_usernames_passwords


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
