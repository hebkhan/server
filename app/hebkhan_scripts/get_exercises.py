import urllib2
import json
import sys


EXERCISES_URL = "http://www.khanacademy.org/api/v1/exercises"

def get_exercises(url):
    f = urllib2.urlopen(url)
    data = json.load(f)
    sys.stdout.write(json.dumps(data, indent=4))


if __name__ == '__main__':
    get_exercises(EXERCISES_URL)

