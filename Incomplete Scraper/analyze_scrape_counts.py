import matplotlib.pyplot as plot 
import functools
import csv

epsilon = 1000

def main():
  d = {}
  with open('scrape_counts', 'r') as inptr:
    reader = csv.reader(inptr)
    for row in reader:
      d[row[0]] = (int(row[1]), int(row[2]), int(row[3]), int(row[4]))

  low = 0
  big = {}
  for user in d:
    (fol_count, frnd_count, scr_fol, scr_frnd) = d[user] 
    if(fol_count - scr_fol < epsilon and frnd_count - scr_frnd < epsilon):
      low += 1
    else:
      big[user] = (fol_count, frnd_count, scr_fol, scr_frnd)

  min_ = 1000000; max_ = -1
  points = []
  for (user, (fol_count, frnd_count, scr_fol, scr_frnd)) in sorted(big.items(), key=functools.cmp_to_key(sort_fun), reverse = True)[:100]:
    diff = max(abs(fol_count - scr_fol), abs(frnd_count - scr_frnd))
    print(fol_count - scr_fol, frnd_count - scr_frnd, user, sep = ',')
    min_ = min(min_, diff)
    max_ = max(max_, diff)

    points.append(diff)

  # print(len(d))
  # print(min_, max_)
  # plot.plot(points) #, bins = range(min_, max_, 1000))
  # plot.show()
def sort_fun(item1, item2):
  (user, (fol_count, frnd_count, scr_fol, scr_frnd)) = item1
  (user1, (fol_count1, frnd_count1, scr_fol1, scr_frnd1)) = item2

  a = max((fol_count - scr_fol), (frnd_count - scr_frnd)) - max((fol_count1 - scr_fol1), (frnd_count1 - scr_frnd1))
  if(a == 0):
    return 0
  if(a > 0):
    return 1
  if(a < 0):
    return -1

if __name__ == '__main__':
  main()