import os
import json
import requests
import base64
from azure.identity import ClientSecretCredential
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import traceback
import logging

# ロギングの設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# Jinja2テンプレート設定
templates = Jinja2Templates(directory="templates")

# Microsoft Graph APIのエンドポイント
GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0/me"

# Azure AD設定
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

# クライアントシークレット認証情報を作成
credential = ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)

# EasyAuthで認証されたユーザー情報を取得
def get_authenticated_user(request: Request):
    user_info_encoded = request.headers.get("X-MS-CLIENT-PRINCIPAL")
    if not user_info_encoded:
        logger.error("Missing X-MS-CLIENT-PRINCIPAL header")
        raise HTTPException(status_code=401, detail="Unauthorized: Missing X-MS-CLIENT-PRINCIPAL header")
    
    try:
        user_info_decoded = json.loads(base64.b64decode(user_info_encoded).decode('utf-8'))
        logger.debug(f"Decoded user info: {user_info_decoded}")
        return user_info_decoded
    except Exception as e:
        logger.error(f"Failed to decode user info: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to decode user info: {str(e)}")

# アクセストークンを取得
def get_access_token():
    try:
        scope = "https://graph.microsoft.com/.default"
        access_token = credential.get_token(scope).token
        logger.debug(f"Access token acquired: {access_token[:10]}...")
        return access_token
    except Exception as e:
        logger.error(f"Failed to get access token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get access token: {str(e)}")

# Microsoft Graph APIからユーザー情報を取得
def get_user_info_from_graph_api():
    try:
        access_token = get_access_token()
        headers = {'Authorization': f'Bearer {access_token}'}
        
        logger.debug(f"Sending request to Graph API: {GRAPH_API_ENDPOINT}")
        response = requests.get(GRAPH_API_ENDPOINT, headers=headers)
        response.raise_for_status()
        user_info = response.json()
        logger.debug(f"Retrieved user info from Graph API: {user_info}")
        return user_info
    except requests.RequestException as e:
        logger.error(f"Failed to get user info from Microsoft Graph API: {str(e)}")
        logger.error(f"Response status code: {e.response.status_code if e.response else 'No response'}")
        logger.error(f"Response content: {e.response.content if e.response else 'No response'}")
        raise HTTPException(status_code=e.response.status_code if e.response else 500, 
                            detail=f"Failed to get user info from Microsoft Graph API: {str(e)}")

@app.middleware("http")
async def log_request(request: Request, call_next):
    logger.debug(f"Request headers: {request.headers}")
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
        logger.error(f"HTTP Exception: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)