# Implementation of the Match

Code for the Match pre-registration system, as described in "Playing with Matches: Adopting Gale-Shapley for Managing Student Enrollments beyond CS2" (SIGCSE 2024).

Main file is match.py. Required data files:
- Courses file: Specifies what courses are in the match each term. Has headers `Course Name`, `Capacity`,`Course Type`, `Prerequisites`, and `Students with Prereq Waiver`. Capacity is the number of seats in he match for that course, Course Type is core or elective, and Prerequisites is a comma-separated list of other courses (which need not be in the Math). OR can be specified in the prerequisites list to indicate that any of the listed courses are acceptable as a prerequisite.
- Registrar data file: Provided each term by the Registrar's office, this file lists students' graduation years and which prerequisite classes have been successfully completed or are in progress during the current term.
- Student preference file: Downloaded from the Google form in which we collect student preferences, as well as their class year and previously taken courses. If a student doesn't have a class year in the registrar data file (e.g., because of coming back from leave), the class year they provide is used. Students are assumed to have taken all courses that they list and the registar lists as taken (as, for instance, a student may know they've taken a course at an off-campus studies program, but the registrar's office is not yet aware).


`data` includes sample files for testing. `documents` includes the text of information given to students about the match (and links to additional information) as well as a pdf printout of a match form for collecting preferences (distributed via Google Forms).


