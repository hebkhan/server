# coding=utf8

from badges import Badge, BadgeCategory, BadgeContextType
from discussion.models_discussion import FeedbackType

# All badges that may be awarded once-per-Feedback inherit from FeedbackBadge
class FeedbackBadge(Badge):

    def __init__(self):
        Badge.__init__(self)
        self.badge_context_type = BadgeContextType.FEEDBACK

    def is_manually_awarded(self):
        return True

    def hide_context(self):
        return True

    def is_already_owned_by(self, user_data, *args, **kwargs):
        feedback = kwargs.get("feedback", None)
        if feedback is None:
            return False

        return self.name_with_target_context(str(feedback.key().id_or_name())) in user_data.badges

    def award_to(self, user_data, *args, **kwargs):
        feedback = kwargs.get("feedback", None)
        if feedback is None:
            return False

        self.complete_award_to(user_data, feedback, str(feedback.key().id_or_name()))

class FeedbackVoteCountBadge(FeedbackBadge):

    def is_satisfied_by(self, *args, **kwargs):
        feedback = kwargs.get("feedback", None)
        if feedback is None:
            return False

        if not feedback.is_type(self.required_feedback_type()):
            return False

        # sum_votes starts at 0, but users see additional +1 vote (creator's implicit vote)
        return feedback.sum_votes + 1 >= self.required_votes

class AnswerVoteCountBadge(FeedbackVoteCountBadge):

    def required_feedback_type(self):
        return FeedbackType.Answer

    def extended_description(self):
        return u"ענו על שאלה לגבי לסרטון וקבלו ניקוד של %s או יותר מקולותיהם של אחרים" % self.required_votes

class QuestionVoteCountBadge(FeedbackVoteCountBadge):

    def required_feedback_type(self):
        return FeedbackType.Question

    def extended_description(self):
        return u"שאלו שאלה על לסרטון וקבלו ניקוד של %s או יותר מקולותיהם של אחרים" % self.required_votes

class LevelOneAnswerVoteCountBadge(AnswerVoteCountBadge):
    def __init__(self):
        AnswerVoteCountBadge.__init__(self)
        self.required_votes = 10
        self.description = ""+u"תשובה טובה"
        self.badge_category = BadgeCategory.SILVER
        self.points = 0

class LevelTwoAnswerVoteCountBadge(AnswerVoteCountBadge):
    def __init__(self):
        AnswerVoteCountBadge.__init__(self)
        self.required_votes = 25
        self.description = ""+u"תשובה מצוינת"
        self.badge_category = BadgeCategory.GOLD
        self.points = 0

class LevelThreeAnswerVoteCountBadge(AnswerVoteCountBadge):
    def __init__(self):
        AnswerVoteCountBadge.__init__(self)
        self.required_votes = 50
        self.description = ""+u"תשובה מדהימה"
        self.badge_category = BadgeCategory.GOLD
        self.points = 0

class LevelOneQuestionVoteCountBadge(QuestionVoteCountBadge):
    def __init__(self):
        QuestionVoteCountBadge.__init__(self)
        self.required_votes = 10
        self.description = ""+u"שאלה טובה"
        self.badge_category = BadgeCategory.SILVER
        self.points = 0

class LevelTwoQuestionVoteCountBadge(QuestionVoteCountBadge):
    def __init__(self):
        QuestionVoteCountBadge.__init__(self)
        self.required_votes = 25
        self.description = ""+u"שאלה מצוינת"
        self.badge_category = BadgeCategory.GOLD
        self.points = 0

class LevelThreeQuestionVoteCountBadge(QuestionVoteCountBadge):
    def __init__(self):
        QuestionVoteCountBadge.__init__(self)
        self.required_votes = 50
        self.description = ""+u"שאלה מדהימה"
        self.badge_category = BadgeCategory.GOLD
        self.points = 0


