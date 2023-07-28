from flask import Flask, render_template, request, url_for, redirect, flash
from flask_bootstrap import Bootstrap
from sqlalchemy import desc
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from dotenv import load_dotenv
from pathlib import Path
import requests
import random
from send_email import SendEmail
import datetime as dt
from datetime import datetime, timedelta
dotenv_path = Path("flask.env")
load_dotenv(dotenv_path=dotenv_path)

def generate_random_password():
    letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
               'u', 'v', 'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N',
               'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
    numbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    symbols = ['!', '#', '$', '%', '&', '(', ')', '*', '+']

    nr_letters = random.randint(8, 10)
    nr_symbols = random.randint(2, 4)
    nr_numbers = random.randint(2, 4)
    password = ""
    password_list = []

    for char in range(nr_letters):
        password_list.append(random.choice(letters))

    for char in range(nr_symbols):
        password_list += random.choice(symbols)

    for char in range(nr_numbers):
        password_list += random.choice(numbers)

    random.shuffle(password_list)

    for char in password_list:
        password += char

    return password

MOVIE_DB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
MOVIE_DB_API_KEY = "d5023044e77f02082b7f229b7a78a54f"
MOVIE_DB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-goes-here'
Bootstrap(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.app_context().push()
login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    average_rating = db.Column(db.Float, nullable=True)
    number_of_reviews = db.Column(db.Integer, nullable=True)
    img_url = db.Column(db.String(250), nullable=False)
    reviews = db.relationship('Reviews', backref='movie')


class Reviews(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    review = db.Column(db.String(250), nullable=True)
    rating = db.Column(db.Float, nullable=True)
    current_time = db.Column(db.String(50), nullable=False)
    current_user = db.Column(db.String(50), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'))


@app.context_processor
def add_imports():
    return dict(datetime=datetime, timedelta=timedelta)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


db.create_all()


@app.route('/', methods=["POST", "GET"])
def sign_in():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if not user or user.password != password:
            flash("Email or password incorrect. Please try again.")
            return redirect(url_for('sign_in'))
        else:
            login_user(user)
            return redirect(url_for('home'))

    return render_template("sign_in.html")

@app.route('/forgot-password', methods=["POST", "GET"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        random_password = generate_random_password()
        password_to_update = User.query.filter_by(email=email).first()
        if not password_to_update:
            flash("Email does not exist")
            return redirect(url_for('forgot_password'))
        else:
            password_to_update.password = random_password
            db.session.commit()
            SendEmail(email, random_password).send_email()
            flash("Check your inbox/spam")
            return redirect(url_for('forgot_password'))
    return render_template("password.html")

@app.route('/create-account', methods=["POST", "GET"])
def create_account():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        repeat_password = request.form["repeat_password"]
        if User.query.filter_by(email=email).first():
            flash("Email already in use!")
            return redirect(url_for('create_account'))

        new_user = User(email=email, password=password)

        if repeat_password != password:
            flash("Passwords do not match.")
            return redirect(url_for('create_account'))
        else:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('sign_in'))

    return render_template("account.html")

@app.route('/change-password', methods=["POST", "GET"])
@login_required
def change_password():
    if request.method == "POST":
        new_password = request.form.get('new_password')
        new_password_to_update = User.query.filter_by(email=current_user.email).first()
        new_password_to_update.password = new_password
        db.session.commit()
        flash("Password changed!")
    return render_template("change-password.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('sign_in'))

@app.route('/movies')
@login_required
def home():
    all_movies = Movie.query.all()
    rating_id = request.args.get("id_rating")
    number_id = request.args.get("id_number")
    if rating_id:
        all_movies = Movie.query.order_by(desc(Movie.average_rating)).all()
    elif number_id:
        all_movies = Movie.query.order_by(desc(Movie.number_of_reviews)).all()
    return render_template("index.html", movies=all_movies)

@app.route('/reviews/')
@login_required
def reviews():
    user = User.query.filter_by(email=current_user.email).first()
    movie_id = request.args.get("id")
    movie = Movie.query.filter_by(id=movie_id).all()
    movie_number_reviews = Movie.query.filter_by(id=movie_id).first()
    review = Reviews.query.filter_by(movie_id=movie_id).all()
    return render_template("reviews.html", movie_id=movie_id, movies=movie, reviews=review, user=user.email,
                           number_of_reviews=movie_number_reviews.number_of_reviews)


@app.route('/add-review/', methods=["POST", "GET"])
@login_required
def add_review():
    def is_float(string):
        try:
            float(string)
            return True
        except ValueError:
            return False
    movie_id = request.args.get("id")
    movie = Movie.query.filter_by(id=movie_id).first()
    review = Reviews.query.filter_by(movie_id=movie_id).all()
    users = []
    for user in review:
        users.append(user.current_user)
    all_movies = Movie.query.all()
    if request.method == "POST":
        user = User.query.filter_by(email=current_user.email).first()
        rating = request.form["add-rating"]
        review = request.form["add-review"]
        current_time = dt.datetime.now()
        current_date = current_time.strftime('%Y-%m-%d')
        current_hour = current_time.strftime('%H:%M')
        time = f"{current_date} {current_hour}"
        if user.email in users:
            flash("You already left a review")
        elif not is_float(rating):
            flash("Rating must be a number between 1 and 10")
            return redirect(url_for('add_review', id=movie_id))
        elif is_float(rating) and (float(rating) < 1 or float(rating) > 10):
            flash("Rating must be a number between 1 and 10")
            return redirect(url_for('add_review', id=movie_id))
        else:
            comment = Reviews(review=review, rating=rating, current_time=time, current_user=user.email, movie=movie)
            db.session.add(comment)
            db.session.commit()
            for movie in all_movies:
                sum_rating = 0
                reviews = Reviews.query.filter_by(movie_id=movie.id).all()
                number_of_reviews = len(reviews)
                for review in reviews:
                    sum_rating = sum_rating + review.rating
                if sum_rating != 0:
                    average_rating = sum_rating / number_of_reviews
                else:
                    average_rating = 0
                average_rating_update = Movie.query.get(movie.id)
                average_rating_update.average_rating = round(average_rating, 1)
                average_rating_update.number_of_reviews = number_of_reviews
                db.session.commit()
            return redirect(url_for('reviews', id=movie_id))
    return render_template("add_review.html", movie_id=movie_id)

@app.route('/add', methods=["POST", "GET"])
@login_required
def add_movie():
    if request.method == "POST":
        movie_title = request.form["add-movie"]
        response = requests.get(MOVIE_DB_SEARCH_URL, params={"api_key": MOVIE_DB_API_KEY, "query": movie_title})
        data = response.json()["results"]
        return render_template("select.html", list_of_movies=data)
    return render_template("add_movie.html")


@app.route("/find", methods=["POST", "GET"])
@login_required
def find_movie():
    movie_api_id = request.args.get("id")
    if movie_api_id:
        response = requests.get(f"https://api.themoviedb.org/3/movie/{movie_api_id}?api_key={MOVIE_DB_API_KEY}&language=en-US")
        data = response.json()
        movies = Movie.query.all()
        titles = []
        for movie in movies:
            titles.append(movie.title)
        new_movie = Movie(
            title=data["title"],
            year=data["release_date"].split("-")[0],
            img_url=f"{MOVIE_DB_IMAGE_URL}{data['poster_path']}",
            description=data["overview"]
        )
        if data["title"] in titles:
            movie = Movie.query.filter_by(title=data["title"]).first()
            movie_id = movie.id
            return redirect(url_for("reviews", id=movie_id))
        else:
            db.session.add(new_movie)
            db.session.commit()
            movie = Movie.query.filter_by(title=data["title"]).first()
            movie_id = movie.id
            average_rating_update = Movie.query.get(movie.id)
            if average_rating_update.average_rating is None or average_rating_update.number_of_reviews is None:
                average_rating_update.average_rating = 0
                average_rating_update.number_of_reviews = 0
                db.session.commit()
            return redirect(url_for("reviews", id=movie_id))

@app.route("/delete", methods=["POST", "GET"])
@login_required
def delete():
    movie_id = request.args.get("id")
    review_id = request.args.get("review_id")
    review_to_delete = Reviews.query.get(review_id)
    db.session.delete(review_to_delete)
    db.session.commit()
    all_movies = Movie.query.all()
    for movie in all_movies:
        sum_rating = 0
        reviews = Reviews.query.filter_by(movie_id=movie.id).all()
        number_of_reviews = len(reviews)
        for review in reviews:
            sum_rating = sum_rating + review.rating
        if sum_rating != 0:
            average_rating = sum_rating / number_of_reviews
        else:
            average_rating = 0
        average_rating_update = Movie.query.get(movie.id)
        average_rating_update.average_rating = round(average_rating, 1)
        average_rating_update.number_of_reviews = number_of_reviews
        db.session.commit()
    return redirect(url_for("reviews", id=movie_id))


if __name__ == "__main__":
    app.run(debug=True)
