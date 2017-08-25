from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)
app.jinja_env.add_extension("pypugjs.ext.jinja.PyPugJSExtension")

# mySQL config
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "myflaskapp"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
mysql = MySQL(app)

@app.route("/")
def index():
	return render_template("home.pug")

@app.route("/about")
def about():
	return render_template("about.pug")

@app.route("/articles")
def articles():
	cur = mysql.connection.cursor()
	result = cur.execute("SELECT * FROM articles")
	articles = cur.fetchall()
	if result > 0:
		return render_template("articles.pug", articles = articles)
	else:
		return render_template("articles.pug")
	cur.close()

@app.route("/articles/<string:id>/")
def article(id):
	cur = mysql.connection.cursor()
	result = cur.execute(f"SELECT * FROM articles WHERE id = '{id}'")
	article = cur.fetchone()
	return render_template("article.pug", article = article)
	cur.close()

class RegisterForm(Form):
	name = StringField("Name", [validators.Length(min=1, max=50)])
	username = StringField("Username", [validators.Length(min=4, max=25)])
	email = StringField("Email", [validators.Length(min=6, max=50)])
	password = PasswordField("Password", [
		validators.DataRequired(),
		validators.EqualTo("confirm", message="Passwords do not match")
	])
	confirm = PasswordField("Confirm password")

@app.route("/register", methods=["GET", "POST"])
def register():
	form = RegisterForm(request.form)
	if request.method == "POST" and form.validate():
		name = form.name.data
		email = form.email.data
		username = form.username.data
		password = sha256_crypt.encrypt(str(form.password.data))

		cur = mysql.connection.cursor()
		cur.execute(f"INSERT INTO users (name, email, username, password) VALUES ('{name}', '{email}', '{username}', '{password}')")
		mysql.connection.commit()
		cur.close()
		
		flash("You are now registered")
		return redirect(url_for("login"))
	return render_template("register.pug", form = form)

@app.route("/login", methods=["GET", "POST"])
def login():
	if request.method == "POST":
		username = request.form["username"]
		password_candidate = request.form["password"]

		cur = mysql.connection.cursor()
		result = cur.execute(f"SELECT * FROM users WHERE username = '{username}'")
		if result > 0:
			data = cur.fetchone()
			password = data["password"]
			name = data["name"]
			if sha256_crypt.verify(password_candidate, password):
				session["logged_in"] = True
				session["username"] = username
				session["name"] = name
				flash(f"Welcome, {name}")
				return redirect(url_for("dashboard"))
			else:
				flash("Wrong password")
		else:
			flash("No user found")
		cur.close()
	return render_template("login.pug")

def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if "logged_in" in session:
			return f(*args, **kwargs)
		else:
			flash("Unauthorized, please log in")
			return redirect(url_for("login"))
	return wrap

@app.route("/logout")
@is_logged_in
def logout():
	session.clear()
	flash("You have been logged out")
	return redirect(url_for("index"))

@app.route("/dashboard")
@is_logged_in
def dashboard():
	cur = mysql.connection.cursor()
	result = cur.execute("SELECT * FROM articles")
	articles = cur.fetchall()
	if result > 0:
		return render_template("dashboard.pug", articles = articles)
	else:
		return render_template("dashboard.pug")
	cur.close()

class ArticleForm(Form):
	title = StringField("Title", [validators.Length(min=1, max=200)])
	body = TextAreaField("Body", [validators.Length(min=30)])

@app.route("/add_article", methods=["GET", "POST"])
@is_logged_in
def add_article():
	form = ArticleForm(request.form)
	if request.method == "POST" and form.validate():
		title = form.title.data
		body = form.body.data

		cur = mysql.connection.cursor()
		cur.execute(f"INSERT INTO articles (title, body, author) VALUES ('{title}', '{body}', '{session['username']}')")
		mysql.connection.commit()
		cur.close()

		flash("Article created")
		return redirect(url_for("dashboard"))
	return render_template("add_article.pug", form = form)

@app.route("/edit_article/<string:id>", methods=["GET", "POST"])
@is_logged_in
def edit_article(id):
	cur = mysql.connection.cursor()
	result = cur.execute(f"SELECT * FROM articles WHERE id = '{id}'")
	article = cur.fetchone()

	form = ArticleForm(request.form)
	form.title.data = article['title']
	form.body.data = article['body']

	if request.method == "POST" and form.validate():
		title = request.form["title"]
		body = request.form["body"]

		cur = mysql.connection.cursor()
		cur.execute(f"UPDATE articles SET title = '{title}', body = '{body}' WHERE id = '{id}'")
		mysql.connection.commit()
		cur.close()

		flash("Article updated")
		return redirect(url_for("dashboard"))
	return render_template("edit_article.pug", form = form)

@app.route("/delete_article", methods=["POST"])
@is_logged_in
def delete_article():
	id = request.form["id"]
	cur = mysql.connection.cursor()
	cur.execute(f"DELETE FROM articles WHERE id = '{id}'")
	mysql.connection.commit()
	cur.close()

	flash("Article deleted")
	return redirect(url_for("dashboard"))


if __name__ == "__main__":
	app.secret_key = "secret123"
	app.jinja_env.auto_reload = True
	app.config['TEMPLATES_AUTO_RELOAD'] = True
	app.run(debug=True)
