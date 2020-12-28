import base64
import json
import os
import nltk
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import pubsub_v1
from newspaper import Article, ArticleException
from retry import retry

nltk.download('punkt')

try:
    publisher = pubsub_v1.PublisherClient()
except DefaultCredentialsError:  # For testing purposes
    pass
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')


# Publishes a message to a Cloud Pub/Sub topic.
def publish(topic_name, data):
    topic_path = publisher.topic_path(PROJECT_ID, topic_name)  # pylint: disable=no-member

    message_json = json.dumps(data)
    message_bytes = message_json.encode('utf-8')

    publish_future = publisher.publish(topic_path, data=message_bytes)
    publish_future.result()  # Verify the publish succeeded


@retry(ArticleException, tries=5, delay=1, backoff=2, max_delay=10)
def download_article(url):
    article = Article(url)
    article.download()
    return article


def post_scraper(event, _):
    if 'data' in event:
        data = json.loads(base64.b64decode(event['data']).decode('utf-8'))
        print(f'[{data["id"]}] scraping {data["url"]}')
        article = download_article(data['url'])
        article.parse()
        article.nlp()
        data['keywords'] = article.keywords
        publish('post-keywords-extracted', data)
