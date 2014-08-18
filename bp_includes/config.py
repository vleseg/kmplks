"""
============= DON'T MODIFY THIS FILE ============
This is the boilerplate default configuration file.
Changes and additions to settings should be done in
/bp_content/themes/<YOUR_THEME>/config/ rather than this config.
"""

import os

config = {

    # webapp2 sessions
    'webapp2_extras.sessions': {'secret_key': '4fqAju4WUIquDXUILz7GrtVQX0NequGBKACFD7gn8dvitRXtfHa4fPofwmDpM7YO'},

    # webapp2 authentication
    'webapp2_extras.auth': {'user_model': 'bp_includes.models.User',
                            'cookie_name': 'session_name'},

    # jinja2 templates
    'webapp2_extras.jinja2': {'template_path': ['bp_admin/templates', 'bp_content/themes/%s/templates' % os.environ['theme']],
                              'environment_args': {'extensions': ['jinja2.ext.i18n']}},

    # application name
    'app_name': "GAE Boilerplate",

    # the default language code for the application.
    # should match whatever language the site uses when i18n is disabled
    'app_lang': 'ru',

    # Locale code = <language>_<territory> (ie 'en_US')
    # to pick locale codes see http://cldr.unicode.org/index/cldr-spec/picking-the-right-language-code
    # also see http://www.sil.org/iso639-3/codes.asp
    # Language codes defined under iso 639-1 http://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
    # Territory codes defined under iso 3166-1 alpha-2 http://en.wikipedia.org/wiki/ISO_3166-1
    # disable i18n if locales array is empty or None
    'locales': [],

    # contact page email settings
    'contact_sender': "",
    'contact_recipient': "",

    # Password AES Encryption Parameters
    # aes_key must be only 16 (*AES-128*), 24 (*AES-192*), or 32 (*AES-256*) bytes (characters) long.
    'aes_key': "E08M4OvLCcPdT6GJQieD0keQWbw3uNM6",
    'salt': "NWphwSaxay7e0FjCgpI67vvzhST8sNd3YVv4pswATww8z6qXyVcDLJnPrMJ0kc0R",

    # get your own consumer key and consumer secret by registering at https://dev.twitter.com/apps
    # callback url must be: http://[YOUR DOMAIN]/login/twitter/complete
    # VLS: social network integration will not be used
    # 'twitter_consumer_key': 'TWITTER_CONSUMER_KEY',
    # 'twitter_consumer_secret': 'TWITTER_CONSUMER_SECRET',

    #Facebook Login
    # get your own consumer key and consumer secret by registering at https://developers.facebook.com/apps
    #Very Important: set the site_url= your domain in the application settings in the facebook app settings page
    # callback url must be: http://[YOUR DOMAIN]/login/facebook/complete
    # VLS: social network integration will not be used
    # 'fb_api_key': 'FACEBOOK_API_KEY',
    # 'fb_secret': 'FACEBOOK_SECRET',

    #Linkedin Login
    #Get you own api key and secret from https://www.linkedin.com/secure/developer
    # VLS: social network integration will not be used
    # 'linkedin_api': 'LINKEDIN_API',
    # 'linkedin_secret': 'LINKEDIN_SECRET',

    # Github login
    # Register apps here: https://github.com/settings/applications/new
    # VLS: social network integration will not be used
    # 'github_server': 'github.com',
    # 'github_redirect_uri': 'http://www.example.com/social_login/github/complete',
    # 'github_client_id': 'GITHUB_CLIENT_ID',
    # 'github_client_secret': 'GITHUB_CLIENT_SECRET',

    # get your own recaptcha keys by registering at http://www.google.com/recaptcha/
    # VLS: reCaptcha won't be used (perhaps)
    # 'captcha_public_key': "CAPTCHA_PUBLIC_KEY",
    # 'captcha_private_key': "CAPTCHA_PRIVATE_KEY",

    # Use a complete Google Analytics code, no just the Tracking ID
    # In config/boilerplate.py there is an example to fill out this value
    # VLS: Google Analytics will not be used.
    # 'google_analytics_code': "",

    # add status codes and templates used to catch and display errors
    # if a status code is not listed here it will use the default app engine
    # stacktrace error page or browser error page
    'error_templates': {
        403: 'errors/default_error.html',
        404: 'errors/default_error.html',
        500: 'errors/default_error.html',
    },

    # Enable Federated login (OpenID and OAuth)
    # Google App Engine Settings must be set to Authentication Options: Federated Login
    # VLS: Federated login will not be used.
    'enable_federated_login': False,

    # jinja2 base layout template
    'base_layout': 'base.html',

    # send error emails to developers
    'send_mail_developer': False,

    # fellas' list
    'developers': 'vlesiil@yandex.ru',

    # If true, it will write in datastore a log of every email sent
    'log_email': True,

    # If true, it will write in datastore a log of every visit
    'log_visit': True,

    # ----> ADD MORE CONFIGURATION OPTIONS HERE <----

} # end config
