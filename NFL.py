import time
import math
import logging
import pandas as pd
from datetime import datetime
from selenium import webdriver
from urllib.parse import urlparse
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
logging.basicConfig(filename=f"Logs/NFL.log", filemode='w', level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
current_time = now.strftime("%H:%M:%S")
logging.info(f"Operation Start at {current_time}")

# Constant
H = 2
G = 2

NFL_GAME_HEADERS = ["Game", "DK Home SGP ML", "DK Home non sgp ML", "Difference"]
NFL_GAME_DATA = []

PASSING_PROPS_HEADERS = ["Game", "Player", "DK Non SGP (o)", "DK Non SGP (o) Line", "DK SGP (o)", "DK SGP (o) Line"]
PASSING_PROPS_DATA = []

RUSHING_PROPS_HEADERS = ["Game", "Player", "DK Non SGP (o)", "DK Non SGP (o) Line", "DK SGP (o)", "DK SGP (o) Line"]
RUSHING_PROPS_DATA = []


# Get Non SGP values from driver header
def non_sgp_bet_values(header, label):
    values = []
    bet_tags = header.find_elements(By.CLASS_NAME, "sportsbook-outcome-body-wrapper")
    if label == "label":
        for bet in bet_tags:
            odd_value = bet.find_element(By.CLASS_NAME, "sportsbook-odds").text
            tag_text = bet.find_element(By.CLASS_NAME, "sportsbook-outcome-cell__label").text
            bet_value = ""
            try:
                bet_value = bet.find_element(By.CLASS_NAME, "sportsbook-outcome-cell__line").text
            except Exception as e:
                pass
            bet_value = str(tag_text) + " " + str(bet_value) + " " + str(odd_value)
            values.append(bet_value.strip().replace("−", "-"))
        return values
    else:
        for bet in bet_tags:
            odd_value = bet.find_element(By.CLASS_NAME, "sportsbook-odds").text
            bet_value = ""
            try:
                bet_value = bet.find_element(By.CLASS_NAME, "sportsbook-outcome-cell__line").text
            except Exception as e:
                pass
            bet_value = str(bet_value) + " " + str(odd_value)
            values.append(bet_value.strip().replace("−", "-"))
        return values


def sgp_bet_values(header, label):
    values = []
    bet_tags = header.find_elements(By.CLASS_NAME, "rj-market__button--yourbet")
    if label == "over":
        for bet in bet_tags:
            bet_value = bet.find_element(By.CLASS_NAME, "rj-market__button-yourbet-title").text
            odd_value = ""
            try:
                odd_value = bet.find_element(By.CLASS_NAME, "rj-market__button-yourbet-odds").text
            except Exception as e:
                pass
            bet_value = str(bet_value) + " " + str(odd_value)
            values.append(bet_value.strip().replace("−", "-"))
        return values[0::2]
    else:
        for bet in bet_tags:
            bet_value = bet.find_element(By.CLASS_NAME, "rj-market__button-yourbet-title").text
            odd_value = ""
            try:
                odd_value = bet.find_element(By.CLASS_NAME, "rj-market__button-yourbet-odds").text
            except Exception as e:
                pass
            bet_value = str(bet_value) + " " + str(odd_value)
            values.append(bet_value.strip().replace("−", "-"))
        return values


# SGP Call
def sgp_call(link, driver):
    sgp_dict = {
        "Game": {},
        "Passing Props": {},
        "Rushing Props": {}
    }
    # Passing Props
    try:
        driver.get(link)
        driver.implicitly_wait(10)
        time.sleep(5)
        # Game
        try:
            driver.find_element(By.XPATH, "//button[text()='Game Lines']").click()
            header_elements = driver.find_elements(By.CLASS_NAME,  "rj-market-collapsible")
            for header in header_elements:
                header_name = header.find_element(By.CLASS_NAME, "rj-market__header").text
                if header_name == "Game":
                    i = 3
                    player_names = header.find_elements(By.XPATH, "//p[contains(@class, 'rj-market__label--row')]")
                    for player_name in player_names:
                        sgp_dict["Game"][player_name.text] = driver.find_element(By.XPATH, f"/html/body/div[2]/div[2]/section/section[2]/section/section/div[2]/sb-comp/div/div/div[2]/sb-lazy-render/div/div[1]/div/div/div/button[{i}]/span[2]").text
                        i = i+3
        except Exception as e:
            print("No GAME SGP Available for this game")
            logging.info(f"No Passing Props SGP Available for this game for Error: {e}")
        # Passing Props
        try:
            driver.find_element(By.XPATH, "//button[text()='Passing Props']").click()
            header_elements = driver.find_elements(By.CLASS_NAME,  "rj-market-collapsible")
            for header in header_elements:
                header_name = header.find_element(By.CLASS_NAME, "rj-market__header").text
                if "Passing Yards" in header_name and "Alternate Passing Yards" not in header_name and "Longest Passing Yards" not in header_name:
                    sgp_dict["Passing Props"][header_name.replace(" Passing Yards", "")] = sgp_bet_values(header, "over")
        except Exception as e:
            print("No Passing Props SGP Available for this game")
            logging.info(f"No Passing Props SGP Available for this game for Error: {e}")

        # Rushing Props
        try:
            driver.find_element(By.XPATH, "//button[text()='Rushing Props']").click()
            header_elements = driver.find_elements(By.CLASS_NAME,  "rj-market-collapsible")
            for header in header_elements:
                header_name = header.find_element(By.CLASS_NAME, "rj-market__header").text
                if "Rushing Yards" in header_name and "Alternate Rushing Yards" not in header_name and "Longest Rushing Yards" not in header_name:
                    sgp_dict["Rushing Props"][header_name.replace(" Rushing Yards", "")] = sgp_bet_values(header, "over")
        except Exception as e:
            print("No Rushing Props SGP Available for this game")
            logging.info(f"No Rushing Props SGP Available for this game for Error: {e}")

    except Exception as e:
        print("Error in SGP Call")
        logging.info(f"Error in SGP Call game for Error: {e}")
    return sgp_dict


# Non SGP Call
def non_sgp_call(link, driver):
    non_sgp_dict = {
        "Game": {},
        "Passing Props": {},
        "Rushing Props": {}
    }
    # Game
    try:
        game_link = link.replace("sgpmode=true", "category=odds&subcategory=game-lines")
        driver.get(game_link)
        driver.implicitly_wait(10)
        player_names = driver.find_elements(By.CLASS_NAME, "event-cell__name-text")
        i = 1
        for player_name in player_names:
            non_sgp_dict["Game"][player_name.text] = driver.find_element(By.XPATH, f"/html/body/div[2]/div[2]/section/section[2]/section/section/div[2]/div[2]/div[1]/div[2]/div[1]/div/table/tbody/tr[{i}]/td[3]/div/div/div/div/div[2]/span").text
            i = i + 1
    except Exception as e:
        print("No GAME Non SGP Available for this game")
        logging.info(f"No GAME Non SGP Available for this game, Error is: {e}")

    # Passing Props
    try:
        pp_link = link.replace("sgpmode=true", "category=odds&subcategory=passing-props")
        driver.get(pp_link)
        driver.implicitly_wait(10)
        header_elements = driver.find_elements(By.CLASS_NAME, "sportsbook-event-accordion__wrapper")
        for header_element in header_elements:
            header_name = header_element.find_element(By.CLASS_NAME, "sportsbook-event-accordion__title").text
            if header_name == "Pass Yds":
                so_player_names = [x.text for x in header_element.find_elements(By.CLASS_NAME, "sportsbook-row-name")]
                so_cell = header_element.find_elements(By.CLASS_NAME, "sportsbook-outcome-cell")
                for s in range(0, len(so_player_names)):
                    non_sgp_dict["Passing Props"][so_player_names[s]] = non_sgp_bet_values(so_cell[s + s], "label")
    except Exception as e:
        print("No Passing Props Non SGP Available for this game")
        logging.info(f"No Passing Props Non SGP Available for this game, Error is: {e}")

    # Rushing Props
    try:
        rp_link = link.replace("sgpmode=true", "category=odds&subcategory=rush/rec-props")
        driver.get(rp_link)
        driver.implicitly_wait(10)
        header_elements = driver.find_elements(By.CLASS_NAME, "sportsbook-event-accordion__wrapper")
        for header_element in header_elements:
            header_name = header_element.find_element(By.CLASS_NAME, "sportsbook-event-accordion__title").text
            if header_name == "Rush Yds":
                so_player_names = [x.text for x in header_element.find_elements(By.CLASS_NAME, "sportsbook-row-name")]
                so_cell = header_element.find_elements(By.CLASS_NAME, "sportsbook-outcome-cell")
                for s in range(0, len(so_player_names)):
                    non_sgp_dict["Rushing Props"][so_player_names[s]] = non_sgp_bet_values(so_cell[s + s], "label")
    except Exception as e:
        print("No Rushing Props Non SGP Available for this game")
        logging.info(f"No Rushing Props Non SGP Available for this game, Error is: {e}")

    return non_sgp_dict


def link_to_name(link):
    parse_url = urlparse(link)
    raw_match_name = str(parse_url.path.split("/")[2]).replace("-", " ")
    raw_match_name = raw_match_name.replace("%40", "VS")
    formula_game_name = f'=HYPERLINK("{link}", "{raw_match_name.title()}")'
    return formula_game_name


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


def NFL_GAME(sgp, non_sgp, link):
    global G
    for s in sgp.items():
        lis = []
        try:
            ml_non_sgp = non_sgp[s[0]]
            game_name = link
            lis.append(game_name)
            lis.append(s[1])
            lis.append(ml_non_sgp)
            lis.append(f"=SIGN(B{G} - C{G}) * MOD(ABS(B{G} - C{G}), 100)")
            NFL_GAME_DATA .append(lis)
            G = G + 1
        except Exception as e:
            continue


def passing_props(sgp, non_sgp, game_name):
    print("Call Passing Props")
    logging.info(f"Call Passing Props")
    global H
    try:
        for i in non_sgp.items():
            try:
                lis = []
                non_sgp_values = i[1][0].split(" ")

                lis.append(game_name)
                lis.append(i[0])
                lis.append(non_sgp_values[1])
                lis.append(non_sgp_values[2])

                sgp_lis = sgp[i[0]]
                non_sgp_line = non_sgp_values[1]
                min_val = 9999
                for x in sgp_lis:
                    val = float(x.split(" ")[0])
                    if val >= float(non_sgp_line) and val <= float(min_val):
                        min_val = val
                        r_val = x
                sgp_values = r_val.split(" ")
                lis.append(sgp_values[0])
                lis.append(sgp_values[1])
                # print(lis)
                PASSING_PROPS_DATA.append(lis)
                H = H + 1
            except:
                continue
    except Exception as e:
        logging.info(f"Error in calling Passing Props and the Error is: {e}")
        # print("Error for calling passing props Check logs for further details")


def rushing_props(sgp, non_sgp, game_name):
    print("Call Rushing Props")
    logging.info(f"Call Rushing Props")
    try:
        for i in non_sgp.items():
            try:
                lis = []
                non_sgp_values = i[1][0].split(" ")

                lis.append(game_name)
                lis.append(i[0])
                lis.append(non_sgp_values[1])
                lis.append(non_sgp_values[2])

                sgp_lis = sgp[i[0]]
                non_sgp_line = non_sgp_values[1]
                min_val = 9999
                for x in sgp_lis:
                    val = float(x.split(" ")[0])
                    if val >= float(non_sgp_line) and val <= float(min_val):
                        min_val = val
                        r_val = x
                sgp_values = r_val.split(" ")
                lis.append(sgp_values[0])
                lis.append(sgp_values[1])
                # lis.append(f"=E{H}-C{H}")
                # lis.append(f"=SIGN(F{H} - D{H}) * MOD(ABS(F{H} - D{H}), 100)")
                RUSHING_PROPS_DATA.append(lis)
            except:
                continue
    except Exception as e:
        logging.info(f"Error in calling Rushing Props and the Error is: {e}")
        # print("Rushing Props have not values")


def write_excel_sheet():
    logging.info(f"Preparing the excel file")
    print(f"Preparing the excel file")

    end_time = datetime.now()
    final_time = end_time.strftime("%H:%M:%S")

    df_game = pd.DataFrame(NFL_GAME_DATA, columns=NFL_GAME_HEADERS)
    df_passing_props = pd.DataFrame(PASSING_PROPS_DATA, columns=PASSING_PROPS_HEADERS)
    df_rushing_props = pd.DataFrame(RUSHING_PROPS_DATA, columns=RUSHING_PROPS_HEADERS)


    # Getting Google sheet book
    WB = client.open('NFL')

    # Setting sheets
    sheet1 = WB[0]
    sheet2 = WB[1]
    sheet3 = WB[2]

    sheet1.clear()
    sheet2.clear()
    sheet3.clear()

    sheet1.set_dataframe(df_game, (1, 1))
    sheet2.set_dataframe(df_passing_props, (1, 1))
    sheet3.set_dataframe(df_rushing_props, (1, 1))

    sheet1.update_value('G1', "Last Update")
    sheet1.update_value('H1', final_time)

    sheet2.update_value('G1', "Last Update")
    sheet2.update_value('H1', final_time)

    sheet3.update_value('G1', "Last Update")
    sheet3.update_value('H1', final_time)

    logging.info(f"There are: {len(NFL_GAME_DATA)} Game ML Data ")
    print(f"There are: {len(NFL_GAME_DATA)} Game ML Data")

    logging.info(f"There are: {len(PASSING_PROPS_DATA)} Passing Props Data ")
    print(f"There are: {len(PASSING_PROPS_DATA)} Passing Props Data")

    logging.info(f"There are: {len(RUSHING_PROPS_DATA)} Rushing Props Data ")
    print(f"There are: {len(RUSHING_PROPS_DATA)} Rushing Props Data")

    logging.info(f"Operation completed successfully at {datetime.now()}")
    print(f"Operation completed successfully at {datetime.now()}")


# NFL Call
def NFL_CALL():

    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    driver.maximize_window()

    try:
        logging.info("NFL Call")
        try:
            nfl_url = "https://sportsbook.draftkings.com/leagues/football/nfl"
            links = get_match_links(nfl_url, driver)
            # links = [" https://sportsbook.draftkings.com/event/la-rams-%40-kc-chiefs/26843976?sgpmode=true"]
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
                print("Non SGP", non_sgp_dict)
                print("SGP", sgp_dict)
                game_name = link_to_name(link)
                if sgp_dict["Game"] != {} and non_sgp_dict["Game"] != {}:
                    NFL_GAME(sgp_dict["Game"], non_sgp_dict["Game"], game_name)

                if sgp_dict["Passing Props"] != {} and non_sgp_dict["Passing Props"] != {}:
                    passing_props(sgp_dict["Passing Props"], non_sgp_dict["Passing Props"], game_name)

                if sgp_dict["Rushing Props"] != {} and non_sgp_dict["Rushing Props"] != {}:
                    rushing_props(sgp_dict["Rushing Props"], non_sgp_dict["Rushing Props"], game_name)

            except Exception as e:
                logging.info(f"Error on getting values for link {link}")
                logging.info(f"Error is {e}")
                print("Error Please Check logs for further details or rerun the file")
        write_excel_sheet()
        driver.quit()
    except Exception as e:
        logging.info(f"Error: {e}")
        print("Error Please Check logs for further details or rerun the file")


# Main Function
def main():
    while True:
        NFL_CALL()

        global PASSING_PROPS_DATA
        global RUSHING_PROPS_DATA
        global NFL_GAME_DATA

        PASSING_PROPS_DATA = []
        RUSHING_PROPS_DATA = []
        NFL_GAME_DATA = []

        global H
        global G

        H = 2
        G = 2

        print("\n \n ---------Waiting For the Next Call 20 Minutes Delay-------\n \n")
        logging.info("\n \n \n---------Waiting For the Next Call 20 Minutes Delay-------\n \n \n")
        time.sleep(1000)


main()
