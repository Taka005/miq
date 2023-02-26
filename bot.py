import logging
from misskey import Misskey, NoteVisibility
import websockets
import asyncio, aiohttp
import json
import datetime
import sys
import traceback
import re
import math
import time
import textwrap
import requests

try:
    import config_my as config
except ImportError:
    import config

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pilmoji import Pilmoji
from io import BytesIO
from modules.emojistore import EmojiStore
import sqlite3

logging.getLogger("websockets").setLevel(logging.INFO)
logging.getLogger("PIL.Image").setLevel(logging.ERROR)
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

WS_URL = f'wss://{config.MISSKEY_INSTANCE}/streaming?i={config.MISSKEY_TOKEN}'

MISSKEY_EMOJI_REGEX = re.compile(r':([a-zA-Z0-9_]+)(?:@?)(|[a-zA-Z0-9\.-]+):')

_tmp_cli = Misskey(config.MISSKEY_INSTANCE, i=config.MISSKEY_TOKEN)
i = _tmp_cli.i()

eStore = EmojiStore(sqlite3.connect('emoji_cache.db'))

session = requests.Session()
session.headers.update({
    'User-Agent': f'Mozilla/5.0 (Linux; x64; Misskey Bot; {i["id"]}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
})

msk = Misskey(config.MISSKEY_INSTANCE, i=config.MISSKEY_TOKEN, session=session)

MY_ID = i['id']
ACCT = f'@{i["username"]}'
print('Bot user id: ' + MY_ID)

BASE_GRADATION_IMAGE = Image.open('base-gd-5.png')
BASE_WHITE_IMAGE = Image.open('base-w.png')

FONT_FILE = 'fonts/MPLUSRounded1c-Regular.ttf'
FONT_FILE_SERIF = 'fonts/NotoSerifJP-Regular.otf'
FONT_FILE_OLD_JAPANESE = 'fonts/YujiSyuku-Regular.ttf'
FONT_FILE_POP = 'fonts/MochiyPopPOne-Regular.ttf'

#MPLUS_FONT_TEXT = ImageFont.truetype(FONT_FILE, size=45)
#MPLUS_FONT_NAME = ImageFont.truetype(FONT_FILE, size=30)
MPLUS_FONT_16 = ImageFont.truetype('fonts/MPLUSRounded1c-Regular.ttf', size=16)

session = aiohttp.ClientSession()

default_format = '%(asctime)s:%(name)s: %(levelname)s:%(message)s'

logging.basicConfig(level=logging.DEBUG, filename='debug.log', encoding='utf-8', format=default_format)
# also write log to stdout
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(logging.Formatter(default_format))
logging.getLogger().addHandler(stdout_handler)

logger = logging.getLogger('miq-fedi')
logger.info('Starting')
def parse_misskey_emoji(host, tx):
    emojis = []
    for emoji in MISSKEY_EMOJI_REGEX.findall(tx):
        h = emoji[1] or host
        if h == '.':
            h = host
        e = eStore.get(h, emoji[0])
        if e:
            emojis.append(e)
    return emojis

def remove_mentions(text, mymention):
    mentions = sorted(re.findall(r'(@[a-zA-Z0-9_@\.]+)', text), key=lambda x: len(x), reverse=True)

    for m in mentions:
        if m == mymention:
            continue
        else:
            text = text.replace(m, '')
    
    return text

def draw_text(im, ofs, string, font='fonts/MPLUSRounded1c-Regular.ttf', size=16, color=(0,0,0,255), split_len=None, padding=4, auto_expand=False, emojis: list = [], disable_dot_wrap=False):
    
    draw = ImageDraw.Draw(im)
    fontObj = ImageFont.truetype(font, size=size)

    # 改行、句読点(。、.,)で分割した後にさらにワードラップを行う
    pure_lines = []
    pos = 0
    l = ''

    if not disable_dot_wrap:
        for char in string:
            if char == '\n':
                pure_lines.append(l)
                l = ''
                pos += 1
            elif char == '、' or char == ',':
                pure_lines.append(l + ('、' if char == '、' else ','))
                l = ''
                pos += 1
            elif char == '。' or char == '.':
                pure_lines.append(l + ('。' if char == '。' else '.'))
                l = ''
                pos += 1
            else:
                l += char
                pos += 1

        if l:
            pure_lines.append(l)
    else:
        pure_lines = string.split('\n')

    lines = []

    for line in pure_lines:
        lines.extend(textwrap.wrap(line, width=split_len))
    
    dy = 0

    draw_lines = []


    # 計算
    for line in lines:
        tsize = fontObj.getsize(line)

        ofs_y = ofs[1] + dy
        t_height = tsize[1]

        x = int(ofs[0] - (tsize[0]/2))
        #draw.text((x, ofs_y), t, font=fontObj, fill=color)
        draw_lines.append((x, ofs_y, line))
        ofs_y += t_height + padding
        dy += t_height + padding
    
    # 描画
    adj_y = -30 * (len(draw_lines)-1)
    for dl in draw_lines:
        with Pilmoji(im) as p:
            p.text((dl[0], (adj_y + dl[1])), dl[2], font=fontObj, fill=color, emojis=emojis, emoji_position_offset=(-4, 4))

    real_y = ofs[1] + adj_y + dy

    return (0, dy, real_y)
    

