from tweepy import OAuthHandler
from tweepy import API
from bs4 import BeautifulSoup as bs
import time
import jsonpickle
import pandas as pd
import re

import twitter_credentials
from elasticsearch import Elasticsearch
import json
import requests

from nltk.sentiment.vader import SentimentIntensityAnalyzer
from datetime import datetime


"""
tweet object being saved in the db.Each tweet has following info
1) text: word to be searched for tweet
2) tweet_id : id of the tweet
3) text: tweet text
4) comment_count: Number of comments for the tweet
5) retweet_count: Number of times the tweet has been retweeted
6) like_count: Number of times the tweet has be liked
7) tweet_type: type of the tweet (original,reply or quoted)
8) linked_to: if it is a reply or quoted tweet then this field contains the tweet id of the original tweet it is linked to
9) user_id: id of the user who has made the tweet
10) entity: contains info about the hastags, url and other entitites present in the tweet
11) geo: location where the tweet has been made
12) place: place where the tweet has been made
13) created_at: date when the tweet has been made
14) lang: language of the tweet
"""
class Tweet:
    def __init__(self,text,tweet_id,text,comment_count,retweet_count,like_count,tweet_type,linked_id,entity,user_id,geo,place,created_at,lang):
        
        date_now = int(datetime.now().timestamp()*1000)
        
        self.text = text
        self.tweet_id = tweet_id
        self.text = text
        self.comment_count = [
            {
                'time':date_now,
                'count':comment_count
            }
        ]
        self.retweet_count = [
            {
                'time':date_now,
                'count':retweet_count
            }
        ]
        self.like_count = [
            {
                'time':date_now,
                'count':like_count
            }
        ]
        self.tweet_type = tweet_type
        self.linked_to = linked_id
        
        analyzer = SentimentIntensityAnalyzer()
        ss = analyzer.polarity_scores(text)
        if ss['compound'] >= 0.05:
            sentiment = "Positive"
        elif ss['compound'] <= -0.05:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
            
        self.sentiment_score = {
            'score': ss,
            'sentiment': sentiment
        }

        self.entity = entity
        self.user_id = user_id
        self.geo = geo
        self.place = place
        self.created_at = created_at
        self.lang = lang

"""
create dataframe for tweet_clean function
"""
def tweet_cleanobj(obj):
    tmp = {
        'id': obj['id'],
        'text': obj['full_text'],
        'tweet_status': obj['status'],
        'depend_tweet': obj['depend'],
        'entity': obj['entities'],
        'user_id': obj['user']['id'],
        'geo': obj['geo'],
        'place': obj['place'],
        'created_at': obj['created_at'],
        'lang': obj['lang']
        }
    return pd.DataFrame([tmp])

"""
checks for various possiblity of tweets (original,retweeted,quoted or reply) and create a dataframe
"""

