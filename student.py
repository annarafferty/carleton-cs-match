import warnings
import csv
import course
import re
from enum import IntEnum
from typing import Optional

# Registrar Data header constants
ID_HEADER = "ID"
NAME_HEADER = "Carleton Name"
EMAIL_HEADER = "Carleton Email"
#This header seems to change across terms - we are robust to multiple versions
CLASS_YEAR_HEADERS = ["Class Year","Class Yr"]
CLASS_LEVEL_HEADER = "Class Level"
ENROLLMENT_STATUS_HEADER = "Enrollment Status Confidential"
COURSE_NAME_HEADER = "Course Name"
STATUS_CODE_HEADER = "Current Status Code"

IGNORE_CODES = ["W","D","X"] # Registar code for dropped courses (w/ or w/o transcript annotation or withdrawal)


# Preference Data header constants
PR_ID_HEADER = "What is your student ID number?"
PR_NAME_HEADER = "What is your full name?"
PR_EMAIL_HEADER = "Email Address"
PR_CORE_TAKEN_HEADER = "Please indicate which of the following courses you have taken, are currently taking, or have placed out of (due to prior study and/or OCS, including if that OCS credit is not yet reflected on your transcript)."
PR_CORE_TAKEN_HEADER_ALT = "Please indicate which of the following courses you have taken or have placed out of (due to prior study and/or OCS, including if that OCS credit is not yet reflected on your transcript)." ####Summer 2020
PR_CORE_TAKEN_PREFIX = "Please indicate which of the following courses you have taken" # Because I keep adjusting the wording to try to make it clearer
PR_CLASS_YEAR_HEADER = "What is your class year? (This should be your graduation year as reflected in the directory.)"

NO_COURSE_CHOICE = "[No CS course - I\'d rather not be matched to anything than a course I rank below this. (Remember that #1 is your most preferred course, so \"below\" means \"a bigger number\".)]"


class ClassYear(IntEnum):
    FROSH = 0
    SOPHOMORE = 1
    JUNIOR = 2
    SENIOR = 3

    def __str__(self):
        return self.name

