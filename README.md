# Twitter_Scraper
Twitter scraper that bypasses normal API limitations

Change Log:
```
(05.13.2019) Global parellelism instead of level parellelism
(05.12.2019) Updated friends.py
(05.12.2019) General Code Cleanup
(05.12.2019) Added ability to resume code and -reset flag
(05.10.2019) Ram optimization to reduce follower array overhead
(05.09.2019) Added assertions to ensure all followers are scraped
(05.09.2019) Parellelize and Multithread code
(05.09.2019) Print out diagnostic information - user being scraped, timestamp, number of followers
(05.08.2019) Added exception handling for delted users
(05.07.2019) Changed output formatting
(05.07.2019) Added support for friends scraping
(04.23.2019) Initial followers scraper
```

TO DO (Code)
```
1. Add Resum functionality to avoid recomputation
```

TO DO (Others):
```
1. Go over Spread of News paper
2. Go ove TSM paper
2. Start collecting AltNews articles
3. Test a few AltNews articles to check density
```

Dropped:
```
Disk-based Hashtable would have to coded and right now, the RAM overhead is acceptable
Explore memory mapping to reduce RAM overhead of hashtable - Priority 3, Urgency 1
```
