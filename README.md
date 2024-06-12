Quizzical
=========
A simple API built with FastAPI for returning multiple choice questions given a set of questions provided in Excel format

# Setup
1. Clone this repo `git clone {repo_url}`
2. Set up a virtual environment and install the requirements from `requirements.txt` (using venv and pip)
3. Define the questions in an Excel format. Save to `data/questions_en.xlsx`, using the template `questions_en.xlsx`. Note you can change the location in the config file `config.env` using the environment variable `DATA_LOCATION`
4. Define the users and roles in `data/users.csv`, using the template `users.csv.template` (note there is an example user `alice` with the right to read questions, but not to add new questions)

# How to use
1. Launch by running `fastapi dev quizzical/main.py` (for development mode, where changes to code are applied immediately) or `fastapi run quizzical` for production
2. Login
- Via curl: `curl localhost:8000/login --header "Authorization: Basic {Base64 encoding of "username:password" (as one string)}`
- Via web browser: Go to `localhost:8000/docs` and enter a username and password from the users database
3. Go to `localhost:8000/docs` to see the available endpoints and try them out!

# Architecture choices
1. Keep it simple => This is a minimal working solution. We opt for flat files and relatively simple libraries
2. Plan for scale and performance => Use pola.rs for loading data in memory. By using lazy evaluation we can deal with large numbers of users/questions in the future (after moving data to a proper database)
3. Validate data formats. We use [patito](https://github.com/JakobGM/patito) as a data modelling layer ontop of pydantic and pola.rs in order to ensure validity of data
4. Don't hard code user data or question data => All data that might need to change is stored in the data folder
4. Customization => The location of the data folder can be changed using config.env or an environment variable
5. No special users => Read and write permissions defined per user in users.csv