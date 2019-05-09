

# # post = session.post(login_url, data=payload)
# followers = []
# for org in queue:
#   link = "https://mobile.twitter.com/" + org + "/followers"
#   req = Request(link, headers=headers)
#   page = urlopen(req)
#   print(page.geturl())
#   soup = BeautifulSoup(page.read(), 'lxml').find('div', {'class':'user-list'})

#   followers = [tmp.get_text() for tmp in soup.find_all('span', {'class':'username'})]
#   # misc = open(str(-1) + ".html", "w")
#   # print(soup.prettify(), file = misc)
#   # misc.close()  

#   for i in range(10):
#     link = 'https://mobile.twitter.com' + soup.find('div', {'class':'w-button-more'}).find('a')['href']
#     req = Request(link, headers=headers)
#     page = urlopen(req)
#     print(page.geturl())

#     soup = BeautifulSoup(page.read(), 'lxml').find('div', {'class':'user-list'})
#     followers += [tmp.get_text() for tmp in soup.find_all('span', {'class':'username'})]

#     # misc = open(str(i) + ".html", "w")
#     # print(soup.prettify(), file = misc)
#     # misc.close()  

#   # for follower in followers:
#   #   print(follower)
