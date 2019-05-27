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

global_repository = "./Global_Repo"
epsilon_diff = 100

def main():
  #########################################      
  # Build Dictionary from Global repository
  #########################################

  make_directory(global_repository) # if it does not already exist
  print("Validating Global Dictionary...")
  all_files = [f for f in listdir(global_repository) if isfile(global_repository + "/" + f)]
  for f in all_files:
    # Validating the user - Does not need to be everytime
    print(f)
    if(not is_scraping_complete(f)):
      os.remove(global_repository + "/" + f)

  #########################################

def all_strip(s, l):
  for t in l:
    idx = s.find(t)
    if(idx != -1):
      s = s[:idx] + s[idx+len(t):]
  return s

def make_directory(dirname):
  if not os.path.exists(dirname):
    os.makedirs(dirname)

def is_scraping_complete(f):
  (completed, scraped_count) = file_line_count(global_repository + "/" + f)
  if(completed):
    return True

  f = all_strip(f, ["followers_", "friends_", ".txt"])
  headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}

  try:
    link = "https://mobile.twitter.com/" + f + "/followers"
    req = Request(link, headers=headers)
    page = urlopen(req)
    doc = lxml.html.fromstring(page.read())
    total_followers = int(doc.xpath('//*[@id="main_content"]/div/div[1]/table/tr[2]/td/span/text()')[0].replace(',', ''))

  except IndexError as e:
    # print("Protected: " + f + " ", e)
    return False

  except Exception as e:
    print("Exception: " + f + " ", e)
    return True

  if(abs(total_followers - scraped_count) < epsilon_diff):
    return True

  print("\nNot scraped: ", f, abs(total_followers - scraped_count))
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

if __name__ == '__main__':
  main()