from flask import Flask, render_template, request, session
from flask_session import Session
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = '3d6f45a5fc12445dbac2f59c3b6c7cb1'

# Flask-Session configuration
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
Session(app)

# TMDb API details
API_KEY = '3eeacf21108e1176964b48d1bd03855d'
BASE_URL = 'https://api.themoviedb.org/3'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        genre = request.form.get('genre')
        keywords = request.form.get('keywords')
        liked_movies = request.form.get('liked_movies')

        genre_id = get_genre_id(genre)
        movies = fetch_movies(genre_id, keywords, liked_movies)

        if movies:
            session['movies'] = movies
            session.modified = True
            suggested_movies = movies[:3]
            return render_template('index.html', movies=suggested_movies)
        else:
            return render_template('index.html', error="No movies found. Try again!")

    return render_template('index.html')

@app.route('/next', methods=['POST'])
def next_movies():
    # Get the remaining movies from session
    movies = session.get('movies', [])

    # Check if no movies are available (session expired or empty)
    if not movies:
        return render_template('index.html', error="Session expired or no more movies. Please start again!")

    # Slice the next 3 movies (remove the first 3 movies)
    next_movies = movies[3:]  # Get the remaining movies after the first 3
    session['movies'] = next_movies  # Update the session with remaining movies
    session.modified = True  # Mark session as modified

    if not next_movies:
        return render_template('index.html', error="No more movies left! Please start again!")

    # Pick the next 3 movies
    suggested_movies = next_movies[:3]

    return render_template('index.html', movies=suggested_movies)

def get_genre_id(genre):
    genre_map = {
        'Action': 28,
        'Comedy': 35,
        'Horror': 27,
        'Romance': 10749,
        'Sci-Fi': 878,
    }
    return genre_map.get(genre, None)

def fetch_movies(genre_id, keywords, liked_movies):
    movies = []

    # If liked_movies are provided, fetch recommendations for each liked movie
    if liked_movies:
        liked_movies_list = liked_movies.split(',')
        for movie_name in liked_movies_list:
            movie_id = get_movie_id_by_name(movie_name.strip())
            if movie_id:
                recommended_movies = fetch_movie_recommendations(movie_id, genre_id)
                movies.extend(recommended_movies)

    # If no movies were found from liked_movies, fall back to search by keywords
    if not movies and keywords:
        url = f'{BASE_URL}/search/movie'
        params = {
            'api_key': API_KEY,
            'query': keywords,  # This is the key parameter to search by keywords
            'sort_by': 'popularity.desc',
            'page': 1,
        }

        if genre_id:
            params['with_genres'] = genre_id  # Apply genre filter if available

        response = requests.get(url, params=params)

        if response.status_code == 200:
            movies = response.json().get('results', [])
            # Filter out unreleased movies
            today = datetime.today().strftime('%Y-%m-%d')
            movies = [movie for movie in movies if movie.get('release_date', '') <= today]

    # Filter out unreleased movies and return unique results
    today = datetime.today().strftime('%Y-%m-%d')
    movies = [movie for movie in movies if movie.get('release_date', '') <= today]
    return list({movie['id']: movie for movie in movies}.values())

def get_movie_id_by_name(movie_name):
    # Search for the movie by name and get its ID
    url = f'{BASE_URL}/search/movie'
    params = {
        'api_key': API_KEY,
        'query': movie_name,
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        results = response.json().get('results', [])
        if results:
            return results[0]['id']
    return None

def fetch_movie_recommendations(movie_id, genre_id=None):
    # Fetch movie recommendations using the movie ID and genre filter
    url = f'{BASE_URL}/movie/{movie_id}/recommendations'
    params = {
        'api_key': API_KEY,
        'page': 1,
    }

    # If genre_id is provided, add it to filter recommendations by genre
    if genre_id:
        params['with_genres'] = genre_id

    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json().get('results', [])
    return []

if __name__ == '__main__':
    app.run(debug=True)
