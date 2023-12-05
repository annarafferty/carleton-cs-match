import sys
import warnings
import argparse

import course
import student
import filenames
import priorityDict
from collections import defaultdict

def printMatch(rosters, rejections, courseDictionary, studentDictionary=None):
    print()
    numMatches = 0
    for c in courseDictionary:
        roster = rosters[courseDictionary[c]]
        numMatches += len(roster)        
        print(c,
              "%d/%d" % (len(roster), courseDictionary[c].getCapacity()),
              " ".join(sorted(roster)).replace("@carleton.edu",""))
        if studentDictionary is not None:
            verbose_strings = [(
                studentDictionary[s].getName()
                + ","
                + str(studentDictionary[s].getRegistrationClassYear())
                + ","
                + str(studentDictionary[s].getWishList()))
                               for s in roster]
            print(c,
              "%d/%d" % (len(roster), courseDictionary[c].getCapacity()))
            print(
              "\n".join(verbose_strings).replace("@carleton.edu",""))

    print(":( :( ", "%d   " % len(rejections),
          " ".join(sorted(rejections)).replace("@carleton.edu",""))
    print(":) :) ", "%d   " % numMatches)
    print("total students processed", "%d   " % (numMatches + len(rejections)))

def printRegistrarMatch(rosters, rejections, courseDictionary, studentDictionary):
    for c in courseDictionary:
        roster = rosters[courseDictionary[c]]
        print("New capacity for %s:    %d"
              % (c, courseDictionary[c].getCapacity() - len(roster)))
        print("New capacity for %s.M:  %d" % (c, len(roster)))
        print()
    for c in courseDictionary:
        roster = rosters[courseDictionary[c]]
        for email in sorted(roster):
            print("%-25s%-18s%s.M" % (email.replace("@carleton.edu",""),
                                        studentDictionary[email].getID(), c))
        print()
    print("DID NOT MATCH:", ", ".join(sorted(rejections)))  
    
def match(studentDict, courseDict, show_steps=False, maxCoursesDictionary={}):
    wishlists = {s : studentDict[s].getWishList() for s in studentDict
                 if studentDict[s].submittedPreferences()}
    rosters = {c : [] for c in courseDict.values()}

    universallyRejected = []
    singleStudentEmails = [s for s in wishlists]

    # Add in exceptions for extra courses for a student
    for email in maxCoursesDictionary:
        numCourses = maxCoursesDictionary[email]
        for _ in range(numCourses - 1): # first course is already included
            singleStudentEmails.append(email)

    while len(singleStudentEmails) > 0:
        proposerEmail = singleStudentEmails.pop(0)

        # If this proposer has no options left, despair, and move on.
        if len(wishlists[proposerEmail]) == 0:
            if show_steps: print("Grim news for %s:  you're out of options. %s" % (proposerEmail, " ".join(studentDict[proposerEmail].getWishList())))
            universallyRejected.append(proposerEmail)
            continue
        proposee = max([courseDict[c] for c in wishlists[proposerEmail]],
                             key = studentDict[proposerEmail].priority)
        wishlists[proposerEmail].remove(proposee.getCourseName())
        cannotTakeProposedCourse = proposee.cannotTake(studentDict[proposerEmail])
        if cannotTakeProposedCourse:
            warnings.warn(proposerEmail + " tried to propose to " + proposee.getCourseName()
                          + " but " + cannotTakeProposedCourse + " so returning to singledom")
            singleStudentEmails.append(proposerEmail)            
        else:
            # Otherwise, add proposer to top remaining choice, which dumps
            # one member of its roster if it's just now gone over capacity.
            rosters[proposee].append(proposerEmail)
            if show_steps: print("Adding", proposerEmail, "to", proposee.getCourseName(),
                                 "which now has", len(rosters[proposee]), "matches", end="")

            if len(rosters[proposee]) > proposee.getCapacity():
                # You're the worst.
                dumpeeEmail = min([studentDict[s] for s in rosters[proposee]],
                                  key = proposee.priority).getEmail()
                if show_steps: print(" but, bad news,", proposee, "is dumping", dumpeeEmail,end="")
                rosters[proposee].remove(dumpeeEmail)
                singleStudentEmails.append(dumpeeEmail)
            if show_steps: print(".")

    return rosters, universallyRejected

