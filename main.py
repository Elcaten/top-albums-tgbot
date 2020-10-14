import json
import os
import random
import traceback
from random import choice

import firebase_admin
import spotipy
import telegram
from firebase_admin import credentials, db
from pymaybe import Nothing, maybe
from spotipy.oauth2 import SpotifyClientCredentials
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardMarkup)
from telegram.ext import (CallbackQueryHandler,
                          CommandHandler, Filters, MessageHandler, Updater)

bot = telegram.Bot(token=os.environ["TELEGRAM_TOKEN"])
firebase_admin.initialize_app(
    credentials.ApplicationDefault(), {'databaseURL': 'https://top-albums-ever.firebaseio.com'})
spotify = spotipy.Spotify(
    client_credentials_manager=SpotifyClientCredentials())


def hasValue(value, default):
    if value is None or type(value) == Nothing:
        return default
    else:
        return value


def processCallback(callback_query):
    queryData = maybe(json.loads(callback_query["data"]))
    button_type = queryData["type"]
    liked = queryData["liked"]
    albumNum = queryData["album"]
    message_id = queryData["message_id"]

    if button_type == 'refresh':
        sendRandomAlbum(callback_query.from_user.id)
    else:
        likedRef = db.reference(
            f'rolling-stones-2003/users/{callback_query.from_user.id}/liked/{albumNum}')
        dislikedRef = db.reference(
            f'rolling-stones-2003/users/{callback_query.from_user.id}/disliked/{albumNum}')

        if liked == True:
            likedRef.set(True)
            dislikedRef.delete()
        else:
            dislikedRef.set(True)
            likedRef.delete()
            bot.delete_message(callback_query.from_user.id, str(message_id))

    bot.answer_callback_query(callback_query.id)


def sendRandomAlbum(chat_id):
    userData = db.reference(f'rolling-stones-2003/users/{chat_id}').get()
    liked = list(hasValue(maybe(userData)['liked'].keys(), []))
    disliked = list(hasValue(maybe(userData)['disliked'].keys(), []))
    randomAlbumNumber = choice(
        [i for i in range(1, 500) if i not in liked + disliked])

    fbAlbum = db.reference(
        f'rolling-stones-2003/top-500-albums/{randomAlbumNumber}').get()

    searchResults = spotify.search(
        q=f'album:{fbAlbum["Album"]} artist:{fbAlbum["Artist"]} year:{fbAlbum["Year"]}',  type="album")
    spotifyAlbum = maybe(searchResults)['albums']['items'][0]

    artistName = spotifyAlbum['artists'][0]['name']
    image = spotifyAlbum['images'][0]['url']
    albumName = spotifyAlbum['name']
    spotifyLink = spotifyAlbum['external_urls']['spotify']
    year = spotifyAlbum['release_date'][0:4]

    if spotifyAlbum is None or type(spotifyAlbum) == Nothing:
        bot.sendMessage(chat_id=chat_id, text=json.dumps(fbAlbum))
    else:
        message = bot.send_message(chat_id=chat_id,
                                   text=f'<a href="{image}">&#8205;</a>\n<b>{albumName}</b> ({year})\nby {artistName}\n{spotifyLink}',
                                   parse_mode="html")
        likedCallbackData = {
            'liked': True,
            'album': randomAlbumNumber,
            'message_id': message.message_id
        }
        refreshCallbakData = {
            'type': 'refresh'
        }
        dislikedCallbackData = {
            'liked': False,
            'album': randomAlbumNumber,
            'message_id': message.message_id
        }
        buttons = [[
            InlineKeyboardButton(
                '👍',  callback_data=json.dumps(likedCallbackData)),
            InlineKeyboardButton(
                '🔄',  callback_data=json.dumps(refreshCallbakData)),
            InlineKeyboardButton(
                '👎',  callback_data=json.dumps(dislikedCallbackData))
        ]]
        keyboard = InlineKeyboardMarkup(buttons)
        bot.editMessageReplyMarkup(
            chat_id, message.message_id, reply_markup=keyboard)


def webhook(request):
    if request.method == "POST":
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        if update.callback_query:
            processCallback(update.callback_query)
        else:
            sendRandomAlbum(update.message.chat.id)
    return "ok"


# def msgCallback(bot, update): return sendRandomAlbum(update.message.chat.id)
# def queryCallback(bot, update): return processCallback(update.callback_query)
# updater = Updater(os.environ["TELEGRAM_TOKEN"])
# dp = updater.dispatcher
# dp.add_handler(MessageHandler(Filters.text, msgCallback))
# dp.add_handler(CallbackQueryHandler(queryCallback))

# updater.start_polling()
# updater.idle()
