from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.responses import RedirectResponse
import requests

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# マネージドIDを使用してアクセストークンを取得する関数
def get_access_token():
    metadata_url = "http://169.254.169.254/metadata/identity/oauth2/token"
    params = {
        "api-version": "2018-02-01",
        "resource": "https://graph.microsoft.com",
    }
    headers = {"Metadata": "true"}

    response = requests.get(metadata_url, params=params, headers=headers)
    response.raise_for_status()
    return response.json()["access_token"]

# Graph APIを呼び出す関数
def call_graph_api(endpoint):
    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    response = requests.get(f"https://graph.microsoft.com/v1.0/{endpoint}", headers=headers)
    response.raise_for_status()
    return response.json()

users = {
    "user1": "password1",
    "user2": "password2"
}

security = HTTPBasic()

def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    username = credentials.username
    password = credentials.password
    if username in users and users[username] == password:
        return username
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Basic"},
    )

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username in users and users[username] == password:
        response = RedirectResponse(url="/home", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="username", value=username)
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})

@app.get("/home")
async def home(request: Request, username: str = Depends(authenticate_user)):
    # Graph APIを呼び出す例
    user_info = call_graph_api("me")
    return templates.TemplateResponse("home.html", {"request": request, "username": username, "user_info": user_info})