def warnForBadMatches(studentDictionary, rosters):
    warnings.warn("")
    warnings.warn("---- students who matched to a course they can't take? ----")
    for course in rosters:
        for sEmail in rosters[course]:
            if course.cannotTake(studentDictionary[sEmail]):
                warnings.warn("%s matched to %s but %-45s.\tstudent: %s"
                              % (sEmail, course.getCourseName(),
                                 course.cannotTake(studentDictionary[sEmail]),
                                 studentDictionary[sEmail]))
                              
def warnForMissingRequirements(studentDictionary, courseDictionary, rosters, currentYear, threshold=1, useOnlyCoreCoursesForMajor=False):
    '''Issue warnings for any students who (i) are seniors [grad year =
    currentYear], (ii) are apparently majors (have CS.399 on their
    records), and (iii) are missing at least threshold requirements
    for the major.
    '''
    warnings.warn("")
    warnings.warn("---- CS majors who may not be on pace for graduation? ----")
    coreTaken = {s : s.getCoreCoursesTaken() for s in studentDictionary.values()}
    elecTaken = {s : s.getElectivesTaken() for s in studentDictionary.values()}
    myMatch = defaultdict(list)
    for c in courseDictionary.values():
        for s in rosters[c]:
            myMatch[s].append(c.getCourseName())
            if course.isCore(c.getCourseName()):
                coreTaken[studentDictionary[s]].append(c.getCourseName())
            elif course.isElective(c.getCourseName()):
                elecTaken[studentDictionary[s]].append(c.getCourseName())
    for s in studentDictionary.values():

        missingRequirements = list(course.CORE_COURSES.difference(set(coreTaken[s])))
        missingRequirements += ["elective"] * (2 - len(elecTaken[s]))
        #
        if int(s.getRegistrationClassYear()) == student.ClassYear.SENIOR \
           and (useOnlyCoreCoursesForMajor or course.regularize("CS.399") in s.getCoursesTaken()) \
           and isMajor(s, coreTaken) \
           and len(missingRequirements) >= threshold:
            warnings.warn("%s, a senior with CS.399 who matched to [%s], is missing [%s]"
                          % (s.getEmail(), ", ".join(myMatch[s.getEmail()]),
                             ", ".join(missingRequirements)))

def isMajor(s, coreTaken):
     comps = course.regularize("CS.399") in s.getCoursesTaken()
     missingRequirements = list(course.CORE_COURSES.difference(set(coreTaken[s])))
     return comps or len(missingRequirements) < 3

def prepareForForcedMatches(forcedMatches, courseDictionary,
                            studentDictionary, show_steps=False):
    '''
    Input: forcedMatches: a list of strings of the form studentemail:coursename
           courseDictionary: keys=courseNames, values=Course objects
           studentDictionary: keys=emailAddresses, values=Student objects
           show_steps: should we print all of the steps to stdout?
    Effect: (1) Reduce capacity in each course by its number of forced matches; 
            (2) Mark the student as ineligible for further matching.
    (no return)
    '''
    for pair in forcedMatches:
        email = pair.split(':')[0]
        courseName = course.regularize(pair.split(':')[1])
        if courseName not in courseDictionary:
            warnings.warn("Trying to force " + email + " into the nonexistent "
                          + "course " + courseName + "; doing nothing.")
        elif email not in studentDictionary:
            warnings.warn("Trying to force nonexistent " + email + " into "
                          + "course " + courseName + "; doing nothing.")
        else:
            courseDictionary[courseName].decrementCapacity()
            studentDictionary[email].markIneligibleForMatch()
            if show_steps: print("Decreasing capacity of " + courseName
                                 + " to make room for " + email)