class Student:

    @classmethod
    def setGeneralCalendarInfo(cls, seniorClassYear: int,
                               upcomingTerm: str) -> None:
        cls.seniorClassYear = seniorClassYear
        cls.upcomingTerm = upcomingTerm

    def __init__(self, idNumber, emailAddress, name, classYear: str,
                 classLevel:Optional[str] = None, enrollmentStatus=None):
        '''For students who are missing from registration data, we won't have
        class level or enrollment status. Senior year and upcoming term is
        needed for those students.
        '''

        self.idNumber = idNumber
        self.emailAddress = emailAddress
        self.name = name # name from registrar's data
        self.classYear = getNumericYearFromText(classYear)
        self.classLevel = classLevel
        self.enrollmentStatus = enrollmentStatus
        self.registrationYear = self.getRegistrationClassYearFromLevelAndStatus()

        self.focus = False
        self.coursesTaken = set()
        self.rawCoursesTaken = set()
        self.coursesDesiredDescendingPreferences = []
        self.hasPreferences = False
        
    def addCourse(self, courseName, warningsLevel=1):
        
        regCourseName = course.regularize(courseName)
        if regCourseName in self.coursesTaken and warningsLevel == 1:
            warnings.warn(regCourseName + " appears twice for " + self.emailAddress)
            
        self.coursesTaken.add(regCourseName)
        self.rawCoursesTaken.add(course.regularize(courseName, substituteEquivalent=False))
            
    def addPreferenceInformation(self, line, courseNameToHeader, courseDictionary):
        '''
        Adds preferences information from the Google Form to this Student. All
        courses that the student ranked will be added to their preferences. A
        warning will be issue about courses in preferences that are (a) already 
        taken or (b) where student doesn't have the prerequisites, unless these
        courses appear after all ranked courses that the student has taken and
        does have the prerequisites for.
        
        line - dictionary representing this student's preference information
        courseNameToHeader - dictionary mapping from course names to the key
            in the line dictionary representing the preference for that course
        courseDictionary - dictionary mapping from course names to Course objects
        '''
        preferences = readCoursePreferencesWithNone(line, courseNameToHeader)#readCoursePreferences(line, courseNameToHeader)
        self.hasPreferences = True
        self.coursesDesiredDescendingPreferences = []

        coursesSkipped = False
        firstCannotTakeErrorMessage = None
        for courseName in preferences:
            if not courseDictionary[courseName].cannotTake(self) and coursesSkipped:
                warnings.warn(self.emailAddress + " has some ineligible courses " + \
                        "with higher priority than eligible courses " + \
                        "(adding anyway); wishlist: " + str(preferences))
                warnings.warn(self.emailAddress + " error message " + str(firstCannotTakeErrorMessage))
            elif courseDictionary[courseName].cannotTake(self):
                # Course they've already taken or are missing prereq for - if we only have those at the end, okay
                coursesSkipped = True
                firstCannotTakeErrorMessage = courseName + " "  + courseDictionary[courseName].cannotTake(self)
            self.coursesDesiredDescendingPreferences.append(courseName)
            
        # do they have no (remaining) preferences?
        if len(self.coursesDesiredDescendingPreferences) == 0:
            warnings.warn(self.emailAddress + " has no preferences.")
    
    def addSelfReportedCoursesTaken(self, reportedCoursesTaken, warningsLevel=1):
        '''
        Merge courses from Google form, listed in reportedCourseTaken, into 
        courses reported by registrar's office. Final coursesTaken for this
        student is the union of both data sources.
        '''
        reportedCoursesTaken = set([course.regularize(courseName) 
                                for courseName in reportedCoursesTaken])
        registrarCoreTaken = set([courseName 
                                  for courseName in self.coursesTaken 
                                  if course.isCore(courseName)])
        extraReported = reportedCoursesTaken.difference(registrarCoreTaken)
        extraRegistrar = registrarCoreTaken.difference(reportedCoursesTaken)
        
        if len(extraReported) != 0 and warningsLevel == 1:
            warnings.warn(self.emailAddress + " reported courses not " + \
                    " in registrar data: " + str(extraReported))
            #warnings.warn("self: " + str(reportedCoursesTaken) + \
            #        " and reg: " + str(registrarCoreTaken))
        
        if len(extraRegistrar) != 0 and warningsLevel == 1:
            warnings.warn(self.emailAddress + " did not report courses in " + \
                            " registrar data: " + str(extraRegistrar))
            #warnings.warn("self: " + str(reportedCoursesTaken) + \
            #        " and reg: " + str(registrarCoreTaken))
        
        self.coursesTaken = self.coursesTaken.union(reportedCoursesTaken)
    
    def removePreference(self, courseName):
        '''
        Removes the regularized version of the course from this student's
        preference list.
        '''
        regCourseName = course.regularize(courseName)
        if regCourseName in self.coursesDesiredDescendingPreferences:
            self.coursesDesiredDescendingPreferences.remove(regCourseName)
        
    def submittedPreferences(self):
        '''
        Returns True if the student submitted a preference form.
        '''
        return self.hasPreferences

    def markIneligibleForMatch(self):
        '''
        Declare this student as ineligible for normal matching.
        '''
        self.hasPreferences = False
        
    def markEligibleForMatch(self):
        '''
        Declare this student as eligible for normal matching.
        '''
        self.hasPreferences = True
        
    def getName(self):
        return self.name
    
    def getEmail(self):
        return self.emailAddress

    def getID(self):
        '''
        Returns the id as a string.
        '''
        return self.idNumber
    
    def getCoursesTaken(self):
        return sorted(self.coursesTaken)

    def getRawCoursesTaken(self):
        return sorted(self.rawCoursesTaken)
        
    def getCoreCoursesTaken(self):
        return sorted([c for c in self.getCoursesTaken()
                                if course.isCore(c)])
                                

    def getElectivesTaken(self):
        return sorted([c for c in self.getCoursesTaken()
                                if course.isElective(c)])
        
    def preferred(self, course1, course2):
        '''
        Returns whichever of course1 or course2 is more preferred,
        or None if neither is desired by this student..
        '''
        courseName1 = course1.getCourseName()
        courseName2 = course2.getCourseName()
        if courseName1 in self.coursesDesiredDescendingPreferences and \
         courseName2 in self.coursesDesiredDescendingPreferences:
                course1Index = self.coursesDesiredDescendingPreferences.index(courseName1)
                course2Index = self.coursesDesiredDescendingPreferences.index(courseName2)
                return course1 if course1Index < course2Index else course2
        elif courseName1 in self.coursesDesiredDescendingPreferences:
                return course1
        elif courseName2 in self.coursesDesiredDescendingPreferences:
            return course2
        else:
            return None
    
    def priority(self, course):
        '''
        Returns a 'score' tuple reporting how happy this student is with the
        given course, so that student.priority(A) > student.priority(B) if 
        and only if this student prefers course A to course B. All courses
        the student doesn't desire have equally low priorities.
        '''
        courseName = course.getCourseName()
        if courseName not in self.coursesDesiredDescendingPreferences:
            return -1
        else:
            courseIndex = self.coursesDesiredDescendingPreferences.index(courseName)
            return len(self.coursesDesiredDescendingPreferences) - courseIndex
            
        
    def getRegistrationClassYear(self) -> ClassYear:
        return self.registrationYear

    def getWishList(self):
        '''
        Returns a copy of the list of regularized course names that includes all courses the student
        includes in their preference list. 
        '''
        return self.coursesDesiredDescendingPreferences.copy()

    def __repr__(self):
        return "%s %-9s %-30s %-36s  %s" % (self.idNumber, self.getRegistrationClassYear(),
                                      self.emailAddress,
                                   " ".join(self.getCoreCoursesTaken()).replace("CS.",""),
                                   #" ".join(self.getElectivesTaken()).replace("CS.",""),
                                   " ".join(self.getWishList()).replace("CS.",""))
                                   

    def getRegistrationClassYearFromLevelAndStatus(self) -> ClassYear:

        '''Class level is a more precise indicator than class year, indicating
        which term a student is in. FR01 means a first-term frosh; FR03 means a
        third-term frosh; it then advances to SO01 to indicate a first-term
        sophomore, etc. When a student is a the end of a particular class year
        (FR03, SO06, JR09), and if they are on campus as usual (see details below),
        then they register as the next class year up. Students are seniors forever;
        there is no super-senior status for students who are here for a 13th
        term.

        Regarding determining if they are on campus as usual, enrollmentStatus
        codes of F (full time) or O (off-campus study) should be used as indicators
        thereof. The other codes [ L (leave of absence), R (required leave due to
        OCS), and X (early grad) ] should not be used to bump up class year.
        '''

        # If student is an early grad, then has a class level of "GR". This
        # student shouldn't be able to register at all, but for simplicity
        # we will simply assume that this student is a senior.
        if self.classLevel == "GR":

            return ClassYear.SENIOR

        
        elif self.classLevel is not None:

            # The prefix doesn't really matter, it's the number of terms that matters.
            termNumber = int(self.classLevel[2:])

            # Class year is determined by simple integer division on the term (minus
            # one). FR01, FR02, FR03 are all considered year 0. SO04, SO05, SO06, are
            # all considered year 1, etc.
            registrationClassYear = (termNumber - 1) // 3

            # If the student is at the end of a class year (i.e., a multiple of 3) and
            # they were regularly enrolled, the registration class year goes up by one.
            if termNumber % 3 == 0 and self.enrollmentStatus in ['F', 'O']:
                registrationClassYear += 1

            # Prevent super-seniors from potentially occuring
            registrationClassYear = min(registrationClassYear, 3)

            return ClassYear(registrationClassYear)

        else:

            # classLevel should only be missing if this is a student that expressed
            # preferences, for whom we have no registration data. In that case, we use
            # the class year to guess. The student's relative class year is determined
            # by comparing the student class year compared to the current year for the
            # senior class. We assume that the student is on phase, meaning that if it
            # is an upcoming fall registration, we bump up the class year.

            # classLevel should only be None if data was not in registrar data, so
            # enrollment status should not be there either
            assert self.enrollmentStatus is None, \
                    "enrollment status should be None when class level is"

            classYear = self.classYear
            if self.classYear < Student.seniorClassYear:
                warnings.warn(self.emailAddress + " has graduation year before " +
                              "current senior class.")
                classYear = Student.seniorClassYear

            yearsBehindSeniors = classYear - Student.seniorClassYear
            if yearsBehindSeniors > 3:
                warnings.warn(self.emailAddress + " has graduation year further " +
                              "in the future than any first year student")
                yearsBehindSeniors = 3

            # registrationClassYear should range from 0 to 3, with 3 being a
            # senior, and 0 being a first-year (three years behind seniors)
            registrationClassYear = 3 - yearsBehindSeniors

            assert Student.upcomingTerm in ["fall", "winter", "spring"], \
                    "Invalid value for upcoming term."
            if Student.upcomingTerm == "fall":
                registrationClassYear += 1

            # Prevent super-seniors from potentially occuring
            registrationClassYear = min(registrationClassYear, 3)

            return ClassYear(registrationClassYear)

