from django.contrib.auth import get_user_model


def get_username(strategy, details, user=None, *args, **kwargs):
    """
    This pipeline function customizes the behavior of python-social-auth to return the username 
    based on the project's custom user model.

    Parameters:
    - strategy: The strategy used by python-social-auth.
    - details: A dictionary containing user details retrieved from the authentication provider.
    - user: An optional User object. If provided, the function returns the username of this user.
    - *args: Additional positional arguments required by python-social-auth.
    - **kwargs: Additional keyword arguments required by python-social-auth.

    Returns:
    - dict: A dictionary containing the username. If a user is provided, it returns {'username': user.username}. 
    """
    if user:
        provider_username = details.get("username")
        if provider_username and provider_username != user.username:
            user_model = get_user_model()
            username_taken = user_model.all_objects.exclude(pk=user.pk).filter(username=provider_username).exists()
            if not username_taken:
                user.username = provider_username
                user.save(update_fields=["username"])
        return {"user": user, "username": user.username}

    username = details.get("username")
    if not username:
        return None

    user_model = get_user_model()
    existing_user = user_model.all_objects.filter(username=username).first()
    if existing_user:
        return {"user": existing_user, "username": existing_user.username}

    return {"username": username}
