# -*- coding: utf-8 -*-

import layer_cache
from avatars import AvatarPointsCategory, PointsAvatar

@layer_cache.cache()
def all_avatars():
    """ Authoritative list of all avatars available to users. """

    return [
        PointsAvatar("greenleaf", "עלה ירוק", "/images/avatars/leaf-green.png", 0),
        PointsAvatar("blueleaf", "עלה כחול", "/images/avatars/leaf-blue.png", 0),
        PointsAvatar("greyleaf", "עלה אפור", "/images/avatars/leaf-grey.png", 0),
        PointsAvatar("redleaf", "עלה אדום", "/images/avatars/leaf-red.png", 0),
        PointsAvatar("orangeleaf", "עלה כתום", "/images/avatars/leaf-orange.png", 0),
        PointsAvatar("yellowleaf", "עלה צהוב", "/images/avatars/leaf-yellow.png", 0),

        PointsAvatar("spunkysam", "ספאנקי סאם", "/images/avatars/spunky-sam.png", 10000),
        PointsAvatar("marcimus", "מארקימוס", "/images/avatars/marcimus.png", 10000),
        PointsAvatar("mrpink", "מר פינק", "/images/avatars/mr-pink.png", 10000),

        PointsAvatar("ojsquid", "תפוזון", "/images/avatars/orange-juice-squid.png", 50000),
        PointsAvatar("purplepi", "פאי סגול", "/images/avatars/purple-pi.png", 50000),
        
        PointsAvatar("mrpants", "מכנסון", "/images/avatars/mr-pants.png", 100000),
        PointsAvatar("ospiceman", "חללאיש", "/images/avatars/old-spice-man.png", 100000),
    ]

@layer_cache.cache()
def avatars_by_name():
    """ Full list of avatars in a dict, keyed by their unique names """
    return dict([(avatar.name, avatar) for avatar in all_avatars()])

def avatar_for_name(name=None):
    """ Returns the avatar for the specified name.

    If name is None or an invalid avatar, defaults to the "default" avatar.
    """
    avatars = avatars_by_name()
    if name in avatars:
        return avatars[name]
    
    return all_avatars()[0]

@layer_cache.cache()
def avatars_by_category():
    """ Full list of all avatars available to users segmented by AvatarCategory
    """
    categories = [
        AvatarPointsCategory("ראשוני", 0, 10000),
        AvatarPointsCategory("שכיח", 10000, 50000),
        AvatarPointsCategory("לא שכיח", 50000, 100000),
        AvatarPointsCategory("נדיר", 100000, 250000)
    ]
    full_list = all_avatars()
    for i, category in enumerate(categories):
        categories[i] = {
            'title': category.title,
            'avatars': category.filter_avatars(full_list)
        }
    return categories
