from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
from tweepy import API
import os
import time
import math

import twitter_credentials

from urllib3.exceptions import ReadTimeoutError

print(time.strftime("%Y%m%d_%H%M%S")) #time when the streaming has started

#Authorizing the access
auth = OAuthHandler(twitter_credentials.consumer_key,twitter_credentials.consumer_secret)
auth.set_access_token(twitter_credentials.access_token,twitter_credentials.access_token_secret)

#constructing API
api = API(auth, wait_on_rate_limit = True, wait_on_rate_limit_notify = True)


auth = OAuthHandler(twitter_credentials.consumer_key,twitter_credentials.consumer_secret)
auth.set_access_token(twitter_credentials.access_token,twitter_credentials.access_token_secret)

#####Class for stream listener####
class StdOutListener(StreamListener):

    def __init__(self):
        self.timeratelimit = 0
        self.timeother = 0
        self.num = 0
        self.streamconnection = True


    def on_data(self, data):
        self.num += 1
        print (self.num)
        #print(data)
        file = open("tweets_brexit.json", "a")
        file.write(data + "\n")
        file.close()
        return True


    def on_error(self,status):
        print ('Error:' + str(status))
        #if rate limit error occurs then the time to make next reconnect
        #attempt increases exponentialy and stream gets disconnected after
        #certain time
        if status == 420:
            print(time.strftime("%Y%m%d_%H%M%S"))
            sleepfor = 60 * math.pow(2,self.timeratelimit)
            if sleepfor > 420:
                print("waited too long.... disconnecting the stream")
                self.streamconnection = False
            print("A reconnection attempt will occur in:" + str(sleepfor/60)+"minutes")
            time.sleep(sleepfor)
            self.timeratelimit += 1
        else:
            #similarly if any other error occurs then time to reconnect increases
            #and stream gets disconnected after certain time
            print(time.strftime("%Y%m%d_%H%M%S"))
            sleepfor = 5*math.pow(2, self.timeother)
            if sleepfor > 600:
                print("Waited too long.... disconnecting the stream")
                self.streamconnection = False
            print("A reconnection will occur in" + str(sleepfor/60) + "minutes")
            time.sleep(sleepfor)
            self.timeother += 1
        return self.streamconnection


    def on_timeout(self):
        sys.stderr.write("Timeout")
        time.sleep(60)
        return True

        
l = StdOutListener()
mystream = Stream(api.auth,l)


def stream_start(stream, **kwargs):
    try:
        stream.filter(**kwargs)
    except ReadTimeoutError:
        stream.disconnect()
        print("ReadTimeoutError")
        print("Reconnection will occur in 15 minutes")
        time.sleep(15*60)
        stream_start(stream, **kwargs)
    except KeyboardInterrupt:
        print("Keyboard interuption")
        mode = int(input("Press 1 to continue and 0 to exit:"))
        if mode == 0:
            stream.disconnect()
        else:
            stream.disconnect()
            print("will connect in 1 minute")
            time.sleep(60)
            stream_start(stream, **kwargs)
    except Exception:
        stream.disconnect()
        print("Error")
        print("Reconnection will occur in 15 minutes")
        time.sleep(15*60)
        stream_start(stream, **kwargs)

search_word = ['brexit']
search_language = ["en"]

stream_start(mystream, languages = search_language, track=search_word)

