from requests_oauthlib import OAuth1Session
from django.conf import settings
from social_django.models import UserSocialAuth

class MessageService:
    @staticmethod
    def send_message(instance):
        """
        Sends a message via Wikimedia API. Supports email or user talk page messages.
        Updates the message's status accordingly.
        """
        url = 'https://meta.wikimedia.org/w/api.php'
        
        try:
            # Step 1: Get the OAuth credentials
            oauth = MessageService._get_oauth_session(instance.sender)

            # Step 2: Fetch CSRF token
            token = MessageService._fetch_csrf_token(oauth, url)
            if not token:
                MessageService._update_instance_status(instance, 'failed', 'Failed to fetch CSRF token.')
                return

            # Step 3: Decide method and send message
            error_message = ''
            if instance.method == 'talkpage':
                success = MessageService._send_talk_page(oauth, url, instance, token)
            elif instance.method == 'email':
                if not MessageService._is_user_emailable(oauth, url, instance.receiver):
                    error_message = 'Receiver is not emailable. Using talk page instead.'
                    instance.method = 'talkpage'
                    success = MessageService._send_talk_page(oauth, url, instance, token)
                elif not MessageService._is_user_emailable(oauth, url, instance.sender):
                    error_message = 'Sender is not emailable. Using talk page instead.'
                    instance.method = 'talkpage'
                    success = MessageService._send_talk_page(oauth, url, instance, token)
                else:
                    success = MessageService._send_email(oauth, url, instance, token)

            # Step 4: Update the instance status
            MessageService._update_instance_status(
                instance,
                'sent' if success else 'failed',
                error_message
            )

        except Exception as e:
            MessageService._update_instance_status(instance, 'failed', f'An exception occurred: {str(e)}')

    @staticmethod
    def _get_oauth_session(sender):
        user_social_auth = UserSocialAuth.objects.get(user=sender)
        return OAuth1Session(
            settings.SOCIAL_AUTH_MEDIAWIKI_KEY,
            client_secret=settings.SOCIAL_AUTH_MEDIAWIKI_SECRET,
            resource_owner_key=user_social_auth.extra_data['access_token']['oauth_token'],
            resource_owner_secret=user_social_auth.extra_data['access_token']['oauth_token_secret']
        )

    @staticmethod
    def _update_instance_status(instance, status, error_message):
        instance.status = status
        # Set error_message: preserve when there's a fallback (sent with warning) or failure
        # Clear error_message when successful without fallback
        instance.error_message = error_message
        instance.subject = ''
        instance.message = ''
        instance.save()

    @staticmethod
    def _fetch_csrf_token(oauth, url):
        params = {
            'action': 'query',
            'meta': 'tokens',
            'format': 'json',
            'formatversion': '2',
        }
        response = oauth.get(url, params=params, timeout=60)
        return response.json().get('query', {}).get('tokens', {}).get('csrftoken', '')

    @staticmethod
    def _is_user_emailable(oauth, url, receiver):
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'users',
            'formatversion': '2',
            'usprop': 'emailable',
            'ususers': receiver,
        }
        response = oauth.get(url, params=params, timeout=60)
        return response.json().get('query', {}).get('users', [{}])[0].get('emailable', False)

    @staticmethod
    def _send_email(oauth, url, instance, token):
        params = {
            'action': 'emailuser',
            'target': instance.receiver,
            'subject': '[Capacity Exchange] ' + instance.subject,
            'text': instance.message,
            'ccme': '1',
            'format': 'json',
            'token': token,
        }
        response = oauth.post(url, data=params, timeout=60)
        return response.json().get('emailuser', {}).get('result') == 'Success'

    @staticmethod
    def _send_talk_page(oauth, url, instance, token):
        params = {
            'action': 'edit',
            'title': f'User talk:{instance.receiver}',
            'section': 'new',
            'sectiontitle': '[Capacity Exchange] ' + instance.subject,
            'text': instance.message + '\n\n--~~~~',
            'format': 'json',
            'token': token,
        }
        response = oauth.post(url, data=params, timeout=60)
        return response.json().get('edit', {}).get('result') == 'Success'
