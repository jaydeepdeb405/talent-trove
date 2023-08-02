from models import Candidate
from extensions import db
import os
import json
import requests
import shutil
from requests.auth import HTTPBasicAuth


# Constants
snow_instance_uri = os.environ.get('TALENT_TROVE_SNOW_URL')
snow_username = os.environ.get('TALENT_TROVE_SNOW_USERNAME')
snow_password = os.environ.get('TALENT_TROVE_SNOW_PASSWORD')


root_dir_path = os.environ.get('TALENT_TROVE_ROOT_DIR_PATH')
resume_root_path = f"{root_dir_path}/TalentTrove/Resumes"
job_desc_root_path = f"{root_dir_path}/TalentTrove/Job description"


def get_job_applications(job_number_param):
    url = f"{snow_instance_uri}/api/x_snc_talenttrove/talenttrove/app_candidates?job_number={job_number_param}"
    response = requests.get(
        url=url,
        auth=HTTPBasicAuth(snow_username, snow_password)
    )
    response_json = response.json()
    candidate_list = response_json.get('result')
    return candidate_list


def refresh_candidates(app_context, email_param=None):
    app_context.push()
    updated_candidates = []
    if not email_param:
        url = f"{snow_instance_uri}/api/x_snc_talenttrove/talenttrove/candidates"
    else:
        url = f"{snow_instance_uri}/api/x_snc_talenttrove/talenttrove/candidates?email={email_param}"
    response = requests.get(
        url=url,
        auth=HTTPBasicAuth(snow_username, snow_password)
    )
    response_json = response.json()
    candidate_list = response_json.get('result')
    if candidate_list and len(candidate_list) > 0:
        db.create_all()
        for candidate in candidate_list:
            email = candidate.get('email')
            resume_id = candidate.get('resume_id')
            attachment = requests.get(
                url=f"{snow_instance_uri}/api/now/attachment/{resume_id}/file",
                auth=HTTPBasicAuth(snow_username, snow_password)
            )
            meta = attachment.headers.get('X-Attachment-Metadata')
            meta = json.loads(meta)
            file_name = meta.get('file_name')
            dir_path = f"{resume_root_path}/{email}"
            resume_path = f"{dir_path}/{file_name}"

            exists = os.path.exists(dir_path)
            if exists:
                for filename in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print('Failed to delete %s. Reason: %s' % (file_path, e))
            else:
                os.makedirs(dir_path)

            f = open(resume_path, "wb")
            f.write(attachment.content)
            f.close()

            candidate_rec = Candidate.query.filter_by(email=email).first()
            if candidate_rec:
                candidate_rec.resume_path = resume_path
                updated_candidates.append({'email': candidate_rec.email, 'resume_path': candidate_rec.resume_path})
            else:
                db.session.add(Candidate(email=email, resume_path=resume_path))
                updated_candidates.append({'email': email, 'resume_path': resume_path})

            db.session.commit()

    return updated_candidates


def get_candidates_from_db(email=None):
    candidate_list = []
    db.create_all()

    if email:
        result = Candidate.query.filter_by(email=email)
    else:
        result = Candidate.query.all()

    for item in result:
        candidate_list.append({'email': item.email, 'resume_path': item.resume_path})
    return candidate_list


def delete_candidates_from_db(email=None):
    if email:
        result = Candidate.query.filter_by(email=email)
        if result:
            candidate_rec = result.first()
            if candidate_rec:
                dir_path = os.path.dirname(candidate_rec.resume_path)
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path)
            num_rows_deleted = result.delete()
            db.session.commit()
            return num_rows_deleted
        return 0
    else:
        dir_path = f"{resume_root_path}/";
        if os.path.exists(dir_path):
            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print('Failed to delete %s. Reason: %s' % (file_path, e))
        num_rows_deleted = db.session.query(Candidate).delete()
        db.session.commit()
        return num_rows_deleted
