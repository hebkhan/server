# coding=utf8

from badges import Badge, BadgeCategory

# All badges awarded for consecutively performing activity on the site inherit from ConsecutiveActivityBadge
class ConsecutiveActivityBadge(Badge):

    def is_satisfied_by(self, *args, **kwargs):
        user_data = kwargs.get("user_data", None)
        if user_data is None:
            return False

        return user_data.current_consecutive_activity_days() >= self.days_required

    def extended_description(self):
        return u"צפו בחלק מסרטון כלשהוא או עבדו על תרגיל כלשהוא כל יום במשך %s ימים רצופים" % self.days_required

class FiveDayConsecutiveActivityBadge(ConsecutiveActivityBadge):
    def __init__(self):
        ConsecutiveActivityBadge.__init__(self)
        self.days_required = 5
        self.description = ""+u"הרגלים טובים"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

class FifteenDayConsecutiveActivityBadge(ConsecutiveActivityBadge):
    def __init__(self):
        ConsecutiveActivityBadge.__init__(self)
        self.days_required = 15
        self.description = ""+u"כמו שעון"
        self.badge_category = BadgeCategory.SILVER
        self.points = 0

class ThirtyDayConsecutiveActivityBadge(ConsecutiveActivityBadge):
    def __init__(self):
        ConsecutiveActivityBadge.__init__(self)
        self.days_required = 30
        self.description = ""+u"כמו שעון אטומי"
        self.badge_category = BadgeCategory.SILVER
        self.points = 0

class HundredDayConsecutiveActivityBadge(ConsecutiveActivityBadge):
    def __init__(self):
        ConsecutiveActivityBadge.__init__(self)
        self.days_required = 100
        self.description = ""+u"כמו שעון עשרת אלפים השנים"
        self.badge_category = BadgeCategory.GOLD
        self.points = 0

