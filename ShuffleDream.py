import os
import discord
import sys
import asyncio
import random
import logging
import json
import requests
from dotenv import load_dotenv
from discord.ext import commands, tasks

if __name__ == '__main__':
    pass

# .envファイルから環境変数を読み込む
load_dotenv()

# ロガーの設定
logger = logging.getLogger('discord_bot')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)  # コンソールに出力するハンドラーを追加
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# Discordボットのトークン
TOKEN = os.getenv("DISCORD_TOKEN")
# Intentsを設定
intents = discord.Intents.default()
intents.messages = True  # メッセージコンテンツを取得するために必要
intents.voice_states = True
if sys.platform == "win32":
    intents.message_content = True
# ボットを作成
bot = commands.Bot(command_prefix='?',intents=intents)

# word_listからランダムに単語を選択する非同期関数
async def choice_word(word_list):
    word = random.choice(word_list)
    return word

def load_words_from_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)
        words = data['words']  # 'words' キーに格納されている単語リストを取得
        return words
# ファイルパス
json_file_path = 'words.json'

# JSONファイルから単語リストを読み込む
word_list = load_words_from_json(json_file_path)

#wavファイルオール削除
async def clearWav():
    # WAVファイルがあれば、すべて消去する
    for filename in os.listdir('.'):
        if filename.endswith('.wav'):
            os.remove(filename)

#s ボットの準備ができたときの処理
@bot.event
async def on_ready():
    print(f'{bot.user.name} が接続しました!')
    #wavファイルがあれば、全て消去する
    await clearWav()
@bot.event
async def on_disconnect():
    print('ボットが切断されました。')
# VOICEVOX APIを使って音声データを生成する関数
def generate_voice(text,speaker):
    try:
        params = {
            'text': text,
            'speaker': speaker  # スピーカーIDは適宜変更してください
        }
        response = requests.post('http://localhost:50021/audio_query', params=params)
        audio_query = response.json()
        # /audio_queryエンドポイントへのリクエスト
        response = requests.post(f'http://localhost:50021/synthesis?speaker={speaker}', json=audio_query)
    
        #response = requests.post('http://localhost:50021/synthesis', json=audio_query)
        sound_file_path = f'{text}.wav'
        
        with open(sound_file_path, 'wb') as f:
            f.write(response.content)
        
        return sound_file_path
    except requests.exceptions.RequestException as e:
        print(f"VOICEVOX APIのリクエスト中にエラーが発生しました: {e}")
        return None
    except Exception as e:
        print(f"音声生成中にエラーが発生しました: {e}")
        return None
# 音声再生用のタスク
@tasks.loop(seconds=10)
async def play_random_word(vc,speaker):
    global word_list
    try:
        word=await choice_word(word_list)
        sound_file_path = generate_voice(word,speaker)
        if sound_file_path:
            vc.play(discord.FFmpegPCMAudio(source=sound_file_path))
            while vc.is_playing():
                await asyncio.sleep(1)
            # 再生後に一時ファイルを削除
            os.remove(sound_file_path)
        else:
            print("音声ファイルの生成に失敗しました。")
    except Exception as e:
        logger.error(f'音声の再生中に失敗しました: {e}')
    
@bot.command(name='join')
async def join(ctx,  channel_name=None,speaker_num=None):
    try:
        if channel_name:
            channel = discord.utils.get(ctx.guild.voice_channels, name=channel_name)
            if not channel:
                await ctx.send(f"{channel_name} という名前のボイスチャンネルが見つかりませんでした。")
                return
        else:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
            else:
                await ctx.send("ユーザーがボイスチャンネルに接続していません。VC名を指定してください。")
                return
        await ctx.send(f"VCに参加します: {channel.name}")

        if speaker_num == None:
            speaker_num = '1'  # デフォルトでスピーカーIDが1に設定されます
        # /speakers エンドポイントにGETリクエストを送信してスピーカー情報を取得

        base_url = "http://127.0.0.1:50021/"

        response = requests.get(base_url + "speakers")
        response.raise_for_status()  # エラーチェック
        
        speakers = response.json()  # JSON形式のレスポンスをデコード

        selected_speaker = None
        for sp in speakers:
            for style in sp["styles"]:
            #speakersの中にspeakerがあれば、OKなければreturn
                if str(style["id"]) == speaker_num:
                    selected_speaker=sp
                    selected_style = style
                    break
        if selected_speaker==None:
            await ctx.send("選択されたスピーカーは存在しません。")
            return
        await ctx.send(f"選択されたスピーカー: {selected_speaker['name']}  {selected_style['name']}")
        vc = await channel.connect()
        if not vc.is_connected():
            await ctx.send("ボイスチャンネルへの接続に失敗しました。")
            return
        play_random_word.start(vc,speaker_num)
    except Exception as e:
        logger.error(f'joinコマンドの処理中にエラーが発生しました: {e}')
        await ctx.send("VCに参加できませんでした。")