def parseMaxCoursesExceptionString(maxCoursesString):
    '''
    Input: maxCoursesString: commandline  string of the form studentemail:numcourses,
            comma-separated
    Return: Dictionary where keys are emails and values are (integer) number of courses
    '''
    return { pair.split(':')[0] : int(pair.split(':')[1]) for pair in maxCoursesString}
     
def parseForcedMatchExceptionString(forcedMatchesString):
    '''
    Input: forcedMatches: a list of strings of the form studentemail:coursename,
            comma-separated
    Return: Dictionary where keys are emails and values are lists of regularized
             courses to force a match to
    '''
    forcedMatchDictionary = {}
    for pair in forcedMatchesString:
        email = pair.split(':')[0]
        courseName = course.regularize(pair.split(':')[1])
        if email not in forcedMatchDictionary:
            forcedMatchDictionary[email] = []
        forcedMatchDictionary[email].append(courseName)
    return forcedMatchDictionary
    
def applyNumberOfCoursesExceptionWithForcedCourses(forcedMatchDictionary, maxCoursesDictionary,
                                                  studentDictionary):
    '''
    Input: forcedMatchDictionary: Dictionary where keys are emails and values are lists of regularized
             courses to force a match to
           maxCoursesDictionary:  Dictionary where keys are emails and values are (integer) number of 
           studentDictionary: keys=emailAddresses, values=Student objects
    Effect: Students who are eligible for both types of exceptions are eligible to match to their exception
             number of courses minus the number of courses we'll force a match to (modification to maxCoursesDictionary
             and objects in studentDictionary).
   '''    
    # Want students who have a max course exception and a force match
    studentsWithBothExceptions = forcedMatchDictionary.keys() & maxCoursesDictionary.keys() # intersect
    for email in studentsWithBothExceptions:
        totalForcedCourses = len(forcedMatchDictionary[email])
        if totalForcedCourses != maxCoursesDictionary[email]:
            # Student can match to at least one more course than we have a forced match for
            # Need to mark them eligible for the match and remove the forced course from their
            # preferences (since we'll match them to that anyway)
            # Then set the number of courses to allow a match to to be smaller, accounting
            # for some matches coming from forcing
            studentDictionary[email].markEligibleForMatch()
            for course in forcedMatchDictionary[email]:
                studentDictionary[email].removePreference(course)
            maxCoursesDictionary[email] = maxCoursesDictionary[email] - totalForcedCourses
        

def applyForcedMatches(forcedMatches, courseDictionary,
                       studentDictionary, rosters, show_steps=False):
    '''
    Input: forcedMatches: a list of strings of the form studentemail:coursename
           courseDictionary: keys=courseNames, values=Course objects
           studentDictionary: keys=emailAddresses, values=Student objects
           rosters: keys=courses, values=list of student emails
           show_steps: should we print all of the steps to stdout?
    Effect: updats rosters by adding in all forced matches.
    (no return)
    '''
    for pair in forcedMatches:
        email = pair.split(':')[0]
        courseName = course.regularize(pair.split(':')[1])
        if courseDictionary[courseName] not in rosters:
            warnings.warn("Trying to force " + email + " into the nonexistent "
                          + "course " + courseName + "; doing nothing.")
        courseDictionary[courseName].incrementCapacity()
        rosters[courseDictionary[courseName]].append(email)
        studentDictionary[email].markEligibleForMatch()
        if show_steps: print("Increasing capacity of " + courseName
                             + " and filling it with forced match " + email)


            
