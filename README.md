# Twitter

The goal of this project to retrive tweets about the particular text or a news url and perform sentimental analysis and also to calculate the popularity score for each tweets.

Getting tweets from twitter has been made easy by the availability of twitter API and various python libraries like tweepy, GetOldTweets. But there are lots of limitations in at each steps. I have tried my level best to ge the best out of all possible ways.

Twitter offeres various API as follows

##Twitter search API:

-	Gets historical data. 
-	Search based on the criteria provided by the user.
-	Go back till 7 days in the past. (premium account: 30 days and enterprise account: data since 2016).

###Drawbacks:
-	Rate limited
-	Request/15minute window (user auth): 180 (Nearly 3200 tweets)
-	Request/15minute window (app auth); 450


##Twitter streaming API:
-	Gets real time tweets.

###Drawbacks:
-	Tweets we get depends on the various factors like demand on twitter, network traffic, etc
-	Only provide sample of tweets that are occurring related to the searched criteria (anywhere between 1 – 40%).
-	Rate limited.

###To be noted:

Consider that we decide to search for tweets containing “Fashion”
-	If the tweets related to “Fashion” is less than 1% of all the tweets that are being posted currently then we will get all the tweets matching the query.
-	Suppose if the tweets related to “Fashion” is more than 1% of all the tweets that are being currently posted then we get only a sample of tweets.

This can be overcome by refining your search query. That is, by combing many search words. The more search words we combine, there is a less possibility that the tweets are more than 1% of the currently posted tweets. 


##Twitter Firehose:

-	Like streaming API but provides full access to the tweets.

###Drawbacks:
-	Very costly.

##Python package
##Twitter GetOldTweet package:

-	Gets old tweets (even years back)

Drawback:

-	Can only use one word at a time in a search query.