def tweet_clean(tweets):
    
    df_tweet = pd.DataFrame()
    tweet_id = []
    
    for obj in tweets:
        ## checks the tweet is not a reply and if it already exist
        if (not obj['in_reply_to_status_id']) & (not obj['in_reply_to_status_id'] in tweet_id):
            ## checks the tweet is not a quoted tweet
            if (not obj['is_quote_status']) & (not obj['is_quote_status'] in tweet_id):

                ## checks if the tweet is a retweeted one
                if 'retweeted_status' in obj:
                    if 'id' in obj['retweeted_status']:
                        ## if it is retweeted one then getting the info about the original tweet from retweet_status object
                        obj = obj['retweeted_status']
                        if not obj['id'] in tweet_id:
                            obj['depend'] = 0
                            obj['status'] = 'original tweet'

                            tweet_id.append(obj['id'])
                            df_tweet = df_tweet.append(tweet_cleanobj(obj),ignore_index=True)
                            
                ## if not retweeted one, get info about the original tweet       
                if not obj['id'] in tweet_id:
                    obj['status'] = 'original tweet'
                    obj['depend'] = 0

                    tweet_id.append(obj['id'])
                    df_tweet = df_tweet.append(tweet_cleanobj(obj),ignore_index=True)
                        
            else:
                ## if it is a quoted tweet get the quoted tweet info
                if not obj['id'] in tweet_id:
                    obj['status'] = 'quoted tweet'
                    obj['depend'] = 0
                    
                    if 'quoted_status' in obj:
                        if 'id' in obj['quoted_status']:
                            obj['depend'] = obj['quoted_status']['id']
                            
                            df_tweet = df_tweet.append(tweet_cleanobj(obj),ignore_index=True)

                            ## get the info about the original tweet from quoted_status object
                            if not obj['quoted_status']['id'] in tweet_id:
                                obj = obj['quoted_status']
                                obj['depend'] = 0
                                obj['status'] = 'original_tweet'

                                tweet_id.append(obj['id'])
                                df_tweet = df_tweet.append(tweet_cleanobj(obj),ignore_index=True)
                    else:
                        tweet_id.append(obj['id'])
                        df_tweet = df_tweet.append(tweet_cleanobj(obj),ignore_index=True)
        
        else:
            try:
                ## if it is a reply tweet then scrape the original tweet
                if not obj['id'] in tweet_id:
                    obj['status'] = 'reply tweet'
                    try:
                        test = requests.get("https://twitter.com/i/web/status/" + str(obj['id']))
                        response = bs(test.content, 'html.parser')
                        tweet = response.find('div', {'data-associated-tweet-id':str(obj['id'])})
                        t = tweet.attrs['data-conversation-id']
                        obj['depend'] = t
                    except:
                        ## if scraping raises error then look for in_reply_status_id
                        obj['depend'] = obj['in_reply_to_status_id']
                    finally:
                        tweet_id.append(obj['id'])
                        df_tweet = df_tweet.append(tweet_cleanobj(obj),ignore_index=True)

                    ## if couldn't find the original tweet id then save the info of the in_reply_to_status
                    if obj['depend'] == obj['in_reply_to_status_id']:
                        obj['id'] = obj['in_reply_to_status_id']
                        obj['status'] = 'not sure'

                        tmp = requests.get("https://twitter.com/i/web/status/" + str(obj['in_reply_to_status_id']))
                        response = bs(tmp.content, 'html.parser')
                        tweet = response.find('div', {'data-associated-tweet-id':str(obj['in_reply_to_status_id'])})
                        datas = response.find('div', class_="js-tweet-text-container")
                        datas = datas.findAll('p')

                        obj['full_text'] = datas[0].text
                    ## if original tweet id is found then scrape for the info
                    elif obj['depend'] == t:
                        obj['id'] = t
                        obj['status'] = 'original tweet'
                        
                        test = requests.get("https://twitter.com/i/web/status/" + str(t))
                        response = bs(test.content, 'html.parser')
                        tweet = response.find('div', {'data-associated-tweet-id':str(t)})
                        datas = response.find('div', class_="js-tweet-text-container")
                        datas = datas.findAll('p')

                        obj['full_text'] = datas[0].text
                    else:
                        print("error1")

                    obj['depend'] = 0
                    obj['entities'] = 'None'
                    obj['user']['id'] = 0
                    obj['geo'] = 'None'
                    obj['created_at'] = 'None'
                    obj['place'] = 'None'
                    obj['lang'] = 'None'

                    tweet_id.append(obj['id'])
                    df_tweet = df_tweet.append(tweet_cleanobj(obj),ignore_index=True)
            except:
                print('error2')
    
    """
    scrape for the retweet,like and comment count
    """

    df_tweet['Retweets'] = 0
    df_tweet['Likes'] = 0
    df_tweet['Response'] = 0

    for index,row in df_tweet.iterrows():
        try:
            
            test = requests.get("https://twitter.com/i/web/status/"+str(row['id']))
            response = bs(test.content, 'html.parser')

            datas = response.find('div',{'data-associated-tweet-id': str(row['id'])})
            datas = datas.find('div',class_ = 'stream-item-footer')
            datas = datas.find_all('span')

            df_tweet.at[index,'Response'] = int(re.sub(r'\D',"",datas[0].text))
            df_tweet.at[index,'Retweet'] = int(re.sub(r'\D',"",datas[3].text))
            df_tweet.at[index,'Likes'] = int(re.sub(r'\D',"",datas[6].text))
        except:
            pass
    
    return df_tweet
