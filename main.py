import os
import base64
import json
import spacy
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import pubsub_v1
from newspaper import Article, ArticleException, Config
from retry import retry
import pke

spacy.cli.download('en')

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
    config = Config()
    config.follow_meta_refresh = True
    config.keep_article_html = True
    article = Article(url, config=config)
    article.download()
    return article


def extract_keywords(url):
    article = download_article(url)
    article.parse()
    lang = article.meta_lang
    if lang in ('en', ''):
        article.nlp()

        extractor = pke.unsupervised.YAKE()
        extractor.load_document(input=article.title + '\n' + article.text, language='en')
        extractor.candidate_selection()
        extractor.candidate_weighting()
        keyphrases = extractor.get_n_best(n=10)

        return article.keywords + [phrase.replace(' ', '-') for (phrase, score) in keyphrases]
    return None


def post_scraper(event, _):
    if 'data' in event:
        data = json.loads(base64.b64decode(event['data']).decode('utf-8'))
        print(f'[{data["id"]}] scraping {data["url"]}')
        keywords = extract_keywords(data['url'])
        if keywords is not None:
            data['keywords'] = keywords
        else:
            print(f'[{data["id"]}] non-english content (url={data["url"]})')
        publish('post-keywords-extracted', data)
