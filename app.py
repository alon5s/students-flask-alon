import json
import crud
from flask import Flask, session, request, redirect, url_for, render_template, abort
from setup_db import execute_query
from sqlite3 import IntegrityError
from classes import Student, Course, Teacher, User, Grade
import datetime
from collections import namedtuple

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


@app.before_request
def auth():
    if "role" not in session.keys():
        session["role"] = "Guest"
        session["email"] = "guest@gmail.com"
    if session["role"] != 'admin':
        if "admin" in request.full_path:
            return abort(403)
        if "courses" in request.full_path:
            return abort(403)
        if "students" in request.full_path:
            return abort(403)
        if "attendance" in request.full_path:
            return abort(403)
    if session["role"] == 'Guest':
        if "profile" in request.full_path:
            return abort(403)


@app.route('/', methods=['GET', 'POST'])
def home():
    courses = [(c_name[0], c_name[1]) for c_name in execute_query("SELECT id,name FROM courses")]
    str, link, log = navbar_auth()
    return render_template("home.html", courses=courses, str=str, link=link, log=log)


def navbar_auth():
    if session["role"] != 'Guest':
        if session["role"] == 'admin':
            str = f'Logged in as: {session["role"]}'
            log = "Logout"
            link = "/logout"
        elif session["role"] == 'student':
            str = f'Logged in as: {session["email"]}'
            log = "Logout"
            link = "/logout"
    else:
        str = f'Welcome {session["role"]}'
        log = "Login"
        link = "/login"
    return str, link, log


def authenticate(email, password):
    role = execute_query(f"SELECT role FROM users WHERE email='{email}' AND password='{password}'")
    if role == []:
        return None
    else:
        return role[0][0]


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = authenticate(request.form["email"], request.form["password"])
        if role is None:
            return abort(403)
        else:
            session["role"] = role
            session["email"] = request.form["email"]
        return redirect(url_for("home"))
    return render_template("login.html")


@app.route('/logout')
def logout():
    session.pop('role', None)
    return redirect(url_for('home'))


@app.route('/admin')
def admin():
    str, link, log = navbar_auth()
    return render_template("admin.html", link=link, log=log)


@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if request.method == 'GET':
        str, link, log = navbar_auth()
        db_courses = crud.read("courses")
        courses = []
        for id, name, desc, t_id in db_courses:
            course = Course(id, name, desc, t_id)
            courses.append(course)
        return render_template("attendance.html", link=link, log=log, courses=courses)


@app.route('/attendance/<c_id>', methods=['GET', 'POST'])
def course_attendance(c_id):
    str, link, log = navbar_auth()
    c_name = execute_query(f"SELECT name FROM courses WHERE id={c_id}")
    c_name = c_name[0][0].title()
    today_date = datetime.date.today()
    if request.method == 'GET':
        students_ids = crud.read_where('student_id', 'students_courses', 'course_id', c_id)
        if len(students_ids) == 0:
            return render_template("c_attendance.html", link=link, log=log, today_date=today_date, c_name=c_name, c_id=c_id)
        else:
            answer_attend = crud.read_whereX2('date', 'attendances', 'course_id', c_id, 'date', f"'{today_date}'")
            if len(answer_attend) == 0:
                for s_id in students_ids:
                    crud.insert('attendances', 'student_id, course_id, date', f"'{s_id[0]}', '{c_id}', '{today_date}'")
                students_names_ids = []
                for s in students_ids:
                    student = namedtuple('S_Id', ['name', 'id'])
                    student.name = crud.student_name(s[0])
                    student.id = s[0]
                    students_names_ids.append(student)
                return render_template("c_attendance.html", link=link, log=log, c_id=c_id, c_name=c_name, today_date=today_date, students=students_names_ids)
            else:
                students_ids_attend = crud.read_whereX2('student_id', 'attendances', 'course_id', c_id, 'date', f"'{today_date}'")
                if len(students_ids) == len(students_ids_attend):
                    pass
                else:
                    for s_i in students_ids:
                        if s_i in students_ids_attend:
                            pass
                        else:
                            crud.insert('attendances', 'student_id, course_id, date', f"'{s_id[0]}', '{c_id}', '{today_date}'")
                course_attend = crud.read_whereX2('student_id, attendance', 'attendances', 'course_id', c_id, 'date', f"'{today_date}'")
                students_attend = []
                for s_a in course_attend:
                    student_a = namedtuple('S_Attend', ['id', 'name', 'attend'])
                    student_a.id = s_a[0]
                    student_a.name = crud.student_name(s_a[0])
                    student_a.attend = {}
                    if s_a[1] == 'yes':
                        student_a.attend['yes'] = 'checked'
                        student_a.attend['no'] = ''
                    elif s_a[1] == 'no':
                        student_a.attend['yes'] = ''
                        student_a.attend['no'] = 'checked'
                    students_attend.append(student_a)
        return render_template('c_attendance.html', link=link, log=log, today_date=today_date, c_name=c_name, c_id=c_id, students_attend=students_attend)
    if request.method == 'POST':
        answer = request.form["attendance"]
        student_id = request.form["s_id"]
        crud.update_attend(f"'{answer}'", student_id, c_id, f"'{today_date}'")
        return redirect(url_for('course_attendance', c_id=c_id))


