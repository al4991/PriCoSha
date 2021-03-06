import os
from flask import Flask, render_template, session, redirect, flash
from flask import url_for, request
from perm import conn

app = Flask(__name__)
app.static_folder = 'static'
app.secret_key = "Doesn'tMatterRn"

# APP_ROOT = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.basename('/static')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route("/", methods=['GET', 'POST'])
def index():
    sessionBool = False
    friendData = None
    memberData = None
    rate_data = None
    tagged_items = None



    if 'userEmail' in session:
        sessionBool = True
    try:
        contentType = request.form['contentType']

    # if no filter selected, show all content
    except Exception:
        contentType = "All"
    # call content to select data that is shown on homepage
    # different if user logged in or not
    data = content(sessionBool, contentType)
    cursor = conn.cursor()
    
    if 'userEmail' in session:
        #display the names of the groups that you own
        friendQuery = "SELECT fg_name FROM FriendGroup WHERE owner_email = %s"
        cursor.execute(friendQuery, session['userEmail'])
        friendData = cursor.fetchall()
        cursor.rownumber = 0
        
        # display the name of the groups you belong to, but do now own
        memberQuery = "SELECT fg_name FROM Belong WHERE email = %s AND owner_email != %s"
        useremail = session['userEmail']
        cursor.execute(memberQuery, (useremail, useremail))
        memberData = cursor.fetchall()
        cursor.rownumber = 0

        # looks for rating that the user did for a specific post
        query = "SELECT item_id, emoji FROM Rate WHERE email = %s"
        cursor.execute(query, (session['userEmail']))
        rate_data = cursor.fetchall()
        cursor.rownumber = 0

        # select the posts and the name of the person who was tagged in the posts
        # only posts that the user has accepted to be tagged in
        tag_query = "SELECT item_id, fname, lname" \
                    " FROM Tag NATURAL JOIN Person WHERE email_tagged = email and status = 'True'"
        cursor.execute(tag_query)
        tagged_items = cursor.fetchall()
        cursor.rownumber = 0

    # finds the number of rates per emoji for ever post
    query = "SELECT item_id, emoji, count(*) AS emoji_count FROM Rate" \
            " GROUP BY item_id, emoji"
    cursor.execute(query)
    rate_stats = cursor.fetchall()

    cursor.close()
    if 'userEmail' in session:
        # if the user is logged in, they're redirected to the homepage where they can see their groups
        # they can also go to pages to see whose tagged them in posts and whose shared posts with them
        # user can see posts that public to them
        return render_template('index.html', ownedGroups=friendData,
                               memberGroups=memberData, posts=data,
                               rates=rate_data, rate_stats=rate_stats,
                               email=session['userEmail'],
                               contentType=contentType, tags=tagged_items)
    else:
        # if user is not logged in they are only allowed to see public posts that have been posted within the last 24 hours
        return render_template('index.html', posts=data,
                               rate_stats=rate_stats, contentType=contentType)



def content(inSession, contentType):
    cursor = conn.cursor()
    # the user is allowed to filter content by the type so they can see all, text only posts or just images
    if inSession:
        # if user is logged in they are allowed to see posts that are public to them 
        # posts are ordered by most recent
        if contentType == "Text":
            query = "SELECT * FROM ContentItem WHERE ((is_pub = 1 AND post_time + INTERVAL 24 hour >= CURRENT_TIMESTAMP) OR email_post = %s) AND" \
                    " content_type = 'text' ORDER BY post_time DESC"
            cursor.execute(query, session['userEmail'])
        elif contentType == "Images":
            query = "SELECT * FROM ContentItem WHERE ((is_pub = 1 AND post_time + INTERVAL 24 hour >= CURRENT_TIMESTAMP) OR email_post = %s) AND" \
                    " content_type = 'image' ORDER BY post_time DESC"
            cursor.execute(query, (session['userEmail']))
        else:
            query = "SELECT * FROM ContentItem WHERE (is_pub = 1 AND post_time + INTERVAL 24 hour >= CURRENT_TIMESTAMP) OR email_post = %s" \
                    " ORDER BY post_time DESC"
            cursor.execute(query, session['userEmail'])

    # user not logged in and can only see public posts
    else:
        if contentType == "Text":
            query = "SELECT * FROM ContentItem WHERE is_pub = 1 AND content_type = 'text'" \
                    " AND post_time + INTERVAL 24 hour >= CURRENT_TIMESTAMP ORDER BY post_time DESC"
            cursor.execute(query)
        elif contentType == "Images":
            query = "SELECT * FROM ContentItem WHERE is_pub = 1 AND content_type = 'image'" \
                    " AND post_time + INTERVAL 24 hour >= CURRENT_TIMESTAMP ORDER BY post_time DESC"
            cursor.execute(query)
        else:
            query = "SELECT * FROM ContentItem WHERE is_pub = 1 AND" \
                    " post_time + INTERVAL 24 hour >= CURRENT_TIMESTAMP ORDER BY post_time DESC"
            cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return data

