import models

def class_exercises_over_time_graph_context(user_data, student_list):

    if not user_data:
        return {}
 
    if student_list:
        students_data = student_list.get_students_data()
    else:
        students_data = user_data.get_students_data()
  
    dict_student_exercises = {}

    exercises = {}
    def get_display_name(exercise):
        try:
            return exercises[exercise]
        except KeyError:
            ret = exercises[exercise] = models.Exercise.get_by_name(exercise).display_name
            return ret

    user_exercise_cache_list = models.UserExerciseCache.get(students_data)
    for i, user_data_student in enumerate(students_data):
        student_nickname = user_data_student.nickname
        student_exercises = []
        dict_student_exercises[student_nickname] = {
                "nickname": student_nickname,
                "email": user_data_student.email,
                "profile_root": user_data_student.profile_root,
                "exercises": student_exercises,
            }

        for exercise, user_exercise in user_exercise_cache_list[i].dicts.iteritems():
            if user_exercise["proficient_date"]:
                joined = min(user_data_student.joined, user_exercise["proficient_date"])
                data = dict(
                    exid = exercise,
                    nickname = student_nickname,
                    days_until_proficient = (user_exercise["proficient_date"] - joined).days,
                    proficient_date = user_exercise["proficient_date"].strftime('%m/%d/%Y'),
                    display_name = get_display_name(exercise),
                )
                student_exercises.append(data)
   
        student_exercises.sort(key = lambda k : k['days_until_proficient'])

    return {
            "dict_student_exercises": dict_student_exercises,
            "exercises": sorted(map(str, exercises)),
            "user_data_students": students_data,
            "c_points": sum(s.points for s in students_data)
            }


