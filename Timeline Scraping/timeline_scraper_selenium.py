import os
import sys
import csv
import time
import mmap
import queue
import shutil
import urllib
import gecko
import datetime
import lxml.html
import threading
import tmp_clearing
from os import listdir
from bs4 import BeautifulSoup
from os.path import isfile, join
from urllib.request import urlopen, Request

######################################################
###### CONFIG VARIABLES - Changeable Parameters ######
######################################################

max_threads = 1        # How many simultaneous threads
max_retry = 10         # Retries in case of error
max_tweets_count = 100 # Number of tweets to scrape 
global_repository = "./Users"
        
######################################################
######################################################

headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}

# all_done = {}
num_edges = 0
file_queue = queue.Queue()
threads = [None] * max_threads 
thread_user_counts = [0] * max_threads
all_drivers = [gecko.init_driver() for i in range(max_threads)]

def main():   
  global num_edges

  if("-reset" in sys.argv):
    reset_folders()

  tmp_time = str(datetime.datetime.now())

  make_directory(global_repository + "/Tmp_Files")
  inputID = sys.argv[1][1:]
  with open("retweets_" + inputID + ".txt", "r") as inptr:
    reader = csv.reader(inptr)
    with open(global_repository + "/Tmp_Files/tmp_input_file_" + tmp_time, "w") as input_tmp_file:
      writer = csv.writer(input_tmp_file)
      for row in reader:
        writer.writerow([row[2]])

  file_queue.put("Tmp_Files/tmp_input_file_" + tmp_time)

  #########################################      
  # Build Dictionary from Global repository
  #########################################

  # make_directory(global_repository) # if it does not already exist
  # print("Building Global Dictionary...")
  # all_files = [f for f in listdir(global_repository) if isfile(global_repository + "/" + f)]
  # for f in all_files:
  #   all_done[all_strip(f, ["user_", ".txt"])] = True
  # print("Global dictionary built.\n")
  #########################################

  #########################
  #### Open Log Files ####
  #########################  
  make_directory('LogFiles')

  with open("LogFiles/log_file_" + tmp_time, "w") as log_file:
    with open("LogFiles/user_" + tmp_time, "w") as user_count_file:
      log_file_writer = csv.writer(log_file)
      user_writer = csv.writer(user_count_file)
  
  #########################
  
      # Lock for semaphore
      lock = threading.Lock() 
      while(not file_queue.empty()):
        # Accessing queue with semaphore
        lock.acquire()
        f = file_queue.get()
        lock.release()

        file_name = global_repository + "/" + f
        
        # Read in all users of this file
        with open(file_name, mode='r') as inptr:
          reader = csv.reader(inptr)
          try:
            user = next_user(reader) # First user
            while True:        
              # We already have users then don't recompute
              if(not already_scraped(user)):
                for thread_num in range(max_threads): # if we have space
                  if(threads[thread_num] == None or not(threads[thread_num].isAlive())):
                    num_edges += thread_user_counts[thread_num]
                    thread_user_counts[thread_num] = 0

                    print("\nStart thread for: ", user, " at ", str(datetime.datetime.now()))
                    # print("Total nodes processed = ", len(all_done))

                    threads[thread_num] = threading.Thread(target=generateUserModel, args=(user, thread_num, log_file_writer, user_writer, lock))
                    threads[thread_num].start()
                    # all_done[user] = True

                    user = next_user(reader)
                    break
              else:
                user = next_user(reader)

          except StopIteration:
            break # We sucessfuly read the whole list

          except KeyboardInterrupt:
            for i in range(max_threads):
              gecko.close_driver(all_drivers[i])
            tmp_clearing.clear_tmps()
            sys.exit()

          while(file_queue.empty() and is_somethread_alive()):
            time.sleep(1)

      for thread_num in range(max_threads):
        if(threads[thread_num] != None):
          threads[thread_num].join()

      for i in range(max_threads):
        gecko.close_driver(all_drivers[i])
      tmp_clearing.clear_tmps()