def preferenceHeaderParse(s):
    '''Turn a string of the form "Preferences [CS202: Math of CS]" into "CS202";
       otherwise return the string, unchanged.'''
    allCourseNumbers = re.findall(r"CS(\d\d\d):",s)
    if len(allCourseNumbers) == 1:
        return "CS." + allCourseNumbers[0]
    elif len(allCourseNumbers) == 0:
        return s
    else:
        warnings.warn("Your header " + s + " contains more than one course.")
        return ""

def getClassYearHeaderBasedOnActualHeaders(fieldnames):        
    '''
    Gets which header is being used for Class Year in this
    version of the registrar file, with possibilities given
    in CLASS_YEAR_HEADERS.
    Needed because the data we get seems to have this
    field vary across terms, due to some change in how
    the data is being fetched that we aren't aware of.
    '''
    classYearHeader = None
    for header in CLASS_YEAR_HEADERS:
        if header in fieldnames:
             classYearHeader = header
    if classYearHeader is None:
        raise Exception("No class year header found in registrar data - fieldnames:" + str(fieldnames))
    return classYearHeader
    
    
def loadStudentsFromRegistrarData(registrarFileName, warningsLevel=1):
    '''
    Returns a dictionary mapping from email keys to Student values
    '''

    studentDictionary = {}
    with open(registrarFileName, encoding="utf-8") as registrarFile:
        registrarReader = csv.DictReader(registrarFile)
        CLASS_YEAR_HEADER = getClassYearHeaderBasedOnActualHeaders(registrarReader.fieldnames)
        
        for line in registrarReader:
            email = line[EMAIL_HEADER]
            if len(email) == 0:
                warnings.warn("Line has length zero email - skipping: %s" % str(line))
                continue

            if email not in studentDictionary:
                student = Student(line[ID_HEADER], line[EMAIL_HEADER], line[NAME_HEADER], line[CLASS_YEAR_HEADER],
                                  line[CLASS_LEVEL_HEADER], line[ENROLLMENT_STATUS_HEADER])
                studentDictionary[email] = student
            student = studentDictionary[email]
            # Some versions of the registrar data don't include a status code header
            if (STATUS_CODE_HEADER not in line) or (not isIgnoredStatusCode(line[STATUS_CODE_HEADER])):
                student.addCourse(line[COURSE_NAME_HEADER], warningsLevel=warningsLevel)
        
    return studentDictionary

