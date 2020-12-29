import json
import base64
from newspaper import ArticleException
from main import post_scraper


def test_post_scraper(mocker):
    payload = {'id': '1', 'url': 'https://daily.dev/posts/docker-compose-the-perfect-development-environment',
               'publicationId': 'pub'}
    event = {'data': base64.b64encode(json.dumps(payload).encode('utf-8'))}
    publish = mocker.patch('main.publish')
    post_scraper(event, None)
    payload['keywords'] = mocker.ANY
    publish.assert_called_once_with('post-keywords-extracted', payload)


def test_post_scraper_not_available(mocker):
    payload = {'id': '1', 'url': 'https://daily2.dev', 'publicationId': 'pub'}
    event = {'data': base64.b64encode(json.dumps(payload).encode('utf-8'))}
    publish = mocker.patch('main.publish')
    try:
        post_scraper(event, None)
    except ArticleException:
        pass
    assert not publish.called, 'method should not have been called'


def test_post_scraper_ignore_non_english(mocker):
    payload = {'id': '1', 'url': 'https://engineerteam.note.jp/n/n2504ddfe61c7',
               'publicationId': 'pub'}
    event = {'data': base64.b64encode(json.dumps(payload).encode('utf-8'))}
    publish = mocker.patch('main.publish')
    post_scraper(event, None)
    publish.assert_called_once_with('post-keywords-extracted', payload)
