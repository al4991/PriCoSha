from flask import Flask, render_template, session, redirect
from flask import url_for, escape, request, flash 
import pymysql.cursors

app = Flask(__name__)
app.secret_key = "Doesn'tMatterRn"

# Setting up MySQL
conn = pymysql.connect(host='localhost',
	                 user='root',
	                 password='root',
	                 db='pricosha',
	                 charset='utf8mb4',
	                 cursorclass=pymysql.cursors.DictCursor)


@app.route("/")
def index():
    return render_template('index.html')


@app.route('/login')
def login(): 
    return render_template('login.html')

@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    user_email = request.form['email']
    password = request.form['password']
    # Set up cursor to prepare for executing queries
    cursor = conn.cursor()
    # Templating the query to check email and password
    # FOR THE FUTURE: we need to account for the fact that we will 
    # be hashing passwords
    query = 'SELECT * FROM PERSON WHERE email = %s and password = %s'
    cursor.execute(query, (user_email, password))
    # Grab the row with email and password (if it exists)
    data = cursor.fetchone()
    # We're done with the cursor now so we can close it
    cursor.close()

    # Checking to see if the login info actually exists or not 
    if (data):
        # creates a session for the user
        session['email'] = user_email
        # redirecting user to our main page
        # return redirect(url_for('/'))
        return render.template('index.html')
    else: 
        # Means we didn't find the login info, so failed login
        # We create an error to pass to our html
        #flash("Something is wrong. Login failed")
        #error = "Invalid email or password"
        #return render_template('login.html', error=error)
        error = "Invalid email or password"
        return render_template('login.html', error=error)

@app.route('/register')
def register(): 
	return render_template('signup.html')

@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    #grabs information from the forms
    user_email = request.form['email']
    password = request.form['password']

    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM PERSON WHERE email = %s'
    cursor.execute(query, (user_email))

    data = cursor.fetchone()
    if(data):
        error = "This user already exists"
        cursor.close()
        return render_template('signup.html', error=error)
    else:
        ins = 'INSERT INTO PERSON VALUES(%s. %s)'
        cursor.execute(ins, (user_email, password))

        conn.commit()
        cursor.close()
        return render_template('index.html')

@app.route('/post',methods=['GET','POST'])
def post():
    user_email = session['email']
    cursor = conn.cursor()
    blog = request.form['blog']
    query = 'INSERT INTO blog (blog_post, email) VALUES(%s, %s)'
    cursor.execute(query,(blog,user_email))        
    conn.commit()
    cursor.close()
    return redirect(url_for('home'))

@app.route('/home')
def home():
    user_email = session['email']
    cursor = conn.cursor()
    query = 'SELECT ts, blog_post FROM blog WHERE email = %s ORDER BY ts DESC'
    cursor.execute(query,(user_email))
    data = cursor.fetchall()
    cursor.close()
    return render_template('home.html', email=user_email, posts=data)


@app.route('/logout')
def logout():
    session.pop('email')
    return redirect('/')

if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug = True)