def generateUserModel(org, thread_num, log_file_writer, user_writer, lock):
  try:
    outptr = open(global_repository + "/Tmp_Files/user_" + org + ".txt", mode='w', encoding="utf-8")
    page_source = gecko.search_twitter(all_drivers[thread_num], org, max_tweets_count)
    soup = BeautifulSoup(page_source, 'lxml')

    # f = open("asdf.html", "w")
    # print(soup.prettify, file = f)
    # f.close()

    # User does not exist
    if(soup.find('form', {'class':'search-404'}) != None):
      outptr.close()
      log_file_writer.writerow(["\nUser does not exist anymore: ", org])
      print("User does not exist anymore: " + org)
      shutil.copy(global_repository + "/Tmp_Files/user_" + org + ".txt", global_repository)
      os.remove(global_repository + "/Tmp_Files/user_" + org + ".txt")
      return 0

    user_dict = print_user_to_file(soup, outptr, recalculate = False)

    if(user_dict["protected"]):
      outptr.close()
      log_file_writer.writerow(["User is protected: ", org])  
      print("User is protected " + org)
      shutil.copy(global_repository + "/Tmp_Files/user_" + org + ".txt", global_repository)
      os.remove(global_repository + "/Tmp_Files/user_" + org + ".txt")
      return 0    

    tweets = gecko.extract_tweets(soup)
    for tweet in tweets:
      print(tweet, file = outptr)
    num_tweets_scraped = len(tweets)

    if(num_tweets_scraped < max_tweets_count and int(user_dict["statuses_count"]) >= max_tweets_count):
      print("User not fully extracted", num_tweets_scraped, file = outptr)
      print("\nUser not fully extracted ", org, num_tweets_scraped)
      log_file_writer.writerow(["\nUser not fully extracted ", org, num_tweets_scraped])
      outptr.close()      
    else:
      outptr.close()
      shutil.copy(global_repository + "/Tmp_Files/user_" + org + ".txt", global_repository)
      os.remove(global_repository + "/Tmp_Files/user_" + org + ".txt")

    thread_user_counts[thread_num-1] = num_tweets_scraped
    user_writer.writerow([org, str(num_tweets_scraped)])
    return num_tweets_scraped

  # Too many requests
  except urllib.error.HTTPError as e:
    print("Too many requests ", e)
    time.sleep(10)
    return 0

  except Exception as e:
    print("\n\n\n\n Exception - Thread Compromised on user ", e, org, thread_num)
    time.sleep(10)
    return 0

def already_scraped(user):
  return False # isfile(global_repository + "/user_" + user + ".txt") or isfile(global_repository + "/Tmp_Files/user_" + user + ".txt")
  # try:
  #   fh = open(global_repository + "/followers_" + user + ".txt", "r")
  #   return True
  # except FileNotFoundError:
  #   return False


def extract_mobile_twitter(soup):
  return soup.find_all('table', {'class':'tweet'})  

def extract_desktop_twitter(soup):
  return soup.find_all('li', {'class':'js-stream-item'})  

# def print_to_file(tweets, org, file, medium):
#   if(medium == "mobile"):
#     for tweet in tweets:
#       tmp_dict = {}

#       if(tweet.find("div", {'class':'tweet-reply-context'}) != None):
#         tmp_dict["tweet_type"] = "reply"
#       elif(tweet.find("div", {'class':'tweet-social-context'}) != None):
#         tmp_dict["tweet_type"] = "retweet"
#       else:
#         tmp_dict["tweet_type"] = "source_tweet"

#       tmp_dict["created_at"] = tweet.find('td', {'class':'timestamp'}).get_text().lstrip().rstrip()
#       tmp_dict["tweet_text"] = tweet.find('div', {'class':'tweet-text'}).get_text().lstrip().rstrip()
#       tmp_dict["tweet_id"] = tweet.find('div', {'class':'tweet-text'})['data-id']
#       tmp_dict["user_mentions"] = format_user_mentions(tweet.find_all('a', {'class':'twitter-atreply'}))
#       tmp_dict["hashtags"] = format_hashtags(tweet.find_all('a', {'class':'twitter-hashtag'}))
#       tmp_dict["urls"] = format_urls(tweet.find_all('a'))
      
#       link = "https://www.twitter.com/" + org + "/status/" + tmp_dict["tweet_id"]

#       req = Request(link)
#       page = urlopen(req)
#       # printPage(page, "Tweet")

#       soup = BeautifulSoup(page.read(), 'lxml')
#       stats = soup.find_all('span', {'class':'ProfileTweet-actionCount'})
#       try:
#         tmp_dict["retweet_count"] = stats[1]['stat-count']
#       except:
#         tmp_dict["retweet_count"] = stats[1].get_text().lstrip().rstrip()
#       try:
#         tmp_dict["favourite_count"] = stats[2]['stat-count']   
#       except:
#         tmp_dict["favourite_count"] = stats[2].get_text().lstrip().rstrip()

#       print(tmp_dict, file = file)

#   elif(medium == "desktop"):        
#     for tweet in tweets:
#       tmp_dict = {}      

#       if(tweet.find("div", {'class':'tweet-reply-context'}) != None):
#         tmp_dict["tweet_type"] = "reply"
#       elif(tweet.find("span", {'class':'js-retweet-text'}) != None):
#         tmp_dict["tweet_type"] = "retweet"
#       else:
#         tmp_dict["tweet_type"] = "source_tweet"

#       try:
#         tmp_dict["created_at"] = tweet.find('a', {'class':'tweet-timestamp'}).get_text().lstrip().rstrip()
#       except Exception as e:
#         tmp_dict["created_at"] = ""
#         print("No created at ", org)

#       try:
#         tmp_dict["tweet_text"] = tweet.find('p', {'class':'tweet-text'}).get_text().lstrip().rstrip()
#       except Exception as e:
#         print("No tweet text ", org)
#         tmp_dict["tweet_text"] = ""

#       try:
#         tmp_dict["tweet_id"] = tweet["data-item-id"]
#       except Exception as e:
#         print("No tweet id: ", org)
#         tmp_dict["tweet_id"] = ""

