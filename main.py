import os
import json
import requests
import base64
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import traceback

app = FastAPI()

# Jinja2テンプレート設定
templates = Jinja2Templates(directory="templates")

# Microsoft Graph APIのエンドポイント
GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0/me"

# EasyAuthで認証されたユーザー情報を取得
def get_authenticated_user(request: Request):
    user_info_encoded = request.headers.get("X-MS-CLIENT-PRINCIPAL")
    if not user_info_encoded:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing X-MS-CLIENT-PRINCIPAL header")
    
    # Base64でエンコードされたユーザー情報をデコード
    try:
        user_info_decoded = json.loads(base64.b64decode(user_info_encoded).decode('utf-8'))
    except Exception as e:
        raise HTTPException(status_code=400, detail="Failed to decode user info: " + str(e))
    
    return user_info_decoded

# マネージドIDまたは対話型ブラウザ認証を使用してMicrosoft Graph用のアクセストークンを取得
def get_access_token():
    try:
        # まずマネージドIDでトークンを取得しようとする
        credential = DefaultAzureCredential()
        scope = "https://graph.microsoft.com/.default"
        access_token = credential.get_token(scope).token
        return access_token
    except Exception as e:
        print(f"Failed to get token using Managed Identity: {str(e)}")
        print("Falling back to interactive browser authentication")
        
        # マネージド ID が使用できない場合は対話型ブラウザ認証を使用
        credential = InteractiveBrowserCredential()
        scope = "https://graph.microsoft.com/user.read"
        access_token = credential.get_token(scope).token
        return access_token

# Microsoft Graph APIからユーザー情報を取得
def get_user_info_from_graph_api():
    access_token = get_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(GRAPH_API_ENDPOINT, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to get user info from Microsoft Graph API: " + response.text)
    
    return response.json()

@app.middleware("http")
async def log_request(request: Request, call_next):
    print(f"Request headers: {request.headers}")
    response = await call_next(request)
    return response

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    try:
        # 認証されたユーザー情報
        user_info = get_authenticated_user(request)
        
        # Microsoft Graphから追加のユーザー情報を取得
        graph_user_info = get_user_info_from_graph_api()

        return templates.TemplateResponse("index.html", {
            "request": request, 
            "user_info": user_info, 
            "graph_user_info": graph_user_info
        })
    except HTTPException as e:
        print(f"Error: {e.detail}")
        raise e
    except Exception as e:
        # エラーの詳細なトレースバックを出力
        traceback.print_exc()
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")