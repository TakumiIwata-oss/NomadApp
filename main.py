from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
import os
import polyline
import requests
import json
from datetime import datetime
import re

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# OpenAI クライアントの設定
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def get_route(origin, destination, api_key):
    """Google Maps APIを使用して経路を取得する関数"""
    base_url = "https://maps.googleapis.com/maps/api/directions/json?"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": "walking",
        "key": api_key
    }
    
    response = requests.get(base_url, params=params)
    data = response.json()
    
    if data["status"] == "OK":
        route = data["routes"][0]["overview_polyline"]["points"]
        return route
    else:
        return None


def get_place_suggestions(query, location, api_key):
    """Google Places APIを使用して場所の候補を取得する関数"""
    base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json?"
    params = {
        "query": query,
        "location": location,
        "radius": 5000,
        "key": api_key
    }
    
    response = requests.get(base_url, params=params)
    data = response.json()
    
    if data["status"] == "OK":
        return data["results"]
    else:
        return []

def get_restaurants_near_location(lat, lng, api_key, radius=2000):
    """指定された座標周辺の飲食店を取得する関数"""
    base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?"
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "type": "restaurant",
        "key": api_key
    }
    
    response = requests.get(base_url, params=params)
    data = response.json()
    
    if data["status"] == "OK":
        restaurants = []
        for place in data["results"][:5]:  # 上位5件のみ取得
            if place.get("rating", 0) >= 3.0:  # 評価3.0以上のみ
                restaurants.append({
                    "name": place["name"],
                    "rating": place.get("rating", "N/A"),
                    "price_level": place.get("price_level", "N/A"),
                    "vicinity": place.get("vicinity", ""),
                    "lat": place["geometry"]["location"]["lat"],
                    "lng": place["geometry"]["location"]["lng"],
                    "place_id": place["place_id"]
                })
        return restaurants
    else:
        return []

def create_google_maps_url(locations, restaurants=None, route_polyline=None):
    """Google Mapsの埋め込みURLを生成"""
    if not locations:
        return None
    
    # 基本的なGoogle Maps Embed URL
    base_url = "https://www.google.com/maps/embed/v1/"
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    if not api_key:
        return None
    
    # 複数の場所がある場合は directions を使用
    if len(locations) >= 2:
        origin = f"{locations[0]['lat']},{locations[0]['lng']}"
        destination = f"{locations[-1]['lat']},{locations[-1]['lng']}"
        
        # 中間地点がある場合はwaypointsに追加
        waypoints = ""
        if len(locations) > 2:
            middle_points = []
            for loc in locations[1:-1]:
                middle_points.append(f"{loc['lat']},{loc['lng']}")
            waypoints = f"&waypoints={','.join(middle_points)}"
        
        url = f"{base_url}directions?key={api_key}&origin={origin}&destination={destination}{waypoints}&mode=walking"
    else:
        # 単一地点の場合は place を使用
        location = locations[0]
        url = f"{base_url}place?key={api_key}&q={location['lat']},{location['lng']}&zoom=15"
    
    return url

def extract_travel_info_from_ai_response(ai_response):
    """AIの応答から旅行情報を抽出する"""
    locations = []
    
    # JSONフォーマットの応答を解析
    try:
        if "```json" in ai_response:
            json_start = ai_response.find("```json") + 7
            json_end = ai_response.find("```", json_start)
            json_str = ai_response[json_start:json_end].strip()
            travel_data = json.loads(json_str)
            
            if "locations" in travel_data:
                for loc in travel_data["locations"]:
                    locations.append({
                        "name": loc.get("name", ""),
                        "description": loc.get("description", ""),
                        "search_query": loc.get("search_query", loc.get("name", ""))
                    })
        else:
            # テキストから場所を抽出（従来の方法）
            location_pattern = r'「([^」]+)」'
            location_names = re.findall(location_pattern, ai_response)
            for name in location_names:
                locations.append({
                    "name": name,
                    "description": "",
                    "search_query": name
                })
    except:
        # フォールバック：テキストから場所を抽出
        location_pattern = r'「([^」]+)」'
        location_names = re.findall(location_pattern, ai_response)
        for name in location_names:
            locations.append({
                "name": name,
                "description": "",
                "search_query": name
            })
    
    return locations

def get_conversation_state():
    """現在の会話状態を取得"""
    if 'conversation_state' not in session:
        session['conversation_state'] = {
            'step': 'greeting',
            'collected_info': {},
            'messages': []
        }
    return session['conversation_state']

def update_conversation_state(step, info=None):
    """会話状態を更新"""
    state = get_conversation_state()
    state['step'] = step
    if info:
        state['collected_info'].update(info)
    session['conversation_state'] = state
    return state

