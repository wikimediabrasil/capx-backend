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

            # Step 1.5: Batch fetch sender/receiver info and validate receiver
            sender_username = MessageService._cap(instance.sender.username)
            receiver_username = MessageService._cap(instance.receiver)

            users_info = MessageService._fetch_users_info(oauth, url, [receiver_username, sender_username])

            receiver = users_info.get(receiver_username, {})
            sender = users_info.get(sender_username, {})

            if not receiver or receiver.get('missing') or receiver.get('invalid'):
                MessageService._update_instance_status(
                    instance,
                    'failed',
                    'Receiver account is invalid or does not exist.'
                )
                return

            # Step 2: Fetch CSRF token
            token = MessageService._fetch_csrf_token(oauth, url)
            if not token:
                MessageService._update_instance_status(instance, 'failed', 'Failed to fetch CSRF token.')
                return

            # Step 3: Decide method and send message
            if instance.method == 'talkpage':
                success = MessageService._send_talk_page(oauth, url, instance, token)
            elif instance.method == 'email':
                # Use batch-fetched info for emailable checks
                receiver_emailable = receiver.get('emailable', False)
                sender_emailable = sender.get('emailable', False)

                if not receiver_emailable:
                    error_message = 'Receiver is not emailable. Using talk page instead.'
                    success = MessageService._send_talk_page(oauth, url, instance, token)
                elif not sender_emailable:
                    error_message = 'Sender is not emailable. Using talk page instead.'
                    success = MessageService._send_talk_page(oauth, url, instance, token)
                else:
                    success = MessageService._send_email(oauth, url, instance, token)

            # Step 4: Update the instance status
            MessageService._update_instance_status(
                instance,
                'sent' if success else 'failed',
                error_message if 'error_message' in locals() else ''
            )

        except Exception as e:
            MessageService._update_instance_status(instance, 'failed', f'An exception occurred: {str(e)}')

    @staticmethod
    def _cap(username):
        return username[0].upper() + username[1:]

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
    def _fetch_users_info(oauth, url, usernames):
        # Accept list of usernames and perform a single batch query
        # API expects pipe-separated usernames
        joined = '|'.join([str(u) for u in usernames])
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'users',
            'formatversion': '2',
            'usprop': 'emailable',
            'ususers': joined,
        }
        response = oauth.get(url, params=params, timeout=60)
        users = response.json().get('query', {}).get('users', [])

        # Map results
        users_info = {}
        for user in users:
            key = user.get('name')
            if not key:
                raise ValueError("User entry missing 'name' field; this indicates an unexpected API response: %r" % (user,))
            users_info[key] = user
        return users_info

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
