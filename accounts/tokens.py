from django.core import signing

ACTIVATION_MAX_AGE = 60 * 60 * 24


def make_activation_token(user):
    return signing.dumps({'user_id': user.pk, 'email': user.email}, salt='account-activation')


def read_activation_token(token):
    return signing.loads(token, max_age=ACTIVATION_MAX_AGE, salt='account-activation')
