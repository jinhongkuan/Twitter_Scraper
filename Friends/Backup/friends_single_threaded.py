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

def main():
  global headers
  global all_done
  
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
      all_friends = []
      with open("result_output/Level" + str(cur_level-1) + "/" + f, mode='r') as inptr:
        reader = csv.reader(inptr)
        for row in reader:
          # Small change from follower.py to keep input format consistent
          if(cur_level != 1):
            all_friends.append(row[1])
          else:
            all_friends.append(row[0])

      for friend in all_friends:
        # We already have friends then don't recompute
        if(not(friend in all_done)):
          seen += generateFriends(friend, cur_level, log_file)
          all_done[friend] = True

        print("Total nodes processed = ", len(all_done))
        print("Total edges seen = ", seen)

  print("Total nodes processed = " + str(len(all_done)), file = log_file)
  print("Total edges seen = " + str(seen), file = log_file)

def generateFriends(org, level, log_file):
  try:
    # Open page
    link = "https://mobile.twitter.com/" + org + "/following"
    req = Request(link, headers=headers)
    page = urlopen(req)

    doc = lxml.html.fromstring(page.read())
    # Extract first 20 followers
    friends = doc.xpath('//span[@class="username"]/text()')[1:]
          
    # Click on Show More and continue till we get all friends
    while(True):
      try:
        link = "https://mobile.twitter.com/" + doc.xpath('//*[@id="main_content"]/div/div[2]/div/a')[0].get('href')
        req = Request(link, headers=headers)
        page = urlopen(req)
        # print(page.geturl())
        doc = lxml.html.fromstring(page.read())
        friends += doc.xpath('//span[@class="username"]/text()')[1:]
      except:
        # Exception might mean a) we have reached end or
        #                      b) some type of timeout
        # Therefore try once more to make sure we have collected all friends
        try:
          link = "https://mobile.twitter.com/" + doc.xpath('//*[@id="main_content"]/div/div[2]/div/a')[0].get('href')
          req = Request(link, headers=headers)
          page = urlopen(req)
          doc = lxml.html.fromstring(page.read())
          friends += doc.xpath('//span[@class="username"]/text()')[1:]
        except Exception as e:
          # If we had exception on the second try
          # we can be confident that we have all friends
          break

    # Write friends to file
    with open("result_output/Level" + str(level) + "/friends_" + org + ".txt", mode='w', encoding="utf-8") as outptr:
      writer = csv.writer(outptr, dialect='excel', delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
      for friend in friends:
        writer.writerow([org, friend])

    return len(friends)
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

