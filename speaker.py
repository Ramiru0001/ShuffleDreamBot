import requests
import json

# VoicevoxエンジンのベースURL
base_url = "http://127.0.0.1:50021/"

def enumerate_speakers():
    try:
        # /speakers エンドポイントにGETリクエストを送信してスピーカー情報を取得
        response = requests.get(base_url + "speakers")
        response.raise_for_status()  # エラーチェック
        
        speakers = response.json()  # JSON形式のレスポンスをデコード
        # スピーカー情報をJSONファイルに書き込む
        with open('speakers.json', 'w', encoding='utf-8') as json_file:
            json.dump(speakers, json_file, ensure_ascii=False, indent=4)

        for speaker in speakers:
            speaker_name = speaker["name"]
            speaker_uuid = speaker["speaker_uuid"]
            supported_styles = speaker["styles"]
            
            print(f"Speaker: {speaker_name} (UUID: {speaker_uuid})")
            print("Supported Styles:")
            for style in supported_styles:
                style_name = style["name"]
                style_id = style["id"]
                print(f"- {style_name}: {style_id}")
            print()
    
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Voicevox engine: {e}")

# enumerate_speakers関数を実行してスピーカー情報とそのスタイルのIDを出力する
enumerate_speakers()
