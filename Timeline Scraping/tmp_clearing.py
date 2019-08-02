import shutil
from os import listdir
from os.path import isfile, join

tmp_directory = "/tmp"

def remove_folder(cur_dir):
  try:
    if(isfile(cur_dir)):
      os.remove(cur_dir)
    else:
      shutil.rmtree(cur_dir)
  except:
    pass

def clear_tmps():
  all_dirs = [tmp_directory + "/" + f for f in listdir(tmp_directory)]# if (f.find("rust_mozprofile") != -1)]

  for cur_dir in all_dirs:
    remove_folder(cur_dir)

if __name__ == '__main__':
  clear_tmps()