"""
scrape the reply tweets for given tweet_id
"""
def reply_scrape(tweet_id):
    print(tweet_id)
    test = requests.get("https://twitter.com/i/web/status/" + str(tweet_id))
    response = bs(test.content, 'html.parser')

    datas = response.find('ol', class_ = 'stream-items js-navigable-stream')
    datas = datas.find_all('li')
    
    text = []
    Response = []
    Retweets = []
    Likes = []
    ids = []
    for d in datas:
        try:
            dd = d.find_all('li')
            ids.append(dd[0].attrs['data-item-id'])
        except:
            pass

    for i in ids:
        test = requests.get("https://twitter.com/i/web/status/" + str(i))
        response = bs(test.content, 'html.parser')
        datas = response.find('div',{'data-associated-tweet-id': str(i)})

        d = datas.find('div',class_ = 'stream-item-footer')
        dd = d.find_all('span')
        Response.append(int(re.sub(r'\D',"",dd[0].text)))
        Retweets.append(int(re.sub(r'\D',"",dd[3].text)))
        Likes.append(int(re.sub(r'\D',"",dd[6].text)))

        d_text = response.find('div', class_="js-tweet-text-container")
        d_text = datas.findAll('p')
        text.append(d_text[0].text)
    
    tweet_replies = pd.DataFrame()

    tweet_replies['ids'] = ids
    tweet_replies['text'] = text
    tweet_replies['Retweets'] = Retweets
    tweet_replies['Likes'] = Likes
    tweet_replies['Response'] = Response
    return tweet_replies


"""
twitter API
"""
def tweet_search(search_word,api):
    try:
        tweets = api.search(q = search_word, tweet_mode = 'extended')
    except ReadTimeoutError:
        print("ReadTimeoutError")
        print("Reconnection will occur in 2 minutes")
        time.sleep(2*60)
        tweets = api.search(q = search_word, tweet_mode = 'extended')
    except KeyboardInterrupt:
        print("Keyboard interuption")
        mode = int(input("Press 1 to continue and o to exit:"))
        if mode == 1:
            tweets = api.search(q = search_word, tweet_mode = 'extended')
    except Exception:
        print("Error")
        print("Reconnection will occur in 5 mins")
        time.sleep(5*60)
        tweets = api.search(q = search_word, tweet_mode = 'extended')
    return tweets

"""
writes the tweet object in the db
"""
def all_tweet(text,tweets):
    global url_db,es

    try:
        tweet_scrape(text)
    except:
        pass

    tweet_all = tweet_clean(tweets)
    original_tweet = []
    if not tweet_all.empty:
        
        for j in range(len(tweet_all.depend_tweet)):

            if tweet_all.depend_tweet[j] == 0:
                id_prev = es.exists(index="rd-tweettest", doc_type="doc", id=str(int(tweet_all.id[j])))
                if not id_prev:
                    data = Tweet(text,int(tweet_all.id[j]),tweet_all.text[j],int(tweet_all.Response[j]),int(tweet_all.Retweets[j]),int(tweet_all.Likes[j]),
                                    tweet_all.tweet_status[j],None,tweet_all.entity[j],int(tweet_all.user_id[j]),tweet_all.geo[j],tweet_all.place[j],tweet_all.created_at[j],tweet_all.lang[j])
                    
                    file_name = url_db + str(int(tweet_all.id[j]))
                    data = json.dumps(data.__dict__)
                    h = {'Content-type': 'application/json'}
                    requests.post(file_name,data, headers = h)
                    original_tweet.append(tweet_all.id[j])
                else:
                    pass
            
            else:
                id_prev = es.exists(index="rd-tweettest", doc_type="doc", id=str(int(tweet_all.depend_tweet[j])))
                if not id_prev:
                    ids = tweet_all.depend_tweet[j]
                    original_tweet.append(tweet_all.depend_tweet[j])
                    data = Tweet(text,int(tweet_all.depend_tweet[j]),str(tweet_all.text[tweet_all[tweet_all['id'] == ids].index.item()]),int(tweet_all.Response[tweet_all[tweet_all['id'] == ids].index.item()]),
                                    int(tweet_all.Retweets[tweet_all[tweet_all['id'] == ids].index.item()]),int(tweet_all.Likes[tweet_all[tweet_all['id'] == ids].index.item()]),str(tweet_all.tweet_status[tweet_all[tweet_all['id'] == ids].index.item()]),
                                    None,tweet_all.entity[tweet_all[tweet_all['id'] == ids].index.item()],int(tweet_all.user_id[tweet_all[tweet_all['id'] == ids].index.item()]),tweet_all.geo[tweet_all[tweet_all['id'] == ids].index.item()],tweet_all.place[tweet_all[tweet_all['id'] == ids].index.item()],
                                      tweet_all.created_at[tweet_all[tweet_all['id'] == ids].index.item()],tweet_all.lang[tweet_all[tweet_all['id'] == ids].index.item()])
                    
                    file_name = url_db + str(int(tweet_all.depend_tweet[j]))
                    data = json.dumps(data.__dict__)
                    h = {'Content-type': 'application/json'}
                    requests.post(file_name,data, headers = h)
                else:
                    pass

                id_prev = es.exists(index="rd-tweettest", doc_type="doc", id=str(int(tweet_all.id[j])))
                if not id_prev:

                    data = Tweet(text,int(tweet_all.id[j]),str(tweet_all.text[j]),int(tweet_all.Response[j]),int(tweet_all.Retweets[j]),
                                    int(tweet_all.Likes[j]),str(tweet_all.tweet_status[j]),int(tweet_all.depend_tweet[j]),tweet_all.entity[j],int(tweet_all.user_id[j]),tweet_all.geo[j],tweet_all.place[j],tweet_all.created_at[j],tweet_all.lang[j])
                    
                    file_name = url_db + str(int(tweet_all.id[j]))
                    data = json.dumps(data.__dict__)
                    h = {'Content-type': 'application/json'}
                    requests.post(file_name,data, headers = h)
                else:
                    pass
                


        for j in original_tweet:
            tr = reply_scrape(j)
            counter = 0
            for k in range(len(tr.ids)):
                data = Tweet(text,int(tr.ids[k]),str(tr.text[k]),int(tr.Response[k]),int(tr.Retweets[k]),int(tr.Likes[k]),"Reply",int(j),
                              None,None,None,None,None,None)
                file_name = url_db + str(int(tr.ids[k]))
                data = json.dumps(data.__dict__)
                h = {'Content-type': 'application/json'}
                requests.post(file_name,data, headers = h)
                counter += 1
    return
