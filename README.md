# tiktok_bot

**Авторы:** Алла Горбунова, Елизавета Клыкова

**Суть проекта:** телеграм-бот, который получает юзернейм, собирает данные о понравившихся пользователю видео и формулирует интересные ему темы посредством построения графа совместной встречаемости тегов и выделения из них связных компонент. Пользователю возвращается эта информация, а также топ-10 любимых авторов, звуков и хештегов, плюс облако слов из описаний к видео.

**Используемые инструменты:** Telegram API, TikTok API, морфологические парсеры (pymorphy, nltk), модуль networkx для работы с графами.
