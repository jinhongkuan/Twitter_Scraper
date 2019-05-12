# Twitter_Scraper
Twitter scraper that bypasses normal API limitations

Change Log:
```
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
0. Ability to pause and resume code                           - Priority 8, Urgency 2
1. Global multithreading instead of level paralellism         - Priority 7, Urgency 3
2. Reflect changes made in Followers into Friends script      - Priority 8, Urgency 9
3. Better diagnostic information                              - Priority 8, Urgency 5
4. Explore memory mapping to reduce RAM overhead of hashtable - Priority 3, Urgency 1
5. Clean up code                                              - Priority 6, Urgency 1
```

TO DO (Others):
```
1. Go over Spread of News paper
2. Go ove TSM paper
2. Start collecting AltNews articles
3. Test a few AltNews articles to check density
```
