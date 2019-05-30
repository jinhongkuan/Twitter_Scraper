import mmap
import sys
import csv
from os import listdir
from os.path import isfile, join
from urllib.request import urlopen, Request
import lxml.html
import os

all_nodes = {}
max_level = 2

def main():
  all_edges = 0

  if(len(sys.argv) > 1):
    test_name = sys.argv[1]
  else:
    test_name = "./Followers/"

  cur_files = [f for f in listdir(test_name) if isfile(test_name + "/" + f)]

  for f in cur_files:
    # all_edges += file_line_count(test_name + "/" + f)
    all_followers = []
    with open(test_name + "/" + f, mode='r') as inptr:
      reader = csv.reader(inptr)
      for row in reader:
        all_nodes[row[0]] = all_nodes.get(row[0], 0) + 1
        all_nodes[row[1]] = all_nodes.get(row[1], 0) + 1
        all_edges += 1
    
  # for cur_level in range(max_level+1):
  #   cur_files = [f for f in listdir(test_name + "/Level" + str(cur_level)) if isfile(test_name + "/Level" + str(cur_level) + "/" + f)]
    
  #   for f in cur_files:

  print("\nTotal edges = ", all_edges)
  print("Total nodes = ", len(all_nodes))
  
  print("\n\n\n10 Most common users by edge number\n\nScreen_name : Indegree + Outdegree")
  count = 0
  for key, value in sorted(all_nodes.items(), key=lambda p:p[1], reverse=True):
    print(key + ": " + str(value))
    count += 1
    if(count > 10):
      break


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
      tmp_line = readline() #.decode("utf-8").split(",")
      if (not tmp_line):
        break
      # all_nodes[tmp_line[0]] = all_nodes.get(tmp_line[0], 0) + 1      
      lines += 1

    f.close()
    return lines

if __name__ == '__main__':
  main()