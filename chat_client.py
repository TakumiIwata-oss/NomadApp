import requests
import json
import os
from typing import Dict, Any, Optional

class ChatClient:
    """山梨県観光AIコンシェルジュのクライアント実装"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """
        初期化
        
        Args:
            base_url: サーバーのベースURL
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.messages = []  # チャット履歴を保存
    
    def send_message(self, message: str) -> Dict[str, Any]:
        """
        メッセージを送信してAIの応答を取得する
        
        Args:
            message: 送信するメッセージ
            
        Returns:
            AIの応答データ（response, map_data含む）
        """
        if not message.strip():
            return {"error": "メッセージが空です"}
        
        # ユーザーメッセージを履歴に追加
        self.append_message(message, 'user')
        
        try:
            response = self.session.post(
                f"{self.base_url}/chat",
                headers={'Content-Type': 'application/json'},
                json={'message': message},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('error'):
                    self.append_message('申し訳ありません。エラーが発生しました。', 'ai')
                    return data
                
                # AIの応答を履歴に追加
                if data.get('response'):
                    self.append_message(data['response'], 'ai')
                
                return data
                
            else:
                error_msg = f"HTTPエラー: {response.status_code}"
                self.append_message('申し訳ありません。エラーが発生しました。', 'ai')
                return {"error": error_msg}
                
        except requests.exceptions.Timeout:
            error_msg = "タイムアウトエラーが発生しました"
            self.append_message('申し訳ありません。エラーが発生しました。', 'ai')
            return {"error": error_msg}
            
        except requests.exceptions.ConnectionError:
            error_msg = "サーバーに接続できませんでした"
            self.append_message('申し訳ありません。エラーが発生しました。', 'ai')
            return {"error": error_msg}
            
        except Exception as e:
            error_msg = f"予期しないエラー: {str(e)}"
            self.append_message('申し訳ありません。エラーが発生しました。', 'ai')
            return {"error": error_msg}
    
    def append_message(self, message: str, sender: str):
        """
        メッセージを履歴に追加する
        
        Args:
            message: メッセージ内容
            sender: 送信者（'user' または 'ai'）
        """
        self.messages.append({
            'message': message,
            'sender': sender,
            'timestamp': self._get_current_time()
        })
    
    def get_chat_history(self) -> list:
        """
        チャット履歴を取得する
        
        Returns:
            チャット履歴のリスト
        """
        return self.messages.copy()
    
    def display_chat_history(self):
        """チャット履歴をコンソールに表示する"""
        print("\n=== チャット履歴 ===")
        for msg in self.messages:
            sender_label = "あなた" if msg['sender'] == 'user' else "AI"
            print(f"[{msg['timestamp']}] {sender_label}: {msg['message']}")
        print("==================\n")
    
    def clear_history(self):
        """チャット履歴をクリアする"""
        self.messages.clear()
    
    def save_map_data(self, map_data: Optional[Dict[str, Any]], filename: str = None) -> Optional[str]:
        """
        地図データを保存する
        
        Args:
            map_data: 地図データ
            filename: 保存ファイル名（指定しない場合は自動生成）
            
        Returns:
            保存したファイルパス（保存に失敗した場合はNone）
        """
        if not map_data:
            return None
        
        if not filename:
            filename = f"map_data_{self._get_current_time().replace(':', '-')}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(map_data, f, ensure_ascii=False, indent=2)
            return filename
        except Exception as e:
            print(f"地図データの保存に失敗しました: {e}")
            return None
    
    def _get_current_time(self) -> str:
        """現在時刻を文字列で取得する"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def interactive_chat():
    """対話型チャットを開始する"""
    client = ChatClient()
    
    print("山梨県観光AIコンシェルジュへようこそ！")
    print("メッセージを入力してください（'quit'で終了、'history'で履歴表示、'clear'で履歴クリア）")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\nあなた: ").strip()
            
            if user_input.lower() == 'quit':
                print("チャットを終了します。")
                break
            elif user_input.lower() == 'history':
                client.display_chat_history()
                continue
            elif user_input.lower() == 'clear':
                client.clear_history()
                print("チャット履歴をクリアしました。")
                continue
            elif not user_input:
                continue
            
            # メッセージを送信
            print("AI: 考え中...")
            response_data = client.send_message(user_input)
            
            if response_data.get('error'):
                print(f"エラー: {response_data['error']}")
            else:
                print(f"AI: {response_data.get('response', '応答がありませんでした')}")
                
                # 地図データがある場合は通知
                if response_data.get('map_data'):
                    map_url = response_data['map_data'].get('url')
                    print(f"📍 地図が生成されました: {map_url}")
                    
                    # 地図データを保存するか確認
                    save_choice = input("地図データを保存しますか？ (y/n): ").strip().lower()
                    if save_choice == 'y':
                        saved_file = client.save_map_data(response_data['map_data'])
                        if saved_file:
                            print(f"地図データを保存しました: {saved_file}")
        
        except KeyboardInterrupt:
            print("\n\nチャットを終了します。")
            break
        except Exception as e:
            print(f"予期しないエラーが発生しました: {e}")


if __name__ == "__main__":
    interactive_chat()