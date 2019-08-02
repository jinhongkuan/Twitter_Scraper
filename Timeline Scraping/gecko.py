import os
import sys
import selenium
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.expected_conditions import staleness_of
from selenium.common.exceptions import TimeoutException
 
from bs4 import BeautifulSoup as bs
import time

def extract_tweets(soup):
  tweets = []

  for li in soup.find_all("li", class_='js-stream-item'):
    # If our li doesn't have a tweet-id, we skip it as it's not going to be a tweet.
    if 'data-item-id' not in li.attrs:
        continue
    else:
      tweet = {
          'tweet_id': li['data-item-id'],
          'tweet_text': None,
          'created_at': None,
          'retweet_count': 0,
          'favourite_count': 0,
          'reply_count': 0,
          'user_id': None,
          'user_screen_name': None,
          'user_name': None, 
          'tweet_type': None
      }

      if(li.find("div", {'class':'tweet-reply-context'}) != None):
        tweet["tweet_type"] = "reply"
      elif(li.find("span", {'class':'js-retweet-text'}) != None):
        tweet["tweet_type"] = "retweet_without_comment"
      elif(li.find("div", {'class':'QuoteTweet-innerContainer'}) != None):
        tweet["tweet_type"] = "retweet_with_comment" 
        st = li.find("div", {'class':'QuoteTweet-innerContainer'})
        st_dict = {
            "tweet_id": None,
            "secondary_user_screen_name": None,
            "secondary_user_id": None,
            "secondary_tweet_text": None
        }

        try:
          st_dict["tweet_id"] = st["data-item-id"]
        except:
          pass

        try:
          st_dict["secondary_user_screen_name"] = st["data-screen-name"]
        except:
          pass

        try:
          st_dict["secondary_user_id"] = st["data-user-id"]
        except:
          pass
        
        try:          
         st_dict["secondary_tweet_text"] = (li.find('div', class_="tweet-text").get_text())
        except:
          pass

        tweet["secondary-tweet"] = st_dict
      else:
        tweet["tweet_type"] = "source_tweet"

      # Tweet Text
      text_p = li.find("p", class_="tweet-text")
      if text_p is not None:
        tweet['tweet_text'] = text_p.get_text()

      # Tweet User ID, User Screen Name, User Name
      user_details_div = li.find("div", class_="tweet")
      if user_details_div is not None:
        tweet['user_id'] = user_details_div['data-user-id']
        tweet['user_screen_name'] = user_details_div['data-screen-name']
        tweet['user_name'] = user_details_div['data-name']

      # Tweet date
      date_span = li.find("span", class_="_timestamp")
      if date_span is not None:
        tweet['created_at'] = float(date_span['data-time-ms'])

      # Tweet Retweets
      retweet_span = li.select("span.ProfileTweet-action--retweet > span.ProfileTweet-actionCount")
      if retweet_span is not None and len(retweet_span) > 0:
        tweet['retweet_count'] = int(retweet_span[0]['data-tweet-stat-count'])

      # Tweet Likes
      like_span = li.select("span.ProfileTweet-action--favorite > span.ProfileTweet-actionCount")
      if like_span is not None and len(like_span) > 0:
        tweet['favourite_count'] = int(like_span[0]['data-tweet-stat-count'])

      # Tweet Replies
      reply_span = li.select("span.ProfileTweet-action--reply > span.ProfileTweet-actionCount")
      if reply_span is not None and len(reply_span) > 0:
        tweet['reply_count'] = int(reply_span[0]['data-tweet-stat-count'])

      tweet["user_mentions"] = format_user_mentions(li.find_all('a', {'class':'twitter-atreply'}))
      tweet["hashtags"] = format_hashtags(li.find_all('a', {'class':'twitter-hashtag'}))
      tweet["urls"] = format_urls(li.find_all('a'))

      tweets.append(tweet)

  return tweets

