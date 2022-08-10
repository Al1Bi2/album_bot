from dataclasses import dataclass

import telebot
import vk_api
from telebot import types

import config


@dataclass
class Album:
    data: dict
    num: int
    last_message: int = None
    offset: int = 0


def check_size(num, size, old):
    change = 1
    if num < 0:
        num = 0
    if num >= size:
        num = size - 1
    if num == old:
        change = 0
    return change, num


def gen_albums(vk):
    vk_albums_list = vk.photos.getAlbums(owner_id=config.GROUP).get('items')
    n_t = 0
    albums_list = []
    for album in vk_albums_list:
        temp = Album(album, n_t)
        albums_list.append(temp)
        n_t = n_t + 1
    return albums_list


def main():
    bot = telebot.TeleBot(config.BOT, parse_mode=None)
    vk_session = vk_api.VkApi(config.LOGIN, config.PASSWORD)

    try:
        vk_session.auth(token_only=True)
    except vk_api.AuthError as err:
        print(err)
        return
    vk = vk_session.get_api()

    albums_list = gen_albums(vk)
    def draw_heart(like):
        if like:
            return "❤️"
        else:
            return "🤍"
    def draw_arrows(album_num,is_liked):
        markup = types.InlineKeyboardMarkup()
        markup.row_width = 5
        markup.add(types.InlineKeyboardButton("<<", callback_data="-9999 " + str(album_num)),
                   types.InlineKeyboardButton("<", callback_data="-1 " + str(album_num)),
                   types.InlineKeyboardButton(draw_heart(is_liked), callback_data="l"),
        types.InlineKeyboardButton(">", callback_data="1 " + str(album_num)),
        types.InlineKeyboardButton(">>", callback_data="9999 " + str(album_num)))
        return markup

    def draw_album_list():
        albums_list_f = gen_albums(vk)
        markup = types.ReplyKeyboardMarkup(selective=True)
        for album in albums_list_f:
            title = album.data['title']
            markup.add(types.KeyboardButton(title))
        return markup

    @bot.callback_query_handler(func=lambda call: True)
    def callback_query(call):
        command = call.data.split()
        if command[0] == 'l':
            print("Like!")
        else:
            album_struct = albums_list[int(command[1])]
            print(album_struct.data)
            old = album_struct.offset
            change, album_struct.offset = check_size(album_struct.offset + int(command[0]),
                                                     album_struct.data['size'],
                                                     album_struct.offset)
            if change:
                album = album_struct.data
                photo = vk.photos.get(owner_id=album['owner_id'],
                                      album_id=album['id'],
                                      photo_sizes=1,
                                      rev=1,
                                      extended=1,
                                      offset=album_struct.offset,
                                      count=1)
                is_liked=photo['items'][0]['likes']['user_likes']
                bot.edit_message_media(types.InputMediaPhoto(photo['items'][0]['sizes'][-5]['url']),
                                       call.message.chat.id, call.message.id,
                                       reply_markup=draw_arrows(album_struct.num,is_liked))

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        markup = draw_album_list()
        bot.reply_to(message, "Добро пожаловать в бот для любимых альбомов!", reply_markup=markup)

    @bot.message_handler(commands=['album'])
    def send_welcome2(message):
        markup = draw_album_list()
        bot.send_message(message.chat.id, 'Список альбомов', reply_markup=markup)

    @bot.message_handler(content_types='text')
    def message_reply(message):
        for album_struct in albums_list:
            album = album_struct.data
            if message.text == album['title']:

                url = vk.photos.get(owner_id=album['owner_id'],
                                    album_id=album['id'],
                                    photo_sizes=1,
                                    rev=1,
                                    offset=album_struct.offset,
                                    count=1)['items'][0]['sizes'][2]['url']
                msg = bot.send_photo(message.chat.id, url, reply_to_message_id=message.id,
                                     reply_markup=draw_arrows(album_struct.num,is_liked))
                # print(msg)
                if album_struct.last_message != None:
                    bot.delete_message(album_struct.last_message.chat.id, album_struct.last_message.id)
                album_struct.last_message = msg

    bot.infinity_polling()


if __name__ == '__main__':
    main()
