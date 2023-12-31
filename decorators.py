import functools
import time
from flask import request, current_app, abort, session
from sqlalchemy.sql import and_

from CTFd.models import Challenges
from CTFd.utils.user import is_admin, get_current_user
from .utils.cache import CacheProvider


def challenge_visible(func):
    @functools.wraps(func)
    def _challenge_visible(*args, **kwargs):
        challenge_id = request.args.get('challenge_id')
        if is_admin():
            Challenges.query.filter(
                Challenges.id == challenge_id
            ).first_or_404('no such challenge')
        else:
            Challenges.query.filter(
                Challenges.id == challenge_id,
                and_(Challenges.state != "hidden", Challenges.state != "locked"),
            ).first_or_404('challenge not visible')
        return func(*args, **kwargs)

    return _challenge_visible


def frequency_limited(func):
    @functools.wraps(func)
    def _frequency_limited(*args, **kwargs):
        if is_admin():
            return func(*args, **kwargs)
        redis_util = CacheProvider(app=current_app, user_id=get_current_user().id)
        if not redis_util.acquire_lock():
            abort(403, '慢点慢点！想累死我啊！')

        if "limit" not in session:
            session["limit"] = int(time.time())
        else:
            if int(time.time()) - session["limit"] < 5:
                abort(403, 'Frequency limit, You should wait at least 5 s.')
        session["limit"] = int(time.time())

        result = func(*args, **kwargs)
        redis_util.release_lock()  # if any exception is raised, lock will not be released
        return result

    return _frequency_limited
