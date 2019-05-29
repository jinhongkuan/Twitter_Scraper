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
max_level = 1          # Depth of graph
max_retry = 10         # Retries in case of error
epsilon_diff = 25 

global_repository = "./Friends"
        
######################################################
######################################################

headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}

all_done = {}
num_edges = 0
file_queue = queue.Queue()
threads = [None] * max_threads 
thread_friend_counts = [0] * max_threads

def main():   
  global num_edges

  if("-reset" in sys.argv):
    reset_folders()

  if(len(sys.argv) < 2):
    print("Usage: python3 friends.py -retweetID")
    sys.exit(1)

  make_directory(global_repository) # if it does not already exist  
  make_directory(global_repository + "/Tmp_Files")
  inputID = sys.argv[1][1:]
  with open("retweets_" + inputID + ".txt", "r") as inptr:
    reader = csv.reader(inptr)
    with open(global_repository + "/Tmp_Files/tmp_input_file", "w") as input_tmp_file:
      writer = csv.writer(input_tmp_file)
      for row in reader:
        writer.writerow(["dummy", row[2]])

  file_queue.put((0, "Tmp_Files/tmp_input_file"))

  #########################################      
  # Build Dictionary from Global repository
  #########################################

  print("Building Global Dictionary...")
  all_files = [f for f in listdir(global_repository) if isfile(global_repository + "/" + f)]
  for f in all_files:
    all_done[all_strip(f, ["followers_", "friends_", ".txt"])] = True
  print("Global dictionary built.\n")
  #########################################

  #########################
  #### Open Log Files ####
  #########################  
  make_directory('LogFiles')

  tmp_time = str(datetime.datetime.now())

  with open("LogFiles/log_file_" + tmp_time, "w") as log_file, open("LogFiles/friend_counts_" + tmp_time, "w") as friend_count_file, open("LogFiles/incomplete_friends_scraped_", "w") as incomplete_scraped:
    log_file_writer = csv.writer(log_file)
    friend_count_writer = csv.writer(friend_count_file)
    incomplete_scraped_writer = csv.writer(incomplete_scraped)
  #########################
  
    # Lock for semaphore
    lock = threading.Lock() 
    while(not file_queue.empty()):
      # Accessing queue with semaphore
      lock.acquire()
      tmp_level, f = file_queue.get()
      lock.release()

      file_name = global_repository + "/" + f

      # Read in all followers of this file
      with open(file_name, mode='r') as inptr:
        reader = csv.reader(inptr)
        try:
          friend = next_friend(reader) # First friend
          while True:        
            # We already have friends then don't recompute
            if(not(friend in all_done)):
              for thread_num in range(max_threads): # if we have space
                if(threads[thread_num] == None or not(threads[thread_num].isAlive())):
                  num_edges += thread_friend_counts[thread_num]
                  thread_friend_counts[thread_num] = 0

                  print("\nStart thread for: ", friend, " at ", str(datetime.datetime.now()))
                  # print("Total nodes processed = ", len(all_done))

                  threads[thread_num] = threading.Thread(target=generateFriends, args=(friend, tmp_level+1, thread_num, log_file_writer, friend_count_writer, incomplete_scraped_writer, lock))
                  threads[thread_num].start()
                  all_done[friend] = True

                  friend = next_friend(reader)
                  break
            else:
              if(tmp_level + 1 < max_level):
                file_queue.put((tmp_level + 1, "friends_" + friend + ".txt"))
              friend = next_friend(reader)

        except StopIteration:
          break # We sucessfuly read the whole list

        except KeyboardInterrupt:
          sys.exit()

        while(file_queue.empty() and is_somethread_alive()):
          time.sleep(1)

    for thread_num in range(max_threads):
      if(threads[thread_num] != None):
        threads[thread_num].join()

def is_scraping_complete(f, cur_level):
  # (completed, scraped_count) = file_line_count(path + str(cur_level) + "/" + f)
  # if(completed):
  #   return True

  # f = all_strip(f, ["friends_", "friends_", ".txt"])

  # try:
  #   link = "https://mobile.twitter.com/" + f + "/followers"
  #   req = Request(link, headers=headers)
  #   page = urlopen(req)
  #   doc = lxml.html.fromstring(page.read())
  #   total_followers = int(doc.xpath('//*[@id="main_content"]/div/div[1]/table/tr[2]/td/span/text()')[0].replace(',', ''))

  # except Exception as e:
  #   print(e)
  #   return True

  # if(total_followers - scraped_count < epsilon_diff):
  #   return True

  return False

