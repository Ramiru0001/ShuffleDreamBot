import json

# words.json ファイルを読み込む
with open('words.json', 'r', encoding='utf-8') as f:
    word_data = json.load(f)

# 単語リストとセットを作成
word_list = word_data['words']
word_set = set(word_list)

# 重複があるか確認
if len(word_list) != len(word_set):
    print("重複する単語があります。")
    
    # 重複する単語を特定
    seen = set()
    duplicates = set()
    for word in word_list:
        if word in seen:
            duplicates.add(word)
        else:
            seen.add(word)
    
    # 重複する単語を削除して1つだけ残す
    unique_words = list(word_set)
    
    # 重複した単語を出力
    print("削除された重複単語: ", duplicates)
    
    # 重複を除いたリストを更新
    word_data['words'] = unique_words
    
    # 更新されたリストをwords.jsonファイルに書き込む
    with open('words.json', 'w', encoding='utf-8') as f:
        json.dump(word_data, f, ensure_ascii=False, indent=4)

else:
    print("重複する単語はありません。")