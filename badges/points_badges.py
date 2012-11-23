# coding=utf8

import util
from badges import Badge, BadgeCategory

# All badges awarded for getting a certain number of points inherit from PointBadge
class PointBadge(Badge):

    def is_satisfied_by(self, *args, **kwargs):
        user_data = kwargs.get("user_data", None)
        if user_data is None:
            return False

        return user_data.points >= self.required_points

    def extended_description(self):
        return u"צבור %s נקודות אנרגיה" % util.thousands_separated_number(self.required_points)

class TenThousandaireBadge(PointBadge):
    def __init__(self):
        PointBadge.__init__(self)
        self.required_points = 10000
        self.description = ""+u"עשר ברביעית"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

class HundredThousandaireBadge(PointBadge):
    def __init__(self):
        PointBadge.__init__(self)
        self.required_points = 100000
        self.description = ""+u"עשר בחמישית"
        self.badge_category = BadgeCategory.SILVER
        self.points = 0

class FiveHundredThousandaireBadge(PointBadge):
    def __init__(self):
        PointBadge.__init__(self)
        self.required_points = 500000
        self.description = ""+u"חמש פעמים עשר בחמישית"
        self.badge_category = BadgeCategory.GOLD
        self.points = 0

class MillionaireBadge(PointBadge):
    def __init__(self):
        PointBadge.__init__(self)
        self.required_points = 1000000
        self.description = ""+u"מיליונר"
        self.badge_category = BadgeCategory.PLATINUM
        self.points = 0

class TenMillionaireBadge(PointBadge):
    def __init__(self):
        PointBadge.__init__(self)
        self.required_points = 10000000
        self.description = ""+u"טסלה"
        self.badge_category = BadgeCategory.DIAMOND
        self.points = 0
        self.is_teaser_if_unknown = True
