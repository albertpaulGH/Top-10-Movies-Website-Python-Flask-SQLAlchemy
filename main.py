# Flask Server for 'Top 10 Movies Website'

import os
from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired
import requests

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///movies.db"

Bootstrap5(app)


# CREATE DB
class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CREATE TABLE
class Movies(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(250), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String(250), nullable=True)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)


with app.app_context():
    db.create_all()


# Creating a child class of class FlaskForm for WTForms
class MovieEdit(FlaskForm):
    rating = FloatField(label="New Rating", validators=[DataRequired()])
    review = StringField(label="New Review", validators=[DataRequired()])
    submit = SubmitField(label="Submit")


# Creating a child class of class FlaskForm for WTForms
class AddMovie(FlaskForm):
    movie = StringField(label="Movie Title", validators=[DataRequired()])
    submit = SubmitField(label="Add Movie")


# Flask routes

@app.route("/")
def home():
    with app.app_context():
        result = db.session.execute(db.select(Movies).order_by(Movies.rating))
        all_movies = result.scalars().all()

    for i in range(len(all_movies)):
        with app.app_context():
            movie_ranking_update = db.session.execute(
                db.select(Movies).where(Movies.title == all_movies[i].title)).scalar()
            movie_ranking_update.ranking = len(all_movies) - i
            db.session.commit()

    with app.app_context():
        result = db.session.execute(db.select(Movies).order_by(Movies.rating))
        all_movies = result.scalars().all()

    return render_template("index.html", movies=all_movies)


@app.route("/edit", methods=["GET", "POST"])
def edit():
    form = MovieEdit()
    movie_id = request.args.get("movie_id")
    if form.validate_on_submit():
        with app.app_context():
            movie_to_update = db.session.execute(db.select(Movies).where(Movies.id == movie_id)).scalar()
            movie_to_update.rating = form.rating.data
            movie_to_update.review = form.review.data
            db.session.commit()
        return redirect(url_for("home"))

    return render_template("edit.html", form=form)


@app.route("/delete")
def delete():
    movie_id = request.args.get("movie_id")
    with app.app_context():
        movie_to_delete = db.session.execute(db.select(Movies).where(Movies.id == movie_id)).scalar()
        db.session.delete(movie_to_delete)
        db.session.commit()

    return redirect(url_for("home"))


@app.route("/add", methods=["GET", "POST"])
def add():
    with app.app_context():
        result = db.session.execute(db.select(Movies).order_by(Movies.rating))
        all_movies = result.scalars().all()

    if len(all_movies) != 10:
        form = AddMovie()
        if form.validate_on_submit():
            movie_name = form.movie.data
            url = f"https://api.themoviedb.org/3/search/movie?query={movie_name}"
            headers = {
                "accept": "application/json",
                "Authorization": os.environ["ACCESS_TOKEN"]
            }

            response = requests.get(url, headers=headers)
            movies_to_select = response.json()["results"]
            return render_template("select.html", movies=movies_to_select)

        return render_template("add.html", form=form, flag=True)
    else:
        return render_template("add.html", status="10 movies already listed, remove one to add a new movie", flag=False)


@app.route("/selected-movie", methods=["GET", "POST"])
def selected_movie():
    movie_id = request.args.get("movie_id")
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"

    headers = {
        "accept": "application/json",
        "Authorization": os.environ["ACCESS_TOKEN"]
    }

    response = requests.get(url, headers=headers)

    movie = response.json()
    with app.app_context():
        new_movie = Movies(
            title=movie["original_title"],
            year=movie["release_date"],
            description=movie["overview"],
            rating=None,
            ranking=None,
            review=None,
            img_url=f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
        )
        db.session.add(new_movie)
        db.session.commit()

    with app.app_context():
        result = db.session.execute(db.select(Movies).where(Movies.title == movie["original_title"]))
        new_movie_id = result.scalar().id

    return redirect(url_for("edit", movie_id=new_movie_id))


if __name__ == "__main__":
    app.run(debug=True)
