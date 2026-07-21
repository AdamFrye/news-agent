# news-agent

This is my news agent project I wrote in like a week. It summarizes x amount of articles from a freshRSS feed and posts them to a GitHub Repo. I did this so that I could pull them down into Obsidian using Obsidian Git. Theres a few silly things in this project but it works.

## Description

The script is a self hosted scheduled event that triggers at a configurable time everyday. I have mine set to 8:50 in the morning so its ready when I start work. It starts by grabbing the articles from your FreshRSS feed from the past 24 hours and sorts them by category. In the config you can set how many articles you want summarized by category. There's an example config if you want to take a look. Then it scrapes the news website for the content of the webpage and feeds it to your OpenWebUi Reponses endpoint and asks for a summary one by one that is then joined together and pushed to github. I chose OpenWebUi because I feed it to my self hosted agent but I'm pretty sure you can do this with any frontier labs API.

## How to Setup

I have a config example, a dotenv example, and a docker-compose that is very close to what I personally use. Once you have the relevant fields entered, just run `docker compose up -d` and it should spin up. In the config you can also change the prompts you give to the article selector and the summarizer. I don't really recommend you change the article selectors prompt very much since it relies very heavily on the output being exactly what it expects. To achieve this make sure to set the temperature of your model extremely low. Like 0. For the summarizer this matters way less.

## Feedback

If anybody has feedback, please create a GitHub issue I'd be tickled to work on this further if someone wants to use it besides me.
