import json
import logging

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
import requests
import urlparse
import time

log = logging.getLogger(__name__)


class Command(BaseCommand):
    args = "<queue_name>"
    help = "Pull items from given queues and send to grading controller"

    def handle(self, *args, **options):
        """
        Constant loop that pulls from queue and posts to grading controller
        """
        log.info(' [*] Pulling from xqueues...')
        self.s=requests.session()

        flag=True
        error = self.login()

        while flag:
            for queue_name in args:
                try:
                    queue_item=self.get_from_queue(queue_name)
                    log.debug(parse_xreply(queue_item))
                    
                    #Post to grading controller here!

                except Exception as err:
                    log.debug("Error getting submission: ".format(err))
                time.sleep(2)

    def login(self):
        '''
        Login to xqueue to pull submissions
        '''
        full_login_url = urlparse.urljoin(settings.XQUEUE_INTERFACE['url'],'/xqueue/login/')

        response = self.s.post(full_login_url,{'username': settings.XQUEUE_INTERFACE['django_auth']['username'],
                                            'password': settings.XQUEUE_INTERFACE['django_auth']['password']})

        response.raise_for_status()
        log.debug("login response: %r", response.json)

        log.debug(response.content)
        (error,msg)= parse_xreply(response.content)

        log.debug(error)

        return error

    def get_from_queue(self,queue_name):
        """
        Get a single submission from xqueue
        """
        try:
            response = self._http_get(urlparse.urljoin(settings.XQUEUE_INTERFACE['url'],'/xqueue/get_submission/'),
                {'queue_name' : queue_name})
        except Exception as err:
            return "Error getting response: {0}".format(err)

        return response

    def _http_get(self,url, data):
        try:
            r = self.s.get(url, params=data)
        except requests.exceptions.ConnectionError, err:
            log.error(err)
            return (1, 'cannot connect to server')

        if r.status_code not in [200]:
            return (1, 'unexpected HTTP status code [%d]' % r.status_code)

        return parse_xreply(r.text)


def parse_xreply(xreply):
    """
    Parse the reply from xqueue. Messages are JSON-serialized dict:
        { 'return_code': 0 (success), 1 (fail)
          'content': Message from xqueue (string)
        }
    """
    try:
        xreply = json.loads(xreply)
    except ValueError, err:
        log.error(err)
        return (1, 'unexpected reply from server')

    return_code = xreply['return_code']
    content = xreply['content']
    return (return_code, content)