"""
calculate the popularity score for each tweet
normal : (likes count of the tweet + retweet count of the tweet)/ (total like count + total retweet count)
formula: ((v/(v+m))*p) + ((m/(v+m))*c)
       m = 1
       c = 0.5
       v = # of tweets
       p = value obtained from normal calculation
"""
def popularity_score(text):
    
    global url_db,u
    q = {"size": 1000,"query": {"bool": {"must": [{"match_phrase" : {"text": text}},{"match_phrase" : {"tweet_type" : "original tweet"}}]}}}
    query = json.dumps(q)
    h = {'Content-type': 'application/json'}
    response = requests.post(u,query, headers = h)
    result = json.loads(response.text)
    data = [doc for doc in result['hits']['hits']]
    id_array  = []
    retweet_array = []
    like_array = []
    for doc in data:
        i = len(doc['_source']['retweet_count'])-1
        try:
            id_array.append(doc['_id'])
            retweet_array.append(doc['_source']['retweet_count'][i]['count'])
            like_array.append(doc['_source']['like_count'][i]['count'])
        except:
            pass
    
    m = 1
    c = 0.5
    v = len(id_array)

    for ind in range(len(id_array)):
        if sum(retweet_array) == 0 and sum(like_array) == 0:
            p = 0
            p1 = ((v/(v+m))*p) + ((m/(v+m))*c)
        elif sum(retweet_array) == 0:
            p = (like_array[ind]/sum(like_array))/2
            p1 =((v/(v+m))*p) + ((m/(v+m))*c)
        elif sum(like_array) == 0:
            p = (retweet_array[ind]/sum(retweet_array))/2
            p1 =((v/(v+m))*p) + ((m/(v+m))*c)
        else:
            p = ((retweet_array[ind]/sum(retweet_array)) + (like_array[ind]/sum(like_array)))/2
            p1 =((v/(v+m))*p) + ((m/(v+m))*c)

        file_name = url_db + str(id_array[ind])
        data = requests.get(file_name)
        data = json.loads(data.text)
        data = data['_source']
        if not 'popularity_score' in data:
            data['popularity_score'] = [{
                'time': int(datetime.now().timestamp()*1000),
                'normal':p,
                'formula':p1
                }]
            data = json.dumps(data)
            h = {'Content-type': 'application/json'}
            requests.post(file_name,data, headers = h)

        # calculating popularity score and rewritting the data for replies and quoted tweets
        q_reply = {"size": 1000,"query": {"bool": {"must": [{"match_phrase" : {"text": text}},{"match": {"linked_to" : id_array[ind]}}],
                                                   "must_not": [{"match_phrase" : {"tweet_type" : "original tweet"}}]}}}
        
        query = json.dumps(q_reply)
        h = {'Content-type': 'application/json'}
        response = requests.post(u,query, headers = h)
        result = json.loads(response.text)
        data = [doc for doc in result['hits']['hits']]
        reply_id  = []
        reply_retweet = []
        reply_like = []
        for doc in data:
            i = len(doc['_source']['retweet_count'])-1
            try:
                reply_id.append(doc['_id'])
                reply_retweet.append(doc['_source']['retweet_count'][i]['count'])
                reply_like.append(doc['_source']['like_count'][i]['count'])
            except:
                pass

        m = 1
        c = 0.5
        vr = len(reply_id)
        
        for ind1 in range(len(reply_id)):
            if sum(reply_retweet) == 0 and sum(reply_like) == 0:
                p = 0
                p1 =((vr/(vr+m))*p) + ((m/(vr+m))*c)
            elif sum(reply_retweet) == 0:
                p = (reply_like[ind1]/sum(reply_like))/2
                p1 =((vr/(vr+m))*p) + ((m/(vr+m))*c)
            elif sum(reply_like) == 0:
                p = (reply_retweet[ind1]/sum(reply_retweet))/2
                p1 =((vr/(vr+m))*p) + ((m/(vr+m))*c)
            else:
                p = ((reply_retweet[ind1]/sum(reply_retweet)) + (reply_like[ind1]/sum(reply_like)))/2
                p1 =((vr/(vr+m))*p) + ((m/(vr+m))*c)
            file_name = url_db + str(reply_id[ind1])
            data = requests.get(file_name)
            data = json.loads(data.text)
            data = data['_source']
            if not 'popularity_score' in data:
                data['popularity_score'] = [{
                    'time': int(datetime.now().timestamp()*1000),
                    'normal': p,
                    'formula':p1
                    }]
                data = json.dumps(data)
                h = {'Content-type': 'application/json'}
                requests.post(file_name,data, headers = h)
    return


