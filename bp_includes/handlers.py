# -*- coding: utf-8 -*-

"""
    A real simple app for using webapp2 with auth and session.

    It just covers the basics. Creating a user, login, logout
    and a decorator for protecting certain handlers.

    Routes are setup in routes.py and added in main.py
"""
# standard library imports
import logging
import json

# related third party imports
import webapp2
from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras.i18n import gettext as _
from webapp2_extras.appengine.auth.models import Unique
from google.appengine.api import taskqueue
from google.appengine.api import users
from google.appengine.api.datastore_errors import BadValueError
from google.appengine.runtime import apiproxy_errors

# local application/library specific imports
import models
import forms as forms
from lib import utils, captcha
from lib.basehandler import BaseHandler
from lib.decorators import user_required
from lib.decorators import taskqueue_method


class LoginRequiredHandler(BaseHandler):
    def get(self):
        continue_url, = self.request.get('continue', allow_multiple=True)
        self.redirect(users.create_login_url(dest_url=continue_url))


class RegisterBaseHandler(BaseHandler):
    """
    Base class for handlers with registration and login forms.
    """

    @webapp2.cached_property
    def form(self):
        return forms.RegisterForm(self)


class SendEmailHandler(BaseHandler):
    """
    Core Handler for sending Emails
    Use with TaskQueue
    """

    @taskqueue_method
    def post(self):

        from google.appengine.api import mail, app_identity

        to = self.request.get("to")
        subject = self.request.get("subject")
        body = self.request.get("body")
        sender = self.request.get("sender")

        if sender != '' or not utils.is_email_valid(sender):
            if utils.is_email_valid(self.app.config.get('contact_sender')):
                sender = self.app.config.get('contact_sender')
            else:
                app_id = app_identity.get_application_id()
                sender = "%s <no-reply@%s.appspotmail.com>" % (app_id, app_id)

        if self.app.config['log_email']:
            try:
                log_email = models.LogEmail(
                    sender=sender,
                    to=to,
                    subject=subject,
                    body=body,
                    when=utils.get_date_time("datetimeProperty")
                )
                log_email.put()
            except (apiproxy_errors.OverQuotaError, BadValueError):
                logging.error("Error saving Email Log in datastore")

        try:
            message = mail.EmailMessage()
            message.sender = sender
            message.to = to
            message.subject = subject
            message.html = body
            message.send()
        except Exception, e:
            logging.error("Error sending email: %s" % e)


class LoginHandler(BaseHandler):
    """
    Handler for authentication
    """

    def get(self):
        """ Returns a simple HTML form for login """

        if self.user:
            self.redirect_to('home')
        params = {}
        return self.render_template('login.html', **params)

    def post(self):
        """
        username: Get the username from POST dict
        password: Get the password from POST dict
        """

        if not self.form.validate():
            return self.get()
        username = self.form.username.data.lower()
        continue_url = self.request.get('continue').encode('ascii', 'ignore')

        try:
            if utils.is_email_valid(username):
                user = self.user_model.get_by_email(username)
                if user:
                    auth_id = user.auth_ids[0]
                else:
                    raise InvalidAuthIdError
            else:
                auth_id = "own:%s" % username
                user = self.user_model.get_by_auth_id(auth_id)

            password = self.form.password.data.strip()
            remember_me = True if str(
                self.request.POST.get('remember_me')) == 'on' else False

            # Password to SHA512
            password = utils.hashing(password, self.app.config.get('salt'))

            # Try to login user with password
            # Raises InvalidAuthIdError if user is not found
            # Raises InvalidPasswordError if provided password
            # doesn't match with specified user
            self.auth.get_user_by_password(
                auth_id, password, remember=remember_me)

            # if user account is not activated, logout and redirect to home
            if (user.activated == False):
                # logout
                self.auth.unset_session()

                # redirect to home with error message
                resend_email_uri = self.uri_for('resend-account-activation',
                                                user_id=user.get_id(),
                                                token=self.user_model.create_resend_token(
                                                    user.get_id()))
                message = _(
                    'Your account has not yet been activated. Please check your email to activate it or') + \
                          ' <a href="' + resend_email_uri + '">' + _(
                    'click here') + '</a> ' + _('to resend the email.')
                self.add_message(message, 'danger')
                return self.redirect_to('home')

            if self.app.config['log_visit']:
                try:
                    log_visit = models.LogVisit(
                        user=user.key,
                        uastring=self.request.user_agent,
                        ip=self.request.remote_addr,
                        timestamp=utils.get_date_time()
                    )
                    log_visit.put()
                except (apiproxy_errors.OverQuotaError, BadValueError):
                    logging.error("Error saving Visit Log in datastore")
            if continue_url:
                self.redirect(continue_url)
            else:
                self.redirect_to('home')
        except (InvalidAuthIdError, InvalidPasswordError), e:
            # Returns error message to self.response.write in
            # the BaseHandler.dispatcher
            message = _("Your username or password is incorrect. "
                        "Please try again (make sure your caps lock is off)")
            self.add_message(message, 'danger')
            self.redirect_to('login',
                             continue_url=continue_url) if continue_url else self.redirect_to(
                'login')

    @webapp2.cached_property
    def form(self):
        return forms.LoginForm(self)