def writeUniqueEmails(studentDict, outfile):
    '''
    Write out the emails of all students who should be notified about the match. These are students
    in the registrar data who have at least one CS course (including AP/prerequisite/etc).
    '''
    with open(outfile, 'w') as writer:
        for s in studentDict:
            csCourses = [c for c in studentDict[s].getRawCoursesTaken() if "CS." in c]
            if len(csCourses) > 0:
                writer.write(s + "\n")
            else:
                warnings.warn("Skipping printing email due to no CS taken: " + s)


def readCoursePreferences(line, courseNameToHeader):
    '''
    Reads the preferences from a row; returns as list.
    This function assumes students may choose not to submit
    preferences for some courses and that there is no explicit
    marking for not wanting to take a course beyond leaving
    that course out.
    '''
    currentPreferences = [None for _ in range(len(courseNameToHeader))]
    for courseName in courseNameToHeader:

        header = courseNameToHeader[courseName]
        value = line[header].strip()
        if value and value.isdigit():
            currentPreferences[int(value) - 1] = courseName
    for i in range(1,len(currentPreferences)-1):
        if currentPreferences[:i] == [None] * i \
           and None not in currentPreferences[i:]:
            warnings.warn("%s may have inverted preferences: prefs=%s"
                          % (line[PR_EMAIL_HEADER], str(currentPreferences)))
    currentPreferences = [c for c in currentPreferences if c]
    return currentPreferences


def readCoursePreferencesWithNone(line, courseNameToHeader):
    '''
    Reads the preferences from a row; returns as list. This function
    assumes an explicit option for "I don't want to take a course ranked below
    this" is present. (Header for that option is stored in NO_COURSE_CHOICE
    '''
    currentPreferences = [None for _ in range(len(courseNameToHeader) + 1)]
    for courseName in courseNameToHeader:

        header = courseNameToHeader[courseName]
        value = line[header].strip()
        if value and value.isdigit():
            currentPreferences[int(value) - 1] = courseName
    
            
    # Check for posible preference inversion
    for i in range(1,len(currentPreferences)-1):
        if currentPreferences[:i] == [None] * i \
           and None not in currentPreferences[i:]:
            warnings.warn("%s may have inverted preferences: prefs=%s"
                          % (line[PR_EMAIL_HEADER], str(currentPreferences)))
    
    # Strip off anything below the NO_COURSE_CHOICE
    noChoiceKey = [key for key in line if NO_COURSE_CHOICE in key][0]
    valueNoCourseChoice = int(line[noChoiceKey].strip())
    currentPreferences = currentPreferences[:valueNoCourseChoice]
    
    currentPreferences = [c for c in currentPreferences if c]
    return currentPreferences

