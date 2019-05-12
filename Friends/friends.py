import sys
import shutil
import time
import threading
import csv
from os import listdir
from os.path import isfile, join
import urllib
from urllib.request import urlopen, Request
import lxml.html
import datetime
import os
from bs4 import BeautifulSoup

######################################################
###### CONFIG VARIABLES - Changeable Parameters ######
######################################################

max_threads = 10       # How many simultaneous threads
max_level = 1          # Depth of graph
max_retry = 10         # Retries in case of error
epsilon_diff = 10 

# If you want to resume from a certain level
# level 0 is input layer
# Default - Start scraping from layer 1
start_level = 1
        
######################################################
######################################################

path = "result_output/Level"
headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}
thread_friend_counts = [0] * max_threads
all_done = {}
num_edges = 0

def main():
  global all_done
  global max_threads
  global max_level  
  global thread_friend_counts
  global num_edges
  global start_level

  if(len(sys.argv) > 1 and sys.argv[1] == "-reset"):
    reset_folders()    

  if(len(sys.argv) > 2 and sys.argv[2][:len('-start')] == "-start"):
    start_level = int(sys.argv[2][len('-start'):])

  #########################
  #### Open Log Files ####
  make_directory('LogFiles')

  tmp_time = str(datetime.datetime.now())
  log_file = open("LogFiles/log_file_" + tmp_time, "w")
  log_file_writer = csv.writer(log_file)
  friend_count_file = open("LogFiles/friend_counts_" + tmp_time, "w")
  friend_count_writer = csv.writer(friend_count_file)
  #########################

  for cur_level in range(start_level, 1 + max_level):
    cur_files = [f for f in listdir(path + str(cur_level-1)) if isfile(path + str(cur_level-1) + "/" + f)]
    make_directory(path + str(cur_level))

    # Generate friends for everyone in cur_files      
    threads = [None] * max_threads  
    for f in cur_files:
      # Read in all friends of this file
      with open(path + str(cur_level-1) + "/" + f, mode='r') as inptr:
        reader = csv.reader(inptr)

        friend = next_friend(reader, cur_level) # First friend
        while True:        
          try:
            # We already have friends then don't recompute
            if(not(friend in all_done)):                    
              for thread_num in range(max_threads): # if we have space
                if(threads[thread_num] == None or not(threads[thread_num].isAlive())):
                  num_edges += thread_friend_counts[thread_num]
                  thread_friend_counts[thread_num] = 0

                  threads[thread_num] = threading.Thread(target=generateFriends, args=(friend, cur_level, thread_num, log_file_writer, friend_count_writer))
                  threads[thread_num].start()
                  all_done[friend] = True

                  friend = next_friend(reader, cur_level)

                  print("\nStart thread for: ", friend, " at ", str(datetime.datetime.now()))
                  print("Total nodes processed = ", len(all_done))
                  break
            else:
              friend = next_friend(reader, cur_level)
          
          except StopIteration:
            break # We sucessfuly read the whole list

          except KeyboardInterrupt:
            log_file.close()
            friend_count_file.close()
            sys.exit()

    for thread_num in range(max_threads):
      if(threads[thread_num] != None):
        threads[thread_num].join()

  log_file_writer.writerow([]) # Next line
  log_file_writer.writerow(["Total nodes processed: ", str(len(all_done))])
  log_file_writer.writerow(["Total edges seen: ", str(num_edges)])
  log_file.close()
  friend_count_file.close()

def generateFriends(org, level, thread_num, log_file_writer, friend_count_writer):
  global max_retry
  global epsilon_diff

  # Open page
  link = "https://mobile.twitter.com/" + org + "/following"  
  outptr = open(path + str(level) + "/friends_" + org + ".txt", mode='w', encoding="utf-8")
  writer = csv.writer(outptr, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)  
  
  try:
    req = Request(link, headers=headers)
    page = urlopen(req)
    doc = lxml.html.fromstring(page.read())
  
  except urllib.error.HTTPError as e:
    outptr.close()
    log_file_writer.writerow(["\nUser does not exist anymore: ", org])
    return 0

  # Extract number of friends for later verification
  try:
    num_friends = int(doc.xpath('//*[@id="main_content"]/div/div[1]/table/tr[2]/td/span/text()')[0].replace(',', ''))
  
  except:
    outptr.close()
    log_file_writer.writerow(["User is protected: ", org])  
    print("User is protected " + org)
    return 0

  # Extract first 20 friends
  friends = doc.xpath('//span[@class="username"]/text()')[1:]
  num_scraped_friends = len(friends)
  for friend in friends:
      writer.writerow([friend, org])

  # Click on Show More and continue till we get all friends
  error_count = 0
  while(abs(num_scraped_friends - num_friends) > epsilon_diff and error_count < max_retry):
    try:
      link = "https://mobile.twitter.com/" + doc.xpath('//*[@id="main_content"]/div/div[2]/div/a')[0].get('href')
    except Exception as e:
      if(abs(num_scraped_friends - num_friends) < epsilon_diff):
        break

      log_file_writer.writerow(["Error: ", e])
      printPage(page, "Error#" + str(error_count) + "_" + org)
      error_count += 1
      time.sleep(1)

    req = Request(link, headers=headers)
    page = urlopen(req)

    # Make sure we have a good page read
    while(page.getcode() > 400):
      print(org, link, page.getcode())
      time.sleep(1)
      page = urlopen(req)

    doc = lxml.html.fromstring(page.read())
    friends = doc.xpath('//span[@class="username"]/text()')[1:]
    num_scraped_friends += len(friends)
    for friend in friends:
        writer.writerow([friend, org])

  if(abs(num_scraped_friends - num_friends) > epsilon_diff):
    print("\nUser not fully extracted ", org, num_scraped_friends, num_friends, link)
    log_file_writer.writerow(["\nUser not fully extracted ", org, num_scraped_friends, num_friends, link])
    printPage(page, org)

  thread_friend_counts[thread_num-1] = num_scraped_friends
  friend_count_writer.writerow([org, str(num_friends), str(num_scraped_friends)])
  outptr.close()
  return num_scraped_friends

def reset_folders():
  sub_dirs = [f.path for f in os.scandir("./result_output") if ("Level0" not in f.path and f.is_dir())]
  for cur_dir in sub_dirs:
    shutil.rmtree(cur_dir)

def printPage(page, name):
  soup = BeautifulSoup(page.read(), 'lxml')
  if not os.path.exists('ErrorFiles/'):
    os.makedirs('ErrorFiles')
  misc = open("ErrorFiles/" + name + ".html", "w")
  print(soup.prettify(), file = misc)
  misc.close() 

def make_directory(name):
  if not os.path.exists(name):
    os.makedirs(name)

def next_friend(reader, cur_level):
  if(cur_level != 1):
    return next(reader)[1]
  return next(reader)[0]

if __name__=="__main__":
  main()