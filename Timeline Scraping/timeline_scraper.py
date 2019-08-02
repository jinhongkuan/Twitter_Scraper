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
import requests
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

max_threads = 10       # How many simultaneous threads
max_retry = 10         # Retries in case of error
max_tweets_count = 50  # Number of tweets to scrape 
global_repository = "./Timeline_Data"
epsilon_diff = 10        
######################################################
######################################################

headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}

num_edges = 0
file_queue = queue.Queue()
threads = [None] * max_threads 
thread_user_counts = [0] * max_threads

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
        writer.writerow([row[0]])

  file_queue.put("Tmp_Files/tmp_input_file_" + tmp_time)

  #########################
  #### Open Log Files ####
  #########################  
  make_directory('LogFiles')

  with open("LogFiles/log_file_" + tmp_time, "w") as log_file, open('LogFiles/user_status_counts_' + tmp_time, 'w') as user_count:
    log_file_writer = csv.writer(log_file)
    user_count_writer = csv.writer(user_count)
    #########################

    # Lock for semaphore
    while(not file_queue.empty()):
      # Accessing queue with semaphore
      f = file_queue.get()
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

                  # print("\nStart thread for: ", user, " at ", str(datetime.datetime.now()))
                  # print("Total nodes processed = ", len(all_done))

                  threads[thread_num] = threading.Thread(target=generateUserModel, args=(user, thread_num, log_file_writer, user_count_writer))
                  threads[thread_num].start()
                  # all_done[user] = True

                  user = next_user(reader)
                  break
            else:
              user = next_user(reader)

        except StopIteration:
          break # We sucessfuly read the whole list

        except KeyboardInterrupt:
          sys.exit()

        while(file_queue.empty() and is_somethread_alive()):
          time.sleep(1)

    for thread_num in range(max_threads):
      if(threads[thread_num] != None):
        threads[thread_num].join()

def generateUserModel(org, thread_num, log_file_writer, user_count_writer):
  try:
    # Open page
    link = "https://mobile.twitter.com/" + org  
    outptr = open(global_repository + "/Tmp_Files/timeline_data_" + org + ".txt", mode='w', encoding="utf-8")
  
    flag = True
    while flag:
      try:
        req = Request(link, headers=headers)
        page = urlopen(req)
        soup = BeautifulSoup(page.read(), 'lxml')
        flag = False

      except urllib.error.HTTPError as e:
        if('Too Many Requests' in str(e)):
          print(org, 'Error - T')
          time.sleep(10)
        elif('Service Temporarily Unavailable' in str(e)):
          print(org, 'Error - S')
          time.sleep(10)
        else:
          outptr.close()
          log_file_writer.writerow(["\nUser does not exist anymore: ", org])
          shutil.copy(global_repository + "/Tmp_Files/timeline_data_" + org + ".txt", global_repository)
          os.remove(global_repository + "/Tmp_Files/timeline_data_" + org + ".txt")
          flag = False
          return 0    

    # Extract number of followers for later verification
    try:
      num_total_status = int(soup.find('td', class_='stat').find('div', class_='statnum').get_text().replace(',', ''))
    
    except:
      outptr.close()
      shutil.copy(global_repository + "/Tmp_Files/timeline_data_" + org + ".txt", global_repository)
      os.remove(global_repository + "/Tmp_Files/timeline_data_" + org + ".txt")
      return 0

    # Extract first 20 followers
    tweets = extract_tweets(soup)
    num_scraped_tweets = len(tweets)
    num_to_be_scraped = min(max_tweets_count, num_total_status)

    # write tweets to file
    write_tweets_to_file(tweets, outptr)

    # Click on Show More and continue till we get all followers
    error_count = 0
    while(num_scraped_tweets < num_to_be_scraped and error_count < max_retry):
      try:
        link = "https://mobile.twitter.com/" + soup.find('div', class_='w-button-more').find('a')['href']
      except KeyboardInterrupt:
        raise KeyboardInterrupt()
      except Exception as e:
          if(abs(num_scraped_tweets - num_to_be_scraped) < epsilon_diff):
            break

          log_file_writer.writerow(["Error: ", e])
          printPage(page, "Error#" + str(error_count) + "_" + org)
          error_count += 1
          time.sleep(1)

      flag = True
      while flag:
        try:
          req = Request(link, headers=headers)
          page = urlopen(req)
          flag = False

        except urllib.error.HTTPError as e:
          if('Too Many Requests' in str(e)):
            print('Error - T', org)
            time.sleep(10)
          elif('Service Temporarily Unavailable' in str(e)):
            print('Error - S', org)
            time.sleep(10)
          else:
            raise Exception(str(e))
            flag = False

      soup = BeautifulSoup(page.read(), 'lxml')
      tweets = extract_tweets(soup)
      num_scraped_tweets += len(tweets)
      write_tweets_to_file(tweets, outptr)

    if(num_to_be_scraped - num_scraped_tweets > epsilon_diff):
      print(org, num_scraped_tweets, num_to_be_scraped, error_count)

    outptr.close()
    shutil.copy(global_repository + "/Tmp_Files/timeline_data_" + org + ".txt", global_repository)
    os.remove(global_repository + "/Tmp_Files/timeline_data_" + org + ".txt")
    thread_user_counts[thread_num-1] = num_scraped_tweets
    user_count_writer.writerow([org, str(num_total_status), str(num_to_be_scraped), str(num_scraped_tweets)])

    return num_scraped_tweets

  except KeyboardInterrupt:
    raise KeyboardInterrupt()
  except Exception as e:
    print("\n\n\n\n Exception - Thread Compromised on user ", org, thread_num, e)
    time.sleep(5)
    return 0

def already_scraped(user):
  return isfile(global_repository + "/timeline_data_" + user + ".txt") or isfile(global_repository + "/Tmp_Files/timeline_data_" + user + ".txt")

def extract_tweets(soup):
  return soup.find_all('table', {'class':'tweet'})  

def write_tweets_to_file(tweets, file):
  for tweet in tweets:
    tmp_dict = {}

    if(tweet.find("div", {'class':'tweet-reply-context'}) != None):
      tmp_dict["tweet_type"] = "reply"
    elif(tweet.find("div", {'class':'tweet-social-context'}) != None):
      tmp_dict["tweet_type"] = "retweet"
    else:
      tmp_dict["tweet_type"] = "source_tweet"

    tmp_dict["created_at"] = tweet.find('td', {'class':'timestamp'}).get_text().lstrip().rstrip()
    tmp_dict["tweet_text"] = tweet.find('div', {'class':'tweet-text'}).get_text().lstrip().rstrip()
    tmp_dict["tweet_id"] = tweet.find('div', {'class':'tweet-text'})['data-id']
    # tmp_dict["user_mentions"] = format_user_mentions(tweet.find_all('a', {'class':'twitter-atreply'}))
    # tmp_dict["hashtags"] = format_hashtags(tweet.find_all('a', {'class':'twitter-hashtag'}))
    # tmp_dict["urls"] = format_urls(tweet.find_all('a'))
    
    print(tmp_dict, file = file)

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
  # link = "https://mobile.twitter.com/BarackObama/tweets"
  # # req = Request(link, headers = headers)
  # # page = urlopen(req)
  # soup = BeautifulSoup(requests.get(link).text, 'lxml')
  # printPage(soup, "Obama desktop -tweets", t = True)
  # # 
  # make_directory(global_repository + "/Tmp_Files")
  # generateUserModel('YoursSougata', 0, csv.writer(open('timepass', 'w')), csv.writer(open('counts', 'w')))