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
CHANNEL_SECRET = os.environ.get('CHANNEL_SECRET', 'e7abc44821e008e091c700b141b2ec31')
CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN', 'NuKWQPd60fq1ZNU3OCioQXvGjpdXQg320cxlsmMKdSgK/d6ssiqt014c2DCGZgfp40eYOvIp9uWxWRDpEgnYaRh3EBmcSSMcMJKrBHddsGPHafjouy9xPHI+ZDNfB2brYP4euOQRj7qyy4T4R8Rc7wdB04t89/1O/w1cDnyilFU=')
IMGBB_API_KEY = os.environ.get('IMGBB_API_KEY', '6e0f692a1c9ea0933f2475a961c33a02')

TARGET_GROUP_ID = os.environ.get('TARGET_GROUP_ID', 'C68c6b953cc5f79bca8b37b0e8a494224')
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

# 取得群組名稱的輔助函式
def get_group_name(line_bot_api, group_id):
    try:
        summary = line_bot_api.get_group_summary(group_id)
        return summary.group_name
    except Exception as e:
        print(f"無法取得群組名稱: {e}")
        return "未知群組"

# 取得群組成員名稱的輔助函式
def get_member_name(line_bot_api, group_id, user_id):
    try:
        profile = line_bot_api.get_group_member_profile(group_id, user_id)
        return profile.display_name
    except Exception as e:
        print(f"無法取得成員名稱（可能未加好友或無權限）: {e}")
        return "群組成員"

# 處理文字訊息
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text(event):
    text = event.message.text.strip()
    
    # 1. 檢查訊息來源：如果不是來自「群組」，直接結束不轉發
    if not isinstance(event.source, GroupSource):
        return

    group_id = event.source.group_id
    user_id = event.source.user_id

    print(f"====================================")
    print(f"【當前群組 ID】：{group_id} | 【使用者 ID】：{user_id}")
    print(f"====================================")

    # 判斷訊息中是否「包含任何阿拉伯數字」
    has_digit = any(char.isdigit() for char in text)

    # 包含數字且已設定目標群組才進行轉發
    if has_digit and TARGET_GROUP_ID != 'YOUR_TARGET_GROUP_ID':
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            
            # 取得群組名稱與發送者名稱
            group_name = get_group_name(line_bot_api, group_id)
            user_name = get_member_name(line_bot_api, group_id, user_id)
            
            # 組合轉發訊息內容（顯示：群組名稱 - 傳送者名稱）
            forward_text = f"【{group_name} | {user_name}】\n{text}"
            
            push_request = PushMessageRequest(
                to=TARGET_GROUP_ID,
                messages=[TextMessage(text=forward_text)]
            )
            line_bot_api.push_message(push_request)

# 處理圖片訊息
@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image(event):
    if not isinstance(event.source, GroupSource):
        return
        
    if TARGET_GROUP_ID == 'YOUR_TARGET_GROUP_ID':
        return

    group_id = event.source.group_id
    user_id = event.source.user_id
    message_id = event.message.id
    
    with ApiClient(configuration) as api_client:
        line_bot_blob_api = MessagingApiBlob(api_client)
        line_bot_api = MessagingApi(api_client)

        # 1. 取得群組名稱與發送者名稱
        group_name = get_group_name(line_bot_api, group_id)
        user_name = get_member_name(line_bot_api, group_id, user_id)

        # 2. 下載 LINE 聊天室傳送的圖片
        image_bytes = line_bot_blob_api.get_message_content(message_id)

        # 3. 上傳至 ImgBB 取得公開網址
        payload = {'key': IMGBB_API_KEY}
        files = {'image': image_bytes}
        res = requests.post('https://api.imgbb.com/1/upload', data=payload, files=files)
        
        if res.status_code == 200:
            res_json = res.json()
            img_url = res_json['data']['url']
            
            # 4. 轉發文字提示（帶群組與人員）與圖片至目標群組
            push_request = PushMessageRequest(
                to=TARGET_GROUP_ID,
                messages=[
                    TextMessage(text=f"【{group_name} | {user_name} 的圖片】"),
                    ImageMessage(original_content_url=img_url, preview_image_url=img_url)
                ]
            )
            line_bot_api.push_message(push_request)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