#       tmp_dict["user_mentions"] = format_user_mentions(tweet.find_all('a', {'class':'twitter-atreply'}))
#       tmp_dict["hashtags"] = format_hashtags(tweet.find_all('a', {'class':'twitter-hashtag'}))
#       tmp_dict["urls"] = format_urls(tweet.find_all('a'))
#       stats = tweet.find_all('span', {'class':'ProfileTweet-actionCount'})
#       if(stats == []):
#         print("No stats: ", tmp_dict["tweet_id"])
#         stats = ["", "", ""]

#       try:
#         tmp_dict["retweet_count"] = stats[1]['stat-count']
#       except:
#         tmp_dict["retweet_count"] = stats[1].get_text().lstrip().rstrip()
#       try:
#         tmp_dict["favourite_count"] = stats[2]['stat-count']   
#       except:
#         tmp_dict["favourite_count"] = stats[2].get_text().lstrip().rstrip()

#       print(tmp_dict, file = file)

def print_user_to_file(soup, file, recalculate = True):    
  if(recalculate):
    link = "https://www.twitter.com/" + soup
    req = Request(link)
    page = urlopen(req)
    # printPage(page, "Test")
    soup = BeautifulSoup(page.read(), 'lxml')

  user_dict = {}
  user_dict["disabled"] = (soup.find('div', {'class':'ProfileWarningTimeline'}) != None)
  try:
    user_dict["protected"] = (soup.find('div', {'class':'ProtectedTimeline'}) != None)
  except:
    user_dict["protected"] = True
  try:
    user_dict["screen_name"] = soup.find('b', {'class':'u-linkComplex-target'}).get_text().lstrip().rstrip()
  except:
    user_dict["screen_name"] = ""
  try:
    user_dict["name"] = soup.find('a', {'class':'ProfileHeaderCard-nameLink'}).get_text().lstrip().rstrip()
  except:
    user_dict["name"] = ""
  try:
    user_dict["created_at"] = soup.find("span", {'class', 'ProfileHeaderCard-joinDateText'}).get_text().lstrip().rstrip()
  except:
    user_dict["created_at"] = ""
  try:
    user_dict["verified"] = (soup.find('span', {'class':'ProfileHeaderCard-badges'}) != None)
  except:
    user_dict["verified"] = False
  try:
    user_dict["id"] = soup.find("div", {'class':'ProfileNav'})['data-user-id']
  except:
    user_dict["id"] = ""
  
  try:
    user_dict["location"] = soup.find("span", {"class":"ProfileHeaderCard-locationText"}).get_text().lstrip().rstrip()
  except:
    user_dict["location"] = ""
  
  try:
    user_dict["statuses_count"] = soup.find("a", {"data-nav":"tweets"}).find("span", {"class":'ProfileNav-value'})['data-count']
  except:
    user_dict["statuses_count"] = 0
  
  try:
    user_dict["listed_count"] = soup.find("a", {"data-nav":"all_lists"}).find("span", {"class":'ProfileNav-value'}).get_text().lstrip().rstrip()
  except:
    user_dict["listed_count"] = 0
  
  try:
    user_dict["friends_count"] = soup.find("a", {"data-nav":"following"}).find("span", {"class":'ProfileNav-value'})['data-count']
  except:
    user_dict["friends_count"] = 0

  try:
    user_dict["followers_count"] = soup.find("a", {"data-nav":"followers"}).find("span", {"class":'ProfileNav-value'})['data-count']
  except:
    user_dict["followers_count"] = 0
  
  try:
    user_dict["favourites_count"] = soup.find("a", {"data-nav":"favorites"}).find("span", {"class":'ProfileNav-value'})['data-count']
  except:
    user_dict["favourites_count"] = 0
  
  print(user_dict, file = file)
  return user_dict

def reset_folders():
  sub_dirs = [f.path for f in os.scandir("./LogFiles")]
  for cur_dir in sub_dirs:
    if(isfile(cur_dir)):
      os.remove(cur_dir)
    else:
      shutil.rmtree(cur_dir)

def printPage(soup, name, t = False):
  if(not t):
    soup = BeautifulSoup(soup.read(), 'lxml')
  if not os.path.exists('LogFiles/ErrorFiles/'):
    os.makedirs('LogFiles/ErrorFiles')
  misc = open("LogFiles/ErrorFiles/" + name + ".html", "w")
  print(soup.prettify(), file = misc)
  misc.close() 

def make_directory(dirname):
  if not os.path.exists(dirname):
    os.makedirs(dirname)

def is_somethread_alive():
  for thread_num in range(max_threads):
    if(threads[thread_num] != None and threads[thread_num].isAlive()):
      return True
  return False

def next_user(reader):
  return next(reader)[0]

if __name__=="__main__":
  main()
  # link = "https://www.twitter.com/ahmadh4all/"
  # req = Request(link)
  # page = urlopen(req)
  # printPage(page, "Obama desktop")
  # 