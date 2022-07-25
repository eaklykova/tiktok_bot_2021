##
import re
import emoji
import string
import networkx as nx
from typing import Union, Tuple
from collections import Counter
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from pymorphy2 import MorphAnalyzer
from wordcloud import WordCloud
from TikTokApi import TikTokApi, exceptions
from networkx.algorithms.components.connected import connected_components


##
def get_liked_videos(web_id: str, username: str) -> list:
    """
    Запускает API и получает информацию о 500 последних лайкнутых видео.
    :param web_id: web_id, полученное от пользователя
    :param username: интересующий пользователь
    :return: список словарей с информацией о видео
    """
    api = TikTokApi.get_instance(custom_verifyFp=web_id)
    user = api.get_user(username)
    secUid = user['userInfo']['user']['secUid']
    liked = api.user_liked(userID=username, secUID=secUid, count=500)
    if not liked:
        raise exceptions.EmptyResponseError
    return liked


##
def get_one_vid_info(nth_vid: dict) -> dict:
    """
    Обрабатывает информацию об одном видео, полученную от API.
    :param nth_vid: словарь с полной информацией о видео
    :return: словарь с нужной информацией о видео
    """
    """
    Эта фукнция собирает информацию об одном видео.
    :param n: номер видео в списке лайкнутых
    :param liked: список лайкнутых видео
    :return: словарь с информацией об n-ном видео
    """
    # немного базовой информации
    vid_info = {'id': nth_vid['id'],
                'desc': nth_vid['desc'],
                'createTime': nth_vid['createTime']}

    # получаем информацию об авторе
    author = {}
    author_info = ['id', 'uniqueId', 'nickname', 'secUid', 'openFavorite',
                   'privateAccount', 'secret']
    for field in author_info:
        author[field] = nth_vid['author'][field]
    vid_info['author'] = author

    # получаем хештеги, если они есть
    hashtags = []
    if 'textExtra' in nth_vid:
        for tag in nth_vid['textExtra']:
            tag_info = {'hashtagId': tag['hashtagId'],
                        'hashtagName': tag['hashtagName'],
                        'type': tag['type']}
            hashtags.append(tag_info)
    vid_info['hashtags'] = hashtags

    # получаем звук
    sound = {}
    sound_info = ['id', 'title', 'duration', 'authorName', 'original', 'album']
    for field in sound_info:
        sound[field] = nth_vid['music'][field]
    vid_info['sound'] = sound

    vid_info['stats'] = nth_vid['stats']

    return vid_info


##
def get_all_vid_info(liked: list) -> dict:
    """
    Обрабатывает информацию обо всех лайкнутых видео.
    :param liked: список словарей с информацией от API
    :return: словарь вида {id видео: словарь с информацией}
    """
    all_likes_info = {}
    for vid in liked:
        vid_info = get_one_vid_info(vid)
        all_likes_info[vid_info['id']] = vid_info
    return all_likes_info


##
def get_data_for_statistics(data: dict) -> tuple:
    """
    Собирает статистику о лайкнутых пользователем видео.
    :param data: словарь с информацией о видео
    :return: статистика по авторам, тегам и т.д.
    """
    authors, tags, tagsets, sounds, non_orig_sounds, descriptions = (
        [] for i in range(6))
    # исключаем из статистики "мусорные теги"
    stops = ['fyp', 'foryou', 'foryoupage', 'рек', 'реки', 'рекомендации',
             'хочуврек', 'хочувтоп', 'топ', 'дуэт', 'duet', 'reply',
             'stitch', 'fy', 'fypシ', 'fypage', '4u']

    for vid_id in list(data.keys()):
        # только имя, отображаемое на видео
        authors.append(data[vid_id]['author']['uniqueId'])
        # хештеги (при наличии) записываем в два списка
        if data[vid_id]['hashtags']:
            taglist = [t['hashtagName'] for t in data[vid_id]['hashtags']
                       if t['hashtagName'] and t['hashtagName'] not in stops]
            tags.extend(taglist)  # общий список тегов
            tagsets.append(taglist)  # теги по видео
        # описание без хештегов
        desc = re.sub(r' ?#\S+ ?', '', data[vid_id]['desc'])
        if desc:
            descriptions.append(desc)
        # звуки в формате "автор — название звука"
        sound_name = data[vid_id]['sound']['title']
        sound = data[vid_id]['sound']['authorName'] + ' — ' + sound_name
        sounds.append(sound)
        if sound_name != 'оригинальный звук' and sound_name != 'original sound':
            non_orig_sounds.append(sound)

    # берем не-оригинальные звуки, которые встречаются чаще 1 раза
    top_sounds = [s[0] for s in Counter(non_orig_sounds).most_common(10)
                  if s[1] > 1]
    # если таких звуков нет, берем любые встретившиеся больше 1 раза
    if not top_sounds:
        top_sounds = [s[0] for s in Counter(sounds).most_common(10) if s[1] > 1]
    fav_sounds = ', '.join([s[0] for s in Counter(top_sounds).most_common(10)])
    if not fav_sounds:
        fav_sounds = 'слишком мало информации :('

    # для остальных категорий тоже минимальное кол-во = 2
    fav_authors = ', '.join([a[0] for a in Counter(authors).most_common(10)
                             if a[1] > 1])
    if not fav_authors:
        fav_authors = 'слишком мало информации :('
    fav_tags = ', '.join([t[0] for t in Counter(tags).most_common(10)
                          if t[1] > 1])
    if not fav_tags:
        fav_tags = 'слишком мало информации :('
    fav_topics = ', '.join([tp[0] for tp in Counter(
        get_fav_topics(tagsets, tags)).most_common(10) if tp[1] > 1])
    if not fav_topics:
        fav_topics = 'слишком мало информации :('

    return fav_authors, fav_tags, fav_topics, fav_sounds, descriptions


