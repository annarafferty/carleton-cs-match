from __future__ import annotations

import csv
import warnings
from priorityDict import PriorityDictionary

# Avoids circular import when importing student. This is a recommended practice
# when doing mutual type hinting.
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from student import Student

# Courses File header constants
CF_COURSE_NAME_HEADER = "Course Name"
CF_COURSE_TYPE_HEADER = "Course Type"
CF_CAPACITY_HEADER = "Capacity"
CF_CORE_COURSE_TYPE = "core"
CF_ELECTIVE_COURSE_TYPE = "elective"
CF_OTHER_COURSE_TYPE = "other"
CF_PREREQUISITES_HEADER = "Prerequisites"
CF_STUDENTS_WITH_PREREQ_WAIVER_HEADER = "Students with Prereq Waiver"

IGNORE_COURSES = ["", "CS.099", "CS.100", "CS.102", "CS.399", "CS.400", "CS.290", "CS.291", "CS.292", "CS.298", "CS.390", "CS.391", "CS.392"]

CORE_EQUIVALENCY = {
    "CS.111" : "CS.111", "CS.111P" : "CS.111", "CS.111AP" : "CS.111",
    "MATH.111" : "MATH.111", "MATH.101" : "MATH.111",
    "CS.201" : "CS.201", "CS.201P" : "CS.201", "CS.201AP" : "CS.201",
    "CS.202" : "CS.202", "CS.202P" : "CS.202", "MATH.236" : "CS.202",
    "CS.208" : "CS.208", "CS.208P" : "CS.208", 
    "CS.251" : "CS.251", "CS.251P" : "CS.251", 
    "CS.252" : "CS.252", "CS.252P" : "CS.252", 
    "CS.254" : "CS.254", "CS.254P" : "CS.254", 
    "CS.257" : "CS.257", "CS.257P" : "CS.257"}

CORE_COURSES = set(CORE_EQUIVALENCY.values())

    
class Course:
    
    def __init__(self, courseName, tiebreaker: PriorityDictionary,
                 prerequisites, studentsWithWaivers, capacity=34):
        self.courseName = courseName
        self.capacity = capacity
        self.tiebreaker = tiebreaker
        self.orPrerequisites = False # For most prerequisites, you need all, not just one
        splitPrerequisites = prerequisites.split(",")
        if len(splitPrerequisites) > 0 and splitPrerequisites[0].strip() == "OR-PREREQS":
            self.orPrerequisites = True
            splitPrerequisites = splitPrerequisites[1:]
        self.prerequisites = [regularize(c) for c in splitPrerequisites]
        self.studentsWithWaivers = studentsWithWaivers.split(",")
        
    def __repr__(self):
        return self.courseName + " " + str(self.capacity)
        
    def getCourseName(self):
        return self.courseName

    def getCapacity(self):
        return self.capacity

    def decrementCapacity(self):
        self.capacity = self.capacity - 1
    def incrementCapacity(self):
        self.capacity = self.capacity + 1

    def cannotTake(self, student):
        '''Returns False if student can take this course, or a
        description of why not if they can't.  Note that prereq waivers (listed 
        in the course data file) will override missing courses and allow a student in.'''
        
        if student.getEmail() in self.studentsWithWaivers:
            return False
        
        errorMessage = ""
        
        if not self.orPrerequisites:
            # Most cases fall here: need all the prerequisites
            missingPrereqs = [c for c in self.prerequisites if c not in student.getCoursesTaken()]
            if len(missingPrereqs) > 0:
                errorMessage += "missing prerequisites: " + " ".join(missingPrereqs)
        else:
            # Occasionally, a course requires that you have at least one of several prerequisite options
            prereqsTaken = [c for c in self.prerequisites if c in student.getCoursesTaken()]
            if len(self.prerequisites) > 0 and len(prereqsTaken) == 0:
                errorMessage += "missing any prerequisites for or-d prereq course: " + self.getCourseName() + " " + " ".join(student.getCoursesTaken())
         
        alreadyTaken = self.courseName in student.getRawCoursesTaken()
        if alreadyTaken:
            errorMessage += "course was already taken"
        if len(errorMessage) > 0:
            return errorMessage
        return False

    def preferred(self, studentA, studentB):
        '''
        Return the student that this course prefers.
        '''
        return max(studentA, studentB, key = self.priority)
    
    def priority(self, _: Student):
        '''
        Returns a 'score' tuple reporting how happy this course is with the
        given student, so that course.priority(A) > course.priority(B) if 
        and only if this course prefers student A to student B.
             *** MUST BE IMPLEMENTED BY SUBCLASSES. ***
        '''
        raise ValueError("No priority for a generic Course!")
    