receivedNotes = set()

async def on_post_note(note):
    pass

async def on_mention(note):
    # HTLとGTLを監視している都合上重複する恐れがあるため
    if note['id'] in receivedNotes:
        return

    receivedNotes.add(note['id'])

    command = False

    childLogger = logger.getChild(note["id"])

    forceRun = '/make' in note['text']
    if forceRun:
        childLogger.info('forceRun enabled')

    # 他のメンション取り除く
    split_text = note['text'].split(' ')
    new_st = []

    note['text'] = remove_mentions(note['text'], ACCT)
    
    if (note['text'].strip() == '') and (not forceRun):
        childLogger.info('text is empty, ignoring')
        return
 
    try:
        content = note['text'].strip().split(' ', 1)[1].strip()
        command = True
    except IndexError:
        logger.getChild(f'{note["id"]}').info('no command found, ignoring')
        pass
    
    # メンションだけされた？
    if note.get('reply'):

        reply_note = note['reply']

        # ボットの投稿への返信の場合は応答しない
        if reply_note['user']['id'] == MY_ID:
            childLogger.info('this is reply to myself, ignoring')
            return

        reply_note['text'] = remove_mentions(reply_note['text'], None)

        if not reply_note['text'].strip():
            childLogger.info('reply text is empty, ignoring')
            return

        if reply_note['cw']:
            reply_note['text'] = reply_note['cw'] + '\n' + reply_note['text']

        username = note["user"]["name"] or note["user"]["username"]
        
        target_user = msk.users_show(reply_note['user']['id'])

        if '#noquote' in target_user.get('description', ''):
            childLogger.info(f'{reply_note["user"]["id"]} does not allow quoting, rejecting')
            msk.notes_create(text='このユーザーは引用を許可していません\nThis user does not allow quoting.', reply_id=note['id'])
            return

        if not (reply_note['visibility'] in ['public', 'home']):
            childLogger.info('visibility is not public, rejecting')
            msk.notes_create(text='この投稿はプライベートであるため、処理できません。\nThis post is private and cannot be processed.', reply_id=note['id'])
            return

        # 引用する
        img = BASE_WHITE_IMAGE.copy()
        # アイコン画像ダウンロード
        if not reply_note['user'].get('avatarUrl'):
            childLogger.info('user has no avatar, rejecting')
            msk.notes_create(text='アイコン画像がないので作れません\nWe can\'t continue because user has no avatar.', reply_id=note['id'])
            return
        
        childLogger.info('downloading avatar image( ' + reply_note['user']['avatarUrl'] + ' )')

        async with session.get(reply_note['user']['avatarUrl']) as resp:
            if resp.status != 200:
                msk.notes_create(text='アイコン画像ダウンロードに失敗しました\nFailed to download avatar image.', reply_id=note['id'])
                return
            avatar = await resp.read()
        

        childLogger.info('avatar image downloaded')
        childLogger.info('generating image')

        icon = Image.open(BytesIO(avatar))
        icon = icon.resize((720, 720), Image.ANTIALIAS)
        icon = icon.convert('L') # グレースケール変換
        icon_filtered = ImageEnhance.Brightness(icon)

        img.paste(icon_filtered.enhance(0.7), (0,0))

        # 黒グラデ合成
        img.paste(BASE_GRADATION_IMAGE, (0,0), BASE_GRADATION_IMAGE)

        # テキスト合成
        tx = ImageDraw.Draw(img)

        base_x = 890

        font_path = FONT_FILE

        if '%serif' in note['text']:
            font_path = FONT_FILE_SERIF
        elif '%pop' in note['text']:
            font_path = FONT_FILE_POP
        elif '%oldjp' in note['text']:
            font_path = FONT_FILE_OLD_JAPANESE

        # 文章描画
        emojis = parse_misskey_emoji(config.MISSKEY_INSTANCE, reply_note['text'])
        tsize_t = draw_text(img, (base_x, 270), note['reply']['text'], font=font_path, size=45, color=(255,255,255,255), split_len=16, auto_expand=True, emojis=emojis)

        # 名前描画
        uname = reply_note['user']['name'] or reply_note['user']['username']
        name_y = tsize_t[2] + 40
        user_emojis = parse_misskey_emoji(config.MISSKEY_INSTANCE, uname)
        tsize_name = draw_text(img, (base_x, name_y), uname, font=font_path, size=25, color=(255,255,255,255), split_len=25, emojis=user_emojis, disable_dot_wrap=True)
        
        # ID描画
        id = reply_note['user']['username']
        id_y = name_y + tsize_name[1] + 4
        tsize_id = draw_text(img, (base_x, id_y), f'(@{id}@{reply_note["user"]["host"] or config.MISSKEY_INSTANCE})', font=font_path, size=18, color=(180,180,180,255), split_len=45, disable_dot_wrap=True)

        # クレジット
        tx.text((980, 694), '<Make it a quote for Fedi> by CyberRex', font=MPLUS_FONT_16, fill=(120,120,120,255))

        childLogger.info('image generated')


        # ドライブにアップロード
        childLogger.info('uploading image')
        try:
            data = BytesIO()
            img.save(data, format='JPEG')
            data.seek(0)
            for i in range(5):
                try:
                    f = msk.drive_files_create(file=data, name=f'{datetime.datetime.utcnow().timestamp()}.jpg')
                    msk.drive_files_update(file_id=f['id'], comment=f'"{reply_note["text"][:400]}" —{reply_note["user"]["name"]}')
                except:
                    childLogger.info('upload failed, retrying (attempt ' + str(i) + ')')
                    continue
                break
            else:
                childLogger.error('upload failed')
                raise Exception('Image upload failed.')
        except Exception as e:
            childLogger.error('upload failed')
            childLogger.error(traceback.format_exc())
            if 'INTERNAL_ERROR' in str(e):
                msk.notes_create('Internal Error occured in Misskey!', reply_id=note['id'])
                return
            if 'RATE_LIMIT_EXCEEDED' in str(e):
                msk.notes_create('利用殺到による一時的なAPI制限が発生しました。しばらく時間を置いてから再度お試しください。\nA temporary API restriction has occurred due to overwhelming usage. Please wait for a while and try again.', reply_id=note['id'])
                return
            if 'YOU_HAVE_BEEN_BLOCKED' in str(e):
                msk.notes_create(f'@{note["user"]["username"]}@{note["user"]["host"] or config.MISSKEY_INSTANCE}\n引用元のユーザーからブロックされています。\nI am blocked by the user who posted the original post.', reply_id=note['id'])
                return
            msk.notes_create('画像アップロードに失敗しました\nFailed to upload image.\n```plaintext\n' + traceback.format_exc() + '\n```', reply_id=note['id'])
            return
        
        childLogger.info('image uploaded')
        childLogger.info('posting')

        try:
            msk.notes_create(text='.', file_ids=[f['id']], reply_id=note['id'])
        except Exception as e:
            childLogger.error('post failed')
            childLogger.error(traceback.format_exc())
            return

        childLogger.info('Finshed')

        return


    if command:

        if content == 'ping':

            postdate = datetime.datetime.fromisoformat(note['createdAt'][:-1]).timestamp()
            nowdate = datetime.datetime.utcnow().timestamp()
            sa = nowdate - postdate
            text = f'{sa*1000:.2f}ms'
            msk.notes_create(text=text, reply_id=note['id'])

            

