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
max_level = 2          # Depth of graph
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
thread_follower_counts = [0] * max_threads
all_done = {}
num_edges = 0

def main():
  global all_done
  global max_threads
  global max_level  
  global thread_follower_counts
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
  follower_count_file = open("LogFiles/follower_counts_" + tmp_time, "w")
  follower_count_writer = csv.writer(follower_count_file)
  #########################

  for cur_level in range(start_level, 1 + max_level):
    cur_files = [f for f in listdir(path + str(cur_level-1)) if isfile(path + str(cur_level-1) + "/" + f)]
    make_directory(path + str(cur_level))

    # Generate followers for everyone in cur_files      
    threads = [None] * max_threads  
    for f in cur_files:
      # Read in all followers of this file
      with open(path + str(cur_level-1) + "/" + f, mode='r') as inptr:
        reader = csv.reader(inptr)

        follower = next_follower(reader) # First follower
        while True:        
          try:
            # We already have followers then don't recompute
            if(not(follower in all_done)):                    
              for thread_num in range(max_threads): # if we have space
                if(threads[thread_num] == None or not(threads[thread_num].isAlive())):
                  num_edges += thread_follower_counts[thread_num]
                  thread_follower_counts[thread_num] = 0

                  threads[thread_num] = threading.Thread(target=generateFollowers, args=(follower, cur_level, thread_num, log_file_writer, follower_count_writer))
                  threads[thread_num].start()
                  all_done[follower] = True

                  follower = next_follower(reader)

                  print("\nStart thread for: ", follower, " at ", str(datetime.datetime.now()))
                  print("Total nodes processed = ", len(all_done))
                  break
            else:
              follower = next_follower(reader)
          
          except StopIteration:
            break # We sucessfuly read the whole list

          except KeyboardInterrupt:
            log_file.close()
            follower_count_file.close()
            sys.exit()

    for thread_num in range(max_threads):
      if(threads[thread_num] != None):
        threads[thread_num].join()

  log_file_writer.writerow([]) # Next line
  log_file_writer.writerow(["Total nodes processed: ", str(len(all_done))])
  log_file_writer.writerow(["Total edges seen: ", str(num_edges)])
  log_file.close()
  follower_count_file.close()

def generateFollowers(org, level, thread_num, log_file_writer, follower_count_writer):
  global max_retry
  global epsilon_diff

  # Open page
  link = "https://mobile.twitter.com/" + org + "/followers"  
  outptr = open(path + str(level) + "/followers_" + org + ".txt", mode='w', encoding="utf-8")
  writer = csv.writer(outptr, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)  
  
  try:
    req = Request(link, headers=headers)
    page = urlopen(req)
    doc = lxml.html.fromstring(page.read())
  
  except urllib.error.HTTPError as e:
    outptr.close()
    log_file_writer.writerow(["\nUser does not exist anymore: ", org])
    return 0

  # Extract number of followers for later verification
  try:
    num_followers = int(doc.xpath('//*[@id="main_content"]/div/div[1]/table/tr[2]/td/span/text()')[0].replace(',', ''))
  
  except:
    outptr.close()
    log_file_writer.writerow(["User is protected: ", org])  
    print("User is protected " + org)
    return 0

  # Extract first 20 followers
  followers = doc.xpath('//span[@class="username"]/text()')[1:]
  num_scraped_followers = len(followers)
  for follower in followers:
      writer.writerow([follower, org])

  # Click on Show More and continue till we get all followers
  error_count = 0
  while(abs(num_scraped_followers - num_followers) > epsilon_diff and error_count < max_retry):
    try:
      link = "https://mobile.twitter.com/" + doc.xpath('//*[@id="main_content"]/div/div[2]/div/a')[0].get('href')
    except Exception as e:
      if(abs(num_scraped_followers - num_followers) < epsilon_diff):
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
    followers = doc.xpath('//span[@class="username"]/text()')[1:]
    num_scraped_followers += len(followers)
    for follower in followers:
        writer.writerow([follower, org])

  if(abs(num_scraped_followers - num_followers) > epsilon_diff):
    print("\nUser not fully extracted ", org, num_scraped_followers, num_followers, link)
    log_file_writer.writerow(["\nUser not fully extracted ", org, num_scraped_followers, num_followers, link])
    printPage(page, org)

  thread_follower_counts[thread_num-1] = num_scraped_followers
  follower_count_writer.writerow([org, str(num_followers), str(num_scraped_followers)])
  outptr.close()
  return num_scraped_followers

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

def next_follower(reader):
  return next(reader)[0]

if __name__=="__main__":
  main()