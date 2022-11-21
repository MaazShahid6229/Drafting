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
driver = webdriver.Chrome(options=chrome_options)
driver.implicitly_wait(10)
driver.maximize_window()

# Operation start date
now = datetime.now()
logging.basicConfig(filename=f"Logs/BaseBall.log", filemode='w', level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
current_time = now.strftime("%H:%M:%S")
logging.info(f"Operation Start at {current_time}")

# Constant Define
GAME_HEADER = ["Player", "Event", "Market", "Run Line Non-SGP", "Run Line SGP", "DK Non-SGP Run Line Odds",
               "DK SGP Run Line Odds", "Bet", "Non-SGP Total", "SGP Total", "DK Non-SGP Total Runs Odds",
               "DK SGP Total Runs Odds", "MoneyLine Non-SGP", "MoneyLine SGP", "Run Line Diff", "Total Run Diff",
               "Money Line Diff"]

Pitcher_Props_Header = ["Player", "Event", "Market", "Bet", "Line", "Non SGP Odds", "SGP Odds", "Diff"]

GAME_DATA = []
Pitcher_Props_Data = []

i = 2
j = 2
z = 2
q = 2


# Unique List Function
def unique_list(lis):
    new_set = set(lis)
    return list(new_set)


# Get Game name from lins
def link_to_name(link):
    parse_url = urlparse(link)
    raw_match_name = str(parse_url.path.split("/")[2]).replace("-", " ")
    raw_match_name = raw_match_name.replace("%40", "VS")
    formula_game_name = f'=HYPERLINK("{link}", "{raw_match_name.title()}")'
    return formula_game_name


# SGP Bet values from header
def get_bet_values(head):
    values = []
    bet_tags = head.find_elements(By.CLASS_NAME, "rj-market__button--yourbet")
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


# Get Non SGP values from driver header
def non_sgp_bet_values(header, header_name):
    values = []
    bet_tags = header.find_elements(By.CLASS_NAME, "sportsbook-outcome-body-wrapper")

    if header_name == "Alternate Total Runs":
        for bet in bet_tags:
            odd_value = bet.find_element(By.CLASS_NAME, "sportsbook-odds").text
            tag_text = bet.find_element(By.CLASS_NAME, "sportsbook-outcome-cell__label").text
            bet_value = ""
            try:
                bet_value = bet.find_element(By.CLASS_NAME, "sportsbook-outcome-cell__line").text
            except Exception as e:
                pass
            bet_value = str(tag_text) + " "+str(bet_value) + " " + str(odd_value)
            values.append(bet_value.strip().replace("−", "-"))
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


def even_odd_list(lis):
    row1 = []
    row2 = []
    for k in range(0, len(lis)):
        if k % 2 == 0:
            row1.append(lis[k])
        else:
            row2.append(lis[k])
    return row1, row2


def match_values(non_sgp_row, sgp_row):
    row = []
    for n in non_sgp_row:
        n_spilt = n.split(" ")
        for m in sgp_row:
            m_spilt = m.split(" ")
            if n_spilt[0] == m_spilt[0]:
                row.append(m_spilt[0])
                row.append(m_spilt[1])
                row.append(n_spilt[1])

    row_len = len(row)

    if row_len == 21:
        pass
    elif row_len < 21:
        for _ in range(row_len, 21):
            row.append(" ")
    elif row_len > 21:
        row = row[0:21]
    return row


def over_under_method(non_sgp_row):
    row1 = []
    row2 = []
    for d in non_sgp_row:
        if "Over" in d:
            row1.append(d.replace("Over ", ""))
        else:
            row2.append(d.replace("Under ", ""))
    return row1, row2


# Get Matches links from main page
def get_match_links(game_link):
    driver.get(game_link)
    logging.info(f"Redirect to Page: {game_link}")
    print(f"Redirect to Page: {game_link}")
    driver.implicitly_wait(10)
    match_links = driver.find_elements(By.CLASS_NAME, "toggle-sgp-badge__nav-link")
    match_links_list = [x.get_attribute("href") for x in match_links]
    return unique_list(match_links_list)


# SGP call to get all the values in list
def sgp_call(link):
    sg_dict = {}
    driver.get(link)
    driver.implicitly_wait(10)

    # For Game-Lines
    driver.find_element(By.XPATH, "//sb-comp/div/div/div[1]/div/div/button[2]").click()
    driver.implicitly_wait(10)
    headers = driver.find_elements(By.CLASS_NAME, "rj-market-collapsible")
    for header in headers:
        header_name = header.find_element(By.CLASS_NAME, "rj-market__header").text

        if header.get_attribute("data-collapsed") == True:
            header.find_element(By.CLASS_NAME, "rj-market-collapsible__trigger").click()
            driver.implicitly_wait(10)

        if header_name == "Game":
            sg_dict["Game"] = get_bet_values(header)
    try:
        # For Pitcher Props
        driver.find_element(By.XPATH, "//button[text()='Pitcher Props']").click()
        driver.implicitly_wait(10)
        pp_headers = driver.find_elements(By.CLASS_NAME, "rj-market-collapsible")
        sg_dict["pp"] = {}

        for pp_header in pp_headers:
            pp_header_name = pp_header.find_element(By.CLASS_NAME, "rj-market__header").text
            if "Strikeouts" in pp_header_name:
                sg_dict["pp"][pp_header_name.replace(" Strikeouts Thrown", "")] = get_bet_values(pp_header)

    except Exception as e:
        print("No Pitcher Props SGP Available for this game")
        logging.info(f"No Pitcher Props SGP Available for this game for Error: {e}")

    return sg_dict


# Non SGP call to get all the values in list
def non_sgp_call(link):
    non_sgp_dict = {}
    link = link.replace("sgpmode=true", "category=odds&subcategory=game-lines")
    driver.get(link)
    driver.implicitly_wait(10)
    players = driver.find_elements(By.CLASS_NAME, "event-cell__label")
    player_names = [players[1].text, players[2].text]

    non_sgp_game_header = driver.find_element(By.CLASS_NAME, "sportsbook-table")
    non_sgp_dict["Game"] = non_sgp_bet_values(non_sgp_game_header, "Game")

    non_sgp_headers = driver.find_elements(By.CLASS_NAME, "sportsbook-event-accordion__wrapper")

    try:
        new_link = link.replace("subcategory=game-lines", "subcategory=pitcher-props")
        driver.get(new_link)
        driver.implicitly_wait(10)
        non_sgp_strikeout = driver.find_element(By.CLASS_NAME, "sportsbook-event-accordion__children-wrapper")
        non_sgp_dict["pp"] = {}
        so_player_names_element = non_sgp_strikeout.find_elements(By.CLASS_NAME, "sportsbook-row-name")
        so_cell = non_sgp_strikeout.find_elements(By.CLASS_NAME, "sportsbook-outcome-cell")
        so_player_names = [x.text for x in so_player_names_element]
        for s in range(0, len(so_player_names)):
            non_sgp_dict["pp"][so_player_names[s]] = non_sgp_bet_values(so_cell[s+s], "PP")

    except Exception as e:
        logging.info(f"No Pitcher Props Non SGP Available for this game for Error: {e}")
        print(e)
    return non_sgp_dict, player_names


# Setting Games list
def games(sgp, non_sgp, players_names, game_names):
    logging.info("Games Call")
    global i
    try:
        row1 = []
        row2 = []

        row1.append(players_names[0])
        row2.append(players_names[1])

        row1.append(game_names)
        row2.append(game_names)

        row1.append("GameLines-Games")
        row2.append("GameLines-Games")

        non_sgp_run_lines1 = non_sgp[0].split(" ")
        sgp_run_lines1 = sgp[0].split(" ")

        non_sgp_total_run1 = non_sgp[1].split(" ")
        sgp_total_run1 = sgp[1].split(" ")

        row1.append(non_sgp_run_lines1[0])
        row1.append(sgp_run_lines1[0])
        row1.append(non_sgp_run_lines1[1])
        row1.append(sgp_run_lines1[1])
        row1.append(sgp_total_run1[0])
        row1.append(non_sgp_total_run1[0])
        row1.append(sgp_total_run1[1])
        row1.append(non_sgp_total_run1[1])
        row1.append(sgp_total_run1[2])
        row1.append(non_sgp[2].strip())
        row1.append(sgp[2].strip())

        row1.append(f'=IF(INT(SUBSTITUTE(G{i},"−", "-"))>INT(SUBSTITUTE(F{i},"−", "-")), ABS(ABS(SUBSTITUTE(G{i}, "−","-"))-ABS(SUBSTITUTE(F{i},"−","-"))), -ABS(ABS(SUBSTITUTE(F{i},"−","-"))-ABS(SUBSTITUTE(G{i},"−","-"))))')
        row1.append(f'=IF(INT(SUBSTITUTE(L{i},"−", "-"))>INT(SUBSTITUTE(K{i},"−", "-")), ABS(ABS(SUBSTITUTE(L{i}, "−","-"))-ABS(SUBSTITUTE(K{i},"−","-"))), -ABS(ABS(SUBSTITUTE(K{i},"−","-"))-ABS(SUBSTITUTE(L{i},"−","-"))))')
        row1.append(f'=IF(INT(SUBSTITUTE(N{i},"−", "-"))>INT(SUBSTITUTE(M{i},"−", "-")), ABS(ABS(SUBSTITUTE(N{i}, "−","-"))-ABS(SUBSTITUTE(M{i},"−","-"))), -ABS(ABS(SUBSTITUTE(M{i},"−","-"))-ABS(SUBSTITUTE(N{i},"−","-"))))')

        non_sgp_run_lines2 = non_sgp[3].split(" ")
        sgp_run_lines2 = sgp[3].split(" ")

        non_sgp_total_run2 = non_sgp[4].split(" ")
        sgp_total_run2 = sgp[4].split(" ")

        row2.append(non_sgp_run_lines2[0])
        row2.append(sgp_run_lines2[0])
        row2.append(non_sgp_run_lines2[1])
        row2.append(sgp_run_lines2[1])
        row2.append(sgp_total_run2[0])
        row2.append(non_sgp_total_run2[0])
        row2.append(sgp_total_run2[1])
        row2.append(non_sgp_total_run2[1])
        row2.append(sgp_total_run2[2])
        row2.append(non_sgp[5].strip())
        row2.append(sgp[5].strip())

        row2.append(f'=IF(INT(SUBSTITUTE(G{i+1},"−", "-"))>INT(SUBSTITUTE(F{i+1},"−", "-")), ABS(ABS(SUBSTITUTE(G{i+1},"−","-"))-ABS(SUBSTITUTE(F{i+1},"−","-"))), -ABS(ABS(SUBSTITUTE(F{i+1},"−","-"))-ABS(SUBSTITUTE(G{i+1},"−","-"))))')
        row2.append(f'=IF(INT(SUBSTITUTE(L{i+1},"−", "-"))>INT(SUBSTITUTE(K{i+1},"−", "-")), ABS(ABS(SUBSTITUTE(L{i+1},"−","-"))-ABS(SUBSTITUTE(K{i+1},"−","-"))), -ABS(ABS(SUBSTITUTE(K{i+1},"−","-"))-ABS(SUBSTITUTE(L{i+1},"−","-"))))')
        row2.append(f'=IF(INT(SUBSTITUTE(N{i+1},"−", "-"))>INT(SUBSTITUTE(M{i+1},"−", "-")), ABS(ABS(SUBSTITUTE(N{i+1},"−","-"))-ABS(SUBSTITUTE(M{i+1},"−","-"))), -ABS(ABS(SUBSTITUTE(M{i+1},"−","-"))-ABS(SUBSTITUTE(N{i+1},"−","-"))))')

        GAME_DATA.append(row1)
        GAME_DATA.append(row2)
        i = i + 2
    except Exception as e:
        logging.info("Error Game At:", e)
        pass


# Pitcher Props Call
def pitcher_props(sgp, non_sgp, game_name):
    logging.info("Pitcher Props Call")
    global q
    for i_non_sgp in non_sgp.items():
        try:
            lis = []
            lis.append(i_non_sgp[0])
            lis.append(game_name)
            lis.append("Strikeouts")
            lis.append("o")
            sgp_lis = sgp[i_non_sgp[0]]
            non_sgp_lis = i_non_sgp[1][0]
            for i_sgp_lis in sgp_lis:
                if int(i_sgp_lis.split(" ")[0].replace("+", "").replace("-", "")) == math.ceil(float(non_sgp_lis.split(" ")[0])):
                    lis.append(non_sgp_lis.split(" ")[0])
                    lis.append(non_sgp_lis.split(" ")[1])
                    lis.append(i_sgp_lis.split(" ")[1])
                    # lis.append(f"=IF(INT(G{q})>INT(F{q}), ABS(ABS(G{q})-ABS(F{q})), -ABS(ABS(F{q})-ABS(G{q})))")
                    lis.append(f"=SIGN(G{q} - F{q}) * MOD(ABS(G{q} - F{q}), 100)")
                    if len(lis) > 0:
                        Pitcher_Props_Data.append(lis)
                        q = q + 1
        except Exception as e:
            logging.info(f"Error is {e}")
            continue


# BaseBall Call
def baseball_ball_call():
    try:
        logging.info("BaseBall Call")
        try:
            basket_ball_url = "https://sportsbook.draftkings.com/leagues/baseball/mlb"
            links = get_match_links(basket_ball_url)
            logging.info(f"Get {len(links)} links on page")
            print(f"Get {len(links)} links on page")
        except Exception as e:
            logging.info(f"Error for calling main page: {e}")
            print("Error Please Check logs for further details or rerun the file")

        for link in links:
            try:
                logging.info(f"Start getting values From: {link}")
                print(f"Start getting values form: {link}")
                sgp_dict = sgp_call(link)
                non_sgp_dict, players = non_sgp_call(link)
                game_name = link_to_name(link)
                games(sgp_dict["Game"], non_sgp_dict["Game"], players, game_name)
                try:
                    pitcher_props(sgp_dict["pp"], non_sgp_dict["pp"], game_name)
                except Exception as e:
                    logging.info(f"No data in pitcher props and the Error is: {e}")
                # break
            except Exception as e:
                logging.info(f"Error on getting values for link {link}")
                logging.info(f"Error is {e}")
                print("Error Please Check logs for further details or rerun the file")

        logging.info(f"Preparing the excel file")
        print(f"Preparing the excel file")

        end_time = datetime.now()
        final_time = end_time.strftime("%H:%M:%S")

        df_pitcher_props = pd.DataFrame(Pitcher_Props_Data, columns=Pitcher_Props_Header)
        df_games = pd.DataFrame(GAME_DATA, columns=GAME_HEADER)

        # Getting Google sheet book
        WB = client.open('BaseBall')

        # Setting sheets
        sheet1 = WB[0]
        sheet2 = WB[1]

        sheet1.clear()
        sheet2.clear()

        sheet1.set_dataframe(df_pitcher_props, (1, 1))
        sheet2.set_dataframe(df_games, (1, 1))

        sheet1.update_value('J1', "Last Update")
        sheet1.update_value('K1', final_time)

        sheet2.update_value('S1', "Last Update")
        sheet2.update_value('T1', final_time)

        logging.info(f"There are: {len(Pitcher_Props_Data)} Pitcher Props  and {len(GAME_DATA)} Game-Lines Data")
        print(f"There are: {len(Pitcher_Props_Data)} Pitcher Props  and {len(GAME_DATA)} Game-Lines Data")

        logging.info(f"Operation completed successfully at {datetime.now()}")
        print(f"Operation completed successfully at {datetime.now()}")

    except Exception as e:
        logging.info(f"Error: {e}")
        print("Error Please Check logs for further details or rerun the file")


# Main Function
def main():
    while True:
        time_now = datetime.now().strftime("%H")
        if time_now == "00":
            print("\n \n ---------Its Night Time and Script is on Sleeping Mode-------\n \n")
            logging.info("\n \n \n---------Its Night Time and Script is on Sleeping Mode-------\n \n \n")
            time.sleep(25000)

        baseball_ball_call()
        global GAME_DATA
        GAME_DATA = []
        global Pitcher_Props_Data
        Pitcher_Props_Data = []
        global i
        i = 2
        global j
        j = 2
        global z
        z = 2
        global q
        q = 2
        print("\n \n ---------Waiting For the Next Call 10 Minutes Delay-------\n \n")
        logging.info("\n \n \n---------Waiting For the Next Call 12 Hours Delay-------\n \n \n")
        time.sleep(43200)


main()