def main():
    

    def warning_on_one_line(message, category, filename, lineno, file=None, line=None):
        return 'WARNING: %s\n' % (message)     # See https://pymotw.com/2/warnings/
    warnings.formatwarning = warning_on_one_line    

    parser = argparse.ArgumentParser(description='Run The Match.')
    parser.add_argument('--force', type=str, nargs='*', default=[],
                        help="forced pairings list; format: 'email:course'")
    parser.add_argument('--warnings', type=int, default=0,
                        help='display warning messages. level 1 means all warnings. \
                              level 2 excludes courses appearing twice, mismatches \
                              between registrar course report and student course report, \
                              and mismatches between student stated id and actual id. "\
                              no warnings printed if not specified or set to level 0.')
    parser.add_argument('--verbose', action='store_true',
                        help='display Gale-Shapley status reports')
    parser.add_argument('--deterministic', action='store_true',
                        help='use nonrandom [reproducible] tiebreaker based on MD5 hash of student email address')
    parser.add_argument('--seed', type=int,
                        help='use reproducible random tiebreakers seeded by value given (deterministic takes priority)')
    parser.add_argument('--suppress_match_output', action='store_true',
                        help='do not print the match (debugging/warnings only)')
    parser.add_argument('--registrar', action='store_true',
                        help='print the data for registrar email in addition to other data')
    parser.add_argument('--senior_class_year', type=str, required=True,
                        help='senior class grad year (4 digits) at the time data was pulled')
    parser.add_argument('--upcoming_term', type=str, choices=['fall', 'winter', 'spring'],
                        help='term that students are registering for', required=True)
    parser.add_argument('--missing_requirement_threshold', type=int, default=1, help='how many unfilled requirements are okay?')
    parser.add_argument('--use_course_threshold_for_major',action='store_true', help='if true, warning for missing requirements wil use hving a large number of core courses, not enrollment in 399, to determine majors')
    parser.add_argument('--num_courses_exception', type=str, nargs='*', default=[],
                        help="exceptions where student is allowed multiple matches; format: 'email:num matches'")
    parser.add_argument('--write_emails_for_advertising', type=str, default=None,
                        help="print only the emails of students who should be notified about the match (based on registrar data")
    args = parser.parse_args()
    if args.warnings == 0:
        warnings.filterwarnings('ignore')

    tiebreaker = priorityDict.PriorityDictionary(debug=args.deterministic, seed=args.seed)

    courseDictionary = course.loadCourses(filenames.coursesFileName, tiebreaker)

    student.Student.setGeneralCalendarInfo(
        student.getNumericYearFromText(args.senior_class_year),
        args.upcoming_term)

    studentDictionary = student.loadStudentsFromRegistrarData(
        filenames.registrarFileName, warningsLevel=args.warnings)

    if args.write_emails_for_advertising is not None:
        student.writeUniqueEmails(studentDictionary, args.write_emails_for_advertising)
        sys.exit(0)

    numStudents = student.addPreferenceDataToStudentDictionary(
        filenames.preferenceFileName, studentDictionary, courseDictionary,
        warningsLevel=args.warnings)

    if args.verbose:
        for s in studentDictionary:
            if studentDictionary[s].submittedPreferences():
                print(studentDictionary[s])
    prepareForForcedMatches(args.force, courseDictionary, studentDictionary, show_steps=args.verbose)
    forcedMatchDictionary = parseForcedMatchExceptionString(args.force)
    maxCoursesDictionary = parseMaxCoursesExceptionString(args.num_courses_exception)
    applyNumberOfCoursesExceptionWithForcedCourses(forcedMatchDictionary, maxCoursesDictionary, studentDictionary)

    rosters, rejections = match(studentDictionary, courseDictionary, show_steps=args.verbose, maxCoursesDictionary=maxCoursesDictionary)


    applyForcedMatches(args.force, courseDictionary, studentDictionary, rosters, show_steps=args.verbose)
    if args.registrar:
        printRegistrarMatch(rosters, rejections, courseDictionary, studentDictionary)
    if not args.suppress_match_output:
        printMatch(rosters, rejections, courseDictionary, studentDictionary)
        print("total students in preferences file (should match total students processed minus 1 extra for each extra matched course due to exceptions):", numStudents)
        
    for rejection in rejections:
        print(studentDictionary[rejection], studentDictionary[rejection].getWishList())
                  
    warnForBadMatches(studentDictionary, rosters)
    warnForMissingRequirements(studentDictionary, courseDictionary, rosters, args.senior_class_year, threshold=args.missing_requirement_threshold, useOnlyCoreCoursesForMajor=args.use_course_threshold_for_major)
    
if __name__ == "__main__":
    main()
    