@app.route('/h_att/<c_id>', methods=['GET', 'POST'])
def h_att(c_id):
    str, link, log = navbar_auth()
    date = request.args["date"]
    db_attendances = crud.read_whereX2("student_id, attendance", "attendances", "course_id", c_id, "date", f"'{date}'")
    if len(db_attendances) == 0:
        note = "Attendance hasn't been filled in this date"
        return render_template("h_att.html", date=date, link=link, log=log, note=note)
    else:
        h1 = "Name"
        h2 = "Attendance"
        students = []
        for student_id, attendance in db_attendances:
            student = namedtuple('student', ['id', 'name', 'att'])
            student.id = student_id
            student.name = crud.student_name(student_id)
            student.att = attendance
            students.append(student)
        return render_template("h_att.html", students=students, date=date, link=link, log=log, h1=h1, h2=h2)


@app.route('/students', methods=['GET', 'POST'])
def students():
    str, link, log = navbar_auth()
    students = execute_query("SELECT * FROM students")
    if request.method == 'POST':
        # FORM1 : ADD STUDENT
        if "form-submit" in request.form:
            try:
                s_name = request.form["s_name"].title()
                s_email = request.form["s_email"]
                s_phone = request.form["s_phone"]
                crud.insert("students", "name, email, phone", f"'{s_name}','{s_email}','{s_phone}'")
                crud.insert("users", "email,password,role", f"'{s_email}','12345678','student'")
                return redirect(url_for('students'))
            except IntegrityError:
                return abort(422)
        # FORM2 : ASSOCIATE STUDENT
        elif "form2-submit" in request.form:
            try:
                s_name = request.form["s_name"].title()
                s_email = request.form["s_email"]
                c_name = request.form["c_name"]
                student_details = crud.read_by_name("students", s_name)
                for id, name, email, phone in student_details:
                    student = Student(id, name, email, phone)
                course_details = crud.read_by_name("courses", c_name)
                for id, name, desc, t_id in course_details:
                    course = Course(id, name, desc, t_id)
                crud.insert("students_courses", "student_id,course_id,grade", f"'{student.id}', '{course.id}', 'NULL'")
                return redirect(url_for('students'))
            except IntegrityError:
                return abort(422)
    return render_template("students.html", students=students, link=link, log=log)


@app.route('/courses', methods=['GET', 'POST'])
def courses():
    str, link, log = navbar_auth()
    if request.method == 'POST':
        # first section: adding course
        add_course_name = request.form['course']
        teacher = request.form['teacher']
        description = request.form['desc_']
        t_id = [i[0] for i in execute_query(
            f"SELECT id FROM teachers WHERE name='{teacher}'")]
        execute_query(
            f"INSERT INTO courses VALUES(NULL,'{add_course_name}','{description}','{t_id[0]}')")
        teachers = [t[0] for t in execute_query("SELECT name FROM teachers")]
        return redirect(url_for('courses'))
    else:
        teachers = [t[0] for t in execute_query("SELECT name FROM teachers")]
        courses = execute_query("SELECT * FROM courses")
        return render_template("courses.html", courses=courses, teachers=teachers, link=link, log=log)


@app.route('/course/<course_id>')
def show_course(course_id):
    str, link, log = navbar_auth()
    c_name = [c_id[0] for c_id in execute_query(
        f"SELECT name FROM courses WHERE id={course_id}")]
    teacher_id = [t_id[0] for t_id in execute_query(
        f"SELECT teacher_id FROM courses WHERE id={course_id}")]
    teacher_details = [(teacher[0], teacher[1]) for teacher in execute_query(
        f"SELECT name,email FROM teachers WHERE id={teacher_id[0]}")]
    message = f"Welcome To Course {c_name[0]}".title()
    student_ids = [s_id[0] for s_id in execute_query(
        f"SELECT student_id FROM students_courses WHERE course_id={course_id}")]
    students = [[(student[0], student[1]) for student in execute_query(
        f"SELECT id, name FROM students WHERE id={student_id}")] for student_id in student_ids]
    return render_template("course.html", teacher_details=teacher_details, c_name=c_name, message=message, students=students, link=link, log=log)


@app.route('/profile/<int:student_id>')
def profile(student_id):
    str, link, log = navbar_auth()
    course_ids = execute_query(f"SELECT course_id FROM students_courses WHERE student_id={student_id}")
    clean_ids = [c[0] for c in course_ids]
    course_names = []
    for i in clean_ids:
        course_names.append(execute_query(f"SELECT name FROM courses WHERE id={i}"))
    student_details = execute_query(f"SELECT * FROM students WHERE id={student_id}")
    return render_template("profile.html", student_details=student_details, course_names=course_names, link=link, log=log, student_id=student_id)