# login page and redirects back to hompepage
@app.route('/login')
def login():
    if 'userEmail' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

# checks the users input of their username and password with that of the database
#if inncorrect, it sends the user an error message 
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    user_email = request.form['userEmail']
    password = request.form['password']

    cursor = conn.cursor()
    query = 'SELECT fname, lname FROM PERSON WHERE email = %s and password = SHA2(%s, 256)'
    cursor.execute(query, (user_email, password))
    data = cursor.fetchone()
    cursor.close()
    if data:
        session['userEmail'] = user_email
        return redirect(url_for('index'))
    else:
        error = "Invalid email or password"
        return render_template('login.html', error=error)

#signup page
@app.route('/register')
def register():
    if 'userEmail' in session:
        return redirect(url_for('index'))
    return render_template('signup.html')

#signup page where the user enters their first and last name and their username and password
# checks that the email isn't already in the database and sends error if it is
# if new user, saves their inputted information to the database
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    # grabs information from the forms
    fname = request.form['fname']
    lname = request.form['lname']
    user_email = request.form['userEmail']
    password = request.form['password']

    # cursor used to send queries
    cursor = conn.cursor()
    # executes query
    query = 'SELECT * FROM PERSON WHERE email = %s'
    cursor.execute(query, user_email)

    data = cursor.fetchone()
    if data:
        error = "This user already exists"
        cursor.close()
        return render_template('signup.html', error=error)
    else:
        ins = 'INSERT INTO PERSON VALUES(%s, SHA2(%s, 256), %s, %s)'
        cursor.execute(ins, (user_email, password, fname, lname))

        conn.commit()
        cursor.close()
        return render_template('index.html')


# user is allowed to post text and image pasted posts
# the user can make the post public or private
# the post is then inserted into the contentitem table in the database
# once posted, the user is redirected to home so their post is displayed at the top
@app.route('/post', methods=['GET', 'POST'])
def post():
    user_email = session['userEmail']
    cursor = conn.cursor()
    blog = request.form['content']
    pub = request.form.get('pub')
    file = request.files.getlist('image')

    destination = None
    if file:
        contentType = "image"
        # the three lines below are to create the path if it doesn't exist already
        target = app.config['UPLOAD_FOLDER']+'/images'
        if not os.path.isdir(target):
            os.makedirs(target)
        # loop through submitted images
        for file in request.files.getlist('image'):
            filename = file.filename
            destination = "/".join([target, filename])

    else:
        contentType = "text"

    pub = True if pub else False
    # This query just throws the post info we got into the contentitem table
    query = 'INSERT INTO ContentItem(email_post, file_path, content_type, item_name, is_pub) VALUES(%s, %s, %s, %s, %s)'
    cursor.execute(query, (user_email, destination, contentType, blog, pub))
    # if there was a photo, make sure we saved it
    if file:
        file.save(destination)
    # commit our changes
    conn.commit()
    cursor.close()
    return redirect(url_for('index'))


# when user logs out, they are redirected to the homepage and their session is over
@app.route('/logout')
def logout():
    session.pop('userEmail')
    return redirect('/')


