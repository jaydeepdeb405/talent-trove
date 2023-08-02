from flask import Flask, jsonify, request
from nlp_search import candidate_search, resume_search
from data_service import *
import threading
import os

# Initialize Flask & SQLAlchemy
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)


@app.route('/refresh/<table>', defaults={'primary_key': None}, methods=['GET'])
@app.route('/refresh/<table>/<primary_key>', methods=['GET'])
def load_from_servicenow(table, primary_key):
    try:
        if table == 'candidate':
            threading.Thread(target=refresh_candidates, args=[app.app_context(), primary_key]).start()
            return jsonify({'success': True, 'message': 'Operation executed in background'})
        else:
            return jsonify({'success': False, 'message': f"Invalid table name {table}"})
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error: {e}"})


@app.route('/search', methods=['GET'])
def search_candidate():
    args = request.args
    search_text = args.get('search_text')
    max_results = request.args.get('max_results')
    max_results = int(max_results) if max_results else 5
    try:
        if search_text:
            result = candidate_search(search_text, max_results)
            return jsonify({'success': True if result else False, 'result': result})
        else:
            return jsonify({'success': False, 'message': 'Mandatory parameter "search_text"'})
    except Exception as e:
        return jsonify({'success': False, 'result': {}, 'message': f"Error: {e}"})


# Pass Job details as Request body - API returns scores for all applied candidates
# Pass Job details as Request body & Email as query param - API returns scores for single job application
# Pass Job details as Request body & search_all as true - API returns recommendations by looksing through all resumes in system
@app.route('/score', methods=['POST'])
def get_candidate_similarity_score():
    args = request.get_json()
    job_description = args.get('job_description')
    job_number = args.get('job_number')
    email_param = request.args.get('email')
    search_all = request.args.get('search_all')
    max_results = request.args.get('max_results')
    max_results = int(max_results) if max_results else 10
    try:
        if search_all == 'true':
            email_list = []
        else:
            email_list = [email_param] if email_param else get_job_applications(job_number)
        result = resume_search(job_description, email_list, max_results)
        return jsonify({'success': True if result else False, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'result': {}, 'message': f"Error: {e}"})


@app.route('/db/<table>', defaults={'primary_key': None}, methods=['GET', 'DELETE'])
@app.route('/db/<table>/<primary_key>', methods=['GET', 'DELETE'])
def perform_crud(table, primary_key):
    if request.method == 'GET':
        try:
            if table == 'candidate':
                records = get_candidates_from_db(primary_key)
                return jsonify({'success': True, 'records': records, 'length': len(records)})
            else:
                return jsonify({'success': False, 'records': [], 'length': 0, 'message': f"Invalid table name {table}"})
        except Exception as e:
            return jsonify({'success': False, 'records': [], 'length': 0, 'message': f"Error: {e}"})
    elif request.method == 'DELETE':
        try:
            if table == 'candidate':
                num_rows_deleted = delete_candidates_from_db(primary_key)
                return jsonify({'success': True, 'delete_count': num_rows_deleted})
            else:
                num_rows_deleted = 0
                return jsonify(
                    {'success': False, 'delete_count': num_rows_deleted, 'message': f"Invalid table name {table}"})
        except Exception as e:
            return jsonify({'success': False, 'delete_count': 0, 'message': f"Error: {e}"})


if __name__ == '__main__':
    app.run()