@bot.command(name='leave')
async def leave(ctx,channel_name=None):
    try:
        if ctx.voice_client:
            if channel_name:
                channel = discord.utils.get(ctx.guild.voice_channels, name=channel_name)
                if not channel:
                    await ctx.send(f"{channel_name} という名前のボイスチャンネルが見つかりませんでした。")
                    return
            else:
                if ctx.author.voice:
                    channel = ctx.author.voice.channel
                else:
                    await ctx.send("ユーザーがボイスチャンネルに接続していません。VC名を指定してください。")
                    return
            await ctx.send(f"VCから退出します: {channel.name}")
            await ctx.guild.voice_client.disconnect()
            play_random_word.stop()
            # wavファイルがあれば、全て消去する
            await clearWav()
        else:
            await ctx.send("ボイスチャンネルに参加していません。")
    except Exception as e:
        logger.error(f'leaveコマンドの処理中にエラーが発生しました: {e}')
        await ctx.send("VCから切断できませんでした。")

@bot.command(name='speakers')
async def list_speakers(ctx):
    try:
        base_url = "http://127.0.0.1:50021/"
        # /speakers エンドポイントにGETリクエストを送信してスピーカー情報を取得
        response = requests.get(base_url + "speakers")
        response.raise_for_status()  # エラーチェック
        
        speakers = response.json()  # JSON形式のレスポンスをデコード

        if not speakers:
            await ctx.send("スピーカー情報が見つかりませんでした。")
            return
        message = "Voicevox Speakers\n"
        current_message = message

        for speaker in speakers:
            speaker_name = speaker["name"]
            supported_styles = speaker["styles"]
            current_message += f"\n {speaker_name} :"
            for style in supported_styles:
                style_name = style["name"]
                style_id = style["id"]
                current_message += f" [{style_name}:{style_id}] "

            # メッセージが2000文字を超えるか確認して送信
            if len(current_message) > 2000:
                await ctx.send( current_message)
                current_message = ""
        # 最後のメッセージを送信
        if current_message:
            await ctx.send(current_message)
    except Exception as e:
         await ctx.send(f"Voicevoxエンジンとの通信中にエラーが発生しました: {e}")
@bot.command(name='change_speaker')
async def change_speakers(ctx, speaker_id=None):
    try:
        base_url = "http://127.0.0.1:50021/"
        
        # /speakers エンドポイントにGETリクエストを送信してスピーカー情報を取得
        response = requests.get(base_url + "speakers")
        response.raise_for_status()  # エラーチェック
        
        speakers = response.json()  # JSON形式のレスポンスをデコード
        
        if not speakers:
            await ctx.send("利用可能なスピーカーが見つかりませんでした。")
            return
        if speaker_id==None:
            await ctx.send("!change_speaker 番号 という形で呼び出してください。")
            return
        # 引数で指定されたスピーカーIDがあれば、そのスピーカーに切り替える
        selected_speaker = None
        for speaker in speakers:
            for style in speaker["styles"]:
                if str(style["id"]) == speaker_id:
                    selected_speaker = speaker
                    selected_style=style
                    break
        
        if selected_speaker:
            await ctx.send(f"スピーカーを変更します: {selected_speaker['name']}  {selected_style['name']}")
            # ここでスピーカーを変更する処理を実装する（未実装）
            voice_client = ctx.voice_client
            play_random_word.stop()
            await asyncio.sleep(10)  # 適宜待機してから新しいタスクを開始する
            play_random_word.start(voice_client,speaker_id)
        else:
            await ctx.send("指定されたスピーカーが見つかりませんでした。")
    except Exception as e:
        await ctx.send(f"スピーカーの変更中にエラーが発生しました: {e}")
    pass
# @bot.command(name='ping')
# async def ping(ctx):
#     await ctx.send('Pong!')
# infoコマンドの追加
@bot.command(name='info')
async def info(ctx):
    info_message = """
    ?info:各コマンドの説明画面です
    ?join <VCの名前> <speaker_id> : 指定したボイスチャネルに参加します。
    ?leave <VCの名前> : 指定したボイスチャネルから退出します。
    ?change_speaker <speaker_id> : 読み上げる声を変更します。
    ?speakers : 利用可能なスピーカーの一覧を表示します。speaker_idはここで確認してください。
    ?info : コマンドの一覧と説明を表示します。
    
    <speaker_id> とは、読み上げる声の番号のこと。?speakersのコマンドで、番号を確認できる。
    VOICEVOXに登録されている声はほぼ全て使用可能す。
    """
    await ctx.send(info_message)



# イベントループの取得と開始
loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(bot.start(TOKEN))
except KeyboardInterrupt:
    loop.run_until_complete(bot.close())
finally:
    loop.close()