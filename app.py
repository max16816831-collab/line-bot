import os
import requests
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, MessagingApiBlob,
    TextMessage, ImageMessage, PushMessageRequest
)
from linebot.v3.webhooks import (
    MessageEvent, TextMessageContent, ImageMessageContent, GroupSource
)

app = Flask(__name__)

# ===== 請替換成你的金鑰與目標群組 ID =====
CHANNEL_SECRET = 'e7abc44821e008e091c700b141b2ec31'
CHANNEL_ACCESS_TOKEN = 'NuKWQPd60fq1ZNU3OCioQXvGjpdXQg320cxlsmMKdSgK/d6ssiqt014c2DCGZgfp40eYOvIp9uWxWRDpEgnYaRh3EBmcSSMcMJKrBHddsGPHafjouy9xPHI+ZDNfB2brYP4euOQRj7qyy4T4R8Rc7wdB04t89/1O/w1cDnyilFU='
IMGBB_API_KEY = '6e0f692a1c9ea0933f2475a961c33a02'

# 請確保此處已貼上你實際的 C 開頭目標群組 ID
TARGET_GROUP_ID = 'C68c6b953cc5f79bca8b37b0e8a494224'
# ==========================================

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

@app.route("/", methods=['GET'])
def home():
    return "Line Bot is running!"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 處理文字訊息
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text(event):
    text = event.message.text.strip()
    
    # 只要訊息進來，就在日誌中印出當前群組 ID
    if isinstance(event.source, GroupSource):
        print(f"====================================")
        print(f"【當前群組 Group ID】：{event.source.group_id}")
        print(f"====================================")

    # 判斷訊息中是否「包含任何阿拉伯數字」
    has_digit = any(char.isdigit() for char in text)

    # 包含數字且已設定目標群組才進行轉發
    if has_digit and TARGET_GROUP_ID != 'YOUR_TARGET_GROUP_ID':
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            push_request = PushMessageRequest(
                to=TARGET_GROUP_ID,
                messages=[TextMessage(text=text)]  # 原樣轉發訊息內容
            )
            line_bot_api.push_message(push_request)

# 處理圖片訊息
@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image(event):
    if TARGET_GROUP_ID == 'YOUR_TARGET_GROUP_ID':
        return

    message_id = event.message.id
    with ApiClient(configuration) as api_client:
        line_bot_blob_api = MessagingApiBlob(api_client)
        line_bot_api = MessagingApi(api_client)

        # 1. 下載 LINE 聊天室傳送的圖片
        image_bytes = line_bot_blob_api.get_message_content(message_id)

        # 2. 上傳至 ImgBB 取得公開網址
        payload = {'key': IMGBB_API_KEY}
        files = {'image': image_bytes}
        res = requests.post('https://api.imgbb.com/1/upload', data=payload, files=files)
        
        if res.status_code == 200:
            res_json = res.json()
            img_url = res_json['data']['url']
            
            # 3. 轉發圖片至目標群組
            push_request = PushMessageRequest(
                to=TARGET_GROUP_ID,
                messages=[ImageMessage(original_content_url=img_url, preview_image_url=img_url)]
            )
            line_bot_api.push_message(push_request)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