def addPreferenceDataToStudentDictionary(
        preferenceFileName, studentDictionary, courseDictionary,
        warningsLevel=1):
    '''
    studentDictionary (keys:emails; values:Students) is modified to add 
    preference lists read from preferenceFileName
    Returns the number of students who we read in preferences for.
    '''
    numStudents  = 0
    with open(preferenceFileName, encoding="utf-8") as preferenceFile:
        preferenceReader = csv.DictReader(preferenceFile)
        fieldnames = preferenceReader.fieldnames
        assert fieldnames is not None, "Fieldnames is None, something went wrong in reading data."
        courseNameToHeader = {preferenceHeaderParse(header) : header
                              for header in fieldnames
                              if header != preferenceHeaderParse(header)}

        for line in preferenceReader:
            numStudents += 1
            email = line[PR_EMAIL_HEADER]
            idNum = line[PR_ID_HEADER]
            name = line[PR_NAME_HEADER]
            selfReportedCourses = []
            coursesTakenHeader = getCoursesTakenHeader(line);
            if coursesTakenHeader is not None:
                selfReportedCourses = line[coursesTakenHeader].split(",")
            else:
                warnings.warn("No header present that matched courses taken" + str(line))


            curStudent = studentDictionary.get(email)
            if email not in studentDictionary:
                curStudent = Student(idNum, email, name,
                                     line[PR_CLASS_YEAR_HEADER])
                studentDictionary[email] = curStudent
                warnings.warn(email + " submitted preference information but not in registrar data;" + \
                                 " adding with the year they gave:" + line[PR_CLASS_YEAR_HEADER])

            if curStudent.getID() != idNum and warningsLevel == 1:
                warnings.warn(email + " reported a different ID than registrar:" + str(curStudent.getID()) + " vs " + str(idNum))

            if (curStudent.getRegistrationClassYear()
                != getRegistrationYearFromNumericYear(
                    getNumericYearFromText(line[PR_CLASS_YEAR_HEADER]))):
                warnings.warn(email + ": Class year from registrar " + str(curStudent.getRegistrationClassYear()) + \
                  " didn't match preferences form year " + str(getNumericYearFromText(line[PR_CLASS_YEAR_HEADER])) + \
                  "; using year from registrar.")
                
            curStudent.addSelfReportedCoursesTaken(selfReportedCourses, warningsLevel=warningsLevel)
            curStudent.addPreferenceInformation(line, courseNameToHeader, courseDictionary)
    return numStudents

def getCoursesTakenHeader(line):
    '''
    Returns the header for the question about courses taken, or None
    if not present.
    '''
    fullTextOptions = [PR_CORE_TAKEN_HEADER, PR_CORE_TAKEN_HEADER_ALT]
    for fullTextOption in fullTextOptions:
        if fullTextOption in line:
            return fullTextOption
            
    # Look for prefix version
    headers = [header for header in line if header.startswith(PR_CORE_TAKEN_PREFIX)]
    if len(headers) == 0:
        return None
    else:
        return headers[0]
    
            
def isIgnoredStatusCode(statusCode):
    '''
    Returns true if the status code (from registrar's data)
    is one that should be ignored.
    '''
    return statusCode in IGNORE_CODES

def getNumericYearFromText(classYear) -> int:
    '''
    Returns a numeric version of the class year
    represented by the string classYear. If classYear
    is only two numbers (e.g., 23), transforms into the year
    in 2xxx (e.g., 2023).  If classYear cannot be interpreted as
    a number, returns 0 and prints a warning.
    '''
    classYear = classYear.strip()
    if len(classYear) == 2:
        classYear = "20" + classYear  # warning:  Not Y2.1K-compliant!
    try:
        return int(classYear)
    except:
        warnings.warn("Couldn't interpret " + classYear + " as an int.")
        return 0

def getRegistrationYearFromNumericYear(numericYear:int ) -> Optional[ClassYear]:
    '''This is a now unrelianle way of actually determining registration year
    and should generally be avoided; it is here only for purposes of doing some
    sanity checking.'''

    try:
        return ClassYear(3 - (numericYear - Student.seniorClassYear))
    except:
        warnings.warn("Couldn't interpret " + str(numericYear) + " as a class year.")
        return None
