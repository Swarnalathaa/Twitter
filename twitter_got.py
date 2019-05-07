
import GetOldTweets3 as got
import time
import datetime

def got_func(search_word, search_lang,time_start, time_end):
    tweetcriteria = got.manager.TweetCriteria().setQuerySearch(search_word).setSince(time_start).setUntil(time_end).setLang(search_lang).setTopTweets(True).setMaxTweets(10)
    tweet = got.manager.TweetManager.getTweets(tweetcriteria)
    #filename  = "tweet_" + time_start + "_" + time_end
    #file = open("filename.txt", "a")
    for t in tweet:
        print(t.date)
        print(t.id)
        print(t.text + "\n")
      #  file.write(t.text + "\n")
    #file.close()


def got_start(ts, te,word_search, tweet_lang):
    try:
        time_start = ts
        time_increment = datetime.datetime.strptime(ts,'%Y-%m-%d') + datetime.timedelta(days = 10)
        time_end = time_increment.strftime('%Y-%m-%d')

        while time_start < te:
            print(time_start)
            print(time_end)
            got_func(word_search,tweet_lang,time_start, time_end)
            time_start = time_end
            time_increment = datetime.datetime.strptime(time_start,'%Y-%m-%d') + datetime.timedelta(days = 10)
            time_end = time_increment.strftime('%Y-%m-%d')
             
    except Exception:
        print("Error")
        print("sleeping for 15 minutes")
        time.sleep(15*60)
        while time_start < te:
            print(time_start)
            print(time_end)
            got_func(word_search,tweet_lang,time_start, time_end)
            time_start = time_end
            time_increment = datetime.datetime.strptime(time_start,'%Y-%m-%d') + datetime.timedelta(days = 10)
            time_end = time_increment.strftime('%Y-%m-%d')


ws = "https://www.luxurydaily.com/inviting-opinion-pieces-on-luxury-issues-marketing-retail-and-media/"
sl = 'en'
got_start("2018-09-01", "2019-01-30",ws,sl)