def popularity_update(text):
    
    global url_db,u
    q = {"size": 1000,"query": {"bool": {"must": [{"match_phrase" : {"text": text}},{"match_phrase" : {"tweet_type" : "original tweet"}}]}}}
    query = json.dumps(q)
    h = {'Content-type': 'application/json'}
    response = requests.post(u,query, headers = h)
    result = json.loads(response.text)
    data = [doc for doc in result['hits']['hits']]
    id_array  = []
    retweet_array = []
    like_array = []
    for doc in data:
        i = len(doc['_source']['retweet_count'])-1
        if not len(doc['_source']['retweet_count']) == 1:
            try:
                id_array.append(doc['_id'])
                retweet_array.append(doc['_source']['retweet_count'][i]['count'])
                like_array.append(doc['_source']['like_count'][i]['count'])
            except:
                pass
    
    m = 1
    c = 0.5
    v = len(id_array)

    for ind in range(len(id_array)):
        if sum(retweet_array) == 0 and sum(like_array) == 0:
            p = 0
            p1 = ((v/(v+m))*p) + ((m/(v+m))*c)
        elif sum(retweet_array) == 0:
            p = (like_array[ind]/sum(like_array))/2
            p1 =((v/(v+m))*p) + ((m/(v+m))*c)
        elif sum(like_array) == 0:
            p = (retweet_array[ind]/sum(retweet_array))/2
            p1 =((v/(v+m))*p) + ((m/(v+m))*c)
        else:
            p = ((retweet_array[ind]/sum(retweet_array)) + (like_array[ind]/sum(like_array)))/2
            p1 =((v/(v+m))*p) + ((m/(v+m))*c)

        file_name = url_db + str(id_array[ind])
        data = requests.get(file_name)
        data = json.loads(data.text)
        data = data['_source']
        data['popularity_score'].append({
            'time': int(datetime.now().timestamp()*1000),
            'normal':p,
            'formula':p1
            })
        data = json.dumps(data)
        h = {'Content-type': 'application/json'}
        requests.post(file_name,data, headers = h)

        # calculating popularity score and rewritting the data for replies and retweets
        q_reply = {"size": 1000,"query": {"bool": {"must": [{"match_phrase" : {"text": text}},{"match": {"linked_to" : id_array[ind]}}],
                                                   "must_not": [{"match_phrase" : {"tweet_type" : "original tweet"}}]}}}
        
        query = json.dumps(q_reply)
        h = {'Content-type': 'application/json'}
        response = requests.post(u,query, headers = h)
        result = json.loads(response.text)
        data = [doc for doc in result['hits']['hits']]
        reply_id  = []
        reply_retweet = []
        reply_like = []
        for doc in data:
            i = len(doc['_source']['retweet_count'])-1
            if not len(doc['_source']['retweet_count']) == 1:
                try:
                    reply_id.append(doc['_id'])
                    reply_retweet.append(doc['_source']['retweet_count'][i]['count'])
                    reply_like.append(doc['_source']['like_count'][i]['count'])
                except:
                    pass

        m = 1
        c = 0.5
        vr = len(reply_id)
        
        for ind1 in range(len(reply_id)):
            if sum(reply_retweet) == 0 and sum(reply_like) == 0:
                p = 0
                p1 =((vr/(vr+m))*p) + ((m/(vr+m))*c)
            elif sum(reply_retweet) == 0:
                p = (reply_like[ind1]/sum(reply_like))/2
                p1 =((vr/(vr+m))*p) + ((m/(vr+m))*c)
            elif sum(reply_like) == 0:
                p = (reply_retweet[ind1]/sum(reply_retweet))/2
                p1 =((vr/(vr+m))*p) + ((m/(vr+m))*c)
            else:
                p = ((reply_retweet[ind1]/sum(reply_retweet)) + (reply_like[ind1]/sum(reply_like)))/2
                p1 =((vr/(vr+m))*p) + ((m/(vr+m))*c)
            file_name = url_db + str(reply_id[ind1])
            data = requests.get(file_name)
            data = json.loads(data.text)
            data = data['_source']
            data['popularity_score'].append({
                'time': int(datetime.now().timestamp()*1000),
                'normal': p,
                'formula':p1
                })
            data = json.dumps(data)
            h = {'Content-type': 'application/json'}
            requests.post(file_name,data, headers = h)
    return

