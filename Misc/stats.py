import sys
import csv
from os import listdir
from os.path import isfile, join
from urllib.request import urlopen, Request
import lxml.html
import os

all_nodes = {}
all_edges = 0
max_level = 2

if(len(sys.argv) > 1):
  test_name = sys.argv[1]
else:
 test_name = ".Followers/Tests/PreranaSr_650K_nodes"

for cur_level in range(max_level+1):
  cur_files = [f for f in listdir(test_name + "/Level" + str(cur_level)) if isfile(test_name + "/Level" + str(cur_level) + "/" + f)]
	
  for f in cur_files:
    all_followers = []
    with open(test_name + "/Level" + str(cur_level) + "/" + f, mode='r') as inptr:
      reader = csv.reader(inptr)
      for row in reader:
        all_nodes[row[0]] = all_nodes.get(row[0], 0) + 1
        all_edges += 1

count = 0
for key, value in sorted(all_nodes.items(), key=lambda p:p[1], reverse=True):
  print(key + ": " + str(value))
  count += 1
  if(count > 100):
    break

print("Total edges = ", all_edges)
print("Total nodes = ", len(all_nodes))




