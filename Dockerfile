# Python 3.9ベースのイメージを使用
FROM python:3.9

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係を追加
COPY requirements.txt .

# パッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# アプリケーションを起動
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:${WEBSITES_PORT}", "main:app"]
