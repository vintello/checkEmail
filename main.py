#https://dev.to/arvind_choudhary/selenium-grid-setup-with-docker-59cn
import datetime
import os
import app_logger
from errors import TooFequently
import re
import random
import time
import requests
import json
import argparse
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = app_logger.get_logger(__name__)


def _tranform_into_email(name:str) ->list:
    '''
    трансформируем имя в емейл
    :param name: имя
    :return:
        список возможных емейлов в порядке приоритетности
    '''
    logger.info(f"Продавец: {name}")
    res = set()
    name_set = set()
    name = name.lower()
    name_set.add(name)
    if "_" in name:
        name = name.replace("_", ".")
        name_set.add(name)
    for name in name_set:
        res.add(f"{name}@gmail.com")
        res.add(f"{name}@hotmail.com")
    return res


def _check_email(driver, emails:list)->bool:
    logger.info("список емейл для проверки : {0}".format(", ".join(emails)))
    result = None
    for em in emails:
        logger.info("проверяем {0}".format(em))
        driver.delete_all_cookies()
        driver.get("https://www.tori.fi/auth/login")
        driver.implicitly_wait(10)
        time.sleep(random.randint(1,3))
        driver.maximize_window()
        elem = driver.find_element(By.XPATH, "//input[@id='email']")
        elem.clear()
        elem.send_keys(em)
        elem.send_keys(Keys.RETURN)
        driver.implicitly_wait(10)
        time.sleep(random.randint(1, 3))
        try:
            elem = driver.find_element(By.XPATH, "//input[@id='accept_terms']")
        except NoSuchElementException as ex:
            logger.debug("галочки нет. скорее всего реальный аккаунт")
            # галочки нет. скорее всего реальный аккаунт
            # проверяем наличие поля для ввода пароля
            try:
                elem = driver.find_element(By.XPATH, "//input[@id='password']")
                result = em
                logger.info(f"email {em} реальный")
                break
            except NoSuchElementException as ex:
                # проверяем есть ли предупреждение что часто пытаемся залогиниться
                ser = False
                try:
                    ser = WebDriverWait(driver, 10).until(EC.visibility_of_element_located(
                        (By.XPATH, "//div[contains(@class, 'ModalDialog')]"))).get_attribute(
                        "innerHTML").split(">")
                    logger.warning("предупреждение от системы о частом логине")

                    #да, такое есть сообщение и надо поспать
                    raise TooFequently("очень часто")
                except TimeoutException as ex:
                    logger.exception("неожиданная ошибка")
                    #вообще ничего не понятно. требуется ручное вмешательство
                    pass
    return result


def analyse_chunk_data(chunk_data, driver) ->None:
    '''
    анализируем блок информации из входящего файла
    :param chunk_data: список строк
    :return:
    '''
    valid_email = None
    for num, row in enumerate(chunk_data):
        if re.findall(r"продавец", row, flags=re.I|re.U):
            name = re.findall(r":(.*?)$", row)
            if name:
                name = name[0].strip()
                name_2_emails = _tranform_into_email(name)
                counter = 0
                #проверяем 3 раза и потом просто игнорируем
                while counter < 3:
                    try:
                        valid_email = _check_email(driver, name_2_emails)
                        counter = 4
                    except TooFequently as ex:
                        time_sleep = random.randint(60, 180)
                        logger.info(f"уходим в спячку на {time_sleep} сек.")
                        time.sleep(time_sleep)
                    except Exception as ex:
                        logger.exception("sssss")
                        pass
                    counter += 1
                if valid_email:
                    break
    return valid_email


def upload_result_file(file_name, chunk_data, email):
    '''
    добавляем в выходной файл только успешно опознанные емейлы в качестве продавца
    :param file_name: название выходного файла
    :param chunk_data: блок данных
    :param email: емейл, которм заменяем продавща
    :return:
    '''
    with open(file_name, "a+") as fil:
        for row in chunk_data:
            if re.findall(r"продавец", row, flags=re.I|re.U):
                row = re.sub(r":(.*?)$",": "+email, row)
            fil.write(row)
        fil.write("="*50)
        fil.write("\n")


def main(input_file_name):
    """
    основная функция. читаем файл до разделителя и формируем блок данных
    разделителем считается строка из знаков равно длинной 50 символов
    :param input_file_name: название файла источника
    :return:
    """
    driver = webdriver.Remote(
        command_executor='http://127.0.0.1:4444/wd/hub',
        options=webdriver.FirefoxOptions()
    )
    dt_curr = datetime.datetime.now()
    parsed_file_name = os.path.splitext(input_file_name)
    out_file_name = "{0}_{1}{2}".format(parsed_file_name[0], dt_curr.strftime("%m%d%Y_%H%M%S"),parsed_file_name[1])
    total_count = 0
    valid_count = 0
    try:
        chunk_data = None
        with open(input_file_name, 'r') as in_f:
            logger.debug(f"стартуем чтение файла {input_file_name}")
            chunk_data_list= []
            chunk_data = []
            while True:
                line = in_f.readline()
                if not line:
                    logger.debug(f"файл {input_file_name} закончился")
                    break
                elif "=="*20 in line:
                    total_count += 1
                    chunk_data_list.append(chunk_data)
                    valid_email = analyse_chunk_data(chunk_data, driver)
                    #valid_email = "ddddddd@ddd.com" # для проверки записи результата
                    if valid_email:
                        valid_count +=0
                        upload_result_file(out_file_name, chunk_data, valid_email)
                        time.sleep(random.randint(20, 60))
                    chunk_data = []
                else:
                    chunk_data.append(line)
    except Exception as ex:
        logger.exception("DDDDDDDDDDD")
    finally:
        driver.quit()
        logger.info(f"Всего было блоков с данными {total_count} из них успешно распознано {valid_count}")

def clear_sessions(session_id=None):
    """
    Here we query and delete orphan sessions
    docs: https://www.selenium.dev/documentation/grid/advanced_features/endpoints/
    :return: None
    """
    url = "http://127.0.0.1:4444"
    if not session_id:
        # delete all sessions
        r = requests.get("{}/status".format(url))
        data = json.loads(r.text)
        for node in data['value']['nodes']:
            for slot in node['slots']:
                if slot['session']:
                    id = slot['session']['sessionId']
                    print(f"delete session {id}")
                    r = requests.delete("{}/session/{}".format(url, id))
    else:
        # delete session from params
        r = requests.delete("{}/session/{}".format(url, session_id))



if __name__ == '__main__':
    logger.info(" "*50)
    descr = 'Программа просматривает структурированный файл информации от сайта www.tori.fi \n'
    descr += "в структурированном файле находит строку Продавец: <name> \n"
    descr += "на основании имени производит генерацию возможных емейлов и проверяет зарегистрирован ли пользователь на сайте \n"
    descr += "если такой пользователь есть,- то меняет имя пользователя на его емейл"
    parser = argparse.ArgumentParser(
        prog='CheckEmail',
        description= descr,
        epilog='2024 (с)')
    parser.add_argument('filename')
    args = parser.parse_args()
    input_file_name = args.filename

    clear_sessions()
    main(input_file_name)
    logger.info(" " * 50)