def generateFriends(org, level, thread_num, log_file_writer, friend_count_writer, incomplete_scraped_writer, lock):
  try:
    # Open page
    link = "https://mobile.twitter.com/" + org + "/following"  
    outptr = open(global_repository + "/Tmp_Files/friends_" + org + ".txt", mode='w', encoding="utf-8")
    writer = csv.writer(outptr, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)  
    
    try:
      req = Request(link, headers=headers)
      page = urlopen(req)
      doc = lxml.html.fromstring(page.read())
    
    except urllib.error.HTTPError as e:
      outptr.close()
      log_file_writer.writerow(["\nUser does not exist anymore: ", org])
      shutil.copy(global_repository + "/Tmp_Files/friends_" + org + ".txt", global_repository)
      os.remove(global_repository + "/Tmp_Files/friends_" + org + ".txt")
      return 0

    # Extract number of friends for later verification
    try:
      num_friends = int(doc.xpath('//*[@id="main_content"]/div/div[1]/table/tr[2]/td/span/text()')[0].replace(',', ''))

    except:
      outptr.close()
      log_file_writer.writerow(["User is protected: ", org])  
      print("User is protected " + org)
      shutil.copy(global_repository + "/Tmp_Files/friends_" + org + ".txt", global_repository)
      os.remove(global_repository + "/Tmp_Files/friends_" + org + ".txt")
      return 0

    # Extract first 20 friends
    friends = doc.xpath('//span[@class="username"]/text()')[1:]
    num_scraped_friends = len(friends)
    for friend in friends:
        writer.writerow([org, friend])

    # Click on Show More and continue till we get all friends
    error_count = 0
    while(error_count < max_retry):
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
          writer.writerow([org, friend])

    if(abs(num_scraped_friends - num_friends) > epsilon_diff):
      incomplete_scraped_writer.writerow(["User not fully extracted", num_scraped_friends, num_friends, link])
      print("\nUser not fully extracted ", org, num_scraped_friends, num_friends, link)
      log_file_writer.writerow(["\nUser not fully extracted ", org, num_scraped_friends, num_friends, link])
      printPage(page, org)
      outptr.close()      
    else:
      outptr.close()
      shutil.copy(global_repository + "/Tmp_Files/friends_" + org + ".txt", global_repository)
      os.remove(global_repository + "/Tmp_Files/friends_" + org + ".txt")

    thread_friend_counts[thread_num-1] = num_scraped_friends
    friend_count_writer.writerow([org, str(num_friends), str(num_scraped_friends)])
    # writer.writerow(["This user has been scraped completely"])

    # Semaphore
    if(level < max_level):
      lock.acquire()
      file_queue.put((level, "friends_" + org + ".txt"))
      lock.release()

    return num_scraped_friends

  except Exception as e:
    print("\n\n\n\n Exception - Thread Compromised on user ", org, level, thread_num)
    time.sleep(10)
    return 0

def reset_folders():
  sub_dirs = [f.path for f in os.scandir("./LogFiles")]
  for cur_dir in sub_dirs:
    if(isfile(cur_dir)):
      os.remove(cur_dir)
    else:
      shutil.rmtree(cur_dir)

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

def next_friend(reader):
  return next(reader)[1]

def is_somethread_alive():
  for thread_num in range(max_threads):
    if(threads[thread_num] != None and threads[thread_num].isAlive()):
      return True
  return False

def file_line_count(filename):
    f = open(filename, "r+")
    completed = False

    try:
      buf = mmap.mmap(f.fileno(), 0)
    except ValueError:
      f.close()
      return (False, 0)

    lines = 0
    readline = buf.readline
    while True:
      tmp_line = readline()
      if (tmp_line == b"This user has been scraped completely"):
        completed = True
      if (not tmp_line):
        break
      lines += 1

    f.close()
    return (completed, lines)

def all_strip(s, l):
  for t in l:
    idx = s.find(t)
    if(idx != -1):
      s = s[:idx] + s[idx+len(t):]
  return s

if __name__=="__main__":
  main()