#if user is logged in, they're redirected to page to add new group
#if not, theyre redirected to index
@app.route('/newGroup')
def newGroup():
    if 'userEmail' in session:
        return render_template('newGroup.html', displayNewGroup="true")
    else:
        return redirect('/')


@app.route('/share/<postid>')
def share(postid):
    if 'userEmail' in session:
        # This query is to select all the groups that we can share this post with.
        # Makes sure we don't allow you to share with groups that you've already shared the post with
        query = 'SELECT owner_email, fg_name FROM belong  WHERE email = %s AND (owner_email, fg_name) ' \
                'NOT IN (SELECT owner_email, fg_name FROM share WHERE item_id = %s)'
        cursor = conn.cursor()
        cursor.execute(query, (session['userEmail'], postid))
        data = cursor.fetchall()
        cursor.close()
        # if there are no groups left to share with, just redirect home
        if data:
            return render_template('share.html', postid=postid, data=data)

    return redirect('/')

# This route is just what commits the actual share after we select the group to share with.
@app.route('/shareAction/<owner_email>/<fg_name>/<postid>', methods=['GET', 'POST'])
def shareAction(owner_email, fg_name, postid):
    query = "INSERT INTO share VALUES (%s, %s, %s)"
    cursor = conn.cursor()
    cursor.execute(query, (owner_email, fg_name, postid))
    conn.commit()
    cursor.close()
    return redirect('/')


# making the html page for shared posts
# displays shared posts, with the tags and emojis associated with it 
@app.route('/sharedPosts')
def sharedPosts():
    if 'userEmail' in session:
        user_email = session['userEmail']
        cursor = conn.cursor()
        # Fetching all the shared posts seen by the user
        query = "SELECT * FROM Share NATURAL JOIN Belong NATURAL JOIN ContentItem WHERE email = %s ORDER BY post_time DESC"
        cursor.execute(query, user_email)
        shares = cursor.fetchall()
        cursor.rownumber = 0

        # Fetching all the emojis for emoji count of the shared posts
        query = "SELECT item_id, emoji, count(*) AS emoji_count FROM Rate GROUP BY item_id, emoji"
        cursor.execute(query)
        rate_stats = cursor.fetchall()
        cursor.rownumber = 0

        # Fetch user's rating for the posts
        query = "SELECT item_id, emoji FROM Rate WHERE email = %s"
        cursor.execute(query, (session['userEmail']))
        rate_data = cursor.fetchall()
        cursor.rownumber = 0

        # Fetch all the tags for each post
        query = "SELECT item_id, fname, lname" \
                " FROM Tag NATURAL JOIN Person WHERE email_tagged = email and status = 'True'"
        cursor.execute(query)
        tags = cursor.fetchall()

        cursor.close()
        return render_template('sharedPosts.html', shares=shares, rate_stats=rate_stats,
                               rates=rate_data, tags=tags)
    else:
        return redirect(url_for('index'))


# renders page to allow user to add people to the group that they've selected
@app.route('/addMember/<nameGroup>')
def addMember(nameGroup):
    if 'userEmail' in session:
        return render_template('newGroup.html', displayAddMember="true", dispGroupName=nameGroup)
    else:
        return redirect('/')


