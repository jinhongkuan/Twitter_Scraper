import os
import sys
import csv
import time
import mmap
import queue
import shutil
import pickle
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
epsilon = 1000

global_repository = "./All_Incomplete_Followers"
        
######################################################
######################################################

headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}

num_edges = 0
file_queue = queue.Queue()
threads = [None] * max_threads 
thread_follower_counts = [0] * max_threads
all_cursors = {}

def main():   
  global num_edges
  global all_cursors

  tmp_time = str(datetime.datetime.now())

  make_directory(global_repository + "/Tmp_Files")
  inputID = sys.argv[1][1:]
  with open("retweets_" + inputID + ".txt", "r") as inptr:
    reader = csv.reader(inptr)
    with open(global_repository + "/Tmp_Files/tmp_input_file_" + tmp_time, "w") as input_tmp_file:
      writer = csv.writer(input_tmp_file)
      for row in reader:
        # If enough followers are missing
        if(int(row[0]) > epsilon):
          writer.writerow([row[2]])

  file_queue.put((0, "Tmp_Files/tmp_input_file_" + tmp_time))

  #########################
  #### Open Log Files ####
  #########################  
  make_directory('LogFiles')

  log_file = open("LogFiles/log_file_" + tmp_time, "w") 
  follower_count_file = open("LogFiles/follower_counts_" + tmp_time, "w") 
  incomplete_scraped = open("LogFiles/incomplete_followers_scraped_" + tmp_time, "w")
  try:
    log_file_writer = csv.writer(log_file)
    follower_count_writer = csv.writer(follower_count_file)
    incomplete_scraped_writer = csv.writer(incomplete_scraped)
    #########################
    # Lock for semaphore
    lock = threading.Lock() 
    if(os.path.isfile('./all_cursors_dump')):
      all_cursors = pickle.load(open('all_cursors_dump', 'rb'))
      print("Loaded all_cursors ", all_cursors)

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
          follower = next_follower(reader) # First follower
        except StopIteration:
          follower = None

        while (follower != None):        
          try:
            # We already have followers then don't recompute
            if(not os.path.isfile(global_repository + "/" + follower)):
              for thread_num in range(max_threads): # if we have space
                if(threads[thread_num] == None or not(threads[thread_num].isAlive())):
                  num_edges += thread_follower_counts[thread_num]
                  thread_follower_counts[thread_num] = 0

                  print("\nStart thread for: ", follower, " at ", str(datetime.datetime.now()))
                  # print("Total nodes processed = ", len(all_done))

                  threads[thread_num] = threading.Thread(target=generateFollowers, args=(follower, tmp_level+1, thread_num, log_file_writer, follower_count_writer, incomplete_scraped_writer, lock))
                  threads[thread_num].start()
                  # all_done[follower] = True

                  follower = next_follower(reader)
                  break

          except StopIteration:
            break # We sucessfuly read the whole list

        while(file_queue.empty() and is_somethread_alive()):
          time.sleep(1)

    for thread_num in range(max_threads):
      if(threads[thread_num] != None):
        threads[thread_num].join()

    log_file.close(); follower_count_file.close(); incomplete_scraped.close()

  except KeyboardInterrupt:
    log_file.close(); follower_count_file.close(); incomplete_scraped.close()
    print("Ctrl+C pressed. Exiting")
    sys.exit()

