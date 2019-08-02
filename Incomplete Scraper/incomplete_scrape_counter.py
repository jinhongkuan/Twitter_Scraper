import os
import sys
import csv
import time
import mmap
import queue
import shutil
import urllib
import datetime
import lxml.html
import threading
from os import listdir
from bs4 import BeautifulSoup
from os.path import isfile, join
from urllib.request import urlopen, Request

######################################################
###### CONFIG VARIABLES - Changeable Parameters ######
######################################################

max_threads = 10       # How many simultaneous threads
max_retry = 10         # Retries in case of error
epsilon_diff = 25            

global_repository = "./"
        
######################################################
######################################################

headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}

file_queue = queue.Queue()
threads = [None] * max_threads 
thread_follower_counts = [0] * max_threads

def main():   
  all_friend_files = [f for f in listdir(global_repository + "/All_Friends") if isfile(global_repository + "/All_Friends/" + f)] 
  all_follower_files = [f for f in listdir(global_repository + "/All_Followers") if isfile(global_repository + "/All_Followers/" + f)] 

  for file in all_friend_files + all_follower_files:
    file_queue.put((0, file))

  with open("scrape_counts", "w") as outptr:
    tmp_level, user = file_queue.get()
    while(not file_queue.empty()):
      try:
        for thread_num in range(max_threads): # if we have space
          if(threads[thread_num] == None or not(threads[thread_num].isAlive())):
            print(user, " started")
            threads[thread_num] = threading.Thread(target = is_scraping_complete, args = (user, outptr))
            threads[thread_num].start()
            mtp_level, user = file_queue.get()
            break
      except KeyboardInterrupt:
        sys.exit()

      while(file_queue.empty() and is_somethread_alive()):
        time.sleep(1)

    for thread_num in range(max_threads):
      if(threads[thread_num] != None):
        threads[thread_num].join()

def is_scraping_complete(file_name, outptr):
  f = all_strip(file_name, ["friends_l1_", "followers_l1_", "followers_", "friends_", ".txt"])

  try:
    link = "https://mobile.twitter.com/" + f
    
    flag = True
    while flag:
      try:
        req = Request(link, headers=headers)
        page = urlopen(req)
        flag = False

      except urllib.error.HTTPError as e:
        if('Too Many Requests' in str(e)):
          time.sleep(5)
        else:
          raise Exception(str(e))
          flag = False

    doc = lxml.html.fromstring(page.read())
    total_followers = int(doc.xpath('//*[@id="main_content"]/div[1]/table[2]/tr/td[3]/a/div[1]/text()')[0].replace(',', ''))
    total_friends = int(doc.xpath('//*[@id="main_content"]/div[1]/table[2]/tr/td[2]/a/div[1]/text()')[0].replace(',', ''))

    print(file_line_count(global_repository + '/All_Followers/followers_' + f + '.txt'))
    (scraped_followers, scraped_friends) = (file_line_count(global_repository + '/All_Followers/followers_' + f + '.txt'), file_line_count(global_repository + '/All_Friends/friends_' + f + '.txt'))
    print(f, total_followers, total_friends, scraped_followers, scraped_friends, sep = ', ')
    # print(f, total_followers, total_friends, scraped_followers, scraped_friends, sep = ', ', file = outptr)
  except Exception as e:
    print(e)


def printPage(page, name):
  soup = BeautifulSoup(page.read(), 'lxml')
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

def file_line_count(filename):
  try:
    f = open(filename, "r+")
  except:
    return 0

  try:
    buf = mmap.mmap(f.fileno(), 0)
  except ValueError:
    f.close()
    return 0

  lines = 0
  readline = buf.readline
  while True:
    tmp_line = readline()
    if (not tmp_line):
      break
    lines += 1

  f.close()
  return lines

def all_strip(s, l):
  for t in l:
    idx = s.find(t)
    if(idx != -1):
      s = s[:idx] + s[idx+len(t):]
  return s

if __name__=="__main__":
  # main()
  is_scraping_complete('followers_crguna.txt', None)
  # link = "http://mobile.twitter.com/PreranaSr"
  # req = Request(link, headers=headers)
  # page = urlopen(req)
  # printPage(page, "BarackObama Mobile")