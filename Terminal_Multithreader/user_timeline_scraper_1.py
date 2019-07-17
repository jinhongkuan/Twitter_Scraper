import tweepy
import datetime
import time
import json
import csv
import sys
import re
import os


file_name = sys.argv[1]

#bhavtosh_app_87:
consumer_key = sys.argv[2]
consumer_secret = sys.argv[3]
access_key = sys.argv[4]
access_secret = sys.argv[5]

users = []
print('Reading users.....')
with open(file_name) as infile:
    for line in infile:
        l_spl = re.split(',', line.rstrip())
        users.append(l_spl[2])

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_key, access_secret)
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

i = 0
for user in users:
    i += 1
    timeline_file_name = 'timeline_data_' + user + '.txt'
    x = os.path.isfile('./timeline_folder/' + timeline_file_name)
    if x is True:
        print(user, ' already scraped..')
    else:
        print('Scraping timeline for ', user, i)
        with open('timeline_folder/timeline_data_' + user + '.txt', 'w') as f:
            try:
                for status in api.user_timeline(screen_name=user, exclude_replies=False,
                                            include_rts=True, count = 100):
                    d = {}
                    d['tweet_type'] = 'source_tweet'
                    d_primary_tweet = {}
                    d_primary_user = {}
                    d_secondary_tweet = {}
                    d_secondary_user = {}

                    '''Primary tweet'''
                    # Primary tweet metadata
                    d_primary_tweet['tweet_id'] = status._json['id']
                    d_primary_tweet['tweet_text'] = status._json['text']
                    d_primary_tweet['created_at'] = status._json['created_at']
                    d_primary_tweet['favorite_count'] = status._json['favorite_count']
                    d_primary_tweet['retweet_count'] = status._json['retweet_count']
                    d_primary_tweet['entities'] = status._json['entities']

                    # Primary user metadata
                    d_primary_user['id'] = status._json['user']['id']
                    d_primary_user['screen_name'] = status._json['user']['screen_name']
                    d_primary_user['name'] = status._json['user']['name']
                    d_primary_user['statuses_count'] = status._json['user']['statuses_count']
                    d_primary_user['favourites_count'] = status._json['user']['favourites_count']
                    d_primary_user['followers_count'] = status._json['user']['followers_count']
                    d_primary_user['friends_count'] = status._json['user']['friends_count']
                    d_primary_user['listed_count'] = status._json['user']['listed_count']
                    d_primary_user['verified'] = status._json['user']['verified']
                    d_primary_user['protected'] = status._json['user']['protected']
                    d_primary_user['created_at'] = status._json['user']['created_at']
                    d_primary_user['location'] = status._json['user']['location']

                    '''Secondary tweet (reply, retweet without comment, retweet with comment, source tweet)'''
                    # reply
                    if status._json['in_reply_to_status_id'] is not None:
                        # Secondary tweet metadata
                        tweet = api.get_status(id=status._json['in_reply_to_status_id'])
                        d['tweet_type'] = 'reply'
                        d_secondary_tweet['tweet_id'] = status._json['in_reply_to_status_id']
                        d_secondary_tweet['tweet_text'] = tweet._json['text']
                        d_secondary_tweet['created_at'] = tweet._json['created_at']
                        d_secondary_tweet['favorite_count'] = tweet._json['favorite_count']
                        d_secondary_tweet['retweet_count'] = tweet._json['retweet_count']
                        d_secondary_tweet['entities'] = tweet._json['entities']

                        # Secondary user metadata
                        d_secondary_user['id'] = tweet._json['user']['id']
                        d_secondary_user['screen_name'] = tweet._json['user']['screen_name']
                        d_secondary_user['name'] = tweet._json['user']['name']
                        d_secondary_user['statuses_count'] = tweet._json['user']['statuses_count']
                        d_secondary_user['favourites_count'] = tweet._json['user']['favourites_count']
                        d_secondary_user['followers_count'] = tweet._json['user']['followers_count']
                        d_secondary_user['friends_count'] = tweet._json['user']['friends_count']
                        d_secondary_user['listed_count'] = tweet._json['user']['listed_count']
                        d_secondary_user['verified'] = tweet._json['user']['verified']
                        d_secondary_user['protected'] = tweet._json['user']['protected']
                        d_secondary_user['created_at'] = tweet._json['user']['created_at']
                        d_secondary_user['location'] = tweet._json['user']['location']

                        d['secondary_tweet'] = d_secondary_tweet
                        d['secondary_user'] = d_secondary_user

                    # retweet without comment
                    if 'retweeted_status' in status._json:
                        d['tweet_type'] = 'retweet_without_comment'
                        d_secondary_tweet['tweet_id'] = status._json['retweeted_status']['id']
                        d_secondary_tweet['tweet_text'] = status._json['retweeted_status']['text']
                        d_secondary_tweet['created_at'] = status._json['retweeted_status']['created_at']
                        d_secondary_tweet['favorite_count'] = status._json['retweeted_status']['favorite_count']
                        d_secondary_tweet['retweet_count'] = status._json['retweeted_status']['retweet_count']
                        d_secondary_tweet['entities'] = status._json['retweeted_status']['entities']

                        # Secondary user metadata
                        d_secondary_user['id'] = status._json['retweeted_status']['user']['id']
                        d_secondary_user['screen_name'] = status._json['retweeted_status']['user']['screen_name']
                        d_secondary_user['name'] = status._json['retweeted_status']['user']['name']
                        d_secondary_user['statuses_count'] = status._json['retweeted_status']['user']['statuses_count']
                        d_secondary_user['favourites_count'] = status._json['retweeted_status']['user']['favourites_count']
                        d_secondary_user['followers_count'] = status._json['retweeted_status']['user']['followers_count']
                        d_secondary_user['friends_count'] = status._json['retweeted_status']['user']['friends_count']
                        d_secondary_user['listed_count'] = status._json['retweeted_status']['user']['listed_count']
                        d_secondary_user['verified'] = status._json['retweeted_status']['user']['verified']
                        d_secondary_user['protected'] = status._json['retweeted_status']['user']['protected']
                        d_secondary_user['created_at'] = status._json['retweeted_status']['user']['created_at']
                        d_secondary_user['location'] = status._json['retweeted_status']['user']['location']

                        d['secondary_tweet'] = d_secondary_tweet
                        d['secondary_user'] = d_secondary_user


                    # retweet with comment
                    if 'quoted_status' in status._json:
                        d['tweet_type'] = 'retweet_with_comment'
                        d_secondary_tweet['tweet_id'] = status._json['quoted_status']['id']
                        d_secondary_tweet['tweet_text'] = status._json['quoted_status']['text']
                        d_secondary_tweet['created_at'] = status._json['quoted_status']['created_at']
                        d_secondary_tweet['favorite_count'] = status._json['quoted_status']['favorite_count']
                        d_secondary_tweet['retweet_count'] = status._json['quoted_status']['retweet_count']
                        d_secondary_tweet['entities'] = status._json['quoted_status']['entities']

                        # Secondary user metadata
                        d_secondary_user['id'] = status._json['quoted_status']['user']['id']
                        d_secondary_user['screen_name'] = status._json['quoted_status']['user']['screen_name']
                        d_secondary_user['name'] = status._json['quoted_status']['user']['name']
                        d_secondary_user['statuses_count'] = status._json['quoted_status']['user']['statuses_count']
                        d_secondary_user['favourites_count'] = status._json['quoted_status']['user']['favourites_count']
                        d_secondary_user['followers_count'] = status._json['quoted_status']['user']['followers_count']
                        d_secondary_user['friends_count'] = status._json['quoted_status']['user']['friends_count']
                        d_secondary_user['listed_count'] = status._json['quoted_status']['user']['listed_count']
                        d_secondary_user['verified'] = status._json['quoted_status']['user']['verified']
                        d_secondary_user['protected'] = status._json['quoted_status']['user']['protected']
                        d_secondary_user['created_at'] = status._json['quoted_status']['user']['created_at']
                        d_secondary_user['location'] = status._json['quoted_status']['user']['location']

                        d['secondary_tweet'] = d_secondary_tweet
                        d['secondary_user'] = d_secondary_user

                    d['primary_tweet'] = d_primary_tweet
                    d['primary_user'] = d_primary_user

                    # print(d)
                    str_status = json.dumps(d)
                    f.write(str_status + '\n')

            except tweepy.error.TweepError:
                print(user, " not found", tweepy.error.TweepError)

time.sleep(10000)