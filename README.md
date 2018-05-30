# Hacker News Scrape
Hacker News Scrape is a data scraper tool that uses [Requests](http://docs.python-requests.org/en/master/), [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/), and [asyncio](https://docs.python.org/3/library/asyncio.html) libraries to asynchronously acquire and parse the first three pages of posts from the main feed of Y Combinator's news site, [Hacker News](http://news.ycombinator.com/). The data gets stored in an Amazon RDS instance of PostgreSQL and served client-side through a series of API endpoints that return statistics based on time period (e.g., `/api/hacker_news/stats/hour/average_comment_count` returns the average comment count for posts in the past hour, `/api/hacker_news/stats/week/top_website` returns the most common websites that articles were posted from). A front-end visualization of the data can be found at [Hacker News Stats](https://hn-stats.crystalprism.io/), which displays various [Highcharts](https://www.highcharts.com/) visualizations of the scraped data, including a pie chart that shows a breakdown of the different types of posts, a word cloud of the most common words used in post comments (excluding stop words), and a bubble chart of the top five users who posted the most comments (with each bubble's width reflecting their total words used). Buttons at the top of the Stats page allow the user to toggle between different time periods of data (e.g., past hour, past day, past week) to fetch data from the API.

## Setup
1. Clone this repository on your server.
2. Install requirements by running `pip install -r requirements.txt`.
3. Create a PostgreSQL database to store Hacker News feed, post, and comment data, as well as a user that has all privileges on your database.
4. Set the following environment variables for the API:
    * `FLASK_APP` for the Flask application name for your server ("server.py")
    * `ENV_TYPE` for the environment status (set this to "Dev" for testing or "Prod" for live)
    * `VIRTUAL_ENV_NAME` for the name of your virtual environment (e.g., 'hn'); this is used to schedule automatic data scrapes of the Hacker News main feed with crontab
    * `DB_CONNECTION` for the [database URL](http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls) to connect to your database via SQLAlchemy ORM (i.e., '<dialect+driver://username:password@host:port/database>')
    * `DB_NAME` for the name of your database
5. Load the initial database structure by running `alembic upgrade head`.
    * Note that you might need to add `PYTHONPATH=.` to the beginning of your revision command if Alembic can't find your module.
6. Initialize the database by running `python management.py init_db` to create a custom text dictionary for use in statistic functions, and schedule hourly scrapes of Hacker News (every hour on the half hour) by running `python management.py sched_scrape`.
7. Start the server by running `flask run` (if you are making changes while the server is running, enter `flask run --reload` instead for instant updates).

## Content API
To retrieve data for a specific Hacker News post or comment, a client can send a request to the following endpoints. Post and comment data get saved in the database "post" and "comment" tables respectively:
<p align="center"><img title="Post and Comment Database Tables" src ="images/post-comment-tables.png" /></p>

\
**GET** /api/hacker_news/post/[post_id]
* Retrieve the latest version of a post from Hacker News scrapes.
* Example response body:
```javascript
{
    "comment_count": 0,
    "created": "Sat, 21 Apr 2018 20:34:06 GMT",
    "feed_rank": 90,
    "link": "https://medium.com/@RoyaPak/designing-for-ethics-706efa1a483e",
    "point_count": 11,
    "title": "Designing for Ethics: Interview with Sam Woolley of the Digital Intelligence Lab",
    "type": "article",
    "username": "benbreen",
    "website": "medium.com"
}
```

\
**GET** /api/hacker_news/comment/[comment_id]
* Retrieve the latest version of a comment for a post from Hacker News scrapes.
* Example response body:
```javascript
{
    "content": "Developing low-cost wireless soil moisture sensors for agriculture. It's old technology but the proven benefit is huge, and adoption has been really poor (mostly) because of the cost.",
    "created": "Mon, 23 Apr 2018 20:34:41 GMT",
    "feed_rank": 50,
    "level": 0,
    "parent_comment": null,
    "post_id": 16905146,
    "username": "simonrobb"
}
```

## Statistics API
To retrieve statistics for the data scraped from Hacker News, a client can send a request to the following endpoints. Statistics are calculated based on the time period specified in the request URL and use pass-through tables that connect the post/comment version to the feeds acquired during that time period:
![Hacker News Database Tables](images/hn-table.png)

\
**GET** /api/hacker_news/stats/[time_period]/average_comment_count
* Retrieve the average comment count from specified Hacker News scrapes ('hour', 'day', 'week', 'all').
* Example response body:
```javascript
65
```

\
**GET** /api/hacker_news/stats/[time_period]/average_comment_tree_depth
* Retrieve the average comment tree depth from specified Hacker News scrapes ('hour', 'day', 'week', 'all').
* Example response body:
```javascript
2
```

\
**GET** /api/hacker_news/stats/[time_period]/average_comment_word_count
* Retrieve the average comment word count from specified Hacker News scrapes ('hour', 'day', 'week', 'all').
* Example response body:
```javascript
59
```

\
**GET** /api/hacker_news/stats/[time_period]/average_point_count
* Retrieve the average point count from specified Hacker News scrapes ('hour', 'day', 'week', 'all').
* Example response body:
```javascript
154
```

\
**GET** /api/hacker_news/stats/[time_period]/comments_highest_word_count?count=[count]
* Retrieve the comments with the highest word counts from specified Hacker News scrapes ('hour', 'day', 'week', 'all'). Optionally specify the number of comments via the request URL's count query parameter.
* Example response body:
```javascript
[
    {
        "content": "(Adapted from a deeply-nested too-late-to-notice reply I made on another thread[1], but which I suspect more people would benefit from seeing)I am skeptical that AIs capable of piloting fully driverless cars are coming in the next few years. In the longer term, I'm more optimistic. There are definitely some fundamental breakthroughs which are needed (with regards to causal reasoning etc.) before \"full autonomy\" can happen -- but a lot of money and creativity is being thrown at these problems, and although none of us will know how hard the Hard problem is until after it's been solved, my hunch is that it will yield within this generation.But I think that framing this as an AI problem is not really correct in the first place.Currently car accidents kill about 1.3 million people per year. Given current driving standards, a lot of these fatalities are \"inevitable\". For example: many real-world car-based trolley problems involve driving around a blind curve too fast to react to what's on the other side. You suddenly encounter an array of obstacles: which one do you choose to hit? Or do you (in some cases) minimise global harm by driving yourself off the road? Faced with these kind of choices, people say \"oh, that's easy -- you can instruct autonomous cars to not drive around blind curves faster than they can react\". But in that case, the autonomous car just goes from being the thing that does the hitting to the thing that gets hit (by a human). Either way, people gonna die -- not due to a specific fault in how individual vehicles are controlled, but due to collective flaws in the entire premise of automotive infrastructure.So the problem is that no matter how good the AIs get, as long as they have to interact with humans in any way, they're still going to kill a fair number of people. I sympathise quite a lot with Musk's utilitarian point of view: if AIs are merely better humans, then it shouldn't matter that they still kill a lot of people; the fact that they kill meaningfully fewer people ought to be good enough to prefer them. If this is the basis for fostering a \"climate of acceptance\" then I don't think it would be a bad thing at all.But I don't expect social or legal systems to adopt a pragmatic utilitarian ethos anytime soon!One barrier it that even apart from the sensational aspect of autonomous-vehicle accidents, it's possible to do so much critiquing of them. When a human driver encounters a real-world trolley problem, they generally freeze up, overcorrect, or do something else that doesn't involve much careful calculation. So shit happens, some poor SOB is liable for it, and there's no black-box to audit.In contrast, when an autonomous vehicle kills someone, there will be a cool, calculated, auditable trail of decision-making which led to that outcome. The impulse to second-guess the AV's reasoning -- by regulators, lawyers, politicians, and competitors -- will be irresistible. To the extent that this fosters actual safety improvements, it's certainly a good thing. But it can be really hard to make even honest critiques of these things, because any suggested change needs to be tested against a near-infinite number of scenarios -- and in any case, not all of the critiques will be honest. This will be a huge barrier to adoption.Another barrier is that people's attitudes towards AVs can change how safe they are. Tesla has real data showing that Autopilot makes driving significantly safer. This data isn't wrong. The problem is that this was from a time when Autopilot was being used by people who were relatively uncomfortable with it. This meant that it was being used correctly -- as a second pair of eyes, augmenting those of the driver. That's fine: it's analogous to an aircraft Autopilot when used like that. But the more comfortable people become with Autopilot -- to the point where they start taking naps or climbing into the back seat -- the less safe it becomes. This is the bane of Level 2 and 3 automation: a feedback loop where increasing AV safety/reliability leads to decreasing human attentiveness, leading (perhaps) to a paradoxical overall decrease in safety and reliability.Even Level 4 and 5 automation isn't immune from this kind of feedback loop. It's just externalised: drivers in Mountain View learned that they could drive more aggressively around the Google AVs, which would always give way to avoid a collision. So safer AI driving has led to more dangerous human driving.So my contention is that while the the AVs may become \"good enough\" anytime between, say, now and 20 years from now -- the above sort of problems will be persistent barriers to adoption. These problems can be boiled down to a single word: humans. As long as AVs share a (high-speed) domain with humans, there will be a lot of fatalities, and the AVs will take the blame for this (since humans aren't black-boxed).Nonetheless, I think we will see AVs become very prominent. Here's how:1. Initially, small networks of low-speed (~12mph) Level-4 AVs operating in mixed environments, generally restricted to campus environments, pedestrianised town centres, etc. At that speed, it's possible to operate safely around humans even with reasonably stupid AIs. Think Easymile, 2getthere, and others.2. These networks will become joined-up by fully-segregated higher-speed AV-only right-of-ways, either on existing motorways or in new types of infrastructure (think the Boring Company).3. As these AVs take a greater mode-share, cities will incrementally convert roads into either mixed low-speed or exclusive high-speed. Development patterns will adapt accordingly. It will be a slow process, but after (say) 40-50 years, the cities will be more or less fully autonomous (with most of the streets being low-speed and heavily shared with pedestrians and bicyclists).Note that this scenario is largely insensitive to AI advances, because the real problem that needs to be solved is at the point of human interface.1: https://news.ycombinator.com/item?id=17170739",
        "created": "Tue, 29 May 2018 17:29:00 GMT",
        "id": 17181209,
        "level": 1,
        "parent_comment": 17179582,
        "post_id": 17179378,
        "total_word_count": 989,
        "username": "nkoren"
    }
]
```

\
**GET** /api/hacker_news/stats/[time_period]/comment_words?count=[count]
* Retrieve the highest-frequency words used in comments from specified Hacker News scrapes ('hour', 'day', 'week', 'all'). Optionally specify the number of words via the request URL's count query parameter.
* Example response body:
```javascript
[
    {
        "ndoc": 38796,
        "nentry": 49174,
        "word": "like"
    },
    {
        "ndoc": 32368,
        "nentry": 46670,
        "word": "people"
    },
    {
        "ndoc": 32911,
        "nentry": 43611,
        "word": "would"
    },
    {
        "ndoc": 29189,
        "nentry": 36294,
        "word": "one"
    },
    {
        "ndoc": 24834,
        "nentry": 29899,
        "word": "think"
    }
]
```

\
**GET** /api/hacker_news/stats/[time_period]/deepest_comment_tree
* Retrieve the deepest comment tree from specified Hacker News scrapes ('hour', 'day', 'week', 'all').
* Example response body:
```javascript
{
    "content": "Our Nexus setup is internal only. For WFH, we have hundreds of folks using a corporate VPN which routes to our office, and then our office routes to our AWS VPC, which is where our Nexus installation lives. I set this configuration up and haven't had any real issues with it, nor do I see any reason to switch between a proxy and npm.If a developer is using an older buggy version of npm that doesn't respect .npmrc and changes a lock file to point back to npmjs.org entries, we deny the PR and ask for it to be fixed. Right now that check is unfortunately manual, but there are plans to automate it. It can be easy to miss at times though, since GitHub often collapses lock files on PR's due to their size.For us, the main purpose of using Nexus as a proxy is to maintain availability and to cache/maintain package versions. If you're using Nexus to make things faster, then you probably shouldn't be using it. If you want faster installs, look into using `npm ci`.",
    "created": "Tue, 29 May 2018 20:15:00 GMT",
    "id": 17182568,
    "level": 10,
    "post_id": 17175960,
    "tree": [
        17182547,
        17181454,
        17181212,
        17180672,
        17178596,
        17177924,
        17177264,
        17176882,
        17176858,
        17176256
    ],
    "username": "acejam"
}
```

\
**GET** /api/hacker_news/stats/[time_period]/posts_highest_comment_count?count=[count]
* Retrieve the posts with the highest comment counts from specified Hacker News scrapes ('hour', 'day', 'week', 'all'). Optionally specify the number of posts via the request URL's count query parameter.
* Example response body:
```javascript
[
    {
        "comment_count": 1095,
        "created": "Sun, 29 Apr 2018 22:41:00 GMT",
        "feed_rank": 64,
        "id": 16954306,
        "link": "https://streetlend.com",
        "point_count": 704,
        "title": "Another Victim of the EU GDPR Regulations: StreetLend.com",
        "type": "article",
        "username": "cbeach",
        "website": "streetlend.com"
    },
    {
        "comment_count": 989,
        "created": "Tue, 01 May 2018 15:03:00 GMT",
        "feed_rank": 42,
        "id": 16967543,
        "link": "item?id=16967543",
        "point_count": 552,
        "title": "Ask HN: Who is hiring? (May 2018)",
        "type": "ask",
        "username": "whoishiring",
        "website": ""
    },
    {
        "comment_count": 980,
        "created": "Sun, 22 Apr 2018 02:41:17 GMT",
        "feed_rank": 77,
        "id": 16874015,
        "link": "https://work.qz.com/1254663/job-interviews-for-programmers-now-often-come-with-days-of-unpaid-homework/",
        "point_count": 638,
        "title": "The latest trend for tech interviews: Days of unpaid homework",
        "type": "article",
        "username": "draven",
        "website": "qz.com"
    },
    {
        "comment_count": 858,
        "created": "Mon, 23 Apr 2018 02:31:27 GMT",
        "feed_rank": 60,
        "id": 16877395,
        "link": "https://www.foundationdb.org/blog/foundationdb-is-open-source/",
        "point_count": 2119,
        "title": "Apple open-sources FoundationDB",
        "type": "article",
        "username": "spullara",
        "website": "foundationdb.org"
    },
    {
        "comment_count": 848,
        "created": "Tue, 01 May 2018 06:30:00 GMT",
        "feed_rank": 60,
        "id": 16964681,
        "link": "https://dogsnog.blog/2018/04/30/i-switched-from-iphone-to-android-1-week-report/",
        "point_count": 301,
        "title": "I switched from iPhone to the Pixel 2: One-week report",
        "type": "article",
        "username": "dogweather",
        "website": "dogsnog.blog"
    }
]
```

\
**GET** /api/hacker_news/stats/[time_period]/posts_highest_point_count?count=[count]
* Retrieve the posts with the highest point count from specified Hacker News scrapes ('hour', 'day', 'week', 'all'). Optionally specify the number of posts via the request URL's count query parameter.
* Example response body:
```javascript
[
    {
        "comment_count": 0,
        "created": "Mon, 23 Apr 2018 02:31:27 GMT",
        "feed_rank": 88,
        "id": 16877395,
        "link": "https://www.foundationdb.org/blog/foundationdb-is-open-source/",
        "point_count": 2122,
        "title": "Apple open-sources FoundationDB",
        "type": "article",
        "username": "spullara",
        "website": "foundationdb.org"
    },
    {
        "comment_count": 280,
        "created": "Mon, 07 May 2018 20:30:00 GMT",
        "feed_rank": 87,
        "id": 17015661,
        "link": "https://byorgey.wordpress.com/2018/05/06/conversations-with-a-six-year-old-on-functional-programming/",
        "point_count": 2039,
        "title": "Conversations with a six-year-old on functional programming",
        "type": "article",
        "username": "weatherlight",
        "website": "byorgey.wordpress.com"
    },
    {
        "comment_count": 743,
        "created": "Tue, 08 May 2018 17:53:00 GMT",
        "feed_rank": 73,
        "id": 17022963,
        "link": "https://ai.googleblog.com/2018/05/duplex-ai-system-for-natural-conversation.html",
        "point_count": 1870,
        "title": "Google Duplex: An AI System for Accomplishing Real World Tasks Over the Phone",
        "type": "article",
        "username": "ivank",
        "website": "googleblog.com"
    },
    {
        "comment_count": 0,
        "created": "Wed, 16 May 2018 12:04:00 GMT",
        "feed_rank": 85,
        "id": 17081684,
        "link": "https://www.zdnet.com/google-amp/article/us-cell-carriers-selling-access-to-real-time-location-data",
        "point_count": 1605,
        "title": "US cell carriers are selling access to your real-time phone location data",
        "type": "article",
        "username": "voctor",
        "website": "zdnet.com"
    },
    {
        "comment_count": 472,
        "created": "Fri, 18 May 2018 11:30:00 GMT",
        "feed_rank": 90,
        "id": 17099969,
        "link": "https://www.quora.com/What-is-the-most-sophisticated-piece-of-software-code-ever-written/answer/John-Byrd-2?share=98032397&srid=u9Nw6",
        "point_count": 1452,
        "title": "This worm we are talking about is sophisticated",
        "type": "article",
        "username": "graposaymaname",
        "website": "quora.com"
    }
]
```

\
**GET** /api/hacker_news/stats/[time_period]/post_types
* Retrieve the count of each type of post from specified Hacker News scrapes ('hour', 'day', 'week', 'all').
* Example response body:
```javascript
[
    {
        "type": "article",
        "type_count": 4152
    },
    {
        "type": "ask",
        "type_count": 225
    },
    {
        "type": "show",
        "type_count": 174
    },
    {
        "type": "job",
        "type_count": 13
    }
]
```

\
**GET** /api/hacker_news/stats/[time_period]/title_words?count=[count]
* Retrieve the highest-frequency words used in post titles from specified Hacker News scrapes ('hour', 'day', 'week', 'all'). Optionally specify the number of words via the request URL's count query parameter.
* Example response body:
```javascript
[
    {
        "ndoc": 174,
        "nentry": 174,
        "word": "hiring"
    },
    {
        "ndoc": 158,
        "nentry": 160,
        "word": "new"
    },
    {
        "ndoc": 139,
        "nentry": 145,
        "word": "google"
    },
    {
        "ndoc": 115,
        "nentry": 117,
        "word": "facebook"
    },
    {
        "ndoc": 117,
        "nentry": 117,
        "word": "yc"
    }
]
```

\
**GET** /api/hacker_news/stats/[time_period]/top_posts?count=[count]
* Retrieve top ranked posts from specified Hacker News scrapes ('hour', 'day', 'week', 'all'). Optionally specify the number of posts via the request URL's count query parameter.
* Example response body:
```javascript
[
    {
        "comment_count": 203,
        "created": "Mon, 07 May 2018 20:30:00 GMT",
        "feed_rank": 1,
        "id": 17015661,
        "link": "https://byorgey.wordpress.com/2018/05/06/conversations-with-a-six-year-old-on-functional-programming/",
        "point_count": 1463,
        "title": "Conversations with a six-year-old on functional programming",
        "type": "article",
        "username": "weatherlight",
        "website": "byorgey.wordpress.com"
    },
    {
        "comment_count": 544,
        "created": "Tue, 08 May 2018 17:53:00 GMT",
        "feed_rank": 1,
        "id": 17022963,
        "link": "https://ai.googleblog.com/2018/05/duplex-ai-system-for-natural-conversation.html",
        "point_count": 1350,
        "title": "Google Duplex: An AI System for Accomplishing Real World Tasks Over the Phone",
        "type": "article",
        "username": "ivank",
        "website": "googleblog.com"
    },
    {
        "comment_count": 306,
        "created": "Thu, 24 May 2018 15:55:00 GMT",
        "feed_rank": 1,
        "id": 17145204,
        "link": "https://www.kiro7.com/www.kiro7.com/news/local/woman-says-her-amazon-device-recorded-private-conversation-sent-it-out-to-random-contact/755507974",
        "point_count": 1084,
        "title": "Woman says Amazon recorded private conversation, sent it out to random contact",
        "type": "article",
        "username": "spking",
        "website": "kiro7.com"
    },
    {
        "comment_count": 354,
        "created": "Fri, 18 May 2018 11:30:00 GMT",
        "feed_rank": 1,
        "id": 17099969,
        "link": "https://www.quora.com/What-is-the-most-sophisticated-piece-of-software-code-ever-written/answer/John-Byrd-2?share=98032397&srid=u9Nw6",
        "point_count": 1029,
        "title": "This worm we are talking about is sophisticated",
        "type": "article",
        "username": "graposaymaname",
        "website": "quora.com"
    },
    {
        "comment_count": 222,
        "created": "Thu, 17 May 2018 20:29:00 GMT",
        "feed_rank": 1,
        "id": 17094213,
        "link": "https://krebsonsecurity.com/2018/05/tracking-firm-locationsmart-leaked-location-data-for-customers-of-all-major-u-s-mobile-carriers-in-real-time-via-its-web-site/",
        "point_count": 916,
        "title": "LocationSmart Leaked Location Data for All Major U.S. Carriers in Real Time",
        "type": "article",
        "username": "uptown",
        "website": "krebsonsecurity.com"
    }
]
```

\
**GET** /api/hacker_news/stats/[time_period]/top_websites?count=[count]
* Retrieve the top websites that posts were posted from from specified Hacker News scrapes ('hour', 'day', 'week', 'all'). Optionally specify the number of websites via the request URL's count query parameter.
* Example response body:
```javascript
[
    {
        "link_count": 156,
        "website": "github.com"
    },
    {
        "link_count": 146,
        "website": "medium.com"
    },
    {
        "link_count": 143,
        "website": "nytimes.com"
    },
    {
        "link_count": 90,
        "website": "theguardian.com"
    },
    {
        "link_count": 80,
        "website": "bloomberg.com"
    }
]
```

\
**GET** /api/hacker_news/stats/[time_period]/users_most_comments?count=[count]
* Retrieve the users with the most comments from specified Hacker News scrapes ('hour', 'day', 'week', 'all'). Optionally specify the number of users via the request URL's count query parameter.
* Example response body:
```javascript
[
    {
        "comment_count": 780,
        "username": "jacquesm",
        "word_count": 43859
    },
    {
        "comment_count": 715,
        "username": "icebraining",
        "word_count": 24623
    },
    {
        "comment_count": 537,
        "username": "dragonwriter",
        "word_count": 39940
    },
    {
        "comment_count": 437,
        "username": "pjmlp",
        "word_count": 15971
    },
    {
        "comment_count": 436,
        "username": "TeMPOraL",
        "word_count": 30924
    }
]
```

\
**GET** /api/hacker_news/stats/[time_period]/users_most_posts?count=[count]
* Retrieve the users with the most posts from specified Hacker News scrapes ('hour', 'day', 'week', 'all'). Optionally specify the number of users via the request URL's count query parameter.
* Example response body:
```javascript
[
    {
        "post_count": 66,
        "username": "rbanffy"
    },
    {
        "post_count": 48,
        "username": "ingve"
    },
    {
        "post_count": 37,
        "username": "kawera"
    },
    {
        "post_count": 37,
        "username": "tosh"
    },
    {
        "post_count": 34,
        "username": "dsr12"
    }
]
```

\
**GET** /api/hacker_news/stats/[time_period]/users_most_words?count=[count]
* Retrieve the users with the most words in their comments from specified Hacker News scrapes ('hour', 'day', 'week', 'all'). Optionally specify the number of users via the request URL's count query parameter.
* Example response body:
```javascript
[
    {
        "comment_count": 780,
        "username": "jacquesm",
        "word_count": 43859
    },
    {
        "comment_count": 537,
        "username": "dragonwriter",
        "word_count": 39940
    },
    {
        "comment_count": 436,
        "username": "TeMPOraL",
        "word_count": 30924
    },
    {
        "comment_count": 258,
        "username": "forapurpose",
        "word_count": 29632
    },
    {
        "comment_count": 205,
        "username": "adventured",
        "word_count": 28187
    }
]
```
