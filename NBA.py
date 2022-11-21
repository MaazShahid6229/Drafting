import time
import logging
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# Setting Google Sheet
import pygsheets
client = pygsheets.authorize(service_account_file="drafting-scrape.json")


# Chrome Option
chrome_options = Options()
chrome_options.headless = True
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument("start-maximized")
chrome_options.add_argument("window-size=1920,1080")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('disable-infobars')
chrome_options.add_argument('--disable-extensions')
chrome_options.add_argument("--log-level=3")

# disable the banner "Chrome is being controlled by automated test software"
chrome_options.add_experimental_option("useAutomationExtension", False)
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

# Setting Chrome Extension
chrome_driver_path = "chromedriver.exe"

# Operation start date
now = datetime.now()
logging.basicConfig(filename=f"Logs/NBA.log", filemode='w', level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
current_time = now.strftime("%H:%M:%S")
logging.info(f"Operation Start at {current_time}")

# Constant
H = 2

NBA_GAME_HEADERS = ["Game", "DK Home SGP ML", "DK Home non sgp ML", "Difference"]
NBA_GAME_DATA = []


# SGP Call
def sgp_call(link, driver):
    sgp = {}
    try:
        driver.get(link)
        driver.implicitly_wait(10)
        time.sleep(5)
        try:
            driver.find_element(By.XPATH, "//button[text()='Game Lines']").click()
            header_elements = driver.find_elements(By.CLASS_NAME,  "rj-market-collapsible")
            for header in header_elements:
                header_name = header.find_element(By.CLASS_NAME, "rj-market__header").text
                if header_name == "Game":
                    i = 3
                    player_names = header.find_elements(By.XPATH, "//p[contains(@class, 'rj-market__label--row')]")
                    for player_name in player_names:
                        sgp[player_name.text] = driver.find_element(By.XPATH, f"/html/body/div[2]/div[2]/section/section[2]/section/section/div[2]/sb-comp/div/div/div[2]/sb-lazy-render/div/div[1]/div/div/div/button[{i}]/span[2]").text
                        i = i+3
        except Exception as e:
            print("No GAME SGP Available for this game")
            logging.info(f"No Passing Props SGP Available for this game for Error: {e}")

    except Exception as e:
        print("Error in SGP Call")
        logging.info(f"Error in SGP Call game for Error: {e}")
    return sgp


# Non SGP Call
def non_sgp_call(link, driver):
    non_sgp_dict = {}
    try:
        link= link.replace("sgpmode=true", "category=odds&subcategory=game-lines")
        driver.get(link)
        driver.implicitly_wait(10)
        player_names = driver.find_elements(By.CLASS_NAME, "event-cell__name-text")
        i = 1
        for player_name in player_names:
            non_sgp_dict[player_name.text] = driver.find_element(By.XPATH, f"/html/body/div[2]/div[2]/section/section[2]/section/section/div[2]/div[2]/div[1]/div[2]/div[1]/div/table/tbody/tr[{i}]/td[3]/div/div/div/div/div[2]/span").text
            i = i + 1
    except Exception as e:
        print("No GAME Non SGP Available for this game")
        logging.info(f"No GAME Non SGP Available for this game, Error is: {e}")
    return non_sgp_dict


def NHL_GAME(sgp, non_sgp, link):
    global H
    for s in sgp.items():
        lis = []
        try:
            ml_non_sgp = non_sgp[s[0]]
            game_name = f'=HYPERLINK("{link}", "{s[0].title()}")'
            lis.append(game_name)
            lis.append(s[1])
            lis.append(ml_non_sgp)
            lis.append(f"=SIGN(B{H} - C{H}) * MOD(ABS(B{H} - C{H}), 100)")
            NBA_GAME_DATA .append(lis)
            H = H + 1
        except Exception as e:
            continue


# Unique List Function
def unique_list(lis):
    new_set = set(lis)
    return list(new_set)


# Get Matches links from main page
def get_match_links(game_link, driver):
    driver.get(game_link)
    logging.info(f"Redirect to Page: {game_link}")
    print(f"Redirect to Page: {game_link}")
    driver.implicitly_wait(10)
    match_links = driver.find_elements(By.CLASS_NAME, "toggle-sgp-badge__nav-link")
    match_links_list = [x.get_attribute("href") for x in match_links]
    return unique_list(match_links_list)


def write_excel_sheet():
    logging.info(f"Preparing the excel file")
    print(f"Preparing the excel file")

    end_time = datetime.now()
    final_time = end_time.strftime("%H:%M:%S")

    df_nhl = pd.DataFrame(NBA_GAME_DATA, columns=NBA_GAME_HEADERS)

    # Getting Google sheet book
    WB = client.open('NBA')

    # Setting sheets
    sheet1 = WB[0]
    sheet1.clear()

    sheet1.set_dataframe(df_nhl, (1, 1))

    sheet1.update_value('G1', "Last Update")
    sheet1.update_value('H1', final_time)

    logging.info(f"There are: {len(NBA_GAME_DATA)} Game ML Data ")
    print(f"There are: {len(NBA_GAME_DATA)} Game ML Data")

    logging.info(f"Operation completed successfully at {datetime.now()}")
    print(f"Operation completed successfully at {datetime.now()}")


# NFL Call
def NBA_CALL():

    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    driver.maximize_window()

    try:
        logging.info("NBA Call")
        try:
            nfl_url = "https://sportsbook.draftkings.com/leagues/basketball/nba"
            links = get_match_links(nfl_url, driver)
            # links = ["https://sportsbook.draftkings.com/event/det-lions-%40-chi-bears/26846030?sgpmode=true"]
            logging.info(f"Get {len(links)} links on page")
            print(f"Get {len(links)} links on page")
        except Exception as e:
            logging.info(f"Error for calling main page: {e}")
            print("Error Please Check logs for further details or rerun the file")

        for link in links:
            try:
                logging.info(f"Start getting values From: {link}")
                print(f"Start getting values form: {link}")
                sgp_dict = sgp_call(link, driver)
                non_sgp_dict = non_sgp_call(link, driver)
                NHL_GAME(sgp_dict, non_sgp_dict, link)

            except Exception as e:
                logging.info(f"Error on getting values for link {link}")
                logging.info(f"Error is {e}")
                print("Error Please Check logs for further details or return the file")
        write_excel_sheet()
        driver.quit()
    except Exception as e:
        logging.info(f"Error: {e}")
        print("Error Please Check logs for further details or return the file")


# Main Function
def main():
    while True:
        NBA_CALL()

        global NBA_GAME_DATA
        global H

        NBA_GAME_DATA = []
        H = 2

        print("\n \n ---------Waiting For the Next Call 20 Minutes Delay-------\n \n")
        logging.info("\n \n \n---------Waiting For the Next Call 20 Minutes Delay-------\n \n \n")
        time.sleep(1000)


main()