#displays the members of the group chosen by the user
@app.route('/removeMember/<nameGroup>', methods=['GET', 'POST'])
def removeMember(nameGroup):
    if 'userEmail' in session:
        useremail = session['userEmail']
        cursor = conn.cursor()
        # selects the members of the people who belong in the user's group
        showMemQuery = 'SELECT * FROM Belong WHERE fg_name = %s AND email != %s AND owner_email=%s'
        cursor.execute(showMemQuery, (nameGroup, useremail, useremail))
        memNames = cursor.fetchall()
        # if there are members in the group
        # nameData is an array with the first and last names of people in the group
        if memNames:
            nameData = []
            for x in range(len(memNames)):
                searchEmail = memNames[x]['email']
                # query to select first and last name of associated email
                nameQuery = 'SELECT * FROM Person WHERE email = (%s)'
                cursor.execute(nameQuery, searchEmail)
                nameData.extend(cursor.fetchall())
            cursor.close()
            return render_template('removeMember.html', memNames=memNames,
                                   nameGroup=nameGroup, nameData=nameData, user=useremail)
        else:
            # if there are no members the group will be deleted
            cursor = conn.cursor()
            # delete everyone from belong
            deleteQuery4 = 'DELETE FROM Belong WHERE owner_email = %s AND fg_name = %s'
            cursor.execute(deleteQuery4, (useremail, nameGroup))
            conn.commit()
            conn.rownumber = 0

            # delete the shared content
            deleteQuery5 = 'DELETE FROM Share WHERE owner_email = %s AND fg_name = %s'
            cursor.execute(deleteQuery5, (useremail, nameGroup))
            conn.commit()
            conn.rownumber = 0

            # delete the group
            deleteQuery6 = 'DELETE FROM FriendGroup WHERE owner_email = %s AND fg_name = %s'
            cursor.execute(deleteQuery6, (useremail, nameGroup))
            conn.commit()
            cursor.close()
            # error = "There is no one in this group. Return home to add people"
            return redirect('/')
    else:
        return redirect('/')


# removes a user from a selected group
# user can delete them - meaning they remove the person from their group
# user can sever their relationship with someone -- they remove a persoon from all of their groups
# severing also removes the user from the groups that they belonged in owned by whoever they severed relationship with
# user can also delete the group
@app.route('/deleteMember', methods=['GET', 'POST'])
def deleteMember():
    if 'userEmail' in session:
        useremail = session['userEmail']
        deletePerson = request.form['memberEmail']
        fromGroup = request.form['deleteGroup']
        # remove deletes a person from the selected group
        if request.form.get('Remove') == 'Remove':
            cursor = conn.cursor()
            # delete a person from your group
            deleteQuery1 = 'DELETE FROM Belong WHERE email = %s AND fg_name = %s AND owner_email = %s'
            cursor.execute(deleteQuery1, (deletePerson, fromGroup, useremail))
            conn.commit()
            cursor.close()
            return removeMember(fromGroup)

        # if you want to completely sever your relationship with the person
        elif request.form.get('Sever') == 'Sever':
            cursor = conn.cursor()
            # removes the person from all their groups
            deleteQuery2 = 'DELETE FROM Belong WHERE email = %s AND owner_email = %s'
            cursor.execute(deleteQuery2, (deletePerson, useremail))
            conn.commit()
            conn.rownumber = 0

            # deletes the user from all of deleted persons group to sever friendship
            deleteQuery3 = 'DELETE FROM Belong WHERE email = %s AND owner_email = %s'
            cursor.execute(deleteQuery3, (useremail, deletePerson))
            conn.commit()
            cursor.close()
            return removeMember(fromGroup)
        # deletes the whole group which also deletes the shared content 
        elif request.form.get('Delete') == 'Delete':
            cursor = conn.cursor()
            # query delete everyone from belong table
            deleteQuery4 = 'DELETE FROM Belong WHERE owner_email = %s AND fg_name = %s'
            cursor.execute(deleteQuery4, (useremail, fromGroup))
            conn.commit()
            conn.rownumber = 0

            # query deletes the shared content associated with the user's group
            deleteQuery5 = 'DELETE FROM Share WHERE owner_email = %s AND fg_name = %s'
            cursor.execute(deleteQuery5, (useremail, fromGroup))
            conn.commit()
            conn.rownumber = 0

            # deletes the group from the database
            deleteQuery6 = 'DELETE FROM FriendGroup WHERE owner_email = %s AND fg_name = %s'
            cursor.execute(deleteQuery6, (useremail, fromGroup))
            conn.commit()
            cursor.close()
            return redirect('/')

        else:
            return removeMember(fromGroup)
    else:
        return redirect('/')