class ElectiveCourse(Course):
    def priority(self, student: Student):
        '''Returns a 'score' tuple reporting how happy this course is with the
           given student, so that course.priority(A) > course.priority(B) if 
           and only if this course prefers student A to student B.

        From match.pdf:
           Courses in The Match not specifically required for the CS major 
           (electives) ... prefer students by descending seniority.
           Among students in the same graduating class, an elective prefers 
           students who have satisfied more of the required CS major courses,
           breaking ties by preferring students who have taken fewer CS 
           electives. Any remaining ties are broken randomly.
        '''
        return (+1 * student.getRegistrationClassYear(),              # big is good, now using enum
                +1 * len(student.getCoreCoursesTaken()),              # big is good
                -1 * len(student.getElectivesTaken()),                # small is good
                +1 * self.tiebreaker.getPriority(student.getEmail())) # big is good
    
        
class CoreCourse(Course):
    def priority(self, student: Student):
        '''Returns a 'score' tuple reporting how happy this course is with the
           given student, so that course.priority(A) > course.priority(B) if 
           and only if this course prefers student A to student B.

        From match.pdf:
           Courses in The Match required for the CS major (202, 208, 251, 252,
           254, 257) prefer students by descending seniority (seniors over
           juniors over sophomores over first years), breaking ties randomly.
        '''
        return (+1 * student.getRegistrationClassYear(),              # big is good, now using enum
                +1 * self.tiebreaker.getPriority(student.getEmail())) # big is good

    
def regularize(s, substituteEquivalent=True):
    '''
    Convert all strings that represent courses in form like
    CS.201 or CS201 or CS 201 or Math/MATH + space/dot + 236 + P etc and converts to
    consistent format.
    '''
    if "or" in s:
        # Keep only the first option if multiple equivalent courses are listed
        s = s[0:s.index("or")]
    s = s.strip().replace(".","").replace(" ","")
    courseNumber = "".join([c for c in s if c.isdigit()])
    courseDepartment = s[:s.find(courseNumber)]
    courseSuffix = s[s.find(courseNumber) + len(courseNumber):]
    dottedName = courseDepartment.upper() + "." + courseNumber + courseSuffix
    if substituteEquivalent and dottedName in CORE_EQUIVALENCY:
        dottedName = CORE_EQUIVALENCY[dottedName]
    return dottedName
    
    
def loadCourses(coursesFileName,tiebreaker):
    '''
    Reads in a csv of courses and returns a dictionary of courseName:Course mappings.
    Courses format, by header:
        CF_COURSE_NAME_HEADER : course name in CS.### format,
        CF_COURSE_TYPE_HEADER: capacity, 
        CF_CAPACITY_HEADER: course type [allowed values: core, elective, other])
        CF_PREREQUISITES_HEADER: comma-separated list of prerequisites in DEPT.### format
        CF_STUDENTS_WITH_PREREQ_WAIVER_HEADER: comma-separated list of emails of students allowed to take course via waiver
    '''
    courseNamesToCourses = {}
    with open(coursesFileName, encoding="utf-8") as coursesFile:
        coursesReader = csv.DictReader(coursesFile)
        for line in coursesReader:
            courseName = line[CF_COURSE_NAME_HEADER]
            courseClassHandle = None
            if line[CF_COURSE_TYPE_HEADER] == CF_CORE_COURSE_TYPE:
                courseClassHandle = CoreCourse
            elif line[CF_COURSE_TYPE_HEADER] == CF_ELECTIVE_COURSE_TYPE:
                courseClassHandle = ElectiveCourse
            else:
                warnings.warn("Course type for " + courseName + " is " + line[CF_COURSE_TYPE_HEADER] +  " - defaulting to elective.")
                courseClassHandle = ElectiveCourse
            courseNamesToCourses[courseName] = courseClassHandle(courseName, tiebreaker,
                                                                 line[CF_PREREQUISITES_HEADER],
                                                                 line[CF_STUDENTS_WITH_PREREQ_WAIVER_HEADER],
                                                                 capacity=int(line[CF_CAPACITY_HEADER]))
    return courseNamesToCourses

def isElective(regularizedCourseName):
    return not isCore(regularizedCourseName) and not isIgnoredCourse(regularizedCourseName)
    
def isCore(regularizedCourseName):
    return regularizedCourseName in CORE_EQUIVALENCY

def isIgnoredCourse(regularizedCourseName):
    return regularizedCourseName in IGNORE_COURSES