def format_user_mentions(mentions):
  new_mentions = []
  for mention in mentions:
    new_mentions.append({"id":mention["data-mentioned-user-id"], "screen_name":mention["href"]})
  return new_mentions

def format_hashtags(hashtags):
  new_hashtags = []
  for hashtag in hashtags:
    new_hashtags.append(hashtag.get_text().lstrip().rstrip())
  return new_hashtags

def format_urls(urls):
  new_urls = []
  for anchor in urls:
    if(anchor.has_attr('data-expanded-url')):
      new_urls.append(anchor['data-expanded-url'])
  return new_urls

def search_twitter(driver, org, max_tweets):
  driver.get("https://www.twitter.com/" + org)

  # wait until the search box has loaded:
  box = driver.wait.until(EC.presence_of_element_located((By.NAME, "q")))
  soup = bs(driver.page_source, 'lxml')
  try:
    available_to_scrape = int(soup.find("a", {"data-nav":"tweets"}).find("span", {"class":'ProfileNav-value'})['data-count'])
  except:
    available_to_scrape = 0
  # find the search box in the html:
  
  # Protected
  if(soup.find('div', {'class':'ProtectedTimeline'}) != None):
    available_to_scrape = 0

  # Temporarily disabled
  if(soup.find('div', {'class':'ProfileWarningTimeline'}) != None):
    available_to_scrape = 0

  wait = WebDriverWait(driver, 1)
  try:
    # wait until the first search result is found. Search results will be tweets, which are html list items and have the class='data-item-id':
    old_page = driver.find_element_by_tag_name('html')
    # tweets = driver.find_elements_by_css_selector("li[data-item-id]")

    last_height = driver.execute_script("return document.body.scrollHeight")

    tweets = []
    max_tweets = min(max_tweets, available_to_scrape)
    error_count = 0; max_error_count = 10
    # while (len(tweets) < max_tweets and available_to_scrape >= max_tweets and datetime.datetime.now() - begin < max_time_elapsed):
    if(max_tweets == 0):
      return driver.page_source

    for i in range(int(max_tweets / 20) + 10):    
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        new_height = driver.execute_script("return document.body.scrollHeight")

        # print("here")
        # if new_height == last_height:
        #   break
        # else:
        #   last_height = new_height

        # wait.until(staleness_of(old_page))
        # Max Tweets reached

        try:
          if(driver.find_element_by_xpath('//button[text()="Back to top ↑"]').is_displayed() == True):
            break
        except:
          pass

        try:
          wait.until(wait_for_more_than_n_elements_to_be_present(
              (By.CSS_SELECTOR, "li[data-item-id]"), 20 * i))
        except TimeoutException:
          error_count += 1
          time.sleep(1)
          print(org, error_count)
          if(error_count > max_error_count):
            sys.exit(1)
            raise TimeoutException

        tweets = driver.find_elements_by_css_selector("li[data-item-id]")
        old_page = driver.find_element_by_tag_name('html')

        if(len(tweets) >= max_tweets):
          break

    # time.sleep(10000000)

    # # scroll down to the last tweet until there are no more tweets:
    # number_of_tweets = len(tweets)
    # while number_of_tweets < max_tweets:
    #   try:
    #     driver.execute_script("arguments[0].scroll1IntoView();", tweets[-1])
    #     tweets = driver.find_elements_by_css_selector("li[data-item-id]")
    #     # find number of visible tweets:
    #     number_of_tweets = len(tweets)
        
    #     wait.until(staleness_of(old_page))
    #     old_page = driver.find_element_by_tag_name('html')

    #   except TimeoutException:
    #     time.sleep(1)
        
      # except Exception as e:
      #   raise Exception(e)

      # try:
      #   # wait for more tweets to be visible:
      #   wait.until(wait_for_more_than_n_elements_to_be_present(
      #       (By.CSS_SELECTOR, "li[data-item-id]"), number_of_tweets))

      # except TimeoutException:
      #   # if no more are visible the "wait.until" call will timeout. Catch the exception and exit the while loop:
      #   # time.sleep(2)
      #   break

    # extract the html for the whole lot:
    page_source = driver.page_source

  except TimeoutException:
    print("Timed Out")
    # if there are no search results then the "wait.until" call in the first "try" statement will never happen and it will time out. So we catch that exception and return no html.
    page_source = driver.page_source

  return page_source