# allows user to add new group that they own
# the user can only create groups that don't already exist
@app.route('/createNewGroup', methods=['GET', 'POST'])
def createNewGroup():
    user_email = session['userEmail']
    groupName = request.form['groupName']
    groupDesc = request.form['groupDesc']

    cursor = conn.cursor()
    # the query checks is the user already owns a group with the inputted name
    checkQuery = 'SELECT fg_name FROM FriendGroup WHERE owner_email = %s AND fg_name = %s'
    cursor.execute(checkQuery, (user_email, groupName))
    groupData = cursor.fetchone()
    # if group exits, send error
    if groupData:
        cursor.rownumber = 0
        error = "You have already created a group with this name"
        cursor.close()
        return render_template('newGroup.html', displayNewGroup="true", error=error)
    # the group doesn't exist so the group is created with the user as the owner
    # the owner is automatically put into the Belong table so they are a member of the group they own
    else:
        newGroupQuery = 'INSERT INTO FriendGroup(owner_email, fg_name, description) VALUES (%s,%s,%s)'
        cursor.execute(newGroupQuery, (user_email, groupName, groupDesc))
        conn.commit()
        cursor.rownumber = 0
        addSelf = 'INSERT INTO Belong(email,owner_email,fg_name) VALUES (%s,%s,%s)'
        cursor.execute(addSelf,(user_email,user_email,groupName))
        conn.commit()
        cursor.close()
        # allows the user to add members to the group they just created
        if request.form.get('AddMember') == 'AddMember':
            return render_template('newGroup.html', displayAddMember="true", dispGroupName=groupName)
    cursor.close()
    return redirect(url_for('index'))


# user is allowed to add members to whichever group they selected
# user adds by inputting the first and last name of the user
# if is more than one user with the same name, the email is required
@app.route('/addNewMember', methods=['GET', 'POST'])
def addNewMember():
    user_email = session['userEmail']
    groupName = request.form['groupName']
    newMemberF = request.form['newMemFname']
    newMemberL = request.form['newMemLname']
    duplicateTest = request.form['duplicateTest']

    cursor = conn.cursor()
    # check that the member you're adding exists
    checkExist = 'SELECT * FROM Person WHERE fname = %s AND lname = %s'
    cursor.execute(checkExist, (newMemberF, newMemberL))
    memExist = cursor.fetchall()
    # if there is more than one user, an email is required
    if duplicateTest == "True":
        cursor.rownumber = 0
        newMemEmail = request.form['newMemEmail']
        # check if they're already in your group
        checkInQuery = 'SELECT * FROM Belong WHERE owner_email = %s AND fg_name = %s AND email = %s'
        cursor.execute(checkInQuery, (user_email, groupName, newMemEmail))
        memExistData2 = cursor.fetchall()
        # if the member already in user's group, the user retrieves an error message
        if memExistData2:
            cursor.close()
            error = "This person is already in your group"
            return render_template('newGroup.html', displayAddMember="true", dispGroupName=groupName, error=error)
        # if the user exists and isn't in the group, they are added
        else:
            cursor.rownumber = 0
            addMemQuery2 = 'INSERT INTO Belong (email, owner_email, fg_name) VALUES (%s, %s, %s)'
            cursor.execute(addMemQuery2, (newMemEmail, user_email, groupName))
            message = "you successfully added a member"
            conn.commit()
            cursor.close()
            return render_template('newGroup.html', displayAddMember="true", dispGroupName=groupName, message=message)
    
    #if we don't know if there are duplicates, we have to check the how many people have the same name
    else:
        # if there is only one person with the inputted name
        if len(memExist) == 1:
            cursor.rownumber = 0
            # if the member exists - check if they're already in your group
            newMember = memExist[0]['email']
            checkMemQuery = 'SELECT * FROM Belong WHERE owner_email = %s AND fg_name = %s AND email = %s'
            cursor.execute(checkMemQuery, (user_email, groupName, newMember))
            memExistData = cursor.fetchone()
            # if they're already in your group send an error message
            if memExistData:
                error = "This person is already in your group"
                cursor.close()
                return render_template('newGroup.html', displayAddMember="true", dispGroupName=groupName,
                                       error=error)
            else:
                # if the member exists and is not in group, add them to your group
                cursor.rownumber = 0
                addMemberQuery = 'INSERT INTO Belong (email, owner_email, fg_name) VALUES (%s, %s, %s)'
                cursor.execute(addMemberQuery, (newMember, user_email, groupName))
                message = "You successfully added a member"
                conn.commit()
                cursor.close()
                return render_template('newGroup.html', displayAddMember="true", dispGroupName=groupName,
                                       message=message)
        # if the user doesn't exist, an error message is sent
        elif len(memExist) == 0:
            error = "This person does not exist, try another name"
            cursor.close()
            return render_template('newGroup.html', displayAddMember="true", dispGroupName=groupName,
                                   error=error)
        # if the query returns something longer than one, that means there are multiple people with the same name
        # will render the page with an error message and a list of the emails associated with that name
        # the user must enter the correct email to add the person
        else:
            error = "There are multiple people with the same name. Enter the correct email and to move on"
            return render_template('newGroup.html', displayAddMember="true", dispGroupName=groupName, error=error,
                                   duplicate="true", memExist=memExist)


