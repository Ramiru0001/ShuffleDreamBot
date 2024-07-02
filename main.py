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
bot = commands.Bot(command_prefix='!',intents=intents)

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

#s ボットの準備ができたときの処理
@bot.event
async def on_ready():
    print(f'{bot.user.name} が接続しました!')
@bot.event
async def on_disconnect():
    print('ボットが切断されました。')
# VOICEVOX APIを使って音声データを生成する関数
def generate_voice(text):
    try:
        params = {
            'text': text,
            'speaker': 1  # スピーカーIDは適宜変更してください
        }
        response = requests.post('http://localhost:50021/audio_query', params=params)
        audio_query = response.json()
        
        response = requests.post('http://localhost:50021/synthesis', json=audio_query)
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
async def play_random_word(vc):
    global word_list
    try:
        word=await choice_word(word_list)
        sound_file_path = generate_voice(word)
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
async def join(ctx):
    try:
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await ctx.send(f"VCに参加します: {channel.name}")
            vc = await channel.connect()
            play_random_word.start(vc)
        else:
            await ctx.send("VCに参加してください。")
    except Exception as e:
        logger.error(f'joinコマンドの処理中にエラーが発生しました: {e}')
        await ctx.send("VCに参加できませんでした。")

@bot.command(name='leave')
async def leave(ctx):
    try:
        if ctx.voice_client:
            channel = ctx.author.voice.channel
            await ctx.send(f"VCから退出します: {channel.name}")
            await ctx.guild.voice_client.disconnect()
            play_random_word.stop()
        else:
            await ctx.send("ボイスチャンネルに参加していません。")
    except Exception as e:
        logger.error(f'leaveコマンドの処理中にエラーが発生しました: {e}')
        await ctx.send("VCから切断できませんでした。")
# メッセージを受信したときの処理
# @bot.event
# async def on_message(message):
#     if message.author == bot.user:
#         return
    
#     if message.content.startswith('!ping'):
#         await message.channel.send('Pong!')

@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('Pong!')

# イベントループの取得と開始
loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(bot.start(TOKEN))
except KeyboardInterrupt:
    loop.run_until_complete(bot.close())
finally:
    loop.close()