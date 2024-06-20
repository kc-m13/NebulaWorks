from selenium.webdriver.support.ui import Select
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import os
import glob
import shutil
import pickle
import logging

def save_obj(obj, name):
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def load_obj(name):
    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)

def setup_logger():
    logging.basicConfig(filename='scraping.log', level=logging.INFO,
                        format='%(asctime)s:%(levelname)s:%(message)s')

def setup_driver(download_dir):
    options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=options)
    return driver

def main():
    setup_logger()
    logging.info("Script started")

    try:
        dict_download = load_obj('to_download')
    except (OSError, IOError):
        dict_download = {}
        save_obj(dict_download, 'to_download')

    BASE_DIR = os.getcwd()
    logging.info(f"Base directory: {BASE_DIR}")

   
    driver = webdriver.Chrome()

    driver.get("https://soilhealth.dac.gov.in/HealthCard/HealthCard/HealthCardPNew")

    state_index = 20
    try:
        state_select = Select(driver.find_element(By.ID, 'State_cd2'))
        state_select.options[state_index].click()
        STATE_DIR = os.path.join(BASE_DIR, state_select.options[state_index].text)
        os.makedirs(STATE_DIR, exist_ok=True)

        district_select = Select(driver.find_element(By.ID, 'Dist_cd2'))

        for dist in district_select.options:
            if dist.text == '--SELECT--':
                continue

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'Sub_dis2')))
            subdistrict_select = Select(driver.find_element(By.ID, 'Sub_dis2'))
            time.sleep(3)
            dist.click()

            for sub_dist in subdistrict_select.options:
                if sub_dist.text == '--SELECT--':
                    continue

                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'village_cd2')))
                village_select = Select(driver.find_element(By.ID, 'village_cd2'))
                time.sleep(3)
                sub_dist.click()

                for each_village in village_select.options:
                    if each_village.text == '--SELECT--':
                        continue

                    VILLAGE_DIR = os.path.join(STATE_DIR, dist.text, sub_dist.text, each_village.text)
                    os.makedirs(VILLAGE_DIR, exist_ok=True)
                    logging.info(f"Processing: {dist.text} - {sub_dist.text} - {each_village.text}")

                    if VILLAGE_DIR in dict_download and dict_download[VILLAGE_DIR] == 1:
                        continue

                    time.sleep(2)
                    each_village.click()
                    driver.execute_script("SearchIngrid();")

                    try:
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'MainTable')))
                        table_of_records = driver.find_element(By.ID, 'MainTable')
                        rows = table_of_records.find_elements(By.TAG_NAME, "tr")
                        if not rows:
                            logging.info('No records in this village')
                            continue

                        while True:
                            time.sleep(4)
                            try:
                                table_of_records = driver.find_element(By.ID, 'MainTable')
                                rows = table_of_records.find_elements(By.TAG_NAME, "tr")

                                for row in rows:
                                    cols = row.find_elements(By.TAG_NAME, "td")
                                    if len(cols) <= 1:
                                        continue

                                    logging.info([col.text for col in cols])
                                    cols[9].click()
                                    time.sleep(22)

                                    iframe = driver.find_elements(By.TAG_NAME, 'iframe')[0]
                                    driver.switch_to.frame(iframe)
                                    butt = driver.find_element(By.ID, 'ReportViewer1_ctl05_ctl04_ctl00_Menu')
                                    options = butt.find_elements(By.TAG_NAME, 'a')
                                    driver.execute_script(options[7].get_attribute('onclick'))

                                    num_of_tabs = len(driver.window_handles)
                                    driver.switch_to.default_content()
                                    time.sleep(2)
                                    original_window_list = driver.window_handles
                                    original_window = original_window_list[0]

                                    for handle in original_window_list:
                                        if handle != original_window:
                                            driver.switch_to.window(handle)
                                            driver.close()

                                    driver.switch_to.window(original_window)

                            except Exception as e:
                                logging.error(f"Row processing error: {e}")
                                break

                            try:
                                driver.find_element(By.LINK_TEXT, 'Next >').click()
                            except:
                                dict_download[VILLAGE_DIR] = 1
                                save_obj(dict_download, 'to_download')
                                for file in glob.glob("*.xml"):
                                    shutil.move(file, VILLAGE_DIR)
                                break

                    except Exception as e:
                        logging.error(f"Error processing table: {e}")
                        continue

    finally:
        driver.quit()
        logging.info("Script finished")

if __name__ == "__main__":
    main()

                    
                    



