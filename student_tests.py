# Very late attempt at a few tests
import student
import match
import priorityDict
import course
import filenames

def testRelativeClassYears():
    student.Student.setGeneralCalendarInfo(2023, "spring")
    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", "FR01", "O")
    assert enrollee.registrationYear == student.ClassYear.FROSH


    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", "FR01", "X")
    assert enrollee.registrationYear == student.ClassYear.FROSH

    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", "FR03", "F")
    assert enrollee.registrationYear == student.ClassYear.SOPHOMORE

    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", "FR03", "O")
    assert enrollee.registrationYear == student.ClassYear.SOPHOMORE

    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", "FR03", "X")
    assert enrollee.registrationYear == student.ClassYear.FROSH

    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", "SO04", "F")
    assert enrollee.registrationYear == student.ClassYear.SOPHOMORE

    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", "SO06", "F")
    assert enrollee.registrationYear == student.ClassYear.JUNIOR

    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", "SO07", "F")
    assert enrollee.registrationYear == student.ClassYear.JUNIOR


    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", "JR09", "F")
    assert enrollee.registrationYear == student.ClassYear.SENIOR

    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", "SO07", "L")
    assert enrollee.registrationYear == student.ClassYear.JUNIOR

    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", "SR10", "F")
    assert enrollee.registrationYear == student.ClassYear.SENIOR

    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", "SR11", "F")
    assert enrollee.registrationYear == student.ClassYear.SENIOR

    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", "SR12", "F")
    assert enrollee.registrationYear == student.ClassYear.SENIOR

    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", "SR13", "F")
    assert enrollee.registrationYear == student.ClassYear.SENIOR

    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", "SR14", "F")
    assert enrollee.registrationYear == student.ClassYear.SENIOR


    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", None, None)
    assert enrollee.registrationYear == student.ClassYear.SENIOR

    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2024", None, None)
    assert enrollee.registrationYear == student.ClassYear.JUNIOR

    student.Student.setGeneralCalendarInfo(2023, "fall")
    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2024", None, None)
    assert enrollee.registrationYear == student.ClassYear.SENIOR

    student.Student.setGeneralCalendarInfo(2023, "winter")
    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2024", None, None)
    assert enrollee.registrationYear == student.ClassYear.JUNIOR

    # Early grad
    student.Student.setGeneralCalendarInfo(2023, "spring")
    enrollee = student.Student(
        1111, "a@carleton.edu", "A", "2023", "GR", "X")
    assert enrollee.registrationYear == student.ClassYear.SENIOR

def testGetRegistrationYearFromClassYear():
    student.Student.setGeneralCalendarInfo(2023, "winter")
    assert student.getRegistrationYearFromNumericYear(2023) == \
        student.ClassYear.SENIOR
    assert student.getRegistrationYearFromNumericYear(2024) == \
        student.ClassYear.JUNIOR
    assert student.getRegistrationYearFromNumericYear(2025) == \
        student.ClassYear.SOPHOMORE
    assert student.getRegistrationYearFromNumericYear(2026) == \
        student.ClassYear.FROSH

def testCorrectMatches():
    '''These tests are based on the small set of test data provided (students a
    through e).'''

    tiebreaker = priorityDict.PriorityDictionary(debug=False, seed=12346)

    courseDictionary = course.loadCourses(filenames.coursesFileName, tiebreaker)

    student.Student.setGeneralCalendarInfo(2023, "spring")
    studentDictionary = student.loadStudentsFromRegistrarData(
        filenames.registrarFileName)

    student.addPreferenceDataToStudentDictionary(
        filenames.preferenceFileName, studentDictionary, courseDictionary,
        warningsLevel=0)

    match.prepareForForcedMatches([], courseDictionary, studentDictionary, show_steps=False)
    forcedMatchDictionary = match.parseForcedMatchExceptionString([])
    maxCoursesDictionary = match.parseMaxCoursesExceptionString([])
    match.applyNumberOfCoursesExceptionWithForcedCourses(forcedMatchDictionary, maxCoursesDictionary, studentDictionary)

    rosters, rejections = match.match(studentDictionary, courseDictionary,
                                      maxCoursesDictionary=maxCoursesDictionary)

    match.printMatch(rosters, rejections, courseDictionary, studentDictionary)

    # Just some random tests to see if things are working as they should
    for key in rosters.keys():
        if key.getCourseName() == 'CS.251':
            assert "c@carleton.edu" in rosters[key]

