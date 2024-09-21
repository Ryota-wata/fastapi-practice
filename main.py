import os
import json
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Jinja2テンプレート設定
templates = Jinja2Templates(directory="templates")

# Microsoft Graph APIのエンドポイント
GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0/me"

# EasyAuthで認証されたユーザー情報を取得
def get_authenticated_user(request: Request):
    user_info_encoded = request.headers.get("X-MS-CLIENT-PRINCIPAL")
    if not user_info_encoded:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Base64でエンコードされたユーザー情報をデコード
    user_info_decoded = user_info_encoded.encode('ascii')
    user_info = json.loads(user_info_decoded)
    
    return user_info

# マネージドIDを使用してMicrosoft Graph用のアクセストークンを取得
def get_access_token():
    token_endpoint = "http://169.254.169.254/metadata/identity/oauth2/token"
    resource = "https://graph.microsoft.com"
    headers = {"Metadata": "true"}
    params = {
        "api-version": "2019-08-01",
        "resource": resource
    }
    
    response = requests.get(token_endpoint, headers=headers, params=params)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to acquire token")
    
    return response.json()["access_token"]

# Microsoft Graph APIからユーザー情報を取得
def get_user_info_from_graph_api():
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(GRAPH_API_ENDPOINT, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to get user info from Microsoft Graph API")
    
    return response.json()

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    # 認証されたユーザー情報
    user_info = get_authenticated_user(request)
    
    # Microsoft Graphから追加のユーザー情報を取得
    graph_user_info = get_user_info_from_graph_api()

    return templates.TemplateResponse("index.html", {
        "request": request, 
        "user_info": user_info, 
        "graph_user_info": graph_user_info
    })
