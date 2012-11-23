# coding=utf8

from badges import Badge, BadgeCategory

class FirstFlagBadge(Badge):

    def __init__(self):
        Badge.__init__(self)
        self.description = ""+u"סמן תורן"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

    def extended_description(self):
        return ""+u"סמן לראשונה שאלה, תשובה או תגובה לסרטון המצריכה תשומת-לב של מפקח"

    def is_manually_awarded(self):
        return True

class FirstUpVoteBadge(Badge):

    def __init__(self):
        Badge.__init__(self)
        self.description = ""+u"חיזוק חיובי"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

    def extended_description(self):
        return ""+u"הצביעו לראשונה בעד שאלה, תשובה או תגובה מועילה לסרטון"

    def is_manually_awarded(self):
        return True

class FirstDownVoteBadge(Badge):

    def __init__(self):
        Badge.__init__(self)
        self.description = ""+u"חיזוק שלילי"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

    def extended_description(self):
        return ""+u"הצביעו לראשונה כנגד שאלה, תשובה או תגובה לא מועילה לסרטון"

    def is_manually_awarded(self):
        return True

class ModeratorBadge(Badge):

    def __init__(self):
        Badge.__init__(self)
        self.description = ""+u"מפקח"
        self.badge_category = BadgeCategory.SILVER
        self.points = 0

        # Hidden badge
        self.is_hidden_if_unknown = True

    def extended_description(self):
        return ""+u"הפכו למפקחים על תשובות, שאלות ותגובות לסרטונים"

    def is_manually_awarded(self):
        return True