# Retrieving what post a user rated on and with what emoji
# current page (whether it is index or shared posts) will have the updated emoji after being redirected
@app.route('/rate', methods=['GET', 'POST'])
def rate():
    user_email = session['userEmail']
    cursor = conn.cursor()
    page = 'index'
    item = list(request.form.keys())[0]

    # if the user is rating on the shared page, make page = sharedPosts
    # otherwise, it is already initialized to index page
    if 'share' in item:
        page = 'sharedPosts'
    cursor.rownumber = 0
    # retrieve the item_id of what is being rated 
    rate_id = int(item.split('te')[-1])

    # determine whether the rating already exists
    query = "SELECT * FROM Rate WHERE item_id = %s AND email = %s"
    cursor.execute(query, (rate_id, user_email))
    rate_exist = cursor.fetchone()
    cursor.rownumber = 0

    # if rating already exists, uopdate the row 
    if rate_exist:
        query = "UPDATE Rate SET rate_time = CURRENT_TIMESTAMP, emoji = %s WHERE item_id = %s AND email = %s"
        cursor.execute(query, (request.form[item], rate_id, user_email))
    # otherwise, insert a new row for the rating
    else:
        query = "INSERT INTO Rate (email, item_id, rate_time, emoji) VALUES (%s, %s, CURRENT_TIMESTAMP, %s)"
        cursor.execute(query, (user_email, rate_id, request.form[item]))
    conn.commit()
    cursor.close()
    return redirect(url_for(page))


# displaying pending tag requests
@app.route('/pendingTags', methods=['GET', 'POST'])
def pending_tag():
    user_email = session['userEmail']
    cursor = conn.cursor()
    # find all tag requests where status = false to display on tag page
    query = "SELECT * FROM Tag NATURAL JOIN ContentItem WHERE email_tagged = %s AND status = 'False'"
    cursor.execute(query, user_email)
    pends = cursor.fetchall()
    cursor.close()

    return render_template('pendingTags.html', pendings=pends)


# confirming if user accepted or rejected tag
@app.route('/tagAuth', methods=['GET', 'POST'])
def tag_auth():
    user_email = session['userEmail']
    cursor = conn.cursor()
    item = list(request.form.keys())[0]
    lst = item.split('@nyu.edu')
    tagger, item_id = lst[0], int(lst[1])
    status = request.form[item]

    # if user accepted tag, update row in table to be true 
    if status == "Accept":
        query = "UPDATE Tag SET status = 'True' WHERE email_tagger = %s" \
                " AND email_tagged = %s AND item_id = %s"
    # otherwise, delete the row from the table
    else:
        query = "DELETE FROM Tag WHERE email_tagger = %s" \
                "AND email_tagged = %s AND item_id = %s"
    cursor.execute(query, (tagger+'@nyu.edu', user_email, item_id))
    conn.commit()
    cursor.close()
    return redirect(url_for('pending_tag'))


