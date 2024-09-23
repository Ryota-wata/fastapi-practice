import os
import json
import requests
import base64
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

# ユーザーアクセストークンを取得
def get_user_access_token(request: Request):
    access_token = request.headers.get("X-MS-TOKEN-AAD-ACCESS-TOKEN")
    if not access_token:
        logger.error("Missing X-MS-TOKEN-AAD-ACCESS-TOKEN header")
        raise HTTPException(status_code=401, detail="Unauthorized: Missing access token")
    return access_token

# Microsoft Graph APIからユーザー情報を取得
def get_user_info_from_graph_api(request: Request):
    access_token = get_user_access_token(request)
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        response = requests.get(GRAPH_API_ENDPOINT, headers=headers)
        response.raise_for_status()
        user_info = response.json()
        logger.debug(f"Retrieved user info from Graph API: {user_info}")
        return user_info
    except requests.RequestException as e:
        logger.error(f"Failed to get user info from Microsoft Graph API: {str(e)}")
        raise HTTPException(status_code=response.status_code, detail=f"Failed to get user info from Microsoft Graph API: {str(e)}")

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
        graph_user_info = get_user_info_from_graph_api(request)

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