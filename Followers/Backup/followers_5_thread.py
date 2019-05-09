import threading
import csv
from os import listdir
from os.path import isfile, join
import urllib
from urllib.request import urlopen, Request
import lxml.html
import datetime
import os
# from bs4 import BeautifulSoup

headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}
all_done = {}
thread_follower_counts = [0, 0, 0, 0, 0]

def main():
  global headers
  global all_done
  global thread_follower_counts

  max_level = 2
  seen = 0

  if not os.path.exists('LogFiles/'):
      os.makedirs('LogFiles')

  log_file = open("LogFiles/log_file_" + str(datetime.datetime.now()), "w")

  for cur_level in range(1, 1+max_level):
    cur_files = [f for f in listdir("result_output/Level" + str(cur_level-1)) if isfile("result_output/Level" + str(cur_level-1) + "/" + f)]
    if not os.path.exists('result_output/Level' + str(cur_level)):
      os.makedirs('result_output/Level' + str(cur_level))

    # Generate followers for everyone in cur_files      
    for f in cur_files:
      all_followers = []
      with open("result_output/Level" + str(cur_level-1) + "/" + f, mode='r') as inptr:
        reader = csv.reader(inptr)
        for row in reader:
          all_followers.append(row[0])

      follower_index = 0
      while follower_index < (len(all_followers) - 5):
        follower1 = all_followers[follower_index]
        follower2 = all_followers[follower_index + 1]
        follower3 = all_followers[follower_index + 2]
        follower4 = all_followers[follower_index + 3]
        follower5 = all_followers[follower_index + 4]

        follower_index += 5

        thread_follower_counts = [0, 0, 0, 0, 0]

        f1 = threading.Thread(target=generateFollowers, args=(follower1, cur_level, log_file, 1))
        f2 = threading.Thread(target=generateFollowers, args=(follower2, cur_level, log_file, 2))
        f3 = threading.Thread(target=generateFollowers, args=(follower3, cur_level, log_file, 3))
        f4 = threading.Thread(target=generateFollowers, args=(follower4, cur_level, log_file, 4))
        f5 = threading.Thread(target=generateFollowers, args=(follower5, cur_level, log_file, 5))

        # Start 5 threads simultaneously
        # We already have followers then don't recompute
        try:
          if(not(follower1 in all_done)):
            all_done[follower1] = True
            f1.start()

          if(not(follower2 in all_done)):
            all_done[follower2] = True
            f2.start()

          if(not(follower3 in all_done)):
            all_done[follower3] = True
            f3.start()

          if(not(follower4 in all_done)):
            all_done[follower4] = True
            f4.start()

          if(not(follower5 in all_done)):
            all_done[follower5] = True
            f5.start()

          # Wait till all threads finish
          f1.join()
          f2.join()
          f3.join()
          f4.join()
          f5.join()

          seen += sum(thread_follower_counts)
          print(thread_follower_counts[0], thread_follower_counts[1], thread_follower_counts[2], thread_follower_counts[3], thread_follower_counts[4])          
          print("Total nodes processed = ", len(all_done))
          print("Total edges seen = ", seen)
        
        except KeyboardInterrupt:
          f1.kill_recieved = True
          f2.kill_recieved = True
          f3.kill_recieved = True
          f4.kill_recieved = True
          f5.kill_recieved = True

          seen += sum(thread_follower_counts)
          print(thread_follower_counts[0], thread_follower_counts[1], thread_follower_counts[2], thread_follower_counts[3], thread_follower_counts[4])
          print("Total nodes processed = ", len(all_done))
          print("Total edges seen = ", seen)
          raise Exception("Kill")
      
      while follower_index < len(all_followers):
        follower = all_followers[follower_index]
        follower_index += 1

        # We already have friends then don't recompute
        if(not(follower in all_done)):
          seen += generateFollowers(follower, cur_level, log_file, 1)
          all_done[follower] = True

        print("Total nodes processed = ", len(all_done))
        print("Total edges seen = ", seen)
            
  print("Total nodes processed = " + str(len(all_done)), file = log_file)
  print("Total edges seen = " + str(seen), file = log_file)

def generateFollowers(org, level, log_file, thread_num):
  global thread_follower_counts
  # Open page
  link = "https://mobile.twitter.com/" + org + "/followers"
  
  try:
    req = Request(link, headers=headers)
    page = urlopen(req)
    doc = lxml.html.fromstring(page.read())
    # Extract first 20 followers
    followers = doc.xpath('//span[@class="username"]/text()')[1:]
          
    # Click on Show More and continue till we get all followers
    while(True):
      try:
        link = "https://mobile.twitter.com/" + doc.xpath('//*[@id="main_content"]/div/div[2]/div/a')[0].get('href')
        req = Request(link, headers=headers)
        page = urlopen(req)
        # print(page.geturl())
        doc = lxml.html.fromstring(page.read())
        followers += doc.xpath('//span[@class="username"]/text()')[1:]
      except:
        # Exception might mean a) we have reached end or
        #                      b) some type of timeout
        # Therefore try once more to make sure we have collected all followers
        try:
          link = "https://mobile.twitter.com/" + doc.xpath('//*[@id="main_content"]/div/div[2]/div/a')[0].get('href')
          req = Request(link, headers=headers)
          page = urlopen(req)
          doc = lxml.html.fromstring(page.read())
          followers += doc.xpath('//span[@class="username"]/text()')[1:]
        except Exception as e:
          # If we had exception on the second try
          # we can be confident that we have all followers
          break
      thread_follower_counts[thread_num-1] = len(followers)

    # Write followers to file
    with open("result_output/Level" + str(level) + "/followers_" + org + ".txt", mode='w', encoding="utf-8") as outptr:
      writer = csv.writer(outptr, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
      for follower in followers:
        writer.writerow([follower, org])

    thread_follower_counts[thread_num-1] = len(followers)
    return len(followers)

  except urllib.error.HTTPError as e:
    print("User does not exist anymore: ", org, file = log_file)
    return 0

# def printPage(req):
#   page = urlopen(req)
#   soup = BeautifulSoup(page.read(), 'lxml')
#   misc = open("error.html", "w")
#   print(soup.prettify(), file = misc)
#   misc.close() 

if __name__=="__main__":
  main()