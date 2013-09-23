# coding=utf8
from __future__ import absolute_import
import os
import logging
import bisect
import layer_cache

from google.appengine.ext import db

from models import Exercise, Video

COMMON_CORE_DOMAINS = {
        "A-APR": "Arithmetic with Polynomials and Rational Expressions",
        "A-CED": "Creating Equations*",
        "A-REI": "Reasoning with Equations and Inequalities",
        "A-SSE": "Seeing Structure in Expressions",
        "CC": "Counting and Cardinality",
        "EE": "Expressions and Equations",
        "F": "Functions",
        "F-BF": "Building Functions",
        "F-IF": "Interpreting Functions",
        "F-LE": "Linear, Quadratic, and Exponential Models",
        "F-TF": "Trigonometric Functions",
        "G": "Geometry",
        "G-C": "Circles",
        "G-CO": "Congruence",
        "G-GMD": "Geometric Measurement and Dimension",
        "G-GPE": "Expressing Geometric Properties with Equations",
        "G-MG": "Modeling with Geometry",
        "G-SRT": "Similarity, Right Triangles, and Trigonometry",
        "MD": "Measurement and Data",
        "MP": "Standards for Mathematical Practice",
        "N-CN": "The Complex Number System",
        "N-Q": "Quantities",
        "N-RN": "The Real Number System",
        "N-VM": "Vector and Matrix Quantities",
        "NBT": "Number and Operations in Base Ten",
        "NF": "Number and Operations--Fractions",
        "NS": "The Number System",
        "OA": "Operations and Algebraic Thinking",
        "RP": "Ratios and Proportional Relationships",
        "S": "Using Probability to Make Decisions",
        "S-CP": "Conditional Probability & the Rules of Probability",
        "S-IC": "Making Inferences and Justifying Conclusions",
        "S-ID": "Interpreting Categorical and Quantitative Data",
        "S-MD": "Using Probability to Make Decisions",
        "SP": "Statistics and Probability"
    }

class CommonCoreMap(db.Model):
    standard = db.StringProperty()
    grade = db.StringProperty()
    domain = db.StringProperty(indexed=False)
    domain_code = db.StringProperty()
    level = db.StringProperty(indexed=False)
    cc_description = db.TextProperty(indexed=False)
    cc_cluster = db.StringProperty(indexed=False)
    exercises = db.ListProperty(db.Key, indexed=False)
    videos = db.ListProperty(db.Key, indexed=False)

    def get_entry(self, lightweight=False):
        entry = {}
        entry['standard'] = self.standard
        entry['grade'] = self.grade
        entry['domain'] = self.domain
        entry['domain_code'] = self.domain_code
        entry['level'] = self.level
        entry['cc_description'] = self.cc_description
        entry['cc_cluster'] = self.cc_cluster
        entry['exercises'] = []
        entry['videos'] = []
        for key in self.exercises:
            if lightweight:
                ex = db.get(key)
                entry['exercises'].append({ "display_name": ex.display_name, "ka_url": ex.ka_url })
            else:
                entry['exercises'].append(db.get(key))
        for key in self.videos:
            if lightweight:
                v = db.get(key)
                entry['videos'].append({ "title": v.title, "ka_url": v.ka_url })
            else:
                entry['videos'].append(db.get(key))

        return entry

    @staticmethod
    def get_all(lightweight=False, structured=False):
        if structured:
            return CommonCoreMap.get_all_structured(lightweight)

        query = CommonCoreMap.all()
        all_entries = []
        for e in query:
            all_entries.append(e.get_entry(lightweight=lightweight))
        return all_entries

    @staticmethod
    @layer_cache.cache_with_key_fxn(key_fxn=lambda lightweight: "structured_cc:%s" % lightweight, layer=layer_cache.Layers.Blobstore)
    def get_all_structured(lightweight=False):
        all_grades = {}
        domains_dict = {}
        standards_dict = {}
        exercise_cache = {}
        video_cache = {}

        query = CommonCoreMap.all()
        for e in query:
            grade = all_grades.setdefault(e.grade, dict(grade=e.grade, domains=[]))
            dkey = e.grade + '.' + e.domain_code
            if dkey not in domains_dict:
                domain = {}
                domain['domain_code'] = e.domain_code
                domain['domain'] = e.domain
                domain['standards'] = []
                grade['domains'].append(domain)
                domains_dict[dkey] = domain
            else:
                domain = domains_dict[dkey]

            if e.standard not in standards_dict:
                standard = {}
                standard['standard'] = e.standard
                standard['cc_description'] = e.cc_description
                standard['cc_cluster'] = e.cc_cluster
                standard['exercises'] = []
                standard['videos'] = []
                domain['standards'].append(standard)
                standards_dict[e.standard] = standard
            else:
                standard = standards_dict[e.standard]

            for key in e.exercises:
                if key not in exercise_cache:
                    ex = db.get(key)
                    exercise_cache[key] = ex
                else:
                    ex = exercise_cache[key]

                if lightweight:
                    standard['exercises'].append({
                        'display_name': ex.display_name,
                        'ka_url': ex.ka_url
                    })
                else:
                    standard['exercises'].append(ex)

            for key in e.videos:
                if key not in video_cache:
                    v = db.get(key)
                    video_cache[key] = v
                else:
                    v = video_cache[key]

                if lightweight:
                    standard['videos'].append({
                        'title': v.title,
                        'ka_url': v.ka_url
                    })
                else:
                    standard['videos'].append(v)

        all_entries = []
        grades = zip('K 1 2 3 4 5 6 7 8 9 801 802 803 804 805 806 807'.split(),
                     u"גן א' ב' ג' ד' ה' ו' ז' ח' ט' שאלון-801 שאלון-802 שאלון-803 שאלון-804 שאלון-805 שאלון-806 שאלון-807".split())
        for x, name in grades:
            if not x in all_grades:
                continue
            entry = all_grades[x]
            entry['grade_name'] = name
            entry['domains'].sort(key=lambda k: k['domain'])
            for domain in entry['domains']:
                domain['standards'].sort(key=lambda k: k['standard'])
            all_entries.append(entry)

        return all_entries

    def update_exercise(self, exercise_name):
        ex = Exercise.all().filter('name =', exercise_name).get()
        if ex is not None:
            if ex.key() not in self.exercises:
                self.exercises.append(ex.key())
        else:
            logging.info("Exercise %s not in datastore" % exercise_name)

        return

    def update_video(self, video_youtube_id):
        v = Video.all().filter('youtube_id =', video_youtube_id).get()
        if v is not None:
            if v.key() not in self.videos:
                self.videos.append(v.key())
        else:
            logging.info("Youtube ID %s not in datastore" % video_youtube_id)

        return