def generateFollowers(org, level, thread_num, log_file_writer, follower_count_writer, incomplete_scraped_writer, lock):
  num_scraped_followers = 0; num_followers = 0; link = ''
  
  try:
    # Open page
    if(org in all_cursors):
      link = all_cursors[org][0]
      num_scraped_followers = all_cursors[org][1]
      print(org, " resuming from ", num_scraped_followers)
      # Appending
      outptr = open(global_repository + "/Tmp_Files/followers_" + org + ".txt", mode='a', encoding="utf-8")
      writer = csv.writer(outptr, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)  
      
    else:
      link = "https://mobile.twitter.com/" + org + "/followers"  
      # Over writing
      outptr = open(global_repository + "/Tmp_Files/followers_" + org + ".txt", mode='w', encoding="utf-8")
      writer = csv.writer(outptr, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)  
      

    try:
      req = Request(link, headers=headers)
      page = urlopen(req)
      doc = lxml.html.fromstring(page.read())
    
    except urllib.error.HTTPError as e:
      outptr.close()
      log_file_writer.writerow(["\nUser does not exist anymore: ", org])
      shutil.copy(global_repository + "/Tmp_Files/followers_" + org + ".txt", global_repository)
      os.remove(global_repository + "/Tmp_Files/followers_" + org + ".txt")
      return 0

    # Extract number of followers for later verification
    try:
      num_followers = int(doc.xpath('//*[@id="main_content"]/div/div[1]/table/tr[2]/td/span/text()')[0].replace(',', ''))
    except KeyboardInterrupt:
      raise KeyboardInterrupt()
    except:
      outptr.close()
      log_file_writer.writerow(["User is protected: ", org])  
      print("User is protected " + org)
      shutil.copy(global_repository + "/Tmp_Files/followers_" + org + ".txt", global_repository)
      os.remove(global_repository + "/Tmp_Files/followers_" + org + ".txt")
      return 0

    # Extract first 20 followers
    followers = doc.xpath('//span[@class="username"]/text()')[1:]
    num_scraped_followers += len(followers)
    # As constant + percentage * total    
    num_to_be_scraped = num_followers
    # If as percentage
    # num_to_be_scraped = int(num_followers * (float(max_edges_restriction[level]) / 100.0))
    for follower in followers:
        writer.writerow([follower, org])

    # Click on Show More and continue till we get all followers
    error_count = 0; prev_dump = 0
    while(num_scraped_followers < num_to_be_scraped and error_count < max_retry):
      try:
        link = "https://mobile.twitter.com/" + doc.xpath('//*[@id="main_content"]/div/div[2]/div/a')[0].get('href')
      except KeyboardInterrupt:
        raise KeyboardInterrupt()
      except Exception as e:
        if(abs(num_scraped_followers - num_to_be_scraped) < epsilon_diff):
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
            time.sleep(5)
          elif('Service Temporarily Unavailable' in str(e)):
            time.sleep(5)
          else:
            raise Exception(str(e))
            flag = False

      doc = lxml.html.fromstring(page.read())
      followers = doc.xpath('//span[@class="username"]/text()')[1:]
      num_scraped_followers += len(followers)
      for follower in followers:
        writer.writerow([follower, org])

      if(num_scraped_followers > 0 and (num_scraped_followers // 5000 > prev_dump)):
        print(org, " has gathered ", num_scraped_followers)
        lock.acquire()
        all_cursors[org] = (link, num_scraped_followers)
        pickle.dump(all_cursors, open('all_cursors_dump', 'wb'))
        lock.release()
        prev_dump = num_scraped_followers // 5000

    if(abs(num_scraped_followers - num_to_be_scraped) > epsilon_diff):
      incomplete_scraped_writer.writerow(["User not fully extracted", num_scraped_followers, num_followers, num_to_be_scraped, level, link])
      print("\nUser not fully extracted ", org, num_scraped_followers, num_followers, link)
      log_file_writer.writerow(["\nUser not fully extracted ", org, num_scraped_followers, num_followers, num_to_be_scraped, level, link])
      printPage(page, org)
      outptr.close()      
    else:
      outptr.close()
      shutil.copy(global_repository + "/Tmp_Files/followers_" + org + ".txt", global_repository)
      os.remove(global_repository + "/Tmp_Files/followers_" + org + ".txt")

    thread_follower_counts[thread_num-1] = num_scraped_followers
    follower_count_writer.writerow([org, str(num_followers), str(num_to_be_scraped), str(num_scraped_followers)])
    # writer.writerow(["This user has been scraped completely"])

    return num_scraped_followers

  except KeyboardInterrupt:
    raise KeyboardInterrupt()

  except Exception as e:
    print("\n\n\n\n Exception - Thread Compromised on user ", org, level, thread_num, e)
    print("\nUser not fully extracted ", org, num_scraped_followers, num_followers, link)  
    time.sleep(10)
    return 0

def printPage(page, name):
  soup = BeautifulSoup(page.read(), 'lxml')
  if not os.path.exists('LogFiles/ErrorFiles/'):
    os.makedirs('LogFiles/ErrorFiles')
  misc = open("LogFiles/ErrorFiles/" + name + ".html", "w")
  print(soup.prettify(), file = misc)
  misc.close() 

def next_follower(reader):
  return next(reader)[0]

def is_somethread_alive():
  for thread_num in range(max_threads):
    if(threads[thread_num] != None and threads[thread_num].isAlive()):
      return True
  return False

def make_directory(dirname):
  if not os.path.exists(dirname):
    os.makedirs(dirname)

if __name__=="__main__":
  main()