def analyze_user_input(message, current_state):
    """ユーザーの入力を分析して必要な情報を抽出"""
    info = {}
    message_lower = message.lower()
    
    # 出発地・目的地の抽出
    if 'から' in message and 'に' in message:
        parts = message.split('から')
        if len(parts) >= 2:
            origin_part = parts[0].strip()
            dest_part = parts[1].split('に')[0].strip()
            info['origin'] = origin_part
            info['destination'] = dest_part
    elif 'まで' in message or 'へ' in message:
        # 目的地のみの場合
        if 'まで' in message:
            info['destination'] = message.split('まで')[0].strip()
        elif 'へ' in message:
            info['destination'] = message.split('へ')[0].strip()
    
    # 移動手段の抽出
    transport_keywords = {
        '電車': 'train', '車': 'car', '徒歩': 'walking', 
        'バス': 'bus', '自転車': 'bicycle', '飛行機': 'plane'
    }
    for keyword, transport in transport_keywords.items():
        if keyword in message:
            info['transport'] = transport
            break
    
    # 予算の抽出
    import re
    budget_match = re.search(r'(\d+)円|予算.*?(\d+)', message)
    if budget_match:
        budget = budget_match.group(1) or budget_match.group(2)
        info['budget'] = int(budget)
    
    # 時間の抽出
    time_match = re.search(r'(\d{1,2})時|午前|午後|朝|昼|夜|夕方', message)
    if time_match:
        info['preferred_time'] = time_match.group(0)
    
    # 食べ物の好みの抽出
    food_keywords = ['和食', '洋食', '中華', 'イタリアン', 'フレンチ', 'ラーメン', '寿司', '焼肉', 'カフェ']
    for food in food_keywords:
        if food in message:
            info['food_preference'] = food
            break
    
    return info

def generate_next_question(state):
    """次に聞くべき質問を生成"""
    collected = state['collected_info']
    
    # 必要な情報のチェックリスト
    required_info = {
        'origin': '出発地はどちらですか？',
        'destination': '目的地はどちらですか？',
        'transport': 'どの交通手段をご希望ですか？（電車、車、徒歩など）',
        'budget': '予算の目安はありますか？（食事代など）',
        'preferred_time': '何時頃に到着予定ですか？',
        'food_preference': 'どんなお料理がお好みですか？（和食、洋食など）'
    }
    
    # 不足している情報を確認
    for key, question in required_info.items():
        if key not in collected or not collected[key]:
            return question, key
    
    return None, 'complete'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    
    # 会話状態を取得
    state = get_conversation_state()
    
    # ユーザー入力を分析
    extracted_info = analyze_user_input(user_message, state)
    
    # 会話履歴にユーザーメッセージを追加
    state['messages'].append({"role": "user", "content": user_message})
    
    # 抽出した情報で状態を更新
    if extracted_info:
        update_conversation_state(state['step'], extracted_info)
        state = get_conversation_state()  # 更新された状態を再取得
    
    # 次の質問を生成
    next_question, next_step = generate_next_question(state)
    
    if next_step != 'complete':
        # まだ情報が不足している場合は質問を返す
        ai_response = f"ありがとうございます！{next_question}"
        state['messages'].append({"role": "assistant", "content": ai_response})
        session['conversation_state'] = state
        
        return jsonify({
            "response": ai_response,
            "map_data": None,
            "locations": [],
            "restaurants": [],
            "route": None,
            "conversation_state": {
                "step": next_step,
                "collected_info": state['collected_info']
            }
        })
    
    # 全ての情報が揃った場合のシステムメッセージ
    collected = state['collected_info']
    context_info = f"""
    収集した旅行情報：
    - 出発地: {collected.get('origin', '未指定')}
    - 目的地: {collected.get('destination', '未指定')}
    - 交通手段: {collected.get('transport', '未指定')}
    - 予算: {collected.get('budget', '未指定')}円
    - 到着時間: {collected.get('preferred_time', '未指定')}
    - 食事の好み: {collected.get('food_preference', '未指定')}
    """
    
    messages = [
        {"role": "system", "content": f"""あなたは対話型旅行コンシェルジュAIです。ユーザーから収集した情報をもとに、最適な旅行ルートと飲食店を提案してください。

        {context_info}

        応答ルール：
        1. 収集した情報を活用して個人に最適化された提案を行う
        2. 具体的な場所名は「」で囲んで記載
        3. 以下のJSONフォーマットで情報を含めてください：

        ```json
        {{
          "locations": [
            {{
              "name": "場所名",
              "description": "特徴や見どころ",
              "search_query": "Google検索用クエリ"
            }}
          ],
          "route_summary": "出発地から目的地までのルート概要",
          "travel_info": "交通手段と所要時間"
        }}
        ```

        4. 予算や時間、食事の好みを考慮した提案
        5. 親しみやすく、実用的な情報を含めて応答"""},
        {"role": "user", "content": f"収集した情報をもとに旅行プランを作成してください。最新のリクエスト: {user_message}"}
    ]
    try:
        # ChatGPT APIを呼び出し
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=800,
            temperature=0.7
        )
        
        # APIレスポンスから回答を取得
        ai_message = response.choices[0].message.content
        
        # 旅行情報を抽出
        travel_locations = extract_travel_info_from_ai_response(ai_message)
        
        map_data = None
        restaurants_data = []
        route_data = None
        
        # Google Maps APIキーを取得
        api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        
        if travel_locations and api_key:
            resolved_locations = []
            all_restaurants = []
            
            # 各場所の座標を取得
            for location_info in travel_locations:
                # ユーザーの要望に合わせて地域を特定しない（全世界対応）
                location_query = location_info['search_query']
                places = get_place_suggestions(location_query, "35.6762,139.6503", api_key)  # 東京を中心とした検索
                
                if places:
                    place = places[0]
                    resolved_location = {
                        "name": location_info["name"],
                        "description": location_info["description"],
                        "lat": place["geometry"]["location"]["lat"],
                        "lng": place["geometry"]["location"]["lng"],
                        "address": place.get("formatted_address", ""),
                        "place_id": place["place_id"]
                    }
                    resolved_locations.append(resolved_location)
                    
                    # 各場所周辺の飲食店を検索
                    restaurants = get_restaurants_near_location(
                        resolved_location["lat"], 
                        resolved_location["lng"], 
                        api_key
                    )
                    all_restaurants.extend(restaurants)
            
            # 重複する飲食店を除去（place_idで判定）
            unique_restaurants = []
            seen_place_ids = set()
            for restaurant in all_restaurants:
                if restaurant["place_id"] not in seen_place_ids:
                    unique_restaurants.append(restaurant)
                    seen_place_ids.add(restaurant["place_id"])
            
            # 評価順でソート
            unique_restaurants.sort(key=lambda x: x.get("rating", 0), reverse=True)
            restaurants_data = unique_restaurants[:8]  # 上位8件
            
            # ルートを生成（複数地点がある場合）
            if len(resolved_locations) >= 2:
                origin = f"{resolved_locations[0]['lat']},{resolved_locations[0]['lng']}"
                destination = f"{resolved_locations[-1]['lat']},{resolved_locations[-1]['lng']}"
                route_polyline = get_route(origin, destination, api_key)
                if route_polyline:
                    route_data = {
                        "polyline": route_polyline,
                        "origin": resolved_locations[0]["name"],
                        "destination": resolved_locations[-1]["name"]
                    }
            
            # Google Maps埋め込みURLを生成
            if resolved_locations:
                google_maps_url = create_google_maps_url(resolved_locations, restaurants_data, 
                                                       route_data["polyline"] if route_data else None)
                
                if google_maps_url:
                    map_data = {
                        "url": google_maps_url,
                        "locations": resolved_locations,
                        "restaurants": restaurants_data,
                        "route": route_data
                    }
        
        return jsonify({
            "response": ai_message,
            "map_data": map_data,
            "locations": map_data["locations"] if map_data else [],
            "restaurants": restaurants_data,
            "route": route_data
        })
    
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

