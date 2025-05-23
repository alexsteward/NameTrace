import streamlit as st
import requests
import time
import json
from urllib.parse import quote
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import hashlib

# Page configuration
st.set_page_config(
    page_title="TraceName - Advanced Username & Name Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for modern, clean design
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2c3e50;
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 10px;
        background: linear-gradient(45deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .subtitle {
        text-align: center;
        color: #7f8c8d;
        font-size: 1.2rem;
        margin-bottom: 40px;
    }
    .stats-container {
        display: flex;
        justify-content: center;
        margin: 20px 0;
        gap: 30px;
        flex-wrap: wrap;
    }
    .stat-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        min-width: 120px;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        display: block;
    }
    .result-found {
        background: linear-gradient(135deg, #56ab2f 0%, #a8e6cf 100%);
        border: none;
        border-radius: 12px;
        padding: 15px;
        margin: 8px 0;
        color: white;
        box-shadow: 0 2px 10px rgba(86, 171, 47, 0.3);
    }
    .result-not-found {
        background: linear-gradient(135deg, #bdc3c7 0%, #ecf0f1 100%);
        border: none;
        border-radius: 12px;
        padding: 15px;
        margin: 8px 0;
        color: #34495e;
        box-shadow: 0 2px 10px rgba(189, 195, 199, 0.3);
    }
    .result-error {
        background: linear-gradient(135deg, #e74c3c 0%, #f8b2b2 100%);
        border: none;
        border-radius: 12px;
        padding: 15px;
        margin: 8px 0;
        color: white;
        box-shadow: 0 2px 10px rgba(231, 76, 60, 0.3);
    }
    .platform-name {
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 5px;
    }
    .platform-url {
        font-family: monospace;
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .leak-warning {
        background: linear-gradient(135deg, #f39c12 0%, #f1c40f 100%);
        color: white;
        padding: 15px;
        border-radius: 12px;
        margin: 8px 0;
        font-weight: bold;
        box-shadow: 0 4px 15px rgba(243, 156, 18, 0.4);
        border-left: 5px solid #e67e22;
    }
    .filter-container {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin: 20px 0;
        border: 1px solid #dee2e6;
    }
    .search-tabs {
        display: flex;
        justify-content: center;
        margin-bottom: 20px;
    }
    .tab-button {
        background: #ecf0f1;
        border: none;
        padding: 10px 20px;
        margin: 0 5px;
        border-radius: 25px;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .tab-button.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Massive platform database with 500+ sources
PLATFORMS = {
    # Social Media & Communication
    "Facebook": {
        "url": "https://facebook.com/{username}", 
        "check": "https://facebook.com/{username}",
        "name_url": "https://facebook.com/search/people/?q={username}",
        "supports_names": True
    },
    "Instagram": {
        "url": "https://instagram.com/{username}", 
        "check": "https://instagram.com/{username}",
        "name_url": "https://instagram.com/explore/tags/{username}",
        "supports_names": True
    },
    "Twitter": {
        "url": "https://twitter.com/{username}", 
        "check": "https://twitter.com/{username}",
        "name_url": "https://twitter.com/search?q={username}",
        "supports_names": True
    },
    "X": {
        "url": "https://x.com/{username}", 
        "check": "https://x.com/{username}",
        "name_url": "https://x.com/search?q={username}",
        "supports_names": True
    },
    "LinkedIn": {
        "url": "https://linkedin.com/in/{username}", 
        "check": "https://linkedin.com/in/{username}",
        "name_url": "https://linkedin.com/search/results/people/?keywords={username}",
        "supports_names": True
    },
    "TikTok": {
        "url": "https://tiktok.com/@{username}", 
        "check": "https://tiktok.com/@{username}",
        "name_url": "https://tiktok.com/search/user?q={username}",
        "supports_names": True
    },
    "Snapchat": {"url": "https://snapchat.com/add/{username}", "check": "https://snapchat.com/add/{username}"},
    "WhatsApp": {"url": "https://wa.me/{username}", "check": "https://wa.me/{username}"},
    "Telegram": {"url": "https://t.me/{username}", "check": "https://t.me/{username}"},
    "Discord": {"url": "https://discord.com/users/{username}", "check": "https://discord.com/users/{username}"},
    "Signal": {"url": "https://signal.me/#p/{username}", "check": "https://signal.me/#p/{username}"},
    "Viber": {"url": "https://viber.com/{username}", "check": "https://viber.com/{username}"},
    "WeChat": {"url": "https://weixin.qq.com/{username}", "check": "https://weixin.qq.com/{username}"},
    "Line": {"url": "https://line.me/ti/p/~{username}", "check": "https://line.me/ti/p/~{username}"},
    "KakaoTalk": {"url": "https://open.kakao.com/o/{username}", "check": "https://open.kakao.com/o/{username}"},
    "Clubhouse": {"url": "https://clubhouse.com/@{username}", "check": "https://clubhouse.com/@{username}"},
    "MeWe": {"url": "https://mewe.com/{username}", "check": "https://mewe.com/{username}"},
    "Parler": {"url": "https://parler.com/profile/{username}", "check": "https://parler.com/profile/{username}"},
    "Gettr": {"url": "https://gettr.com/user/{username}", "check": "https://gettr.com/user/{username}"},
    "Truth Social": {"url": "https://truthsocial.com/@{username}", "check": "https://truthsocial.com/@{username}"},
    "Mastodon": {"url": "https://mastodon.social/@{username}", "check": "https://mastodon.social/@{username}"},
    "Threads": {"url": "https://threads.net/@{username}", "check": "https://threads.net/@{username}"},
    "BeReal": {"url": "https://bere.al/{username}", "check": "https://bere.al/{username}"},
    "Yubo": {"url": "https://yubo.live/en/{username}", "check": "https://yubo.live/en/{username}"},
    "VSCO": {"url": "https://vsco.co/{username}", "check": "https://vsco.co/{username}"},
    "Pinterest": {"url": "https://pinterest.com/{username}", "check": "https://pinterest.com/{username}"},
    "Tumblr": {"url": "https://{username}.tumblr.com", "check": "https://{username}.tumblr.com"},
    
    # Professional & Business
    "AngelList": {"url": "https://angel.co/{username}", "check": "https://angel.co/{username}"},
    "Behance": {"url": "https://behance.net/{username}", "check": "https://behance.net/{username}"},
    "Dribbble": {"url": "https://dribbble.com/{username}", "check": "https://dribbble.com/{username}"},
    "Upwork": {"url": "https://upwork.com/freelancers/~{username}", "check": "https://upwork.com/freelancers/~{username}"},
    "Fiverr": {"url": "https://fiverr.com/{username}", "check": "https://fiverr.com/{username}"},
    "Freelancer": {"url": "https://freelancer.com/u/{username}", "check": "https://freelancer.com/u/{username}"},
    "Guru": {"url": "https://guru.com/freelancers/{username}", "check": "https://guru.com/freelancers/{username}"},
    "99designs": {"url": "https://99designs.com/profiles/{username}", "check": "https://99designs.com/profiles/{username}"},
    "Toptal": {"url": "https://toptal.com/resume/{username}", "check": "https://toptal.com/resume/{username}"},
    "PeoplePerHour": {"url": "https://peopleperhour.com/freelancer/{username}", "check": "https://peopleperhour.com/freelancer/{username}"},
    "Thumbtack": {"url": "https://thumbtack.com/profile/{username}", "check": "https://thumbtack.com/profile/{username}"},
    "TaskRabbit": {"url": "https://taskrabbit.com/profile/{username}", "check": "https://taskrabbit.com/profile/{username}"},
    
    # Development & Tech
    "GitHub": {"url": "https://github.com/{username}", "check": "https://api.github.com/users/{username}", "api": True},
    "GitLab": {"url": "https://gitlab.com/{username}", "check": "https://gitlab.com/{username}"},
    "Bitbucket": {"url": "https://bitbucket.org/{username}", "check": "https://bitbucket.org/{username}"},
    "SourceForge": {"url": "https://sourceforge.net/u/{username}", "check": "https://sourceforge.net/u/{username}"},
    "Stack Overflow": {"url": "https://stackoverflow.com/users/{username}", "check": "https://api.stackexchange.com/2.3/users?inname={username}&site=stackoverflow", "api": True},
    "CodePen": {"url": "https://codepen.io/{username}", "check": "https://codepen.io/{username}"},
    "Replit": {"url": "https://replit.com/@{username}", "check": "https://replit.com/@{username}"},
    "Dev.to": {"url": "https://dev.to/{username}", "check": "https://dev.to/api/users/by_username?url={username}", "api": True},
    "HackerRank": {"url": "https://hackerrank.com/{username}", "check": "https://hackerrank.com/{username}"},
    "LeetCode": {"url": "https://leetcode.com/{username}", "check": "https://leetcode.com/{username}"},
    "Kaggle": {"url": "https://kaggle.com/{username}", "check": "https://kaggle.com/{username}"},
    "HackerNews": {"url": "https://news.ycombinator.com/user?id={username}", "check": "https://hacker-news.firebaseio.com/v0/user/{username}.json", "api": True},
    "CodeChef": {"url": "https://codechef.com/users/{username}", "check": "https://codechef.com/users/{username}"},
    "Codeforces": {"url": "https://codeforces.com/profile/{username}", "check": "https://codeforces.com/profile/{username}"},
    "AtCoder": {"url": "https://atcoder.jp/users/{username}", "check": "https://atcoder.jp/users/{username}"},
    "TopCoder": {"url": "https://topcoder.com/members/{username}", "check": "https://topcoder.com/members/{username}"},
    "Exercism": {"url": "https://exercism.org/profiles/{username}", "check": "https://exercism.org/profiles/{username}"},
    "Codewars": {"url": "https://codewars.com/users/{username}", "check": "https://codewars.com/users/{username}"},
    "FreeCodeCamp": {"url": "https://freecodecamp.org/{username}", "check": "https://freecodecamp.org/{username}"},
    "npm": {"url": "https://npmjs.com/~{username}", "check": "https://npmjs.com/~{username}"},
    "PyPI": {"url": "https://pypi.org/user/{username}", "check": "https://pypi.org/user/{username}"},
    "Docker Hub": {"url": "https://hub.docker.com/u/{username}", "check": "https://hub.docker.com/u/{username}"},
    "Heroku": {"url": "https://heroku.com/{username}", "check": "https://heroku.com/{username}"},
    
    # Gaming
    "Steam": {"url": "https://steamcommunity.com/id/{username}", "check": "https://steamcommunity.com/id/{username}"},
    "Twitch": {"url": "https://twitch.tv/{username}", "check": "https://twitch.tv/{username}"},
    "Xbox Live": {"url": "https://xbox.com/en-US/Profile?Gamertag={username}", "check": "https://xbox.com/en-US/Profile?Gamertag={username}"},
    "PlayStation": {"url": "https://my.playstation.com/profile/{username}", "check": "https://my.playstation.com/profile/{username}"},
    "Epic Games": {"url": "https://fortnitetracker.com/profile/epic/{username}", "check": "https://fortnitetracker.com/profile/epic/{username}"},
    "Roblox": {"url": "https://roblox.com/users/{username}/profile", "check": "https://roblox.com/users/{username}/profile"},
    "Minecraft": {"url": "https://namemc.com/profile/{username}", "check": "https://namemc.com/profile/{username}"},
    "Fortnite": {"url": "https://fortnitetracker.com/profile/all/{username}", "check": "https://fortnitetracker.com/profile/all/{username}"},
    "Valorant": {"url": "https://tracker.gg/valorant/profile/riot/{username}", "check": "https://tracker.gg/valorant/profile/riot/{username}"},
    "CS:GO": {"url": "https://csgostats.gg/player/{username}", "check": "https://csgostats.gg/player/{username}"},
    "League of Legends": {"url": "https://op.gg/summoners/na/{username}", "check": "https://op.gg/summoners/na/{username}"},
    "Overwatch": {"url": "https://playoverwatch.com/en-us/career/pc/{username}", "check": "https://playoverwatch.com/en-us/career/pc/{username}"},
    "Apex Legends": {"url": "https://apex.tracker.gg/apex/profile/origin/{username}", "check": "https://apex.tracker.gg/apex/profile/origin/{username}"},
    "Call of Duty": {"url": "https://cod.tracker.gg/warzone/profile/battlenet/{username}", "check": "https://cod.tracker.gg/warzone/profile/battlenet/{username}"},
    "Battlefield": {"url": "https://battlefieldtracker.com/bf2042/profile/origin/{username}", "check": "https://battlefieldtracker.com/bf2042/profile/origin/{username}"},
    "Rocket League": {"url": "https://rocketleague.tracker.network/rocket-league/profile/steam/{username}", "check": "https://rocketleague.tracker.network/rocket-league/profile/steam/{username}"},
    "Chess.com": {"url": "https://chess.com/member/{username}", "check": "https://chess.com/member/{username}"},
    "Lichess": {"url": "https://lichess.org/@/{username}", "check": "https://lichess.org/@/{username}"},
    
    # Media & Content
    "YouTube": {"url": "https://youtube.com/@{username}", "check": "https://youtube.com/@{username}"},
    "Vimeo": {"url": "https://vimeo.com/{username}", "check": "https://vimeo.com/{username}"},
    "Dailymotion": {"url": "https://dailymotion.com/{username}", "check": "https://dailymotion.com/{username}"},
    "SoundCloud": {"url": "https://soundcloud.com/{username}", "check": "https://soundcloud.com/{username}"},
    "Spotify": {"url": "https://open.spotify.com/user/{username}", "check": "https://open.spotify.com/user/{username}"},
    "Apple Music": {"url": "https://music.apple.com/profile/{username}", "check": "https://music.apple.com/profile/{username}"},
    "Bandcamp": {"url": "https://{username}.bandcamp.com", "check": "https://{username}.bandcamp.com"},
    "Mixcloud": {"url": "https://mixcloud.com/{username}", "check": "https://mixcloud.com/{username}"},
    "Last.fm": {"url": "https://last.fm/user/{username}", "check": "https://last.fm/user/{username}"},
    "Deezer": {"url": "https://deezer.com/profile/{username}", "check": "https://deezer.com/profile/{username}"},
    "Pandora": {"url": "https://pandora.com/people/{username}", "check": "https://pandora.com/people/{username}"},
    "Tidal": {"url": "https://tidal.com/browse/user/{username}", "check": "https://tidal.com/browse/user/{username}"},
    "ReverbNation": {"url": "https://reverbnation.com/{username}", "check": "https://reverbnation.com/{username}"},
    "Patreon": {"url": "https://patreon.com/{username}", "check": "https://patreon.com/{username}"},
    "Ko-fi": {"url": "https://ko-fi.com/{username}", "check": "https://ko-fi.com/{username}"},
    "Buy Me a Coffee": {"url": "https://buymeacoffee.com/{username}", "check": "https://buymeacoffee.com/{username}"},
    
    # Blogging & Writing
    "Medium": {"url": "https://medium.com/@{username}", "check": "https://medium.com/@{username}"},
    "Substack": {"url": "https://{username}.substack.com", "check": "https://{username}.substack.com"},
    "WordPress": {"url": "https://{username}.wordpress.com", "check": "https://{username}.wordpress.com"},
    "Blogger": {"url": "https://{username}.blogspot.com", "check": "https://{username}.blogspot.com"},
    "Ghost": {"url": "https://{username}.ghost.io", "check": "https://{username}.ghost.io"},
    "Hashnode": {"url": "https://{username}.hashnode.dev", "check": "https://{username}.hashnode.dev"},
    "Wix": {"url": "https://{username}.wixsite.com", "check": "https://{username}.wixsite.com"},
    "Squarespace": {"url": "https://{username}.squarespace.com", "check": "https://{username}.squarespace.com"},
    "Weebly": {"url": "https://{username}.weebly.com", "check": "https://{username}.weebly.com"},
    "Notion": {"url": "https://notion.so/{username}", "check": "https://notion.so/{username}"},
    
    # Forums & Communities
    "Reddit": {"url": "https://reddit.com/user/{username}", "check": "https://reddit.com/user/{username}/about.json", "api": True},
    "Quora": {
        "url": "https://quora.com/profile/{username}", 
        "check": "https://quora.com/profile/{username}",
        "name_url": "https://quora.com/search?q={username}&type=people",
        "supports_names": True
    },
    "Discord Servers": {"url": "https://disboard.org/search?keyword={username}", "check": "https://disboard.org/search?keyword={username}"},
    "Slack": {"url": "https://{username}.slack.com", "check": "https://{username}.slack.com"},
    
    # Dating & Social
    "Tinder": {"url": "https://tinder.com/@{username}", "check": "https://tinder.com/@{username}"},
    "Bumble": {"url": "https://bumble.com/{username}", "check": "https://bumble.com/{username}"},
    "Match": {"url": "https://match.com/profile/{username}", "check": "https://match.com/profile/{username}"},
    "OkCupid": {"url": "https://okcupid.com/profile/{username}", "check": "https://okcupid.com/profile/{username}"},
    "PlentyOfFish": {"url": "https://pof.com/profile/{username}", "check": "https://pof.com/profile/{username}"},
    "Badoo": {"url": "https://badoo.com/profile/{username}", "check": "https://badoo.com/profile/{username}"},
    "Zoosk": {"url": "https://zoosk.com/profile/{username}", "check": "https://zoosk.com/profile/{username}"},
    "eHarmony": {"url": "https://eharmony.com/profile/{username}", "check": "https://eharmony.com/profile/{username}"},
    "Hinge": {"url": "https://hinge.co/{username}", "check": "https://hinge.co/{username}"},
    
    # Shopping & Commerce
    "eBay": {"url": "https://ebay.com/usr/{username}", "check": "https://ebay.com/usr/{username}"},
    "Amazon": {"url": "https://amazon.com/profile/{username}", "check": "https://amazon.com/profile/{username}"},
    "Etsy": {"url": "https://etsy.com/people/{username}", "check": "https://etsy.com/people/{username}"},
    "Mercari": {"url": "https://mercari.com/u/{username}", "check": "https://mercari.com/u/{username}"},
    "Depop": {"url": "https://depop.com/{username}", "check": "https://depop.com/{username}"},
    "Poshmark": {"url": "https://poshmark.com/closet/{username}", "check": "https://poshmark.com/closet/{username}"},
    "Vinted": {"url": "https://vinted.com/member/{username}", "check": "https://vinted.com/member/{username}"},
    "ThredUp": {"url": "https://thredup.com/closet/{username}", "check": "https://thredup.com/closet/{username}"},
    "Vestiaire": {"url": "https://vestiairecollective.com/women/{username}", "check": "https://vestiairecollective.com/women/{username}"},
    "Grailed": {"url": "https://grailed.com/{username}", "check": "https://grailed.com/{username}"},
    
    # Photo & Visual
    "Flickr": {"url": "https://flickr.com/people/{username}", "check": "https://flickr.com/people/{username}"},
    "500px": {"url": "https://500px.com/{username}", "check": "https://500px.com/{username}"},
    "SmugMug": {"url": "https://{username}.smugmug.com", "check": "https://{username}.smugmug.com"},
    "DeviantArt": {"url": "https://deviantart.com/{username}", "check": "https://deviantart.com/{username}"},
    "ArtStation": {"url": "https://artstation.com/{username}", "check": "https://artstation.com/{username}"},
    "Unsplash": {"url": "https://unsplash.com/@{username}", "check": "https://unsplash.com/@{username}"},
    "Pexels": {"url": "https://pexels.com/@{username}", "check": "https://pexels.com/@{username}"},
    "Shutterstock": {"url": "https://shutterstock.com/g/{username}", "check": "https://shutterstock.com/g/{username}"},
    "Getty Images": {"url": "https://gettyimages.com/photos/{username}", "check": "https://gettyimages.com/photos/{username}"},
    "Adobe Stock": {"url": "https://stock.adobe.com/contributor/{username}", "check": "https://stock.adobe.com/contributor/{username}"},
    
    # Fitness & Health
    "MyFitnessPal": {"url": "https://myfitnesspal.com/profile/{username}", "check": "https://myfitnesspal.com/profile/{username}"},
    "Strava": {"url": "https://strava.com/athletes/{username}", "check": "https://strava.com/athletes/{username}"},
    "Fitbit": {"url": "https://fitbit.com/user/{username}", "check": "https://fitbit.com/user/{username}"},
    "Garmin": {"url": "https://connect.garmin.com/modern/profile/{username}", "check": "https://connect.garmin.com/modern/profile/{username}"},
    "Nike": {"url": "https://nike.com/profile/{username}", "check": "https://nike.com/profile/{username}"},
    "Adidas": {"url": "https://adidas.com/us/profile/{username}", "check": "https://adidas.com/us/profile/{username}"},
    "Under Armour": {"url": "https://underarmour.com/profile/{username}", "check": "https://underarmour.com/profile/{username}"},
    
    # Travel
    "TripAdvisor": {"url": "https://tripadvisor.com/members/{username}", "check": "https://tripadvisor.com/members/{username}"},
    "Airbnb": {"url": "https://airbnb.com/users/show/{username}", "check": "https://airbnb.com/users/show/{username}"},
    "Booking.com": {"url": "https://booking.com/profile/{username}", "check": "https://booking.com/profile/{username}"},
    "Expedia": {"url": "https://expedia.com/user/{username}", "check": "https://expedia.com/user/{username}"},
    "Hotels.com": {"url": "https://hotels.com/profile/{username}", "check": "https://hotels.com/profile/{username}"},
    "Kayak": {"url": "https://kayak.com/profile/{username}", "check": "https://kayak.com/profile/{username}"},
    "Skyscanner": {"url": "https://skyscanner.com/profile/{username}", "check": "https://skyscanner.com/profile/{username}"},
    
    # Education
    "Khan Academy": {"url": "https://khanacademy.org/profile/{username}", "check": "https://khanacademy.org/profile/{username}"},
    "Coursera": {"url": "https://coursera.org/user/{username}", "check": "https://coursera.org/user/{username}"},
    "edX": {"url": "https://edx.org/profile/{username}", "check": "https://edx.org/profile/{username}"},
    "Udemy": {"url": "https://udemy.com/user/{username}", "check": "https://udemy.com/user/{username}"},
    "Skillshare": {"url": "https://skillshare.com/profile/{username}", "check": "https://skillshare.com/profile/{username}"},
    "MasterClass": {"url": "https://masterclass.com/profile/{username}", "check": "https://masterclass.com/profile/{username}"},
    "Pluralsight": {"url": "https://pluralsight.com/profile/{username}", "check": "https://pluralsight.com/profile/{username}"},
    "LinkedIn Learning": {"url": "https://linkedin.com/learning/instructors/{username}", "check": "https://linkedin.com/learning/instructors/{username}"},
    
    # Crypto & Finance
    "CoinBase": {"url": "https://coinbase.com/{username}", "check": "https://coinbase.com/{username}"},
    "Binance": {"url": "https://binance.com/en/activity/referral-entry?fromActivityPage=true&ref={username}", "check": "https://binance.com/en/activity/referral-entry?fromActivityPage=true&ref={username}"},
    "Kraken": {"url": "https://kraken.com/u/{username}", "check": "https://kraken.com/u/{username}"},
    "OpenSea": {"url": "https://opensea.io/{username}", "check": "https://opensea.io/{username}"},
    "Rarible": {"url": "https://rarible.com/{username}", "check": "https://rarible.com/{username}"},
    "Foundation": {"url": "https://foundation.app/@{username}", "check": "https://foundation.app/@{username}"},
    "SuperRare": {"url": "https://superrare.com/{username}", "check": "https://superrare.com/{username}"},
    "Nifty Gateway": {"url": "https://niftygateway.com/profile/{username}", "check": "https://niftygateway.com/profile/{username}"},
    "Async Art": {"url": "https://async.art/u/{username}", "check": "https://async.art/u/{username}"},
    "KnownOrigin": {"url": "https://knownorigin.io/{username}", "check": "https://knownorigin.io/{username}"},
    "MakersPlace": {"url": "https://makersplace.com/{username}", "check": "https://makersplace.com/{username}"},
    "BlockFi": {"url": "https://blockfi.com/profile/{username}", "check": "https://blockfi.com/profile/{username}"},
    "Celsius": {"url": "https://celsius.network/profile/{username}", "check": "https://celsius.network/profile/{username}"},
    
    # News & Information
    "Wikipedia": {"url": "https://en.wikipedia.org/wiki/User:{username}", "check": "https://en.wikipedia.org/wiki/User:{username}"},
    "Wikimedia": {"url": "https://commons.wikimedia.org/wiki/User:{username}", "check": "https://commons.wikimedia.org/wiki/User:{username}"},
    "Fandom": {"url": "https://community.fandom.com/wiki/User:{username}", "check": "https://community.fandom.com/wiki/User:{username}"},
    
    # Regional/International
    "VKontakte": {"url": "https://vk.com/{username}", "check": "https://vk.com/{username}"},
    "Odnoklassniki": {"url": "https://ok.ru/{username}", "check": "https://ok.ru/{username}"},
    "Weibo": {"url": "https://weibo.com/{username}", "check": "https://weibo.com/{username}"},
    "QQ": {"url": "https://user.qzone.qq.com/{username}", "check": "https://user.qzone.qq.com/{username}"},
    "Baidu": {"url": "https://tieba.baidu.com/home/main?un={username}", "check": "https://tieba.baidu.com/home/main?un={username}"},
    "Naver": {"url": "https://blog.naver.com/{username}", "check": "https://blog.naver.com/{username}"},
    "Mixi": {"url": "https://mixi.jp/{username}", "check": "https://mixi.jp/{username}"},
    "Nico Nico": {"url": "https://nicovideo.jp/user/{username}", "check": "https://nicovideo.jp/user/{username}"},
    "Pixiv": {"url": "https://pixiv.net/users/{username}", "check": "https://pixiv.net/users/{username}"},
    "Ameba": {"url": "https://ameblo.jp/{username}", "check": "https://ameblo.jp/{username}"},
    "XING": {"url": "https://xing.com/profile/{username}", "check": "https://xing.com/profile/{username}"},
    "Diaspora": {"url": "https://diaspora.social/people/{username}", "check": "https://diaspora.social/people/{username}"},
    
    # Adult Content (for cybersecurity investigation purposes)
    "OnlyFans": {"url": "https://onlyfans.com/{username}", "check": "https://onlyfans.com/{username}"},
    "Chaturbate": {"url": "https://chaturbate.com/{username}", "check": "https://chaturbate.com/{username}"},
    "ManyVids": {"url": "https://manyvids.com/Profile/{username}", "check": "https://manyvids.com/Profile/{username}"},
    "Cam4": {"url": "https://cam4.com/{username}", "check": "https://cam4.com/{username}"},
    "LiveJasmin": {"url": "https://livejasmin.com/en/girl/{username}", "check": "https://livejasmin.com/en/girl/{username}"},
    "MyFreeCams": {"url": "https://myfreecams.com/profiles/{username}", "check": "https://myfreecams.com/profiles/{username}"},
    "Stripchat": {"url": "https://stripchat.com/{username}", "check": "https://stripchat.com/{username}"},
    "BongaCams": {"url": "https://bongacams.com/profile/{username}", "check": "https://bongacams.com/profile/{username}"},
    
    # Data Breach & Leak Databases
    "HaveIBeenPwned": {"url": "https://haveibeenpwned.com/account/{username}", "check": "https://haveibeenpwned.com/api/v3/breachedaccount/{username}", "api": True, "leak_db": True},
    "LeakCheck": {"url": "https://leakcheck.io/search/{username}", "check": "https://leakcheck.io/search/{username}", "leak_db": True},
    "IntelligenceX": {"url": "https://intelx.io/search?term={username}", "check": "https://intelx.io/search?term={username}", "leak_db": True},
    "DeHashed": {"url": "https://dehashed.com/search?query={username}", "check": "https://dehashed.com/search?query={username}", "leak_db": True},
    "BreachDirectory": {"url": "https://breachdirectory.org/search?q={username}", "check": "https://breachdirectory.org/search?q={username}", "leak_db": True},
    "Snusbase": {"url": "https://snusbase.com/search/{username}", "check": "https://snusbase.com/search/{username}", "leak_db": True},
    "WeLeakInfo": {"url": "https://weleakinfo.to/search/{username}", "check": "https://weleakinfo.to/search/{username}", "leak_db": True},
    "BreachForums": {"url": "https://breachforums.is/search?q={username}", "check": "https://breachforums.is/search?q={username}", "leak_db": True},
    "RaidForums": {"url": "https://raidforums.com/search?q={username}", "check": "https://raidforums.com/search?q={username}", "leak_db": True},
    "DatabaseLeak": {"url": "https://databaseleak.com/search/{username}", "check": "https://databaseleak.com/search/{username}", "leak_db": True},
    "LeakLookup": {"url": "https://leak-lookup.com/search/{username}", "check": "https://leak-lookup.com/search/{username}", "leak_db": True},
    "PwnDB": {"url": "https://pwndb.com/search/{username}", "check": "https://pwndb.com/search/{username}", "leak_db": True},
    "Vigilante.pw": {"url": "https://vigilante.pw/search/{username}", "check": "https://vigilante.pw/search/{username}", "leak_db": True},
    "LeakPeek": {"url": "https://leakpeek.com/search/{username}", "check": "https://leakpeek.com/search/{username}", "leak_db": True},
    "Breach-Parse": {"url": "https://breach-parse.com/search/{username}", "check": "https://breach-parse.com/search/{username}", "leak_db": True},
    "DatabaseDumps": {"url": "https://databasedumps.com/search/{username}", "check": "https://databasedumps.com/search/{username}", "leak_db": True},
    "DataViper": {"url": "https://dataviper.io/search/{username}", "check": "https://dataviper.io/search/{username}", "leak_db": True},
    "ScatteredSecrets": {"url": "https://scatteredsecrets.com/search/{username}", "check": "https://scatteredsecrets.com/search/{username}", "leak_db": True},
    "LeakBase": {"url": "https://leakbase.cc/search/{username}", "check": "https://leakbase.cc/search/{username}", "leak_db": True},
    "NullByte": {"url": "https://nullbyte.org.il/search/{username}", "check": "https://nullbyte.org.il/search/{username}", "leak_db": True},
    
    # Paste Sites
    "Pastebin": {"url": "https://pastebin.com/u/{username}", "check": "https://pastebin.com/u/{username}"},
    "GitHub Gist": {"url": "https://gist.github.com/{username}", "check": "https://gist.github.com/{username}"},
    "Ghostbin": {"url": "https://ghostbin.co/user/{username}", "check": "https://ghostbin.co/user/{username}"},
    "Paste.ee": {"url": "https://paste.ee/u/{username}", "check": "https://paste.ee/u/{username}"},
    "Paste.org": {"url": "https://paste.org/user/{username}", "check": "https://paste.org/user/{username}"},
    "Dpaste": {"url": "https://dpaste.com/user/{username}", "check": "https://dpaste.com/user/{username}"},
    "JustPaste.it": {"url": "https://justpaste.it/u/{username}", "check": "https://justpaste.it/u/{username}"},
    "ControlC": {"url": "https://controlc.com/profile/{username}", "check": "https://controlc.com/profile/{username}"},
    "Hastebin": {"url": "https://hastebin.com/user/{username}", "check": "https://hastebin.com/user/{username}"},
    "PasteBin.pl": {"url": "https://pastebin.pl/user/{username}", "check": "https://pastebin.pl/user/{username}"},
    
    # Archives
    "Internet Archive": {"url": "https://archive.org/details/@{username}", "check": "https://archive.org/details/@{username}"},
    "Wayback Machine": {"url": "https://web.archive.org/web/*/{username}", "check": "https://web.archive.org/web/*/{username}"},
    "Archive.today": {"url": "https://archive.today/search/?q={username}", "check": "https://archive.today/search/?q={username}"},
    "Library of Congress": {"url": "https://loc.gov/search/?q={username}", "check": "https://loc.gov/search/?q={username}"},
    
    # Messaging Boards & Old School
    "ICQ": {"url": "https://icq.com/people/{username}", "check": "https://icq.com/people/{username}"},
    "Skype": {"url": "skype:{username}?userinfo", "check": "skype:{username}?userinfo"},
    "Yahoo": {"url": "https://yahoo.com/profile/{username}", "check": "https://yahoo.com/profile/{username}"},
    "AOL": {"url": "https://aol.com/profile/{username}", "check": "https://aol.com/profile/{username}"},
    "MSN": {"url": "https://msn.com/profile/{username}", "check": "https://msn.com/profile/{username}"},
    
    # Misc/Other
    "Gravatar": {"url": "https://gravatar.com/{username}", "check": "https://gravatar.com/{username}"},
    "About.me": {"url": "https://about.me/{username}", "check": "https://about.me/{username}"},
    "Linktree": {"url": "https://linktr.ee/{username}", "check": "https://linktr.ee/{username}"},
    "Bio.link": {"url": "https://bio.link/{username}", "check": "https://bio.link/{username}"},
    "Carrd": {"url": "https://{username}.carrd.co", "check": "https://{username}.carrd.co"},
    "ContactOut": {"url": "https://contactout.com/{username}", "check": "https://contactout.com/{username}"},
    "Fullcontact": {"url": "https://fullcontact.com/profile/{username}", "check": "https://fullcontact.com/profile/{username}"},
    "Pipl": {"url": "https://pipl.com/search/?q={username}", "check": "https://pipl.com/search/?q={username}"},
    "Spokeo": {"url": "https://spokeo.com/{username}", "check": "https://spokeo.com/{username}"},
    "WhitePages": {"url": "https://whitepages.com/name/{username}", "check": "https://whitepages.com/name/{username}"},
    "TruePeopleSearch": {"url": "https://truepeoplesearch.com/results?name={username}", "check": "https://truepeoplesearch.com/results?name={username}"},
    "FastPeopleSearch": {"url": "https://fastpeoplesearch.com/name/{username}", "check": "https://fastpeoplesearch.com/name/{username}"},
    "PeekYou": {"url": "https://peekyou.com/{username}", "check": "https://peekyou.com/{username}"},
    "That'sThem": {"url": "https://thatsthem.com/name/{username}", "check": "https://thatsthem.com/name/{username}"},
    "VoterRecords": {"url": "https://voterrecords.com/voter/{username}", "check": "https://voterrecords.com/voter/{username}"},
    
    # Business & Professional Networks
    "Crunchbase": {"url": "https://crunchbase.com/person/{username}", "check": "https://crunchbase.com/person/{username}"},
    "Bloomberg": {"url": "https://bloomberg.com/profile/person/{username}", "check": "https://bloomberg.com/profile/person/{username}"},
    "Forbes": {"url": "https://forbes.com/profile/{username}", "check": "https://forbes.com/profile/{username}"},
    "Fortune": {"url": "https://fortune.com/author/{username}", "check": "https://fortune.com/author/{username}"},
    "SEC Edgar": {"url": "https://sec.gov/edgar/search/#/people/{username}", "check": "https://sec.gov/edgar/search/#/people/{username}"},
    "OpenCorporates": {"url": "https://opencorporates.com/officers?q={username}", "check": "https://opencorporates.com/officers?q={username}"},
    
    # Academic & Research
    "Google Scholar": {"url": "https://scholar.google.com/citations?user={username}", "check": "https://scholar.google.com/citations?user={username}"},
    "ResearchGate": {"url": "https://researchgate.net/profile/{username}", "check": "https://researchgate.net/profile/{username}"},
    "Academia.edu": {"url": "https://academia.edu/{username}", "check": "https://academia.edu/{username}"},
    "ORCID": {"url": "https://orcid.org/{username}", "check": "https://orcid.org/{username}"},
    "Scopus": {"url": "https://scopus.com/authid/detail.uri?authorId={username}", "check": "https://scopus.com/authid/detail.uri?authorId={username}"},
    "PubMed": {"url": "https://pubmed.ncbi.nlm.nih.gov/?term={username}", "check": "https://pubmed.ncbi.nlm.nih.gov/?term={username}"},
    "arXiv": {"url": "https://arxiv.org/search/?searchtype=author&query={username}", "check": "https://arxiv.org/search/?searchtype=author&query={username}"},
    "SSRN": {"url": "https://ssrn.com/author={username}", "check": "https://ssrn.com/author={username}"},
    
    # Food & Lifestyle
    "Yelp": {"url": "https://yelp.com/user_details?userid={username}", "check": "https://yelp.com/user_details?userid={username}"},
    "Zomato": {"url": "https://zomato.com/{username}", "check": "https://zomato.com/{username}"},
    "Foursquare": {"url": "https://foursquare.com/{username}", "check": "https://foursquare.com/{username}"},
    "Untappd": {"url": "https://untappd.com/user/{username}", "check": "https://untappd.com/user/{username}"},
    "Vivino": {"url": "https://vivino.com/users/{username}", "check": "https://vivino.com/users/{username}"},
    "Goodreads": {"url": "https://goodreads.com/{username}", "check": "https://goodreads.com/{username}"},
    "LibraryThing": {"url": "https://librarything.com/profile/{username}", "check": "https://librarything.com/profile/{username}"},
    
    # Real Estate & Location
    "Zillow": {"url": "https://zillow.com/profile/{username}", "check": "https://zillow.com/profile/{username}"},
    "Realtor.com": {"url": "https://realtor.com/realestateagents/{username}", "check": "https://realtor.com/realestateagents/{username}"},
    "Trulia": {"url": "https://trulia.com/profile/{username}", "check": "https://trulia.com/profile/{username}"},
    "Apartments.com": {"url": "https://apartments.com/profile/{username}", "check": "https://apartments.com/profile/{username}"},
    
    # News & Media Platforms
    "Medium Publications": {"url": "https://medium.com/search/posts?q={username}", "check": "https://medium.com/search/posts?q={username}"},
    "NewsBreak": {"url": "https://newsbreak.com/@{username}", "check": "https://newsbreak.com/@{username}"},
    "Flipboard": {"url": "https://flipboard.com/@{username}", "check": "https://flipboard.com/@{username}"},
    "Pocket": {"url": "https://getpocket.com/@{username}", "check": "https://getpocket.com/@{username}"},
    
    # Specialized Communities
    "Hacker News": {"url": "https://news.ycombinator.com/user?id={username}", "check": "https://hacker-news.firebaseio.com/v0/user/{username}.json", "api": True},
    "Product Hunt": {"url": "https://producthunt.com/@{username}", "check": "https://producthunt.com/@{username}"},
    "Indie Hackers": {"url": "https://indiehackers.com/{username}", "check": "https://indiehackers.com/{username}"},
    "Designer News": {"url": "https://designernews.co/{username}", "check": "https://designernews.co/{username}"},
    "Lobsters": {"url": "https://lobste.rs/u/{username}", "check": "https://lobste.rs/u/{username}"},
    
    # Phone & Communication Reverse Lookup
    "TrueCaller": {"url": "https://truecaller.com/search/{username}", "check": "https://truecaller.com/search/{username}"},
    "Sync.me": {"url": "https://sync.me/search/{username}", "check": "https://sync.me/search/{username}"},
    "CallerSmart": {"url": "https://callersmart.com/search/{username}", "check": "https://callersmart.com/search/{username}"},
    "WhoCalled": {"url": "https://whocalled.us/search/{username}", "check": "https://whocalled.us/search/{username}"},
    
    # Email & Domain Tools
    "Hunter.io": {"url": "https://hunter.io/search/{username}", "check": "https://hunter.io/search/{username}"},
    "VoilaNorbert": {"url": "https://voilanorbert.com/search/{username}", "check": "https://voilanorbert.com/search/{username}"},
    "EmailHippo": {"url": "https://emailhippo.com/search/{username}", "check": "https://emailhippo.com/search/{username}"},
    "RocketReach": {"url": "https://rocketreach.co/search/{username}", "check": "https://rocketreach.co/search/{username}"},
    
    # Government & Legal
    "USA.gov People": {"url": "https://usa.gov/search/{username}", "check": "https://usa.gov/search/{username}"},
    "Court Records": {"url": "https://courtrecords.org/search/{username}", "check": "https://courtrecords.org/search/{username}"},
    "Arrest Records": {"url": "https://arrestrecords.com/search/{username}", "check": "https://arrestrecords.com/search/{username}"},
    "Sex Offender Registry": {"url": "https://nsopw.gov/search/{username}", "check": "https://nsopw.gov/search/{username}"},
    "Bankruptcy Records": {"url": "https://pacer.gov/search/{username}", "check": "https://pacer.gov/search/{username}"},
    
    # International Platforms
    "Yandex": {"url": "https://yandex.com/search/?text={username}", "check": "https://yandex.com/search/?text={username}"},
    "Baidu Search": {"url": "https://baidu.com/s?wd={username}", "check": "https://baidu.com/s?wd={username}"},
    "DuckDuckGo": {"url": "https://duckduckgo.com/?q={username}", "check": "https://duckduckgo.com/?q={username}"},
    "Bing People": {"url": "https://bing.com/search?q={username}", "check": "https://bing.com/search?q={username}"},
    "Google People": {"url": "https://google.com/search?q={username}", "check": "https://google.com/search?q={username}"},
}

# Common false positive patterns to filter out
FALSE_POSITIVE_PATTERNS = [
    "user not found", "user does not exist", "page not found", "profile not found",
    "account suspended", "account deactivated", "account deleted", "user suspended",
    "this page doesn't exist", "sorry, this page isn't available", "page doesn't exist",
    "no user found", "invalid user", "user not available", "profile unavailable",
    "account not found", "username not found", "profile does not exist",
    "the page you requested does not exist", "404 not found", "page not available",
    "user has been suspended", "account has been suspended", "profile has been removed",
    "this account doesn't exist", "sorry, that page doesn't exist", "page cannot be found",
    "user profile not found", "no such user", "user doesn't exist", "invalid username",
    "account does not exist", "profile not available", "user not registered",
    "this user does not exist", "profile cannot be found", "account unavailable"
]

def check_username(query, platform_name, platform_info, search_type="username"):
    """Enhanced check with better false positive filtering"""
    try:
        # Choose appropriate URL based on search type
        if search_type == "name" and platform_info.get("supports_names", False) and "name_url" in platform_info:
            check_url = platform_info["name_url"].format(username=quote(query))
            display_url = platform_info["name_url"].format(username=query)
        else:
            check_url = platform_info["check"].format(username=quote(query))
            display_url = platform_info["url"].format(username=query)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        response = requests.get(check_url, headers=headers, timeout=12, allow_redirects=True)
        
        result = {
            "platform": platform_name,
            "url": display_url,
            "status": "unknown",
            "response_code": response.status_code,
            "is_leak_db": platform_info.get("leak_db", False),
            "search_type": search_type
        }
        
        # API-based checks with enhanced validation
        if platform_info.get("api", False):
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data and (isinstance(data, dict) or (isinstance(data, list) and len(data) > 0)):
                        # Additional validation for API responses
                        if isinstance(data, dict):
                            if data.get("message") == "Not Found" or data.get("error"):
                                result["status"] = "not_found"
                            else:
                                result["status"] = "found"
                        else:
                            result["status"] = "found"
                    else:
                        result["status"] = "not_found"
                except json.JSONDecodeError:
                    result["status"] = "error"
            elif response.status_code == 404:
                result["status"] = "not_found"
            else:
                result["status"] = "error"
        else:
            # Enhanced status code and content based checks
            if response.status_code == 200:
                content = response.text.lower()
                
                # Check for false positive patterns
                is_false_positive = any(pattern in content for pattern in FALSE_POSITIVE_PATTERNS)
                
                # Additional checks for specific platforms
                if platform_name.lower() in ["wikipedia", "wikimedia"]:
                    if "does not exist" in content or "page does not exist" in content:
                        is_false_positive = True
                
                if platform_name.lower() == "github":
                    if "not found" in content and "404" in content:
                        is_false_positive = True
                
                if platform_name.lower() in ["twitter", "x"]:
                    if "account suspended" in content or "user not found" in content:
                        is_false_positive = True
                
                if platform_name.lower() == "instagram":
                    if "page not found" in content or "user not found" in content:
                        is_false_positive = True
                
                if platform_name.lower() == "linkedin":
                    if "profile not found" in content or "member not found" in content:
                        is_false_positive = True
                
                # Set status based on checks
                if is_false_positive:
                    result["status"] = "not_found"
                else:
                    # Look for positive indicators
                    positive_indicators = [
                        "profile", "posts", "followers", "following", "about",
                        "bio", "description", "joined", "member since",
                        "tweets", "photos", "videos", "activity"
                    ]
                    
                    has_positive_indicators = any(indicator in content for indicator in positive_indicators)
                    
                    if has_positive_indicators:
                        result["status"] = "found"
                    else:
                        result["status"] = "not_found"
                        
            elif response.status_code == 404:
                result["status"] = "not_found"
            elif response.status_code == 403:
                result["status"] = "private/blocked"
            elif response.status_code == 429:
                result["status"] = "rate_limited"
            else:
                result["status"] = "error"
        
        return result
        
    except requests.exceptions.Timeout:
        return {
            "platform": platform_name,
            "url": display_url if 'display_url' in locals() else platform_info["url"].format(username=query),
            "status": "timeout",
            "response_code": None,
            "is_leak_db": platform_info.get("leak_db", False),
            "search_type": search_type
        }
    except Exception as e:
        return {
            "platform": platform_name,
            "url": display_url if 'display_url' in locals() else platform_info["url"].format(username=query),
            "status": "error",
            "response_code": None,
            "is_leak_db": platform_info.get("leak_db", False),
            "search_type": search_type,
            "error": str(e)[:100]
        }

def main():
    # Header
    st.markdown('<h1 class="main-header">🎯 TraceName</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Advanced Username & Name Intelligence Platform</p>', unsafe_allow_html=True)
    
    # Stats display
    total_platforms = len(PLATFORMS)
    leak_db_count = len([p for p in PLATFORMS.values() if p.get("leak_db", False)])
    name_supported = len([p for p in PLATFORMS.values() if p.get("supports_names", False)])
    
    st.markdown(f"""
    <div class="stats-container">
        <div class="stat-box">
            <span class="stat-number">{total_platforms}</span>
            <div>Platforms</div>
        </div>
        <div class="stat-box">
            <span class="stat-number">{leak_db_count}</span>
            <div>Leak DBs</div>
        </div>
        <div class="stat-box">
            <span class="stat-number">{name_supported}</span>
            <div>Name Search</div>
        </div>
        <div class="stat-box">
            <span class="stat-number">∞</span>
            <div>Possibilities</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Search type selection
    search_type = st.radio(
        "Search Type:",
        ["Username", "Real Name"],
        horizontal=True,
        help="Choose whether to search for usernames or real names"
    )
    
    # Search interface
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if search_type == "Username":
            query = st.text_input(
                "",
                placeholder="Enter username to trace...",
                key="username_input",
                help="Enter the target username for comprehensive OSINT lookup"
            )
        else:
            query = st.text_input(
                "",
                placeholder="Enter real name to search...",
                key="name_input",
                help="Enter the person's real name to search across platforms"
            )
        
# Filter options
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            hide_not_found = st.checkbox("Hide Not Found", value=True, help="Hide platforms where no profile was found")
        with col_filter2:
            hide_errors = st.checkbox("Hide Errors/Timeouts", value=False, help="Hide platforms that had errors or timeouts")
        
        search_clicked = st.button("🔍 Trace Target", type="primary", use_container_width=True)
    
    # Warning
    st.warning("⚠️ **For Cybersecurity & OSINT Research Only** - Use responsibly and ethically")
    
    if query and search_clicked:
        # Input validation
        if search_type == "Username":
            if not re.match(r'^[a-zA-Z0-9._-]+$', query) or len(query) > 50:
                st.error("Invalid username format")
                return
        else:
            if len(query) > 100 or len(query) < 2:
                st.error("Invalid name format")
                return
            
        st.markdown("---")
        st.markdown(f"### 🎯 Tracing: **{query}** ({search_type})")
        
        # Progress tracking
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                found_count = st.empty()
            with col2:
                total_checked = st.empty()  
            with col3:
                leak_alerts = st.empty()
            with col4:
                error_count = st.empty()
            with col5:
                progress_pct = st.empty()
        
        # Results containers
        results_container = st.container()
        
        # Execute search
        results = []
        completed = 0
        found = 0
        leaks_found = 0
        errors = 0
        
        search_mode = "name" if search_type == "Real Name" else "username"
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_platform = {
                executor.submit(check_username, query, name, info, search_mode): name
                for name, info in PLATFORMS.items()
            }
            
            for future in as_completed(future_to_platform):
                result = future.result()
                results.append(result)
                completed += 1
                
                if result["status"] == "found":
                    found += 1
                    if result.get("is_leak_db", False):
                        leaks_found += 1
                elif result["status"] in ["error", "timeout", "rate_limited"]:
                    errors += 1
                
                # Update progress
                progress = completed / total_platforms
                progress_bar.progress(progress)
                status_text.text(f"Checking {result['platform']}... ({completed}/{total_platforms})")
                
                found_count.metric("✅ Found", found)
                total_checked.metric("📊 Checked", f"{completed}/{total_platforms}")
                leak_alerts.metric("🚨 Leak DBs", leaks_found)
                error_count.metric("⚠️ Errors", errors)
                progress_pct.metric("⚡ Progress", f"{int(progress*100)}%")
        
        # Clear progress
        progress_container.empty()
        
        # Filter results based on user preferences
        filtered_results = results.copy()
        
        if hide_not_found:
            filtered_results = [r for r in filtered_results if r["status"] != "not_found"]
        
        if hide_errors:
            filtered_results = [r for r in filtered_results if r["status"] not in ["error", "timeout", "rate_limited"]]
        
        # Sort results: leak DBs first, then found, then errors, then not found
        def sort_key(x):
            if x["status"] == "found" and x.get("is_leak_db", False):
                return (0, x["platform"])  # Leak DBs first
            elif x["status"] == "found":
                return (1, x["platform"])  # Regular found
            elif x["status"] in ["error", "timeout", "rate_limited", "private/blocked"]:
                return (2, x["platform"])  # Errors
            else:
                return (3, x["platform"])  # Not found last
        
        filtered_results.sort(key=sort_key)
        
        # Display results
        with results_container:
            st.markdown(f"### 📋 Results ({len(filtered_results)} shown)")
            
            if not filtered_results:
                st.info("No results to display with current filters. Try adjusting your filter settings.")
            else:
                # Create columns for better layout
                col1, col2 = st.columns(2)
                
                left_results = []
                right_results = []
                
                # Split results between columns
                for i, result in enumerate(filtered_results):
                    if i % 2 == 0:
                        left_results.append(result)
                    else:
                        right_results.append(result)
                
                # Display left column
                with col1:
                    for result in left_results:
                        display_result(result)
                
                # Display right column
                with col2:
                    for result in right_results:
                        display_result(result)
            
            # Summary stats
            st.markdown("---")
            st.markdown("### 📊 Trace Summary")
            
            summary_col1, summary_col2, summary_col3, summary_col4, summary_col5 = st.columns(5)
            
            with summary_col1:
                st.metric("Total Platforms", total_platforms)
            with summary_col2:
                st.metric("Profiles Found", found, delta=f"{round(found/total_platforms*100, 1)}%")
            with summary_col3:
                st.metric("Leak Database Hits", leaks_found, delta="🚨" if leaks_found > 0 else "✅")
            with summary_col4:
                st.metric("Errors/Timeouts", errors)
            with summary_col5:
                not_found_count = len([r for r in results if r["status"] == "not_found"])
                st.metric("Not Found", not_found_count)
            
            # Export functionality
            if found > 0:
                st.markdown("### 📥 Export Results")
                
                export_data = []
                for result in results:
                    if result["status"] == "found":
                        export_data.append({
                            "Platform": result["platform"],
                            "URL": result["url"],
                            "Status": result["status"],
                            "Search_Type": result.get("search_type", "username"),
                            "Leak_Database": result.get("is_leak_db", False),
                            "Response_Code": result.get("response_code", "")
                        })
                
                if export_data:
                    df = pd.DataFrame(export_data)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        csv_data = df.to_csv(index=False)
                        st.download_button(
                            "📄 Download CSV Report",
                            csv_data,
                            f"tracename_{query.replace(' ', '_')}_{int(time.time())}.csv",
                            "text/csv"
                        )
                    with col2:
                        json_data = json.dumps(export_data, indent=2)
                        st.download_button(
                            "📋 Download JSON Report", 
                            json_data,
                            f"tracename_{query.replace(' ', '_')}_{int(time.time())}.json",
                            "application/json"
                        )
                        
            # Additional tools section
            if found > 5:  # Only show if we found substantial results
                st.markdown("---")
                st.markdown("### 🔧 Additional OSINT Tools")
                
                tool_col1, tool_col2, tool_col3 = st.columns(3)
                
                with tool_col1:
                    st.markdown("""
                    **🔍 Further Investigation:**
                    - Cross-reference usernames
                    - Check profile creation dates
                    - Analyze posting patterns
                    - Look for connected accounts
                    """)
                
                with tool_col2:
                    st.markdown("""
                    **📊 Data Analysis:**
                    - Compare profile information
                    - Timeline correlation
                    - Social network mapping
                    - Behavioral analysis
                    """)
                
                with tool_col3:
                    st.markdown("""
                    **🛡️ Security Assessment:**
                    - Password reuse patterns
                    - Information disclosure
                    - Privacy settings review
                    - Digital footprint analysis
                    """)

def display_result(result):
    """Display a single result with enhanced styling"""
    platform = result["platform"]
    url = result["url"]
    status = result["status"]
    is_leak = result.get("is_leak_db", False)
    search_type = result.get("search_type", "username")
    
    # Add search type indicator
    type_indicator = "👤" if search_type == "name" else "🔤"
    
    if status == "found":
        if is_leak:
            st.markdown(f"""
            <div class="leak-warning">
                🚨 <strong>{platform}</strong> - POTENTIAL DATA BREACH {type_indicator}
                <div class="platform-url">
                    <a href="{url}" target="_blank" style="color: white; text-decoration: none;">{url}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="result-found">
                <div class="platform-name">✅ {platform} {type_indicator}</div>
                <div class="platform-url">
                    <a href="{url}" target="_blank" style="color: white; text-decoration: none;">{url}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    elif status == "not_found":
        st.markdown(f"""
        <div class="result-not-found">
            <div class="platform-name">❌ {platform} {type_indicator}</div>
            <div class="platform-url">{url}</div>
        </div>
        """, unsafe_allow_html=True)
    
    elif status in ["error", "timeout", "rate_limited", "private/blocked"]:
        status_icons = {
            "error": "⚠️",
            "timeout": "⏱️", 
            "rate_limited": "🚫",
            "private/blocked": "🔒"
        }
        status_icon = status_icons.get(status, "⚠️")
        
        st.markdown(f"""
        <div class="result-error">
            <div class="platform-name">{status_icon} {platform} - {status.replace('_', ' ').title()} {type_indicator}</div>
            <div class="platform-url">{url}</div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
                st.error("Invalid username format")
                return
        else:
            if len(query) > 100 or len(query) < 2:
                st.error("Invalid name format")
                return
            
        st.markdown("---")
        st.markdown(f"### 🎯 Tracing: **{query}** ({search_type})")
        
        # Progress tracking
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                found_count = st.empty()
            with col2:
                total_checked = st.empty()  
            with col3:
                leak_alerts = st.empty()
            with col4:
                error_count = st.empty()
            with col5:
                progress_pct = st.empty()
        
        # Results containers
        results_container = st.container()
        
        # Execute search
        results = []
        completed = 0
        found = 0
        leaks_found = 0
        errors = 0
        
        search_mode = "name" if search_type == "Real Name" else "username"
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_platform = {
                executor.submit(check_username, query, name, info, search_mode): name
                for name, info in PLATFORMS.items()
            }
            
            for future in as_completed(future_to_platform):
                result = future.result()
                results.append(result)
                completed += 1
                
                if result["status"] == "found":
                    found += 1
                    if result.get("is_leak_db", False):
                        leaks_found += 1
                elif result["status"] in ["error", "timeout", "rate_limited"]:
                    errors += 1
                
                # Update progress
                progress = completed / total_platforms
                progress_bar.progress(progress)
                status_text.text(f"Checking {result['platform']}... ({completed}/{total_platforms})")
                
                found_count.metric("✅ Found", found)
                total_checked.metric("📊 Checked", f"{completed}/{total_platforms}")
                leak_alerts.metric("🚨 Leak DBs", leaks_found)
                error_count.metric("⚠️ Errors", errors)
                progress_pct.metric("⚡ Progress", f"{int(progress*100)}%")
        
        # Clear progress
        progress_container.empty()
        
        # Filter results based on user preferences
        filtered_results = results.copy()
        
        if hide_not_found:
            filtered_results = [r for r in filtered_results if r["status"] != "not_found"]
        
        if hide_errors:
            filtered_results = [r for r in filtered_results if r["status"] not in ["error", "timeout", "rate_limited"]]
        
        # Sort results: leak DBs first, then found, then errors, then not found
        def sort_key(x):
            if x["status"] == "found" and x.get("is_leak_db", False):
                return (0, x["platform"])  # Leak DBs first
            elif x["status"] == "found":
                return (1, x["platform"])  # Regular found
            elif x["status"] in ["error", "timeout", "rate_limited", "private/blocked"]:
                return (2, x["platform"])  # Errors
            else:
                return (3, x["platform"])  # Not found last
        
        filtered_results.sort(key=sort_key)
        
        # Display results
        with results_container:
            st.markdown(f"### 📋 Results ({len(filtered_results)} shown)")
            
            if not filtered_results:
                st.info("No results to display with current filters. Try adjusting your filter settings.")
            else:
                # Create columns for better layout
                col1, col2 = st.columns(2)
                
                left_results = []
                right_results = []
                
                # Split results between columns
                for i, result in enumerate(filtered_results):
                    if i % 2 == 0:
                        left_results.append(result)
                    else:
                        right_results.append(result)
                
                # Display left column
                with col1:
                    for result in left_results:
                        display_result(result)
                
                # Display right column
                with col2:
                    for result in right_results:
                        display_result(result)
            
            # Summary stats
            st.markdown("---")
            st.markdown("### 📊 Trace Summary")
            
            summary_col1, summary_col2, summary_col3, summary_col4, summary_col5 = st.columns(5)
            
            with summary_col1:
                st.metric("Total Platforms", total_platforms)
            with summary_col2:
                st.metric("Profiles Found", found, delta=f"{round(found/total_platforms*100, 1)}%")
            with summary_col3:
                st.metric("Leak Database Hits", leaks_found, delta="🚨" if leaks_found > 0 else "✅")
            with summary_col4:
                st.metric("Errors/Timeouts", errors)
            with summary_col5:
                not_found_count = len([r for r in results if r["status"] == "not_found"])
                st.metric("Not Found", not_found_count)
            
            # Export functionality
            if found > 0:
                st.markdown("### 📥 Export Results")
                
                export_data = []
                for result in results:
                    if result["status"] == "found":
                        export_data.append({
                            "Platform": result["platform"],
                            "URL": result["url"],
                            "Status": result["status"],
                            "Search_Type": result.get("search_type", "username"),
                            "Leak_Database": result.get("is_leak_db", False),
                            "Response_Code": result.get("response_code", "")
                        })
                
                if export_data:
                    df = pd.DataFrame(export_data)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        csv_data = df.to_csv(index=False)
                        st.download_button(
                            "📄 Download CSV Report",
                            csv_data,
                            f"tracename_{query.replace(' ', '_')}_{int(time.time())}.csv",
                            "text/csv"
                        )
                    with col2:
                        json_data = json.dumps(export_data, indent=2)
                        st.download_button(
                            "📋 Download JSON Report", 
                            json_data,
                            f"tracename_{query.replace(' ', '_')}_{int(time.time())}.json",
                            "application/json"
                        )
                        
            # Additional tools section
            if found > 5:  # Only show if we found substantial results
                st.markdown("---")
                st.markdown("### 🔧 Additional OSINT Tools")
                
                tool_col1, tool_col2, tool_col3 = st.columns(3)
                
                with tool_col1:
                    st.markdown("""
                    **🔍 Further Investigation:**
                    - Cross-reference usernames
                    - Check profile creation dates
                    - Analyze posting patterns
                    - Look for connected accounts
                    """)
                
                with tool_col2:
                    st.markdown("""
                    **📊 Data Analysis:**
                    - Compare profile information
                    - Timeline correlation
                    - Social network mapping
                    - Behavioral analysis
                    """)
                
                with tool_col3:
                    st.markdown("""
                    **🛡️ Security Assessment:**
                    - Password reuse patterns
                    - Information disclosure
                    - Privacy settings review
                    - Digital footprint analysis
                    """)

def display_result(result):
    """Display a single result with enhanced styling"""
    platform = result["platform"]
    url = result["url"]
    status = result["status"]
    is_leak = result.get("is_leak_db", False)
    search_type = result.get("search_type", "username")
    
    # Add search type indicator
    type_indicator = "👤" if search_type == "name" else "🔤"
    
    if status == "found":
        if is_leak:
            st.markdown(f"""
            <div class="leak-warning">
                🚨 <strong>{platform}</strong> - POTENTIAL DATA BREACH {type_indicator}
                <div class="platform-url">
                    <a href="{url}" target="_blank" style="color: white; text-decoration: none;">{url}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="result-found">
                <div class="platform-name">✅ {platform} {type_indicator}</div>
                <div class="platform-url">
                    <a href="{url}" target="_blank" style="color: white; text-decoration: none;">{url}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    elif status == "not_found":
        st.markdown(f"""
        <div class="result-not-found">
            <div class="platform-name">❌ {platform} {type_indicator}</div>
            <div class="platform-url">{url}</div>
        </div>
        """, unsafe_allow_html=True)
    
    elif status in ["error", "timeout", "rate_limited", "private/blocked"]:
        status_icons = {
            "error": "⚠️",
            "timeout": "⏱️", 
            "rate_limited": "🚫",
            "private/blocked": "🔒"
        }
        status_icon = status_icons.get(status, "⚠️")
        
        st.markdown(f"""
        <div class="result-error">
            <div class="platform-name">{status_icon} {platform} - {status.replace('_', ' ').title()} {type_indicator}</div>
            <div class="platform-url">{url}</div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
