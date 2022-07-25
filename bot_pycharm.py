import telebot
import requests
from api_pycharm import stats_for_bot

TOKEN = '1463478134:AAHjbKvKgxnzqtZEq2Pt3-e_sCmGXuzauBg'
bot = telebot.TeleBot(TOKEN)

data = {}


@bot.message_handler(func=lambda msg: 'привет' in msg.text.lower())
@bot.message_handler(commands=['start'])
def ask_web_id(initial_message):
    """
    Запрашивает web_id в ответ на первое сообщение пользователя.
    :param initial_message: первое сообщение пользователя
    :return: None
    """
    msg_text = '''Привет! Я бот для ТикТока.\nЧтобы начать, мне нужен \
специальный код, который обновляется раз в два часа. \nЧтобы его получить, \
зайди на сайт www.tiktok.com с компьютера, нажми Ctrl+Shift+i, в \
открывшемся окне выбери Application — Cookies и найди строку s_v_web_id. \n\
Скопируй код из второго столбца (начинается на "verify_") и отправь мне!'''
    msg = bot.send_message(initial_message.chat.id, msg_text)
    bot.register_next_step_handler(msg, ask_un)


def ask_un(msg_web_id):
    """
    Спрашивает имя пользователя для анализа.
    :param msg_web_id: валидный web_id
    :return: None
    """
    data[msg_web_id.chat.id] = [msg_web_id.text]
    msg_text = '''Теперь отправь мне имя пользователя, у которого открыты \
лайкнутые видео'''
    msg = bot.send_message(msg_web_id.chat.id, msg_text)
    bot.register_next_step_handler(msg, wait)


def wait(message):
    """
    Отправляет сообщение об ожидании и запускает обработку.
    :param message: предыдущее сообщение
    :return: None
    """
    bot.send_message(message.chat.id, 'Принял, одну секунду!')
    data[message.chat.id].append(message.text)
    process(message.chat.id)


def process(chat_id):
    """
    Вызывает обкачку и составление статистики.
    :param chat_id: айди текущего чата
    :return: None
    """
    web_id = data[chat_id][0]
    username = data[chat_id][1]

    # функция, вызывающая API и обрабатывающая результаты
    error, stats_or_message = stats_for_bot(web_id, username)
    # если произошла ошибка, то отправляем сообщение пользователю
    if error:
        bot.send_message(chat_id, stats_or_message)
    else:  # иначе обрабатываем статистику
        msg_text = f'''Ваши любимые авторы: {stats_or_message['fav_authors']} \n
Ваши любимые хештеги: {stats_or_message['fav_tags']} \n
Ваши любимые темы: {stats_or_message['fav_topics']} \n
Ваши любимые звуки: {stats_or_message['fav_sounds']}\n\n'''
        bot.send_message(chat_id, msg_text)
        if stats_or_message['wordcloud']:
            file = {'photo': open(stats_or_message['wordcloud'], 'rb')}
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendPhoto?chat_id=" +
                str(chat_id), files=file)
        new_msg = 'Чтобы проверить другого пользователя, отправь /start ещё раз'
        bot.send_message(chat_id, new_msg)


bot.polling()