@app.route('/share', methods=['POST'])
def create_share_link():
    """旅行ルートの共有リンクを生成"""
    try:
        data = request.json
        
        # 共有データを生成（実際のアプリでは Database に保存）
        share_id = f"route_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 簡単な共有テキストを生成
        share_text = "🌟 AI生成の旅行ルート 🌟\n\n"
        
        if data.get('locations'):
            share_text += "📍 観光スポット:\n"
            for location in data['locations']:
                share_text += f"• {location['name']}\n"
            share_text += "\n"
        
        if data.get('restaurants'):
            share_text += "🍽️ おすすめ飲食店:\n"
            for restaurant in data['restaurants'][:3]:
                share_text += f"• {restaurant['name']} (★{restaurant['rating']})\n"
            share_text += "\n"
        
        share_text += "#旅行 #AI旅行プラン #Instagram映え"
        
        return jsonify({
            "share_id": share_id,
            "share_text": share_text,
            "share_url": f"{request.host_url}share/{share_id}"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    print(f"Starting Flask app on port {port}")
    print(f"API Key設定状況: {'設定済み' if os.getenv('OPENAI_API_KEY') else '未設定'}")
    
    # 開発環境でのみngrokを使用
    if debug and os.environ.get('USE_NGROK') == 'true':
        print("To use ngrok, set USE_NGROK=true environment variable")
        print("To set ngrok auth token, set NGROK_AUTH_TOKEN environment variable")
        
        try:
            from pyngrok import ngrok
            
            # Set ngrok auth token if provided
            if os.environ.get('NGROK_AUTH_TOKEN'):
                ngrok.set_auth_token(os.environ.get('NGROK_AUTH_TOKEN'))
            
            # Create ngrok tunnel
            public_url = ngrok.connect(port)
            print(f" * ngrok tunnel: {public_url}")
        except Exception as e:
            print(f"Warning: Could not create ngrok tunnel: {e}")
            print("Running without ngrok...")
    
    app.run(host='0.0.0.0', port=port, debug=debug)