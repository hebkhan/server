# coding=utf8

from badges import BadgeCategory
from exercise_badges import ExerciseBadge

# All badges awarded for completing a streak of certain length inherit from StreakBadge
class StreakBadge(ExerciseBadge):

    def is_satisfied_by(self, *args, **kwargs):
        user_exercise = kwargs.get("user_exercise", None)
        if user_exercise is None:
            return False

        # Don't give streak rewards for summative exercises currently
        if user_exercise.summative:
            return False

        return user_exercise.longest_streak >= self.streak_required

    def extended_description(self):
        return u"ענו נכון על %s שאלות ברצף בתרגיל אחד" % str(self.streak_required)

class NiceStreakBadge(StreakBadge):

    def __init__(self):
        StreakBadge.__init__(self)
        self.streak_required = 20
        self.description = ""+u"רצף יפה"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

class GreatStreakBadge(StreakBadge):
    def __init__(self):
        StreakBadge.__init__(self)
        self.streak_required = 40
        self.description = ""+u"רצף יפהפה"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

class AwesomeStreakBadge(StreakBadge):
    def __init__(self):
        StreakBadge.__init__(self)
        self.streak_required = 60
        self.description = ""+u"רצף מדהים"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 0

class RidiculousStreakBadge(StreakBadge):
    def __init__(self):
        StreakBadge.__init__(self)
        self.streak_required = 80
        self.description = ""+u"רצף מגוחך"
        self.badge_category = BadgeCategory.SILVER
        self.points = 0

class LudicrousStreakBadge(StreakBadge):
    def __init__(self):
        StreakBadge.__init__(self)
        self.streak_required = 100
        self.description = ""+u"רצף מטריף"
        self.badge_category = BadgeCategory.SILVER
        self.points = 0