class wait_for_more_than_n_elements_to_be_present(object):
  def __init__(self, locator, count):
    self.locator = locator
    self.count = count

  def __call__(self, driver):
    try:
      elements = EC._find_elements(driver, self.locator)
      return len(elements) > self.count
    except StaleElementReferenceException:
      return False

def init_driver():
  # initiate the driver:
  driver = webdriver.Firefox() #r"/home/salec006/Twitter_Scraper")

  # set a default wait time for the browser [5 seconds here]:
  driver.wait = WebDriverWait(driver, 1)

  # driver.get("https://www.twitter.com/login")
  # driver.wait.until(EC.presence_of_element_located((By.NAME, "session[username_or_email]")))
  # time.sleep(1)
  # driver.find_element_by_class_name("js-username-field").send_keys('salec006@umn.edu')
  # time.sleep(1)
  # driver.find_element_by_class_name("js-password-field").send_keys('ResearchPurposes')
  # time.sleep(1)
  # driver.find_element_by_class_name("EdgeButtom--medium").click()
  # time.sleep(1)
  
  return driver

def close_driver(driver):
  driver.close()
  return

def make_directory(dirname):
  if not os.path.exists(dirname):
    os.makedirs(dirname)

if __name__ == "__main__":
  # start a driver for a web browser:
  driver = init_driver() 

  users_to_scrape = ["AltNews", "AnkitBajpai1978", "Truth_inLies", "Jay03811550", "CuriousIndian10", "JnS_Conglo", "SheenuDr", "shad_ind", "Amazinglyjeet", "dhirajbhasin2", "sayk_art", "IndiaInMyBlood_", "Anandkvp0207", "_imveeresh", "zoo_bear", "monotoshmittra", "puriyash41", "aazzeemm", "TheYessarTribe", "harry1_samm", "HappyIndian_", "PurpleAmythyst", "vvenkataramu", "jahfaljaseel", "AdithyaPatelR", "Berojgar_Engg", "LyRajesh", "Pradeep90187743", "NKaul24", "SurrealDawn", "ifrarkhan", "gyaani_baba1", "sk1990_sk", "AlChutiyaap", "Arshil0", "iashann", "roshanbesekar", "silvertongue_me", "CmaSureshPetkar", "suresh104sfi", "love_India88", "MuraliMohanRat1", "IndiasBigdebate", "abhicoolpal", "goodsamaratin", "naishadhvyas", "Hippie37278802", "sabirspf", "ahmadh4all", "Official_Z_Khan", "WalterM42438719", "basu_smarajit", "anupamkanu", "Hassanbadshah", "retheeshraj10", "ShankarGopalak", "BinoyJana10", "Popat_Patra", "MibManD", "NaidGorle", "PyarSeMario", "mohit2853", "mv_krishnarao", "wkp1971", "R_Rock2105", "daaktardush", "bsjass1", "amitaman", "honeymassey2018", "SaniaFarooqui", "raviiitd", "kas256"]
  for user in users_to_scrape:
    page_source = search_twitter(driver, user, 100)
    
    make_directory("./Users/" + sys.argv[1])
    outptr = open("./Users/" + sys.argv[1] + "/user_" + user + ".txt", mode = "w")

    # extract info from the search results:
    soup = bs(page_source, 'lxml')
    tweets = extract_tweets(soup)
    print(len(tweets))
    print(tweets, file = outptr)

  # close the driver:
  close_driver(driver)