@app.route('/teachers')
def teachers():
    str, link, log = navbar_auth()
    teachers = execute_query("SELECT * FROM teachers")
    return render_template("teachers.html", link=link, log=log, teachers=teachers)


@app.route('/teacher/<teacher_id>', methods=['GET', 'POST'])
def teacher_profile(teacher_id):
    if request.method == 'GET':
        str, link, log = navbar_auth()
        t_name = crud.teacher_name(teacher_id)
        course_details = crud.read_where("id,name", "courses", "teacher_id", teacher_id)
        courses = []
        for id, name in course_details:
            course = Course(id, name)
            courses.append(course)
        grades_courses = {}
        for course in courses:
            for course in get_course(course.id):
                grades_courses[course.name] = get_grades(course.id)
        return render_template("teacher.html", grades_courses=grades_courses, link=link, log=log, t_name=t_name, courses=courses)
    elif request.method == 'POST':
        grade = request.form['grade']
        s_name = request.form['s_name']
        c_name = request.form['c_name']
        s_id = crud.read_where("id", "students", "name", f"'{s_name}'")
        c_id = crud.read_where("id", "courses", "name", f"'{c_name}'")
        crud.update_grade(grade, s_id[0][0], c_id[0][0])
        return redirect(url_for("teacher_profile", teacher_id=teacher_id))


def get_course(course_id):
    courses = execute_query(f"SELECT id, name FROM courses WHERE id={course_id}")
    return [Course(*course) for course in courses]


def get_grades(course_id):
    grades = execute_query(f"SELECT students.name, students_courses.grade FROM students JOIN students_courses ON students.id=students_courses.student_id WHERE students_courses.course_id={course_id}")
    return [Grade(name=grade[0], grade=grade[1]) for grade in grades]


@app.route('/update/<int:student_id>', methods=['GET', 'POST'])
def update(student_id):
    str, link, log = navbar_auth()
    if request.method == 'POST':
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]
        if (email != '') or (phone != '') or (password != ''):
            execute_query(f"UPDATE students SET email='{email}',phone='{phone}' WHERE id={student_id}")
            db_email = execute_query(f"SELECT email FROM students WHERE id={student_id}")
            execute_query(f"UPDATE users SET password='{password}' WHERE email='{db_email[0][0]}'")
        return redirect(url_for("profile", student_id=student_id))
    else:
        return render_template("update.html", link=link, log=log, student_id=student_id)


@app.route('/results', methods=['GET', 'POST'])
def results():
    str, link, log = navbar_auth()
    search = request.args['search']
    c_check = request.args.get('c')
    s_check = request.args.get('s')
    t_check = request.args.get('t')
    c_note = "Courses:"
    s_note = "Students:"
    t_note = "Teachers:"
    result = f"This is what I have found for '{search}'"
    div = """<div class="message">"""
    div_ = "</div>"
    if search == '':
        return render_template("results.html", result=result, div=div, div_=div_)
    else:
        if c_check != "c" and s_check != "s" and t_check != "t":
            db_courses = crud.read_by_like("*", "courses", "name", search)
            courses = []
            for id, name, desc, t_id in db_courses:
                course = Course(id, name, desc, t_id)
                courses.append(course)
            db_students = crud.read_by_like("*", "students", "name", search)
            students = []
            for id, name, email, phone in db_students:
                student = Course(id, name, email, phone)
                students.append(student)
            db_teachers = crud.read_by_like("*", "teachers", "name", search)
            teachers = []
            for id, name, email in db_teachers:
                teacher = Teacher(id, name, email)
                teachers.append(teacher)
            return render_template("results.html", t_note=t_note, s_note=s_note, c_note=c_note, courses=courses, students=students, teachers=teachers, result=result, div=div, div_=div_, link=link, log=log)
        if c_check == 'c':
            db_courses = crud.read_by_like("*", "courses", "name", search)
            courses = []
            for id, name, desc, t_id in db_courses:
                course = Course(id, name, desc, t_id)
                courses.append(course)
        else:
            courses = []
            c_note = ""
        if s_check == 's':
            db_students = crud.read_by_like("*", "students", "name", search)
            students = []
            for id, name, email, phone in db_students:
                student = Course(id, name, email, phone)
                students.append(student)
        else:
            students = []
            s_note = ""
        if t_check == 't':
            db_teachers = crud.read_by_like("*", "teachers", "name", search)
            teachers = []
            for id, name, email in db_teachers:
                teacher = Teacher(id, name, email)
                teachers.append(teacher)
        else:
            t_note = ""
            teachers = []
        return render_template("results.html", t_note=t_note, s_note=s_note, c_note=c_note, courses=courses, students=students, teachers=teachers, result=result, div=div, div_=div_, link=link, log=log)
