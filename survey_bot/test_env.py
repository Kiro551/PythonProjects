import os

print("1. Текущая папка:", os.getcwd())

env_path = os.path.join(os.getcwd(), '.env')
print("2. Ожидаемый путь к файлу:", env_path)
print("3. Файл существует?", os.path.exists(env_path))

if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
        print("4. Содержимое файла (в кавычках, чтобы видеть пробелы):")
        print(repr(content))
else:
    print("4. Файл .env НЕ НАЙДЕН!")
    # Попробуем найти любые файлы, похожие на .env
    import glob
    print("   Возможно, файл называется иначе. Вот что есть в папке:")
    for file in glob.glob("*env*"):
        print("   -", file)

print("5. Проверяем, видит ли Python переменную BOT_TOKEN:", os.getenv('BOT_TOKEN'))