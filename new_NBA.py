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
logging.basicConfig(filename=f"Logs/NBA2.log", filemode='w', level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
current_time = now.strftime("%H:%M:%S")
logging.info(f"Operation Start at {current_time}")

# Constant
H = 2
P = 2
A = 2
R = 2

NBA_GAME_HEADERS = ["Game", "DK Home SGP ML", "DK Home non sgp ML", "Difference"]
NBA_GAME_DATA = []

NBA_POINTS_HEADERS = ["Player", "Points", "DK SGP Line", "DK Non-SGP Line", "Difference"]
NBA_REBOUND_HEADERS = ["Player", "Rebounds", "DK SGP Line", "DK Non-SGP Line", "Difference"]
NBA_ASSISTS_HEADERS = ["Player", "Points", "DK SGP Line", "DK Non-SGP Line", "Difference"]

NBA_POINTS_DATA = []
NBA_REBOUND_DATA = []
NBA_ASSISTS_DATA = []


def get_sgp_values(header, label):
    values = []
    bet_tags = header.find_elements(By.CLASS_NAME, "rj-market__button--yourbet")
    for bet in bet_tags:
        bet_value = bet.find_element(By.CLASS_NAME, "rj-market__button-yourbet-title").text
        odd_value = ""
        try:
            odd_value = bet.find_element(By.CLASS_NAME, "rj-market__button-yourbet-odds").text
        except Exception as e:
            pass
        bet_value = str(bet_value) + " " + str(odd_value)
        values.append(bet_value.strip().replace("−", "-"))

    if label == "over":
        return values[0::2]
    else:
        return values


def get_val(element):
    odd_value = element.find_element(By.CLASS_NAME, "sportsbook-odds").text
    bet_value = ""
    try:
        bet_value = element.find_element(By.CLASS_NAME, "sportsbook-outcome-cell__line").text
    except Exception as e:
        pass
    bet_value = str(bet_value) + " " + str(odd_value)
    return bet_value.replace("−", "-")


def get_non_sgp_values(header, k):
    non_sgp_dict = {}
    i = 0
    player_names = header.find_elements(By.CLASS_NAME, "sportsbook-row-name")
    for player_name in player_names:
        element = header.find_element(By.XPATH, f"//div[2]/div[2]/div[1]/div[2]/div[{k}]/div/div[2]/div/table/tbody/tr[{i+1}]/td[1]/div/div/div")
        non_sgp_dict[player_name.text] = get_val(element)
        i = i+1
    return non_sgp_dict


# SGP Call
def sgp_call(link, driver):
    sgp = {
        "Game": {},
        "Points": {},
        "Assists": {},
        "Rebounds": {}
    }
    try:
        driver.get(link)
        driver.implicitly_wait(10)
        time.sleep(5)
        # For Game Lines
        try:
            driver.find_element(By.XPATH, "//button[text()='Game Lines']").click()
            header_elements = driver.find_elements(By.CLASS_NAME,  "rj-market-collapsible")
            for header in header_elements:
                header_name = header.find_element(By.CLASS_NAME, "rj-market__header").text
                if header_name == "Game":
                    i = 3
                    player_names = header.find_elements(By.XPATH, "//p[contains(@class, 'rj-market__label--row')]")
                    for player_name in player_names:
                        sgp["Game"][player_name.text] = driver.find_element(By.XPATH, f"/html/body/div[2]/div[2]/section/section[2]/section/section/div[2]/sb-comp/div/div/div[2]/sb-lazy-render/div/div[1]/div/div/div/button[{i}]/span[2]").text
                        i = i+3
        except Exception as e:
            print("No GAME SGP Available for this game")
            logging.info(f"No GAME SGP Available for this game for Error: {e}")
        # For Points
        try:
            driver.find_element(By.XPATH, "//button[text()='Points']").click()
            driver.implicitly_wait(10)
            driver.execute_script("window.scrollTo(0, window.scrollY + 1300)")
            time.sleep(2)
            points_headers = driver.find_elements(By.CLASS_NAME, "rj-market-collapsible")
            for header in points_headers:
                header_name = header.find_element(By.CLASS_NAME, "rj-market__header").text
                if header.get_attribute("data-collapsed") == "true" and "Points O/U" in header_name:
                    header.find_element(By.CLASS_NAME, "rj-market-collapsible__trigger").click()
                    driver.execute_script("window.scrollTo(0, window.scrollY + 300)")
                    time.sleep(1)
                    driver.implicitly_wait(10)
                if "Points O/U" in header_name:
                    sgp["Points"][header_name.replace(" Points O/U", "")] = get_sgp_values(header, "over")
        except Exception as e:
            print("No Points SGP Available for this game")
            logging.info(f"No Points SGP Available for this game for Error: {e}")

        # For Assists
        try:
            driver.find_element(By.XPATH, "//button[text()='Assists']").click()
            driver.implicitly_wait(10)
            driver.execute_script("window.scrollTo(0, window.scrollY + 1000)")
            time.sleep(2)
            assists_headers = driver.find_elements(By.CLASS_NAME, "rj-market-collapsible")
            for header in assists_headers:
                header_name = header.find_element(By.CLASS_NAME, "rj-market__header").text
                if header.get_attribute("data-collapsed") == "true" and "Assists O/U" in header_name:
                    header.find_element(By.CLASS_NAME, "rj-market-collapsible__trigger").click()
                    driver.execute_script("window.scrollTo(0, window.scrollY + 300)")
                    time.sleep(1)
                    driver.implicitly_wait(10)
                if "Assists O/U" in header_name:
                    sgp["Assists"][header_name.replace(" Assists O/U", "")] = get_sgp_values(header, "over")
        except Exception as e:
            print("No Assists SGP Available for this game")
            logging.info(f"No Assists SGP Available for this game for Error: {e}")

        # For Rebounds
        try:
            driver.find_element(By.XPATH, "//button[text()='Rebounds']").click()
            driver.implicitly_wait(10)
            driver.execute_script("window.scrollTo(0, window.scrollY + 1000)")
            time.sleep(2)
            rebound_headers = driver.find_elements(By.CLASS_NAME, "rj-market-collapsible")
            for header in rebound_headers:
                header_name = header.find_element(By.CLASS_NAME, "rj-market__header").text
                if header.get_attribute("data-collapsed") == "true" and "Rebounds O/U" in header_name:
                    header.find_element(By.CLASS_NAME, "rj-market-collapsible__trigger").click()
                    driver.execute_script("window.scrollTo(0, window.scrollY + 300)")
                    time.sleep(1)
                    driver.implicitly_wait(10)
                if "Rebounds O/U" in header_name:
                    sgp["Rebounds"][header_name.replace(" Rebounds O/U", "")] = get_sgp_values(header, "over")
        except Exception as e:
            print("No Rebounds SGP Available for this game")
            logging.info(f"No Rebounds SGP Available for this game for Error: {e}")

    except Exception as e:
        print("Error in SGP Call")
        logging.info(f"Error in SGP Call game for Error: {e}")
    return sgp


# Non SGP Call
def non_sgp_call(link, driver):
    non_sgp_dict = {
        "Game": {},
        "Points": {},
        "Rebounds": {},
        "Assists": {}
    }

    # Game Line
    try:
        game_line_link = link.replace("sgpmode=true", "category=odds&subcategory=game-lines")
        driver.get(game_line_link)
        driver.implicitly_wait(10)
        player_names = driver.find_elements(By.CLASS_NAME, "event-cell__name-text")
        i = 1
        for player_name in player_names:
            non_sgp_dict["Game"][player_name.text] = driver.find_element(By.XPATH, f"/html/body/div[2]/div[2]/section/section[2]/section/section/div[2]/div[2]/div[1]/div[2]/div[1]/div/table/tbody/tr[{i}]/td[3]/div/div/div/div/div[2]/span").text
            i = i + 1
    except Exception as e:
        print("No GAME-Lines Non-SGP Available for this game")
        logging.info(f"No GAME-Lines Non-SGP Available for this game, Error is: {e}")
    # Player Props
    try:
        pp_link = link.replace("sgpmode=true", "category=odds&subcategory=player-props")
        driver.get(pp_link)
        driver.implicitly_wait(10)
        time.sleep(3)
        pp_headers = driver.find_elements(By.CLASS_NAME, "sportsbook-event-accordion__wrapper")
        k = 0
        for pp_header in pp_headers:
            header_name = pp_header.find_element(By.CLASS_NAME, "sportsbook-event-accordion__title").text
            k = k + 1
            if header_name == "Points":
                non_sgp_dict["Points"] = get_non_sgp_values(pp_header, k)
                continue
            if header_name == "Rebounds":
                non_sgp_dict["Rebounds"] = get_non_sgp_values(pp_header, k)
                continue
            if header_name == "Assists":
                non_sgp_dict["Assists"] = get_non_sgp_values(pp_header, k)
                continue
    except Exception as e:
        print("No Player Props Non-SGP Available for this game")
        logging.info(f"No Player Props Non-SGP Available for this game, Error is: {e}")

    return non_sgp_dict


def NBA_GAME(sgp, non_sgp, link):
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
            NBA_GAME_DATA.append(lis)
            H = H + 1
        except Exception as e:
            continue


def points(sgp_row, non_sgp_row, link):
    global P
    for key, non_sgp_value in non_sgp_row.items():
        try:
            sgp_values = sgp_row[key]
            row = []
            for sgp_value in sgp_values:
                if non_sgp_value.split(" ")[0] == sgp_value.split(" ")[0]:
                    row.append(f'=HYPERLINK("{link}", "{key.title()}")')
                    row.append(sgp_value.split(" ")[0])
                    row.append(sgp_value.split(" ")[1])
                    row.append(non_sgp_value.split(" ")[1])
                    row.append(f"=SIGN(C{P} - D{P}) * MOD(ABS(C{P} - D{P}), 100)")
                    NBA_POINTS_DATA.append(row)
                    P = P + 1
        except Exception as e:
            pass


def assists(sgp_row, non_sgp_row, link):
    global A
    for key, non_sgp_value in non_sgp_row.items():
        try:
            sgp_values = sgp_row[key]
            row = []
            for sgp_value in sgp_values:
                if non_sgp_value.split(" ")[0] == sgp_value.split(" ")[0]:
                    row.append(f'=HYPERLINK("{link}", "{key.title()}")')
                    row.append(sgp_value.split(" ")[0])
                    row.append(sgp_value.split(" ")[1])
                    row.append(non_sgp_value.split(" ")[1])
                    row.append(f"=SIGN(C{A} - D{A}) * MOD(ABS(C{A} - D{A}), 100)")
                    NBA_ASSISTS_DATA.append(row)
                    A = A + 1
        except Exception as e:
            pass


def rebounds(sgp_row, non_sgp_row, link):
    global R
    for key, non_sgp_value in non_sgp_row.items():
        try:
            sgp_values = sgp_row[key]
            row = []
            for sgp_value in sgp_values:
                if non_sgp_value.split(" ")[0] == sgp_value.split(" ")[0]:
                    row.append(f'=HYPERLINK("{link}", "{key.title()}")')
                    row.append(sgp_value.split(" ")[0])
                    row.append(sgp_value.split(" ")[1])
                    row.append(non_sgp_value.split(" ")[1])
                    row.append(f"=SIGN(C{R} - D{R}) * MOD(ABS(C{R} - D{R}), 100)")
                    NBA_REBOUND_DATA.append(row)
                    R = R + 1
        except Exception as e:
            pass


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
    # final_time = end_time.strftime("%H:%M:%S")
    final_time = end_time.strftime("%d/%m/%Y %H:%M:%S")

    df_nba_game = pd.DataFrame(NBA_GAME_DATA, columns=NBA_GAME_HEADERS)
    df_nba_points = pd.DataFrame(NBA_POINTS_DATA, columns=NBA_POINTS_HEADERS)
    df_nba_assists = pd.DataFrame(NBA_ASSISTS_DATA, columns=NBA_ASSISTS_HEADERS)
    df_nba_rebounds = pd.DataFrame(NBA_REBOUND_DATA, columns=NBA_REBOUND_HEADERS)

    # Getting Google sheet book
    WB = client.open('NBA')

    # Setting sheets
    sheet1 = WB[0]
    sheet2 = WB[1]
    sheet3 = WB[2]
    sheet4 = WB[3]

    sheet1.clear()
    sheet2.clear()
    sheet3.clear()
    sheet4.clear()

    sheet1.set_dataframe(df_nba_game, (1, 1))
    sheet2.set_dataframe(df_nba_points, (1, 1))
    sheet3.set_dataframe(df_nba_assists, (1, 1))
    sheet4.set_dataframe(df_nba_rebounds, (1, 1))

    sheet1.update_value('G1', "Last Update")
    sheet1.update_value('H1', final_time)

    sheet2.update_value('G1', "Last Update")
    sheet2.update_value('H1', final_time)

    sheet3.update_value('G1', "Last Update")
    sheet3.update_value('H1', final_time)

    sheet4.update_value('G1', "Last Update")
    sheet4.update_value('H1', final_time)

    logging.info(f"There are: {len(NBA_GAME_DATA)} Game ML Data ")
    print(f"There are: {len(NBA_GAME_DATA)} Game ML Data")

    logging.info(f"There are: {len(NBA_POINTS_DATA)} Points Props Data ")
    print(f"There are: {len(NBA_POINTS_DATA)} Points Props Data")

    logging.info(f"There are: {len(NBA_ASSISTS_DATA)} Assists Props Data ")
    print(f"There are: {len(NBA_ASSISTS_DATA)} Assists Props Data")

    logging.info(f"There are: {len(NBA_REBOUND_DATA)} Rebounds Props Data ")
    print(f"There are: {len(NBA_REBOUND_DATA)} Rebounds Props Data")

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
            # links = ["https://sportsbook.draftkings.com/event/dal-mavericks-%40-tor-raptors/27992398?sgpmode=true"]
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
                print(sgp_dict)
                print(non_sgp_dict)
                if sgp_dict["Game"] != {} and non_sgp_dict["Game"] != {}:
                    NBA_GAME(sgp_dict["Game"], non_sgp_dict["Game"], link)

                if sgp_dict["Points"] != {} and non_sgp_dict["Points"] != {}:
                    points(sgp_dict["Points"], non_sgp_dict["Points"], link)

                if sgp_dict["Rebounds"] != {} and non_sgp_dict["Rebounds"] != {}:
                    rebounds(sgp_dict["Rebounds"], non_sgp_dict["Rebounds"], link)

                if sgp_dict["Assists"] != {} and non_sgp_dict["Assists"] != {}:
                    assists(sgp_dict["Assists"], non_sgp_dict["Assists"], link)

            except Exception as e:
                logging.info(f"Error on getting values for link {link}")
                logging.info(f"Error is {e}")
                print("Error Please Check logs for further details or return the file")
        write_excel_sheet()
        driver.quit()
    except Exception as e:
        logging.info(f"Error: {e}")
        print("Error Please Check logs for further details or return the file")


# NBA_CALL()
# Main Function
def main():
    while True:
        NBA_CALL()

        global NBA_GAME_DATA
        global NBA_POINTS_DATA
        global NBA_ASSISTS_DATA
        global NBA_REBOUND_DATA

        global A
        global R
        global H
        global P

        NBA_GAME_DATA = []
        NBA_POINTS_DATA = []
        NBA_REBOUND_DATA = []
        NBA_ASSISTS_DATA = []

        H = 2
        P = 2
        A = 2
        R = 2

        print("\n \n ---------Waiting For the Next Call 20 Minutes Delay-------\n \n")
        logging.info("\n \n \n---------Waiting For the Next Call 20 Minutes Delay-------\n \n \n")
        time.sleep(1000)


main()
