import mmap
from os import listdir
from os.path import isfile

global_dir = "./Timeline Scraping/Timeline_Data"

def main():
  global_status_count = 0
  max_global_count = 0
  all_files = [f for f in listdir(global_dir) if isfile(global_dir + "/" + f)]

  for file in all_files:
    num_local_status = file_line_count(global_dir + "/" + file)
    global_status_count += num_local_status
    max_global_count = max(max_global_count, num_local_status)

  print("Average number of status = ", global_status_count / len(all_files))
  print("Maximum = ", max_global_count)

def file_line_count(filename):
  f = open(filename, "r+")

  try:
    buf = mmap.mmap(f.fileno(), 0)
  except ValueError:
    f.close()
    return 0

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