# tagging a user 
# if a user tags him/herself, the tag is automatically accepted
# if a user tags another user who cannot view the post, generate an error and display on home
# if a user already tagged the user, display an error saying that user is already tagged for post
@app.route('/tag', methods=['GET', 'POST'])
def tag():
    user_email = session['userEmail']
    cursor = conn.cursor()
    item = list(request.form.keys())[0]
    taggee = request.form[item]
    cursor.rownumber = 0
    tag_id = int(item.split('d')[-1])

    # check to see if email to be tagged exist
    query = "SELECT * FROM Person WHERE email = %s"
    cursor.execute(query, taggee)
    tag_email_exist = cursor.fetchone()

    # generate error if email does not exist on home page
    if not tag_email_exist:
        error = "This email has not been registered."
        flash(error)
        return redirect(url_for('index'))

    # check to see if the tag already exists 
    query = "SELECT * FROM Tag WHERE item_id = %s AND email_tagger = %s AND email_tagged = %s"
    cursor.execute(query, (tag_id, user_email, taggee))
    tag_exist = cursor.fetchone()
    cursor.rownumber = 0

    # if tag does not exist
    if not tag_exist:
        # check to see if the content is public 
        query = "SELECT is_pub FROM ContentItem WHERE item_id = %s"
        cursor.execute(query, tag_id)
        is_public = cursor.fetchone()
        cursor.rownumber = 0
        if is_public['is_pub']:
            status = "False"

            # if tagging yourself, automatically accept the tag
            if user_email == taggee:
                status = "True"

            # insert the pending/accepted tag into the tag table
            query = "INSERT INTO Tag(email_tagged, email_tagger, item_id, status) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (taggee, user_email, tag_id, status))

        # if it's a private post, confirm that you are tagging someone who you already shared the post with 
        else:
            query = "SELECT * FROM Belong NATURAL JOIN Share WHERE email = %s AND item_id = %s"
            cursor.execute(query, (taggee, tag_id))
            is_shared = cursor.fetchone()
            # if post is shared, insert row into table 
            if is_shared:
                query = "INSERT INTO Tag(email_tagged, email_tagger, item_id, status) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (taggee, user_email, tag_id, "False"))
            # otherwise, all cases failed
            # generate the error to the home page
            else:
                error = "Tag request cannot be done."
                flash(error)
                return redirect(url_for('index'))
    # generate error saying that email is already tagged 
    else:
        error = "You already tagged " + taggee + " for this post!"
        flash(error)
        return redirect(url_for('index'))
    conn.commit()
    cursor.close()
    return redirect(url_for('index'))


# selects all the comments and the emails associated with the comment for a post 
# selecting the post to display on the page
# when user selects a post to comment on, they see the post and the comments previously done
@app.route('/comments/<postid>', methods=['GET', 'POST'])
def comments(postid):
    if 'userEmail' in session:
        # just grabs all the comments linked to this
        query = 'SELECT content, commentor_email FROM comments WHERE item_id = %s'
        cursor = conn.cursor()
        cursor.execute(query, postid)
        data = cursor.fetchall()

        cursor.rownumber = 0

        query2 = 'SELECT * FROM ContentItem WHERE item_id = %s'
        cursor.execute(query2, postid)
        main_post = cursor.fetchone()
        cursor.close()
        return render_template('comments.html', data=data, post=main_post, postid=postid)


# if user is logged in, their comment is added to the comment table and displayed on the page
# comments are unique to a post
@app.route('/commentsubmit/<postid>', methods=['GET', 'POST'])
def commentsubmit(postid):
    if 'userEmail' in session:
        comment_content = request.form['content']

        query = 'INSERT INTO comments (content, commentor_email, item_id) VALUES (%s, %s, %s)'
        cursor = conn.cursor()
        cursor.execute(query, (comment_content, session['userEmail'], postid))
        conn.commit()
        cursor.close()
    return redirect(url_for('comments', postid=postid))


if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug=True)
