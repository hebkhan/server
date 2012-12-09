# coding=utf8

from badges import Badge, BadgeCategory

# All badges awarded for completing some specific count of exercises inherit from ExerciseCompletionCountBadge
class ExerciseCompletionCountBadge(Badge):

    def is_satisfied_by(self, *args, **kwargs):
        user_data = kwargs.get("user_data", None)
        if user_data is None:
            return False

        return len(user_data.all_proficient_exercises) >= self.required_exercises

    def extended_description(self):
        return u"השיגו מיומנות ב-%d תרגילים כלשהם" % self.required_exercises

class GettingStartedBadge(ExerciseCompletionCountBadge):
    def __init__(self):
        ExerciseCompletionCountBadge.__init__(self)
        self.required_exercises = 3
        self.description = ""+u"רק מתחיל"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 100

class MakingProgressBadge(ExerciseCompletionCountBadge):
    def __init__(self):
        ExerciseCompletionCountBadge.__init__(self)
        self.required_exercises = 7
        self.description = ""+u"מתקדם"
        self.badge_category = BadgeCategory.BRONZE
        self.points = 1000

class ProductiveBadge(ExerciseCompletionCountBadge):
    def __init__(self):
        ExerciseCompletionCountBadge.__init__(self)
        self.required_exercises = 15
        self.description = ""+u"יצרני"
        self.badge_category = BadgeCategory.SILVER
        self.points = 2000

class HardAtWorkBadge(ExerciseCompletionCountBadge):
    def __init__(self):
        ExerciseCompletionCountBadge.__init__(self)
        self.required_exercises = 25
        self.description = ""+u"עובד קשה"
        self.badge_category = BadgeCategory.SILVER
        self.points = 6000

class WorkHorseBadge(ExerciseCompletionCountBadge):
    def __init__(self):
        ExerciseCompletionCountBadge.__init__(self)
        self.required_exercises = 50
        self.description = ""+u"סוס עבודה"
        self.badge_category = BadgeCategory.GOLD
        self.points = 14000

class MagellanBadge(ExerciseCompletionCountBadge):
    def __init__(self):
        ExerciseCompletionCountBadge.__init__(self)
        self.required_exercises = 100
        self.description = ""+u"מגלן"
        self.badge_category = BadgeCategory.PLATINUM
        self.points = 30000

class CopernicusBadge(ExerciseCompletionCountBadge):
    def __init__(self):
        ExerciseCompletionCountBadge.__init__(self)
        self.required_exercises = 200
        self.description = ""+u"קופרניקוס"
        self.badge_category = BadgeCategory.PLATINUM
        self.points = 80000

class KeplerBadge(ExerciseCompletionCountBadge):
    def __init__(self):
        ExerciseCompletionCountBadge.__init__(self)
        self.required_exercises = 300
        self.description = ""+u"קפלר"
        self.badge_category = BadgeCategory.PLATINUM
        self.points = 125000

class AtlasBadge(ExerciseCompletionCountBadge):
    def __init__(self):
        ExerciseCompletionCountBadge.__init__(self)
        self.required_exercises = 500
        self.description = ""+u"אטלס"
        self.badge_category = BadgeCategory.DIAMOND
        self.points = 200000
        self.is_teaser_if_unknown = True