class LogoutHandler(BaseHandler):
    """
    Destroy user session and redirect to login
    """

    def get(self):
        if self.user:
            message = _(
                "You've signed out successfully. Warning: Please clear all cookies and logout "
                "of OpenID providers too if you logged in on a public computer.")
            self.add_message(message, 'info')

        self.auth.unset_session()
        # User is logged out, let's try redirecting to login page
        try:
            self.redirect(self.auth_config['login_url'])
        except (AttributeError, KeyError), e:
            logging.error("Error logging out: %s" % e)
            message = _(
                "User is logged out, but there was an error on the redirection.")
            self.add_message(message, 'danger')
            return self.redirect_to('home')


class RegisterHandler(BaseHandler):
    """
    Handler for Sign Up Users
    """

    def get(self):
        """ Returns a simple HTML form for create a new user """

        if self.user:
            self.redirect_to('home')
        params = {}
        return self.render_template('register.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            return self.get()
        username = self.form.username.data.lower()
        name = self.form.name.data.strip()
        last_name = self.form.last_name.data.strip()
        email = self.form.email.data.lower()
        password = self.form.password.data.strip()
        country = self.form.country.data
        tz = self.form.tz.data

        # Password to SHA512
        password = utils.hashing(password, self.app.config.get('salt'))

        # Passing password_raw=password so password will be hashed
        # Returns a tuple, where first value is BOOL.
        # If True ok, If False no new user is created
        unique_properties = ['username', 'email']
        auth_id = "own:%s" % username
        user = self.auth.store.user_model.create_user(
            auth_id, unique_properties, password_raw=password,
            username=username, name=name, last_name=last_name, email=email,
            ip=self.request.remote_addr, country=country, tz=tz
        )

        if not user[0]:  # user is a tuple
            if "username" in str(user[1]):
                message = _(
                    'Sorry, The username <strong>{}</strong> is already '
                    'registered.').format(username)
            elif "email" in str(user[1]):
                message = _(
                    'Sorry, The email <strong>{}</strong> is already '
                    'registered.').format(email)
            else:
                message = _('Sorry, The user is already registered.')
            self.add_message(message, 'danger')
            return self.redirect_to('register')
        else:
            # User registered successfully
            # But if the user registered using the form, the user has to check
            # their email to activate the account ???
            try:
                if not user[1].activated:
                    # send email
                    subject = _(
                        "%s Account Verification" %
                        self.app.config.get('app_name'))
                    confirmation_url = self.uri_for(
                        "account-activation",
                        user_id=user[1].get_id(),
                        token=self.user_model.create_auth_token(
                            user[1].get_id()),
                        _full=True)

                    # load email's template
                    template_val = {
                        "app_name": self.app.config.get('app_name'),
                        "username": username,
                        "confirmation_url": confirmation_url,
                        "support_url": self.uri_for("contact", _full=True)
                    }
                    body_path = "emails/account_activation.txt"
                    body = self.jinja2.render_template(
                        body_path, **template_val)

                    email_url = self.uri_for('taskqueue-send-email')
                    taskqueue.add(url=email_url, params={
                        'to': str(email),
                        'subject': subject,
                        'body': body,
                    })

                    message = _('You were successfully registered. '
                                'Please check your email to activate your '
                                'account.')
                    self.add_message(message, 'success')
                    return self.redirect_to('home')

                # If the user didn't register using registration form ???
                db_user = self.auth.get_user_by_password(
                    user[1].auth_ids[0], password)

                message = _(
                    'Welcome <strong>{}</strong>, you are now logged '
                    'in.').format(username)
                self.add_message(message, 'success')
                return self.redirect_to('home')
            except (AttributeError, KeyError), e:
                logging.error(
                    'Unexpected error creating the user %s: %s' % (username,
                                                                   e))
                message = _(
                    'Unexpected error creating the user %s' % username)
                self.add_message(message, 'danger')
                return self.redirect_to('home')

    @webapp2.cached_property
    def form(self):
        f = forms.RegisterForm(self)
        f.country.choices = self.countries_tuple
        f.tz.choices = self.tz
        return f


class AccountActivationHandler(BaseHandler):
    """
    Handler for account activation
    """

    def get(self, user_id, token):
        try:
            if not self.user_model.validate_auth_token(user_id, token):
                message = _('The link is invalid.')
                self.add_message(message, 'danger')
                return self.redirect_to('home')

            user = self.user_model.get_by_id(long(user_id))
            # activate the user's account
            user.activated = True
            user.put()

            # Login User
            self.auth.get_user_by_token(int(user_id), token)

            # Delete token
            self.user_model.delete_auth_token(user_id, token)

            message = _(
                'Congratulations, Your account <strong>{}</strong> has been '
                'successfully activated.').format(user.username)
            self.add_message(message, 'success')
            self.redirect_to('home')

        except (AttributeError, KeyError, InvalidAuthIdError, NameError), e:
            logging.error("Error activating an account: %s" % e)
            message = _('Sorry, Some error occurred.')
            self.add_message(message, 'danger')
            return self.redirect_to('home')


class ResendActivationEmailHandler(BaseHandler):
    """
    Handler to resend activation email
    """

    def get(self, user_id, token):
        try:
            if not self.user_model.validate_resend_token(user_id, token):
                message = _('The link is invalid.')
                self.add_message(message, 'danger')
                return self.redirect_to('home')

            user = self.user_model.get_by_id(long(user_id))
            email = user.email

            if (user.activated == False):
                # send email
                subject = _(
                    "%s Account Verification" % self.app.config.get('app_name'))
                confirmation_url = self.uri_for(
                    "account-activation",
                    user_id=user.get_id(),
                    token=self.user_model.create_auth_token(user.get_id()),
                    _full=True)

                # load email's template
                template_val = {
                    "app_name": self.app.config.get('app_name'),
                    "username": user.username,
                    "confirmation_url": confirmation_url,
                    "support_url": self.uri_for("contact", _full=True)
                }
                body_path = "emails/account_activation.txt"
                body = self.jinja2.render_template(body_path, **template_val)

                email_url = self.uri_for('taskqueue-send-email')
                taskqueue.add(url=email_url, params={
                    'to': str(email),
                    'subject': subject,
                    'body': body,
                })

                self.user_model.delete_resend_token(user_id, token)

                message = _(
                    'The verification email has been resent to %s. '
                    'Please check your email to activate your account.' % email)
                self.add_message(message, 'success')
                return self.redirect_to('home')
            else:
                message = _(
                    'Your account has been activated. '
                    'Please <a href="/login/">sign in</a> to your account.')
                self.add_message(message, 'warning')
                return self.redirect_to('home')

        except (KeyError, AttributeError), e:
            logging.error("Error resending activation email: %s" % e)
            message = _('Sorry, Some error occurred.')
            self.add_message(message, 'danger')
            return self.redirect_to('home')


class EditProfileHandler(BaseHandler):
    """
    Handler for Edit User Profile
    """

    @user_required
    def get(self):
        """ Returns a simple HTML form for edit profile """

        params = {}
        if self.user:
            user_info = self.user_model.get_by_id(long(self.user_id))
            self.form.username.data = user_info.username
            self.form.name.data = user_info.name
            self.form.last_name.data = user_info.last_name
            self.form.country.data = user_info.country
            self.form.tz.data = user_info.tz
            providers_info = user_info.get_social_providers_info()
            if not user_info.password:
                params['local_account'] = False
            else:
                params['local_account'] = True
            params['used_providers'] = providers_info['used']
            params['unused_providers'] = providers_info['unused']
            params['country'] = user_info.country
            params['tz'] = user_info.tz

        return self.render_template('edit_profile.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            return self.get()
        username = self.form.username.data.lower()
        name = self.form.name.data.strip()
        last_name = self.form.last_name.data.strip()
        country = self.form.country.data
        tz = self.form.tz.data

        try:
            user_info = self.user_model.get_by_id(long(self.user_id))

            try:
                message = ''
                # update username if it has changed and it isn't already taken
                if username != user_info.username:
                    user_info.unique_properties = ['username', 'email']
                    uniques = [
                        'User.username:%s' % username,
                        'User.auth_id:own:%s' % username,
                    ]
                    # Create the unique username and auth_id.
                    success, existing = Unique.create_multi(uniques)
                    if success:
                        # free old uniqueы
                        Unique.delete_multi(
                            ['User.username:%s' % user_info.username,
                             'User.auth_id:own:%s' % user_info.username])
                        # The unique values were created, so we can save the
                        # user.
                        user_info.username = username
                        user_info.auth_ids[0] = 'own:%s' % username
                        message += _(
                            'Your new username is '
                            '<strong>{}</strong>').format(username)

                    else:
                        message += _(
                            'The username <strong>{}</strong> is already '
                            'taken. Please choose another.').format(username)
                        # At least one of the values is not unique.
                        self.add_message(message, 'danger')
                        return self.get()
                user_info.name = name
                user_info.last_name = last_name
                user_info.country = country
                user_info.tz = tz
                user_info.put()
                message += " " + _('Thanks, your settings have been saved.')
                self.add_message(message, 'success')
                return self.get()

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating profile: ' + e)
                message = _('Unable to update profile. Please try again later.')
                self.add_message(message, 'danger')
                return self.get()

        except (AttributeError, TypeError), e:
            login_error_message = _('Your session has expired.')
            self.add_message(login_error_message, 'danger')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        f = forms.EditProfileForm(self)
        f.country.choices = self.countries_tuple
        f.tz.choices = self.tz
        return f


class EditPasswordHandler(BaseHandler):
    """
    Handler for Edit User Password
    """

    @user_required
    def get(self):
        """ Returns a simple HTML form for editing password """

        params = {}
        return self.render_template('edit_password.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            return self.get()
        current_password = self.form.current_password.data.strip()
        password = self.form.password.data.strip()

        try:
            user_info = self.user_model.get_by_id(long(self.user_id))
            auth_id = "own:%s" % user_info.username

            # Password to SHA512
            current_password = utils.hashing(
                current_password, self.app.config.get('salt'))
            try:
                user = self.user_model.get_by_auth_password(
                    auth_id, current_password)
                # Password to SHA512
                password = utils.hashing(password, self.app.config.get('salt'))
                user.password = security.generate_password_hash(
                    password, length=12)
                user.put()

                # send email
                subject = self.app.config.get(
                    'app_name') + " Account Password Changed"

                # load email's template
                template_val = {
                    "app_name": self.app.config.get('app_name'),
                    "first_name": user.name,
                    "username": user.username,
                    "email": user.email,
                    "reset_password_url": self.uri_for(
                        "password-reset", _full=True)
                }
                email_body_path = "emails/password_changed.txt"
                email_body = self.jinja2.render_template(
                    email_body_path, **template_val)
                email_url = self.uri_for('taskqueue-send-email')
                taskqueue.add(url=email_url, params={
                    'to': user.email,
                    'subject': subject,
                    'body': email_body,
                    'sender': self.app.config.get('contact_sender'),
                })

                # Login User
                self.auth.get_user_by_password(user.auth_ids[0], password)
                self.add_message(_('Password changed successfully.'), 'success')
                return self.redirect_to('edit-profile')
            except (InvalidAuthIdError, InvalidPasswordError), e:
                # Returns error message to self.response.write in
                # the BaseHandler.dispatcher
                message = _(
                    "Incorrect password! Please enter your current password "
                    "to change your account settings.")
                self.add_message(message, 'danger')
                return self.redirect_to('edit-password')
        except (AttributeError, TypeError), e:
            login_error_message = _('Your session has expired.')
            self.add_message(login_error_message, 'danger')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.EditPasswordForm(self)


class EditEmailHandler(BaseHandler):
    """
    Handler for Edit User's Email
    """

    @user_required
    def get(self):
        """ Returns a simple HTML form for edit email """

        params = {}
        if self.user:
            user_info = self.user_model.get_by_id(long(self.user_id))
            params['current_email'] = user_info.email

        return self.render_template('edit_email.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            return self.get()
        new_email = self.form.new_email.data.strip()
        password = self.form.password.data.strip()

        try:
            user_info = self.user_model.get_by_id(long(self.user_id))
            auth_id = "own:%s" % user_info.username
            # Password to SHA512
            password = utils.hashing(password, self.app.config.get('salt'))

            try:
                # authenticate user by its password
                user = self.user_model.get_by_auth_password(auth_id, password)

                # if the user change his/her email address
                if new_email != user.email:

                    # check whether the new email has been used by another user
                    a_user = self.user_model.get_by_email(new_email)
                    if a_user is not None:
                        message = _(
                            "The email %s is already registered." % new_email)
                        self.add_message(message, 'danger')
                        return self.redirect_to("edit-email")

                    # send email
                    subject = _(
                        "%s Email Changed Notification" %
                        self.app.config.get('app_name'))
                    user_token = self.user_model.create_auth_token(self.user_id)
                    confirmation_url = self.uri_for(
                        "email-changed-check",
                        user_id=user_info.get_id(),
                        encoded_email=utils.encode(new_email),
                        token=user_token,
                        _full=True)

                    # load email's template
                    template_val = {
                        "app_name": self.app.config.get('app_name'),
                        "first_name": user.name,
                        "username": user.username,
                        "new_email": new_email,
                        "confirmation_url": confirmation_url,
                        "support_url": self.uri_for("contact", _full=True)
                    }

                    old_body_path = "emails/email_changed_notification_old.txt"
                    old_body = self.jinja2.render_template(
                        old_body_path, **template_val)

                    new_body_path = "emails/email_changed_notification_new.txt"
                    new_body = self.jinja2.render_template(
                        new_body_path, **template_val)

                    email_url = self.uri_for('taskqueue-send-email')
                    taskqueue.add(url=email_url, params={
                        'to': user.email,
                        'subject': subject,
                        'body': old_body,
                    })
                    taskqueue.add(url=email_url, params={
                        'to': new_email,
                        'subject': subject,
                        'body': new_body,
                    })

                    # display successful message
                    msg = _(
                        "Please check your new email for confirmation. Your "
                        "email will be updated after confirmation.")
                    self.add_message(msg, 'success')
                    return self.redirect_to('edit-profile')

                else:
                    self.add_message(
                        _("You didn't change your email."), "warning")
                    return self.redirect_to("edit-email")


            except (InvalidAuthIdError, InvalidPasswordError), e:
                # Returns error message to self.response.write in
                # the BaseHandler.dispatcher
                message = _(
                    "Incorrect password! Please enter your current password to "
                    "change your account settings.")
                self.add_message(message, 'danger')
                return self.redirect_to('edit-email')

        except (AttributeError, TypeError), e:
            login_error_message = _('Your session has expired.')
            self.add_message(login_error_message, 'danger')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.EditEmailForm(self)


class PasswordResetHandler(BaseHandler):
    """
    Password Reset Handler with Captcha
    """

    def get(self):
        chtml = captcha.displayhtml(
            public_key=self.app.config.get('captcha_public_key'),
            use_ssl=(self.request.scheme == 'https'),
            error=None)

        # reCaptcha key placeholder
        recaptcha_kph = 'PUT_YOUR_RECAPTCHA_PUBLIC_KEY_HERE'
        if (self.app.config.get('captcha_public_key') == recaptcha_kph or
                    self.app.config.get(
                            'captcha_private_key') == recaptcha_kph):
            chtml = (
                '<div class="alert alert-danger"><strong>Error</strong>: You '
                'have to '
                '<a href="http://www.google.com/recaptcha/whyrecaptcha" '
                'target="_blank">sign up for API keys</a> in order to use '
                'reCAPTCHA.</div><input type="hidden" '
                'name="recaptcha_challenge_field" value="manual_challenge" />'
                '<input type="hidden" name="recaptcha_response_field" '
                'value="manual_challenge" />')
        params = {
            'captchahtml': chtml,
        }
        return self.render_template('password_reset.html', **params)

    def post(self):
        # check captcha
        challenge = self.request.POST.get('recaptcha_challenge_field')
        response = self.request.POST.get('recaptcha_response_field')
        remote_ip = self.request.remote_addr

        c_response = captcha.submit(
            challenge,
            response,
            self.app.config.get('captcha_private_key'),
            remote_ip)

        if c_response.is_valid:
            # captcha was valid... carry on..nothing to see here
            pass
        else:
            _message = _('Wrong image verification code. Please try again.')
            self.add_message(_message, 'danger')
            return self.redirect_to('password-reset')

        # check if we got an email or username
        email_or_username = str(
            self.request.POST.get('email_or_username')).lower().strip()
        if utils.is_email_valid(email_or_username):
            user = self.user_model.get_by_email(email_or_username)
            _message = (
                _("If the email address you entered") +
                " (<strong>%s</strong>) " % email_or_username)
        else:
            auth_id = "own:%s" % email_or_username
            user = self.user_model.get_by_auth_id(auth_id)
            _message = (
                _("If the username you entered") + " (<strong>%s</strong>) "
                % email_or_username)

        _message += (_(
            "is associated with an account in our records, you will receive an "
            "email from us with instructions for resetting your password. "
            "<br>If you don't receive instructions within a minute or two, "
            "check your email's spam and junk filters, or ") + '<a href="' +
                     self.uri_for('contact') + '">' + _(
            'contact us') + '</a> ' +
                     _("for further assistance."))

        if user is not None:
            user_id = user.get_id()
            token = self.user_model.create_auth_token(user_id)
            email_url = self.uri_for('taskqueue-send-email')
            reset_url = self.uri_for(
                'password-reset-check', user_id=user_id, token=token,
                _full=True)
            subject = _(
                "%s Password Assistance" % self.app.config.get('app_name'))

            # load email's template
            template_val = {
                "username": user.username,
                "email": user.email,
                "reset_password_url": reset_url,
                "support_url": self.uri_for("contact", _full=True),
                "app_name": self.app.config.get('app_name'),
            }

            body_path = "emails/reset_password.txt"
            body = self.jinja2.render_template(body_path, **template_val)
            taskqueue.add(url=email_url, params={
                'to': user.email,
                'subject': subject,
                'body': body,
                'sender': self.app.config.get('contact_sender'),
            })
        self.add_message(_message, 'warning')
        return self.redirect_to('login')


class PasswordResetCompleteHandler(BaseHandler):
    """
    Handler to process the link of reset password that received the user
    """

    def get(self, user_id, token):
        verify = self.user_model.get_by_auth_token(int(user_id), token)
        params = {}
        if verify[0] is None:
            message = _(
                'The URL you tried to use is either incorrect or no longer '
                'valid. Enter your details again below to get a new one.')
            self.add_message(message, 'warning')
            return self.redirect_to('password-reset')

        else:
            return self.render_template(
                'password_reset_complete.html', **params)

    def post(self, user_id, token):
        verify = self.user_model.get_by_auth_token(int(user_id), token)
        user = verify[0]
        password = self.form.password.data.strip()
        if user and self.form.validate():
            # Password to SHA512
            password = utils.hashing(password, self.app.config.get('salt'))

            user.password = security.generate_password_hash(password, length=12)
            user.put()
            # Delete token
            self.user_model.delete_auth_token(int(user_id), token)
            # Login User
            self.auth.get_user_by_password(user.auth_ids[0], password)
            self.add_message(_('Password changed successfully.'), 'success')
            return self.redirect_to('home')

        else:
            self.add_message(_('The two passwords must match.'), 'danger')
            return self.redirect_to(
                'password-reset-check', user_id=user_id, token=token)

    @webapp2.cached_property
    def form(self):
        return forms.PasswordResetCompleteForm(self)


class EmailChangedCompleteHandler(BaseHandler):
    """
    Handler for completed email change
    Will be called when the user click confirmation link from email
    """

    def get(self, user_id, encoded_email, token):
        verify = self.user_model.get_by_auth_token(int(user_id), token)
        email = utils.decode(encoded_email)
        if verify[0] is None:
            message = _(
                'The URL you tried to use is either incorrect or no longer '
                'valid.')
            self.add_message(message, 'warning')
            self.redirect_to('home')

        else:
            # save new email
            user = verify[0]
            user.email = email
            user.put()
            # delete token
            self.user_model.delete_auth_token(int(user_id), token)
            # add successful message and redirect
            message = _('Your email has been successfully updated.')
            self.add_message(message, 'success')
            self.redirect_to('edit-profile')


class HomeRequestHandler(RegisterBaseHandler):
    """
    Handler to show the home page
    """

    def get(self):
        """ Returns a simple HTML form for home """
        params = {}
        return self.render_template('home.html', **params)


class RobotsHandler(BaseHandler):
    def get(self):
        params = {
            'scheme': self.request.scheme,
            'host': self.request.host,
        }
        self.response.headers['Content-Type'] = 'text/plain'

        def set_variables(text, key):
            return text.replace("{{ %s }}" % key, params[key])

        robots_txt = "bp_content/themes/%s/templates/seo/robots.txt"
        self.response.write(reduce(set_variables, params, open(
            robots_txt % self.get_theme).read()))


class HumansHandler(BaseHandler):
    def get(self):
        params = {
            'scheme': self.request.scheme,
            'host': self.request.host,
        }
        self.response.headers['Content-Type'] = 'text/plain'

        def set_variables(text, key):
            return text.replace("{{ %s }}" % key, params[key])

        humans_txt = "bp_content/themes/%s/templates/seo/humans.txt"
        self.response.write(reduce(set_variables, params, open(
            humans_txt % self.get_theme).read()))


class SitemapHandler(BaseHandler):
    def get(self):
        params = {
            'scheme': self.request.scheme,
            'host': self.request.host,
        }
        self.response.headers['Content-Type'] = 'application/xml'

        def set_variables(text, key):
            return text.replace("{{ %s }}" % key, params[key])

        sitemap_xml = "bp_content/themes/%s/templates/seo/sitemap.xml"
        self.response.write(reduce(set_variables, params, open(
            sitemap_xml % self.get_theme).read()))


class CrossDomainHandler(BaseHandler):
    def get(self):
        params = {
            'scheme': self.request.scheme,
            'host': self.request.host,
        }
        self.response.headers['Content-Type'] = 'application/xml'

        def set_variables(text, key):
            return text.replace("{{ %s }}" % key, params[key])

        crossdomain_xml = "bp_content/themes/%s/templates/seo/crossdomain.xml"
        self.response.write(reduce(set_variables, params, open(
            crossdomain_xml % self.get_theme).read()))