async def on_followed(user):
    try:
        msk.following_create(user['id'])
    except:
        pass

async def main():

    logger.info(f'Connecting to {config.MISSKEY_INSTANCE}...')
    async with websockets.connect(WS_URL) as ws:
        reconnect_counter = 0
        logger.info(f'Connected to {config.MISSKEY_INSTANCE}')
        logger.info('Attemping to watching timeline...')
        p = {
            'type': 'connect',
            'body': {
                'channel': 'globalTimeline',
                'id': 'GTL1'
            }
        }
        await ws.send(json.dumps(p))
        p = {
            'type': 'connect',
            'body': {
                'channel': 'homeTimeline',
                'id': 'HTL1'
            }
        }
        await ws.send(json.dumps(p))
        p = {
            'type': 'connect',
            'body': {
                'channel': 'main'
            }
        }
        await ws.send(json.dumps(p))
        
        logger.info('Now watching timeline...')
        while True:
            data = await ws.recv()
            j = json.loads(data)
            # print(j)

            if j['type'] == 'channel':

                if j['body']['type'] == 'note':
                    note = j['body']['body']
                    try:
                        await on_post_note(note)
                    except Exception as e:
                        print(traceback.format_exc())
                        logger.error(traceback.format_exc())
                        continue

                if j['body']['type'] == 'mention':
                    note = j['body']['body']
                    try:
                        await on_mention(note)
                    except Exception as e:
                        print(traceback.format_exc())
                        logger.error(traceback.format_exc())
                        continue

                if j['body']['type'] == 'followed':
                    try:
                        await on_followed(j['body']['body'])
                    except Exception as e:
                        print(traceback.format_exc())
                        logger.error(traceback.format_exc())
                        continue
                

reconnect_counter = 0

while True:
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        break
    except:
        time.sleep(10)
        reconnect_counter += 1
        logger.warning('Disconnected from WebSocket. Reconnecting...')
        if reconnect_counter > 10:
            logger.critical('Too many reconnects. Exiting.')
            sys.exit(1)
        continue