def tweet_scrape(text):
    q = {"size": 1000,"query": {"bool": {"must": [{"match_phrase" : {"text": text}}]}}}
    query = json.dumps(q)
    h = {'Content-type': 'application/json'}
    response = requests.post(u,query,headers = h)
    result = json.loads(response.text)
    
    data = [doc for doc in result['hits']['hits']]
    id_list = []
    
    for doc in data:
        try:
            id_list.append(doc['_id'])
        except:
            pass
    ## scraping retweet,like and comment count for given tweet id
    for i in id_list:
        if not i == None:

            try:
                test = requests.get("https://twitter.com/i/web/status/"+str(i))
                response = bs(test.content, 'html.parser')

                datas = response.find('div',{'data-associated-tweet-id': str(i)})
                datas = datas.find('div',class_ = 'stream-item-footer')
                datas = datas.find_all('span')
                Response =  int(re.sub(r'\D',"",datas[0].text))
                Retweets = int(re.sub(r'\D',"",datas[3].text))
                Likes = int(re.sub(r'\D',"",datas[6].text))
            except:
                Response = 0
                Retweets = 0
                Likes = 0

            date_now = int(datetime.now().timestamp()*1000)
            retweet_count = {
                'time': date_now,
                'count': Retweets
                }
            comment_count = {
                'time': date_now,
                'count': Response
                }
            like_count = {
                'time': date_now,
                'count':Likes
                }
            ## updating on the db
            file_name = url_db + str(i)
            data = requests.get(file_name)
            data = json.loads(data.text)
            data = data['_source']
            data['retweet_count'].append(retweet_count)
            data['comment_count'].append(comment_count)
            data['like_count'].append(like_count)

            data = json.dumps(data)
            h = {'Content-type': 'application/json'}
            requests.post(file_name,data, headers = h)
    return


"""
################
# CONSTANTES #
################
"""
url_db = " "

u = url_db + "_search"

es = Elasticsearch(url_db)
event = [{"text": "brexit"},{"text":"Donald Trump"}]
"""
########
# MAIN #
########
"""
def lambda_handler(event):
    
    # twitter authentication
    auth = OAuthHandler(twitter_credentials.consumer_key,twitter_credentials.consumer_secret)
    auth.set_access_token(twitter_credentials.access_token,twitter_credentials.access_token_secret)


    api = API(auth, wait_on_rate_limit = True, wait_on_rate_limit_notify = True)

    counter = 0
    for f in event:

        #starting search API
        tweets = tweet_search(f['text'],api)
        tweets = [jsonpickle.encode(x._json, unpicklable=False) for x in tweets]
        tweets = [json.loads(x) for x in tweets]
        
        all_tweet(f['text'],tweets)    
        popularity_score(f['text'])
        counter += 1

        popularity_update(f['text'])


        
lambda_handler(event)
