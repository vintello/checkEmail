# установка Linux

### настройка виртуального окружения Python

создаем виртуальное окружение

    python3 -m venv env

активируем виртуальное окружение и дальше работаем только с ним 

      source env/bin/activate

Далее, необходимо установить все зависимости 

      pip install -r requirements.txt

### настройка доккер

    sudo apt  install docker.io

запуск контейнера

    sudo docker run -d -p 4444:4444 -p 7900:7900 --shm-size="2g" selenium/standalone-firefox:4.21.0-20240517

остановка контейнера

    sudo docker ps

получаем айди запущенного контейнера

останавливаем контейнер по айдишке

    sudo docker stop 9f8cd62f2a71

просмотр состояния браузера в контейнере (пароль - secret)

    http://127.0.0.1:7900/

просмотр сессий контейнера

    http://127.0.0.1:4444/

### Запуск приложения

    python main.py <name_file.txt>