##
def to_edges(tagset: list):
    """
    Превращает набор тегов в пары ребёр
    :param tagset: набор тегов одного видео
    :return: None
    """
    it = iter(tagset)
    last = next(it)
    for current in it:
        yield last, current
        last = current


def to_graph(tagsets: list):
    """
    Создаёт граф из наборов тегов
    :param tagsets: список наборов тегов по видео
    :return: граф из наборов тегов
    """
    G = nx.Graph()
    for tagset in tagsets:
        G.add_nodes_from(tagset)
        if len(tagset) > 1:
            G.add_edges_from(to_edges(tagset))
    return G


def topic_title(topic: list, tags: list):
    """
    Выделяет самый частотный тег как название всей группы-топик
    :param topic: теги, объединенные в один топик
    :param tags: все теги, встретившиеся в лайкнутых видео
    :return: название топика
    """
    freqs = {}
    for word in topic:
        freqs[word] = Counter(tags)[word]
    return Counter(freqs).most_common(1)[0][0]


def get_fav_topics(tagsets: list, tags: list) -> list:
    """
    Общая функция выделения топиков:
    выбирает топики, содержащие больше 2 тегов;
    определяет частотность топика как общее число вхождений всех тегов топика.
    :param tagsets: список наборов тегов по видео
    :param tags: все теги, встретившиеся в лайкнутых видео
    :return: список топиков, где число вхождений топика = его частотность
    """
    G = to_graph(tagsets)
    topics = [topic for topic in list(connected_components(G))
              if len(topic) > 2]
    topic_dict = {topic_title(topic, tags): topic for topic in topics}
    fav_topics = []
    for title in list(topic_dict.keys()):
        full_freq = 0
        for tag in topic_dict[title]:
            full_freq += Counter(tags)[tag]
        # название топика столько раз, сколько встретились отдельные теги
        fav_topics.extend([title] * full_freq)
        # это неизящный, но самый простой способ,
        # позволяющий в дальнейшем избежать сортировки словаря по значению
        # и проверки длины словаря (хотим выбрать 10 самых частотных)
    return fav_topics


##
def make_wordcloud(descriptions: list) -> Union[str, bool]:
    """
    Обрабатывает описания тиктоков (приводит к нижнему регистру, очищает от
    специальных символов, токенизирует, лемматизирует) и генерирует на их
    основе облако слов (в файле .png).
    :param descriptions: список описаний лайкнутых видео
    :return: None, генерирует файл .png
    """
    if not descriptions:
        return False
    # удаляем эмодзи, приводим к нижнему регистру, токенизируем
    descs = emoji.get_emoji_regexp().sub(u'', ' '.join(descriptions))
    tokens = word_tokenize(descs.lower())

    # пунктуация и стоп-слова
    other = ['``', "\'\'", '...', '--', '–', '—',
             '«', '»', '“', '”', '’', '***', '…', '￼', '️']
    punct = string.punctuation + ''.join(other)
    blacklist = stopwords.words('english') + stopwords.words('russian') + \
        ['ответ', 'пользователь', 'такой', 'это', 'очень', 'е', 'e',
         'всё', 'весь', 'reply']

    # удаляем лишнее, лемматизируем
    words = [t.strip(punct) for t in tokens if t.strip(punct)]
    lemmas = []
    morph = MorphAnalyzer()
    for token in words:
        if re.search('[\u0400-\u04FF]', token):
            lemma = morph.parse(token)[0].normal_form
        else:
            lemma = token
        if lemma not in blacklist:
            lemmas.append(lemma)

    # создаем и сохраняем вордклауд
    try:
        wordcloud = WordCloud(
            width=525, height=375, background_color='white').generate(
            ' '.join(lemmas))
        filename = 'desc_cloud.png'
        wordcloud.to_file(filename)
        return filename
    except ValueError:
        return False


##
def stats_for_bot(web_id: str, username: str) -> Tuple[bool, Union[dict, str]]:
    """
    Общая функция, объединяющая запрос к апи и обработку полученных данных.
    :param web_id: web_id, полученное от пользователя
    :param username: интересующий пользователь
    :return: статистика для выдачи в боте
    """
    try:
        tt_data = get_all_vid_info(get_liked_videos(web_id, username))
        fav_authors, fav_tags, fav_topics, fav_sounds, descriptions = \
            get_data_for_statistics(tt_data)
        desc_cloud = make_wordcloud(descriptions)
        bot_dict = {'fav_authors': fav_authors,
                    'fav_tags': fav_tags,
                    'fav_topics': fav_topics,
                    'fav_sounds': fav_sounds,
                    'wordcloud': desc_cloud}
        return False, bot_dict
    except exceptions.TikTokNotFoundError:
        msg = 'Такого пользователя не существует, попробуй ещё раз'
        return True, msg
    except exceptions.EmptyResponseError:
        msg = 'У этого пользователя \
приватная страница, скрыты лайки или он ещё ничего не лайкнул, \
попробуй кого-то другого'
        return True, msg
    except (exceptions.JSONDecodeFailure, exceptions.TikTokCaptchaError):
        msg = 'Ой! Что-то пошло не так. Проверь, что присланный код верен, \
или повтори попытку позже'
        return True, msg


##
"""from pprint import pprint
web_id = 'verify_kqdsd94e_WG7FteTC_IVy3_4YkB_BnwO_5aIucFZqUz0d'
username = 'amkeif'
bot_dict = stats_for_bot(web_id, username)
pprint(bot_dict)
"""
